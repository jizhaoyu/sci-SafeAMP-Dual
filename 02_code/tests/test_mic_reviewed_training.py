from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from mic_reviewed_release import (DEFAULT_OUTPUT, NEW_STATE, STATE16,
                                  _candidate_decisions, _check_inputs,
                                  audit_existing_baseline, prepare, review,
                                  verify_manifest)
from research_utils import ROOT
from train_mic_reviewed_baseline import FREEZE, PROTOCOL, freeze, train


def test_two_new_source_records_remain_unreleased_and_unlabelled():
    ctx = _check_inputs()
    rows = _candidate_decisions(ctx)
    assert set(rows.record_id) == {"chekmenev2006:p1-COO-", "bmap2025:BMAP-27B"}
    assert set(rows.evidence_decision) == {
        "withheld_actual_assay_n_terminus_unverified",
        "withheld_isolate_specific_mic_unverified",
    }
    assert rows.derived_label.isna().all()
    assert not rows.expanded_training_release.astype(bool).any()
    assert set(rows.source_doi) == {"10.1016/j.bbamem.2006.03.034", "10.1002/mlf2.70020"}


def test_historical_15_baseline_isolation_reaudit_recomputes_all_105_pairs(tmp_path):
    source = DEFAULT_OUTPUT
    review_dir = tmp_path / "copied_review"
    review_dir.mkdir()
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    for name in ["manifest.json", *manifest["outputs"]]:
        shutil.copy2(source / name, review_dir / name)
    results = audit_existing_baseline(review_dir)
    assert results["status"] == "passed_existing_15_historical_partition_preserved"
    assert results["molecules"] == 15
    assert results["observations"] == 22
    assert results["all_member_pairs_recomputed"] == 105
    assert results["cross_fold_homology_edges"] == 0
    assert results["cross_fold_primary_studies"] == 0
    assert results["training_performed"] is False


def test_existing_baseline_reaudit_keeps_both_classes_in_every_partition(tmp_path):
    review_dir = tmp_path / "copied_review"
    review_dir.mkdir()
    manifest = json.loads((DEFAULT_OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    for name in ["manifest.json", *manifest["outputs"]]:
        shutil.copy2(DEFAULT_OUTPUT / name, review_dir / name)
    audit_existing_baseline(review_dir)
    roles = pd.read_csv(ROOT / "03_experiments/audits/mic_three_fold_20261002_v1/fold_roles.csv")
    for fold in range(3):
        for role in ("train", "validation"):
            selected = roles[(roles.fold == fold) & (roles.role == role)]
            assert set(selected.amp.astype(int)) == {0, 1}


def test_prepare_refuses_to_publish_cohort_when_both_candidates_are_withheld(tmp_path):
    target = ROOT / "03_experiments/audits" / f"test_mic_reviewed_empty_cohort_{tmp_path.name}"
    with pytest.raises(ValueError, match="No newly released molecules"):
        prepare(DEFAULT_OUTPUT, target)
    assert not target.exists()


def test_protocol_freeze_and_training_fail_closed_without_readiness_release(tmp_path):
    cohort = ROOT / "03_experiments/audits/mic_source_expansion_result_20261002_v2"
    release = ROOT / "03_experiments/audits/mic_three_fold_primary_release_20261002_v1"
    partition = ROOT / "03_experiments/audits/mic_three_fold_validation_20261002_v1.json"
    protocol_path = ROOT / "03_experiments/protocols/test_mic_reviewed_must_not_freeze.json"
    freeze_path = ROOT / "03_experiments/audits/test_mic_reviewed_must_not_freeze.json"
    with pytest.raises(ValueError, match="does not admit a new expanded cohort"):
        freeze(cohort, release, partition, protocol_path, freeze_path)
    assert not protocol_path.exists()
    assert not freeze_path.exists()
    run_path = ROOT / "03_experiments/runs/test_mic_reviewed_without_protocol"
    with pytest.raises(ValueError, match="protocol and freeze record are required"):
        train(run_path, tmp_path / "missing.json", tmp_path / "missing_freeze.json")
    assert not run_path.exists()


def test_readiness_state_and_formal_02_status_are_both_blocked():
    state = json.loads(NEW_STATE.read_text(encoding="utf-8"))
    old = json.loads(STATE16.read_text(encoding="utf-8"))
    assert state["status"] == "mic_expansion_blocked_existing_baseline_preserved"
    assert state["training_blocked"] is True
    assert state["training_protocol_id"] is None
    assert state["records_released_for_training"] == 0
    assert state["new_candidates_released"] == 0
    assert state["formal_dual_task_status"] == old["formal_dual_task_status"] == "blocked"
    assert state["formal_state_sha256"] == old["formal_state_sha256"]
    manifest = verify_manifest(DEFAULT_OUTPUT)
    assert manifest["existing_baseline_isolation_audit"]["all_member_pairs_recomputed"] == 105
    assert manifest["existing_baseline_isolation_audit"]["cross_fold_homology_edges"] == 0


def test_protocol_11_and_freeze_slots_remain_unused_until_gate_passes():
    if PROTOCOL.exists():
        pytest.skip("Protocol 11 has already been frozen in subsequent exploratory round")
    assert not PROTOCOL.exists()
    assert not FREEZE.exists()

