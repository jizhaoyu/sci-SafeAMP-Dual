"""Generate current state and exact document patches without changing history."""
import argparse
import difflib
import json
import shutil
from pathlib import Path

from publish_mic_repair_status import DOCS, START, END
from research_utils import ROOT, read_json, sha256, utc_now
from research_evidence_gate import verify_manifest
from repair_alternative_primary_audit import verify_bindings


def save(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def generate(state_path, backup_dir):
    if state_path.exists() or backup_dir.exists():
        raise FileExistsError('State or document backup already exists')
    ready_path = ROOT / '03_experiments/audits/mic_training_readiness_20261004_v25.json'
    ready = read_json(ready_path)
    protocol = ROOT / '03_experiments/protocols/protocol-mic-13.json'
    freeze = ROOT / '03_experiments/audits/protocol_mic_13_freeze_20261004_v1.json'
    release = ROOT / '03_experiments/audits/mic_goat_followup_release_20261004_v1'
    review_path = ROOT / '03_experiments/audits/mic_goat_run_validation_20261004_v1.json'
    run = ROOT / '03_experiments/runs/mic_goat_baseline_20261004_v2'
    review = read_json(review_path)
    manifest = verify_manifest(run)
    verify_manifest(release)
    verify_bindings(read_json(release / 'manifest.json')['protected'])
    if (review['status'] != 'passed' or review['fit_calls_during_validation'] != 0
            or review['run_manifest_sha256'] != sha256(run / 'manifest.json')
            or review['protocol_sha256'] != sha256(protocol) or review['freeze_sha256'] != sha256(freeze)):
        raise ValueError('Verified run binding mismatch')
    backup_dir.mkdir(parents=True, exist_ok=False)
    before = {}
    for name in DOCS:
        target = backup_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
        before[name] = sha256(ROOT / name)
    save(backup_dir / 'manifest.json', {'generated_at': utc_now(), 'original_document_sha256': before,
                                      'outputs': {name: sha256(backup_dir / name) for name in DOCS}})
    state = dict(ready)
    state.update(status='local_exploratory_training_independently_verified', generated_at=utc_now(),
                 supersedes=ready_path.relative_to(ROOT).as_posix(), state_path=state_path.relative_to(ROOT).as_posix(),
                 data_dir=release.relative_to(ROOT).as_posix(), audit_protocol_id='protocol-mic-06',
                 training_started=True, training_blocked=False, training_execution_status='completed',
                 result_verification_status='passed', evidence_observations=manifest['observations'],
                 new_candidates_released=1, models_saved=review['models_reloaded'], oof_rows=manifest['oof_rows'],
                 validation_path=review_path.relative_to(ROOT).as_posix(), run_directory=run.relative_to(ROOT).as_posix(),
                 classes={'positive': 6, 'negative': 11}, component_counts={'total': 7, 'positive': 4, 'negative': 6},
                 cross_fold_homology_edges=0, cross_fold_primary_studies=0, all_member_comparisons=136,
                 previous_verified_baseline='03_experiments/audits/mic_training_readiness_20261004_v22.json',
                 failed_attempt_manifest='03_experiments/runs/mic_goat_baseline_20261004_v1/manifest.json',
                 observations_are_table_mentions_not_independent_replicate_count=True,
                 formal_dual_task_status='blocked', formal_results_available=False, publication_ready=False)
    bound = [ready_path, protocol, freeze, release / 'manifest.json', review_path, run / 'manifest.json',
             backup_dir / 'manifest.json', ROOT / state['failed_attempt_manifest'],
             ROOT / '03_experiments/audits/mic_training_readiness_20261004_v24.json',
             Path(__file__), ROOT / '04_paper/research_status.json']
    state['inputs'].update({p.relative_to(ROOT).as_posix(): sha256(p) for p in bound})
    save(state_path, state)
    return state


def render(state):
    if state['status'] != 'local_exploratory_training_independently_verified' or state['training_blocked']:
        raise ValueError('Only a verified admitted state may be published')
    return '\n'.join([START, '## 当前研究状态（机器生成）', '',
        f"状态来源：`{state['state_path']}`。生成时间：{state['generated_at']}（UTC）。",
        f"数据版本：`{state['data_version']}`；数据目录：`{state['data_dir']}`；审查协议：`{state['audit_protocol_id']}`。",
        f"训练协议：`{state['training_protocol_id']}`；当前状态：`{state['status']}`。", '',
        '| 状态 | 当前结论 |', '|---|---|',
        '| 证据准入 | 17 分子、42 条测定表述；6 阳性、11 阴性；ChMAP-28 新增准入，两条 mini-ChBac 因正负标签冲突未释放 |',
        '| 全员及研究隔离 | 136 对、7 组件；固定三折 seed=42；跨折同源 0、跨折测量研究 0；各训练/验证含两类 |',
        '| 训练执行 | 固定 LR/RF/Dummy 三折完成，9 个模型、51 条 OOF；training_blocked=false |',
        '| 独立复核 | passed；禁止 fit，重载 9 模型并复算全部 OOF、指标及缩放器训练范围 |',
        '| 原双任务 | blocked；protocol-amd-02；正式运行 none |',
        '| 正式结果 / 投稿就绪 | false / false |', '',
        f"运行目录：`{state['run_directory']}`；复核：`{state['validation_path']}`。",
        '42 条为测定表格提及数，不代表 42 次独立实验。各分子只产生一个训练样本。',
        'protocol-mic-12 首次运行因指标函数绑定缺失中断，失败产物保留；protocol-mic-13 仅修复技术入口，科学定义与参数不变。',
        '原 16 分子已验证基线保留；以下旧正文为历史快照，不能覆盖本状态块或支撑当前证据放行。',
        '本轮是历史性能已知后的小样本探索，没有独立外部验证、临床泛化或投稿批准。', END])


def document_patch(state):
    sections = ['*** Begin Patch']
    for name in DOCS:
        before = (ROOT / name).read_text(encoding='utf-8')
        if before.count(START) != 1 or before.count(END) != 1:
            raise ValueError('Missing/duplicate current markers: ' + name)
        left, right = before.index(START), before.index(END) + len(END)
        after = before[:left] + render(state) + before[right:]
        diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm=''))
        if diff:
            sections.append('*** Update File: ' + name)
            sections.extend('@@' if line.startswith('@@') else line for line in diff[2:])
    return '\n'.join(sections + ['*** End Patch'])


def validate_documents(state):
    verify_bindings(state['inputs'])
    for name in DOCS:
        body = (ROOT / name).read_text(encoding='utf-8')
        if body.count(START) != 1 or body.count(END) != 1:
            raise ValueError('Missing/duplicate status block: ' + name)
        actual = body[body.index(START):body.index(END) + len(END)]
        if actual != render(state):
            raise ValueError('Document differs from machine status: ' + name)
    print('PASS: five exact machine-generated status blocks; state bindings unchanged')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['generate', 'patch', 'validate'])
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--backup', type=Path)
    args = parser.parse_args()
    if args.command == 'generate':
        if args.backup is None: parser.error('--backup is required for generation')
        print(json.dumps(generate(args.state.resolve(), args.backup.resolve()), ensure_ascii=False))
    elif args.command == 'patch': print(document_patch(read_json(args.state)))
    else: validate_documents(read_json(args.state))
