"""Archive 37 unavailable-original candidates by user scope decision; no evidence release."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
PRIOR = ROOT/'03_experiments/audits/hc50_salmon_endpoint_closure_20261005_v1'
PRIOR_SHA = '6983d6ae7ec52103061674dd076448fb8fb32027bc45ae9e5f1dae8e0d52b815'
DECISION = 'excluded_from_current_scope_original_unavailable'
USER_REQUEST = '这37条如果找不到就不找了,或者直接去掉'
DOCS = ['README.md','docs/REMEDIATION_STATUS.md','docs/handoff/TASK_STATE.md',
        'docs/DOCUMENTATION_INDEX.md','03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream))


def save(path, value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)


def write_rows(path, data):
    with path.open('x',encoding='utf-8-sig',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def current_blocks():
    result = {}
    start, end = '<!-- RESEARCH_STATUS_CURRENT_START -->', '<!-- RESEARCH_STATUS_CURRENT_END -->'
    for name in DOCS:
        text = (ROOT/name).read_text(encoding='utf-8')
        require(text.count(start) == text.count(end) == 1, 'Missing/duplicate current block: '+name)
        block = text[text.index(start):text.index(end)+len(end)]
        result[name] = hashlib.sha256(block.encode('utf-8')).hexdigest()
    require(len(set(result.values())) == 1, 'Current document blocks differ')
    return result


def close(out):
    require(sha(PRIOR/'review/manifest.json') == PRIOR_SHA, 'Previous manifest changed')
    prior = json.loads((PRIOR/'review/manifest.json').read_text(encoding='utf-8'))
    protected = {**prior['protected'], **prior['inputs']}
    protected.update({p.relative_to(ROOT).as_posix():sha(p) for p in PRIOR.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for name, expected in protected.items():
        require(sha(ROOT/name) == expected, 'Protected source changed: '+name)
    old = rows(PRIOR/'review/merged_candidate_decisions.csv')
    removed = [r for r in old if r['screen_status'] == 'original_not_acquired']
    retained = [r for r in old if r['screen_status'] != 'original_not_acquired']
    require(len(old) == len({r['candidate_id'] for r in old}) == 78 and len(removed) == 37 and len(retained) == 41, 'Frozen scope differs')
    require(all(r['decision'] == 'pending' and r['formal_release'] == 'False' for r in removed), 'Unexpected released/unavailable candidate')
    archive = []
    for row in removed:
        revised = dict(row)
        revised['decision'] = DECISION
        revised['review_scope'] = 'user_directed_scope_exclusion; no additional evidence review'
        revised['reason'] += ' 用户决定停止本轮继续获取缺原文的37条，退出当前候选审查范围；仅归档来源缺口，不代表实验不存在或阴性，不用于训练。'
        archive.append(revised)
    updates = {r['candidate_id']:r for r in archive}
    merged = [updates.get(r['candidate_id'],r) for r in old]
    generated = datetime.now(timezone.utc).isoformat()
    summary = {'generated_at':generated, 'data_version':BASE.name, 'protocol_id':'protocol-amd-02',
               'previous_review_manifest_sha256':PRIOR_SHA, 'scope_change_basis':'explicit user decision',
               'user_request':USER_REQUEST, 'historical_candidate_records':78, 'current_screened_scope_records':41,
               'archived_unavailable_original_records':37, 'archived_source_identifier_pairs':len({(r['pmid'],r['doi']) for r in removed}),
               'active_original_search_tasks':0, 'resume_archived_search_requires_new_user_request':True,
               'current_scope_decision_counts':dict(Counter(r['decision'] for r in retained)),
               'historical_merged_decision_counts':dict(Counter(r['decision'] for r in merged)),
               'remaining_evidence_followup_records':sum(r['decision'] not in {'excluded_by_known_molecular_form'} for r in retained),
               'formal_external_released':0, 'formal_scientific_status':'blocked',
               'homology_boundary':'>=0.40 unchanged','training_state_changed':False,'model_fit_calls':0,
               'network_requests':0,'independent_human_review':False,
               'meaning':'Scope exclusion only; missing evidence is not a negative assay label or proof of experimental absence.'}
    blocks = current_blocks()
    out.mkdir(parents=True)
    write_rows(out/'current_scope_records.csv',retained)
    write_rows(out/'scope_exclusions.csv',archive)
    write_rows(out/'merged_candidate_decisions.csv',merged)
    save(out/'summary.json',summary)
    report = f'''# 缺原文37条退出当前审查范围

生成时间：{generated}（UTC）。数据版本`{BASE.name}`，科学协议`protocol-amd-02`。

## 用户决定与执行结果

用户提出：“{USER_REQUEST}”。按照这一决定，既定78条中的37条缺原文候选退出本轮审查，停止进一步网络检索；涉及25个DOI/PMID标识对。未删除历史来源或获取尝试，未推断实验不存在，未改成阴性标签。再次审查这些记录须有新的用户请求或提供原文后的明确准入审查。

当前已筛查范围保留41条，逐字段与前一批一致：22条来源不足、10条待证据复核、9条因已知分子形式排除；仍待证据的为32条。41条是已筛查范围，不能理解为41条训练样本。78条追溯表仍保留全部ID，其中37条新决定为`{DECISION}`，并保留`original_not_acquired`的历史事实。

## 状态口径

当前缺原文37条的继续检索待办为0；历史缺原文记录为37。这是工作范围收缩，不是证据已经取得或科学门禁已通过。正式外部新增0，原双任务仍blocked；当前MIC探索状态v26及其训练结果保持原样。0.40全员隔离、标签和分子形式规则不变，没有新训练、邮件或外部请求。

## 产物与核查

- `current_scope_records.csv`：41条保留范围，含原排除记录，原决定不变。
- `scope_exclusions.csv`：37条退出决定与历史来源、缺口理由。
- `merged_candidate_decisions.csv`：78条完整追溯清单。
- `summary.json`：本批范围状态；不能替代正式研究准入状态。
- `manifest.json`：绑定前一批、历史保护文件、生成脚本、五份当前状态块和本批输出。

本批只是执行用户的范围决定，没有新增测定审查，也不声称独立人工评审。摘要核对、范围覆盖和复跑结论以实际`verification.json`及`reproduction_check.json`为准。
'''
    with (out/'report.md').open('x',encoding='utf-8') as stream:
        stream.write(report)
    save(out/'manifest.json', {'generated_at':generated,'protected':protected,
                              'inputs':{Path(__file__).relative_to(ROOT).as_posix():sha(Path(__file__))},
                              'current_document_blocks':blocks,
                              'outputs':{p.name:sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps(summary,ensure_ascii=True))


def verify(review, output):
    manifest = json.loads((review/'manifest.json').read_text(encoding='utf-8'))
    for group in ['protected','inputs','outputs']:
        root = review if group == 'outputs' else ROOT
        for name, expected in manifest[group].items():
            path = (root/name).resolve()
            require(path.is_relative_to(root) and sha(path) == expected, 'Binding mismatch: '+name)
    require(current_blocks() == manifest['current_document_blocks'], 'Current status block changed')
    old = rows(PRIOR/'review/merged_candidate_decisions.csv')
    retained = rows(review/'current_scope_records.csv')
    removed = rows(review/'scope_exclusions.csv')
    merged = rows(review/'merged_candidate_decisions.csv')
    require(retained == [r for r in old if r['screen_status'] != 'original_not_acquired'], 'Retained records changed')
    old_removed = [r for r in old if r['screen_status'] == 'original_not_acquired']
    require(len(retained) == 41 and len(removed) == len(old_removed) == 37 and len(merged) == 78, 'Coverage mismatch')
    require([r['candidate_id'] for r in removed] == [r['candidate_id'] for r in old_removed], 'Wrong records excluded')
    require(len({(r['pmid'],r['doi']) for r in removed}) == 25, 'Source scope mismatch')
    for before, after in zip(old_removed,removed):
        require({k:v for k,v in before.items() if k not in {'decision','reason','review_scope'}} == {k:v for k,v in after.items() if k not in {'decision','reason','review_scope'}}, 'Assay/source fact changed')
        require(after['decision'] == DECISION and after['reason'].startswith(before['reason']) and after['formal_release'] == 'False', 'Improper scope decision')
    updates = {r['candidate_id']:r for r in removed}
    require(merged == [updates.get(r['candidate_id'],r) for r in old], 'Traceability table mismatch')
    require(len({r['candidate_id'] for r in merged}) == 78, 'Duplicate candidate IDs')
    summary = json.loads((review/'summary.json').read_text(encoding='utf-8'))
    require(summary['current_scope_decision_counts'] == dict(Counter(r['decision'] for r in retained)) and summary['historical_merged_decision_counts'] == dict(Counter(r['decision'] for r in merged)), 'Summary counts mismatch')
    require(summary['active_original_search_tasks'] == summary['formal_external_released'] == summary['model_fit_calls'] == summary['network_requests'] == 0 and summary['formal_scientific_status'] == 'blocked' and not summary['training_state_changed'], 'Unexpected release/work state')
    result = {'generated_at':datetime.now(timezone.utc).isoformat(),'status':'passed','review_manifest_sha256':sha(review/'manifest.json'),
              'protected_files_checked':len(manifest['protected']),'output_files_checked':len(manifest['outputs']),
              'retained_records_unchanged':41,'scope_exclusion_records':37,'source_identifier_pairs':25,
              'historical_traceability_records':78,'current_document_blocks_unchanged':5,'formal_external_released':0,'model_fit_calls':0}
    save(output,result)
    print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command',required=True)
    build = commands.add_parser('close')
    build.add_argument('--output',type=Path,required=True)
    check = commands.add_parser('verify')
    check.add_argument('--review',type=Path,required=True)
    check.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(BASE) and not output.exists(), 'Choose a new output inside this audit')
    if args.command == 'close':
        close(output)
    else:
        review = args.review.resolve()
        require(review.is_relative_to(BASE), 'Review must remain inside this audit')
        verify(review,output)


if __name__ == '__main__':
    main()
