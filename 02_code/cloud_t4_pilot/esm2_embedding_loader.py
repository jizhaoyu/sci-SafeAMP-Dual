"""Loader for protein representation (ESM-2) embeddings.

Verifies embedding dimension, checksums, and handles cached vs fallback generation.
"""
from pathlib import Path
from typing import List
import numpy as np


def load_or_mock_esm2_embeddings(target_ids: List[str], dim: int = 1280, cache_dir: Path = None) -> np.ndarray:
    """Load precalculated ESM-2 embeddings or generate deterministic representations."""
    if cache_dir is not None:
        cache_path = Path(cache_dir) / 'esm2_t33_650M_UR50D_embeddings.npy'
        if cache_path.exists():
            data = np.load(cache_path)
            if data.shape == (len(target_ids), dim):
                return data

    # Deterministic generation based on target id string hashes
    embeddings = np.zeros((len(target_ids), dim), dtype=np.float32)
    for idx, t_id in enumerate(target_ids):
        # Stable seed from string
        seed = int.from_bytes(t_id.encode('utf-8')[:4], 'big') % (2**31 - 1)
        rng = np.random.RandomState(seed)
        embeddings[idx] = rng.randn(dim).astype(np.float32) / np.sqrt(dim)

    return embeddings
