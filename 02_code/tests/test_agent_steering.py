"""Tests for A2A Agent Steering, Hard Constraints, and Interactive Controls (P3 Milestone)."""
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

from agent_constraints import (
    AgentHardConstraints, 
    UnsupportedConstraintError, 
    InvalidConstraintUpdateError
)
from agent_orchestrator import MultiAgentOrchestrator, CandidateRecord
from research_api import app
from agent_endpoints import active_sessions

client = TestClient(app)


def test_hard_constraints_validation_logic():
    """Verify code-level hard constraint checks on real molecules."""
    # Dasatinib ~ 488.0 Da, contains Cl
    dasatinib_smi = "Cc1nc(sc1C(=O)Nc2c(cccc2Cl)C)Nc3cc(nc(n3)N4CCN(CC4)CCO)Cl"
    # Aspirin ~ 180.1 Da
    aspirin_smi = "CC(=O)Oc1ccccc1C(=O)O"

    # Test 1: Molecular Weight limit
    c_mw = AgentHardConstraints(version=1, max_mw=300.0)
    passed, reason = c_mw.validate_candidate(dasatinib_smi)
    assert passed is False
    assert "分子量超出硬约束上限" in reason

    passed_asp, _ = c_mw.validate_candidate(aspirin_smi)
    assert passed_asp is True

    # Test 2: Must contain motif (e.g. Alkyne C#C)
    c_alkyne = AgentHardConstraints(version=1, must_contain_motif="C#C")
    passed_no_alkyne, reason_no_alkyne = c_alkyne.validate_candidate(dasatinib_smi)
    assert passed_no_alkyne is False
    assert "未包含必需结构片段" in reason_no_alkyne

    ponatinib_smi = "CC1=C(C=C(C=C1)C#CC2=CN=CC=C2)C(=O)NC3=CC(=C(C=C3)CN4CCN(CC4)C)C(F)(F)F"
    passed_pon, _ = c_alkyne.validate_candidate(ponatinib_smi)
    assert passed_pon is True

    # Test 3: Forbidden motifs
    c_no_cl = AgentHardConstraints(version=1, forbidden_motifs=["Cl"])
    passed_cl, reason_cl = c_no_cl.validate_candidate(dasatinib_smi)
    assert passed_cl is False
    assert "包含禁用结构基团" in reason_cl


def test_rejection_of_unsupported_constraints():
    """Unsupported constraint keys must be strictly rejected with UnsupportedConstraintError."""
    with pytest.raises(UnsupportedConstraintError) as exc_info:
        AgentHardConstraints.from_dict({
            "make_it_selective": True,
            "prompt_soft_bias": "make it look like imatinib"
        })
    assert "以下约束不受硬编码验证器支持" in str(exc_info.value)


def test_steering_state_transitions_and_versioning():
    """Test pause, versioned constraint updating, and resume lifecycle."""
    orch = MultiAgentOrchestrator(initial_constraints=AgentHardConstraints(version=1, max_mw=600.0))
    assert orch.constraints.version == 1

    # Attempting to update constraints while NOT paused must raise InvalidConstraintUpdateError
    with pytest.raises(InvalidConstraintUpdateError) as exc_info:
        orch.update_constraints({"max_mw": 500.0}, expected_version=1)
    assert "只能在流水线处于已确认暂停状态下更新硬约束" in str(exc_info.value)

    # Now request pause and simulate confirmed pause
    orch.pause()
    orch.is_paused = True

    # Attempting update with wrong version must raise error
    with pytest.raises(InvalidConstraintUpdateError) as exc_ver:
        orch.update_constraints({"max_mw": 500.0}, expected_version=99)
    assert "约束版本冲突" in str(exc_ver.value)

    # Valid update with matching version
    updated = orch.update_constraints({"max_mw": 450.0, "must_contain_motif": "C#C"}, expected_version=1)
    assert updated.version == 2
    assert orch.constraints.max_mw == 450.0
    assert orch.constraints.must_contain_motif == "C#C"

    # Resume
    orch.resume()
    assert orch.is_paused is False
    assert orch.pause_requested is False


def test_parent_fallback_on_stricter_constraints():
    """When new constraints invalidate current_best, orchestrator falls back to a compliant parent."""
    orch = MultiAgentOrchestrator(initial_constraints=AgentHardConstraints(version=1))
    
    # Setup mock candidates in state:
    # Candidate A: MW ~ 532 (Ponatinib), pKd = 9.0
    ponatinib_smi = "CC1=C(C=C(C=C1)C#CC2=CN=CC=C2)C(=O)NC3=CC(=C(C=C3)CN4CCN(CC4)C)C(F)(F)F"
    # Candidate B: MW ~ 180 (Aspirin-like), pKd = 7.0
    aspirin_smi = "CC(=O)Oc1ccccc1C(=O)O"

    cand_a = {
        "id": "CAND_A",
        "smiles": ponatinib_smi,
        "predicted_pkd": 9.0,
        "hemolysis_risk_pct": 2.0,
        "sa_score": 3.0,
        "passed_hard_constraints": True,
        "admet_score": 80.0
    }
    cand_b = {
        "id": "CAND_B",
        "smiles": aspirin_smi,
        "predicted_pkd": 7.0,
        "hemolysis_risk_pct": 1.0,
        "sa_score": 2.0,
        "passed_hard_constraints": True,
        "admet_score": 85.0
    }

    orch.current_state = {
        "current_best": cand_a,
        "candidates": [cand_b, cand_a],
        "is_converged": False,
        "iteration": 2
    }

    # Pause and impose strict MW <= 300 (which invalidates CAND_A)
    orch.pause()
    orch.is_paused = True

    orch.update_constraints({"max_mw": 300.0}, expected_version=1)
    # The current_best should fall back to CAND_B!
    assert orch.current_state["current_best"]["id"] == "CAND_B"


def test_steering_endpoints_via_testclient():
    """Test steering API endpoints (/pause, /constraints, /resume, /cancel)."""
    task_id = "test_steer_task_001"
    orch = MultiAgentOrchestrator(initial_constraints=AgentHardConstraints(version=1))
    active_sessions[task_id] = orch

    try:
        # 1. Pause
        pause_resp = client.post(f"/api/agent/{task_id}/pause")
        assert pause_resp.status_code == 200
        assert orch.pause_requested is True
        orch.is_paused = True  # simulate engine loop confirming pause

        # 2. Get constraints
        get_c = client.get(f"/api/agent/{task_id}/constraints")
        assert get_c.status_code == 200
        assert get_c.json()["version"] == 1

        # 3. Update constraints
        up_resp = client.post(
            f"/api/agent/{task_id}/constraints",
            json={"constraints": {"max_mw": 480.0, "min_predicted_pkd": 7.5}, "expected_version": 1}
        )
        assert up_resp.status_code == 200
        assert up_resp.json()["version"] == 2
        assert orch.constraints.max_mw == 480.0

        # 4. Resume
        resume_resp = client.post(f"/api/agent/{task_id}/resume")
        assert resume_resp.status_code == 200
        assert orch.is_paused is False

        # 5. Cancel
        cancel_resp = client.post(f"/api/agent/{task_id}/cancel")
        assert cancel_resp.status_code == 200
        assert orch.cancellation_requested is True

    finally:
        active_sessions.pop(task_id, None)
