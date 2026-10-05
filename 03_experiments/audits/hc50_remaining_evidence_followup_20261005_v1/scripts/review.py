"""Classify retained evidence gaps and review bounded primary-source findings."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from acquire import BASE, ROOT, PRIOR, PRIOR_SHA, PLP, SLAY, save, sha

AY = ROOT/'03_experiments/audits/hc50_primary_followup_20261004_v1/acquisition/raw/pmid_30872680.xml'
FORM_EXCLUSIONS = {'HIST_DRAMP21421':'AY1C-AgNP','HIST_DRAMP21423':'CAY1-AgNP'}
DOCS = ['README.md','docs/REMEDIATION_STATUS.md','docs/handoff/TASK_STATE.md',
        'docs/DOCUMENTATION_INDEX.md','03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md']


def require(value, message):
    if not value:
        raise ValueError(message)


def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream))


def write_rows(path, data):
    with path.open('x',encoding='utf-8-sig',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def text(node):
    return ' '.join(''.join(node.itertext()).split())


def blocks():
    import hashlib
    result = {}
    start,end = '<!-- RESEARCH_STATUS_CURRENT_START -->','<!-- RESEARCH_STATUS_CURRENT_END -->'
    for name in DOCS:
        data = (ROOT/name).read_text(encoding='utf-8')
        require(data.count(start) == data.count(end) == 1, 'Invalid current markers')
        result[name] = hashlib.sha256(data[data.index(start):data.index(end)+len(end)].encode('utf-8')).hexdigest()
    require(len(set(result.values())) == 1, 'Current status blocks disagree')
    return result


def gap(row):
    status = row['screen_status']
    categories = {
        'primary_mbc_and_single_point_hemolysis_reviewed':('MBC_not_MIC; single_point_not_HC50; form_unconfirmed','SLAY S2/S3仍未取得；本轮有限公开路径结束，保留原端点不符结论'),
        'animal_rbc_only':('non_human_RBC','已审查来源种属不符；需要同一分子的独立人HC50原始测定'),
        'publisher_figure_and_cited_primary_followup_reviewed':('single_point_or_missing_HC50; identity_or_condition_unresolved','本轮不重复已完成的正式图检索；按上一批具体身份/培养基冲突保留'),
        'endpoint_and_species_conflict':('HC10_not_HC50; RBC_species_conflict','解决原文物种矛盾仍不能把HC10变成HC50'),
        'endpoint_mismatch':('MIC80_not_MIC; missing_HC50','游离肽保留端点不符；两个明确银纳米颗粒缀合物按形式排除'),
        'single_concentration_hemolysis':('single_point_not_HC50; RBC_species_unconfirmed','方法论文全文未取得；保留种属未知，不借用其他pilosulin测定'),
        'primary_human_hc50_range_and_ecoli_mic_reviewed':('threshold_interval_unresolved; MIC_category_gap','真实范围不取平均、不选端点；原测定不能按当前规则确定类别'),
        'supplement_sequence_and_censored_endpoints_reviewed':('censored_HC50_bound_insufficient; form_unconfirmed','现有删失下界不足；不能四舍五入或调阈值放行'),
        'primary_molecular_identity_only_reviewed':('target_endpoints_missing','该已审查论文无所需目标端点；细胞/病毒测定不转用'),
        'original_sequence_and_curve_conflict_reviewed':('HC50_text_figure_conflict; fungal_MIC_not_Ecoli_MIC; form_unconfirmed','需解决图文冲突并提供对应E.coli测定；不转用真菌MIC'),
    }
    require(status in categories,'Unclassified retained record: '+row['candidate_id'])
    category, action = categories[status]
    return {'candidate_id':row['candidate_id'],'name':row['name'],'pmid':row['pmid'],'doi':row['doi'],
            'previous_screen_status':status,'gap_category':category,'next_evidence_requirement':action,
            'formal_release':False,'archived_37_reopened':False}


def primary_checks():
    plp = ET.parse(PLP).getroot()
    ay = ET.parse(AY).getroot()
    require('10.3390/toxins11010050' in text(plp) and 'Mass Spectrometry Analysis' in text(plp.find('.//article-title')),'Wrong PLP source')
    table = plp.find(".//table-wrap[@id='toxins-11-00050-t003']")
    plp_row = next(r for r in table.findall('.//tr') if r.find('td') is not None and text(r.find('td')) == 'PLP2')
    cells = [text(c) for c in plp_row.findall('td')]
    require(cells[:6] == ['PLP2','<6.2','<6.2','<50','Negative','10.4'],'Unexpected PLP2 row encoding')
    require('NBRC 14237' in text(table) and 'at 50' in text(table) and 'Hemolytic Activity' in text(table),'PLP header mismatch')
    method = plp.find(".//sec[@id='sec4dot5-toxins-11-00050']")
    require(any(r.get('rid') == 'B6-toxins-11-00050' for r in method.findall('.//xref')),'Wrong method reference')
    reference = plp.find(".//ref[@id='B6-toxins-11-00050']")
    require('10.1016/j.abb.2004.05.013' in text(reference) and '15246874' in text(reference),'Method DOI/PMID not matched')
    metadata = json.loads((BASE/'acquisition/raw/plp_method_metadata.json').read_text(encoding='utf-8'))
    require(metadata['hitCount'] == 1 and metadata['resultList']['result'][0]['id'] == '15246874' and metadata['resultList']['result'][0]['doi'] == '10.1016/j.abb.2004.05.013','Wrong method metadata')
    require('10.1038/s41598-019-41005-7' in text(ay) and 'A Peptide-Nanoparticle System' in text(ay.find('.//article-title')),'Wrong conjugate source')
    ay_table = ay.find(".//table-wrap[@id='Tab1']")
    require(all(x in text(ay_table) for x in ['AY1C-NP','CAY1-NP','E. coli']),'Conjugate table aliases absent')
    paragraphs = [text(p) for p in ay.iter('p')]
    defining = next(p for p in paragraphs if 'AY1C-AgNP' in p and 'CAY1-AgNP' in p and 'Silver nanoparticles' in p)
    require('corresponding conjugates' in defining,'Source does not define conjugated molecules')
    require(any('MIC80%' in p for p in paragraphs),'Do not misidentify MIC80 as standard MIC')
    return [
        {'candidate_ids':'HIST_DRAMP21455','primary_file':PLP.relative_to(ROOT).as_posix(),'sha256':sha(PLP),
         'location':'Table 3, row PLP2; Section 4.5; reference 6','finding':'E.coli NBRC14237 MIC <6.2 uM; hemolysis at 10 uM literal Negative and at 50 uM 10.4%; no numeric HC50; RBC species unconfirmed',
         'method_source_role':'2004 cited method, not a new PLP2 measurement study','formal_release':False},
        {'candidate_ids':'HIST_DRAMP21421;HIST_DRAMP21423','primary_file':AY.relative_to(ROOT).as_posix(),'sha256':sha(AY),
         'location':'Results defining conjugates; Table 1 AY1C-NP/CAY1-NP; Figure 1 caption','finding':'Measured named objects are silver nanoparticle conjugates, not free unmodified monomeric peptides; exclude those objects under unchanged form rule; MIC80 and hemolysis percent still not substituted',
         'method_source_role':'original measurement paper; no transfer from free peptide rows','formal_release':False}]


def review(out):
    acquisition = json.loads((BASE/'acquisition/manifest.json').read_text(encoding='utf-8'))
    require(sha(PRIOR/'review/manifest.json') == PRIOR_SHA,'Previous closure changed')
    for name, expected in acquisition['protected'].items():
        require(sha(ROOT/name) == expected,'Protected source changed: '+name)
    for name, expected in acquisition['outputs'].items():
        require(sha(BASE/'acquisition'/name) == expected,'Acquired source changed')
    require(sha(BASE/'scripts/acquire.py') == acquisition['script_sha256'],'Acquisition script changed')
    checks = primary_checks()
    old = rows(PRIOR/'review/merged_candidate_decisions.csv')
    current = rows(PRIOR/'review/current_scope_records.csv')
    archived = rows(PRIOR/'review/scope_exclusions.csv')
    unresolved = [r for r in current if r['decision'] != 'excluded_by_known_molecular_form']
    require(len(old) == 78 and len(current) == 41 and len(archived) == 37 and len(unresolved) == 32,'Scope changed')
    triage = [gap(r) for r in unresolved]
    target = [r for r in current if r['pmid'] in {'29307492','30658410'} or r['candidate_id'] in FORM_EXCLUSIONS]
    require(len(target) == 17 and len({r['candidate_id'] for r in target}) == 17,'Expected 17 source follow-up records')
    acquisition_rows = json.loads((BASE/'acquisition/source_acquisition.json').read_text(encoding='utf-8'))
    require(len(acquisition_rows) == 6 and not any(r['status'].startswith('pdf_acquired') for r in acquisition_rows),'Unexpected usable PDF: requires visual/source review before continuing')
    new = []
    for prior in target:
        row = dict(prior)
        row['review_scope'] = 'agent_primary_text_and_bounded_source_followup; not independent human review'
        if row['candidate_id'] in FORM_EXCLUSIONS:
            name = FORM_EXCLUSIONS[row['candidate_id']]
            require(name in row['name'],'Wrong nanoparticle candidate identity')
            row['decision'] = 'excluded_by_known_molecular_form'
            row['screen_status'] = 'primary_nanoparticle_conjugate_form_excluded'
            row['reason'] += ' 本轮重核原文Results和Table 1：该记录是银纳米颗粒缀合受测对象，违反当前未修饰单体形式要求，按已知形式排除；不能用游离肽测定替换。'
            row['source_location'] += '; PMID30872680 Results defining AgNP conjugates; Table 1 NP aliases'
        elif row['pmid'] == '29307492':
            row['reason'] += ' 本轮再次限定4个公开附件请求：2个非PDF响应、2个404，仍未取得S2/S3；本轮路径尝试结束，不对失败页填入MIC或HC50。'
            row['source_location'] += '; retained-followup acquisition/source_acquisition.json'
        else:
            row['reason'] += ' 本轮复核Table 3的PLP2行：E.coli NBRC14237 MIC <6.2 µM，10 µM溶血原文为Negative，50 µM为10.4%；保留原文词语，不将Negative变为0。Section4.5指向2004方法论文，只有元数据及跳转响应，RBC种属仍未知；方法引用不算新的PLP2测定来源。'
            row['source_location'] += '; PMID30658410 Table3 rowPLP2; Section4.5 and reference6; method metadata PMID15246874'
        row['formal_release'] = row['sequence_and_form_release'] = 'False'
        new.append(row)
    updates = {r['candidate_id']:r for r in new}
    merged = [updates.get(r['candidate_id'],r) for r in old]
    retained = [updates.get(r['candidate_id'],r) for r in current]
    generated = datetime.now(timezone.utc).isoformat()
    summary = {'generated_at':generated,'data_version':BASE.name,'protocol_id':'protocol-amd-02',
               'historical_records':78,'current_screened_scope_records':41,'archived_unavailable_original_records':37,
               'archived_37_search_restarted':False,'gap_triage_records':32,'source_followup_records':17,
               'new_known_form_exclusions':2,'remaining_evidence_followup_records':30,
               'current_scope_decision_counts':dict(Counter(r['decision'] for r in retained)),
               'historical_decision_counts':dict(Counter(r['decision'] for r in merged)),
               'network_requests':6,'usable_slay_supplement_pdfs_added':0,'plp_rbc_species_confirmed':False,
               'numeric_human_hc50_added':0,'formal_external_released':0,'formal_scientific_status':'blocked',
               'training_state_changed':False,'model_fit_calls':0,'independent_human_review':False,
               'review_mode':'agent original JATS review and public access follow-up; no independent human review'}
    out.mkdir(parents=True)
    write_rows(out/'evidence_gap_triage.csv',triage)
    write_rows(out/'followup_decisions.csv',new)
    write_rows(out/'current_scope_records.csv',retained)
    write_rows(out/'merged_candidate_decisions.csv',merged)
    write_rows(out/'primary_source_checks.csv',checks)
    save(out/'summary.json',summary)
    report = f'''# 保留候选证据缺口：SLAY、PLP2与AgNP形式复核

生成时间：{generated}（UTC）。版本`{BASE.name}`，协议`protocol-amd-02`。

## 实际进展

已梳理32条未解决记录；其中17条进行本轮来源跟进。原文明确区分AY1C-AgNP/CAY1-AgNP与游离肽，两条银纳米颗粒受测对象据现行未修饰单体规则转为已知形式排除。当前41条范围因此为22条来源不足、8条待复核、11条形式排除，仍有证据问题的记录从32降至30；没有新准入样本。37条缺原文归档决定完全保留，未重新检索。

## 原文及访问结果

- [SLAY原文](https://pmc.ncbi.nlm.nih.gov/articles/PMC5786472/)的两份已观察PMC附件本轮仍为非PDF响应；PII派生出版方mmc6/mmc7地址为404，不能确认附件编号对应关系。S2/S3没有取得，不借失败页填MIC/HC50；该14条既有MBC与单点溶血决定保留。仅结束本轮有限路径尝试，不声称没有其他公开来源。
- [PLP2原文](https://pmc.ncbi.nlm.nih.gov/articles/PMC6356579/)的Table3原始JATS行及表头复核通过：E.coli NBRC14237 MIC <6.2 µM，10 µM溶血栏写Negative，50 µM为10.4%。Negative不解释为测定0，两个固定浓度百分比不生成HC50。Section4.5引用文献6，对应DOI10.1016/j.abb.2004.05.013、PMID15246874；本批核对了元数据，但入口只是跳转页，未取得方法全文，RBC物种仍未知，也不能借其他pilosulin分子的结果。Table2的天然加工形式不自动证明合成受测样品的完整形式。
- [银纳米颗粒论文](https://doi.org/10.1038/s41598-019-41005-7)Results直接定义受测缀合物，Table1使用AY1C-NP/CAY1-NP别名，足以核实两条已知形式排除对象。游离AY1C、CAY1仍保留原决定；不因命名带C而推断环化。原文MIC80及百分比溶血仍不能替代目标MIC/HC50。

## 32条缺口分类

14条SLAY为MBC/单点溶血，5条鲑鱼片段保留端点/身份/培养基问题，2条已知动物RBC，1条HC10与RBC图文物种冲突，4条AY体系端点不符（其中2条本轮形式排除），1条PLP2固定浓度溶血，1条Nc1a范围跨类别/空档，2条黑水虻删失下界不足，1条Dhvar3本来源无目标端点，1条ToAP2图文冲突及真菌MIC。逐条所需证据见`evidence_gap_triage.csv`，不是可训练队列。

## 状态和交付

正式外部新增0，原双任务仍blocked；已完成MIC探索状态v26、训练结果及>=0.40全员隔离保持原样。未拟合模型、发邮件或运行pytest。本轮15条原决定未获放行，两条因实验对象形式排除；其他61条累计记录逐字段不变。

`summary.json`为本轮机器审计状态；`current_scope_records.csv`41条与`merged_candidate_decisions.csv`78条保留来源追溯；`primary_source_checks.csv`绑定原文单元格/定位及摘要。访问时间、失败与响应摘要见上级acquisition。本轮为代理JATS原文复核，未声称独立人工评审；访问失败不证明实验不存在。
'''
    with (out/'report.md').open('x',encoding='utf-8') as stream:
        stream.write(report)
    inputs = {p.relative_to(ROOT).as_posix():sha(p) for p in [AY,PLP,SLAY,Path(__file__),BASE/'scripts/acquire.py',BASE/'acquisition/manifest.json']}
    inputs.update({p.relative_to(ROOT).as_posix():sha(p) for p in (BASE/'acquisition').rglob('*') if p.is_file()})
    save(out/'manifest.json',{'generated_at':generated,'protected':acquisition['protected'],'inputs':inputs,
                             'current_document_blocks':blocks(),'outputs':{p.name:sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps(summary))


def verify(review_dir, output):
    manifest = json.loads((review_dir/'manifest.json').read_text(encoding='utf-8'))
    for group in ['protected','inputs','outputs']:
        root = review_dir if group == 'outputs' else ROOT
        for name, expected in manifest[group].items():
            path = (root/name).resolve()
            require(path.is_relative_to(root) and sha(path) == expected,'Hash/path mismatch: '+name)
    require(blocks() == manifest['current_document_blocks'],'Current status block changed')
    require(rows(review_dir/'primary_source_checks.csv') == [{k:str(v) for k,v in r.items()} for r in primary_checks()], 'Primary cell/identity replay mismatch')
    old = rows(PRIOR/'review/merged_candidate_decisions.csv')
    current = rows(PRIOR/'review/current_scope_records.csv')
    new = rows(review_dir/'followup_decisions.csv')
    merged = rows(review_dir/'merged_candidate_decisions.csv')
    retained = rows(review_dir/'current_scope_records.csv')
    triage = rows(review_dir/'evidence_gap_triage.csv')
    require(len(new) == len({r['candidate_id'] for r in new}) == 17 and len(merged) == 78 and len(retained) == 41 and len(triage) == 32,'Coverage count mismatch')
    mapping = {r['candidate_id']:r for r in new}
    require(merged == [mapping.get(r['candidate_id'],r) for r in old] and retained == [mapping.get(r['candidate_id'],r) for r in current],'Outside-scope record changed')
    archived = rows(PRIOR/'review/scope_exclusions.csv')
    require([r for r in merged if r['decision'] == 'excluded_from_current_scope_original_unavailable'] == archived,'Archived 37 changed')
    require(triage == [{k:str(v) for k,v in gap(r).items()} for r in current if r['decision'] != 'excluded_by_known_molecular_form'],'Triage coverage/classification mismatch')
    before = {r['candidate_id']:r for r in old}
    changed = {r['candidate_id'] for r in merged if r['decision'] != before[r['candidate_id']]['decision']}
    require(changed == set(FORM_EXCLUSIONS),'Unexpected scientific decision changes')
    for row in new:
        previous = before[row['candidate_id']]
        require(all(row[k] == previous[k] for k in ['candidate_id','name','pmid','doi','study_independence','cross_cohort_audit']),'Source/study/isolation fact overwritten')
        require(row['formal_release'] == row['sequence_and_form_release'] == 'False' and row['reason'].startswith(previous['reason']),'Evidence incorrectly released')
    summary = json.loads((review_dir/'summary.json').read_text(encoding='utf-8'))
    require(summary['current_scope_decision_counts'] == dict(Counter(r['decision'] for r in retained)) and summary['historical_decision_counts'] == dict(Counter(r['decision'] for r in merged)),'Count mismatch')
    require(summary['new_known_form_exclusions'] == 2 and summary['remaining_evidence_followup_records'] == sum(r['decision'] != 'excluded_by_known_molecular_form' for r in retained) == 30,'Remaining work count mismatch')
    require(summary['formal_external_released'] == summary['numeric_human_hc50_added'] == summary['model_fit_calls'] == 0 and summary['formal_scientific_status'] == 'blocked' and not summary['training_state_changed'] and not summary['archived_37_search_restarted'],'Unauthorized state change')
    result = {'generated_at':datetime.now(timezone.utc).isoformat(),'status':'passed','review_manifest_sha256':sha(review_dir/'manifest.json'),
              'protected_files_checked':len(manifest['protected']),'input_files_checked':len(manifest['inputs']),'output_files_checked':len(manifest['outputs']),
              'gap_records_checked':32,'followup_decisions_checked':17,'unchanged_outside_scope':61,
              'archived_records_unchanged':37,'original_table_cell_checks':'PLP2 MIC/hemolysis and method identifiers; conjugate identity/aliases',
              'new_form_exclusions':2,'current_document_blocks_unchanged':5,'formal_release':False,'model_fit_calls':0,
              'limitation':'Program replay uses same primary text checks; not independent human review.'}
    save(output,result)
    print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command',required=True)
    build = commands.add_parser('review')
    build.add_argument('--output',type=Path,required=True)
    check = commands.add_parser('verify')
    check.add_argument('--review',type=Path,required=True)
    check.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(BASE) and not output.exists(),'Choose a new output within this audit')
    if args.command == 'review':
        review(output)
    else:
        review_dir = args.review.resolve()
        require(review_dir.is_relative_to(BASE),'Review must remain in this audit')
        verify(review_dir,output)


if __name__ == '__main__':
    main()
