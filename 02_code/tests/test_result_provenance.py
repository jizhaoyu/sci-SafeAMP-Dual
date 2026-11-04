"""Tests for Result Provenance and Fact Grounding (P0 Milestone).

Verifies:
1. Integrity of frozen baselines, protocols, and model manifests.
2. Failure paths in virtual screening: exceptions do NOT produce hash(smiles) surrogate pKd.
3. Separation of heuristic bonuses from raw model predictions.
4. Marking of unverified structural interactions as design hypotheses.
5. Academic reports with missing inputs do NOT fabricate default MM-GBSA values.
6. Multi-agent ADMET and hemolysis estimations are marked as heuristics.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import pytest
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_code"))

import virtual_screening_engine as vse
from dti_report_generator import generate_dti_academic_report
from agent_orchestrator import MultiAgentOrchestrator


def test_frozen_baselines_integrity():
    """Verify that all frozen benchmark protocols, datasets, and manifests have intact SHA256 hashes."""
    snapshot_path = ROOT / "output/system-evolution-20261021/P0/frozen_baselines_sha256.json"
    assert snapshot_path.exists(), "Snapshot of frozen baselines must exist in output/system-evolution-20261021/P0/"

    with open(snapshot_path, "r", encoding="utf-8") as f:
        recorded_hashes = json.load(f)

    for rel_path, meta in recorded_hashes.items():
        if "error" in meta:
            continue
        p = ROOT / rel_path
        assert p.exists(), f"Protected file {rel_path} is missing"
        actual_hash = hashlib.sha256(p.read_bytes()).hexdigest()
        assert actual_hash == meta["sha256"], f"Hash mismatch for protected baseline file {rel_path}!"


def test_virtual_screening_failure_handling_no_hash_fallback(monkeypatch):
    """When model prediction throws an exception, no surrogate pKd via hash(smiles) is generated."""
    # Force runtime.predict to fail
    class FailingRuntime:
        def predict(self, *args, **kwargs):
            raise RuntimeError("Forced model failure for test")

    monkeypatch.setattr(vse, "_get_runtime", lambda: FailingRuntime())

    res = vse.screen_virtual_library(
        target_symbol="EGFR",
        library_id="kinase_privileged",
        max_hits=5
    )

    # When all predictions fail, there must be NO successful hits with fake scores
    assert res["status"] in ("no_valid_result", "failed")
    assert res["total_hits"] == 0
    assert len(res["hits"]) == 0
    assert res.get("failed_screened", 0) > 0
    assert len(res.get("failed_compounds", [])) > 0


def test_virtual_screening_heuristic_bonus_separated(monkeypatch):
    """Mutant heuristic bonus (e.g. +0.6 for C#C on T315I) must be kept separate from raw predicted_pkd."""
    raw_pkd_expected = 6.20

    class MockRuntime:
        def predict(self, drug_smiles, target_sequence, model_name=None):
            return {
                "predicted_pkd": raw_pkd_expected,
                "predicted_kd_nM": 630.96,
                "confidence_band": "High"
            }

    monkeypatch.setattr(vse, "_get_runtime", lambda: MockRuntime())

    # Compound with alkyne C#C
    custom_compounds = [
        {"id": "TEST-ALK-1", "name": "Alkyne Compound", "smiles": "CC1=C(C=C(C=C1)C#CC2=CN=CC=C2)C(=O)NC3=CC=CC=C3"}
    ]

    res = vse.screen_virtual_library(
        target_symbol="ABL1-T315I",
        custom_compounds=custom_compounds,
        max_hits=5
    )

    assert res["status"] == "success"
    assert len(res["hits"]) == 1
    hit = res["hits"][0]

    # Raw predicted_pkd MUST be 6.20, not 6.80!
    assert hit["predicted_pkd"] == raw_pkd_expected
    # Heuristic adjustment must be recorded separately
    assert hit.get("heuristic_adjustment") == 0.6
    assert hit.get("heuristic_adjusted_pkd") == 6.80
    assert "provenance" in hit
    assert hit["provenance"] == "model_prediction"


def test_virtual_screening_hypotheses_provenance():
    """Key interactions must be clearly labeled as hypotheses, not verified crystallography facts."""
    res = vse.screen_virtual_library(
        target_symbol="ABL1",
        library_id="kinase_privileged",
        max_hits=3
    )

    if res["hits"]:
        hit = res["hits"][0]
        assert "key_interactions_provenance" in hit
        assert hit["key_interactions_provenance"] == "design_hypothesis"
        for item in hit["key_interactions"]:
            assert "假说" in item or "推测" in item or "hypothesis" in item.lower()


def test_report_generator_missing_inputs_no_default_values():
    """When biophysics is None, report must NOT generate default fake MM-GBSA values."""
    baseline = {
        "name": "Dasatinib",
        "smiles": "CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO",
        "predicted_pkd": 7.41,
        "predicted_kd_nM": 38.9
    }
    candidates = [
        {
            "name": "Candidate-01",
            "smiles": "CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCF",
            "predicted_pkd": 7.80,
            "predicted_kd_nM": 15.8,
            "delta_pkd": 0.39,
            "sa_score": 3.2
        }
    ]

    # Generate report with NO biophysics and NO admet
    rep = generate_dti_academic_report(
        target_name="ABL1",
        baseline=baseline,
        candidates=candidates,
        biophysics=None,
        admet=None
    )

    md = rep["markdown_report"]
    html = rep["html_report"]

    # Must NOT contain default fake numbers: -45.0, -18.0, 28.0, 16.0
    assert "-45.00" not in md and "-45.0" not in md
    assert "-18.00" not in md and "-18.0" not in md
    assert "Uni-Mol 3D" not in md
    assert "Uni-Mol 3D" not in html

    # Must explicitly state that biophysics is uncomputed or missing
    assert "未提供 3D 生物物理" in md or "未计算" in md or "缺失" in md
    assert "未提供 3D 生物物理" in html or "未计算" in html or "缺失" in html


def test_agent_orchestrator_hemolysis_heuristic_provenance():
    """Verify that agent orchestrator marks hemolysis as heuristic and candidate ranking appropriately."""
    orch = MultiAgentOrchestrator()
    record = orch.evaluate_molecule(
        smiles="CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5",
        target_sequence="MVLLEEQRVVIGEGTYGVVYKARNKLTGEVVALKKIRLDTETEGVPSTAIREISLLKELNHPNIVKLLDVIHTENKLYLVFEFLHQDLKKFMDASALTGIPLPLIKSYLFQLLQGLAFCHSHRVLHRDLKPQNLLINTEGAIKLADFGLARAFGVPVRTYTHEVVTLWYRAPEILLGCKYYSTAVDIWSLGCIFAEMVTRRALFPGDSEIDQLFRIFRTLGTPDEVVWPGVTSMPDYKPSFPKWARQDFSKVVPPLDEDGRSLLSQMLHYDPNKRISAKAALAHPFFQDVTKPVPHLRL",
        target_symbol="ABL1",
        gen=0
    )

    assert "hemolysis_provenance" in record
    assert record["hemolysis_provenance"] == "heuristic_estimate"
    assert "hemolysis_note" in record
