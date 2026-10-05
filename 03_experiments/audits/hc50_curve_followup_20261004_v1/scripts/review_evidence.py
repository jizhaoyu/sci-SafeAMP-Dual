"""Review four fixed candidates. Conditional calculations never release labels or models."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from docx import Document
from acquire_sources import BASE, ROOT, PRIOR, IDS, PAPERS, sha, write_json

OLD = ROOT / '03_experiments/audits/hc50_primary_followup_20261004_v1/acquisition'
DOCS = BASE / 'publisher_static_content_acquisition_20261005/raw'


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def save_csv(path, data):
    with path.open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader(); writer.writerows(data)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def text(element):
    return ' '.join(' '.join(element.itertext()).split())


def doc_table(number):
    return Document(DOCS / f'41598_2026_40997_MOESM{number}_ESM.docx').tables[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    require(not out.exists(), 'Output exists; refusing overwrite')
    acquired = json.loads((BASE / 'acquisition/manifest.json').read_text(encoding='utf-8'))
    protected = acquired['protected']
    inputs = {}
    for folder in ['acquisition', 'publisher_supplements', 'publisher_transport_retry',
                   'publisher_article_acquisition', 'publisher_static_content_acquisition_20261005']:
        manifest = BASE / folder / 'manifest.json'
        data = json.loads(manifest.read_text(encoding='utf-8'))
        inputs[manifest.relative_to(ROOT).as_posix()] = sha(manifest)
        for name, expected in data['outputs'].items():
            inputs[(BASE / folder / name).relative_to(ROOT).as_posix()] = expected
    # Bind all six inspected images and the rendered source tables; keep failed helper folders.
    inspection = BASE / 'inspection_20261005'
    for path in inspection.rglob('*'):
        if path.is_file() and 'libreoffice_profile' not in path.parts:
            inputs[path.relative_to(ROOT).as_posix()] = sha(path)
    for path in (BASE / 'scripts').glob('*.py'):
        inputs[path.relative_to(ROOT).as_posix()] = sha(path)
    for name, expected in {**inputs, **protected}.items():
        require(sha(ROOT / name) == expected, f'Changed input: {name}')
    prior = rows(PRIOR / 'merged_candidate_decisions.csv')
    candidates = {row['candidate_id']: row for row in prior if row['candidate_id'] in IDS}
    require(set(candidates) == IDS, 'Fixed candidate coverage changed')
    inventory = {row['candidate_id']: row for row in rows(OLD / 'candidate_inventory.csv')}
    xml = {pmid: ET.parse(OLD / f'raw/pmid_{pmid}.xml').getroot() for pmid in PAPERS}
    source_review, excerpts = [], {}
    for pmid, r in xml.items():
        ids = {x.get('pub-id-type'): x.text for x in r.findall('.//article-id')}
        require(ids['pmid'] == pmid and ids['pmcid'] == PAPERS[pmid], 'Source identity mismatch')
        require(ids['doi'] == next(row['doi'] for row in candidates.values() if row['pmid'] == pmid), 'DOI mismatch')
        permissions = r.find('.//permissions')
        source_review.append({'pmid': pmid, 'pmcid': ids['pmcid'], 'doi': ids['doi'],
                             'source_file': (OLD / f'raw/pmid_{pmid}.xml').relative_to(ROOT).as_posix(),
                             'source_sha256': sha(OLD / f'raw/pmid_{pmid}.xml'),
                             'review_mode': 'agent_original_source_review; not independent human review',
                             'license_text': text(permissions), 'approved_for_formal_release': False})
    ct = xml['35323465']
    t1 = ct.find(".//table-wrap[@id='marinedrugs-20-00167-t001']")
    require('two disulfide bonds' in text(t1), 'Missing CT7 molecular-form evidence')
    excerpts['CT7_table1'] = text(t1)
    excerpts['CT7_hemolysis_methods'] = text(ct.find(".//sec[@id='sec3dot3-marinedrugs-20-00167']"))
    excerpts['CT7_figure2_caption'] = text(ct.find(".//fig[@id='marinedrugs-20-00167-f002']"))
    toap = xml['27917162']
    excerpts['ToAP2_methods'] = text(toap.find(".//sec[@id='sec8']"))
    excerpts['ToAP2_results'] = text(toap.find(".//sec[@id='sec15']"))
    require('maintained its curve above 50%' in excerpts['ToAP2_results'], 'Missing ToAP2 narrative conflict anchor')
    require('120 min' in excerpts['CT7_hemolysis_methods'] and '1.5 h' in excerpts['CT7_figure2_caption'], 'Missing CT7 timing conflict')
    bsf = xml['41735465']
    for sid in ['Sec3', 'Sec5', 'Sec6', 'Sec7', 'Sec14']:
        element = bsf.find(f".//sec[@id='{sid}']")
        if element is not None:
            excerpts[f'BSF_{sid}'] = text(element)
    s1, s2, s3 = doc_table(1), doc_table(2), doc_table(3)
    require(s2.rows[0].cells[2].text.startswith('Half maximal') and s2.rows[1].cells[2].text == 'Red blood cells (human)', 'Wrong human RBC column')
    require(s2.rows[0].cells[12].text.startswith('Minimum Inhibitory') and s2.rows[1].cells[12].text == 'E. coli', 'Wrong E. coli MIC column')
    s1_rows = {row.cells[0].text.split(' (')[0].strip(): (index, row) for index, row in enumerate(s1.rows[1:], 1)}
    identities, observations, bounds = [], [], []
    for cid, name in [('DBAASP_25709', 'NHill_AD_C49215'), ('DBAASP_25712', 'Hill_BB_C7985')]:
        s1_index, row = s1_rows[name]
        sequence = row.cells[1].text.strip()
        mw = Decimal(row.cells[3].text)
        require(sequence == inventory[cid]['sequence'] and len(sequence) == int(row.cells[2].text), 'Supplement/inventory sequence mismatch')
        identities.append({'candidate_id': cid, 'sequence': sequence, 'source_location': f'Supplementary Table S1, row {s1_index}, Sequence',
                           'source_file': (DOCS / '41598_2026_40997_MOESM1_ESM.docx').relative_to(ROOT).as_posix(),
                           'sequence_verified': True, 'reported_mw_g_per_mol': str(mw),
                           'molecular_form': 'terminal chemistry, stereochemistry and covalent disulfide status not explicitly confirmed; category alone insufficient',
                           'complete_identity_released': False})
        matched = [(i, row) for i, row in enumerate(s2.rows) if row.cells[0].text.strip() == name]
        require(len(matched) == 2 and {row.cells[1].text.strip() for _, row in matched} == {'1', '2'}, 'Missing two independent screening repeats')
        for index, row in matched:
            for column, normalized, reported, target in [(2, 'human_hemolysis_50_percent_censored', 'IC50', 'human red blood cells'),
                                                        (12, 'MIC', 'MIC', 'E. coli ATCC 8739')]:
                value = row.cells[column].text.strip()
                observations.append({'candidate_id': cid, 'repeat': row.cells[1].text.strip(),
                                     'reported_endpoint': reported, 'normalized_endpoint': normalized,
                                     'target': target, 'raw_value': value, 'unit': 'µM',
                                     'source_location': f'Supplementary Table S2; table row {index}; column {column}; zero-based DOCX indexes',
                                     'source_file': (DOCS / '41598_2026_40997_MOESM2_ESM.docx').relative_to(ROOT).as_posix(),
                                     'formal_label': '', 'formal_release': False})
                numeric = Decimal(value.lstrip('>'))
                converted = numeric * mw / Decimal(1000)
                # These calculations illustrate threshold insufficiency only; identity is not released.
                tentative = 'positive_if_mass_and_identity_accepted' if normalized == 'MIC' and not value.startswith('>') and converted <= 32 else 'unknown'
                bounds.append({'candidate_id': cid, 'repeat': row.cells[1].text.strip(), 'endpoint': normalized,
                               'operator': '>' if value.startswith('>') else '=', 'reported_value_uM': str(numeric),
                               'source_reported_mw_g_per_mol': str(mw), 'conditional_value_ug_per_ml': str(converted),
                               'calculation_basis': 'Supplement S1 reported molecular weight; conditional only, complete molecular form not verified',
                               'threshold_interpretation': tentative, 'formal_label': '', 'formal_release': False})
    # ToAP2's full sequence appears in original Table 1, while its analog is a different molecule.
    toap_seq = next(''.join(tr.findall('td')[3].itertext()).strip() for tr in toap.find(".//table-wrap[@id='T1']").findall('.//tbody/tr')
                    if ''.join(tr.findall('td')[0].itertext()).strip() == 'ToAP2')
    require(toap_seq == inventory['DBAASP_9865']['sequence'], 'ToAP2 original sequence mismatch')
    identities.append({'candidate_id': 'DBAASP_9865', 'sequence': toap_seq, 'source_location': 'Table 1, ToAP2 row',
                       'source_file': (OLD / 'raw/pmid_27917162.xml').relative_to(ROOT).as_posix(),
                       'sequence_verified': True, 'reported_mw_g_per_mol': '', 'molecular_form': 'no explicit full terminal-chemistry confirmation; do not borrow amidated ToAP2S1 identity',
                       'complete_identity_released': False})
    # Figure 1B was visually inspected; retain the exact transcription as an auditable agent decision.
    ct7_sequence = 'RVCIRVCYRGVCYRRCW'
    require(ct7_sequence == inventory['DBAASP_19706']['sequence'], 'CT7 figure transcription mismatch')
    identities.append({'candidate_id': 'DBAASP_19706', 'sequence': ct7_sequence, 'source_location': 'Figure 1B CT7 row; Table 1 footnote 3',
                       'source_file': (BASE / 'acquisition/raw/ct7_figure_1.jpg').relative_to(ROOT).as_posix(),
                       'sequence_verified': True, 'reported_mw_g_per_mol': '', 'molecular_form': 'four cysteines forming two disulfide bonds, explicitly stated in Table 1 footnote 3',
                       'complete_identity_released': False})
    ct_table = ct.find(".//table-wrap[@id='marinedrugs-20-00167-t002']")
    for tr in ct_table.findall('.//tbody/tr'):
        cells = [text(td) for td in tr.findall('td')]
        if len(cells) == 9 and cells[0].startswith('E. coli'):
            observations.append({'candidate_id': 'DBAASP_19706', 'repeat': 'not individually reported', 'reported_endpoint': 'MIC',
                                 'normalized_endpoint': 'MIC', 'target': cells[0], 'raw_value': cells[7], 'unit': 'µM',
                                 'source_location': f'Table 2, CT7 column, {cells[0]} (ATTC spelling retained as published)',
                                 'source_file': (OLD / 'raw/pmid_35323465.xml').relative_to(ROOT).as_posix(),
                                 'formal_label': '', 'formal_release': False})
    require(sum(o['candidate_id'] == 'DBAASP_19706' for o in observations) == 6, 'CT7 E. coli row coverage')
    conflicts = [
        {'candidate_id': 'DBAASP_19706', 'issue': 'hemolysis_exposure_conflict', 'evidence': 'Figure 2 caption 1.5 h; Methods 3.3 120 min', 'resolution': 'unresolved; no exact HC50 derived'},
        {'candidate_id': 'DBAASP_19706', 'issue': 'approximation_is_not_exact_hc50', 'evidence': 'Results describe almost 50% at 128 µM; tachyplesin-1 HC50 is a different molecule', 'resolution': 'CT7 numeric HC50 left missing'},
        {'candidate_id': 'DBAASP_9865', 'issue': 'figure_and_narrative_disagree', 'evidence': 'Figure 3A solid ToAP2 curve appears near/below 50%; Results say above 50%; open-square ToAP2S1 is distinct', 'resolution': 'unresolved; no curve fit, numerical digitization or HC50 assignment'},
        {'candidate_id': 'DBAASP_25709', 'issue': 'mic_boundary_cannot_be_rounded_up', 'evidence': '>32 µM × 3985.541 / 1000 = >127.537312 µg/mL; negative boundary is >=128', 'resolution': 'unknown conditional MIC label; not rounded to 128'},
        {'candidate_id': 'DBAASP_25709|DBAASP_25712', 'issue': 'rbc_lower_bound_below_negative_threshold', 'evidence': 'RBC IC50 >32 µM; conditional bounds >127.537312 and >103.482208 µg/mL do not reach >=250', 'resolution': 'HC50 labels remain unknown; bounds are not exact values'},
        {'candidate_id': 'DBAASP_25709|DBAASP_25712', 'issue': 'structure_class_is_not_covalent_identity', 'evidence': 'S1 gives Alo/Defensin classes but lacks explicit termini and covalent disulfide confirmation', 'resolution': 'molecular form remains pending; cysteine count not used to fabricate bonds'},
    ]
    reasons = {
        'DBAASP_19706': ('excluded_by_known_molecular_form', 'explicit_disulfide_form_excluded', '原文及图确认 CT7；表1明确两个二硫键，不符合当前未修饰线性肽边界。HC50仅近似曲线，暴露时间冲突仍保留。'),
        'DBAASP_9865': ('current_source_insufficient_for_dual_release', 'original_sequence_and_curve_conflict_reviewed', 'ToAP2序列确认；人溶血正文与Figure 3A不一致，无精确HC50。此研究测的是真菌MIC，不能当作大肠杆菌MIC；完整末端形式仍待核实。'),
        'DBAASP_25709': ('pending', 'supplement_sequence_and_censored_endpoints_reviewed', 'S1/S2确认本分子及两个重复的RBC IC50 >32 µM、E. coli MIC >32 µM；质量阈值条件不足，末端/共价形式仍待核实，不能借用其他分子或四舍五入放行。'),
        'DBAASP_25712': ('pending', 'supplement_sequence_and_censored_endpoints_reviewed', 'S1/S2确认本分子、两个重复E. coli MIC 8 µM及RBC IC50 >32 µM；RBC下界不足以产生当前HC50类别，完整末端/共价形式仍待核实。'),
    }
    decisions = []
    for cid, row in candidates.items():
        revised = dict(row)
        decision, status, reason = reasons[cid]
        revised.update(decision=decision, screen_status=status, reason=reason,
                       review_scope='agent_primary_source_and_image_review; not independent human review',
                       source_location='Supplementary Tables S1/S2 and methods Sec5/Sec6' if cid.startswith('DBAASP_257') else 'Original figures, tables and methods; see source_regions.json',
                       formal_release='False', sequence_and_form_release='False',
                       study_independence='original measurement study identified; independent external study audit not passed',
                       cross_cohort_audit='not_released; sequence verification alone does not establish zero leakage')
        decisions.append(revised)
    updates = {row['candidate_id']: row for row in decisions}
    merged = [updates.get(row['candidate_id'], row) for row in prior]
    generated = datetime.now(timezone.utc).isoformat()
    summary = {'generated_at': generated, 'data_version': BASE.name, 'review_output_version': out.name,
               'review_mode': 'agent_original_source_review', 'independent_human_review': False,
               'fixed_batch_candidates': 4, 'sequence_matches': 4, 'primary_studies_followed_up': 3,
               'supplementary_documents_acquired_and_visually_reviewed': 3,
               'new_distinct_human_hemolysis_50_percent_censored_molecules': 2,
               'censored_human_rbc_repeat_observations': 4, 'new_exact_hc50_values': 0,
               'paired_ecoli_mic_repeat_observations': 4, 'ct7_ecoli_table_rows': 6,
               'formal_external_released': 0, 'formal_scientific_status': 'blocked',
               'protocol_id': 'protocol-amd-02', 'homology_boundary': '>=0.40 unchanged',
               'training_state_changed': False, 'model_fit_calls': 0,
               'merged_candidate_records': len(merged), 'merged_decision_counts': dict(Counter(row['decision'] for row in merged)),
               'merged_candidates_endpoint_screened': sum(row['screen_status'] != 'original_not_acquired' for row in merged),
               'remaining_original_access_gaps': sum(row['screen_status'] == 'original_not_acquired' for row in merged)}
    out.mkdir(parents=True, exist_ok=False)
    for filename, data in [('sequence_identity_review.csv', identities), ('raw_assay_observations.csv', observations),
                           ('conditional_threshold_checks.csv', bounds), ('source_review.csv', source_review),
                           ('conflicts.csv', conflicts), ('candidate_decisions.csv', decisions), ('merged_candidate_decisions.csv', merged)]:
        save_csv(out / filename, data)
    write_json(out / 'source_regions.json', {'regions': excerpts, 'image_review': 'CT7 Figure 1B/2A, ToAP2 Figure 3A and all three DOCX rendered pages visually reviewed; no numerical digitization',
               'source_status_correction': 'publisher_article_acquisition/raw/nature_primary.html is Client Challenge, not primary article despite HTTP 200; not used as evidence',
               'supplement_S3_scope': 'prediction scores and cross-paper summaries not treated as original MIC/HC50; S2 columns determine endpoints'})
    write_json(out / 'summary.json', summary)
    report = f"""# 人红细胞曲线与补充表复核\n\n生成时间：{generated}（UTC）；数据版本 `{BASE.name}`；本次输出 `{out.name}`。协议 `protocol-amd-02` 与 >=0.40 门禁未修改。代理原文和图像复核，不是独立人工评审。\n\n## 实际进展\n\n本批深查既定四条候选、三篇原始研究。取得黑水虻论文三份出版方 DOCX 补充表，原样保存并通过既有 LibreOffice 导出 PDF、逐页渲染复核。两条分子的完整序列均与库存一致；S2 逐重复人红细胞 IC50 是溶血50%端点的删失下界，不能与 MRC5 或细菌生长 IC50 混用。\n\n| 候选 | 原始证据 | 本批决定 |\n|---|---|---|\n| CT7 | Figure 1B 序列与库存一致；Table 1 明确两个二硫键；6条E. coli测定行含2条n.d. | 因已知共价形式排除；不把近50%曲线写成HC50，保留1.5h/120min冲突 |\n| ToAP2 | Table 1 序列一致；Figure 3A 与正文关于50%的陈述不一致；本研究MIC对象为真菌 | 当前来源不足；HC50不读图拟合、不借用ToAP2S1；末端身份仍待核实 |\n| NHill_AD_C49215 | S1 序列/MW；S2两个重复E. coli MIC >32 µM、人RBC IC50 >32 µM | 仍待核实；条件换算下界不能四舍五入达到标签阈值 |\n| Hill_BB_C7985 | S1 序列/MW；S2两个重复E. coli MIC 8 µM、人RBC IC50 >32 µM | 仍待核实；RBC下界不足、完整分子形式未确认 |\n\n## 阈值核对与准入边界\n\n仅用于解释缺口的条件换算，采用 S1 报告的 MW，不声称完整分子身份已释放：NHill 的 >32 µM 对应 >127.537312 µg/mL，不能保证达到 MIC 阴性边界 >=128；NHill 与 Hill 的溶血50%下界分别 >127.537312、>103.482208 µg/mL，均不足以确定 HC50 >=250 或 <=100 类别。Hill 的 MIC 8 µM 条件值为25.870552 µg/mL；这不消除 HC50/形式缺口。全部正式标签留空，新增正式外部记录0。\n\nS1 的 Alo/Defensin 分类和Cys数量不是二硫键实测依据，末端及共价形式继续待核实。S3 的预测值与既往论文汇总不产生当前测量标签，也不虚增独立研究。两次筛查重复不等于两篇独立研究。尚未通过开发集研究别名与全员同源准入审计。\n\n## 完成范围与剩余工作\n\n四条都是以前已经初筛的记录，因此累计筛查仍为 {summary['merged_candidates_endpoint_screened']}/78，当前渠道仍有 {summary['remaining_original_access_gaps']} 条缺原文；累计分类为 `{json.dumps(summary['merged_decision_counts'], ensure_ascii=False)}`。新增两条分子的真实人RBC删失端点证据（4个重复测定），没有新增精确HC50。原双任务仍 `blocked`，既有MIC训练/协议/模型保持原样。\n\n下一步优先取得剩余44条的原文；本批两条黑水虻肽还需覆盖当前HC50判定边界的测定及明确分子形式，不能靠修改阈值解决。CT7的形式不合格结论已确定；ToAP2的图文冲突可向作者澄清，但本轮未发送消息。\n\n## 来源、验收与复跑\n\n原研究：[黑水虻2026](https://doi.org/10.1038/s41598-026-40997-3)、[CT7 2022](https://doi.org/10.3390/md20030167)、[ToAP2 2016](https://doi.org/10.3389/fmicb.2016.01844)。原文声明许可保存在 `source_review.csv`；不自动把正文许可扩展至未核实的第三方材料。全部获取尝试与失败保留；Nature主页面本地响应是Client Challenge，不作原文；最终补充表来自公开Springer附件地址。\n\n`verification.json` 仅验证覆盖、原始单元格、条件换算与保护摘要，不代表独立人工审稿或科学准入通过。表、清单与摘要见本目录；获取及图像在上一层目录。输出已存在则拒绝覆盖。\n\n```powershell\npython -X utf8 03_experiments/audits/hc50_curve_followup_20261004_v1/scripts/review_evidence.py --output 03_experiments/audits/hc50_curve_followup_20261004_v1/review_my_run\n```\n"""
    with (out / 'report.md').open('x', encoding='utf-8') as stream:
        stream.write(report)
    write_json(out / 'manifest.json', {'generated_at': generated, 'inputs': inputs, 'protected': protected,
               'outputs': {p.name: sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
