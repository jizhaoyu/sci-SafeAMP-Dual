import unittest
import numpy as np
import pandas as pd
from dti_gene_max_loader import DtiGeneMaxDatasetLoader, CENSORED_KD_THRESHOLD

class TestDtiGeneMaxDatasetLoader(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = DtiGeneMaxDatasetLoader()
        cls.df = cls.loader.load()

    def test_dimensions(self):
        self.assertEqual(len(self.df), 25772)
        self.assertEqual(self.df["ID1"].nunique(), 68)
        self.assertEqual(self.df["ID2"].nunique(), 379)

    def test_censorship_annotations(self):
        censored_df = self.loader.get_censored_pairs()
        uncensored_df = self.loader.get_uncensored_pairs()
        
        self.assertTrue((censored_df["Y"] >= CENSORED_KD_THRESHOLD).all())
        self.assertTrue((uncensored_df["Y"] < CENSORED_KD_THRESHOLD).all())
        self.assertEqual(len(censored_df) + len(uncensored_df), len(self.df))
        
        # In DAVIS, exactly ~80% pairs are at 10,000 nM
        self.assertGreater(len(censored_df), 15000)

    def test_semantic_mapping(self):
        # Test EGFR(T790M)
        egfr_rows = self.df[self.df["ID2"] == "EGFR(T790M)"]
        self.assertGreater(len(egfr_rows), 0)
        self.assertEqual(egfr_rows["canonical_gene_symbol"].iloc[0], "EGFR")
        self.assertEqual(egfr_rows["standard_display_name"].iloc[0], "EGFR (Gene-Max)")
        self.assertTrue(egfr_rows["is_misleading_mutation_label"].iloc[0])

        # Test BRAF(V600E)
        braf_rows = self.df[self.df["ID2"] == "BRAF(V600E)"]
        self.assertGreater(len(braf_rows), 0)
        self.assertEqual(braf_rows["canonical_gene_symbol"].iloc[0], "BRAF")
        self.assertEqual(braf_rows["standard_display_name"].iloc[0], "BRAF (Gene-Max)")
        self.assertTrue(braf_rows["is_misleading_mutation_label"].iloc[0])

        # Test ABL1p
        abl_rows = self.df[self.df["ID2"] == "ABL1p"]
        self.assertGreater(len(abl_rows), 0)
        self.assertEqual(abl_rows["canonical_gene_symbol"].iloc[0], "ABL1")
        self.assertEqual(abl_rows["standard_display_name"].iloc[0], "ABL1 (Gene-Max)")
        self.assertTrue(abl_rows["is_misleading_mutation_label"].iloc[0])

    def test_pkd_calculation(self):
        # 10,000 nM -> 5.0 pKd
        c_rows = self.df[self.df["Y"] == 10000.0]
        self.assertTrue(np.allclose(c_rows["pkd"].values, 5.0, atol=1e-4))
        
        # 1 nM -> 9.0 pKd
        # 100 nM -> 7.0 pKd
        df_100 = self.df[np.isclose(self.df["Y"], 100.0)]
        if len(df_100) > 0:
            self.assertTrue(np.allclose(df_100["pkd"].values, 7.0, atol=1e-4))

    def test_integrity_report(self):
        rep = self.loader.validate_integrity()
        self.assertEqual(rep["status"], "PASS")
        self.assertTrue(rep["plan_a_aligned"])

if __name__ == "__main__":
    unittest.main()
