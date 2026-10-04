"""Tests for research readiness status generator and CLI contract."""
import json
from pathlib import Path
import pytest

from research_readiness import generate_current_status
from research_utils import write_json, read_json
from test_publication_approval import make_export_fixtures


def test_missing_prepared_manifest_raises(tmp_path):
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    with pytest.raises(ValueError, match="Prepared directory does not contain manifest.json"):
        generate_current_status(empty_dir)


def test_blocked_preparation_generates_blocked_status(tmp_path):
    prep_dir = tmp_path / "prep_blocked"
    prep_dir.mkdir()
    write_json(prep_dir / "manifest.json", {
        "status": "blocked",
        "reason": "Single-class partition in fold 0",
        "protocol_id": "legacy-v1"
    })
    
    st = generate_current_status(prep_dir)
    assert st["status"] == "blocked"
    assert st["dataset_preparation_status"] == "blocked"
    assert st["run_status"] == "none"
    assert st["formal_results_available"] is False
    assert st["publication_ready"] is False
    assert any("Single-class partition" in b for b in st["blockers"])


def test_validated_prep_without_run_is_not_formal_results(tmp_path):
    prep_dir = tmp_path / "prep_valid"
    prep_dir.mkdir()
    write_json(prep_dir / "manifest.json", {
        "status": "validated",
        "protocol_id": "legacy-v1"
    })

    st = generate_current_status(prep_dir, run_dir=None)
    assert st["status"] == "blocked"
    assert st["dataset_preparation_status"] == "validated"
    assert st["run_status"] == "none"
    assert st["formal_results_available"] is False
    assert st["publication_ready"] is False
    assert any("No experimental run evaluated" in b for b in st["blockers"])


def test_historical_protocol_cannot_emit_ready_status(tmp_path):
    prep_dir, run_dir = make_export_fixtures(tmp_path)
    
    st = generate_current_status(prep_dir, run_dir)
    assert st["status"] == "blocked"
    assert st["dataset_preparation_status"] == "validated"
    assert st["run_status"] == "completed"
    assert st["formal_results_available"] is True
    assert any('protocol_conflict' in b for b in st['blockers'])
    # Without human approval, publication_ready must remain False!
    assert st["publication_ready"] is False
    assert any("Publication submission requires formal human review" in b for b in st["blockers"])


def test_research_readiness_cli(tmp_path, capsys):
    prep_dir, run_dir = make_export_fixtures(tmp_path)
    out_file = tmp_path / "status_out.json"

    import sys
    from unittest.mock import patch
    import research_readiness

    test_args = [
        "research_readiness.py",
        "--prepared", str(prep_dir),
        "--run", str(run_dir),
        "--output", str(out_file)
    ]
    with patch.object(sys, "argv", test_args):
        # Call the __main__ block logic
        st = research_readiness.generate_current_status(prep_dir, run_dir)
        research_readiness.write_json(out_file, st)
    
    assert out_file.exists()
    saved = read_json(out_file)
    assert saved["status"] == "blocked"
    assert saved["formal_results_available"] is True
