"""Unit and integration tests for De Novo Pocket Molecule Generation and AI Retrosynthesis Planner."""
import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_web_server"))

from pocket_de_novo_generator import generate_de_novo_pocket_molecules, _calc_ip_novelty
from retrosynthesis_planner import plan_retrosynthesis_route
from research_api import app

client = TestClient(app)


def test_ip_novelty_calculation():
    """Verify IP novelty computation against reference FDA kinase drugs."""
    # Test identical drug (Dasatinib) -> novelty should be 0.0 or near 0.0 (sim ~ 1.0)
    dasatinib_smi = "CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO"
    novelty, nearest, sim = _calc_ip_novelty(dasatinib_smi)
    assert nearest == "Dasatinib"
    assert sim >= 0.99
    assert novelty <= 0.01

    # Test novel bioisostere candidate -> novelty should be >= 0.35
    novel_smi = "CN1CCN(CC1)C2=CC(=C(C=C2)NC(=O)C3=CN4C=CN=C4S3)C5=NC(=NC=C5)NC6=CC(=C(C=C6)F)Cl"
    novelty2, nearest2, sim2 = _calc_ip_novelty(novel_smi)
    assert 0.0 <= novelty2 <= 1.0
    assert novelty2 >= 0.30


def test_de_novo_generation_scaffold_hopping():
    """Test pocket-conditioned generation in scaffold hopping mode."""
    res = generate_de_novo_pocket_molecules(
        target_symbol="ABL1",
        generation_mode="scaffold_hopping",
        num_candidates=4
    )
    assert res["status"] == "success"
    assert res["target_symbol"] == "ABL1"
    assert res["total_generated"] >= 4
    
    first = res["candidates"][0]
    assert "candidate_id" in first
    assert first["molecular_weight"] > 200
    assert first["predicted_pkd"] > 5.0
    assert first["delta_g_bind_kcal"] < 0  # Favorable binding free energy
    assert first["sa_score"] > 0
    assert "key_interactions_predicted" in first
    assert len(first["key_interactions_predicted"]) >= 2


def test_de_novo_generation_gatekeeper_mutant():
    """Test auto-steered generation on gatekeeper resistant kinase (ABL1-T315I)."""
    res = generate_de_novo_pocket_molecules(
        target_symbol="ABL1-T315I",
        generation_mode="scaffold_hopping", # Should auto-switch or handle gatekeeper
        num_candidates=4
    )
    assert res["status"] == "success"
    assert res["is_mutant_target"] is True
    assert "ILE" in res["gatekeeper_residue"].upper()
    assert res["generation_mode"] == "gatekeeper_bypasser"
    assert len(res["candidates"]) >= 4


def test_retrosynthesis_planner_alkyne_route():
    """Test CA-retrosynthesis planning for alkyne-bridged gatekeeper inhibitor."""
    test_smi = "CC1=C(C=C(C=C1)C#CC2=CN=CC=C2)C(=O)NC3=CC(=C(C=C3)CN4CCN(CC4)CCO)C(F)(F)F"
    route = plan_retrosynthesis_route(test_smi, molecule_name="Ponatinib-Analog-GK")
    
    assert route["target_molecule_name"] == "Ponatinib-Analog-GK"
    assert route["total_steps"] >= 3
    assert len(route["commercial_precursors"]) >= 2
    assert any("2510-22-7" in p["cas_number"] for p in route["commercial_precursors"])
    
    # Check steps
    assert any("Sonogashira" in step["reaction_type"] for step in route["synthesis_steps"])
    assert any("Amide" in step["reaction_type"] for step in route["synthesis_steps"])
    assert route["cumulative_yield_percent"] > 0


def test_retrosynthesis_planner_snar_route():
    """Test CA-retrosynthesis planning for quinazoline / ether-linked inhibitor."""
    test_smi = "COC1=C(C=C2C(=C1)N=CN=C2NC3=CC(=CC(=C3)C#C)Cl)OCC4=CC=CC=N4"
    route = plan_retrosynthesis_route(test_smi, molecule_name="Gefitinib-Analog-Hop")
    
    assert route["total_steps"] >= 2
    assert len(route["commercial_precursors"]) >= 2
    assert any("SNAr" in step["reaction_type"] or "Etherification" in step["reaction_type"] for step in route["synthesis_steps"])


def test_fastapi_de_novo_and_retrosynthesis_endpoints():
    """Test full integration via FastAPI endpoints."""
    # 1. De novo generate endpoint
    resp_gen = client.post("/api/dti/de_novo_generate", json={
        "target_symbol": "EGFR-T790M",
        "generation_mode": "gatekeeper_bypasser",
        "num_candidates": 3,
        "novelty_floor": 0.30
    })
    assert resp_gen.status_code == 200
    gen_data = resp_gen.json()
    assert gen_data["status"] == "success"
    assert len(gen_data["candidates"]) == 3
    cand_smi = gen_data["candidates"][0]["smiles"]
    cand_name = gen_data["candidates"][0]["name"]

    # 2. Retrosynthesis plan endpoint using generated molecule
    resp_retro = client.post("/api/dti/retrosynthesis_plan", json={
        "smiles": cand_smi,
        "molecule_name": cand_name
    })
    assert resp_retro.status_code == 200
    retro_data = resp_retro.json()
    assert retro_data["total_steps"] >= 2
    assert len(retro_data["commercial_precursors"]) >= 1
    assert len(retro_data["synthesis_steps"]) >= 2
