"""Regression checks for evidence gates; no model fitting or network access."""
import copy
from pathlib import Path

import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import research_evidence_gate as gate
import publish_mic_repair_status as status
import train_mic_esm2_three_fold as esm_entry
import train_mic_three_fold_v3 as hand_entry
from audit_mic_evidence_repair import original_identifiers, verify_original_materials
from curate_dual_task_external_evidence import curate_dual_task_evidence
from research_utils import ROOT, read_json


@pytest.fixture(autouse=True)
def forbid_fitting(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Regression verification must not fit models")
    for cls in (LogisticRegression, RandomForestClassifier, DummyClassifier, Pipeline, StandardScaler):
        monkeypatch.setattr(cls, "fit", fail)


def original_release():
    return gate.require_primary_release(
        read_json(ROOT / "03_experiments/protocols/protocol-mic-07.json"),
        ROOT / "03_experiments/audits/protocol_mic_07_freeze_20261002_v2.json",
        ROOT / "02_code/train_mic_three_fold_v2.py")


def test_existing_complete_release_still_passes():
    release = original_release()
    assert (release["molecules_evidence_approved"], release["observations_evidence_approved"]) == (15, 22)


@pytest.mark.parametrize("entry", [hand_entry, esm_entry])
def test_unreleased_frozen_protocol_rejected(entry):
    with pytest.raises(ValueError, match="does not bind a complete primary evidence release"):
        entry.load_validated()


@pytest.mark.parametrize("entry", [hand_entry, esm_entry])
def test_missing_freeze_rejected(entry, tmp_path, monkeypatch):
    monkeypatch.setattr(entry, "FREEZE", tmp_path / "absent-freeze.json")
    with pytest.raises(ValueError, match="mandatory protocol freeze is missing"):
        entry.load_validated()


def test_partial_release_not_promoted(monkeypatch):
    verify = gate.verify_manifest
    def incomplete(directory):
        result = copy.deepcopy(verify(directory))
        result["full_release_review_complete"] = False
        return result
    monkeypatch.setattr(gate, "verify_manifest", incomplete)
    with pytest.raises(ValueError, match="incomplete or for another cohort"):
        original_release()


def test_missing_molecule_approval_rejected(monkeypatch):
    read = pd.read_csv
    def fewer_rows(path, *args, **kwargs):
        rows = read(path, *args, **kwargs)
        return rows.iloc[:-1] if Path(path).name == "molecule_evidence_review.csv" else rows
    monkeypatch.setattr(pd, "read_csv", fewer_rows)
    with pytest.raises(ValueError, match="complete molecule/observation coverage"):
        original_release()


def test_primary_xml_ids_not_reference_ids(tmp_path):
    # Synthetic XML tests software parsing only; it is never a scientific evidence record.
    file = tmp_path / "article.xml"
    file.write_text('<article><front><article-meta><article-id pub-id-type="doi">10.1000/primary</article-id>'
                    '<article-id pub-id-type="pmid">1234</article-id></article-meta></front>'
                    '<back><article-meta><article-id pub-id-type="doi">10.1000/reference</article-id>'
                    '</article-meta></back></article>', encoding="utf-8")
    assert original_identifiers(file) == {"doi": "10.1000/primary", "pmid": "1234"}


def test_error_body_not_original_article(tmp_path):
    file = tmp_path / "error.xml"
    file.write_text("<error>HTTP 500</error>", encoding="utf-8")
    assert original_identifiers(file) == {}


def test_bmap_source_corrected_without_approving_aggregate():
    folder = ROOT / "03_experiments/audits/mic_evidence_repair_20261003_v1"
    sources = pd.read_csv(folder / "source_identifier_review.csv", keep_default_na=False)
    row = sources[sources.source_id.eq("bmap2025")].iloc[0]
    assert row.doi == "10.1002/mlf2.70020" and str(row.pmid) == "40600060"
    assays = pd.read_csv(folder / "assay_evidence_review.csv", keep_default_na=False)
    row = assays[assays.record_id.eq("bmap2025:BMAP-27B")].iloc[0]
    assert row.decision == "withheld_aggregate_target_endpoint" and row.approved_label == ""
    assert str(row.reported_mic) == "1.563-6.250"


def test_record_id_does_not_generate_labels(tmp_path, monkeypatch):
    folder = ROOT / "03_experiments/audits/dramp_dual_task_primary_audit_20261003_v1"
    dev = ROOT / "02_code/data/sources/combined_v3_evidence_clean_20261001/records.csv"
    # Patch only read data in memory; the published database snapshot is not modified.
    read = pd.read_csv
    def candidate(path, *args, **kwargs):
        rows = read(path, *args, **kwargs)
        row = rows[rows.dramp_id.eq("DRAMP20968")].copy()
        row.loc[:, "max_identity_to_dev"] = 0.99
        return row
    monkeypatch.setattr(pd, "read_csv", candidate)
    out = tmp_path / "external-review"
    result = curate_dual_task_evidence(folder / "candidate_primary_audit.csv", dev, out)
    assert result["eligible_verified_count"] == 0
    values = read(out / "curated_candidate_evaluations.csv")
    assert values[["mic_ug_ml", "hc50_ug_ml", "amp_label", "hemo_label"]].isna().all().all()


def test_external_output_immutable(tmp_path):
    with pytest.raises(FileExistsError):
        curate_dual_task_evidence(tmp_path / "unused.csv", tmp_path / "unused-dev.csv", tmp_path)


def test_esm_existing_output_rejected_before_model_loading(tmp_path, monkeypatch):
    import extract_mic_esm2_features as extractor
    def fail():
        raise AssertionError("No checkpoint loading during immutable-output verification")
    monkeypatch.setattr(extractor.esm.pretrained, "esm2_t6_8M_UR50D", fail)
    with pytest.raises(FileExistsError):
        extractor.extract_features(tmp_path / "unused.csv", tmp_path)


def test_state_does_not_inherit_old_training_protocol():
    state = read_json(status.DEFAULT_STATE)
    assert state["training_protocol_id"] is None
    assert state["gates"]["training_protocol"]["protocol_id"] is None
    assert state["training_command"] is None and state["training_blocked"]
    assert state["records_released_for_training"] == 0 and state["historical_training_completed"]


def test_machine_state_semantic_conflict_rejected():
    state = read_json(status.DEFAULT_STATE)
    state["gates"]["training_protocol"]["protocol_id"] = "protocol-mic-09"
    with pytest.raises(ValueError, match="Inconsistent current research state"):
        status.render_current_status(state)


def test_all_current_documents_agree():
    from publish_mic_followup_status import current_state_path, validate_documents
    validate_documents(read_json(current_state_path()))


def test_document_fact_change_rejected(tmp_path, monkeypatch):
    state = read_json(status.DEFAULT_STATE)
    file = tmp_path / "status.md"
    file.write_text(status.render_current_status(state).replace("训练命令：`null`", "训练命令：`run`"), encoding="utf-8")
    monkeypatch.setattr(status, "ROOT", tmp_path)
    monkeypatch.setattr(status, "DOCS", ("status.md",))
    with pytest.raises(ValueError, match="facts differ"):
        status.validate_documents(state)


def test_historical_materials_unchanged():
    assert len(verify_original_materials()["protected_files"]) == 99
