"""Prepare world-model-enhanced features (Uni-Mol + ESM-2) for the 25,772 DAVIS pairs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import time
import numpy as np

from extract_worldmodel_features import (
    extract_worldmodel_drug_features,
    extract_worldmodel_kinase_features,
)
from research_utils import ROOT, sha256, utc_now


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=ROOT / "03_experiments/protocols/protocol-dti-01.json")
    parser.add_argument("--input-features-dir", type=Path, default=ROOT / "03_experiments/prepared/dti_davis_enhanced_features_20261007_v1")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "03_experiments/prepared/dti_davis_worldmodel_features_20261008_v1")
    args = parser.parse_args()

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    with args.protocol.open("r", encoding="utf-8") as f:
        proto = json.load(f)

    # Load drug & target mapping from existing verified features dir
    in_dir = args.input_features_dir.resolve()
    with (in_dir / "drug_ids.json").open("r", encoding="utf-8") as f:
        drug_ids = json.load(f)
    with (in_dir / "target_ids.json").open("r", encoding="utf-8") as f:
        target_ids = json.load(f)

    # Read davis.csv to retrieve original sequences and smiles
    davis_csv = ROOT / proto["source_data"]["path"]
    drug_smiles_map = {}
    target_seq_map = {}
    with davis_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d_id = str(row["ID1"])
            t_id = str(row["ID2"])
            if d_id not in drug_smiles_map:
                drug_smiles_map[d_id] = row["X1"]
            if t_id not in target_seq_map:
                target_seq_map[t_id] = row["X2"]

    print(f"Extracting Uni-Mol 3D representations for {len(drug_ids)} clinical kinase inhibitors...")
    t0 = time.time()
    drug_wm_list = []
    for d_id in drug_ids:
        smi = drug_smiles_map[d_id]
        vec = extract_worldmodel_drug_features(smi)
        drug_wm_list.append(vec)
    drug_wm_matrix = np.stack(drug_wm_list, axis=0).astype(np.float32)
    print(f"Drug features extracted: shape {drug_wm_matrix.shape} in {time.time() - t0:.2f}s")

    print(f"Extracting ESM-2 biological representations for {len(target_ids)} protein kinases...")
    t1 = time.time()
    target_wm_list = []
    for idx, t_id in enumerate(target_ids):
        seq = target_seq_map[t_id]
        vec = extract_worldmodel_kinase_features(seq)
        target_wm_list.append(vec)
        if (idx + 1) % 50 == 0:
            print(f"  Processed {idx + 1}/{len(target_ids)} kinases...")
    target_wm_matrix = np.stack(target_wm_list, axis=0).astype(np.float32)
    print(f"Target features extracted: shape {target_wm_matrix.shape} in {time.time() - t1:.2f}s")

    # Save arrays
    np.save(out_dir / "drug_features.npy", drug_wm_matrix)
    np.save(out_dir / "target_features.npy", target_wm_matrix)

    with (out_dir / "drug_ids.json").open("w", encoding="utf-8") as f:
        json.dump(drug_ids, f, indent=2)
    with (out_dir / "target_ids.json").open("w", encoding="utf-8") as f:
        json.dump(target_ids, f, indent=2)

    # Copy pairs metadata
    import shutil
    shutil.copy(in_dir / "pairs_metadata.csv", out_dir / "pairs_metadata.csv")
    if (in_dir / "drug_names.json").exists():
        shutil.copy(in_dir / "drug_names.json", out_dir / "drug_names.json")

    # Compute manifest hashes
    outputs = {
        "drug_features.npy": sha256(out_dir / "drug_features.npy"),
        "target_features.npy": sha256(out_dir / "target_features.npy"),
        "drug_ids.json": sha256(out_dir / "drug_ids.json"),
        "target_ids.json": sha256(out_dir / "target_ids.json"),
        "pairs_metadata.csv": sha256(out_dir / "pairs_metadata.csv"),
    }
    manifest = {
        "status": "prepared",
        "protocol_id": proto["protocol_id"],
        "generated_at": utc_now(),
        "drug_feature_dim": int(drug_wm_matrix.shape[1]),
        "target_feature_dim": int(target_wm_matrix.shape[1]),
        "num_drugs": len(drug_ids),
        "num_targets": len(target_ids),
        "total_pairs": 25772,
        "outputs": outputs
    }
    with (out_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Successfully prepared world-model features in {out_dir}")


if __name__ == "__main__":
    main()
