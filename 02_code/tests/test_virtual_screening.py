"""Unit and integration tests for Ultra-Large Scale Virtual Screening Engine."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_web_server"))

from virtual_screening_engine import (
    get_screening_libraries_metadata,
    screen_virtual_library,
    butina_cluster_compounds,
    PRESET_SCREENING_LIBRARIES
)


def test_screening_libraries_metadata():
    """Verify built-in screening libraries metadata and availability."""
    libs = get_screening_libraries_metadata()
    assert len(libs) >= 3
    lib_ids = [l["id"] for l in libs]
    assert "enamine_diversity" in lib_ids
    assert "kinase_privileged" in lib_ids
    assert "fda_approved_derivatives" in lib_ids

    # Check each library has valid descriptors
    for l in libs:
        assert l["total_compounds"] > 0
        assert l["average_mw"] > 150
        assert len(l["vendor_source"]) > 0


def test_butina_clustering_diversity():
    """Verify Butina clustering groups molecules and identifies cluster representatives."""
    test_smiles = [
        # Cluster A: Dasatinib-like aminothiazole
        "CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO",
        "CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)C",
        "CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCOCC4",
        # Cluster B: Ponatinib-like alkyne
        "CC1=C(C=C(C=C1)C#CC2=CN=CC=C2)C(=O)NC3=CC(=C(C=C3)CN4CCN(CC4)C)C(F)(F)F",
        "CC1=C(C=C(C=C1)C#CC2=CN=CC=C2)C(=O)NC3=CC(=C(C=C3)CN4CCN(CC4)CCO)C(F)(F)F",
        # Cluster C: Gefitinib-like quinazoline
        "COC1=C(C=C2C(=C1)N=CN=C2NC3=CC(=C(C=C3)F)Cl)OCCCN4CCOCC4",
        "COC1=C(C=C2C(=C1)N=CN=C2NC3=CC=CC(=C3)C#C)OCCOC"
    ]
    
    clusters, representatives = butina_cluster_compounds(test_smiles, cutoff=0.40)
    assert len(clusters) >= 2
    # Total assigned items equals input items
    total_assigned = sum(len(c) for c in clusters)
    assert total_assigned == len(test_smiles)
    # Each cluster has 1 representative
    assert len(representatives) == len(clusters)


def test_virtual_screening_wildtype_kinase():
    """Test virtual screening execution on wildtype kinase (EGFR)."""
    res = screen_virtual_library(
        target_symbol="EGFR",
        library_id="kinase_privileged",
        max_hits=10,
        min_pkd_threshold=5.0
    )
    assert res["status"] == "success"
    assert res["target_symbol"] == "EGFR"
    assert res["total_screened"] >= 10
    assert res["total_hits"] > 0
    assert len(res["hits"]) <= 10
    
    top_hit = res["hits"][0]
    assert "compound_id" in top_hit
    assert "smiles" in top_hit
    assert top_hit["predicted_pkd"] >= 5.0
    assert top_hit["delta_g_bind_kcal"] < 0
    assert top_hit["sa_score"] > 0
    assert "cluster_id" in top_hit
    assert "is_cluster_representative" in top_hit


def test_virtual_screening_gatekeeper_mutant():
    """Test virtual screening on gatekeeper resistant kinase (ABL1-T315I)."""
    res = screen_virtual_library(
        target_symbol="ABL1-T315I",
        library_id="kinase_privileged",
        max_hits=10
    )
    assert res["status"] == "success"
    assert res["total_hits"] > 0
    # Top hits for T315I should prioritize molecules capable of circumventing steric gatekeeper
    hit_smiles = [h["smiles"] for h in res["hits"]]
    # Should identify at least one alkyne or bypass motif
    has_bypass = any("C#C" in s or "CF3" in s or "C(F)(F)F" in s for s in hit_smiles)
    assert has_bypass is True


def test_virtual_screening_custom_smiles_list():
    """Test virtual screening on user-provided custom SMILES dataset."""
    custom_list = [
        {"id": "CUSTOM-01", "name": "Custom Imidazopyrazine", "smiles": "CN1CCN(CC1)C2=CC(=C(C=C2)NC(=O)C3=CN4C=CN=C4S3)C5=NC(=NC=C5)NC6=CC(=C(C=C6)F)Cl"},
        {"id": "CUSTOM-02", "name": "Custom Ethynyl Pyridine", "smiles": "CC1=C(C=C(C=C1)C#CC2=CN=CC=C2)C(=O)NC3=CC(=C(C=C3)CN4CCN(CC4)CCO)C(F)(F)F"},
        {"id": "CUSTOM-03", "name": "Custom Quinazoline", "smiles": "COC1=C(C=C2C(=C1)N=CN=C2NC3=CC(=C(C=C3)F)Cl)OCCCN4CCOCC4"}
    ]
    
    res = screen_virtual_library(
        target_symbol="ABL1",
        custom_compounds=custom_list,
        max_hits=5
    )
    assert res["status"] == "success"
    assert res["total_screened"] == 3
    assert len(res["hits"]) == 3


def test_fastapi_virtual_screening_endpoints():
    """Test virtual screening API endpoints via FastAPI test client."""
    from fastapi.testclient import TestClient
    from research_api import app

    client = TestClient(app)

    # 1. GET /api/dti/screening_libraries
    resp_libs = client.get("/api/dti/screening_libraries")
    assert resp_libs.status_code == 200
    libs_data = resp_libs.json()
    assert len(libs_data) >= 3
    assert any(l["id"] == "kinase_privileged" for l in libs_data)

    # 2. POST /api/dti/virtual_screen
    resp_screen = client.post("/api/dti/virtual_screen", json={
        "target_symbol": "BRAF-V600E",
        "library_id": "kinase_privileged",
        "max_hits": 8,
        "min_pkd_threshold": 5.0
    })
    assert resp_screen.status_code == 200
    screen_data = resp_screen.json()
    assert screen_data["status"] == "success"
    assert screen_data["target_symbol"] == "BRAF-V600E"
    assert screen_data["total_hits"] > 0
    assert len(screen_data["hits"]) <= 8

