"""End-to-end integration and verification tests for DTI inference runtime and FastAPI backend."""
import unittest
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_code"))
sys.path.insert(0, str(ROOT / "05_web_server"))

from fastapi.testclient import TestClient
from app import app
from dti_inference_runtime import DTIInferenceRuntime
from dti_evidence import get_evidence_status

# Representative Drugs (SMILES)
# 1. Dasatinib (达沙替尼) - in DAVIS (ID: 3062316)
DASATINIB_SMILES = "Cc1nc(Nc2ncc(C(=O)Nc3c(C)cccc3Cl)s2)cc(N2CCN(CCO)CC2)n1"

# 2. Osimertinib (奥希替尼) - 3rd-generation EGFR-TKI
OSIMERTINIB_SMILES = "COc1cc(N(C)CCN(C)C)c(NC(=O)C=C)cc1Nc2nccc(n2)c3cn(C)c4ccccc34"

# 3. Vemurafenib (维莫非尼, PLX4032) - BRAF inhibitor (also in DAVIS as ID: 42611257)
VEMURAFENIB_SMILES = "CCCS(=O)(=O)Nc1ccc(F)c(C(=O)c2c[nH]c3ncc(Cl)cc23)c1F"


class TestDTIBackendIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.runtime = DTIInferenceRuntime()
        cls.runtime.load()
        cls.client = TestClient(app)

    def test_01_runtime_and_status_endpoint(self):
        """Verify /api/dti/status returns ready, Plan A protocol, censoring thresholds, etc."""
        # 1. Check direct runtime status
        rt_status = self.runtime.get_status()
        self.assertEqual(rt_status["status"], "ready")
        self.assertEqual(rt_status["plan_a_protocol"], "Gene-Max DTI v1.0")
        self.assertEqual(rt_status["target_semantic_definition"], "Kinase Gene-Level Maximum Affinity (min Kd / max pKd)")
        self.assertEqual(rt_status["censoring_threshold_kd"], 10000.0)
        self.assertEqual(rt_status["censoring_threshold_pkd"], 5.0)
        self.assertEqual(rt_status["total_benchmark_pairs"], 25772)
        self.assertEqual(rt_status["num_targets"], 379)
        self.assertEqual(rt_status["num_drugs"], 68)
        self.assertEqual(rt_status["default_model"], "f1_ridge")
        self.assertIn("f1_ridge", rt_status["models_available"])

        # 2. Check HTTP API endpoint /api/dti/status
        resp = self.client.get("/api/dti/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["plan_a_protocol"], "Gene-Max DTI v1.0")
        self.assertEqual(data["censoring_threshold_kd"], 10000.0)
        self.assertEqual(data["censoring_threshold_pkd"], 5.0)
        self.assertEqual(data["num_targets"], 379)
        self.assertEqual(data["num_drugs"], 68)
        self.assertEqual(data["default_model"], "f1_ridge")

    def test_02_targets_endpoint_metadata(self):
        """Verify /api/dti/targets returns 379 targets with Plan A metadata."""
        resp = self.client.get("/api/dti/targets")
        self.assertEqual(resp.status_code, 200)
        targets = resp.json()
        self.assertEqual(len(targets), 379)

        target_map = {t["id"]: t for t in targets}

        # Check required metadata fields
        sample = targets[0]
        for field in [
            "id", "canonical_gene_symbol", "standard_display_name",
            "is_misleading_mutation_label", "misleading_label_type",
            "target_semantic_type", "curation_note", "length", "sequence",
            "fold", "is_test"
        ]:
            self.assertIn(field, sample, f"Missing field: {field}")

        # Check EGFR(T790M)
        self.assertIn("EGFR(T790M)", target_map)
        egfr = target_map["EGFR(T790M)"]
        self.assertEqual(egfr["canonical_gene_symbol"], "EGFR")
        self.assertEqual(egfr["standard_display_name"], "EGFR (Gene-Max)")
        self.assertTrue(egfr["is_misleading_mutation_label"])
        self.assertIn("Gene-Max", egfr["standard_display_name"])

        # Check BRAF(V600E)
        self.assertIn("BRAF(V600E)", target_map)
        braf = target_map["BRAF(V600E)"]
        self.assertEqual(braf["canonical_gene_symbol"], "BRAF")
        self.assertEqual(braf["standard_display_name"], "BRAF (Gene-Max)")
        self.assertTrue(braf["is_misleading_mutation_label"])

        # Check ABL1p
        self.assertIn("ABL1p", target_map)
        abl1 = target_map["ABL1p"]
        self.assertEqual(abl1["canonical_gene_symbol"], "ABL1")
        self.assertEqual(abl1["standard_display_name"], "ABL1 (Gene-Max)")
        self.assertTrue(abl1["is_misleading_mutation_label"])

    def test_03_evidence_status_endpoint(self):
        """Verify /api/dti/evidence_status returns valid research evidence structure."""
        resp = self.client.get("/api/dti/evidence_status")
        self.assertEqual(resp.status_code, 200)
        ev = resp.json()
        self.assertEqual(ev["status"], "available")
        self.assertEqual(ev["external_evaluation_completed"], False)
        self.assertEqual(ev["human_review"], "pending")
        self.assertEqual(ev["admitted_count"], 0)
        self.assertEqual(ev["reviewed_count"], 8)
        self.assertEqual(ev["confirmed_point_count"], 5)
        self.assertIn("f1_ridge", ev.get("model_diagnostics", {}))
        f1_diag = ev["model_diagnostics"]["f1_ridge"]
        self.assertEqual(f1_diag["scope"], "existing_DAVIS_diagnostic")
        self.assertGreater(f1_diag["high_affinity_count"], 0)

    def test_04_real_inference_representative_pairs(self):
        """Verify /api/dti/predict with real f1_ridge model on representative pairs."""
        # Retrieve target sequences
        target_map = {t["id"]: t for t in self.client.get("/api/dti/targets").json()}
        abl1_seq = target_map["ABL1p"]["sequence"]
        egfr_seq = target_map["EGFR(T790M)"]["sequence"]
        braf_seq = target_map["BRAF(V600E)"]["sequence"]

        test_cases = [
            ("达沙替尼 + ABL1", DASATINIB_SMILES, abl1_seq, "ABL1"),
            ("奥希替尼 + EGFR", OSIMERTINIB_SMILES, egfr_seq, "EGFR"),
            ("维莫非尼 + BRAF", VEMURAFENIB_SMILES, braf_seq, "BRAF"),
        ]

        for name, smiles, seq, gene in test_cases:
            resp = self.client.post("/api/dti/predict", json={
                "drug_smiles": smiles,
                "target_sequence": seq,
                "model_name": "f1_ridge"
            })
            self.assertEqual(resp.status_code, 200, f"Failed prediction for {name}: {resp.text}")
            res = resp.json()

            # Verify predictions
            pkd = res["predicted_pkd"]
            kd_nM = res["predicted_kd_nM"]
            self.assertIsInstance(pkd, float)
            self.assertGreater(pkd, 4.0)
            self.assertLess(pkd, 13.0)

            # Mathematical conversion check: Kd = 10^(9 - pKd)
            expected_kd = 10.0 ** (9.0 - pkd)
            self.assertAlmostEqual(math.log10(kd_nM), math.log10(expected_kd), places=2)

            # Model metadata
            self.assertEqual(res["model_used"], "f1_ridge")
            self.assertIn("affinity_tier", res)
            self.assertIn("affinity_tier_code", res)
            self.assertIn("domain", res)
            self.assertIn("domain_label", res)

            # Scientific warning and research evidence
            self.assertIn("warning", res)
            self.assertIn("DAVIS 冻结基准模型", res["warning"])
            self.assertIn("research_evidence", res)
            self.assertEqual(res["research_evidence"]["external_evaluation_completed"], False)
            self.assertEqual(res["research_evidence"]["admitted_count"], 0)

            print(f"[TEST PAIR] {name}: pKd={pkd:.4f}, Kd={kd_nM:.2f} nM, domain={res['domain']}, tier={res['affinity_tier']}")

    def test_05_predict_batch_and_profile_panel(self):
        """Verify /api/dti/predict_batch and /api/dti/profile_panel endpoints."""
        target_map = {t["id"]: t for t in self.client.get("/api/dti/targets").json()}
        abl1_seq = target_map["ABL1p"]["sequence"]
        egfr_seq = target_map["EGFR(T790M)"]["sequence"]

        # Batch
        batch_resp = self.client.post("/api/dti/predict_batch", json={
            "pairs": [
                {"drug_smiles": DASATINIB_SMILES, "target_sequence": abl1_seq, "model_name": "f1_ridge"},
                {"drug_smiles": OSIMERTINIB_SMILES, "target_sequence": egfr_seq, "model_name": "f1_ridge"},
            ]
        })
        self.assertEqual(batch_resp.status_code, 200)
        batch_res = batch_resp.json()
        self.assertEqual(len(batch_res), 2)
        self.assertEqual(batch_res[0]["model_used"], "f1_ridge")
        self.assertEqual(batch_res[1]["model_used"], "f1_ridge")

        # Profile panel
        prof_resp = self.client.post("/api/dti/profile_panel", json={
            "drug_smiles": DASATINIB_SMILES,
            "model_name": "f1_ridge"
        })
        self.assertEqual(prof_resp.status_code, 200)
        prof_res = prof_resp.json()
        self.assertEqual(len(prof_res), 14)  # 14 matched kinases in DAVIS panel
        self.assertIn("kinase_name", prof_res[0])
        self.assertIn("predicted_pkd", prof_res[0])
        # Verify sorted descending by pKd
        for i in range(len(prof_res) - 1):
            self.assertGreaterEqual(prof_res[i]["predicted_pkd"], prof_res[i+1]["predicted_pkd"])


if __name__ == "__main__":
    unittest.main()
