"""Workspace acceptance preserves scientific bindings and compares fixed results."""
import json
from pathlib import Path
import shutil
import sys

import pandas as pd
import pytest

import accept_mic_delivery as acceptance
from mic_delivery import build_delivery
from research_utils import ROOT, read_json, sha256

STATE = ROOT / acceptance.STATE_RELATIVE
PROTOCOL = ROOT / acceptance.PROTOCOL_RELATIVE
FREEZE = ROOT / acceptance.FREEZE_RELATIVE
RUN = ROOT / read_json(STATE)['run_directory']


@pytest.fixture(scope='module')
def delivery(tmp_path_factory):
    bundle = tmp_path_factory.mktemp('acceptance') / 'bundle'
    result = build_delivery(RUN, PROTOCOL, FREEZE, bundle)
    return bundle, result['manifest_sha256']


def reanchor(bundle):
    manifest = read_json(bundle / 'manifest.json')
    manifest['files'] = {name: sha256(bundle / name) for name in manifest['files']}
    (bundle / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    return sha256(bundle / 'manifest.json')


def test_accepts_temporary_delivery_without_changing_v26(delivery, tmp_path):
    bundle, anchor = delivery
    before = sha256(STATE)
    output = tmp_path / 'acceptance.json'
    report = acceptance.accept_delivery(bundle, anchor, output)
    assert read_json(output) == report
    assert report['engineering_delivery_accepted'] is True
    assert report['formal_dual_task_status'] == 'blocked'
    assert report['formal_results_available'] is report['publication_ready'] is False
    assert report['new_scientific_experiment'] is report['independent_human_review_claimed'] is False
    assert report['documents_verified'] == 5
    assert report['offline_validation']['models_reloaded'] == 9
    assert report['reference_run_comparisons']['oof_predictions.csv']['rows'] == 51
    release = read_json(ROOT / read_json(PROTOCOL)['release_manifest'])
    assert report['source_provenance']['current_release_protected_bindings_verified'] == len(release['protected'])
    assert report['source_provenance']['historical_source_input_mismatch_count'] == 1
    assert report['source_provenance']['unverified_historical_certificate_reference_count'] == 10
    assert sha256(STATE) == before == report['state_sha256']


def test_acceptance_cli_stdout_is_one_json_document(delivery, tmp_path, monkeypatch, capsys):
    bundle, anchor = delivery
    output = tmp_path / 'cli-acceptance.json'
    monkeypatch.setattr(sys, 'argv', ['accept_mic_delivery.py', '--bundle', str(bundle),
                                    '--manifest-sha256', anchor, '--output', str(output)])
    acceptance.main()
    captured = capsys.readouterr()
    assert json.loads(captured.out) == read_json(output)
    assert 'PASS: five exact' in captured.err


def test_rejects_wrong_anchor_without_output(delivery, tmp_path):
    bundle, _ = delivery
    output = tmp_path / 'rejected.json'
    with pytest.raises(ValueError, match='(?i)anchor|manifest.*sha|manifest.*digest'):
        acceptance.accept_delivery(bundle, '0' * 64, output)
    assert not output.exists()


def test_rejects_forged_state_even_with_valid_passed_fields(delivery, tmp_path):
    bundle, anchor = delivery
    forged = tmp_path / 'state.json'
    state = read_json(STATE)
    state['inputs'][acceptance.PROTOCOL_RELATIVE] = '0' * 64
    forged.write_text(json.dumps(state), encoding='utf-8')
    with pytest.raises(ValueError, match='anchored v26'):
        acceptance.accept_delivery(bundle, anchor, tmp_path / 'rejected.json', forged)


def test_same_bytes_state_copy_is_allowed(delivery, tmp_path):
    bundle, anchor = delivery
    copied = tmp_path / 'state.json'
    shutil.copyfile(STATE, copied)
    report = acceptance.accept_delivery(bundle, anchor, tmp_path / 'acceptance.json', copied)
    assert report['state_path'] == acceptance.STATE_RELATIVE
    assert report['state_updated'] is False


def test_rejects_scientific_binding_change_with_regenerated_anchor(delivery, tmp_path):
    original, _ = delivery
    bundle = tmp_path / 'changed'
    shutil.copytree(original, bundle)
    protocol = read_json(bundle / 'protocol.json')
    protocol['decision_threshold'] = 0.4
    (bundle / 'protocol.json').write_text(json.dumps(protocol), encoding='utf-8')
    output = tmp_path / 'rejected.json'
    with pytest.raises(ValueError):
        acceptance.accept_delivery(bundle, reanchor(bundle), output)
    assert not output.exists()


def test_rejects_frozen_dependency_change_without_touching_original(delivery, tmp_path, monkeypatch):
    bundle, anchor = delivery
    real_sha = acceptance.sha256
    dependency = (ROOT / '02_code/feature_extractor.py').resolve()

    def changed_sha(path):
        return '0' * 64 if Path(path).resolve() == dependency else real_sha(path)

    monkeypatch.setattr(acceptance, 'sha256', changed_sha)
    output = tmp_path / 'rejected.json'
    with pytest.raises(ValueError, match='Immutable binding changed'):
        acceptance.accept_delivery(bundle, anchor, output)
    assert not output.exists()


def test_rejects_history_change_without_touching_original(delivery, tmp_path, monkeypatch):
    bundle, anchor = delivery
    real_sha = acceptance.sha256
    history = (ROOT / '03_experiments/runs/mic_followup_baseline_20261004_v1/fixed_features.npy').resolve()
    monkeypatch.setattr(acceptance, 'sha256', lambda path: '0' * 64
                        if Path(path).resolve() == history else real_sha(path))
    with pytest.raises(ValueError, match='Immutable binding changed'):
        acceptance.accept_delivery(bundle, anchor, tmp_path / 'rejected.json')


def test_exclusive_output_preserves_existing_bytes(delivery, tmp_path):
    bundle, anchor = delivery
    output = tmp_path / 'existing.json'
    output.write_bytes(b'preserve existing evidence')
    with pytest.raises(ValueError, match='overwrite'):
        acceptance.accept_delivery(bundle, anchor, output)
    assert output.read_bytes() == b'preserve existing evidence'
    with pytest.raises(ValueError, match='outside the delivery bundle'):
        acceptance.accept_delivery(bundle, anchor, bundle / 'unmanifested.json')


def test_reference_numeric_tolerance_and_row_order(tmp_path):
    reference = tmp_path / 'original.csv'
    current = tmp_path / 'current.csv'
    frame = pd.DataFrame({'sample_id': ['first', 'second'], 'probability': [0.25, 0.75]})
    frame.to_csv(reference, index=False)
    frame.assign(probability=[0.25 + 5e-13, 0.75]).to_csv(current, index=False)
    assert acceptance.compare_frame(current, reference, 'oof.csv') == 2
    frame.iloc[::-1].to_csv(current, index=False)
    with pytest.raises(ValueError, match='row order'):
        acceptance.compare_frame(current, reference, 'oof.csv')
    frame.assign(probability=[0.26, 0.75]).to_csv(current, index=False)
    with pytest.raises(ValueError, match='numerical'):
        acceptance.compare_frame(current, reference, 'oof.csv')


@pytest.mark.parametrize('directory', [
    '03_experiments/runs/mic_delivery_reproduction_20261004_v1',
    '03_experiments/protocols',
    '03_experiments/audits/mic_goat_followup_release_20261004_v1/cohort',
])
def test_acceptance_cannot_add_files_to_frozen_research_artifacts(delivery, directory):
    bundle, anchor = delivery
    output = ROOT / directory / 'delivery-acceptance-must-not-be-created.json'
    assert not output.exists()
    with pytest.raises(ValueError, match='outside frozen research artifact'):
        acceptance.accept_delivery(bundle, anchor, output)
    assert not output.exists()


def test_changed_validation_certificate_is_refused(delivery, tmp_path):
    bundle, _ = delivery
    certificate = read_json(bundle / 'validation.json')
    certificate['fit_calls_during_validation'] = 1
    with pytest.raises(ValueError, match='certificate is incomplete'):
        acceptance.verify_certificate(certificate, bundle / 'run/manifest.json', sha256(PROTOCOL), sha256(FREEZE))


def test_exact_reference_copy_allowed_and_changed_manifest_rejected(delivery, tmp_path):
    bundle, anchor = delivery
    reference = tmp_path / 'reference'
    shutil.copytree(RUN, reference)
    report = acceptance.accept_delivery(bundle, anchor, tmp_path / 'accepted.json', reference_run=reference)
    assert report['reference_run'] == str(reference.resolve())
    manifest = read_json(reference / 'manifest.json')
    manifest['generated_at'] = '2026-10-05T00:00:00+00:00'
    (reference / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='Reference run must be the original'):
        acceptance.accept_delivery(bundle, anchor, tmp_path / 'rejected.json', reference_run=reference)
