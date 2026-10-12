"""Unit tests for Bilinear ESM-2 Interaction deployment and runtime integration."""
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "02_code") not in sys.path:
    sys.path.insert(0, str(ROOT / "02_code"))
if str(ROOT / "05_web_server") not in sys.path:
    sys.path.insert(0, str(ROOT / "05_web_server"))

from dti_inference_runtime import DTIInferenceRuntime
from dti_endpoints import list_dti_models


@pytest.fixture(scope="module")
def runtime():
    rt = DTIInferenceRuntime()
    rt.load()
    return rt


def test_bilinear_model_registered_and_available(runtime):
    assert "bilinear_esm2_interaction" in runtime.models
    assert runtime.bilinear_predictor is not None
    assert runtime.bilinear_predictor.loaded


def test_bilinear_single_prediction(runtime):
    imatinib = "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5"
    abl1_seq = runtime.targets["ABL1p"]["sequence"]

    res = runtime.predict(imatinib, abl1_seq, model_name="bilinear_esm2_interaction")
    assert res["model_used"] == "bilinear_esm2_interaction"
    assert res["features_dim"] == 2528
    assert 5.0 <= res["predicted_pkd"] <= 9.0
    assert res["predicted_kd_nM"] > 0
    assert res["provenance"]["protocol"] == "DTI-Phase3-Bilinear-20261012"


def test_bilinear_kinome_profiling_diversity(runtime):
    imatinib = "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5"
    gefitinib = "COC1=C(C=C2C(=C1)N=CN=C2NC3=CC(=C(C=C3)F)Cl)OCCCN4CCOCC4"

    prof_imatinib = runtime.profile_kinase_panel(imatinib, model_name="bilinear_esm2_interaction")
    prof_gefitinib = runtime.profile_kinase_panel(gefitinib, model_name="bilinear_esm2_interaction")

    assert len(prof_imatinib) == len(prof_gefitinib) >= 14

    ranks_imatinib = [x["kinase_name"] for x in prof_imatinib]
    ranks_gefitinib = [x["kinase_name"] for x in prof_gefitinib]

    # Verify that different drugs do NOT produce identical rankings
    assert ranks_imatinib != ranks_gefitinib


def test_bilinear_model_exposed_in_api():
    models = list_dti_models()
    model_ids = [m["id"] for m in models]
    assert "bilinear_esm2_interaction" in model_ids

    bilinear_entry = next(m for m in models if m["id"] == "bilinear_esm2_interaction")
    assert "双线性" in bilinear_entry["name"]
    assert bilinear_entry["metrics_by_domain"]["strict_dual_cold_test"]["p10"] == 0.1615


def test_bilinear_predict_endpoint(runtime):
    from dti_endpoints import predict_dti_affinity, DTIPredictionRequest
    imatinib = "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5"
    abl1_seq = runtime.targets["ABL1p"]["sequence"]

    req = DTIPredictionRequest(
        drug_smiles=imatinib,
        target_sequence=abl1_seq,
        model_name="bilinear_esm2_interaction"
    )
    res = predict_dti_affinity(req)
    assert res["model_used"] == "bilinear_esm2_interaction"
    assert "research_evidence" in res
    assert 5.0 <= res["predicted_pkd"] <= 9.0

