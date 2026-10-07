"""Unit tests for world-model-enhanced DTI runtime execution."""
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dti_inference_runtime import DTIInferenceRuntime


def test_runtime_loads_worldmodel_and_predicts():
    runtime = DTIInferenceRuntime()
    runtime.load()

    assert "worldmodel_stacked_ensemble" in runtime.models
    status = runtime.get_status()
    assert "worldmodel_stacked_ensemble" in status["models_available"]

    smiles = "Cc1ccc(cc1)Nc2nccc(n2)c3cccnc3"
    seq = "MKKFFDSRREQGGSGLGSGSSGGGGSTSGLGSGYRGAR"

    res = runtime.predict(smiles, seq, model_name="worldmodel_stacked_ensemble")
    assert res["model_used"] == "worldmodel_stacked_ensemble"
    assert 5.0 <= res["predicted_pkd"] <= 12.0
    assert res["predicted_kd_nM"] > 0
    assert "concordance_index" in res["domain_benchmark_metrics"]
