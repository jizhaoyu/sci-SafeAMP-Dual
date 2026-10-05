"""Bounded original-source audit. No dataset release, label assignment, or model fitting."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
from bs4 import BeautifulSoup
import fitz
from acquire_sources import BASE, ROOT, PRIOR, sha, save

INVENTORY = ROOT / '03_experiments/audits/hc50_primary_followup_20261004_v1/acquisition/candidate_inventory.csv'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def csv_save(path, records):
    require(bool(records), f'Empty table: {path}')
    with path.open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def html(path):
    return BeautifulSoup(path.read_bytes(), 'html.parser')


def cells(row):
    return [cell.get_text(' ', strip=True) for cell in row.find_all(['td', 'th'], recursive=False)]


def classify_response(record, directory):
    if 'file' not in record:
        return 'request_failed_not_original'
    path = directory / record['file']
    require(sha(path) == record['sha256'], f'Changed capture: {path}')
    if record['requested_file'] == 'pmid_27818338_author_accepted.pdf':
        return 'author_manuscript_identity_reviewed'
    if record['requested_file'] in ['pmid_34302796_primary.html', 'pmid_16940535_primary.html']:
        return 'primary_html_identity_reviewed'
    if record['status'] == 'bioc_acquired_requires_identity_review':
        return 'supporting_bioc_identity_reviewed'
    data = path.read_bytes()
    text = html(path).get_text(' ', strip=True).lower()
    if 'challenge' in text or 'pow_challenge' in data.decode('utf-8', errors='replace').lower():
        return 'access_check_not_original'
    if text == 'redirecting':
        return 'redirect_stub_not_original'
    return 'non_primary_response_not_original'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    require(out.is_relative_to(BASE) and not out.exists(), 'Use a new output directory inside this audit batch')
    acquisition = BASE / 'acquisition'
    additional = BASE / 'additional_acquisition'
    captured = json.loads((acquisition / 'manifest.json').read_text(encoding='utf-8'))
    for name, expected in captured['protected'].items():
        require(sha(ROOT / name) == expected, f'Protected input changed: {name}')
    for folder in [acquisition, additional]:
        manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
        for name, expected in manifest['outputs'].items():
            require(sha(folder / name) == expected, f'Capture output changed: {name}')
    extra_manifest = json.loads((additional / 'manifest.json').read_text(encoding='utf-8'))
    require(sha(acquisition / 'manifest.json') == extra_manifest['inputs']['acquisition/manifest.json'], 'Acquisition binding changed')
    inputs = {p.relative_to(ROOT).as_posix(): sha(p) for folder in [acquisition, additional] for p in folder.rglob('*') if p.is_file()}
    for p in [Path(__file__), BASE / 'scripts/primary_review_notes.json', BASE / 'scripts/acquire_sources.py', BASE / 'scripts/acquire_additional.py', INVENTORY]:
        inputs[p.relative_to(ROOT).as_posix()] = sha(p)
    notes = json.loads((BASE / 'scripts/primary_review_notes.json').read_text(encoding='utf-8'))
    for name in notes['visual_review']['images']:
        inputs[(BASE / name).relative_to(ROOT).as_posix()] = sha(BASE / name)
    subset = read_rows(acquisition / 'candidate_subset.csv')
    prior = read_rows(PRIOR / 'merged_candidate_decisions.csv')
    inventory = {r['candidate_id']: r for r in read_rows(INVENTORY)}
    ids = {r['candidate_id'] for r in subset}
    require(len(subset) == len(ids) == 44 and len(prior) == 78, 'Candidate coverage changed')
    require(ids == {r['candidate_id'] for r in prior if r['screen_status'] == 'original_not_acquired'}, 'Missing-original subset changed')
    catalog = json.loads((acquisition / 'study_catalog.json').read_text(encoding='utf-8'))
    require(len(catalog) == 28, 'Source coverage changed')
    decisions = {r['candidate_id']: dict(r) for r in subset}
    source_raw = [(r, folder) for folder in [acquisition, additional] for r in json.loads((folder / 'source_acquisition.json').read_text(encoding='utf-8'))]
    attempts = []
    for record, directory in source_raw:
        attempts.append({**record, 'capture_directory': directory.relative_to(BASE).as_posix(), 'reviewed_response_role': classify_response(record, directory)})

    source_reviews = []
    acquired = {'27818338', '34302796', '16940535'}
    for study in catalog:
        original = study['pmid'] in acquired
        source_reviews.append({
            'study_id': study['study_id'], 'pmid': study['pmid'], 'doi': study['doi'], 'pmcid': study['pmcid'],
            'title': study['title'], 'candidate_ids': ';'.join(study['candidate_ids']),
            'capture_attempts': sum(r['pmid'] == study['pmid'] and r['doi'] == study['doi'] for r in attempts),
            'original_identity_reviewed': original,
            'review_mode': 'agent_original_source_review' if original else 'public_access_attempt_only',
            'license': ('repository states publisher copyright; redistribution permission not established' if study['pmid'] == '27818338' else
                        'PMC author manuscript; no CC license established in captured notice' if study['pmid'] == '34302796' else
                        'Copyright 2006 American Society for Microbiology; no CC license established' if study['pmid'] == '16940535' else 'original not acquired; permission not established'),
            'decision': 'endpoint_screen_completed_no_formal_release' if original else 'original_access_gap_not_evidence_of_absent_assay',
            'formal_release': False,
        })
    observations, identities = [], []

    def identity(cid, source_seq, location, source_name, mass='', basis='', form='not fully confirmed'):
        entry = inventory[cid]
        matched = entry['sequence'] == source_seq
        identities.append({'candidate_id': cid, 'inventory_name': entry['name'], 'source_name': source_name,
                           'inventory_sequence': entry['sequence'], 'source_sequence': source_seq,
                           'inventory_length': len(entry['sequence']), 'source_length': len(source_seq),
                           'sequence_match': matched, 'source_location': location,
                           'reported_mass_da': mass, 'mass_basis': basis, 'molecular_form_evidence': form,
                           'sequence_and_form_release': False})
        return matched

    def observe(cid, source_name, endpoint, target, value, unit, location, source_file, conditions, limitation, **extra):
        observations.append({'candidate_id': cid, 'source_molecule_name': source_name,
                             'endpoint': endpoint, 'target': target, 'raw_value': value, 'unit': unit,
                             'source_location': location, 'source_file': source_file, 'conditions': conditions,
                             'limitation': limitation, 'formal_label': '', 'formal_release': False,
                             'conditional_lower_ug_ml': extra.get('lower', ''), 'conditional_upper_ug_ml': extra.get('upper', ''),
                             'conversion_mass_da': extra.get('mass', ''), 'conversion_basis': extra.get('basis', '')})

    salmon_file = 'acquisition/raw/pmid_27818338_author_accepted.pdf'
    with fitz.open(BASE / salmon_file) as document:
        pdf = [p.get_text() for p in document]
    joined = ''.join(pdf).lower()
    require(len(pdf) == 37 and '10.1016/j.fsi.2016.11.004' in joined, 'Wrong salmon paper')
    require('antimicrobial and host cell-directed activities' in joined, 'Salmon title missing')
    table_text = ' '.join(pdf[30].split())
    match = re.search(r'E\. coli ATCC 25922 ((?:\d+\s+){5}\d+) S\. aureus', table_text)
    require(match is not None, 'E. coli row not found')
    mic_values = match.group(1).split()
    require(mic_values == ['32', '4', '2', '16', '4', '16'], 'Changed Table 2 row')
    require('up to 100 µM' in pdf[18] and 'human red blood cells' in pdf[18] and 'Figure S1' in pdf[18], 'Human narrative missing')
    require('MIC >64 µM' in pdf[15] and 'complete' in pdf[15], 'Complete-medium statement missing')
    for note in notes['salmon']:
        cid, name = note['candidate_id'], note['source_name']
        require(inventory[cid]['pmid'] == '27818338', 'Salmon PMID mismatch')
        require(note['mw_da'] in pdf[29], 'Salmon Table 1 mass missing')
        matched = identity(cid, note['source_sequence'], 'Figure 1; PDF page 32; visual transcription', name,
                           note['mw_da'], 'Table 1 MW; average/monoisotopic basis not explicitly stated',
                           'Fmoc synthesis reported; full terminal/stereochemical form not released; STF disulfide belongs to another molecule')
        limitation = 'source-named molecule only; ' + ('sequence matches; full form/S1 pending' if matched else 'sequence differs from inventory; no assay transfer to inventory molecule')
        observe(cid, name, 'MIC', 'E. coli ATCC 25922', mic_values[note['mic_column']], 'µM',
                'Table 2; PDF page 31; E. coli row', salmon_file, '5% TSB in SPB; pH 7.4; table represents three independent experiments', limitation)
        observe(cid, name, 'human_hemolysis_qualitative_test_ceiling', 'human red blood cells', 'no hemolytic effects reported up to 100', 'µM test ceiling; not a reported HC50',
                'Results; PDF page 19; lines 450-457; Figure S1 cited but not acquired', salmon_file,
                'human assay 30 min, 37 C; PBS; separate trout assay is not used', limitation + '; no exact HC50 or digitized value inferred')
        observe(cid, name, 'MIC_bacterial_panel_statement', 'bacterial panel; no individual row shown', '>64', 'µM',
                'Results; PDF page 16; lines 370-387; data not shown', salmon_file,
                'complete Mueller-Hinton broth; complete TSB also inactive without an explicit numeric value',
                limitation + '; preserve complete-vs-diluted medium discrepancy; panel statement not an additional strain-specific measurement')
        decisions[cid].update(screen_status='primary_sequence_and_medium_discrepancy_reviewed', review_scope='agent_original_source_review; key PDF pages visually inspected; not independent human review',
                              source_location='Figure 1; Tables 1/2; human assay and Results; PDF pages 11,16,19,30-32',
                              decision='current_source_insufficient_for_dual_release',
                              reason=('清单与Figure 1的rtCATH2(5-40)序列不一致，不转移测定。' if not matched else '序列与Figure 1一致；完整分子形式仍待核实。') +
                              '人RBC仅报告100 µM测试范围内未见溶血，所引S1未取得；不填写精确HC50。保留稀培养基有限MIC与完整MH菌群MIC >64 µM的条件差异，不挑选低MIC准入。',
                              formal_release='False', sequence_and_form_release='False',
                              study_independence='one_measurement_study; development study aliases not yet audited', cross_cohort_audit='not_released; all-member external audit not run')

    ant_file = 'acquisition/raw/pmid_34302796_primary.html'
    ant = html(BASE / ant_file)
    require('10.1016/j.bcp.2021.114693' in ant.get_text().lower(), 'Wrong ponericin DOI')
    require('Multipurpose peptides:' in ant.select_one('h1').get_text(), 'Wrong ponericin title')
    seq_row = next(cells(r) for r in ant.select('#T1 tbody tr') if 'M-PONTX–Nc1a' in r.get_text())
    mic_row = cells(ant.select('#T2 tbody tr')[0])
    hc_row = next(cells(r) for r in ant.select('#T3 tbody tr') if cells(r)[0] == 'Nc1a')
    require(seq_row[2] == inventory[notes['ant_candidate_id']]['sequence'], 'Nc1a sequence mismatch')
    require(mic_row[2] == '25.8–51.6' and hc_row[7] == '28.6–48.2', 'Nc1a endpoint cell changed')
    require('human red blood cells' in ant.select_one('#T3').get_text(' ', strip=True), 'HC50 target missing')
    cid = notes['ant_candidate_id']
    identity(cid, seq_row[2], 'Table 1, Nc1a row', 'M-PONTX–Nc1a', seq_row[4],
             'observed monoisotopic mass; theoretical monoisotopic mass 2478.3 Da',
             'Results describes short linear peptides without detected post-translational modifications; synthesis uses chlorotrityl resin; complete release not asserted')
    mass = Decimal(seq_row[4])
    for endpoint, target, value, low, high, location, conditions in [
        ('HC50', 'human red blood cells', hc_row[7], '28.6', '48.2', 'Table 3 Nc1a hemolysis column; Methods 2.11/P19', '37 C, 1 h; two independent experiments with duplicate assays; reported interval retained'),
        ('MIC', 'E. coli ATCC 25922 (source HTML renders strain as 259922)', mic_row[2], '25.8', '51.6', 'Table 2 E. coli Nc1a column; Methods 2.9', 'source-specific antimicrobial assay; strain typography ambiguity retained; lowest MIC across other species not used'),
    ]:
        observe(cid, 'Nc1a', endpoint, target, value, 'µM', location, ant_file, conditions,
                'conditional monoisotopic-mass conversion for threshold-gap illustration only; not a formal mass/label release',
                lower=str(Decimal(low)*mass/1000), upper=str(Decimal(high)*mass/1000), mass=str(mass), basis='observed monoisotopic mass, Table 1; not confirmed formal conversion basis')
    decisions[cid].update(screen_status='primary_human_hc50_range_and_ecoli_mic_reviewed', review_scope='agent_original_source_review; not independent human review',
                          source_location='PMC10167921; Tables 1-3; Methods 2.6/2.9/2.11; Results', decision='current_source_insufficient_for_dual_release',
                          reason='序列一致；真实人RBC HC50为28.6–48.2 µM，不能取平均或只取下端标类。用原文单同位素质量作条件换算时范围跨100 µg/mL；E. coli MIC 25.8–51.6 µM位于既定类别空档。Table 3的最低MIC与HEK293 CC50均不替代对应端点。正式单位口径及来源/全员隔离未释放。',
                          formal_release='False', sequence_and_form_release='False', study_independence='one_measurement_study; development study aliases not yet audited', cross_cohort_audit='not_released; all-member external audit not run')

    dhvar_file = 'acquisition/raw/pmid_16940535_primary.html'
    dhvar = html(BASE / dhvar_file)
    require('10.1128/jvi.00796-06' in dhvar.get_text().lower(), 'Wrong Dhvar3 DOI')
    section = dhvar.select_one('#sec2').get_text(' ', strip=True)
    sequence = re.search(r'Dhvar3, ([A-Z]+);', section).group(1)
    identity(notes['dhvar_candidate_id'], sequence, 'Peptide synthesis and purification, #sec2', 'Dhvar3',
             form='sequence confirmed; full terminal form not released; FITC labeling in this section applies to Dh-5/Dhvar2, not Dhvar3')
    article_body = dhvar.select_one('article') or dhvar
    body_text = article_body.get_text(' ', strip=True).lower()
    require(not re.search(r'hemolys|haemolys|\bhc\s*50\b', body_text), 'Unexpected hemolysis mention requires fresh review')
    decisions[notes['dhvar_candidate_id']].update(screen_status='primary_molecular_identity_only_reviewed', review_scope='agent_original_source_review; not independent human review',
                           source_location='PMC1563894; Peptide synthesis and purification, #sec2', decision='current_source_insufficient_for_dual_release',
                           reason='原文可核对Dhvar3序列，未找到本任务所需的人RBC HC50或E. coli MIC测定；其他细胞/病毒端点不替代。FITC标记属于另外两个分子，不转移到Dhvar3。结论仅限这篇已取得原文。',
                           formal_release='False', sequence_and_form_release='False', study_independence='qualifying_measurement_source_not_established', cross_cohort_audit='not_released; all-member external audit not run')

    for cid, row in decisions.items():
        if row['pmid'] not in acquired:
            row['review_scope'] = 'public_source_access_attempt; original not acquired'
            row['reason'] += ' 本批已尝试公开来源，取得的重定向/访问检查/非原文响应或请求失败不算原文；访问缺口不证明测定不存在。'
    updated = list(decisions.values())
    merged = [decisions.get(row['candidate_id'], row) for row in prior]
    summary = {
        'generated_at': datetime.now(timezone.utc).isoformat(), 'data_version': BASE.name,
        'review_output_version': out.name, 'review_mode': 'agent_original_source_review', 'independent_human_review': False,
        'fixed_batch_candidates': 44, 'fixed_batch_studies': 28, 'capture_attempts': len(attempts),
        'new_original_papers_identity_reviewed': 3, 'new_candidates_endpoint_screened': len(identities),
        'sequence_matches': sum(r['sequence_match'] for r in identities), 'sequence_conflicts': sum(not r['sequence_match'] for r in identities),
        'new_human_hc50_reported_ranges': 1, 'new_exact_hc50_values': 0, 'raw_observation_rows': len(observations),
        'formal_external_released': 0, 'formal_scientific_status': 'blocked', 'protocol_id': 'protocol-amd-02',
        'homology_boundary': '>=0.40 unchanged', 'training_state_changed': False, 'model_fit_calls': 0,
        'merged_candidate_records': len(merged), 'merged_decision_counts': dict(Counter(r['decision'] for r in merged)),
        'merged_candidates_endpoint_screened': sum(r['screen_status'] != 'original_not_acquired' for r in merged),
        'remaining_original_access_gaps': sum(r['screen_status'] == 'original_not_acquired' for r in merged),
        'batch_outcome': 'review_complete_formal_release_blocked',
    }
    out.mkdir(parents=True)
    csv_save(out / 'candidate_decisions.csv', updated)
    csv_save(out / 'merged_candidate_decisions.csv', merged)
    csv_save(out / 'source_review.csv', source_reviews)
    csv_save(out / 'sequence_identity_review.csv', identities)
    csv_save(out / 'raw_assay_observations.csv', observations)
    save(out / 'response_review.json', attempts)
    save(out / 'visual_review.json', notes['visual_review'])
    save(out / 'summary.json', summary)
    report = f'''# 缺失原文候选公开来源跟进

生成时间：{summary['generated_at']}。数据版本：`{BASE.name}`；协议：`protocol-amd-02`。本批代理原文复核，不是独立人工审稿。

## 本批结果

固定44条、28个来源，保存40次公开请求记录；取得并核对3篇原文，新增筛查7条。累计 **41/78** 已筛查，**37条**仍缺原文。已取得来源涉及3个测量/候选来源，不代表3个通过隔离的外部研究。

发现1条真实人RBC HC50范围；新增正式准入 **0**。正式双任务保持 **blocked**；未运行训练、修订协议或生成正式模型结果。此前MIC探索性训练与交付状态保持原样。

## 原文决定

### 鲑鱼肽：5条，同一论文

[作者接受稿](https://air.uniud.it/bitstream/11390/1102192/1/D%27Este%20et%20al%20FSI%202016%20accepted.pdf)，DOI `10.1016/j.fsi.2016.11.004`。Figure 1、Tables 1/2及人RBC方法/结果已视觉复核。4条清单序列匹配；rtCATH2(5-40)清单35残基，原图36残基，少一个S，不修改历史清单、不将测定移给不一致分子。片段编号保留原名，不用编号推算缺失序列。

Table 2的大肠杆菌MIC在稀培养基下有数值；正文同时报告完整MH培养基菌群MIC >64 µM。两种条件均保留；完整MH是菌群陈述、未逐菌株列值，不伪装为独立大肠杆菌单株测量。完整TSB只有未显示数据的无活性陈述，不复制MH的数值。本文人RBC结果为100 µM范围内未见溶血，所引Figure S1未取得。Figure 4A是鱼红细胞，不能补成人HC50；不从文字填精确HC50。分子完整形式未释放。

### Nc1a：1条，HC50是真实范围，标签不能确定

[PMC原文](https://pmc.ncbi.nlm.nih.gov/articles/PMC10167921/)，DOI `10.1016/j.bcp.2021.114693`。Table 1序列一致，正文支持线性且未检测到翻译后修饰；Table 3人RBC HC50为 **28.6–48.2 µM**，Table 2对应E. coli MIC为 **25.8–51.6 µM**。保存原范围，不平均、不只取端点；Table 3跨物种最低MIC及细胞CC50不作为目标标签。

原文单同位素观测质量只作条件换算展示：HC50 **70.8708–119.4396 µg/mL**，跨100阈值；MIC **63.9324–127.8648 µg/mL**，处于32与128之间。单同位素质量不是已确认的正式换算口径，以上均不产生正式标签。论文HTML的菌株号显示为259922，保留其排版歧义。来源别名、分子完整准入和全员隔离均未释放。

### Dhvar3：1条，只有分子身份可核对

[PMC原文](https://pmc.ncbi.nlm.nih.gov/articles/PMC1563894/)，DOI `10.1128/JVI.00796-06`。方法中序列匹配，未找到本任务要求的人RBC HC50和E. coli MIC。其他端点不转为标签。该节FITC标签属于其他分子，不归到Dhvar3。本结论仅限已取得原文，不断言全部文献没有合格测定。

## 访问与许可缺口

其余25个来源/37条仍缺可归档原文。DOI重定向存根、访问检查、403、429、超时、TLS失败及非XML服务页面均单列。追加公开PDF尝试未成功。没有处理访问挑战，也未将错误响应计为原文。原文访问可用不等于允许再分发：作者稿/PMC的版权说明保留，未建立CC许可的来源标为权限待确认。

## 复跑与验收

三份CSV分别保留逐候选决定、逐研究访问结论、原始测定；累计清单固定78条。`sequence_identity_review.csv`包括源图转录与序列冲突。所有正式标签留空，准入为False。`manifest.json`绑定来源响应、前序审计、脚本、转录及视觉产物；核查结果见`verification.json`。

```powershell
python -X utf8 03_experiments/audits/hc50_missing_originals_20261005_v1/scripts/review_sources.py --output 03_experiments/audits/hc50_missing_originals_20261005_v1/review_reproduction_v1
python -X utf8 03_experiments/audits/hc50_missing_originals_20261005_v1/scripts/verify_sources.py --review 03_experiments/audits/hc50_missing_originals_20261005_v1/review_reproduction_v1 --output 03_experiments/audits/hc50_missing_originals_20261005_v1/review_reproduction_v1/verification.json
```

输出目录必须不存在；复跑从已绑定本地来源重建决定，网络获取不是可保证相同的过程。核查覆盖、单元格及摘要不等同独立人工复核。后续优先补鲑鱼稿S1、原始序列冲突和剩余37条原文；找到合格证据后仍需按既有规则执行完整准入与全员隔离。
'''
    with (out / 'report.md').open('x', encoding='utf-8') as stream:
        stream.write(report)
    save(out / 'manifest.json', {'generated_at': summary['generated_at'], 'prior_review_manifest_sha256': sha(PRIOR / 'manifest.json'),
                                'inputs': inputs, 'protected': captured['protected'],
                                'outputs': {p.name: sha(p) for p in out.iterdir() if p.is_file()},
                                'formal_release': False, 'model_fit_calls': 0})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
