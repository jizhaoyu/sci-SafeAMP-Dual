"""Unit tests for Phase 3: Wet-lab Dispatch Generator, Academic Report, and Feedback Calibration."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_web_server"))

from wetlab_dispatch_generator import generate_96_well_dispatch
from dti_report_generator import generate_dti_academic_report
from wetlab_feedback_calibrator import calibrate_with_wetlab_feedback
from app import app


SAMPLE_BASELINE = {
    "name": "Dasatinib",
    "smiles": "Cc1cccc(Cl)c1NC(=O)c2cnc(s2)Nc3cc(nc(n3)N4CCNCC4)C",
    "predicted_pkd": 7.41,
    "predicted_kd_nM": 38.9,
    "sa_score": 3.2,
    "sa_tier": "easy",
    "admet": {
        "admet_health_score": 75.0,
        "herg_risk": "low",
        "solubility_logs": -4.1
    }
}

SAMPLE_CANDIDATES = [
    {
        "id": "cand_1",
        "name": "对位氟化衍生物",
        "smiles": "Cc1cccc(Cl)c1NC(=O)c2cnc(s2)Nc3cc(nc(n3)N4CCNCC4)CF",
        "modification_type": "氟原子取代",
        "predicted_pkd": 7.82,
        "predicted_kd_nM": 15.1,
        "delta_pkd": 0.41,
        "sa_score": 3.4,
        "uncertainty_sigma": 0.40,
        "rationale": "引入氟原子增强疏水堆积与偶极矩配位",
        "admet": {
            "admet_health_score": 78.0,
            "herg_risk": "low"
        }
    },
    {
        "id": "cand_2",
        "name": "三氟甲基修饰物",
        "smiles": "Cc1cccc(Cl)c1NC(=O)c2cnc(s2)Nc3cc(nc(n3)N4CCNCC4)C(F)(F)F",
        "modification_type": "亲脂性增效",
        "predicted_pkd": 7.65,
        "predicted_kd_nM": 22.4,
        "delta_pkd": 0.24,
        "sa_score": 3.8,
        "uncertainty_sigma": 0.42,
        "rationale": "占据变构疏水背口袋",
        "admet": {
            "admet_health_score": 72.0,
            "herg_risk": "low"
        }
    }
]


def test_wetlab_dispatch_96_well():
    dispatch = generate_96_well_dispatch("ABL1", SAMPLE_BASELINE, SAMPLE_CANDIDATES)

    assert dispatch["target_name"] == "ABL1"
    assert dispatch["total_wells"] == len(SAMPLE_CANDIDATES) + 2  # 2 candidates + 2 controls
    assert dispatch["candidates_count"] == 2
    assert dispatch["tier1_count"] >= 1

    wells = dispatch["wells"]
    assert wells[0]["well_id"] == "A01"
    assert wells[0]["compound_type"] == "positive_control"

    assert wells[-1]["well_id"] == "H12"
    assert wells[-1]["compound_type"] == "negative_control"

    csv_data = dispatch["csv_content"]
    assert "Plate_Barcode" in csv_data
    assert "Well" in csv_data
    assert "A01" in csv_data
    assert "H12" in csv_data
    assert "Dasatinib" in csv_data


def test_academic_report_generation():
    res = generate_dti_academic_report(
        target_name="ABL1",
        baseline=SAMPLE_BASELINE,
        candidates=SAMPLE_CANDIDATES,
        biophysics={
            "preferred_conformation": "Type I / DFG-in 活性构象",
            "mmgbsa": {
                "delta_g_bind": -10.1,
                "delta_e_vdw": -48.2,
                "delta_e_elec": -19.4,
                "delta_g_gb": 31.0,
                "delta_g_sa": -5.2,
                "minus_t_delta_s": 15.5
            }
        },
        admet={
            "admet_health_score": 75.0,
            "herg_label": "心脏安全性优良",
            "herg_pic50": 4.8
        }
    )

    assert "markdown_report" in res
    assert "html_report" in res

    md = res["markdown_report"]
    assert "# 先导化合物结构优化与激酶结合亲和力学术评估报告" in md
    assert "ABL1" in md
    assert "MM-GBSA" in md
    assert "对位氟化衍生物" in md
    assert "通式 (Formula I)" in md

    html = res["html_report"]
    assert "<!DOCTYPE html>" in html
    assert "ABL1" in html
    assert "&Delta;G_bind" in html


def test_wetlab_feedback_calibration():
    # Feedback: candidate 1 measured Kd = 12.0 nM (pKd ≈ 7.92, higher than predicted 7.82)
    measurements = [
        {
            "name": "对位氟化衍生物",
            "smiles": SAMPLE_CANDIDATES[0]["smiles"],
            "measured_kd_nM": 12.0,
            "notes": "Biacore SPR 验证"
        }
    ]

    res = calibrate_with_wetlab_feedback(
        target_name="ABL1",
        candidates=SAMPLE_CANDIDATES,
        measurements=measurements,
        y_best_reference=7.41
    )

    assert res["status"] == "success"
    assert res["assayed_count"] == 1
    assert res["mae"] > 0
    assert len(res["calibrated_candidates"]) == 2

    c0 = next(c for c in res["calibrated_candidates"] if c["id"] == "cand_1")
    assert c0["is_experimentally_verified"] is True
    # Uncertainty of verified candidate shrinks to near zero
    assert c0["calibrated_uncertainty_sigma"] < c0["prior_uncertainty_sigma"]

    c1 = next(c for c in res["calibrated_candidates"] if c["id"] == "cand_2")
    assert c1["is_experimentally_verified"] is False
    # Kernel propagation adjusts unmeasured candidate
    assert c1["calibrated_uncertainty_sigma"] <= c1["prior_uncertainty_sigma"]


def test_fastapi_phase3_endpoints():
    client = TestClient(app)

    # 1. Test wetlab dispatch
    dispatch_resp = client.post("/api/dti/wetlab_dispatch", json={
        "target_name": "ABL1",
        "baseline": SAMPLE_BASELINE,
        "candidates": SAMPLE_CANDIDATES
    })
    assert dispatch_resp.status_code == 200
    dispatch_data = dispatch_resp.json()
    assert dispatch_data["total_wells"] == 4
    assert len(dispatch_data["csv_content"]) > 50

    # 2. Test academic report
    report_resp = client.post("/api/dti/academic_report", json={
        "target_name": "ABL1",
        "baseline": SAMPLE_BASELINE,
        "candidates": SAMPLE_CANDIDATES
    })
    assert report_resp.status_code == 200
    report_data = report_resp.json()
    assert len(report_data["markdown_report"]) > 100
    assert len(report_data["html_report"]) > 100

    # 3. Test wetlab feedback
    feedback_resp = client.post("/api/dti/wetlab_feedback", json={
        "target_name": "ABL1",
        "candidates": SAMPLE_CANDIDATES,
        "measurements": [{
            "name": "对位氟化衍生物",
            "smiles": SAMPLE_CANDIDATES[0]["smiles"],
            "measured_kd_nM": 10.5
        }]
    })
    assert feedback_resp.status_code == 200
    feedback_data = feedback_resp.json()
    assert feedback_data["status"] == "success"
    assert "calibrated_candidates" in feedback_data
