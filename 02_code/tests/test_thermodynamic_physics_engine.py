"""Unit tests for Thermodynamic Physics Engine and MM-GBSA Delta-Learning."""
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fetch_kinase_pocket_3d import generate_ligand_3d_coordinates
from thermodynamic_physics_engine import (
    count_rotatable_bonds,
    predict_physical_affinity_dti,
    calibrate_with_physics
)


def test_count_rotatable_bonds():
    # Benzene: 0 rotatable bonds
    lig_benzene = generate_ligand_3d_coordinates("c1ccccc1")
    assert count_rotatable_bonds(lig_benzene) == 0

    # Hexane: CCCCCC -> 3 internal rotatable bonds
    lig_hexane = generate_ligand_3d_coordinates("CCCCCC")
    assert count_rotatable_bonds(lig_hexane) == 3

    # Gefitinib: has multiple rotatable bonds in ether chains
    gefitinib = "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1"
    lig_gef = generate_ligand_3d_coordinates(gefitinib)
    n_rot = count_rotatable_bonds(lig_gef)
    assert 4 <= n_rot <= 12, f"Gefitinib rotatable bonds expected 4-12, got {n_rot}"


def test_mmgbsa_free_energy_decomposition():
    seq = "MKKFFDSRREQGGSGLGSGSSGGGGSTSGLGSGYRGAR" + "A"*50 + "VAIK" + "A"*80 + "HRDL" + "A"*20 + "DFG" + "A"*100
    smiles = "Cc1ccc(cc1)Nc2nccc(n2)c3cccnc3"

    res = predict_physical_affinity_dti(seq, smiles)
    assert np.isfinite(res.delta_g_bind)
    assert np.isfinite(res.delta_e_vdw)
    assert np.isfinite(res.delta_e_elec)
    assert np.isfinite(res.delta_g_gb)
    assert np.isfinite(res.delta_g_sa)
    assert np.isfinite(res.minus_t_delta_s)

    # Free energy conservation check: Delta G = sum of components
    expected_sum = res.delta_e_vdw + res.delta_e_elec + res.delta_g_gb + res.delta_g_sa + res.minus_t_delta_s
    assert abs(res.delta_g_bind - expected_sum) < 1e-4

    # Descriptors shape check
    assert res.physics_descriptors.shape == (8,)
    assert np.all(np.isfinite(res.physics_descriptors))

    # Biological range check (pKd between 2.0 and 14.0)
    assert 2.0 <= res.predicted_pkd <= 14.0


def test_physics_calibration():
    seq = "MKKFFDSRREQGGSGLGSGSSGGGGSTSGLGSGYRGAR" + "A"*50 + "VAIK" + "A"*80 + "HRDL" + "A"*20 + "DFG" + "A"*100
    smiles = "Cc1ccc(cc1)Nc2nccc(n2)c3cccnc3"

    res = predict_physical_affinity_dti(seq, smiles)
    ml_pkd = 7.50
    calibrated = calibrate_with_physics(ml_pkd, res, weight_physics=0.20)

    expected = 0.80 * 7.50 + 0.20 * res.predicted_pkd
    assert abs(calibrated - expected) < 1e-5
