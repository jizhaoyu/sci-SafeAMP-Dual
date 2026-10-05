"""Close this evidence batch and check the existing immutable MIC delivery."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
PRIOR = ROOT/'03_experiments/audits/hc50_remaining_evidence_followup_20261005_v1'
PRIOR_SHA = 'd8a442b9027a8894913bf85e3f025ff7920b22a6d7db43ba8ff3607ef1626495'
BUNDLE = ROOT/'03_experiments/deliveries/mic_baseline_20261004_v1'
ARCHIVE = BUNDLE.with_suffix('.zip')
BUNDLE_SHA = 'f8b8606dc807279cc78c6728260f6d3d7da463f2416bf47e8d3bafbdf1789ed3'
ARCHIVE_SHA = '858f6aa9a09dfc822b6a7c155a629ae13caf0e2c922abe3448d81119e3491b2b'
STATE = ROOT/'03_experiments/audits/mic_training_readiness_20261004_v26.json'
FORMAL = ROOT/'04_paper/research_status.json'
FINAL_DECISION = 'not_admitted_in_this_external_batch'
DOCS = ['README.md','docs/REMEDIATION_STATUS.md','docs/handoff/TASK_STATE.md',
        'docs/DOCUMENTATION_INDEX.md','03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md']


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda:stream.read(1024*1024),b''):
            result.update(part)
    return result.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)


def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream))


def write_rows(path, data, fields=None):
    with path.open('x',encoding='utf-8-sig',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=fields or list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def current_blocks():
    result = {}
    start,end = '<!-- RESEARCH_STATUS_CURRENT_START -->','<!-- RESEARCH_STATUS_CURRENT_END -->'
    for name in DOCS:
        data = (ROOT/name).read_text(encoding='utf-8')
        require(data.count(start) == data.count(end) == 1,'Invalid MIC current status markers')
        block = data[data.index(start):data.index(end)+len(end)]
        result[name] = hashlib.sha256(block.encode('utf-8')).hexdigest()
    require(len(set(result.values())) == 1,'MIC current document blocks disagree')
    return result


def check_delivery(out):
    require(sha(BUNDLE/'manifest.json') == BUNDLE_SHA and sha(ARCHIVE) == ARCHIVE_SHA,'Trusted delivery/ZIP changed')
    manifest = read_json(BUNDLE/'manifest.json')
    files = {**manifest['files'],'manifest.json':BUNDLE_SHA}
    require(len(files) == 395,'Expected 394 bound files plus manifest')
    for name, expected in files.items():
        path = (BUNDLE/name).resolve()
        require(path.is_relative_to(BUNDLE) and sha(path) == expected,'Delivery file changed: '+name)
    out.mkdir(parents=True)
    commands = []
    with tempfile.TemporaryDirectory(prefix='mic_closeout_validation_') as temporary:
        temporary_root = Path(temporary).resolve()
        require(temporary_root.parent == Path(tempfile.gettempdir()).resolve() and temporary_root.name.startswith('mic_closeout_validation_') and not temporary_root.is_relative_to(ROOT),'Unsafe temporary path')
        target = (temporary_root/'bundle').resolve()
        require(target.is_relative_to(temporary_root),'Unsafe extraction target')
        with zipfile.ZipFile(ARCHIVE) as archive:
            entries = [info for info in archive.infolist() if not info.is_dir()]
            require(len(entries) == len(files) and {info.filename for info in entries} == set(files),'ZIP inventory differs')
            for info in archive.infolist():
                name = info.filename.rstrip('/')
                require(not PurePosixPath(name).is_absolute() and '\\' not in name and ':' not in name and all(x not in {'','..','.'} for x in name.split('/')),'Unsafe ZIP member')
                require((target/name).resolve().is_relative_to(target),'ZIP target outside extraction scope')
                require((info.external_attr >> 16) & 0o170000 != 0o120000,'ZIP symlink forbidden')
                if not info.is_dir():
                    require(hashlib.sha256(archive.read(info)).hexdigest() == files[name],'ZIP content/CRC differs: '+name)
            archive.extractall(target)
        results = {}
        for command in ['verify','replay']:
            argv = [sys.executable,'-I','-B',str(target/'runtime.py'),command,'--bundle',str(target),'--manifest-sha256',BUNDLE_SHA]
            if command == 'replay':
                argv.extend(['--sample-id','3e656d2ae8d48ae33078fcd4'])
            process = subprocess.run(argv,cwd=temporary_root,capture_output=True,text=True,encoding='utf-8',timeout=120)
            commands.append({'command':command,'argv':argv,'working_directory':str(temporary_root),'exit_code':process.returncode})
            for suffix, content in [('stdout',process.stdout),('stderr',process.stderr)]:
                with (out/f'{command}.{suffix}.txt').open('x',encoding='utf-8') as stream:
                    stream.write(content)
            save(out/'commands.json',commands) if command == 'replay' else None
            require(process.returncode == 0,'Packaged runtime failed; see archived stdout/stderr')
            result = json.loads(process.stdout)
            save(out/f'{command}.json',result)
            results[command] = result
        validation = results['verify']
        require(validation['status'] == 'passed' and validation['models_reloaded'] == 9 and validation['oof_rows_independently_recomputed'] == 51 and validation['fit_calls_during_validation'] == 0 and validation['scaler_training_range_verified'],'Incomplete runtime verification')
        require(len(results['replay']) == 3 and {r['sample_id'] for r in results['replay']} == {'3e656d2ae8d48ae33078fcd4'},'Sample replay coverage mismatch')
        csv_rows = rows(BUNDLE/'run/oof_predictions.csv')
        expected = [r for r in csv_rows if r['sample_id'] == '3e656d2ae8d48ae33078fcd4']
        require({r['model'] for r in expected} == {r['model'] for r in results['replay']},'Replay model coverage mismatch')
        for result in results['replay']:
            row = next(r for r in expected if r['model'] == result['model'])
            require(int(row['fold']) == result['fold'] and int(row['observed_label']) == result['observed_label'] and abs(float(row['probability'])-result['probability']) <= 1e-12,'Sample replay differs from saved OOF')
        require(target.resolve().is_relative_to(temporary_root),'Temporary cleanup target changed')
    require(not temporary_root.exists(),'Temporary extraction not cleaned')
    require(sha(BUNDLE/'manifest.json') == BUNDLE_SHA and sha(ARCHIVE) == ARCHIVE_SHA,'Immutable delivery changed during check')
    generated = datetime.now(timezone.utc).isoformat()
    summary = {'generated_at':generated,'status':'passed','engineering_delivery_accepted':True,
               'bundle':BUNDLE.relative_to(ROOT).as_posix(),'archive':ARCHIVE.relative_to(ROOT).as_posix(),
               'manifest_sha256':BUNDLE_SHA,'archive_sha256':ARCHIVE_SHA,'archive_bytes':ARCHIVE.stat().st_size,
               'bound_files_checked':394,'zip_files_checked':395,'zip_contents_and_crc_checked':True,
               'isolated_python':True,'outside_workspace':True,'temporary_extraction_cleaned':True,
               'models_reloaded':9,'oof_rows_recomputed':51,'single_sample_replay_rows':3,
               'fit_calls':0,'scaler_training_range_verified':True,
               'formal_results_available':False,'publication_ready':False,
               'protected':{p.relative_to(ROOT).as_posix():sha(p) for p in [ARCHIVE,BUNDLE/'manifest.json',STATE,FORMAL]},
               'bundle_files':files,'outputs':{p.name:sha(p) for p in out.iterdir() if p.is_file()}}
    save(out/'summary.json',summary)
    print(json.dumps({k:summary[k] for k in ['status','bound_files_checked','zip_files_checked','models_reloaded','oof_rows_recomputed','fit_calls','outside_workspace']}))


def close(out, delivery):
    require(sha(PRIOR/'review/manifest.json') == PRIOR_SHA,'Previous scientific review changed')
    previous = read_json(PRIOR/'review/manifest.json')
    protected = {**previous['protected'],**previous['inputs']}
    protected.update({p.relative_to(ROOT).as_posix():sha(p) for p in PRIOR.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    check = read_json(delivery/'summary.json')
    require(check['status'] == 'passed' and check['engineering_delivery_accepted'],'Delivery check incomplete')
    protected.update(check['protected'])
    for name,expected in check['bundle_files'].items():
        protected[(BUNDLE/name).relative_to(ROOT).as_posix()] = expected
    for name,expected in protected.items():
        require(sha(ROOT/name) == expected,'Protected input changed: '+name)
    for name,expected in check['outputs'].items():
        require(sha(delivery/name) == expected,'Delivery check result changed')
    current = rows(PRIOR/'review/current_scope_records.csv')
    old = rows(PRIOR/'review/merged_candidate_decisions.csv')
    scope = [r for r in current if r['decision'] != 'excluded_by_known_molecular_form']
    gaps = {r['candidate_id']:r for r in rows(PRIOR/'review/evidence_gap_triage.csv')}
    require(len(scope) == 30 and len(current) == 41 and len(old) == len({r['candidate_id'] for r in old}) == 78,'Expected fixed 30/41/78 scope')
    require(all(r['formal_release'] == r['sequence_and_form_release'] == 'False' for r in scope),'Unexpected previously released sample')
    decisions, updates = [], {}
    for row in scope:
        gap = gaps[row['candidate_id']]
        decisions.append({'candidate_id':row['candidate_id'],'name':row['name'],'pmid':row['pmid'],'doi':row['doi'],
                          'previous_decision':row['decision'],'final_batch_decision':FINAL_DECISION,
                          'blocking_evidence_categories':gap['gap_category'],'evidence_basis':row['reason'],
                          'required_evidence_to_reopen':gap['next_evidence_requirement'],
                          'source_location':row['source_location'],'formal_release':False,'assay_label_generated':False,
                          'meaning':'Closed for this batch; not a negative biological label or claim that measurements never exist.'})
        updated = dict(row)
        updated['decision'] = FINAL_DECISION
        updated['review_scope'] = 'user_approved_existing_primary_audits_closeout; no new measurement review'
        updated['reason'] += ' 本轮依据既有原始测定审计结案：尚不满足现行完整分子/目标端点准入条件，本批不准入；不生成标签、不继续本批检索，未来只有提供可核查新证据并重新审查才能打开。'
        updates[row['candidate_id']] = updated
    merged = [updates.get(r['candidate_id'],r) for r in old]
    retained = [updates.get(r['candidate_id'],r) for r in current]
    generated = datetime.now(timezone.utc).isoformat()
    validation = read_json(delivery/'verify.json')
    summary = {'generated_at':generated,'data_version':BASE.name,'protocol_id':'protocol-amd-02',
               'evidence_batch_status':'closed_without_eligible_external_cohort','batch_closeout_complete':True,
               'current_batch_search_tasks':0,'historical_candidate_records':78,'current_screened_scope_records':41,
               'final_not_admitted_records':30,'known_form_exclusions':11,'archived_unavailable_original_records':37,
               'decision_counts':dict(Counter(r['decision'] for r in merged)),
               'eligible_external_records':0,'cross_cohort_isolation_status':'not_run_no_evidence_eligible_records',
               'formal_dual_task_status':'blocked','formal_results_available':False,'publication_ready':False,
               'homology_boundary':'>=0.40 unchanged','archived_37_search_restarted':False,'network_requests':0,
               'mic_training_status':'local_exploratory_training_independently_verified','mic_state_path':STATE.relative_to(ROOT).as_posix(),
               'mic_protocol_id':'protocol-mic-13','mic_molecules':17,'mic_models':9,'mic_oof_rows':51,
               'mic_delivery_status':'verified_existing_frozen_bundle','mic_delivery_check':(delivery/'summary.json').relative_to(ROOT).as_posix(),
               'mic_bundle':BUNDLE.relative_to(ROOT).as_posix(),'mic_archive':ARCHIVE.relative_to(ROOT).as_posix(),
               'mic_manifest_sha256':BUNDLE_SHA,'mic_archive_sha256':ARCHIVE_SHA,'training_state_changed':False,'model_fit_calls':0,
               'project_original_dual_task_objective_completed':False,'independent_human_review':False}
    out.mkdir(parents=True)
    write_rows(out/'final_evidence_decisions.csv',decisions)
    write_rows(out/'current_scope_records.csv',retained)
    write_rows(out/'merged_candidate_decisions.csv',merged)
    write_rows(out/'eligible_external_records.csv',[],fields=['candidate_id','sequence','mic_label','hc50_label','primary_source','formal_release'])
    save(out/'project_delivery_status.json',summary)
    write_rows(out/'mic_all_model_metrics.csv',validation['pooled_descriptive_metrics'])
    report = f'''# 本批证据结案与MIC工程交付

生成时间：{generated}（UTC）。本批版本`{BASE.name}`；外部证据协议`protocol-amd-02`，MIC训练协议`protocol-mic-13`。

## 最终结论

本批证据审查已结案，继续检索待办0。30条最终不准入、11条已知形式排除、37条此前缺原文归档，共78条完整追溯；没有合格外部记录。30条没有生成阴性标签，也不意味着永久排除或实验不存在。每条具体阻断类别、原审计依据及重新打开所需证据在`final_evidence_decisions.csv`。

证据合格记录为0，所以没有执行跨队列隔离；状态为`not_run_no_evidence_eligible_records`，不能写作隔离通过。原双任务仍blocked，原研究目标没有完成，正式结果与投稿就绪false。原协议、>=0.40全员隔离、标签与分子形式边界保持原样。

## 当前可交付结果

MIC探索训练已完成，17个分子、42条测定表述、固定三折、44维特征、LR/RF/Dummy共9模型、51条OOF。42条表述不代表42次独立实验。当前状态v26及历史训练和原始证据保留不变。本轮没有重新fit、调参、校准、模型选优或新肽预测。

交付复用`{summary['mic_archive']}`。ZIP {check['archive_bytes']}字节，SHA256 `{ARCHIVE_SHA}`；manifest `{BUNDLE_SHA}`。实际核对394份绑定文件和ZIP内395份文件，ZIP内容及CRC均一致；在工作区外临时解压，用`python -I -B`执行包内verify和单个已准入样本replay。复核重载9模型、独立复算51条OOF和全部指标、验证缩放器训练范围，零fit；样本重放3条与保存OOF一致，临时目录已清理。运行stdout/stderr、退出码和指标保存在`{delivery.relative_to(ROOT).as_posix()}`。

该包支持已准入队列留出预测重放及审计，不是未经验证的新肽生产预测服务。历史性能已看过、样本量小且没有合格独立外部队列，所以不能声明外部泛化、临床用途或投稿资格。所有模型完整指标一并见`mic_all_model_metrics.csv`，不选最好模型。

## 验证范围与剩余限制

本轮核查数据/证据绑定、冻结包、模型预测、原样保留及结案文档；不运行pytest或重新训练。此前交付相关历史回归记录为60 passed/1 failed，冻结旧发布器不兼容17分子42表述；不能把本轮审计通过写成整个项目测试全通过。此前新增58项交付回归结果保留，不冒称本轮重新执行。

这是用户认可范围下的工程交付和证据批次收尾。原双任务科学条件仍未满足；只有同一合规分子的原始人HC50与E.coli MIC证据、明确形式和足够独立样本通过原协议门禁，才能另开有证据的新批次。当前不自动继续检索或训练。
'''
    with (out/'report.md').open('x',encoding='utf-8') as stream:
        stream.write(report)
    block = f'''<!-- PROJECT_CLOSEOUT_CURRENT_START -->
## 本批结案与交付（机器审计）

状态来源：`{(out/'project_delivery_status.json').relative_to(ROOT).as_posix()}`；生成时间：{generated}（UTC）；版本：`{BASE.name}`。
证据协议：`protocol-amd-02`；MIC训练协议：`protocol-mic-13`；MIC状态来源仍为`{STATE.relative_to(ROOT).as_posix()}`。

- 本批外部证据审查：已结案；30条不准入、11条形式排除、37条缺原文归档；合格外部0，当前检索待办0。
- 跨队列隔离：`not_run_no_evidence_eligible_records`；没有把未执行记为通过。
- MIC探索工程交付：现有17样本/9模型/51OOF冻结包本轮复核通过，零fit，工作区外ZIP运行通过。
- 原双任务：`blocked`；原研究目标未完成；正式结果/投稿就绪：`false`/`false`。

交接入口：[项目收尾与交付指南](D:/桌面文件/sci/docs/handoff/PROJECT_CLOSEOUT_20261005.md)。证据结案表和本轮运行检查见状态来源所列目录；历史MIC机器状态块保留。
<!-- PROJECT_CLOSEOUT_CURRENT_END -->
'''
    with (out/'current_closeout_block.md').open('x',encoding='utf-8') as stream:
        stream.write(block)
    inputs = {Path(__file__).relative_to(ROOT).as_posix():sha(Path(__file__))}
    inputs.update({p.relative_to(ROOT).as_posix():sha(p) for p in delivery.rglob('*') if p.is_file()})
    save(out/'manifest.json',{'generated_at':generated,'protected':protected,'inputs':inputs,'mic_current_document_blocks':current_blocks(),
                             'outputs':{p.name:sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps(summary))


def verify(review, output):
    manifest = read_json(review/'manifest.json')
    for group in ['protected','inputs','outputs']:
        root = review if group == 'outputs' else ROOT
        for name,expected in manifest[group].items():
            path = (root/name).resolve()
            require(path.is_relative_to(root) and sha(path) == expected,'Binding mismatch: '+name)
    require(current_blocks() == manifest['mic_current_document_blocks'],'MIC current status changed')
    old = rows(PRIOR/'review/merged_candidate_decisions.csv')
    current = rows(PRIOR/'review/current_scope_records.csv')
    decisions = rows(review/'final_evidence_decisions.csv')
    merged = rows(review/'merged_candidate_decisions.csv')
    retained = rows(review/'current_scope_records.csv')
    eligible = rows(review/'eligible_external_records.csv')
    scope = {r['candidate_id'] for r in current if r['decision'] != 'excluded_by_known_molecular_form'}
    require(len(scope) == len(decisions) == 30 and {r['candidate_id'] for r in decisions} == scope,'Final decision coverage differs')
    require(len(merged) == len({r['candidate_id'] for r in merged}) == 78 and len(retained) == 41 and not eligible,'Scope/eligible inventory differs')
    require([r['candidate_id'] for r in old] == [r['candidate_id'] for r in merged],'Historical IDs/order changed')
    by_id = {r['candidate_id']:r for r in merged}
    require(retained == [by_id[r['candidate_id']] for r in current],'Retained table differs')
    preserved = 0
    allowed_changes = {'decision','reason','review_scope'}
    for before,after in zip(old,merged):
        if before['candidate_id'] not in scope:
            require(before == after,'Archived/form-excluded record changed')
            preserved += 1
        else:
            require(after['decision'] == FINAL_DECISION and after['reason'].startswith(before['reason']),'Wrong closeout decision')
            require(all(before[k] == after[k] for k in before if k not in allowed_changes),'Source/assay fact altered')
            require(after['formal_release'] == after['sequence_and_form_release'] == 'False','Unqualified release')
    require(preserved == 48,'Expected unchanged 37 archived plus 11 form exclusions')
    summary = read_json(review/'project_delivery_status.json')
    require(summary['decision_counts'] == dict(Counter(r['decision'] for r in merged)),'State counts differ')
    require(summary['evidence_batch_status'] == 'closed_without_eligible_external_cohort' and summary['current_batch_search_tasks'] == summary['eligible_external_records'] == summary['model_fit_calls'] == summary['network_requests'] == 0,'Incomplete closure')
    require(summary['cross_cohort_isolation_status'] == 'not_run_no_evidence_eligible_records' and summary['formal_dual_task_status'] == 'blocked' and not summary['project_original_dual_task_objective_completed'] and not summary['formal_results_available'] and not summary['publication_ready'] and not summary['training_state_changed'],'False scientific completion')
    checks = {'generated_at':datetime.now(timezone.utc).isoformat(),'status':'passed','review_manifest_sha256':sha(review/'manifest.json'),
              'protected_files_checked':len(manifest['protected']),'input_files_checked':len(manifest['inputs']),'output_files_checked':len(manifest['outputs']),
              'final_decisions_checked':30,'retained_records':41,'historical_records':78,'archived_or_form_excluded_unchanged':48,
              'eligible_external_records':0,'isolation_not_claimed_passed':True,'mic_current_document_blocks_unchanged':5,
              'model_fit_calls':0,'formal_dual_task_status':'blocked','original_objective_completed':False}
    save(output,checks)
    print(json.dumps(checks))


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command',required=True)
    check = commands.add_parser('check-delivery')
    check.add_argument('--output',type=Path,required=True)
    build = commands.add_parser('close')
    build.add_argument('--delivery-check',type=Path,required=True)
    build.add_argument('--output',type=Path,required=True)
    audit = commands.add_parser('verify')
    audit.add_argument('--review',type=Path,required=True)
    audit.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(BASE) and not output.exists(),'Choose a new output inside this audit')
    if args.command == 'check-delivery':
        check_delivery(output)
    elif args.command == 'close':
        delivery = args.delivery_check.resolve()
        require(delivery.is_relative_to(BASE),'Delivery check outside this audit')
        close(output,delivery)
    else:
        review = args.review.resolve()
        require(review.is_relative_to(BASE),'Review outside this audit')
        verify(review,output)


if __name__ == '__main__':
    main()
