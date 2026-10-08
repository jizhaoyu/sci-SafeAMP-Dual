"""Unit tests for Synthetic Accessibility (SA Score) and 3D Kinase Pocket Structure Service."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from synthetic_accessibility import compute_sa_score, SyntheticAccessibilityResult
from kinase_pocket_structure_service import get_kinase_pocket_3d


def test_synthetic_accessibility_dasatinib():
    dasatinib_smi = "Cc1cccc(Cl)c1NC(=O)c2cnc(s2)Nc3cc(nc(n3)N4CCNCC4)C"
    res = compute_sa_score(dasatinib_smi)

    assert isinstance(res, SyntheticAccessibilityResult)
    assert 1.0 <= res.sa_score <= 10.0
    assert res.sa_tier in ["easy", "moderate", "difficult", "extremely_difficult"]
    assert res.sa_color in ["emerald", "cyan", "amber", "rose"]
    # Dasatinib is an approved commercial drug with modular convergent synthesis
    assert res.sa_score < 4.5
    assert "合成" in res.sa_label


def test_synthetic_accessibility_simple_and_extreme():
    aspirin = "CC(=O)Oc1ccccc1C(=O)O"
    res_easy = compute_sa_score(aspirin)
    assert res_easy.sa_score < 3.0
    assert res_easy.sa_tier == "easy"

    complex_macrocycle = "CC1C(C(C(C(=O)C(CC(C(C(C(C(C(=O)O1)C)O)C)OC2CC(C(C(O2)C)O)(C)OC)C)O)C)C)O"
    res_complex = compute_sa_score(complex_macrocycle)
    assert res_complex.sa_score > res_easy.sa_score

    empty_res = compute_sa_score("")
    assert empty_res.sa_score == 3.0
    assert empty_res.sa_tier == "easy"


def test_kinase_pocket_structure_abl1():
    res = get_kinase_pocket_3d("ABL1", "Dasatinib")
    assert res["status"] == "success"
    assert res["pdb_code"] == "2GQG"
    assert res["binding_mode"] == "type_i"
    assert "DFG-in" in res["dfg_conformation_label"]
    assert res["hinge_residue"] == "Met318"
    assert len(res["key_hydrogen_bonds"]) >= 2
    assert "ATOM" in res["pdb_content"]
    assert "HETATM" in res["pdb_content"]
    assert "END" in res["pdb_content"]
    assert res["num_atoms"] > 20


def test_kinase_pocket_structure_egfr_and_braf():
    # EGFR
    egfr_res = get_kinase_pocket_3d("EGFR", "Gefitinib")
    assert egfr_res["pdb_code"] == "1M17"
    assert "Met793" in egfr_res["hinge_residue"]
    assert egfr_res["binding_mode"] == "type_i"

    # BRAF Type-II DFG-out
    braf_res = get_kinase_pocket_3d("BRAF", "Sorafenib")
    assert braf_res["pdb_code"] == "4MNE"
    assert braf_res["binding_mode"] == "type_ii"
    assert "DFG-out" in braf_res["dfg_conformation_label"]
    assert "Cys532" in braf_res["hinge_residue"]


def test_kinase_pocket_structure_custom_target():
    res = get_kinase_pocket_3d("NOVEL_KINASE_XYZ", "Compound_99")
    assert res["status"] == "success"
    assert "AF-NOVEL_KINASE_XYZ" in res["pdb_code"]
    assert res["binding_mode"] == "type_i"
    assert len(res["pdb_content"]) > 100
