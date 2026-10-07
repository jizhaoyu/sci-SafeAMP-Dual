"""Unit tests for combined Uni-Mol + ESM-2 world model feature extraction pipeline."""
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extract_worldmodel_features import (
    extract_worldmodel_drug_features,
    extract_worldmodel_kinase_features,
    extract_worldmodel_pair_features,
)


def test_worldmodel_pair_features():
    smiles = "Cc1ccc(cc1)Nc2nccc(n2)c3cccnc3"
    seq = "MKKFFDSRREQGGSGLGSGSSGGGGSTSGLGSGYRGAR"

    d_vec = extract_worldmodel_drug_features(smiles)
    t_vec = extract_worldmodel_kinase_features(seq)
    pair_vec = extract_worldmodel_pair_features(smiles, seq)

    assert d_vec.shape == (2568,)
    assert t_vec.shape == (420,)
    assert pair_vec.shape == (2988,)
    assert np.all(np.isfinite(pair_vec))
    np.testing.assert_allclose(pair_vec, np.concatenate([d_vec, t_vec]), rtol=1e-5)
