"""Unit tests to verify SOTA stacked_ensemble is the default model across DTI runtime and endpoints."""
from dti_inference_runtime import DTIInferenceRuntime
import pytest


def test_default_model_is_stacked_ensemble():
    runtime = DTIInferenceRuntime()
    status = runtime.get_status()
    assert status["status"] == "ready"
    assert "stacked_ensemble" in status["models_available"]
    assert status["default_model"] == "stacked_ensemble"


def test_prediction_uses_stacked_ensemble_by_default():
    runtime = DTIInferenceRuntime()
    runtime.load()
    drug_id = list(runtime.drugs.keys())[0]
    target_id = list(runtime.targets.keys())[0]
    drug_smiles = runtime.drugs[drug_id]["smiles"]
    target_seq = runtime.targets[target_id]["sequence"]
    
    res = runtime.predict(drug_smiles, target_seq)
    assert res["model_used"] == "stacked_ensemble"
    assert "predicted_pkd" in res
    assert 5.0 <= res["predicted_pkd"] <= 12.0
