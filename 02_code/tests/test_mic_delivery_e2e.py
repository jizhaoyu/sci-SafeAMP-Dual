"""Acceptance through the exported CLI, without the research workspace on sys.path."""
import json
import shutil
import subprocess
import sys

import pytest

from mic_delivery import build_delivery
from research_utils import ROOT


RUN = ROOT / '03_experiments/runs/mic_delivery_reproduction_20261004_v1'
PROTOCOL = ROOT / '03_experiments/protocols/protocol-mic-13.json'
FREEZE = ROOT / '03_experiments/audits/protocol_mic_13_freeze_20261004_v1.json'


@pytest.fixture(scope='module')
def moved_bundle(tmp_path_factory):
    target = tmp_path_factory.mktemp('mic-portable-delivery')
    result = build_delivery(RUN, PROTOCOL, FREEZE, target / 'original')
    moved = target / 'moved'
    shutil.copytree(target / 'original', moved)
    return moved, result['manifest_sha256']


def invoke(bundle, anchor, command, *extra):
    return subprocess.run(
        [sys.executable, str(bundle / 'runtime.py'), command,
         '--bundle', str(bundle), '--manifest-sha256', anchor, *extra],
        cwd=bundle.parent, capture_output=True, text=True, encoding='utf-8',
        timeout=60,
    )


def test_exported_runtime_verifies_after_directory_move(moved_bundle):
    bundle, anchor = moved_bundle
    result = invoke(bundle, anchor, 'verify')
    assert result.returncode == 0, result.stderr
    verified = json.loads(result.stdout)
    assert verified['status'] == 'passed'
    assert verified['models_reloaded'] == 9
    assert verified['oof_rows_independently_recomputed'] == 51
    assert verified['fit_calls_during_validation'] == 0


def test_exported_runtime_replays_all_models_for_one_holdout_sample(moved_bundle):
    bundle, anchor = moved_bundle
    sample = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))['sample_ids'][0]
    result = invoke(bundle, anchor, 'replay', '--sample-id', sample)
    assert result.returncode == 0, result.stderr
    rows = json.loads(result.stdout)
    assert len(rows) == 3
    assert {row['sample_id'] for row in rows} == {sample}
    assert {row['model'] for row in rows} == {'dummy_prior', 'logistic_regression', 'random_forest'}


def test_exported_runtime_rejects_unknown_sample(moved_bundle):
    bundle, anchor = moved_bundle
    result = invoke(bundle, anchor, 'replay', '--sample-id', 'not-an-admitted-sample')
    assert result.returncode != 0


def test_exported_runtime_requires_correct_trust_anchor(moved_bundle):
    bundle, _ = moved_bundle
    result = invoke(bundle, '0' * 64, 'verify')
    assert result.returncode != 0


def test_portable_bundle_includes_conflicts_and_full_original_pair_audit(moved_bundle):
    bundle, _ = moved_bundle
    assert (bundle / 'release/all_original_mic_mentions.csv').is_file()
    assert (bundle / 'release/candidate_decisions.csv').is_file()
    assert (bundle / 'cohort/all_member_similarity.csv').is_file()
    assert not any(path.name == '.env' or 'secret' in path.parts for path in bundle.rglob('*'))
