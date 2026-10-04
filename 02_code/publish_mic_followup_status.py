"""Publish and check exact current documents for the original-figure follow-up."""
import difflib
import re
from pathlib import Path

from publish_mic_repair_status import DOCS, START, END
from research_utils import ROOT, read_json, sha256


def current_state_path():
    body=(ROOT/DOCS[0]).read_text(encoding='utf-8')
    block=body[body.index(START):body.index(END)]
    match=re.search(r'状态来源：`([^`]+)`',block)
    if not match: raise ValueError('Current document lacks a machine state reference')
    return ROOT/match.group(1)


def render(state):
    if state['status']=='mic_expansion_blocked_existing_baseline_preserved':
        from mic_reviewed_release import render_current_status
        return render_current_status(state)
    if state['status'] not in {'ready_for_local_exploratory_training','local_exploratory_training_independently_verified'}:
        raise ValueError('Unexpected follow-up state')
    verified=state['status']=='local_exploratory_training_independently_verified'
    if verified != state['training_started'] or state['training_blocked'] or state['formal_results_available'] or state['publication_ready']:
        raise ValueError('Machine state semantic conflict')
    if state['evidence_molecules']!=16 or state['evidence_observations']!=23 or state['new_candidates_released']!=1:
        raise ValueError('Current evidence inventory differs')
    return '\n'.join([START,'## 当前研究状态（机器生成）','',
        f"状态来源：`{state['state_path']}`。生成时间：{state['generated_at']}（UTC）。",
        f"数据版本：`{state['data_version']}`；数据目录：`{state['data_dir']}`；审查协议：`protocol-mic-08`。",
        f"训练协议：`{state['training_protocol_id']}`；当前状态：`{state['status']}`。",'',
        '| 状态 | 当前结论 |','|---|---|',
        '| 证据准入 | 16 分子、23 观察；BMAP-27B 原图 CREC6 单株测定准入；Piscidin 1 继续暂缓 |',
        '| 全员及研究隔离 | 120 对；固定三折 seed=42；跨折同源 0、跨折主要研究 0；各训练/验证含两类 |',
        f"| 训练执行 | {'固定 LR/RF/Dummy 三折完成，9 个模型、48 条 OOF' if verified else '未开始，待新协议冻结'} |",
        f"| 独立复核 | {'passed；禁止 fit，重载 9 模型并复算全部 OOF 与指标' if verified else '尚未执行'} |",
        '| 原双任务 | blocked；protocol-amd-02；正式运行 none |',
        '| 正式结果 / 投稿就绪 | false / false |','',
        '旧 15 分子基线保留。旧 Gemini 17 分子扩充队列的证据准入声明已撤销，历史计算产物不能替代当前原始证据。',
        '本轮是历史性能已知后的小样本探索；没有独立外部验证或临床泛化结论。',END])


def validate_documents(state):
    expected=render(state)
    for name in DOCS:
        body=(ROOT/name).read_text(encoding='utf-8')
        if body.count(START)!=1 or body.count(END)!=1: raise ValueError('Missing/duplicate current markers: '+name)
        block=body[body.index(START):body.index(END)+len(END)]
        if block!=expected: raise ValueError('Current document differs from machine state: '+name)
    for name,digest in state['inputs'].items():
        if sha256(ROOT/name)!=digest: raise ValueError('Current state input changed: '+name)


def document_patch(state):
    sections=['*** Begin Patch'];block=render(state)
    for name in DOCS:
        before=(ROOT/name).read_text(encoding='utf-8')
        if before.count(START)!=1 or before.count(END)!=1: raise ValueError('Invalid current markers')
        left,right=before.index(START),before.index(END)+len(END)
        after=before[:left]+block+before[right:]
        diff=list(difflib.unified_diff(before.splitlines(),after.splitlines(),lineterm=''))
        if diff:
            sections.append('*** Update File: '+name)
            sections.extend('@@' if line.startswith('@@') else line for line in diff[2:])
    return '\n'.join(sections+['*** End Patch'])
