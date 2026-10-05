"""Review all goat-study single-agent MIC mentions before any fixed-fold split.

No model fitting. Each input/output is bound; every output directory is new.
Repeated mentions across tables are not claimed as independent experiments.
"""
import argparse
import csv
import hashlib
import itertools
import json
import math
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from feature_extractor import MOLECULAR_WEIGHTS

from mic_followup_release import aliases_for, audit_partition, graph_components
from public_data import bounds, measurement_label
from research_data import sequence_identity
from research_utils import ROOT, read_json, sha256, utc_now
from repair_alternative_primary_audit import verify_bindings

BASE = ROOT / '03_experiments/audits/mic_followup_release_20261004_v1'
STATE = ROOT / '03_experiments/audits/mic_training_readiness_20261004_v22.json'
SOURCE_ID = 'goat2018'
ALIASES = 'doi:10.3389/fmicb.2018.02983|pmid:30555455|pmcid:PMC6284057'
FORM = 'linear canonical sequence with free amino and carboxyl termini'
W = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def text(node):
    return ' '.join(' '.join(node.itertext()).split())


def write_json(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def table_rows(table):
    return [[text(cell) for cell in row] for row in table.findall('.//tr')]


def word_tables(path):
    with zipfile.ZipFile(path) as bundle:
        root = ET.fromstring(bundle.read('word/document.xml'))
    return [[[''.join(t.text or '' for t in cell.findall('.//w:t', W))
              for cell in row.findall('w:tc', W)] for row in table.findall('w:tr', W)]
            for table in root.findall('.//w:tbl', W)]


def extract(materials):
    acquisition = read_json(materials / 'acquisition.json')
    if not acquisition['supplement_acquired']:
        raise ValueError('Supplement not acquired')
    for relative, expected in acquisition['outputs'].items():
        if sha256(materials / relative) != expected:
            raise ValueError('Acquired source changed: ' + relative)
    primary, supplement = materials / 'raw/goat_antibacterial2018.xml', materials / 'raw/Data_Sheet_1.docx'
    root = ET.parse(primary).getroot()
    if '10.3389/fmicb.2018.02983' not in text(root.find('.//article-meta')):
        raise ValueError('Original article identity mismatch')
    tables = {t.get('id'): t for t in root.findall('.//table-wrap')}
    supplements = word_tables(supplement)
    identities = {row[0]: {'seq': row[1], 'calculated_m_plus_h': row[2], 'observed_m_plus_h': row[3]}
                  for row in supplements[0][2:5]}
    if len(identities) != 3 or any(not 10 <= len(m['seq']) <= 50 for m in identities.values()):
        raise ValueError('Incomplete original molecular identity')
    mentions = []

    def add(peptide, target, value, condition, table_id, row_index, col_index, source_path):
        if peptide not in identities or not target.startswith('E. coli'):
            return
        if bounds(value) is None:
            raise ValueError('Unsupported original assay cell: ' + value)
        mentions.append({'peptide': peptide, 'target': target.replace('E. coli', 'Escherichia coli', 1),
                         'raw_mic': value, 'raw_unit': 'µM', 'condition': condition,
                         'location': f'{table_id}; data row {row_index + 1}; column {col_index + 1}',
                         'source_file': source_path.relative_to(ROOT).as_posix()})

    peptides = list(identities)
    for i, cells in enumerate(table_rows(tables['T2'])):
        if len(cells) == 10 and cells[0].startswith('E. coli'):
            for j, peptide in enumerate(peptides):
                for salt in range(2):
                    col = 4 + 2 * j + salt
                    add(peptide, cells[0], cells[col], 'MHB; 0.9% NaCl' if salt else 'MHB; without added NaCl',
                        'Table 2', i, col, primary)
    # Only individual MIC A/B columns; mixture doses/FIC are never assays of a single peptide.
    for i, cells in enumerate(table_rows(tables['T3'])):
        if len(cells) == 9 and cells[0].startswith('E. coli'):
            for peptide, col in ((peptides[0], 1), (peptides[1], 4)):
                add(peptide, cells[0], cells[col], 'MHB; salt not specified in this table; standalone MIC column',
                    'Table 3', i, col, primary)
    for i, cells in enumerate(table_rows(tables['T4'])):
        if len(cells) == 4 and cells[0].startswith('E. coli'):
            for peptide, col in ((peptides[0], 2), (peptides[1], 3)):
                add(peptide, cells[0], cells[col], 'MHB; selection history in target; salt not specified in table',
                    'Table 4', i, col, primary)
    for i, cells in enumerate(table_rows(tables['T5'])):
        if len(cells) == 7 and cells[0].startswith('E. coli'):
            for j, peptide in enumerate(peptides):
                for salt in range(2):
                    col = 1 + 2 * j + salt
                    add(peptide, cells[0], cells[col], 'MHB; 0.9% NaCl' if salt else 'MHB; without added NaCl',
                        'Table 5', i, col, primary)
    for i, cells in enumerate(supplements[1]):
        if len(cells) == 4 and cells[0].startswith('E. coli'):
            add(peptides[0], cells[0], cells[1], 'MHB; salt not specified in supplementary table',
                'Table S2', i, 1, supplement)
    if len(mentions) != 45:
        raise ValueError(f'Original table coverage differs: {len(mentions)} mentions')
    return identities, mentions, root


def prepare(materials, output):
    materials, output = materials.resolve(), output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / '03_experiments/audits'):
        raise ValueError('Unused local output directory required')
    previous = read_json(STATE)
    protected = dict(previous['inputs'])
    protected[STATE.relative_to(ROOT).as_posix()] = sha256(STATE)
    protected.update({p.relative_to(ROOT).as_posix(): sha256(p)
                      for p in (ROOT / previous['run_directory']).rglob('*') if p.is_file()})
    verify_bindings(protected)
    identities, mentions, article = extract(materials)
    molecules = pd.read_csv(BASE / 'cohort/candidate_molecules.csv', keep_default_na=False)
    assays = pd.read_csv(BASE / 'cohort/candidate_observations.csv', keep_default_na=False)
    sources = pd.read_csv(BASE / 'evidence/source_review.csv', keep_default_na=False)
    approved = pd.read_csv(BASE / 'evidence/molecule_evidence_review.csv', keep_default_na=False)
    basis = ('Original Table S1 explicitly identifies all three assayed recombinant peptides; '
             'the primary expression/purification and results sections report mature peptides '
             'without significant post-translational modification, matched mass spectra and no amidation step. '
             'Free termini are inferred jointly from the reported molecular form and sequence/mass agreement, '
             'not from a database category. No independent human signoff claimed.')
    limitations = ('Different strains, added salt and selection histories remain explicit. '
                   'Table 3 salt is not independently stated. Repeated table mentions are not independent replicates. '
                   'Supplementary Table S1 lists monoisotopic [M+H]+, not neutral average molecular mass; '
                   'normalization uses the existing canonical sequence mass rule.')
    raw_rows = []
    for index, mention in enumerate(mentions):
        seq = identities[mention['peptide']]['seq']
        label = measurement_label({'concentration': mention['raw_mic'], 'unit': {'name': mention['raw_unit']}}, seq, 32, 128)
        raw_rows.append({**mention, 'sequence': seq, 'derived_label': label,
                         'eligible_binary_endpoint': label is not None, 'mention_index': index,
                         'primary_file_sha256': sha256(ROOT / mention['source_file'])})
    decisions = []
    approved_new = []
    for peptide, identity in identities.items():
        observed = [r for r in raw_rows if r['peptide'] == peptide]
        labels = {r['derived_label'] for r in observed if r['derived_label'] is not None}
        decision = ('blocked_opposite_measured_labels' if len(labels) > 1 else
                    'withheld_no_binary_endpoint' if not labels else 'passed_primary_evidence')
        sample_id = hashlib.sha256((FORM + '\0' + identity['seq']).encode()).hexdigest()[:24]
        decisions.append({'peptide': peptide, 'sample_id': sample_id, **identity,
                          'measurement_mentions': len(observed), 'binary_label_set': json.dumps(sorted(labels)),
                          'decision': decision, 'molecular_evidence': basis,
                          'condition_limitations': limitations, 'selection_basis': 'all_original_single_agent_ecoli_MIC_columns; before_split'})
        if decision == 'passed_primary_evidence':
            approved_new.append((sample_id, peptide, identity['seq'], observed, next(iter(labels))))
    primary = materials / 'raw/goat_antibacterial2018.xml'
    supplement = materials / 'raw/Data_Sheet_1.docx'
    if approved_new:
        source = {key: '' for key in sources.columns}
        source.update(source_id=SOURCE_ID, primary_file=primary.relative_to(ROOT).as_posix(), sha256=sha256(primary),
                      source_url='https://doi.org/10.3389/fmicb.2018.02983',
                      primary_locations='Tables 2-5; supplementary Tables S1-S2; expression and antimicrobial assay sections',
                      molecular_evidence=basis, method_evidence='Original single-agent E. coli MIC; no synergy-dose labels',
                      limitations_and_scope=limitations)
        sources = pd.concat([sources, pd.DataFrame([source])], ignore_index=True)
    for sample_id, peptide, seq, observed, label in approved_new:
        if seq in set(molecules.seq):
            raise ValueError('Duplicate molecule requires explicit aggregation')
        binary = [r for r in observed if r['derived_label'] is not None]
        record_ids = []
        for mention in binary:
            record_id = f'goat2018:mention:{mention["mention_index"]}'
            record_ids.append(record_id)
            assay = {key: '' for key in assays.columns}
            assay.update(sample_id=sample_id, record_id=record_id, source_dataset='original_primary_article',
                         assay_index=mention['mention_index'], target=mention['target'], medium='Mueller-Hinton broth',
                         method='original broth microdilution; visible turbidity endpoint', raw_mic=mention['raw_mic'],
                         raw_unit=mention['raw_unit'], eligible=True, derived_label=label,
                         reference_resolution='original_single_agent_MIC_column', assay_study_ids=ALIASES,
                         source_id=SOURCE_ID, primary_peptide_name=peptide, sequence=seq,
                         primary_file=mention['source_file'], primary_file_sha256=mention['primary_file_sha256'],
                         primary_locations=mention['location'], primary_method_conditions=mention['condition'],
                         condition_limitations=limitations, raw_value_unit_target_rechecked=True,
                         decision='passed_primary_evidence')
            # Use the existing neutral sequence mass normalization, never ion m/z.
            mass = sum(MOLECULAR_WEIGHTS[a] for a in seq) - 18.0152 * (len(seq) - 1)
            lo, hi = bounds(mention['raw_mic'])
            assay.update(normalized_low_ug_ml=lo * mass / 1000, normalized_high_ug_ml=hi * mass / 1000)
            assays = pd.concat([assays, pd.DataFrame([assay])], ignore_index=True)
        molecule = {key: '' for key in approved.columns}
        molecule.update(sample_id=sample_id, sequence=seq, source_id=SOURCE_ID, primary_peptide_name=peptide,
                        primary_file=supplement.relative_to(ROOT).as_posix(), primary_file_sha256=sha256(supplement),
                        primary_locations='Supplementary Table S1; visual render page 2; primary expression/results sections',
                        molecular_form=FORM, molecular_evidence=basis, condition_limitations=limitations,
                        derived_label=label, observations_rechecked=len(binary), decision='passed_primary_evidence',
                        human_reviewer_signoff='not_claimed')
        approved = pd.concat([approved, pd.DataFrame([molecule])], ignore_index=True)
        candidate = {key: '' for key in molecules.columns}
        candidate.update(sample_id=sample_id, seq=seq, amp=label, record_ids=json.dumps(record_ids),
                         source_datasets='original_primary_article', study_ids=ALIASES)
        molecules = pd.concat([molecules, pd.DataFrame([candidate])], ignore_index=True)
    aliases = aliases_for(molecules, assays, sources)
    pairs = [{'sample_id_a': a.sample_id, 'sample_id_b': b.sample_id,
              'identity': sequence_identity(a.seq, b.seq, identity_mode='alignment')}
             for a, b in itertools.combinations(molecules.itertuples(index=False), 2)]
    components = graph_components(molecules.sample_id.tolist(), pairs, aliases)
    molecules['component'] = molecules.sample_id.map(components)
    counts = {'total': len(set(components.values())),
              'positive': molecules.loc[molecules.amp.astype(int).eq(1), 'component'].nunique(),
              'negative': molecules.loc[molecules.amp.astype(int).eq(0), 'component'].nunique()}
    roles = []
    if min(counts.values()) >= 3:
        splitter = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)
        for fold, (train, valid) in enumerate(splitter.split(np.zeros((len(molecules), 1)),
                                          molecules.amp.astype(int), molecules.component)):
            for role, positions in (('train', train), ('validation', valid)):
                roles.extend({'sample_id': molecules.iloc[i].sample_id, 'fold': fold, 'role': role,
                              'amp': int(molecules.iloc[i].amp), 'component': int(molecules.iloc[i].component)} for i in positions)
        partition = audit_partition(molecules, assays, sources, pd.DataFrame(roles), pd.DataFrame(pairs))
    else:
        partition = {'status': 'blocked', 'blockers': ['At least three components of each class required'],
                     'model_fitting_performed': False}
    output.mkdir(parents=True, exist_ok=False)
    cohort, evidence = output / 'cohort', output / 'evidence'
    cohort.mkdir(); evidence.mkdir()
    pd.DataFrame(raw_rows).to_csv(output / 'all_original_mic_mentions.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(decisions).to_csv(output / 'candidate_decisions.csv', index=False, encoding='utf-8-sig')
    for filename, table in (('candidate_molecules.csv', molecules), ('candidate_observations.csv', assays),
                            ('all_member_similarity.csv', pd.DataFrame(pairs))):
        table.to_csv(cohort / filename, index=False, encoding='utf-8-sig')
    pd.DataFrame(roles, columns=['sample_id', 'fold', 'role', 'amp', 'component']).to_csv(cohort / 'fold_roles.csv', index=False)
    for filename, table in (('source_review.csv', sources), ('molecule_evidence_review.csv', approved),
                            ('assay_evidence_review.csv', assays)):
        table.to_csv(evidence / filename, index=False, encoding='utf-8-sig')
    write_json(output / 'partition_audit.json', partition)
    inputs = {p.relative_to(ROOT).as_posix(): sha256(p) for p in
              [Path(__file__), materials / 'acquisition.json', primary, supplement,
               materials / 'Data_Sheet_1.pdf', materials / 'supplement-review-2.png',
               BASE / 'manifest.json', STATE, ROOT / '02_code/mic_followup_release.py',
               ROOT / '02_code/public_data.py', ROOT / '02_code/research_data.py',
               ROOT / '02_code/validate_mic_acid_progress.py']}
    generated = utc_now()
    cohort_record = {'status': partition['status'], 'generated_at': generated, 'molecules': len(molecules),
                     'observations': len(assays), 'component_counts': {k: int(v) for k, v in counts.items()},
                     'fold_structure_gate_passed': partition['status'] == 'passed',
                     'validation': {'folds': 3, 'shuffle': True, 'seed': 42},
                     'candidate_selection_after_split': False, 'inputs': inputs,
                     'outputs': {p.name: sha256(p) for p in cohort.iterdir()}}
    write_json(cohort / 'manifest.json', cohort_record)
    write_json(evidence / 'manifest.json', {'status': 'passed_for_local_exploratory_training_protocol_review',
               'generated_at': generated, 'full_release_review_complete': True,
               'molecules_evidence_approved': len(molecules), 'observations_evidence_approved': len(assays),
               'cohort_manifest_sha256': sha256(cohort / 'manifest.json'), 'inputs': inputs,
               'records_released_for_training': 0, 'training_started': False,
               'independent_human_review_claimed': False,
               'outputs': {p.name: sha256(p) for p in evidence.iterdir()}})
    state = {'status': 'evidence_review_complete_partition_' + partition['status'], 'generated_at': generated,
             'supersedes': STATE.relative_to(ROOT).as_posix(), 'audit_protocol_id': 'protocol-mic-06',
             'previous_training_protocol_id': 'protocol-mic-11', 'new_training_protocol_id': None,
             'data_version': output.name, 'new_molecules_evidence_approved': len(approved_new),
             'molecules': len(molecules), 'observations': len(assays), 'component_counts': cohort_record['component_counts'],
             'training_blocked': True, 'training_started': False,
             'blockers': partition['blockers'] + ['New protocol and freeze required before new training'],
             'current_mic_baseline_status': previous['status'], 'formal_dual_task_status': 'blocked',
             'formal_results_available': False, 'publication_ready': False}
    write_json(output / 'review_state.json', state)
    report = (f'# 山羊肽证据与固定三折审计\n\n生成时间：{generated}\n\n'
              f'官方补充表 S1 已结构化及视觉核对；来源 DOI：10.3389/fmicb.2018.02983，CC BY 4.0。\n\n'
              f'审查全部 {len(raw_rows)} 条单药 E. coli MIC 表格提及，保留菌株、盐条件及选择历史。'
              'Table 3 仅取单药 MIC 列，组合浓度不产生标签。重复表述不被声称为独立实验重复。\n\n'
              f'新增证据合格分子：{len(approved_new)}；总分子：{len(molecules)}；测定表述：{len(assays)}。'
              '两条 mini-ChBac 记录因跨条件正负标签冲突阻止分子释放，不通过删去高 MIC 条件解决。\n\n'
              f'固定三折：{partition["status"]}；全员分子对：{len(pairs)}；组件：{counts}。'
              '同源和测量来源关系共同合并，seed=42，仅划分一次。\n\n'
              '现有 16 分子基线保持不变；本目录尚未冻结新训练协议，没有新模型拟合。原双任务继续 blocked。\n')
    with (output / 'report.md').open('x', encoding='utf-8') as stream:
        stream.write(report)
    verify_bindings(protected)
    verify_bindings(inputs)
    write_json(output / 'manifest.json', {'generated_at': generated, 'status': state['status'],
               'inputs': inputs, 'protected': protected,
               'outputs': {p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*') if p.is_file()}})
    print(json.dumps(state, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--materials', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.materials, args.output)
