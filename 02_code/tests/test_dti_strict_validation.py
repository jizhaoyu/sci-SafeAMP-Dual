"""Unit and endpoint tests for strict validation of SMILES, target sequence, and model names."""
import pytest
from fastapi.testclient import TestClient

from dti_inference_runtime import DTIInferenceRuntime
import sys
from pathlib import Path

# Add web server to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_web_server"))
from app import app

client = TestClient(app)

VALID_SMILES = "CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO"
VALID_SEQUENCE = "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"


class TestDTIRuntimeValidation:
    @pytest.fixture(autouse=True)
    def setup_runtime(self):
        self.runtime = DTIInferenceRuntime()
        self.runtime.load()

    def test_invalid_smiles_rejected(self):
        invalid_smiles_cases = [
            "invalid_smiles",
            "!!!!!!!!!!!!",
            "",
            "   ",
            "c1ccccc",       # unclosed ring
            "CC(C",          # unclosed parenthesis
            "CC)C",          # unmatched closing parenthesis
            "CC(C)X",        # invalid atom X
            "=C",            # bond with no leading atom
        ]
        for smi in invalid_smiles_cases:
            with pytest.raises(ValueError, match=r"(?i)invalid|smiles|empty"):
                self.runtime.predict(smi, VALID_SEQUENCE)

    def test_invalid_sequence_rejected(self):
        invalid_seq_cases = [
            "!!!!!!!!!!!!",
            "",
            "   ",
            "ACDEF",                           # length < 10
            "ACDEFGHIKLMNPQRSTVWY123",         # digits not allowed
            "ACDEFGHIKLMNPQRSTVWY!",           # punctuation
            "ACDEFGHIKLMNPQRSTVWYB",           # non-canonical B
            "ACDEFGHIKLMNPQRSTVWYJ",           # non-canonical J
        ]
        for seq in invalid_seq_cases:
            with pytest.raises(ValueError, match=r"(?i)invalid|sequence|short|character"):
                self.runtime.predict(VALID_SMILES, seq)

    def test_valid_sequence_normalization(self):
        # Mixed whitespace and lowercase
        spaced_seq = "  mqifvktltgktitlevepsdtienvkakiqd kegip  pdqqrlifagkqledgrtlsdyniqkestlhlvlrlrgg \n"
        res = self.runtime.predict(VALID_SMILES, spaced_seq)
        assert res["predicted_pkd"] >= 5.0
        assert res["target_length"] == len("".join(spaced_seq.split()))

    def test_unknown_model_rejected(self):
        with pytest.raises(ValueError, match=r"(?i)unknown|unavailable|model"):
            self.runtime.predict(VALID_SMILES, VALID_SEQUENCE, model_name="no_such_model")

    def test_explicit_empty_and_blank_model_rejected(self):
        for bad_name in ["", "   ", "\t\n"]:
            with pytest.raises(ValueError, match=r"(?i)cannot be empty|whitespace|blank"):
                self.runtime.predict(VALID_SMILES, VALID_SEQUENCE, model_name=bad_name)

    def test_non_string_model_name_rejected(self):
        for bad_type in [123, ["list"], {"dict": 1}]:
            with pytest.raises(ValueError, match=r"(?i)must be a string|None"):
                self.runtime.predict(VALID_SMILES, VALID_SEQUENCE, model_name=bad_type)

    def test_omitted_model_uses_default(self):
        res = self.runtime.predict(VALID_SMILES, VALID_SEQUENCE, model_name=None)
        assert res["model_used"] == "f1_ridge"

    def test_registered_models_all_succeed(self):
        for m_name in self.runtime.models.keys():
            res = self.runtime.predict(VALID_SMILES, VALID_SEQUENCE, model_name=m_name)
            assert res["model_used"] == m_name


class TestDTIEndpointsValidation:
    def test_endpoint_rejects_invalid_smiles(self):
        resp = client.post("/api/dti/predict", json={
            "drug_smiles": "invalid_smiles",
            "target_sequence": VALID_SEQUENCE,
            "model_name": "stacked_ensemble"
        })
        assert resp.status_code == 422
        assert "Prediction failed" in resp.json().get("detail", "")

    def test_endpoint_rejects_invalid_sequence(self):
        resp = client.post("/api/dti/predict", json={
            "drug_smiles": VALID_SMILES,
            "target_sequence": "!!!!!!!!!!!!",
            "model_name": "stacked_ensemble"
        })
        assert resp.status_code == 422
        assert "Prediction failed" in resp.json().get("detail", "")

    def test_endpoint_rejects_unknown_model(self):
        resp = client.post("/api/dti/predict", json={
            "drug_smiles": VALID_SMILES,
            "target_sequence": VALID_SEQUENCE,
            "model_name": "no_such_model"
        })
        assert resp.status_code == 422
        assert "Prediction failed" in resp.json().get("detail", "")

    def test_batch_endpoint_reports_per_item_errors(self):
        resp = client.post("/api/dti/predict_batch", json={
            "pairs": [
                {
                    "drug_smiles": VALID_SMILES,
                    "target_sequence": VALID_SEQUENCE,
                    "model_name": "stacked_ensemble"
                },
                {
                    "drug_smiles": "invalid_smiles",
                    "target_sequence": VALID_SEQUENCE,
                    "model_name": "stacked_ensemble"
                }
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Item 0 succeeded
        assert "predicted_pkd" in data[0]
        # Item 1 failed
        assert "error" in data[1]
        assert "predicted_pkd" not in data[1]

    def test_profile_panel_rejects_invalid_smiles(self):
        resp = client.post("/api/dti/profile_panel", json={
            "drug_smiles": "invalid_smiles"
        })
        assert resp.status_code == 422

    def test_extended_chemistry_inputs_consistency(self):
        from unittest.mock import patch
        from dti_endpoints import dti_runtime

        # 1. Illegal chemistry and syntax cases
        invalid_cases = [
            "CN(C)(C)(C)C",        # neutral nitrogen 5 single bonds (coordination 5 > 4)
            "ccc",                 # acyclic aromatic chain
            "C=1CCCCC-1",          # conflicting explicit ring closure bonds
            "C[N+2](C)(C)(C)(C)C", # [N+2] coordination/valence exceeded
            "CO(C)C",              # neutral oxygen 3 bonds
            "CFC",                 # fluorine 2 bonds
            "C11",                 # self-loop
            "C1C1",                # 2-cycle ring closure
            "[CH5]",               # carbon 5 hydrogens
            "C=(C)C",              # pending bond before branch
            "c1ccccc1cc2ccccc2",   # lowercase aromatic bridge between two rings (not in any cycle)
        ]
        model = dti_runtime.models["stacked_ensemble"]
        with patch.object(model, "predict", side_effect=AssertionError("Model must not run for invalid inputs")) as spy:
            for smi in invalid_cases:
                # Single predict endpoint
                r_pred = client.post("/api/dti/predict", json={
                    "drug_smiles": smi,
                    "target_sequence": VALID_SEQUENCE,
                    "model_name": "stacked_ensemble"
                })
                assert r_pred.status_code == 422, f"Expected 422 for {smi}, got {r_pred.status_code}"
                assert "predicted_pkd" not in r_pred.json()

                # Profile panel endpoint
                r_prof = client.post("/api/dti/profile_panel", json={
                    "drug_smiles": smi,
                    "model_name": "stacked_ensemble"
                })
                assert r_prof.status_code == 422, f"Profile expected 422 for {smi}, got {r_prof.status_code}"
            assert spy.call_count == 0

        # 2. Legal controls
        valid_controls = [
            "c1ccccc1",          # benzene
            "C[N+](C)(C)C",      # quaternary ammonium
            "CCO",               # ethanol
            "c1ccccc1Cc2ccccc2", # aliphatic bridge between two benzene rings
        ]
        for smi in valid_controls:
            r_pred = client.post("/api/dti/predict", json={
                "drug_smiles": smi,
                "target_sequence": VALID_SEQUENCE,
                "model_name": "stacked_ensemble"
            })
            assert r_pred.status_code == 200, f"Expected 200 for {smi}, got {r_pred.status_code}"
            assert "predicted_pkd" in r_pred.json()

            r_prof = client.post("/api/dti/profile_panel", json={
                "drug_smiles": smi,
                "model_name": "stacked_ensemble"
            })
            assert r_prof.status_code == 200, f"Profile expected 200 for {smi}, got {r_prof.status_code}"
            assert len(r_prof.json()) > 0

        # 3. Batch prediction mixed pairs consistency
        batch_pairs = [{"drug_smiles": s, "target_sequence": VALID_SEQUENCE, "model_name": "stacked_ensemble"} for s in invalid_cases + valid_controls]
        r_batch = client.post("/api/dti/predict_batch", json={"pairs": batch_pairs})
        assert r_batch.status_code == 200
        batch_data = r_batch.json()
        assert len(batch_data) == len(invalid_cases) + len(valid_controls)
        for i in range(len(invalid_cases)):
            assert batch_data[i].get("status") == "failed"
            assert "predicted_pkd" not in batch_data[i]
        for j in range(len(valid_controls)):
            idx = len(invalid_cases) + j
            assert "predicted_pkd" in batch_data[idx]

    def test_endpoint_rejects_empty_and_blank_model(self):
        for bad_name in ["", "   ", "\t"]:
            resp = client.post("/api/dti/predict", json={
                "drug_smiles": VALID_SMILES,
                "target_sequence": VALID_SEQUENCE,
                "model_name": bad_name
            })
            assert resp.status_code == 422
            assert "Prediction failed" in resp.json().get("detail", "")

    def test_endpoint_omitted_model_uses_default(self):
        resp = client.post("/api/dti/predict", json={
            "drug_smiles": VALID_SMILES,
            "target_sequence": VALID_SEQUENCE,
            "model_name": None
        })
        assert resp.status_code == 200
        assert "predicted_pkd" in resp.json()

    def test_profile_panel_model_validation(self):
        for bad_name in ["", "   ", "nonexistent_model"]:
            resp = client.post("/api/dti/profile_panel", json={
                "drug_smiles": VALID_SMILES,
                "model_name": bad_name
            })
            assert resp.status_code == 422
            assert "Kinome profiling failed" in resp.json().get("detail", "")
        # Valid omitted model
        resp = client.post("/api/dti/profile_panel", json={
            "drug_smiles": VALID_SMILES,
            "model_name": None
        })
        assert resp.status_code == 200
        assert len(resp.json()) > 0

    def test_batch_endpoint_model_validation(self):
        resp = client.post("/api/dti/predict_batch", json={
            "pairs": [
                {"drug_smiles": VALID_SMILES, "target_sequence": VALID_SEQUENCE, "model_name": ""},
                {"drug_smiles": VALID_SMILES, "target_sequence": VALID_SEQUENCE, "model_name": "   "},
                {"drug_smiles": VALID_SMILES, "target_sequence": VALID_SEQUENCE, "model_name": "no_such_model"},
                {"drug_smiles": VALID_SMILES, "target_sequence": VALID_SEQUENCE, "model_name": None},
                {"drug_smiles": VALID_SMILES, "target_sequence": VALID_SEQUENCE, "model_name": "rigorous_stacked_ensemble"}
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        assert data[0].get("status") == "failed"
        assert data[1].get("status") == "failed"
        assert data[2].get("status") == "failed"
        assert "predicted_pkd" in data[3]
        assert "predicted_pkd" in data[4]

    def test_catalog_four_scenarios(self):
        from unittest.mock import patch
        from dti_endpoints import list_dti_models, dti_runtime

        # 场景 1：空注册表 -> 返回 []
        with patch.object(dti_runtime, "models", {}), patch.object(dti_runtime, "load", return_value=None):
            cat = list_dti_models()
            assert cat == []

        # 场景 2：只有旧模型（非 rigorous_） -> 返回 []
        with patch.object(dti_runtime, "models", {"stacked_ensemble": 1, "ridge": 1}), patch.object(dti_runtime, "load", return_value=None):
            cat = list_dti_models()
            assert cat == []

        # 场景 3：只有部分新模型 -> 仅返回实际已注册项
        with patch.object(dti_runtime, "models", {"rigorous_ridge_alpha50": 1}), patch.object(dti_runtime, "load", return_value=None):
            cat = list_dti_models()
            assert len(cat) == 1
            assert cat[0]["id"] == "rigorous_ridge_alpha50"

        # 场景 4：完整新模型 -> 返回全部 5 个模型
        with patch.object(dti_runtime, "models", {
            "rigorous_stacked_ensemble": 1,
            "rigorous_ridge_alpha50": 1,
            "rigorous_ridge_alpha10": 1,
            "rigorous_hist_gradient_boosting": 1,
            "rigorous_random_forest": 1
        }), patch.object(dti_runtime, "load", return_value=None):
            cat = list_dti_models()
            assert len(cat) == 5
            ids = [m["id"] for m in cat]
            assert "rigorous_stacked_ensemble" in ids
            assert "rigorous_random_forest" in ids


