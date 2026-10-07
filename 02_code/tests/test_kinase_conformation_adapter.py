"""Unit tests for Kinase Conformation Adapter and Induced Fit Engine."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kinase_conformation_adapter import (
    classify_inhibitor_binding_mode,
    estimate_kinase_dfg_penalty,
    compute_induced_fit_interaction
)


def test_inhibitor_modality_classification():
    drugs = {
        'Imatinib': ('Cc1ccc(cc1)Nc2nccc(n2)c3cccnc3NC(=O)c4ccc(cc4)CN5CCN(C)CC5', 'type_ii'),
        'Sorafenib': ('CNC(=O)c1cc(Oc2ccc(NC(=O)Nc3ccc(Cl)c(c3)C(F)(F)F)cc2)ccn1', 'type_ii'),
        'Gefitinib': ('COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1', 'type_i'),
        'Dasatinib': ('Cc1cccc(c1Cl)NC(=O)c2cnc(s2)Nc3cc(nc(n3)C)N4CCN(CC4)CCO', 'type_i'),
        'Osimertinib': ('COc1cc(N(C)CCN(C)C)c(NC(=O)C=C)cc1Nc2nccc(n2)c3cn(C)c4ccccc34', 'covalent'),
        'Erlotinib': ('COCCOC1=C(C=C2C(=C1)C(=NC=N2)NC3=CC=CC(=C3)C#C)OCCOC', 'type_i')
    }
    for name, (smiles, expected) in drugs.items():
        assert classify_inhibitor_binding_mode(smiles) == expected, f"{name} should be {expected}"


def test_kinase_dfg_penalty_estimation():
    # Synthetic Abl-like sequence with flexible activation loop (DFGLSR)
    abl_seq = "SHNYIT" + "A"*50 + "VAIK" + "A"*40 + "HRDL" + "A"*20 + "DFGLSRLMT" + "A"*50
    penalty_abl = estimate_kinase_dfg_penalty(abl_seq)
    assert penalty_abl <= 2.0, f"Abl should have low DFG-out penalty (got {penalty_abl})"

    # Synthetic EGFR-like sequence with rigid activation loop (DFGLAKL)
    egfr_seq = "MKK" + "A"*50 + "VAIK" + "A"*40 + "HRDLAARN" + "A"*20 + "DFGLAKL" + "A"*50
    penalty_egfr = estimate_kinase_dfg_penalty(egfr_seq)
    assert penalty_egfr >= 4.5, f"EGFR should have high DFG-out penalty (got {penalty_egfr})"


def test_induced_fit_interaction_selectivity():
    abl_seq = "SHNYIT" + "A"*50 + "VAIK" + "A"*40 + "HRDL" + "A"*20 + "DFGLSRLMT" + "A"*50
    egfr_seq = "MKK" + "A"*50 + "VAIK" + "A"*40 + "HRDLAARN" + "A"*20 + "DFGLAKL" + "A"*50
    imatinib = "Cc1ccc(cc1)Nc2nccc(n2)c3cccnc3NC(=O)c4ccc(cc4)CN5CCN(C)CC5"

    res_abl = compute_induced_fit_interaction(abl_seq, imatinib)
    res_egfr = compute_induced_fit_interaction(egfr_seq, imatinib)

    assert res_abl.binding_mode == "type_ii"
    assert res_abl.preferred_conformation == "dfg_out"
    # Abl should suffer much smaller conformational penalty than EGFR for Type II Imatinib
    assert res_abl.dfg_flip_penalty_kcal < res_egfr.dfg_flip_penalty_kcal
    assert res_abl.induced_fit_score > res_egfr.induced_fit_score, "Imatinib should have higher affinity for Abl than EGFR"


def test_covalent_inhibitor_interaction():
    egfr_seq = "MKK" + "A"*50 + "VAIK" + "A"*40 + "HRDLAARN" + "A"*20 + "DFGLAKL" + "A"*50
    osimertinib = "COc1cc(N(C)CCN(C)C)c(NC(=O)C=C)cc1Nc2nccc(n2)c3cn(C)c4ccccc34"

    res = compute_induced_fit_interaction(egfr_seq, osimertinib)
    assert res.binding_mode == "covalent"
    assert res.preferred_conformation == "dfg_in"
    assert res.effective_pkd_delta > 0.0, "Covalent adduct formation should provide binding bonus"
