"""Extract ESM-2 biological foundation representations for protein kinases (320-dim).

Uses fair-esm pretrained esm2_t6_8M_UR50D encoder with mean-pooling over sequence tokens.
Includes in-memory LRU-like caching and safe context truncation for long kinase domains.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional
import numpy as np
import torch

_ESM_MODEL = None
_ESM_BATCH_CONVERTER = None
_ESM_CACHE: Dict[str, np.ndarray] = {}
logger = logging.getLogger(__name__)


def _get_esm_model():
    global _ESM_MODEL, _ESM_BATCH_CONVERTER
    if _ESM_MODEL is None:
        import esm
        _ESM_MODEL, alphabet = esm.pretrained.esm2_t6_8M_UR50D()
        _ESM_MODEL.eval()
        _ESM_BATCH_CONVERTER = alphabet.get_batch_converter()
    return _ESM_MODEL, _ESM_BATCH_CONVERTER


def extract_esm_kinase_representation(sequence: str, strict: bool = True) -> np.ndarray:
    """
    Extract 320-dim ESM-2 foundation embedding for a kinase sequence.
    For sequences > 1022 residues, uses sliding window (window=1022, step=512)
    to cover full-length sequences without truncating C-terminal kinase domains.
    In strict mode (default=True), raises RuntimeError if PyTorch/ESM fails, preventing silent fallback.
    """
    clean_seq = "".join(sequence.split()).upper()
    if not clean_seq:
        return np.zeros(320, dtype=np.float32)

    if clean_seq in _ESM_CACHE:
        return _ESM_CACHE[clean_seq].copy()

    try:
        model, batch_converter = _get_esm_model()
        seq_len = len(clean_seq)

        if seq_len <= 1022:
            data = [("query_kinase", clean_seq)]
            _, _, batch_tokens = batch_converter(data)
            with torch.no_grad():
                results = model(batch_tokens, repr_layers=[6])
                # Exclude <cls> (idx 0) and <eos> (idx -1) tokens
                token_rep = results["representations"][6][0, 1:-1]
                pooled = token_rep.mean(dim=0).cpu().numpy().astype(np.float32)
        else:
            # Multi-window sliding coverage for long kinase domains
            window_size = 1022
            step = 512
            windows = []
            start = 0
            while start < seq_len:
                end = min(start + window_size, seq_len)
                windows.append(clean_seq[start:end])
                if end == seq_len:
                    break
                start += step
                if start + window_size > seq_len:
                    windows.append(clean_seq[max(0, seq_len - window_size):seq_len])
                    break

            window_reps = []
            for w_seq in windows:
                data = [("query_window", w_seq)]
                _, _, batch_tokens = batch_converter(data)
                with torch.no_grad():
                    results = model(batch_tokens, repr_layers=[6])
                    token_rep = results["representations"][6][0, 1:-1]
                    w_pooled = token_rep.mean(dim=0).cpu().numpy().astype(np.float32)
                    window_reps.append(w_pooled)

            pooled = np.mean(window_reps, axis=0).astype(np.float32)

        _ESM_CACHE[clean_seq] = pooled
        return pooled.copy()
    except Exception as exc:
        logger.error("ESM-2 model execution failed: %s", exc)
        if strict:
            raise RuntimeError(f"ESM-2 representation extraction strictly failed for sequence length {len(clean_seq)}: {exc}") from exc
        # Only in non-strict mode, provide isolated fallback without polluting _ESM_CACHE
        from extract_dti_davis_enhanced_features import extract_enhanced_kinase_features
        feat = extract_enhanced_kinase_features(clean_seq)
        fallback = np.tile(feat, 4)[:320].astype(np.float32)
        return fallback.copy()


def batch_extract_esm_kinase_representations(sequences: List[str], batch_size: int = 16) -> np.ndarray:
    """Batch extract 320-dim ESM-2 representations for multiple sequences."""
    results = []
    for seq in sequences:
        results.append(extract_esm_kinase_representation(seq))
    return np.stack(results, axis=0).astype(np.float32)
