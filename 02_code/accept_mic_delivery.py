"""Accept a MIC engineering delivery against the unchanged, verified v26 state.

This workspace acceptance is distinct from the portable, offline verifier. It
does not fit models, update scientific readiness, or establish a new experiment.
Future readiness versions require an explicit adapter and a new state anchor.
"""
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path, PurePosixPath
import sys

import numpy as np
import pandas as pd

from mic_delivery_runtime import DeliveryRuntime
from publish_mic_goat_status import DOCS, validate_documents
from research_utils import ROOT, read_json, sha256, utc_now

STATE_RELATIVE = '03_experiments/audits/mic_training_readiness_20261004_v26.json'
STATE_SHA256 = '404e9d90166564ec9c7543022853ae694dabc9022d913fa5d8e10f3b842a2da1'
PROTOCOL_RELATIVE = '03_experiments/protocols/protocol-mic-13.json'
FREEZE_RELATIVE = '03_experiments/audits/protocol_mic_13_freeze_20261004_v1.json'
TRAINING_ENTRY = '02_code/train_mic_goat_baseline_v2.py'
RUNTIME_SOURCE = '02_code/mic_delivery_runtime.py'
ATOL = 1e-12


def check(condition, message):
    if not condition:
        raise ValueError(message)


def relative_file(directory, name):
    check(isinstance(name, str) and name and '\\' not in name,
          'Invalid relative artifact path')
    relative = PurePosixPath(name)
    check(not relative.is_absolute() and ':' not in name
          and all(part not in ('', '.', '..') for part in name.split('/')),
          'Invalid relative artifact path: ' + name)
    result = (directory / name).resolve()
    check(result.is_relative_to(directory.resolve()) and result.is_file(),
          'Artifact escapes directory or is missing: ' + name)
    return result


def verify_bindings(bindings, directory, protected):
    check(isinstance(bindings, dict) and bool(bindings), 'Missing immutable bindings')
    for name, expected in bindings.items():
        path = relative_file(directory, name)
        check(sha256(path) == expected, 'Immutable binding changed: ' + name)
        if path in protected:
            check(protected[path] == expected, 'Conflicting immutable binding: ' + name)
        protected[path] = expected


def verify_inventory(directory, protected):
    manifest = read_json(directory / 'manifest.json')
    verify_bindings(manifest['outputs'], directory, protected)
    for key in ('inputs', 'protected'):
        if manifest.get(key):
            verify_bindings(manifest[key], ROOT, protected)
    return manifest


def verify_certificate(certificate, run_manifest, protocol_sha, freeze_sha):
    check(certificate.get('status') == 'passed'
          and certificate.get('protocol_id') == 'protocol-mic-13'
          and certificate.get('models_reloaded') == 9
          and certificate.get('oof_rows_independently_recomputed') == 51
          and certificate.get('fit_calls_during_validation') == 0
          and certificate.get('scaler_training_range_verified') is True,
          'Independent run validation certificate is incomplete')
    check(certificate.get('run_manifest_sha256') == sha256(run_manifest)
          and certificate.get('protocol_sha256') == protocol_sha
          and certificate.get('freeze_sha256') == freeze_sha,
          'Independent run validation certificate binding differs')
    check(certificate.get('formal_results_available') is False
          and certificate.get('publication_ready') is False,
          'Independent certificate changes scientific authorization')


def verify_workspace(state_path):
    state_path = state_path.resolve()
    check(sha256(state_path) == STATE_SHA256, 'Only the anchored v26 state is supported')
    state = read_json(state_path)
    expected = {
        'state_path': STATE_RELATIVE, 'training_protocol_id': 'protocol-mic-13',
        'status': 'local_exploratory_training_independently_verified',
        'training_blocked': False, 'training_started': True,
        'training_execution_status': 'completed', 'result_verification_status': 'passed',
        'evidence_molecules': 17, 'evidence_observations': 42,
        'records_released_for_training': 42, 'models_saved': 9, 'oof_rows': 51,
        'formal_dual_task_status': 'blocked', 'formal_results_available': False,
        'publication_ready': False,
    }
    check(all(state.get(key) == value and type(state.get(key)) is type(value)
              for key, value in expected.items()), 'v26 scientific state semantics differ')
    protected = {state_path: STATE_SHA256}
    verify_bindings(state['inputs'], ROOT, protected)
    protocol_path, freeze_path = ROOT / PROTOCOL_RELATIVE, ROOT / FREEZE_RELATIVE
    protocol, frozen = read_json(protocol_path), read_json(freeze_path)
    protocol_sha, freeze_sha = sha256(protocol_path), sha256(freeze_path)
    check(state['inputs'].get(PROTOCOL_RELATIVE) == protocol_sha
          and state['inputs'].get(FREEZE_RELATIVE) == freeze_sha
          and protocol['protocol_id'] == frozen['protocol_id'] == 'protocol-mic-13'
          and frozen['protocol_file_sha256'] == protocol_sha
          and frozen['model_training_started'] is False,
          'v26 protocol/freeze binding differs')
    check(protocol['training_entry_sha256'] == frozen['training_entry_sha256']
          == state['training_entry_sha256'] == sha256(ROOT / TRAINING_ENTRY),
          'Frozen training entry changed')
    protected[(ROOT / TRAINING_ENTRY).resolve()] = state['training_entry_sha256']
    check(protocol['dependency_sha256'] == frozen['dependency_sha256'],
          'Freeze dependency inventory differs')
    verify_bindings(protocol['dependency_sha256'], ROOT, protected)
    verify_bindings({protocol['parent_protocol_path']: protocol['parent_protocol_sha256']}, ROOT, protected)
    for key in ('cohort_manifest', 'evidence_release_manifest', 'independent_partition_validation',
                'molecules', 'observations', 'fold_roles', 'release_manifest', 'readiness_state'):
        verify_bindings({protocol[key]: protocol[key + '_sha256']}, ROOT, protected)
    release = relative_file(ROOT, protocol['release_manifest']).parent
    for directory in (release, release / 'cohort', release / 'evidence'):
        verify_inventory(directory, protected)
    original_run = (ROOT / state['run_directory']).resolve()
    run_manifest = verify_inventory(original_run, protected)
    check(run_manifest['protocol_sha256'] == protocol_sha
          and run_manifest['freeze_sha256'] == freeze_sha, 'Original run scientific binding differs')
    certificate = read_json(relative_file(ROOT, state['validation_path']))
    verify_certificate(certificate, original_run / 'manifest.json', protocol_sha, freeze_sha)
    check(certificate['run_directory'] == state['run_directory'], 'Original validation run path differs')
    formal = read_json(ROOT / '04_paper/research_status.json')
    check(formal.get('status') == 'blocked' and formal.get('formal_results_available') is False
          and formal.get('publication_ready') is False, 'Original dual task is no longer blocked')
    validate_documents(state)
    return state, protocol, protected


def compare_frame(delivered, reference, filename):
    current = pd.read_csv(delivered, keep_default_na=False, float_precision='round_trip')
    previous = pd.read_csv(reference, keep_default_na=False, float_precision='round_trip')
    check(list(current.columns) == list(previous.columns) and current.shape == previous.shape,
          'Reference column/row order differs: ' + filename)
    for column in previous.columns:
        a, b = current[column], previous[column]
        if pd.api.types.is_numeric_dtype(b):
            check(pd.api.types.is_numeric_dtype(a), 'Reference numeric type differs: ' + filename)
            check(np.isfinite(a.to_numpy(float)).all() and np.isfinite(b.to_numpy(float)).all()
                  and np.allclose(a.to_numpy(float), b.to_numpy(float), rtol=0, atol=ATOL),
                  'Reference numerical values/order differ: ' + filename + '/' + column)
        else:
            check(a.tolist() == b.tolist(), 'Reference row order/values differ: ' + filename + '/' + column)
    return len(current)


def accept_delivery(bundle, manifest_sha256, output, state_path=None, reference_run=None):
    bundle, output = Path(bundle).resolve(), Path(output).resolve()
    check(not output.exists(), 'Refusing to overwrite acceptance output')
    check(not output.is_relative_to(bundle), 'Acceptance output must be outside the delivery bundle')
    state_path = Path(state_path) if state_path is not None else ROOT / STATE_RELATIVE
    state, protocol, protected = verify_workspace(state_path)
    for directory in (ROOT / '03_experiments/runs', ROOT / '03_experiments/protocols',
                      relative_file(ROOT, protocol['release_manifest']).parent):
        check(not output.is_relative_to(directory.resolve()),
              'Acceptance output must be outside frozen research artifact directories')
    runtime = DeliveryRuntime(bundle, manifest_sha256)
    offline = runtime.verify()
    manifest = read_json(bundle / 'manifest.json')
    check(manifest['schema_version'] == 1 and manifest['protocol_id'] == protocol['protocol_id'],
          'Delivery protocol differs from v26')
    artifact = {key: relative_file(bundle, value) for key, value in manifest['artifacts'].items()}
    check(sha256(artifact['protocol']) == state['inputs'][PROTOCOL_RELATIVE]
          and sha256(artifact['freeze']) == state['inputs'][FREEZE_RELATIVE],
          'Delivery scientific binding differs from v26')
    for key in ('molecules', 'observations', 'fold_roles'):
        check(sha256(artifact[key]) == protocol[key + '_sha256'], 'Delivery data binding differs: ' + key)
    check(manifest['sample_ids'] == protocol['sample_ids']
          and manifest['model_names'] == list(protocol['models']), 'Delivery sample/model order differs')
    runtime_source = ROOT / RUNTIME_SOURCE
    runtime_sha = sha256(runtime_source)
    check(manifest['files'].get('runtime.py') == runtime_sha
          and sha256(relative_file(bundle, 'runtime.py')) == runtime_sha,
          'Packaged runtime source differs from the reviewed workspace runtime')
    protected[runtime_source.resolve()] = runtime_sha
    check('evidence/source_index.json' in manifest['files'], 'Delivery source index is not bound')
    provenance = read_json(relative_file(bundle, 'evidence/source_index.json'))
    source_mismatches = provenance['historical_source_input_mismatches']
    certificate_gaps = provenance['unverified_historical_certificate_references']
    release_record = read_json(ROOT / protocol['release_manifest'])
    validate = read_json(artifact['validation'])
    verify_certificate(validate, artifact['run_manifest'], sha256(artifact['protocol']), sha256(artifact['freeze']))
    check(offline.get('status') == 'passed' and offline.get('fit_calls_during_validation') == 0,
          'Offline delivery verification did not pass without fitting')
    reference = (ROOT / state['run_directory']).resolve()
    if reference_run is not None:
        supplied = Path(reference_run).resolve()
        check(sha256(supplied / 'manifest.json') == state['inputs'][state['run_directory'] + '/manifest.json'],
              'Reference run must be the original v26-verified run or an exact copy')
        reference = supplied
    verify_inventory(reference, protected)
    comparisons = {}
    for key, filename in (('oof', 'oof_predictions.csv'), ('fold_metrics', 'fold_metrics.csv'),
                          ('pooled_metrics', 'pooled_descriptive_metrics.csv')):
        comparisons[filename] = {'rows': compare_frame(artifact[key], reference / filename, filename),
                                 'values_and_order_equal': True, 'absolute_tolerance': ATOL}
    features = np.load(artifact['features'], allow_pickle=False)
    original_features = np.load(reference / 'fixed_features.npy', allow_pickle=False)
    check(features.shape == original_features.shape == (17, 44)
          and np.isfinite(features).all() and np.isfinite(original_features).all()
          and np.allclose(features, original_features, rtol=0, atol=ATOL),
          'Reference feature values/sample order differ')
    comparisons['fixed_features.npy'] = {'shape': [17, 44], 'values_and_order_equal': True,
                                         'absolute_tolerance': ATOL}
    for path, expected_sha in protected.items():
        check(sha256(path) == expected_sha, 'Protected input changed during acceptance: ' + str(path))
    result = {
        'status': 'passed', 'generated_at': utc_now(), 'engineering_delivery_accepted': True,
        'bundle_directory': str(bundle), 'manifest_sha256': manifest_sha256,
        'state_path': STATE_RELATIVE, 'state_sha256': STATE_SHA256,
        'state_updated': False, 'protocol_id': 'protocol-mic-13',
        'documents_verified': len(DOCS), 'immutable_files_verified': len(protected),
        'packaged_runtime_sha256': runtime_sha, 'offline_validation': offline,
        'source_provenance': {
            'closure_scope': provenance['closure_scope'],
            'permission_scope': provenance['permission_scope'],
            'current_release_protected_bindings_verified': len(release_record['protected']),
            'historical_source_input_mismatch_count': len(source_mismatches),
            'unverified_historical_certificate_reference_count': len(certificate_gaps),
            'historical_source_input_mismatches': source_mismatches,
            'unverified_historical_certificate_references': certificate_gaps,
            'limitations': [
                'Source files are retained; this acceptance does not verify all inputs of every historical certificate.',
                'Historical source/document bytes missing from their earlier snapshots remain unverified and cannot support historical reproducibility claims.',
                'Current v26 inputs, protocol-13 dependencies, current release protected bindings and original verified run outputs were checked against their immutable digests.',
            ],
        },
        'reference_run': str(reference), 'reference_run_comparisons': comparisons,
        'formal_dual_task_status': 'blocked', 'formal_results_available': False,
        'publication_ready': False, 'new_scientific_experiment': False,
        'independent_human_review_claimed': False,
        'historical_fixed_inventory_checks': {
            'applicable_to_current_cohort': False,
            'reason': 'Historical publisher/tests assert the frozen 16-molecule inventory; v26 admits 17 molecules and 42 assay-table mentions. Their sources and assertions remain unchanged.',
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--state', type=Path, default=ROOT / STATE_RELATIVE)
    parser.add_argument('--reference-run', type=Path)
    args = parser.parse_args()
    with redirect_stdout(sys.stderr):
        result = accept_delivery(args.bundle, args.manifest_sha256, args.output, args.state, args.reference_run)
    # ASCII JSON remains UTF-8 compatible even under a Windows GBK console.
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))


if __name__ == '__main__':
    main()
