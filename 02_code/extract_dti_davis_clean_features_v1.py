"""Extract clean, deterministic features for DAVIS benchmark (v1-20261009).

Guarantees:
1. 100% cross-process deterministic molecular fingerprints via _deterministic_hash.
2. Honest naming of 512D distance-geometry & electrotopological manifold baseline.
3. Full sequence coverage of long kinases (>1022 aa) using sliding window pooling.
4. Preserves identical drug and target index ordering as historical runs.
"""
import os
import sys
import json
import shutil
import hashlib
import numpy as np
import pandas as pd

PROJECT_ROOT = r"D:\桌面文件\sci"
CODE_DIR = os.path.join(PROJECT_ROOT, "02_code")
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from extract_worldmodel_features import (
    extract_worldmodel_drug_features,
    extract_worldmodel_kinase_features
)

def compute_file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("======================================================================")
    print("EXTRACTING CLEAN DETERMINISTIC DAVIS FEATURES (20261009_v1)")
    print("======================================================================")

    # Output directory
    out_dir = os.path.join(PROJECT_ROOT, r"03_experiments\prepared\dti_davis_clean_features_20261009_v1")
    os.makedirs(out_dir, exist_ok=True)

    # Reference paths
    ref_prep_dir = os.path.join(PROJECT_ROOT, r"03_experiments\prepared\dti_davis_worldmodel_features_20261008_v1")
    davis_csv_path = os.path.join(PROJECT_ROOT, r"03_experiments\audits\dti_davis_acquisition_20261006_v2\davis.csv")

    # Load canonical ID order
    with open(os.path.join(ref_prep_dir, "drug_ids.json"), "r", encoding="utf-8") as f:
        drug_ids = json.load(f)
    with open(os.path.join(ref_prep_dir, "target_ids.json"), "r", encoding="utf-8") as f:
        target_ids = json.load(f)

    print(f"Loaded {len(drug_ids)} drug IDs and {len(target_ids)} target IDs.")

    # Load mappings from davis.csv
    df_davis = pd.read_csv(davis_csv_path)
    drug_to_smi = dict(zip(df_davis["ID1"].astype(str), df_davis["X1"]))
    target_to_seq = dict(zip(df_davis["ID2"].astype(str), df_davis["X2"]))

    # 1. Extract Drug Features (68, 2568)
    print("Extracting deterministic drug features...")
    drug_feats = []
    for d_id in drug_ids:
        smi = drug_to_smi[str(d_id)]
        feat = extract_worldmodel_drug_features(smi)
        drug_feats.append(feat)
    drug_feats_arr = np.array(drug_feats, dtype=np.float32)
    print(f"Drug features extracted: shape={drug_feats_arr.shape}")
    assert drug_feats_arr.shape == (68, 2568), f"Unexpected shape {drug_feats_arr.shape}"

    # 2. Extract Target Features (379, 420)
    print("Extracting full-coverage target features with ESM-2 sliding window...")
    target_feats = []
    for idx, t_id in enumerate(target_ids):
        seq = target_to_seq[str(t_id)]
        feat = extract_worldmodel_kinase_features(seq)
        target_feats.append(feat)
        if (idx + 1) % 100 == 0 or idx + 1 == len(target_ids):
            print(f"  Processed {idx + 1}/{len(target_ids)} targets...")
    target_feats_arr = np.array(target_feats, dtype=np.float32)
    print(f"Target features extracted: shape={target_feats_arr.shape}")
    assert target_feats_arr.shape == (379, 420), f"Unexpected shape {target_feats_arr.shape}"

    # Save arrays
    drug_feat_path = os.path.join(out_dir, "drug_features.npy")
    target_feat_path = os.path.join(out_dir, "target_features.npy")
    np.save(drug_feat_path, drug_feats_arr)
    np.save(target_feat_path, target_feats_arr)

    # Copy ID files and pairs metadata
    shutil.copyfile(os.path.join(ref_prep_dir, "drug_ids.json"), os.path.join(out_dir, "drug_ids.json"))
    shutil.copyfile(os.path.join(ref_prep_dir, "target_ids.json"), os.path.join(out_dir, "target_ids.json"))
    shutil.copyfile(os.path.join(ref_prep_dir, "pairs_metadata.csv"), os.path.join(out_dir, "pairs_metadata.csv"))

    # Feature specification
    feature_spec = {
        "version": "dti_davis_clean_features_20261009_v1",
        "timestamp": "2026-10-09",
        "drug_features": {
            "dim": 2568,
            "components": [
                {"name": "deterministic_morgan_ecfp", "dim": 2048, "algorithm": "Weisfeiler-Lehman + MD5 deterministic hashing"},
                {"name": "physicochemical_descriptors", "dim": 8, "algorithm": "RDKit-compatible MW, LogP, TPSA, HBD, HBA, RotB, Rings, AromRings"},
                {"name": "heuristic_geom_manifold", "dim": 512, "algorithm": "Floyd-Warshall Laplacian spectrum (128D) + Electrotopological state (128D) + Spatial structural manifold (256D)"}
            ]
        },
        "target_features": {
            "dim": 420,
            "components": [
                {"name": "enhanced_kinase_descriptors", "dim": 100, "algorithm": "Amino acid composition & catalytic pocket descriptors"},
                {"name": "esm2_foundation_representation", "dim": 320, "algorithm": "fair-esm esm2_t6_8M_UR50D mean pooling with sliding-window full coverage (window=1022, step=512)"}
            ]
        }
    }
    with open(os.path.join(out_dir, "feature_spec.json"), "w", encoding="utf-8") as f:
        json.dump(feature_spec, f, indent=2, ensure_ascii=False)

    # Manifest
    manifest = {
        "dataset": "DAVIS",
        "created_at": "2026-10-09",
        "files": {
            "drug_features.npy": {
                "shape": list(drug_feats_arr.shape),
                "sha256": compute_file_sha256(drug_feat_path)
            },
            "target_features.npy": {
                "shape": list(target_feats_arr.shape),
                "sha256": compute_file_sha256(target_feat_path)
            },
            "pairs_metadata.csv": {
                "sha256": compute_file_sha256(os.path.join(out_dir, "pairs_metadata.csv"))
            }
        }
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("======================================================================")
    print("SUCCESS: Clean features saved to:", out_dir)
    print(f"  drug_features.npy: {drug_feats_arr.shape}, SHA256: {manifest['files']['drug_features.npy']['sha256']}")
    print(f"  target_features.npy: {target_feats_arr.shape}, SHA256: {manifest['files']['target_features.npy']['sha256']}")
    print("======================================================================")

if __name__ == "__main__":
    main()
