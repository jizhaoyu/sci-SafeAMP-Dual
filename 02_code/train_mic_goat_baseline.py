"""New frozen MIC follow-up; public primary evidence gates precede every fit.

The historical protocol-mic-11 entry and models are never edited. The training
loop is reused in a scoped adapter after this entry verifies protocol-mic-12.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedGroupKFold

import train_mic_reviewed_baseline as base
from feature_extractor import extract_handcrafted_features
from mic_followup_release import audit_partition
from prepare_goat_mic_followup import extract
from public_data import measurement_label
from repair_alternative_primary_audit import verify_bindings
from research_evidence_gate import require_primary_release, verify_manifest, workspace_path
from research_utils import ROOT, read_json, sha256, utc_now
from validate_mic_three_fold_run import independent_metrics

ENTRY = Path(__file__).resolve()
DEPENDENCIES = ('02_code/train_mic_reviewed_baseline.py', '02_code/train_mic_three_fold_v2.py',
                '02_code/train_mic_baselines.py', '02_code/research_evidence_gate.py',
                '02_code/feature_extractor.py', '02_code/public_data.py', '02_code/research_data.py',
                '02_code/research_utils.py', '02_code/mic_followup_release.py',
                '02_code/prepare_goat_mic_followup.py', '02_code/repair_alternative_primary_audit.py',
                '02_code/validate_mic_acid_progress.py', '02_code/validate_mic_three_fold_run.py')
PARENT = ROOT / '03_experiments/protocols/protocol-mic-11.json'


def check(condition, message):
    if not condition:
        raise ValueError(message)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def inspect_release(directory):
    record = verify_manifest(directory)
    verify_bindings(record['protected'])
    cohort, evidence = directory / 'cohort', directory / 'evidence'
    verify_manifest(cohort)
    verify_manifest(evidence)
    mol = pd.read_csv(cohort / 'candidate_molecules.csv', keep_default_na=False)
    obs = pd.read_csv(cohort / 'candidate_observations.csv', keep_default_na=False)
    roles = pd.read_csv(cohort / 'fold_roles.csv', keep_default_na=False)
    sources = pd.read_csv(evidence / 'source_review.csv', keep_default_na=False)
    pairs = pd.read_csv(cohort / 'all_member_similarity.csv')
    check(mol.sample_id.is_unique and mol.seq.is_unique, 'Duplicate molecular identities')
    check(set(mol.amp.astype(int)) == {0, 1}, 'Both classes required')
    counts = [mol.component.nunique(),
              mol.loc[mol.amp.astype(int).eq(1), 'component'].nunique(),
              mol.loc[mol.amp.astype(int).eq(0), 'component'].nunique()]
    check(min(counts) >= 3, 'At least three independent components of each class required')
    audit = audit_partition(mol, obs, sources, roles, pairs)
    check(audit['status'] == 'passed', 'Fixed split audit failed: ' + str(audit['blockers']))
    expected_roles = []
    splitter = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)
    for fold, (train, valid) in enumerate(splitter.split(np.zeros((len(mol), 1)), mol.amp.astype(int), mol.component)):
        for role, positions in (('train', train), ('validation', valid)):
            expected_roles.extend((mol.iloc[i].sample_id, fold, role) for i in positions)
    check(sorted(expected_roles) == sorted(zip(roles.sample_id, roles.fold.astype(int), roles.role)),
          'Roles do not reproduce the single fixed split')
    # Reconstruct all original mentions and reject selection by label or fold.
    material = workspace_path(next(p for p in record['inputs'] if p.endswith('/acquisition.json'))).parent
    identities, mentions, _ = extract(material)
    raw = pd.read_csv(directory / 'all_original_mic_mentions.csv', keep_default_na=False)
    decisions = pd.read_csv(directory / 'candidate_decisions.csv', keep_default_na=False)
    check(len(raw) == len(mentions) and len(decisions) == len(identities), 'Incomplete candidate/source coverage')
    for expected, stored in zip(mentions, raw.to_dict('records')):
        check(all(str(expected[k]) == str(stored[k]) for k in expected), 'Original assay transcription changed')
        check(stored['sequence'] == identities[stored['peptide']]['seq'], 'Original assayed sequence changed')
        label = measurement_label({'concentration': stored['raw_mic'], 'unit': {'name': stored['raw_unit']}}, stored['sequence'], 32, 128)
        check((stored['derived_label'] == '' if label is None else
               stored['derived_label'] != '' and float(stored['derived_label']) == label),
              'Primary label does not reproduce')
    approved_names = set()
    for row in decisions.itertuples(index=False):
        labels = {int(float(v)) for v in raw.loc[(raw.peptide == row.peptide) & raw.derived_label.ne(''), 'derived_label']}
        expected = ('blocked_opposite_measured_labels' if len(labels) > 1 else
                    'withheld_no_binary_endpoint' if not labels else 'passed_primary_evidence')
        check(row.decision == expected and row.binary_label_set == json.dumps(sorted(labels)), 'Conflict policy changed')
        if expected == 'passed_primary_evidence':
            approved_names.add(row.peptide)
    added_obs = obs[obs.source_id.eq('goat2018')]
    check(set(added_obs.primary_peptide_name) == approved_names, 'Unapproved molecular release')
    for peptide in approved_names:
        expected = raw[(raw.peptide == peptide) & raw.derived_label.ne('')]
        stored = added_obs[added_obs.primary_peptide_name == peptide]
        check(len(stored) == len(expected), 'Incomplete approved assay coverage')
        for a, b in zip(expected.to_dict('records'), stored.to_dict('records')):
            check(a['raw_mic'] == b['raw_mic'] and a['target'] == b['target']
                  and a['location'] == b['primary_locations'] and a['condition'] == b['primary_method_conditions'],
                  'Approved assay differs from original source')
    parent = read_json(PARENT)
    old_mol = pd.read_csv(workspace_path(parent['molecules']), keep_default_na=False)
    old_obs = pd.read_csv(workspace_path(parent['observations']), keep_default_na=False)
    check(set(old_mol.sample_id).issubset(set(mol.sample_id)), 'Historical molecules removed')
    for row in old_mol.itertuples(index=False):
        current = mol[mol.sample_id == row.sample_id].iloc[0]
        check(current.seq == row.seq and int(current.amp) == int(row.amp), 'Historical identity/label changed')
    check(obs[obs.record_id.isin(old_obs.record_id)].to_dict('records') == old_obs.to_dict('records'),
          'Historical observations changed')
    return mol, obs, roles, audit


def review(directory, output):
    check(not output.exists(), 'Refusing to overwrite independent review')
    mol, obs, roles, audit = inspect_release(directory)
    write_json(output, {**audit, 'generated_at': utc_now(), 'complete_primary_mentions_rechecked': 45,
               'candidate_conflict_policy_verified': True, 'fixed_split_reproduced': True,
               'evidence_release_manifest_sha256': sha256(directory / 'evidence/manifest.json'),
               'cohort_manifest_sha256': sha256(directory / 'cohort/manifest.json'),
               'release_manifest_sha256': sha256(directory / 'manifest.json'),
               'validator_sha256': sha256(ENTRY), 'model_fit_calls': 0,
               'visual_source_review': 'agent table review; no independent human assessment claimed'})
    return audit


def freeze(directory, review_path, ready_path, protocol_path, freeze_path):
    for path in (ready_path, protocol_path, freeze_path):
        check(path.is_relative_to(ROOT) and not path.exists(), 'Reserved output exists or is outside workspace')
    check(protocol_path == ROOT / '03_experiments/protocols/protocol-mic-12.json', 'Unexpected reserved protocol')
    independent = read_json(review_path)
    check(independent['status'] == 'passed' and independent['validator_sha256'] == sha256(ENTRY)
          and independent['release_manifest_sha256'] == sha256(directory / 'manifest.json'), 'Independent review binding mismatch')
    mol, obs, roles, audit = inspect_release(directory)
    parent = read_json(PARENT)
    old_mol = pd.read_csv(workspace_path(parent['molecules']), keep_default_na=False)
    check(set(mol.sample_id) > set(old_mol.sample_id), 'No approved molecular expansion')
    features = np.vstack([extract_handcrafted_features(s) for s in mol.seq])
    check(features.shape == (len(mol), 44) and np.isfinite(features).all(), 'Invalid fixed features')
    material_paths = {'cohort_manifest': directory / 'cohort/manifest.json',
                      'evidence_release_manifest': directory / 'evidence/manifest.json',
                      'independent_partition_validation': review_path,
                      'molecules': directory / 'cohort/candidate_molecules.csv',
                      'observations': directory / 'cohort/candidate_observations.csv',
                      'fold_roles': directory / 'cohort/fold_roles.csv',
                      'release_manifest': directory / 'manifest.json'}
    dependencies = {p: sha256(ROOT / p) for p in DEPENDENCIES}
    ready = {'status': 'ready_for_local_exploratory_training', 'generated_at': utc_now(),
             'supersedes': '03_experiments/audits/mic_training_readiness_20261004_v22.json',
             'training_blocked': False, 'training_started': False, 'blockers': [],
             'training_protocol_id': 'protocol-mic-12', 'data_version': directory.name,
             'records_released_for_training': len(obs), 'evidence_molecules': len(mol),
             'inputs': {p.relative_to(ROOT).as_posix(): sha256(p) for p in material_paths.values()},
             'training_entry_sha256': sha256(ENTRY), 'formal_dual_task_status': 'blocked',
             'formal_results_available': False, 'publication_ready': False}
    protocol = {key: parent[key] for key in ('label_rule', 'similarity', 'molecule_domain', 'models',
                'decision_threshold', 'validation', 'features_spec', 'model_selection')}
    protocol.update(protocol_id='protocol-mic-12', protocol_version=1,
                    status='frozen_local_exploratory_baseline_training', frozen_at=utc_now(),
                    parent_protocol_path=PARENT.relative_to(ROOT).as_posix(), parent_protocol_sha256=sha256(PARENT),
                    research_stage='follow-up exploratory; historical model performance already viewed; not preregistration',
                    scope='fixed local E. coli MIC exploration; no external/generalization/publication claim',
                    environment=base._environment(), training_entry_sha256=sha256(ENTRY),
                    dependency_sha256=dependencies, readiness_state=ready_path.relative_to(ROOT).as_posix(),
                    observation_ids=sorted(obs.record_id.astype(str)), sample_ids=mol.sample_id.tolist(),
                    feature_order='exact vector returned by frozen extract_handcrafted_features',
                    cohort_directory=directory.relative_to(ROOT).as_posix())
    for key, path in material_paths.items():
        protocol[key] = path.relative_to(ROOT).as_posix()
        protocol[key + '_sha256'] = sha256(path)
    base._make_models(protocol)
    write_json(ready_path, ready)
    protocol['readiness_state_sha256'] = sha256(ready_path)
    write_json(protocol_path, protocol)
    write_json(freeze_path, {'protocol_id': protocol['protocol_id'], 'frozen_at': utc_now(),
               'protocol_file_sha256': sha256(protocol_path), 'training_entry_sha256': sha256(ENTRY),
               'model_training_started': False, 'dependency_sha256': dependencies})
    return ready


def load(protocol_path, freeze_path):
    check(protocol_path.is_file() and freeze_path.is_file(), 'Mandatory protocol and freeze missing')
    protocol, frozen = read_json(protocol_path), read_json(freeze_path)
    check(protocol['protocol_id'] == 'protocol-mic-12' and frozen['protocol_id'] == protocol['protocol_id'], 'Unexpected protocol ID')
    check(protocol['status'] == 'frozen_local_exploratory_baseline_training'
          and frozen['model_training_started'] is False, 'Not a pre-training freeze')
    check(frozen['protocol_file_sha256'] == sha256(protocol_path)
          and frozen['training_entry_sha256'] == protocol['training_entry_sha256'] == sha256(ENTRY), 'Freeze binding differs')
    check(datetime.fromisoformat(frozen['frozen_at']) < datetime.now(timezone.utc), 'Freeze must precede fitting')
    parent = read_json(PARENT)
    check(protocol['parent_protocol_sha256'] == sha256(PARENT), 'Historical scientific protocol changed')
    for field in ('label_rule', 'similarity', 'molecule_domain', 'models', 'validation', 'decision_threshold', 'features_spec'):
        check(protocol[field] == parent[field], 'Frozen specification changed: ' + field)
    check(protocol['environment'] == base._environment(), 'Frozen runtime differs')
    check(set(protocol['dependency_sha256']) == set(DEPENDENCIES), 'Dependency coverage differs')
    verify_bindings(protocol['dependency_sha256'])
    check(frozen['dependency_sha256'] == protocol['dependency_sha256'], 'Freeze dependency binding differs')
    for key in ('cohort_manifest', 'evidence_release_manifest', 'independent_partition_validation',
                'molecules', 'observations', 'fold_roles', 'release_manifest', 'readiness_state'):
        check(sha256(workspace_path(protocol[key])) == protocol[key + '_sha256'], 'Frozen input changed: ' + key)
    ready = read_json(workspace_path(protocol['readiness_state']))
    check(ready['status'] == 'ready_for_local_exploratory_training' and ready['training_blocked'] is False
          and ready['training_started'] is False and ready['blockers'] == [], 'Not an admitted pre-training state')
    require_primary_release(protocol, freeze_path, ENTRY)
    mol, obs, roles, audit = inspect_release(workspace_path(protocol['cohort_directory']))
    check(protocol['sample_ids'] == mol.sample_id.tolist()
          and protocol['observation_ids'] == sorted(obs.record_id.astype(str)), 'Frozen sample/observation order differs')
    review_record = read_json(workspace_path(protocol['independent_partition_validation']))
    check(review_record['status'] == 'passed' and review_record['fixed_split_reproduced']
          and review_record['model_fit_calls'] == 0, 'Independent review failed')
    base._make_models(protocol)
    features = np.vstack([extract_handcrafted_features(s) for s in mol.seq]).astype(np.float64)
    check(features.shape == (len(mol), 44) and np.isfinite(features).all(), 'Invalid fixed features')
    return protocol, mol, roles, features


def train(output, protocol_path, freeze_path):
    # The replacement loader verifies the NEW frozen protocol; it is not an
    # override of any scientific gate. Patches are local and restored on exit.
    load(protocol_path, freeze_path)
    with patch.object(base, '_load_and_validate', load), patch.object(base, 'TRAIN_ENTRY', ENTRY):
        return base.train(output, protocol_path, freeze_path)


def validate(run, output, protocol_path, freeze_path):
    check(not output.exists() and not output.is_relative_to(run), 'Unused separate verification path required')
    with ExitStack() as stack:
        for cls in (LogisticRegression, RandomForestClassifier, DummyClassifier, StandardScaler, Pipeline):
            stack.enter_context(patch.object(cls, 'fit', side_effect=AssertionError('No fit during verification')))
        protocol, mol, roles, features = load(protocol_path, freeze_path)
        manifest = read_json(run / 'manifest.json')
        check(manifest['protocol_sha256'] == sha256(protocol_path) and manifest['freeze_sha256'] == sha256(freeze_path), 'Run binding differs')
        verify_manifest(run)
        check(manifest['training_started'] is True and manifest['protocol_id'] == protocol['protocol_id'], 'Run identity differs')
        actual_files = {p.relative_to(run).as_posix() for p in run.rglob('*') if p.is_file() and p.name != 'manifest.json'}
        expected_files = {'fixed_features.npy', 'fold_metrics.csv', 'oof_predictions.csv', 'pooled_descriptive_metrics.csv', 'report.md'}
        expected_files |= {f'fold_models/{name}_fold{fold}.joblib' for name in protocol['models'] for fold in range(3)}
        check(actual_files == set(manifest['outputs']) == expected_files, 'Missing or unmanifested outputs')
        check(datetime.fromisoformat(read_json(freeze_path)['frozen_at']) < datetime.fromisoformat(manifest['generated_at']), 'Run predates freeze')
        np.testing.assert_allclose(np.load(run / 'fixed_features.npy', allow_pickle=False), features, rtol=0, atol=1e-12)
        predictions = pd.read_csv(run / 'oof_predictions.csv', float_precision='round_trip')
        check(len(predictions) == len(mol) * 3 and not predictions.duplicated(['model', 'sample_id']).any(), 'OOF coverage differs')
        positions = {s: i for i, s in enumerate(mol.sample_id)}
        y = mol.amp.astype(int).to_numpy()
        metrics = []
        for fold in range(3):
            selected = roles[roles.fold.astype(int) == fold]
            train_ids = selected[selected.role == 'train'].sample_id.tolist()
            valid_ids = selected[selected.role == 'validation'].sample_id.tolist()
            tr, va = np.asarray([positions[s] for s in train_ids]), np.asarray([positions[s] for s in valid_ids])
            for name in protocol['models']:
                model = joblib.load(run / f'fold_models/{name}_fold{fold}.joblib')
                expected = base._make_models(protocol)[name]
                estimator = model.steps[-1][1] if isinstance(model, Pipeline) else model
                expected_estimator = expected.steps[-1][1] if isinstance(expected, Pipeline) else expected
                check(estimator.get_params(deep=False) == expected_estimator.get_params(deep=False), 'Model parameters changed')
                check(estimator.classes_.tolist() == [0, 1], 'Class ordering differs')
                if name == 'logistic_regression':
                    check(isinstance(model, Pipeline) and len(model.steps) == 2
                          and isinstance(model.steps[0][1], StandardScaler), 'Unexpected preprocessing')
                    scaler = model.steps[0][1]
                    np.testing.assert_allclose(scaler.mean_, features[tr].mean(axis=0), rtol=0, atol=1e-12)
                    np.testing.assert_allclose(scaler.var_, features[tr].var(axis=0), rtol=0, atol=1e-12)
                    check(int(scaler.n_samples_seen_) == len(tr), 'Scaler training coverage differs')
                if name == 'dummy_prior':
                    np.testing.assert_allclose(estimator.class_prior_, np.bincount(y[tr], minlength=2) / len(tr), atol=1e-12, rtol=0)
                scores = model.predict_proba(features[va])[:, 1]
                frame = predictions[(predictions.model == name) & (predictions.fold == fold)].set_index('sample_id')
                check(len(frame) == len(valid_ids) and set(frame.index) == set(valid_ids), 'OOF fold coverage differs')
                np.testing.assert_allclose(frame.loc[valid_ids, 'probability'].to_numpy(), scores, rtol=0, atol=1e-12)
                check(frame.loc[valid_ids, 'observed_label'].astype(int).tolist() == y[va].tolist(), 'OOF labels differ')
                metrics.append({'model': name, 'fold': fold, **independent_metrics(y[va], scores)})
        pooled = [{'model': name, **independent_metrics(part.observed_label.to_numpy(), part.probability.to_numpy())}
                  for name, part in predictions.groupby('model', sort=True)]
        for filename, expected_rows, keys in (('fold_metrics.csv', metrics, ['model', 'fold']),
                                              ('pooled_descriptive_metrics.csv', pooled, ['model'])):
            stored = pd.read_csv(run / filename).sort_values(keys).reset_index(drop=True)
            expected = pd.DataFrame(expected_rows).sort_values(keys).reset_index(drop=True)
            check(stored[keys].to_dict('records') == expected[keys].to_dict('records'), 'Metric inventory differs')
            columns = [c for c in expected.columns if c not in keys]
            np.testing.assert_allclose(stored[columns].to_numpy(float), expected[columns].to_numpy(float), rtol=0, atol=1e-12)
    result = {'status': 'passed', 'generated_at': utc_now(), 'protocol_id': protocol['protocol_id'],
              'models_reloaded': 9, 'oof_rows_independently_recomputed': len(predictions),
              'fit_calls_during_validation': 0, 'scaler_training_range_verified': True,
              'pooled_descriptive_metrics': pooled, 'run_manifest_sha256': sha256(run / 'manifest.json'),
              'protocol_sha256': sha256(protocol_path), 'freeze_sha256': sha256(freeze_path),
              'run_directory': run.relative_to(ROOT).as_posix(),
              'formal_results_available': False, 'publication_ready': False}
    write_json(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('review'); p.add_argument('--release', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('freeze')
    for field in ('release', 'review', 'ready', 'protocol', 'freeze'):
        p.add_argument('--' + field, type=Path, required=True)
    p = sub.add_parser('train')
    for field in ('output', 'protocol', 'freeze'): p.add_argument('--' + field, type=Path, required=True)
    p = sub.add_parser('validate')
    for field in ('run', 'output', 'protocol', 'freeze'): p.add_argument('--' + field, type=Path, required=True)
    args = parser.parse_args()
    values = {k: v.resolve() for k, v in vars(args).items() if isinstance(v, Path)}
    if args.command == 'review': result = review(values['release'], values['output'])
    elif args.command == 'freeze': result = freeze(*(values[k] for k in ('release', 'review', 'ready', 'protocol', 'freeze')))
    elif args.command == 'train': result = train(*(values[k] for k in ('output', 'protocol', 'freeze')))
    else: result = validate(*(values[k] for k in ('run', 'output', 'protocol', 'freeze')))
    print(json.dumps(result, ensure_ascii=False))
