"""Unit tests for 3D kinase catalytic pocket modeling."""
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fetch_kinase_pocket_3d import model_kinase_pocket_3d, generate_ligand_3d_coordinates


def test_kinase_pocket_3d_generation():
    seq = "MKKFFDSRREQGGSGLGSGSSGGGGSTSGLGSGYRGAR" + "A"*50 + "VAIK" + "A"*80 + "HRDL" + "A"*20 + "DFG" + "A"*100
    pocket = model_kinase_pocket_3d(seq)
    
    assert pocket is not None
    assert len(pocket.atoms) > 10, "Pocket should contain catalytic residues atoms"
    assert pocket.coords.shape == (len(pocket.atoms), 3)
    assert np.all(np.isfinite(pocket.coords))
    assert pocket.dfg_status in ["dfg_in", "dfg_out", "dfg_flexible"]


def test_ligand_3d_coordinates_generation():
    smiles = "Cc1ccc(cc1)Nc2nccc(n2)c3cccnc3"
    ligand = generate_ligand_3d_coordinates(smiles)

    assert ligand is not None
    assert len(ligand.atoms) > 0
    assert ligand.coords.shape == (len(ligand.atoms), 3)
    assert np.all(np.isfinite(ligand.coords))
    # Distance between adjacent bonded atoms should be physically realistic (~1.2 to 1.6 Angstroms)
    bonds = ligand.bonds
    if len(bonds) > 0:
        u, v = bonds[0][0], bonds[0][1]
        dist = np.linalg.norm(ligand.coords[u] - ligand.coords[v])
        assert 1.0 <= dist <= 2.0, f"Bond distance {dist:.2f} should be physically realistic"
