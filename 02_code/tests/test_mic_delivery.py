"""Current delivery builder checks without changing any frozen artifacts."""
import json
from pathlib import Path
import shutil
import tempfile

import pytest

import mic_delivery as delivery
from research_utils import ROOT, read_json, sha256

PROTOCOL = ROOT / '03_experiments/protocols/protocol-mic-13.json'
FREEZE = ROOT / '03_experiments/audits/protocol_mic_13_freeze_20261004_v1.json'
RUN = ROOT / '03_experiments/runs/mic_goat_baseline_20261004_v2'


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    output = tmp_path_factory.mktemp('mic-delivery-builder') / 'bundle'
    result = delivery.build_delivery(RUN, PROTOCOL, FREEZE, output)
    return output, result


def test_real_independent_validation_and_complete_export(built):
    bundle, result = built
    assert result['manifest_sha256'] == sha256(bundle / 'manifest.json')
    validation = read_json(bundle / 'validation.json')
    assert validation['status'] == 'passed'
    assert validation['models_reloaded'] == 9
    assert validation['oof_rows_independently_recomputed'] == 51
    assert validation['fit_calls_during_validation'] == 0
    assert validation['run_manifest_sha256'] == sha256(RUN / 'manifest.json')
    assert validation['generated_at'] > read_json(RUN / 'manifest.json')['generated_at']
    for relative in ('release/manifest.json', 'release/all_original_mic_mentions.csv',
                     'release/candidate_decisions.csv', 'release/partition_audit.json',
                     'release/independent_partition_validation.json', 'runtime.py',
                     'README.md', 'MODEL_CARD.md', 'LICENSE_NOTICE.md', 'requirements-lock.txt'):
        assert (bundle / relative).is_file()
    manifest = read_json(bundle / 'manifest.json')
    assert manifest['schema_version'] == 1
    assert manifest['scope'] == 'admitted_cohort_oof_replay_only'
    assert len(manifest['sample_ids']) == 17
    assert set(manifest['models']) == {'logistic_regression', 'random_forest', 'dummy_prior'}
    assert sum(len(folds) for folds in manifest['models'].values()) == 9
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob('*') if p.is_file()}
    assert actual == set(manifest['files']) | {'manifest.json'}
    for relative, expected in manifest['files'].items():
        assert sha256(bundle / relative) == expected
    assert manifest['files']['runtime.py'] == sha256(delivery.RUNTIME)
    assert 'scipy==' in (bundle / 'requirements-lock.txt').read_text()
    assert 'threadpoolctl==' in (bundle / 'requirements-lock.txt').read_text()


def test_sources_preserve_all_primary_citations_and_historical_limits(built):
    bundle, _ = built
    index = read_json(bundle / 'evidence/source_index.json')
    assert len(index['sources']) == 10
    for source in index['sources']:
        assert sha256(bundle / source['bundle_primary_file']) == source['sha256']
        assert source['source_url'].startswith('https://')
        assert 'not independently confirmed' in source['redistribution_permission']
    assert any(s['primary_license_notices'] for s in index['sources'])
    assert any(not s['primary_license_notices'] for s in index['sources'])
    assert 'historical certificates' in index['closure_scope']
    mismatches = index['historical_source_input_mismatches']
    assert len(mismatches) == 1 and mismatches[0]['input'] == '02_code/mic_reviewed_release.py'
    assert mismatches[0]['historical_sha256'] != mismatches[0]['current_sha256']
    refs = index['unverified_historical_certificate_references']
    assert sum(str(r['input']).endswith('.md') for r in refs) == 7


def test_existing_delivery_refuses_before_validation(built, monkeypatch):
    bundle, _ = built
    monkeypatch.setattr(delivery.frozen, 'validate', lambda *_: pytest.fail('must not validate'))
    with pytest.raises(FileExistsError, match='Refusing to overwrite'):
        delivery.build_delivery(RUN, PROTOCOL, FREEZE, bundle)


def test_missing_freeze_refuses(tmp_path):
    with pytest.raises(ValueError, match='Mandatory protocol and freeze missing'):
        delivery.build_delivery(RUN, PROTOCOL, tmp_path / 'missing.json', tmp_path / 'bundle')
    assert not (tmp_path / 'bundle').exists()


@pytest.mark.parametrize('field', ['protocol', 'freeze'])
def test_changed_frozen_binding_refuses(tmp_path, field):
    original = PROTOCOL if field == 'protocol' else FREEZE
    value = read_json(original)
    value['decision_threshold' if field == 'protocol' else 'protocol_file_sha256'] = 0.4
    changed = tmp_path / (field + '.json')
    changed.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError, match='Freeze binding differs'):
        delivery.build_delivery(RUN, changed if field == 'protocol' else PROTOCOL,
                                changed if field == 'freeze' else FREEZE, tmp_path / 'bundle')
    assert not (tmp_path / 'bundle').exists()


def test_incomplete_run_refuses_before_export(tmp_path):
    with tempfile.TemporaryDirectory(prefix='mic-delivery-test-', dir=RUN.parent) as temporary:
        copied = Path(temporary) / 'run'
        shutil.copytree(RUN, copied)
        (copied / 'fold_models/dummy_prior_fold0.joblib').unlink()
        with pytest.raises(FileNotFoundError):
            delivery.build_delivery(copied, PROTOCOL, FREEZE, tmp_path / 'bundle')
    assert not (tmp_path / 'bundle').exists()


def test_validation_certificate_requires_actual_coverage(tmp_path, monkeypatch):
    validate = delivery.frozen.validate

    def insufficient(*args):
        result = validate(*args)
        return {**result, 'oof_rows_independently_recomputed': 50}

    monkeypatch.setattr(delivery.frozen, 'validate', insufficient)
    with pytest.raises(ValueError, match='lacks required coverage'):
        delivery.build_delivery(RUN, PROTOCOL, FREEZE, tmp_path / 'bundle')
    assert not (tmp_path / 'bundle').exists()


def test_retrain_calls_frozen_training_then_build(tmp_path, monkeypatch):
    run = tmp_path / 'run'
    output = tmp_path / 'bundle'
    events = []
    monkeypatch.setattr(delivery, 'ROOT', tmp_path)
    monkeypatch.setattr(delivery.frozen, 'train', lambda *args: events.append(('train', args)))

    def build(*args):
        events.append(('build', args))
        return {'manifest_sha256': 'a' * 64}

    monkeypatch.setattr(delivery, 'build_delivery', build)
    assert delivery.retrain(run, PROTOCOL, FREEZE, output)['manifest_sha256'] == 'a' * 64
    assert [e[0] for e in events] == ['train', 'build']
    assert events[0][1] == (run, PROTOCOL.resolve(), FREEZE.resolve())


def test_retrain_existing_run_does_not_fit(tmp_path, monkeypatch):
    monkeypatch.setattr(delivery.frozen, 'train', lambda *_: pytest.fail('must not fit'))
    with pytest.raises(FileExistsError):
        delivery.retrain(RUN, PROTOCOL, FREEZE, tmp_path / 'bundle')


def test_sensitive_source_and_source_changed_during_copy_refuse(tmp_path):
    (tmp_path / '.env').write_text('redacted fixture', encoding='utf-8')
    with pytest.raises(ValueError, match='Sensitive or linked source'):
        delivery._tree(tmp_path)
    source = tmp_path / 'source.csv'
    source.write_text('first', encoding='utf-8')
    expected = sha256(source)
    source.write_text('changed', encoding='utf-8')
    with pytest.raises(ValueError, match='Source changed during export'):
        delivery._copy(source, tmp_path / 'output.csv', expected)
