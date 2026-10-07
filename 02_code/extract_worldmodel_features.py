"""Unified biological world model feature extractor fusing Uni-Mol 3D descriptors and ESM-2 representations."""
from __future__ import annotations

from typing import Tuple
import numpy as np

from extract_dti_davis_enhanced_features import (
    extract_enhanced_drug_features,
    extract_enhanced_kinase_features,
)
from extract_unimol_features import extract_unimol_representation
from extract_esm_kinase_features import extract_esm_kinase_representation


def extract_worldmodel_drug_features(smiles: str) -> np.ndarray:
    """
    Extract 2568-dim world-model-enhanced small molecule feature vector:
    - 2056-dim Morgan circular fingerprints and structural descriptors
    - 512-dim Uni-Mol 3D topological manifold representation
    """
    base_feat = extract_enhanced_drug_features(smiles)      # (2056,)
    unimol_feat = extract_unimol_representation(smiles)     # (512,)
    return np.concatenate([base_feat, unimol_feat]).astype(np.float32)


def extract_worldmodel_kinase_features(sequence: str) -> np.ndarray:
    """
    Extract 420-dim world-model-enhanced kinase feature vector:
    - 100-dim domain-aware kinase catalytic pocket descriptors
    - 320-dim ESM-2 biological foundation sequence embedding
    """
    pocket_feat = extract_enhanced_kinase_features(sequence)    # (100,)
    esm_feat = extract_esm_kinase_representation(sequence)      # (320,)
    return np.concatenate([pocket_feat, esm_feat]).astype(np.float32)


def extract_worldmodel_pair_features(smiles: str, sequence: str) -> np.ndarray:
    """
    Extract 2988-dim combined interaction feature vector for a drug-kinase pair.
    """
    d_vec = extract_worldmodel_drug_features(smiles)
    t_vec = extract_worldmodel_kinase_features(sequence)
    return np.concatenate([d_vec, t_vec]).astype(np.float32)
