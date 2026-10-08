"""Unit tests for Clinical Kinase & Resistant Mutants Knowledge Hub and 3D pocket service."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from target_knowledge_hub import (
    get_all_clinical_targets,
    get_clinical_target_by_symbol,
    fetch_uniprot_chembl_enrichment,
    CLINICAL_KINASE_REGISTRY
)
from kinase_pocket_structure_service import get_kinase_pocket_3d


def test_target_registry_volume():
    """Verify registry contains 50+ high-quality clinical oncology kinase targets & mutants."""
    all_targets = get_all_clinical_targets()
    assert len(all_targets) >= 50, f"Expected >= 50 targets, got {len(all_targets)}"
    
    # Check balance of wildtype vs mutants
    mutants = [t for t in all_targets if t["is_mutant"]]
    wildtypes = [t for t in all_targets if not t["is_mutant"]]
    assert len(mutants) >= 15, f"Expected >= 15 resistance mutants, got {len(mutants)}"
    assert len(wildtypes) >= 30, f"Expected >= 30 wildtype targets, got {len(wildtypes)}"


def test_core_resistance_mutants_fields():
    """Verify key clinical resistance mutants have accurate gatekeeper and mutation descriptions."""
    # 1. EGFR-T790M Gatekeeper
    egfr_t790m = get_clinical_target_by_symbol("EGFR-T790M")
    assert egfr_t790m is not None
    assert egfr_t790m["is_mutant"] is True
    assert egfr_t790m["gatekeeper_residue"] == "Met790"
    assert egfr_t790m["pdb_code"] == "2JIT"
    assert "奥希替尼" in "".join(egfr_t790m["approved_drugs"])

    # 2. ABL1-T315I Gatekeeper
    abl1_t315i = get_clinical_target_by_symbol("ABL1-T315I")
    assert abl1_t315i is not None
    assert abl1_t315i["gatekeeper_residue"] == "Ile315"
    assert abl1_t315i["pdb_code"] == "2V7T"
    assert "普纳替尼" in "".join(abl1_t315i["approved_drugs"])

    # 3. BTK-C481S Covalent Loss
    btk_c481s = get_clinical_target_by_symbol("BTK-C481S")
    assert btk_c481s is not None
    assert btk_c481s["mutation_type"] == "Covalent Site"
    assert btk_c481s["pdb_code"] == "6O8I"
    assert "吡妥布替尼" in "".join(btk_c481s["approved_drugs"])

    # 4. BRAF-V600E Activation Loop
    braf_v600e = get_clinical_target_by_symbol("BRAF-V600E")
    assert braf_v600e is not None
    assert braf_v600e["pdb_code"] == "4MBJ"
    assert "维莫非尼" in "".join(braf_v600e["approved_drugs"])


def test_target_catalog_filtering():
    """Verify catalog filtering by family, mutant status, and search query."""
    # Filter TK family
    tk_targets = get_all_clinical_targets(family="TK")
    assert len(tk_targets) > 20
    assert all(t["family"] == "TK" for t in tk_targets)

    # Search for "肺癌"
    lung_targets = get_all_clinical_targets(search_query="肺癌")
    assert len(lung_targets) >= 5
    symbols = [t["symbol"] for t in lung_targets]
    assert any("EGFR" in s for s in symbols)
    assert any("ALK" in s for s in symbols)


def test_uniprot_chembl_enrichment():
    """Verify UniProt & ChEMBL cross references."""
    enrichment = fetch_uniprot_chembl_enrichment(uniprot_id="P00533", chembl_id="CHEMBL203")
    assert enrichment["uniprot_id"] == "P00533"
    assert "uniprot.org" in enrichment["database_cross_references"]["uniprot_url"]
    assert "chembl" in enrichment["database_cross_references"]["chembl_target_url"]


def test_kinase_pocket_3d_integration():
    """Verify get_kinase_pocket_3d integrates with the 60+ target knowledge base."""
    # Check HER2
    her2_pocket = get_kinase_pocket_3d(target_name="HER2", drug_name="Tucatinib")
    assert her2_pocket["pdb_code"] == "3RCD"
    assert her2_pocket["hinge_residue"] == "Met801"
    assert her2_pocket["gatekeeper_residue"] == "Thr798"
    assert "ATOM" in her2_pocket["pdb_content"]

    # Check EGFR-T790M mutant
    t790m_pocket = get_kinase_pocket_3d(target_name="EGFR-T790M", drug_name="Osimertinib")
    assert t790m_pocket["pdb_code"] == "2JIT"
    assert t790m_pocket["is_mutant"] is True
    assert t790m_pocket["gatekeeper_residue"] == "Met790"
    # Verify MET sidechain atoms in PDB
    assert "SD  MET A 315" in t790m_pocket["pdb_content"]


def test_fastapi_clinical_endpoints():
    """Verify FastAPI routes for clinical targets and enrichment lookup."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_web_server"))
    from dti_endpoints import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # 1. GET /api/dti/clinical_targets
    res1 = client.get("/api/dti/clinical_targets")
    assert res1.status_code == 200
    targets = res1.json()
    assert len(targets) >= 50

    # 2. GET /api/dti/clinical_target/EGFR-T790M
    res2 = client.get("/api/dti/clinical_target/EGFR-T790M")
    assert res2.status_code == 200
    detail = res2.json()
    assert detail["symbol"] == "EGFR-T790M"
    assert "enrichment" in detail
    assert "uniprot.org" in detail["enrichment"]["database_cross_references"]["uniprot_url"]

    # 3. POST /api/dti/search_targets
    res3 = client.post("/api/dti/search_targets", json={"query": "奥希替尼"})
    assert res3.status_code == 200
    search_data = res3.json()
    assert search_data["total_hits"] >= 1
    assert any("EGFR" in r["symbol"] for r in search_data["results"])

