"""Verified F1 default and explicit legacy model compatibility."""
from dti_inference_runtime import DTIInferenceRuntime
import pytest


def test_default_model_is_verified_f1_ridge():
    runtime = DTIInferenceRuntime()
    status = runtime.get_status()
    assert status["status"] == "ready"
    assert "stacked_ensemble" in status["models_available"]
    assert status["default_model"] == "f1_ridge"


def test_prediction_uses_verified_f1_by_default():
    runtime = DTIInferenceRuntime()
    runtime.load()
    drug_id = list(runtime.drugs.keys())[0]
    target_id = list(runtime.targets.keys())[0]
    drug_smiles = runtime.drugs[drug_id]["smiles"]
    target_seq = runtime.targets[target_id]["sequence"]
    
    res = runtime.predict(drug_smiles, target_seq)
    assert res["model_used"] == "f1_ridge"
    assert "predicted_pkd" in res
    assert res["features_dim"] == 2156
    assert res["predicted_pkd"] == res["raw_predicted_pkd"]


def test_explicit_legacy_stacking_remains_available():
    runtime = DTIInferenceRuntime()
    runtime.load()
    drug = next(iter(runtime.drugs.values()))
    target = next(iter(runtime.targets.values()))
    result = runtime.predict(drug["smiles"], target["sequence"], model_name="stacked_ensemble")
    assert result["model_used"] == "stacked_ensemble"
    assert 5.0 <= result["predicted_pkd"] <= 12.0
