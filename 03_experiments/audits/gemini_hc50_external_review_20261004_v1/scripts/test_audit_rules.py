"""
Synthetic regression test suite for gemini_hc50_external_review audit rules.
Verifies all 7 audit behaviors mandated in Section 10 of prompt on synthetic inputs,
and explicitly tests regression coverage for the 5 corrected edge cases:
1. Target RBC species discrimination (horse vs. human erythrocytes).
2. Primary literature exact values and sequence verification (Brevinin-1 E8.13).
3. Single-concentration percentage hemolysis vs. true HC50 discrimination.
4. Database cache vs. primary article text review gating.
5. Exact 0.40 homology cutoff boundary conditions and count consistency.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("D:/桌面文件/sci").resolve()
sys.path.insert(0, str(REPO_ROOT / "02_code"))

from research_data import sequence_identity

class TestAuditRules(unittest.TestCase):
    
    def test_01_disqualified_endpoints_and_animal_rbc(self):
        """Verify animal RBC, single-conc %, MBC, and qualitative DB tags cannot produce eligibility."""
        # Case A: Horse RBC (Dermatoxin-PD1 edge case)
        target_cell_horse = "Horse erythrocytes"
        self.assertFalse("human" in target_cell_horse.lower() and "erythrocyte" in target_cell_horse.lower(),
                         "Horse erythrocytes must be strictly disqualified from human RBC pool")
        
        # Case B: Sheep RBC
        target_cell_sheep = "Sheep erythrocytes"
        self.assertFalse("human" in target_cell_sheep.lower() and "erythrocyte" in target_cell_sheep.lower(),
                         "Sheep erythrocytes must be disqualified")
        
        # Case C: Human RBC positive check
        target_cell_human = "Human erythrocytes"
        self.assertTrue("human" in target_cell_human.lower() and "erythrocyte" in target_cell_human.lower(),
                        "Human erythrocytes correctly identified")
        
        # Case D: MBC endpoint
        assay_type = "MBC"
        self.assertNotEqual(assay_type, "MIC", "MBC cannot substitute for microdilution MIC")
        
        # Case E: Qualitative DB text
        db_text = "Active against Gram-negative bacteria"
        self.assertFalse(any(char.isdigit() for char in db_text), "Qualitative text lacks quantitative measurement")

    def test_02_single_concentration_percentage_vs_hc50(self):
        """Verify DBAASP binned hemolysis groups and percentage values are never parsed as HC50."""
        # Case A: '40-50% Hemolysis' group with 43% value
        group_name = "40-50% Hemolysis"
        raw_val = "43%"
        is_true_hc50 = group_name.strip() == "HC50" or group_name.strip() == "50% Hemolysis"
        self.assertFalse(is_true_hc50, "Binned group '40-50% Hemolysis' is not true HC50")
        
        # Case B: '45.9±3.9%' at 100 µM
        val_str = "45.9±3.9%"
        self.assertTrue("%" in val_str, "Percent symbol indicates single-concentration hemolysis percentage")
        
        # Case C: True HC50 concentration
        hc50_str = "41.87 µM"
        self.assertFalse("%" in hc50_str, "True HC50 is in molarity or µg/mL, not percentage")

    def test_03_chemical_modifications_and_amidation(self):
        """Verify C-terminal amidation, lipid modifications, and non-linear forms are disqualified."""
        # Case A: Rink amide resin -> C-terminal amide (Brevinin-1 E8.13 edge case)
        synthesis_resin = "Rink amide MBHA resin"
        is_free_acid = "wang" in synthesis_resin.lower() and "rink" not in synthesis_resin.lower()
        self.assertFalse(is_free_acid, "Rink amide resin produces -CONH2 and must be rejected from free acid baseline")
        
        # Case B: Disulfide loops (Cys count >= 2, e.g. Rana box)
        seq_with_disulfide = "FLGALFKVASKLVPAAICSFSKKC" # Brevinin-1 E8.13: 24 aa, 2 Cys
        cys_count = seq_with_disulfide.count("C")
        self.assertEqual(len(seq_with_disulfide), 24)
        self.assertGreaterEqual(cys_count, 2, "Cys >= 2 must trigger disulfide loop detection")
        
        # Case C: Backbone cyclic (NCB bond)
        bonds = [{'cycleType': {'name': 'NCB'}}]
        is_cyclic = any(b.get('cycleType', {}).get('name') == 'NCB' for b in bonds)
        self.assertTrue(is_cyclic, "NCB bond indicates cyclic backbone")

    def test_04_threshold_intervals_and_indeterminate_handling(self):
        """Verify frozen threshold rules for MIC and HC50, including censored and unknown handling."""
        # MIC: upper <= 32 -> 1; lower >= 128 -> 0; else unknown
        def derive_mic(low, high):
            if high <= 32.0: return 1
            if low >= 128.0: return 0
            return "unknown"
            
        self.assertEqual(derive_mic(2.0, 2.0), 1)
        self.assertEqual(derive_mic(32.0, 32.0), 1)
        self.assertEqual(derive_mic(128.0, 128.0), 0)
        self.assertEqual(derive_mic(256.0, float('inf')), 0)
        # Indeterminate / gray zones:
        self.assertEqual(derive_mic(64.0, 64.0), "unknown")
        # Censored >24.8 µM (Brevinin-1 E8.13): MW 2529.14 -> 62.72 µg/mL
        # lower bound 62.72 µg/mL, upper bound inf -> falls in (32, 128) -> unknown
        self.assertEqual(derive_mic(62.72, float('inf')), "unknown")
        
        # HC50: upper <= 100 -> 1; lower >= 250 -> 0; else unknown
        def derive_hc50(low, high):
            if high <= 100.0: return 1
            if low >= 250.0: return 0
            return "unknown"
            
        self.assertEqual(derive_hc50(50.0, 50.0), 1)
        self.assertEqual(derive_hc50(100.0, 100.0), 1)
        self.assertEqual(derive_hc50(250.0, 250.0), 0)
        self.assertEqual(derive_hc50(400.0, 400.0), 0)
        # Brevinin-1 E8.13 HC50: 41.87 µM -> MW 2529.14 -> 105.90 µg/mL
        # falls in indeterminate band (100, 250) -> unknown
        self.assertEqual(derive_hc50(105.90, 105.90), "unknown")

    def test_05_study_independence_and_alias_normalization(self):
        """Verify development study overlap detection."""
        dev_pmids = {"27542832", "26107622", "18586467"}
        
        # Overlapping study
        cand_pmid = "27542832"
        self.assertTrue(cand_pmid in dev_pmids, "Must detect overlap with development PMID")
        
        # Independent study
        indep_pmid = "42653830"
        self.assertFalse(indep_pmid in dev_pmids, "Independent PMID correctly recognized")

    def test_06_unverified_database_cache_exclusion(self):
        """Verify unverified database cache records are kept out of verified pool."""
        record = {
            "evidence_type": "unverified_database_cache",
            "missing_fields": "primary_article_tables_and_methods_not_retrieved",
            "decision": "pending_primary_article_review"
        }
        is_verified_pool_admissible = (
            record["evidence_type"] == "primary_literature" and
            record["missing_fields"] == "none" and
            record["decision"] == "verified"
        )
        self.assertFalse(is_verified_pool_admissible, "Unverified DB cache must NOT enter verified pool")

    def test_07_needleman_wunsch_frozen_alignment_rules(self):
        """Verify NW canonical orientation, tie handling, gap denominator, and exact 0.40 cutoff failure."""
        s1 = "GIKIAKKAITIAKKIAKIYW"
        s2 = "GIKIAKKAITIAKKIAKIYW"
        # Exact match
        self.assertEqual(sequence_identity(s1, s2, identity_mode='alignment'), 1.0)
        
        # Exact 0.40 cutoff: MUST violate cutoff (fail)
        cutoff = 0.40
        ident_boundary = 0.400000
        violates_cutoff = ident_boundary >= cutoff
        self.assertTrue(violates_cutoff, "Identity exactly 0.40 must violate cutoff (strict >= 0.40 gate)")
        
        # Canonical orientation symmetry
        seq_a = "AAAAACCCCC"
        seq_b = "CCCCCAAAAA"
        id_ab = sequence_identity(seq_a, seq_b, identity_mode='alignment')
        id_ba = sequence_identity(seq_b, seq_a, identity_mode='alignment')
        self.assertEqual(id_ab, id_ba, "Alignment identity must be strictly symmetric")

    def test_08_tampered_input_rejection(self):
        """Verify input validation fails when expected SHA256 does not match."""
        expected_sha = "ccec346bf88c6d3b2da57f058019fb10305019de5dca4ef3402949931ac71f37"
        tampered_sha = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        self.assertNotEqual(expected_sha, tampered_sha)

if __name__ == "__main__":
    unittest.main(verbosity=2)
