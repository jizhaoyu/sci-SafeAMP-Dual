"""Extract deterministic ESM-2 (esm2_t6_8M_UR50D, layer 6 mean-pooled) representations for 17 expanded MIC molecules."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import esm
import numpy as np
import pandas as pd
import torch

from research_utils import ROOT, sha256, utc_now, write_json

CANDIDATES = ROOT / "03_experiments/audits/mic_source_expansion_result_20261002_v2/candidate_molecules.csv"
MODEL_NAME = "esm2_t6_8M_UR50D"
LAYER = 6
EMBED_DIM = 320


def extract_features(candidates_csv: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(candidates_csv, keep_default_na=False)
    if len(df) != 17 or not df["sample_id"].is_unique or not df["seq"].is_unique:
        raise ValueError(f"Expected 17 unique candidate molecules, found {len(df)}")

    # Load frozen pretrained ESM-2 model and alphabet
    model, alphabet = esm.pretrained.esm2_t6_8M_UR50D()
    batch_converter = alphabet.get_batch_converter()
    model.eval()

    data = list(zip(df["sample_id"], df["seq"]))
    batch_labels, batch_strs, batch_tokens = batch_converter(data)

    with torch.no_grad():
        results = model(batch_tokens, repr_layers=[LAYER], return_contacts=False)
        rep = results["representations"][LAYER]
        pooled_vectors = []
        per_seq_stats = []
        for i, (sample_id, seq) in enumerate(zip(df["sample_id"], df["seq"])):
            seq_len = len(seq)
            # Index 0 is <cls>, indices 1 to seq_len are residue tokens, index seq_len+1 is <eos>
            res_rep = rep[i, 1 : seq_len + 1]
            vec = res_rep.mean(dim=0).cpu().numpy().astype(np.float32)
            pooled_vectors.append(vec)
            per_seq_stats.append({
                "sample_id": sample_id,
                "seq_len": seq_len,
                "vector_mean": float(vec.mean()),
                "vector_std": float(vec.std()),
                "vector_norm": float(np.linalg.norm(vec)),
            })

    matrix = np.stack(pooled_vectors, axis=0)
    if matrix.shape != (17, EMBED_DIM):
        raise ValueError(f"Expected shape (17, {EMBED_DIM}), got {matrix.shape}")
    if not np.isfinite(matrix).all():
        raise ValueError("Non-finite values encountered in extracted ESM-2 embeddings")

    npy_path = output_dir / "esm2_features.npy"
    meta_path = output_dir / "esm2_features_meta.json"

    np.save(npy_path, matrix)

    meta = {
        "status": "esm2_features_extracted",
        "generated_at": utc_now(),
        "model_name": MODEL_NAME,
        "model_parameters": 8_000_000,
        "representation_layer": LAYER,
        "embedding_dimensions": EMBED_DIM,
        "pooling": "mean_across_residues_excluding_special_tokens",
        "cohort_source": str(candidates_csv.relative_to(ROOT)),
        "cohort_csv_sha256": sha256(candidates_csv),
        "molecules_count": len(df),
        "feature_shape": list(matrix.shape),
        "npy_file": str(npy_path.relative_to(ROOT)),
        "npy_sha256": sha256(npy_path),
        "per_sequence_summary": per_seq_stats,
    }
    write_json(meta_path, meta)
    return meta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=CANDIDATES)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "03_experiments/features/mic_expanded_17")
    args = parser.parse_args()
    res = extract_features(args.candidates, args.output_dir)
    print(json.dumps({k: res[k] for k in ("status", "model_name", "feature_shape", "npy_file", "npy_sha256")}, indent=2))
