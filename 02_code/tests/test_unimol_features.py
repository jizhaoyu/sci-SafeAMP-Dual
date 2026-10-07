"""Unit tests for Uni-Mol and 3D molecular world model representation extraction."""
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extract_unimol_features import extract_unimol_representation, batch_extract_unimol_representations


def test_unimol_representation_shape_and_dtype():
    smiles = "Cc1ccc(cc1)Nc2nccc(n2)c3cccnc3"
    vec = extract_unimol_representation(smiles)
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (512,)
    assert vec.dtype == np.float32
    assert np.all(np.isfinite(vec))


def test_unimol_deterministic_and_distinct():
    smiles_a = "Cc1ccc(cc1)Nc2nccc(n2)c3cccnc3" # Imatinib-like core
    smiles_b = "CC(=O)Oc1ccccc1C(=O)O"           # Aspirin
    vec_a1 = extract_unimol_representation(smiles_a)
    vec_a2 = extract_unimol_representation(smiles_a)
    vec_b = extract_unimol_representation(smiles_b)

    # Determinism
    np.testing.assert_allclose(vec_a1, vec_a2, rtol=1e-6)

    # Distinctness across different chemotypes
    cos_sim = float(np.dot(vec_a1, vec_b) / (np.linalg.norm(vec_a1) * np.linalg.norm(vec_b) + 1e-8))
    assert cos_sim < 0.95, f"Expected distinct molecules to have non-identical vectors, got cosine sim {cos_sim}"


def test_batch_extraction():
    smiles_list = [
        "c1ccccc1",
        "CC(=O)O",
        "CCN(CC)CC"
    ]
    batch_vecs = batch_extract_unimol_representations(smiles_list)
    assert isinstance(batch_vecs, np.ndarray)
    assert batch_vecs.shape == (3, 512)
    assert np.all(np.isfinite(batch_vecs))
