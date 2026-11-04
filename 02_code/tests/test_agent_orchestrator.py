"""Unit tests for Antigravity A2A Multi-Agent Orchestrator."""
import asyncio
import json
import pytest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_code"))

from agent_orchestrator import MultiAgentOrchestrator, AgentState, utc_now_iso


IMATINIB = "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5"
ABL1_SEQ = "MLEICLKLVGCKSKKGLSSSSSCYLEEALQRPVASDFEPQGLSEAARWNSKENLLAGPSENDPNLFVALYDFVASGDNTLSITKGEKLRVLGYNHNGEWCEAQTKNGQGWVPSNYITPVNSLEKHSWYHGPVSRNAAEYLLSSGINGSFLVRESESSPGQRSISLRYEGRVYHYRINTASDGKLYVSSESRFNTLAELVHHHSTVADGLITTLHYPAPKRNKPTI"


@pytest.fixture
def orchestrator():
    return MultiAgentOrchestrator()


def test_orchestrator_evaluate_molecule(orchestrator):
    record = orchestrator.evaluate_molecule(
        smiles=IMATINIB,
        target_sequence=ABL1_SEQ,
        target_symbol="ABL1",
        gen=0,
        modifications="Baseline",
        rationale="Initial check"
    )
    assert record["id"].startswith("GEN0_")
    assert record["smiles"] == IMATINIB
    assert record["target_symbol"] == "ABL1"
    assert record["predicted_pkd"] >= 5.0
    assert record["admet_score"] >= 0.0
    assert record["sa_score"] >= 1.0
    assert record["hemolysis_risk_pct"] >= 0.0


@pytest.mark.asyncio
async def test_run_pipeline_stream(orchestrator):
    state: AgentState = {
        "task_id": "test_task_001",
        "scenario": "kinase_escape",
        "user_goal": "Optimize Imatinib against ABL1",
        "target_symbol": "ABL1",
        "target_sequence": ABL1_SEQ,
        "baseline_smiles": IMATINIB,
        "current_agent": "supervisor",
        "iteration": 0,
        "max_iterations": 2,
        "target_pkd": 9.5,
        "min_admet_score": 60.0,
        "max_hemolysis_pct": 10.0,
        "candidates": [],
        "current_best": None,
        "pareto_frontier": [],
        "step_count": 0,
        "is_converged": False,
        "final_verdict": None
    }

    events = []
    async for raw_event in orchestrator.run_pipeline_stream(state):
        assert raw_event.startswith("event: ")
        lines = raw_event.strip().split("\n")
        event_name = lines[0].replace("event: ", "")
        data = json.loads(lines[1].replace("data: ", ""))
        events.append((event_name, data))

    event_names = [e[0] for e in events]
    assert "init" in event_names
    assert "agent_thought" in event_names
    assert "candidate_evaluated" in event_names
    assert "finished" in event_names

    # Check finished payload
    final_data = [e[1] for e in events if e[0] == "finished"][0]
    assert "verdict" in final_data
    assert final_data["verdict"]["total_iterations"] <= 2
    assert final_data["verdict"]["best_molecule"] is not None
