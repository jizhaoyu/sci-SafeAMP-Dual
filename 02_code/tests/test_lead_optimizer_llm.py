"""Unit and integration tests for Auditable LLM Lead Optimizer (P4 Milestone)."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = PROJECT_ROOT / "05_web_server"
CODE_DIR = PROJECT_ROOT / "02_code"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from dti_lead_optimizer import DTILeadOptimizer, generate_heuristic_candidates
from dti_inference_runtime import DTIInferenceRuntime
from research_api import app

client = TestClient(app)

IMATINIB_SMILES = "Cc1ccc(cc1Nc2nccc(n2)c3cccnc3)NC(=O)c4ccc(cc4)CN5CCN(CC5)C"
ABL1_SEQUENCE = (
    "MLEICLKLVGCKSKKGLSSSSSCYLEEALQRPVASDFEPQGLSEAARWNSKENLLAGPSENDPNLFVALYDFVASGDNTLSITKGEKLRVLGYNHNGEWCEAQTKNGQGWVPSNYITPVNS"
    "LEKHSWYHGPVSRNAAEYLLSSGINGSFLVRESESSPGQRSISLRYEGRVYHYRINTASDGKLYVSSESRFNTLAELVHHHSTVADGLITTLHYPAPKRNKPTI"
)


@pytest.fixture(scope="module")
def runtime():
    rt = DTIInferenceRuntime()
    rt.load()
    return rt


def test_heuristic_mode_generation_and_audit_metrics(runtime):
    """Verify heuristic mode generates valid candidates, tags sources, and produces audit metrics."""
    optimizer = DTILeadOptimizer(runtime)
    res = optimizer.optimize(
        drug_smiles=IMATINIB_SMILES,
        target_sequence=ABL1_SEQUENCE,
        target_name="ABL1",
        generation_mode="heuristic"
    )

    assert res["mode"] == "heuristic_medchem_rules"
    assert res["fallback_reason"] is None
    assert len(res["candidates"]) >= 4

    for cand in res["candidates"]:
        assert cand["source"] == "heuristic_rule"
        assert "scaffold_type" in cand
        assert "parent_similarity" in cand
        assert cand["predicted_pkd"] >= 5.0

    audit = res["audit_metrics"]
    assert audit["total_candidates_evaluated"] == len(res["candidates"])
    assert audit["validity_rate"] == 1.0
    assert audit["scaffold_retention_count"] + audit["scaffold_hopping_count"] == len(res["candidates"])
    assert "mean_pairwise_diversity" in audit


def test_llm_mode_fallback_when_unconfigured(runtime):
    """When LLM API Key is absent, system must gracefully fall back to heuristic rules with clear notice."""
    optimizer = DTILeadOptimizer(runtime)
    res = optimizer.optimize(
        drug_smiles=IMATINIB_SMILES,
        target_sequence=ABL1_SEQUENCE,
        target_name="ABL1",
        generation_mode="llm",
        llm_config={}  # Empty config without key
    )

    assert res["mode"] == "heuristic_fallback"
    assert "未配置大模型 API Key" in res["fallback_reason"]
    assert len(res["candidates"]) >= 4
    assert res["candidates"][0]["source"] == "heuristic_rule"


def test_llm_mode_fallback_on_network_error(runtime, monkeypatch):
    """When LLM API throws network/server exception, system falls back to rules without crashing."""
    import urllib.request

    def mock_urlopen(*args, **kwargs):
        raise urllib.error.URLError("Connection refused for test")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    optimizer = DTILeadOptimizer(runtime)
    res = optimizer.optimize(
        drug_smiles=IMATINIB_SMILES,
        target_sequence=ABL1_SEQUENCE,
        target_name="ABL1",
        generation_mode="llm",
        llm_config={"api_key": "test_fake_key_12345"}
    )

    assert res["mode"] == "heuristic_fallback"
    assert "大模型接口调用异常" in res["fallback_reason"]
    assert len(res["candidates"]) >= 4


def test_optimize_lead_endpoint_via_testclient():
    """Verify POST /api/dti/optimize_lead endpoint works with generation_mode and returns audit_metrics."""
    payload = {
        "drug_smiles": IMATINIB_SMILES,
        "target_sequence": ABL1_SEQUENCE,
        "target_name": "ABL1",
        "optimization_goal": "提高结合强度与水溶性",
        "generation_mode": "heuristic"
    }

    resp = client.post("/api/dti/optimize_lead", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "mode" in data
    assert "audit_metrics" in data
    assert "candidates" in data
    assert len(data["candidates"]) >= 4
    assert data["audit_metrics"]["validity_rate"] == 1.0
