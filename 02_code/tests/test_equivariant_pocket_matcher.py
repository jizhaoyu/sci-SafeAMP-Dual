"""Unit tests for SE(3) Equivariant Pocket-Ligand Matcher and Geometric Network."""
import sys
from pathlib import Path
import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fetch_kinase_pocket_3d import model_kinase_pocket_3d, generate_ligand_3d_coordinates
from equivariant_pocket_matcher import (
    rbf_expansion,
    compute_soft_lennard_jones,
    compute_equivariant_pocket_match,
    predict_pocket_match_dti,
    EquivariantPocketMatcherNN
)


def random_rotation_matrix() -> np.ndarray:
    """Generate a random 3D rotation matrix in SO(3)."""
    q = np.random.randn(4).astype(np.float32)
    q /= np.linalg.norm(q)
    w, x, y, z = q
    return np.array([
        [1 - 2*y*y - 2*z*z, 2*x*y - 2*z*w, 2*x*z + 2*y*w],
        [2*x*y + 2*z*w, 1 - 2*x*x - 2*z*z, 2*y*z - 2*x*w],
        [2*x*z - 2*y*w, 2*y*z + 2*x*w, 1 - 2*x*x - 2*y*y]
    ], dtype=np.float32)


def test_rbf_expansion():
    dists = np.array([1.5, 3.0, 5.0, 8.0], dtype=np.float32)
    rbf = rbf_expansion(dists, num_bins=16, d_min=1.5, d_max=8.0)
    assert rbf.shape == (4, 16)
    assert np.all(np.isfinite(rbf))
    assert np.all(rbf >= 0.0)
    # Peak of first bin should be near 1.0 for d=1.5
    assert rbf[0, 0] > 0.9


def test_soft_lennard_jones():
    dists = np.array([1.0, 3.0, 6.0], dtype=np.float32)
    vdw_sum = np.array([3.2, 3.2, 3.2], dtype=np.float32)
    e_rep, e_att = compute_soft_lennard_jones(dists, vdw_sum)
    assert len(e_rep) == 3
    assert np.all(np.isfinite(e_rep))
    assert np.all(np.isfinite(e_att))
    # At small distance (1.0 A), repulsive energy should be positive and finite
    assert e_rep[0] > 0.0
    assert e_rep[0] < 1000.0  # Soft-core prevents singularity


def test_se3_rotation_and_translation_invariance():
    """Verify that rigidly rotating and translating ligand coordinates produces invariant features."""
    seq = "MKKFFDSRREQGGSGLGSGSSGGGGSTSGLGSGYRGAR" + "A"*50 + "VAIK" + "A"*80 + "HRDL" + "A"*20 + "DFG" + "A"*100
    smiles = "Cc1ccc(cc1)Nc2nccc(n2)c3cccnc3"
    
    pocket = model_kinase_pocket_3d(seq)
    ligand1 = generate_ligand_3d_coordinates(smiles)
    res1 = compute_equivariant_pocket_match(pocket, ligand1)
    
    # Apply arbitrary rigid rotation and translation to ligand coordinates
    R = random_rotation_matrix()
    t = np.array([12.5, -8.3, 24.1], dtype=np.float32)
    
    ligand2 = generate_ligand_3d_coordinates(smiles)
    ligand2.coords = ligand2.coords @ R.T + t
    res2 = compute_equivariant_pocket_match(pocket, ligand2)
    
    assert res1.geom_features.shape == (32,)
    assert res2.geom_features.shape == (32,)
    # Features should match with high numerical precision
    np.testing.assert_allclose(res1.geom_features, res2.geom_features, atol=1e-3)
    assert abs(res1.dock_score - res2.dock_score) < 1e-3


def test_gatekeeper_t790m_resistance_sensitivity():
    """Verify that T790M Gatekeeper mutation increases steric clash and lowers dock score."""
    egfr_wt_seq = "MKKFFDSRREQGGSGLGSGSSGGGGSTSGLGSGYRGAR" + "A"*50 + "VAIK" + "A"*40 + "T" + "A"*40 + "HRDL" + "A"*20 + "DFG" + "A"*100
    # Gefitinib SMILES
    gefitinib = "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1"

    # Wild-type (Gatekeeper Thr)
    res_wt = predict_pocket_match_dti(egfr_wt_seq, gefitinib, gatekeeper_override="T")
    # Resistant mutant (Gatekeeper Met)
    res_t790m = predict_pocket_match_dti(egfr_wt_seq, gefitinib, gatekeeper_override="M")

    # In T790M, Methionine sidechain extends into the cleft
    assert res_t790m.gatekeeper_clash >= res_wt.gatekeeper_clash
    # Overall dock score in T790M should penalize steric clash
    assert res_t790m.dock_score < res_wt.dock_score


def test_equivariant_pocket_matcher_nn():
    """Verify PyTorch neural network forward pass on geometric feature tensors."""
    model = EquivariantPocketMatcherNN(in_features=32, hidden_dim=64)
    x = torch.randn(8, 32, dtype=torch.float32)
    out = model(x)
    assert out.shape == (8, 1)
    assert torch.all(torch.isfinite(out))
