"""Unit tests for ADMET Predictor and Lead Optimization ADMET Integration."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_web_server"))

from admet_predictor import predict_admet_properties, ADMETResult


def test_admet_dasatinib_profile():
    dasatinib_smi = "Cc1cccc(Cl)c1NC(=O)c2cnc(s2)Nc3cc(nc(n3)N4CCNCC4)C"
    result = predict_admet_properties(dasatinib_smi)

    assert isinstance(result, ADMETResult)
    assert result.smiles == dasatinib_smi

    # Solubility (Delaney ESOL)
    assert -8.0 <= result.solubility_logs <= 0.0
    assert result.solubility_tier in ["high", "moderate", "poor"]
    assert "LogS" in result.solubility_label

    # Permeability (Caco-2)
    assert 0.0 <= result.caco2_papp <= 40.0
    assert result.caco2_tier in ["high", "moderate", "low"]

    # Blood-Brain Barrier (Clark LogBB)
    assert -3.0 <= result.log_bb <= 2.0
    assert result.bbb_tier in ["cns_penetrant", "cns_balanced", "cns_impermeant"]

    # CYP Inhibition
    assert result.cyp3a4_inhibition in ["low_risk", "moderate_risk", "high_risk"]
    assert result.cyp2d6_inhibition in ["low_risk", "moderate_risk", "high_risk"]

    # hERG Cardiac Risk
    assert 3.5 <= result.herg_pic50 <= 9.0
    assert result.herg_risk in ["low", "medium", "high"]
    assert result.herg_color in ["emerald", "amber", "rose"]

    # Health & Radar
    assert 10.0 <= result.admet_health_score <= 100.0
    for dim in ["solubility", "permeability", "herg_safety", "cyp_stability", "synthesis_sa"]:
        assert dim in result.radar_scores
        assert 0.0 <= result.radar_scores[dim] <= 100.0

    for light in ["solubility", "permeability", "herg_safety", "cyp_stability"]:
        assert light in result.traffic_lights
        assert result.traffic_lights[light] in ["green", "amber", "red"]

    d = result.to_dict()
    assert isinstance(d, dict)
    assert d["smiles"] == dasatinib_smi
    assert "admet_health_score" in d


def test_admet_empty_and_fallback():
    fallback = predict_admet_properties("")
    assert fallback.smiles == ""
    assert fallback.admet_health_score > 50.0
    assert "solubility" in fallback.radar_scores
    assert "herg_safety" in fallback.traffic_lights


def test_admet_cardiac_differential():
    # Hydrophilic carboxylate (Aspirin) -> low hERG affinity
    aspirin = "CC(=O)Oc1ccccc1C(=O)O"
    res_asp = predict_admet_properties(aspirin)
    assert res_asp.herg_risk == "low"
    assert res_asp.herg_pic50 < 5.0

    # Lipophilic molecule with basic amine center
    lipophilic_amine = "c1ccc(cc1)CCCCN2CCN(CC2)c3ccccc3"
    res_amine = predict_admet_properties(lipophilic_amine)
    assert res_amine.herg_pic50 > res_asp.herg_pic50


def test_admet_fastapi_endpoint():
    from fastapi.testclient import TestClient
    from app import app

    client = TestClient(app)
    dasatinib_smi = "Cc1cccc(Cl)c1NC(=O)c2cnc(s2)Nc3cc(nc(n3)N4CCNCC4)C"
    resp = client.post("/api/dti/predict_admet", json={"drug_smiles": dasatinib_smi})
    assert resp.status_code == 200
    data = resp.json()
    assert "admet_health_score" in data
    assert "radar_scores" in data
    assert "herg_pic50" in data
    assert data["radar_scores"]["synthesis_sa"] > 0


def test_admet_in_lead_optimizer():
    from dti_inference_runtime import DTIInferenceRuntime
    from dti_lead_optimizer import DTILeadOptimizer

    runtime = DTIInferenceRuntime()
    optimizer = DTILeadOptimizer(runtime)

    dasatinib_smi = "Cc1cccc(Cl)c1NC(=O)c2cnc(s2)Nc3cc(nc(n3)N4CCNCC4)C"
    abl1_seq = "MDPSSPNYDKWEMERTDITMKHKLGGGQYGEVYEGVWKKYSLTVAVKTLKEDTMEVEEFLKEAAVMKEIKHPNLVQLLGVCTREPPFYIITEFMTYGNLLDYLRECNRQEVNAVVLLYMATQISSAMEYLEKKNFIHRDLAARNCLVGENHLVKVADFGLSRLMTGDTYTAHAGAKFPIKWTAPESLAYNKFSIKSDVWAFGVLLWEIATYGMSPYPGIDLSQVYELLEKDYRMERPEGCPEKVYELMRACWQWNPSDRPSFAEIHQAFETMFQESSISDEVEKELGKQGVRGAVSTLLQAPELPTKTRT"

    res = optimizer.optimize(
        drug_smiles=dasatinib_smi,
        target_sequence=abl1_seq,
        target_name="ABL1",
        optimization_goal="提升亲和力与结合强度"
    )

    assert "baseline" in res
    assert "admet" in res["baseline"]
    assert res["baseline"]["admet"]["admet_health_score"] > 0

    assert len(res["candidates"]) > 0
    for cand in res["candidates"]:
        assert "admet" in cand
        assert "radar_scores" in cand["admet"]
        assert "herg_pic50" in cand["admet"]
