"""Extract immutable molecular and protein features for DAVIS benchmark under frozen protocol."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np

from dti_source_preflight import PROTECTED, save
from research_utils import ROOT, sha256, utc_now
from test_molecular_similarity import get_morgan_fingerprint


STANDARD_AMINO_ACIDS = [
    'A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L',
    'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'Y'
]

KYTE_DOOLITTLE = {
    'A': 1.8, 'C': 2.5, 'D': -3.5, 'E': -3.5, 'F': 2.8,
    'G': -0.4, 'H': -3.2, 'I': 4.5, 'K': -3.9, 'L': 3.8,
    'M': 1.9, 'N': -3.5, 'P': -1.6, 'Q': -3.5, 'R': -4.5,
    'S': -0.8, 'T': -0.7, 'V': 4.2, 'W': -0.9, 'Y': -1.3
}

CHARGE_ESTIMATE = {
    'K': 1.0, 'R': 1.0, 'H': 0.1,
    'D': -1.0, 'E': -1.0
}

BOMAN_INDEX_MAP = {
    'L': -4.92, 'I': -4.92, 'V': -4.04, 'F': -2.98, 'W': -2.33,
    'A': -1.81, 'M': -1.45, 'C': -1.28, 'G': -0.94, 'Y': -0.14,
    'T': 2.57, 'S': 3.40, 'H': 4.66, 'Q': 5.54, 'K': 5.55,
    'N': 6.64, 'E': 6.81, 'D': 8.72, 'R': 9.38, 'P': 0.0
}


def extract_protein_features(seq: str) -> np.ndarray:
    """Compute 20-dim AAC and 8-dim physicochemical descriptors for protein kinase sequence."""
    length = len(seq)
    if length == 0:
        raise ValueError("Empty sequence")
    
    # 20-dim Amino Acid Composition
    counts = {aa: 0 for aa in STANDARD_AMINO_ACIDS}
    for aa in seq:
        if aa in counts:
            counts[aa] += 1
    aac = [counts[aa] / length for aa in STANDARD_AMINO_ACIDS]

    # Physicochemical descriptors
    hydro_values = [KYTE_DOOLITTLE.get(aa, 0.0) for aa in seq]
    mean_hydro = float(np.mean(hydro_values))
    hydro_ratio = sum(1 for aa in seq if KYTE_DOOLITTLE.get(aa, 0.0) > 0.0) / length
    net_charge = sum(CHARGE_ESTIMATE.get(aa, 0.0) for aa in seq)
    charge_density = net_charge / length
    cationic_ratio = sum(1 for aa in seq if aa in ['K', 'R']) / length
    boman_idx = sum(BOMAN_INDEX_MAP.get(aa, 0.0) for aa in seq) / length

    props = [
        float(length) / 1000.0,
        mean_hydro / 4.5,
        net_charge / 50.0,
        charge_density,
        hydro_ratio,
        cationic_ratio,
        boman_idx / 5.0,
        1.0 if 'C' in counts and counts['C'] > 0 else 0.0
    ]
    return np.array(aac + props, dtype=np.float32)


def compute_pkd(kd_nM: float) -> float:
    """Compute pKd from Kd in nM. Censored at 10,000 nM -> pKd = 5.0."""
    if kd_nM >= 10000.0 or kd_nM <= 0.0:
        return 5.0
    return float(9.0 - math.log10(kd_nM))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError(f"Output directory already exists: {args.output}")

    # Check protected files before execution
    before = {p: sha256(ROOT / p) for p in PROTECTED}

    protocol_path = args.protocol.resolve()
    with protocol_path.open("r", encoding="utf-8") as f:
        proto = json.load(f)

    # Validate protocol status
    assert proto["protocol_id"] == "protocol-dti-01", "Protocol mismatch"
    assert proto["status"] == "frozen_dti_davis_benchmark", "Protocol not frozen"

    davis_csv_path = ROOT / proto["source_data"]["path"]
    fold_path = ROOT / proto["isolation_audit"]["fold_memberships_path"]

    assert sha256(davis_csv_path) == proto["source_data"]["sha256"], "davis.csv hash mismatch"
    assert sha256(fold_path) == proto["isolation_audit"]["fold_memberships_sha256"], "folds hash mismatch"

    with fold_path.open("r", encoding="utf-8") as f:
        fold_data = json.load(f)

    drug_fold_map = {}
    for fold_name, d_ids in fold_data["drug_folds"].items():
        fold_idx = int(fold_name.split("_")[1])
        for d_id in d_ids:
            drug_fold_map[str(d_id)] = fold_idx

    target_fold_map = {}
    for fold_name, t_ids in fold_data["target_folds"].items():
        fold_idx = int(fold_name.split("_")[1])
        for t_id in t_ids:
            target_fold_map[str(t_id)] = fold_idx

    # Read DAVIS data
    drugs_dict = {}   # id -> smiles
    targets_dict = {} # id -> seq
    pairs = []

    with davis_csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            d_id = str(row["ID1"])
            t_id = str(row["ID2"])
            d_smiles = row["X1"]
            t_seq = row["X2"]
            kd = float(row["Y"])

            if d_id not in drugs_dict:
                drugs_dict[d_id] = d_smiles
            if t_id not in targets_dict:
                targets_dict[t_id] = t_seq

            pkd = compute_pkd(kd)
            d_fold = drug_fold_map[d_id]
            t_fold = target_fold_map[t_id]

            # Domain determination
            if d_fold <= 4 and t_fold <= 4:
                domain = "train_block"
            elif d_fold == 5 and t_fold == 5:
                domain = "strict_dual_cold_test"
            elif d_fold <= 4 and t_fold == 5:
                domain = "cold_target_test"
            elif d_fold == 5 and t_fold <= 4:
                domain = "cold_drug_test"
            else:
                raise ValueError(f"Unmatched domain for fold ({d_fold}, {t_fold})")

            pairs.append({
                "pair_idx": idx,
                "drug_id": d_id,
                "target_id": t_id,
                "kd_nM": kd,
                "pkd": pkd,
                "drug_fold": d_fold,
                "target_fold": t_fold,
                "domain": domain
            })

    assert len(drugs_dict) == 68, f"Expected 68 drugs, got {len(drugs_dict)}"
    assert len(targets_dict) == 379, f"Expected 379 targets, got {len(targets_dict)}"
    assert len(pairs) == 25772, f"Expected 25772 pairs, got {len(pairs)}"

    # Sort drug and target keys for deterministic indexing
    sorted_drugs = sorted(drugs_dict.keys())
    sorted_targets = sorted(targets_dict.keys())
    drug_to_idx = {d: i for i, d in enumerate(sorted_drugs)}
    target_to_idx = {t: i for i, t in enumerate(sorted_targets)}

    print(f"Computing 2048-dim Morgan fingerprints for {len(sorted_drugs)} small molecules...")
    drug_features = np.zeros((len(sorted_drugs), 2048), dtype=np.float32)
    for i, d_id in enumerate(sorted_drugs):
        smiles = drugs_dict[d_id]
        fp = get_morgan_fingerprint(smiles, radius=2, n_bits=2048)
        drug_features[i] = fp

    print(f"Computing 28-dim AAC & physicochemical features for {len(sorted_targets)} kinase proteins...")
    target_features = np.zeros((len(sorted_targets), 28), dtype=np.float32)
    for i, t_id in enumerate(sorted_targets):
        seq = targets_dict[t_id]
        feat = extract_protein_features(seq)
        target_features[i] = feat

    # Verify domain counts match protocol specification exactly
    domain_counts = {}
    for p in pairs:
        dom = p["domain"]
        domain_counts[dom] = domain_counts.get(dom, 0) + 1

    expected_domains = proto["domains"]
    assert domain_counts["train_block"] == expected_domains["train_block"]["pairs"], "train_block count mismatch"
    assert domain_counts["strict_dual_cold_test"] == expected_domains["strict_dual_cold_test"]["pairs"], "strict_dual_cold mismatch"
    assert domain_counts["cold_target_test"] == expected_domains["cold_target_test"]["pairs"], "cold_target mismatch"
    assert domain_counts["cold_drug_test"] == expected_domains["cold_drug_test"]["pairs"], "cold_drug mismatch"

    args.output.mkdir(parents=True, exist_ok=True)

    # Save features and metadata
    drug_feat_path = args.output / "drug_features.npy"
    target_feat_path = args.output / "target_features.npy"
    np.save(drug_feat_path, drug_features)
    np.save(target_feat_path, target_features)

    drug_ids_path = args.output / "drug_ids.json"
    target_ids_path = args.output / "target_ids.json"
    save(drug_ids_path, sorted_drugs)
    save(target_ids_path, sorted_targets)

    pairs_csv_path = args.output / "pairs_metadata.csv"
    with pairs_csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "pair_idx", "drug_id", "target_id", "kd_nM", "pkd",
            "drug_fold", "target_fold", "domain"
        ])
        writer.writeheader()
        writer.writerows(pairs)

    # Summary manifest
    outputs = {
        "drug_features.npy": sha256(drug_feat_path),
        "target_features.npy": sha256(target_feat_path),
        "drug_ids.json": sha256(drug_ids_path),
        "target_ids.json": sha256(target_ids_path),
        "pairs_metadata.csv": sha256(pairs_csv_path)
    }

    manifest = {
        "generated_at": utc_now(),
        "protocol_id": "protocol-dti-01",
        "num_drugs": 68,
        "drug_feature_dim": 2048,
        "num_targets": 379,
        "target_feature_dim": 28,
        "total_pairs": 25772,
        "domain_distribution": domain_counts,
        "outputs": outputs
    }
    manifest_path = args.output / "manifest.json"
    save(manifest_path, manifest)

    # Protected files check after execution
    after = {p: sha256(ROOT / p) for p in PROTECTED}
    assert before == after, "PROTECTED files changed during feature extraction!"

    state = {
        "generated_at": utc_now(),
        "status": "davis_features_extracted_ready_for_baselines",
        "protocol_id": "protocol-dti-01",
        "training_ready": true if False else False,
        "total_pairs": 25772,
        "domain_counts": domain_counts,
        "inputs": {
            "protocol": sha256(protocol_path),
            "davis_csv": sha256(davis_csv_path),
            "fold_memberships": sha256(fold_path)
        },
        "outputs": {k: v for k, v in outputs.items()}
    }
    state["outputs"]["manifest.json"] = sha256(manifest_path)
    save(args.output / "state.json", state)

    print("Feature extraction successfully completed and verified.")
    print(f"Manifest and state saved to {args.output}")


if __name__ == "__main__":
    main()
