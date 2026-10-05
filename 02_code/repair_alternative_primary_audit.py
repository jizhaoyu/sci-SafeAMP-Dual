"""Repair unverified Gemini transcriptions; never release evidence or fit models."""
import argparse
import csv
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from public_data import bounds, measurement_label
from research_data import sequence_identity
from research_utils import ROOT, read_json, sha256, utc_now
from validate_mic_acid_progress import independent_identity

BASE = ROOT / '03_experiments/audits/alternative_primary_search_20261004_v2'
STATE = ROOT / '03_experiments/audits/mic_training_readiness_20261004_v22.json'
PROTOCOL = ROOT / '03_experiments/protocols/protocol-mic-11.json'
DEV = ROOT / '03_experiments/prepared/amd02_evidence_clean_20261001/records.csv'
MIC = ROOT / '03_experiments/audits/mic_followup_release_20261004_v1/cohort/candidate_molecules.csv'


def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def content(node):
    return ' '.join(' '.join(node.itertext()).split())


def name(value):
    return re.sub(r'\s+', '', value)


def save_json(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def save_csv(path, records):
    if not records:
        raise ValueError('Empty audit table')
    with path.open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def derive_label(raw, mw, rule):
    """Preserve censoring; classify normalized, unrounded intervals."""
    interval = bounds(raw)
    if interval is None or not math.isfinite(mw) or mw <= 0:
        raise ValueError('Invalid original concentration or molecular mass')
    low, high = (v * mw / 1000 for v in interval)
    operator = re.match(r'^\s*([<>]=?)', raw)
    if operator:
        normalized = operator.group(1) + repr(float(re.sub(r'^[<>]=?\s*', '', raw)) * mw / 1000)
    elif low == high:
        normalized = repr(low)
    else:
        normalized = f'{low}-{high}'
    label = measurement_label({'concentration': normalized, 'unit': {'name': 'ug/ml'}}, '',
                              rule['positive_if_upper_bound_ug_ml_lte'],
                              rule['negative_if_lower_bound_ug_ml_gte'])
    return low, high if math.isfinite(high) else None, label


def primary_pin2():
    article = ET.parse(BASE / 'raw/pandinin2014.xml').getroot()
    tables = {t.get('id'): t for t in article.findall('.//table-wrap')}
    molecules = {}
    for row in tables['pone-0101742-t001'].findall('.//tr'):
        cells = [content(cell) for cell in row]
        if len(cells) == 9 and cells[0].startswith('Pin2'):
            molecules[name(cells[0])] = {'seq': cells[1], 'mw': float(cells[7]),
                                       'location': 'Table 1; theoretical molecular weight (Da)'}
    assays, current = [], None
    for index, row in enumerate(tables['pone-0101742-t003'].findall('.//tr')):
        cells = [content(cell) for cell in row]
        if len(cells) != 5 or cells[1] not in ('MHA', 'MHB'):
            continue
        if cells[0]:
            current = name(cells[0])
        if current not in molecules:
            raise ValueError('Unresolved original table molecule')
        value = re.match(r'^([<>]=?\s*)?\d+(?:\.\d+)?', cells[2])
        if value is None:
            raise ValueError('Unsupported original concentration')
        assays.append({'candidate_name': current, 'condition': cells[1],
                      'raw_mic': value.group(0).replace(' ', ''), 'raw_cell': cells[2],
                      'location': f'Table 3; XML row {index + 1}; E. coli column'})
    if len(molecules) != 5 or len(assays) != 10:
        raise ValueError('Incomplete original table coverage')
    return molecules, assays


def verify_bindings(bindings):
    for relative, digest in bindings.items():
        if sha256(ROOT / relative) != digest:
            raise ValueError('Changed bound artifact: ' + relative)


def validate(output):
    output = output.resolve()
    manifest = read_json(output / 'manifest.json')
    verify_bindings(manifest['inputs'])
    verify_bindings(manifest['protected'])
    for relative, digest in manifest['outputs'].items():
        if sha256(output / relative) != digest:
            raise ValueError('Changed audit output: ' + relative)
    actual = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}
    if actual != set(manifest['outputs']) | {'manifest.json'}:
        raise ValueError('Unexpected or missing output file')
    decisions, pairs = rows(output / 'molecule_decisions.csv'), rows(output / 'sequence_pairs.csv')
    if len(pairs) != len(decisions) * (len(rows(DEV)) + len(rows(MIC))):
        raise ValueError('Incomplete member comparison coverage')
    if len({(p['candidate_name'], p['reference_cohort'], p['reference_id']) for p in pairs}) != len(pairs):
        raise ValueError('Duplicate member comparisons')
    state = read_json(output / 'handoff_status.json')
    if state['new_molecules_admitted'] != 0 or state['new_training_executed']:
        raise ValueError('Repair cannot release evidence or train')
    originals, observations = primary_pin2()
    for decision in decisions:
        if decision['source_id'] == 'pandinin2014':
            original = originals[name(decision['candidate_name'])]
            if decision['seq'] != original['seq'] or float(decision['mw']) != original['mw']:
                raise ValueError('Original identity not reproduced')
    assays = rows(output / 'assay_decisions.csv')
    if len(assays) != len(observations):
        raise ValueError('Original measurement coverage mismatch')
    rule = read_json(PROTOCOL)['label_rule']
    for observed, stored in zip(observations, assays):
        if any(str(observed[key]) != stored[key] for key in observed):
            raise ValueError('Original measurement transcription mismatch')
        low, high, label = derive_label(observed['raw_mic'], originals[observed['candidate_name']]['mw'], rule)
        if (float(stored['lower_bound_ugml']) != low
                or (float(stored['upper_bound_ugml']) if stored['upper_bound_ugml'] else None) != high
                or stored['derived_label'] != (str(label) if label is not None else '')):
            raise ValueError('Measurement conversion or derived label mismatch')
    for pair in pairs:
        identity = independent_identity(pair['candidate_seq'], pair['reference_seq'])
        if (identity != float(pair['identity_alignment'])
                or (pair['conflict_ge_0_40'] == 'True') != (identity >= 0.40)):
            raise ValueError('Independent global alignment mismatch')
    print(json.dumps({'status': 'passed', 'comparison_rows': len(pairs),
                      'original_measurements_checked': len(assays),
                      'protected_bindings': len(manifest['protected']), 'model_fit_calls': 0}))


def repair(output):
    output = output.resolve()
    if not output.is_relative_to(ROOT / '03_experiments/audits') or output == BASE:
        raise ValueError('Output must be a new local audit directory')
    if output.exists():
        raise FileExistsError('Refusing to overwrite audit: ' + str(output))
    previous = read_json(STATE)
    protected = dict(previous['inputs'])
    protected[STATE.relative_to(ROOT).as_posix()] = sha256(STATE)
    protected.update({p.relative_to(ROOT).as_posix(): sha256(p)
                      for p in (ROOT / previous['run_directory']).rglob('*') if p.is_file()})
    verify_bindings(protected)
    inputs = [Path(__file__), DEV, MIC, PROTOCOL, BASE / 'molecule_decisions.csv',
              BASE / 'assay_decisions.csv', BASE / 'handoff_status.json',
              ROOT / '02_code/public_data.py', ROOT / '02_code/research_data.py',
              ROOT / '02_code/research_utils.py', ROOT / '02_code/validate_mic_acid_progress.py']
    inputs.extend(p for p in (BASE / 'raw').iterdir() if p.is_file())
    input_hashes = {p.relative_to(ROOT).as_posix(): sha256(p) for p in inputs}
    protocol = read_json(PROTOCOL)
    originals, observations = primary_pin2()
    decisions = rows(BASE / 'molecule_decisions.csv')
    changes, assay_rows = [], []
    for row in decisions:
        key = name(row['candidate_name'])
        if row['source_id'] == 'pandinin2014':
            original = originals[key]
            for field in ('seq', 'mw'):
                if str(row[field]) != str(original[field]):
                    changes.append({'candidate_name': row['candidate_name'], 'field': field,
                                    'old_value': row[field], 'corrected_value': original[field],
                                    'source_location': original['location']})
                row[field] = original[field]
            row['length'] = len(row['seq'])
            row['identity_review'] = 'sequence_and_mass_reproduced_from_original_table'
            row['decision'] = 'pending_complete_release_review'
        else:
            row['identity_review'] = 'pending_full_primary_identity_and_assay_review'
            row['decision'] = 'pending_evidence_review; homology_requires_merge_not_rejection'
        row['admitted'] = False
        row['prior_decision_is_not_approval'] = True
    for observation in observations:
        mw = originals[observation['candidate_name']]['mw']
        low, high, label = derive_label(observation['raw_mic'], mw, protocol['label_rule'])
        assay_rows.append({**observation, 'source_id': 'pandinin2014', 'raw_unit': 'uM',
                           'molecular_weight_da': mw, 'lower_bound_ugml': low,
                           'upper_bound_ugml': high, 'upper_unbounded': high is None,
                           'derived_label': label,
                           'label_outcome': 'unknown' if label is None else 'positive' if label == 1 else 'negative',
                           'review_scope': 'original_table_transcription; complete_release_review_pending',
                           'released_for_training': False})
    for decision in decisions:
        if decision['source_id'] == 'pandinin2014':
            labels = {a['derived_label'] for a in assay_rows
                      if a['candidate_name'] == name(decision['candidate_name']) and a['derived_label'] is not None}
            decision['decision'] = ('withheld_no_qualifying_binary_mic_observation' if not labels
                                    else 'withheld_conflicting_measurement_labels' if len(labels) > 1
                                    else 'pending_complete_release_review')
    pending = [dict(row, derived_label='', released_for_training=False,
                    decision='pending_primary_assay_review; previous_label_untrusted')
               for row in rows(BASE / 'assay_decisions.csv') if row['source_id'] != 'pandinin2014']
    pair_rows, summary = [], []
    for candidate in decisions:
        for cohort, members, id_key in (('formal_417', rows(DEV), 'record_id'), ('mic_16', rows(MIC), 'sample_id')):
            selected = []
            for member in members:
                identity = sequence_identity(candidate['seq'], member['seq'], identity_mode='alignment')
                pair = {'candidate_name': candidate['candidate_name'], 'candidate_seq': candidate['seq'],
                        'reference_cohort': cohort, 'reference_id': member[id_key], 'reference_seq': member['seq'],
                        'identity_alignment': identity, 'conflict_ge_0_40': identity >= protocol['similarity']['cutoff'],
                        'identity_review': candidate['identity_review']}
                selected.append(pair)
                pair_rows.append(pair)
            summary.append({'candidate_name': candidate['candidate_name'], 'reference_cohort': cohort,
                            'max_identity': max(p['identity_alignment'] for p in selected),
                            'violating_pairs': sum(p['conflict_ge_0_40'] for p in selected),
                            'interpretation': 'external_isolation_check' if cohort == 'formal_417'
                            else 'merge_required_when_conflict; not_an_admission_decision'})
    generated = utc_now()
    conflicts = sum(s['violating_pairs'] > 0 for s in summary if s['reference_cohort'] == 'formal_417')
    state = {'status': 'corrected_prescreen_evidence_review_pending', 'generated_at': generated,
             'supersedes_audit_status': (BASE / 'handoff_status.json').relative_to(ROOT).as_posix(),
             'current_machine_state': STATE.relative_to(ROOT).as_posix(),
             'current_mic_status': previous['status'], 'current_mic_training_blocked': previous['training_blocked'],
             'formal_dual_task_status': previous['formal_dual_task_status'],
             'training_protocol_id': protocol['protocol_id'], 'data_version': previous['data_version'],
             'new_molecules_admitted': 0, 'new_labels_released': 0, 'new_training_executed': False,
             'formal_results_available': False, 'publication_ready': False,
             'source_summary': {'candidate_input_sequences': len(decisions), 'pairwise_comparisons': len(pair_rows),
                                'formal_conflict_candidate_inputs': conflicts},
             'new_cohort_partition_gate': 'not_run; primary_evidence_review_incomplete',
             'limitations': ['Findings apply only to this batch; unverified identities are prescreen inputs.',
                             'Shared MIC components require merging plus source grouping and full fixed-fold audit.',
                             'No conclusion about exhaustion of public experimental data is supported.']}
    output.mkdir(parents=True, exist_ok=False)
    save_csv(output / 'molecule_decisions.csv', decisions)
    save_csv(output / 'assay_decisions.csv', assay_rows)
    save_csv(output / 'pending_assay_transcriptions.csv', pending)
    save_csv(output / 'sequence_pairs.csv', pair_rows)
    save_json(output / 'transcription_corrections.json', changes)
    save_json(output / 'candidate_identity_prescreen.json', {'generated_at': generated, 'summary': summary})
    save_json(output / 'handoff_status.json', state)
    report = (f'# Gemini 审计修复报告\n\n生成时间：{generated}\n\n'
              f'当前路径：`{output.relative_to(ROOT).as_posix()}`；历史 v2 保留为待纠错材料。\n\n'
              f'协议：`{protocol["protocol_id"]}`；现有数据：`{previous["data_version"]}`。\n\n'
              f'MIC：`{previous["status"]}`；双任务：`{previous["formal_dual_task_status"]}`。\n\n'
              f'完成 {len(pair_rows)} 对本批输入比较；{conflicts}/{len(decisions)} 个输入与正式集存在同源边。'
              '身份尚未复核的输入仅用于预筛，不能视为已确认实验分子；结论不覆盖全部历史候选或全网。\n\n'
              'Table 1 自动修正 Pin2[14] 分子量、Pin2[17] 序列与分子量。Table 3 两种培养条件分别保留。'
              '标签由原始区间、未舍入换算值和既有阈值推导，保留开放上界。\n\n'
              '已有组件同源不是 MIC 扩充的自动拒绝理由。其他候选保持待核实；'
              '后续须完成身份和测定复核，再合并同源及研究关系、审计固定三折，不预判放行。\n\n'
              '新准入 0、新训练 0；冻结数据、协议、模型和原机器状态保留。'
              '本轮修复不声称完整证据释放或正式实验放行。\n')
    with (output / 'report.md').open('x', encoding='utf-8') as stream:
        stream.write(report)
    verify_bindings(input_hashes)
    verify_bindings(protected)
    save_json(output / 'manifest.json', {'generated_at': generated,
              'inputs': input_hashes, 'protected': protected,
              'outputs': {p.relative_to(output).as_posix(): sha256(p) for p in output.iterdir() if p.is_file()}})
    validate(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['repair', 'validate'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    (repair if args.command == 'repair' else validate)(args.output)
