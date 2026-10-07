"""Unit tests for ESM-2 kinase representation extractor."""
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extract_esm_kinase_features import extract_esm_kinase_representation, batch_extract_esm_kinase_representations


def test_esm_kinase_representation_shape_and_dtype():
    # ABL1 partial kinase sequence
    seq = "MSKGPAVGIDLGTTYSCVGVFQHGKVEIIANDQGNRTTPSYVAFTDTERLIGDAAKNQVAMNPTNTVFDAKRLIGRRFDDAVV"
    rep = extract_esm_kinase_representation(seq)
    assert isinstance(rep, np.ndarray)
    assert rep.shape == (320,)
    assert rep.dtype == np.float32
    assert np.all(np.isfinite(rep))


def test_esm_kinase_long_sequence_truncation():
    # Sequence longer than 1022 residues should be safely handled
    long_seq = "A" * 1200
    rep = extract_esm_kinase_representation(long_seq)
    assert rep.shape == (320,)
    assert np.all(np.isfinite(rep))


def test_batch_extraction():
    seqs = [
        "MKKFFDSRREQGGSGLGSGSSGGGGSTSGLGSGYRGAR",
        "MSKGPAVGIDLGTTYSCVGVFQHGKVEIIANDQGNRTT",
    ]
    batch_rep = batch_extract_esm_kinase_representations(seqs)
    assert batch_rep.shape == (2, 320)
    assert np.all(np.isfinite(batch_rep))
