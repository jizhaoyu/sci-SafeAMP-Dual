"""Tests for research_feasibility gating evaluation on raw records and prepared directories."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from research_feasibility import audit_prepared_feasibility, audit_feasibility
from research_utils import sha256, write_json


def make_valid_prepared_fixture(tmp_path):
    prep_dir = tmp_path / "prepared_v1"
    prep_dir.mkdir(parents=True)

    # 1. exclusions.json
    write_json(prep_dir / "exclusions.json", [])
    # 2. evidence_audit.json
    write_json(prep_dir / "evidence_audit.json", {"status": "validated"})
    # 3. partition_audit.json
    write_json(prep_dir / "partition_audit.json", {"status": "validated", "splits": {}, "folds": {}})
    # 4. cluster_membership.csv
    pd.DataFrame([
        {"sample_id": "s1", "cluster_id": 0, "representative_sample_id": "s1"}
    ]).to_csv(prep_dir / "cluster_membership.csv", index=False)
    # 5. records.csv
    pd.DataFrame([]).to_csv(prep_dir / "records.csv", index=False)
    # 6. dataset.csv
    pd.DataFrame([]).to_csv(prep_dir / "dataset.csv", index=False)

    manifest = {
        "status": "validated",
        "protocol_id": "legacy-v1",
        "cutoff": 0.40,
        "dataset_sha256": sha256(prep_dir / "dataset.csv"),
        "provenance_sha256": sha256(prep_dir / "records.csv"),
        "cluster_membership_sha256": sha256(prep_dir / "cluster_membership.csv"),
        "partition_audit_sha256": sha256(prep_dir / "partition_audit.json"),
        "evidence_audit_sha256": sha256(prep_dir / "evidence_audit.json"),
        "exclusions_sha256": sha256(prep_dir / "exclusions.json"),
    }
    write_json(prep_dir / "manifest.json", manifest)
    return prep_dir


def test_missing_prepared_files_blocks_feasibility(tmp_path):
    prep_dir = tmp_path / "incomplete_prepared"
    prep_dir.mkdir()
    # Missing files
    write_json(prep_dir / "manifest.json", {"status": "validated"})
    out_dir = tmp_path / "audit_out_1"

    is_feasible, report = audit_prepared_feasibility(prep_dir, out_dir)
    assert is_feasible is False
    assert report["status"] == "blocked"
    assert any("Missing required prepared files" in b for b in report["blockers"])


def test_protocol_mismatch_blocks_prepared_feasibility(tmp_path):
    prep_dir = make_valid_prepared_fixture(tmp_path)
    out_dir = tmp_path / "audit_out_2"

    is_feasible, report = audit_prepared_feasibility(prep_dir, out_dir, protocol_id="protocol-amd-01")
    assert is_feasible is False
    assert any("does not match prepared protocol" in b for b in report["blockers"])


def test_protocol_conflict_blocks_feasibility_gate(tmp_path):
    records_file = tmp_path / "dummy_records.csv"
    records_file.write_text("invalid,records")
    out_dir = tmp_path / "audit_out_3"

    is_feasible, report = audit_feasibility(records_file, out_dir, protocol_id="protocol-amd-01")
    assert is_feasible is False
    assert any("protocol_conflict" in b for b in report["blockers"])
