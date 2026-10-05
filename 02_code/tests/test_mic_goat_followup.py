"""Current follow-up checks; historical frozen inventory checks remain intact."""
import json
from pathlib import Path
import shutil

import pandas as pd
import pytest

from publish_mic_goat_status import validate_documents
from research_utils import ROOT, read_json
from train_mic_goat_baseline_v2 import inspect_release, load, validate
from mic_followup_release import audit_partition
from research_evidence_gate import verify_manifest

RELEASE = ROOT / '03_experiments/audits/mic_goat_followup_release_20261004_v1'
PROTOCOL = ROOT / '03_experiments/protocols/protocol-mic-13.json'
FREEZE = ROOT / '03_experiments/audits/protocol_mic_13_freeze_20261004_v1.json'
RUN = ROOT / '03_experiments/runs/mic_goat_baseline_20261004_v2'
STATE = ROOT / '03_experiments/audits/mic_training_readiness_20261004_v26.json'


def test_current_machine_documents_agree_without_fixed_historical_inventory():
    validate_documents(read_json(STATE))


def test_original_mentions_and_opposite_labels_are_preserved():
    mentions = pd.read_csv(RELEASE / 'all_original_mic_mentions.csv')
    decisions = pd.read_csv(RELEASE / 'candidate_decisions.csv')
    assert len(mentions) == 45
    assert decisions.measurement_mentions.tolist() == [19, 18, 8]
    assert decisions.binary_label_set.tolist() == ['[1]', '[0, 1]', '[0, 1]']
    assert decisions.decision.tolist() == ['passed_primary_evidence',
                                          'blocked_opposite_measured_labels',
                                          'blocked_opposite_measured_labels']
    assert 'Escherichia coli (CI 214)' in set(mentions.target)
    assert mentions.target.str.contains('26 days').any()


def test_fixed_split_preserves_full_sources_and_all_pairs():
    mol, obs, roles, audit = inspect_release(RELEASE)
    assert len(mol) == 17 and len(obs) == 42
    assert int(mol.amp.sum()) == 6 and audit['pairs_recomputed'] == 136
    assert audit['status'] == 'passed'
    assert audit['cross_fold_homology_edges'] == audit['cross_fold_primary_studies'] == 0
    assert mol.component.nunique() == 7


def test_missing_freeze_refuses_before_fit(tmp_path):
    with pytest.raises(ValueError, match='Mandatory protocol and freeze missing'):
        load(PROTOCOL, tmp_path / 'absent.json')


def test_changed_protocol_refuses_before_fit(tmp_path):
    changed = tmp_path / 'protocol.json'
    protocol = read_json(PROTOCOL)
    protocol['decision_threshold'] = 0.4
    changed.write_text(json.dumps(protocol), encoding='utf-8')
    with pytest.raises(ValueError, match='Freeze binding differs'):
        load(changed, FREEZE)


def test_incomplete_member_comparison_is_rejected():
    cohort = RELEASE / 'cohort'
    mol = pd.read_csv(cohort / 'candidate_molecules.csv', keep_default_na=False)
    obs = pd.read_csv(cohort / 'candidate_observations.csv', keep_default_na=False)
    roles = pd.read_csv(cohort / 'fold_roles.csv', keep_default_na=False)
    pairs = pd.read_csv(cohort / 'all_member_similarity.csv')
    sources = pd.read_csv(RELEASE / 'evidence/source_review.csv', keep_default_na=False)
    with pytest.raises(ValueError, match='pair audit differs'):
        audit_partition(mol, obs, sources, roles, pairs.iloc[:-1])


def test_changed_prediction_digest_is_rejected(tmp_path):
    copied = tmp_path / 'run'
    shutil.copytree(RUN, copied)
    (copied / 'oof_predictions.csv').write_text('changed', encoding='utf-8')
    with pytest.raises(ValueError, match='output changed'):
        verify_manifest(copied)


def test_current_run_reloads_and_recomputes_without_fit(tmp_path):
    result = validate(RUN, tmp_path / 'validation.json', PROTOCOL, FREEZE)
    assert result['status'] == 'passed'
    assert result['models_reloaded'] == 9
    assert result['oof_rows_independently_recomputed'] == 51
    assert result['fit_calls_during_validation'] == 0
