"""Extract enhanced kinase domain features (100-dim) and molecular descriptors for DAVIS benchmark under frozen protocol."""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
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

AA_CLASS = {
    'A': 0, 'V': 0, 'L': 0, 'I': 0, 'P': 0, 'F': 0, 'W': 0, 'M': 0, # Hydrophobic nonpolar
    'G': 1, 'S': 1, 'T': 1, 'C': 1, 'Y': 1, 'N': 1, 'Q': 1,         # Polar neutral
    'K': 2, 'R': 2, 'H': 2,                                         # Basic (+)
    'D': 3, 'E': 3                                                  # Acidic (-)
}


def extract_enhanced_kinase_features(seq: str) -> np.ndarray:
    """Compute 100-dim kinase domain-aware descriptors."""
    seq = "".join(seq.split()).upper()
    length = len(seq)
    if length == 0:
        raise ValueError("Empty sequence")
    
    # 1. 20-dim AAC
    counts = {aa: 0 for aa in STANDARD_AMINO_ACIDS}
    for aa in seq:
        if aa in counts:
            counts[aa] += 1
    aac = [counts[aa] / length for aa in STANDARD_AMINO_ACIDS]

    # 2. 8-dim Global physicochemical descriptors
    hydro_values = [KYTE_DOOLITTLE.get(aa, 0.0) for aa in seq]
    mean_hydro = float(np.mean(hydro_values))
    hydro_ratio = sum(1 for aa in seq if KYTE_DOOLITTLE.get(aa, 0.0) > 0.0) / length
    net_charge = sum(CHARGE_ESTIMATE.get(aa, 0.0) for aa in seq)
    charge_density = net_charge / length
    cationic_ratio = sum(1 for aa in seq if aa in ['K', 'R']) / length
    boman_idx = sum(BOMAN_INDEX_MAP.get(aa, 0.0) for aa in seq) / length

    global_props = [
        float(length) / 1000.0,
        mean_hydro / 4.5,
        net_charge / 50.0,
        charge_density,
        hydro_ratio,
        cationic_ratio,
        boman_idx / 5.0,
        1.0 if counts.get('C', 0) > 0 else 0.0
    ]

    # 3. 24-dim Segmented CTD (N-lobe, Core Catalytic Domain, C-lobe)
    part_len = max(1, length // 3)
    p1 = seq[:part_len]
    p2 = seq[part_len:part_len * 2]
    p3 = seq[part_len * 2:]
    
    ctd_props = []
    for part in [p1, p2, p3]:
        p_len = len(part)
        if p_len == 0:
            ctd_props.extend([0.0] * 8)
            continue
        h_ratio = sum(1 for aa in part if aa in 'AVILMFWP') / p_len
        pos_ratio = sum(1 for aa in part if aa in 'KRH') / p_len
        neg_ratio = sum(1 for aa in part if aa in 'DE') / p_len
        aro_ratio = sum(1 for aa in part if aa in 'FYW') / p_len
        polar_ratio = sum(1 for aa in part if aa in 'STCYNQ') / p_len
        gp_ratio = sum(1 for aa in part if aa in 'GP') / p_len
        p_hydro = float(np.mean([KYTE_DOOLITTLE.get(aa, 0.0) for aa in part])) / 4.5
        p_charge = float(sum(CHARGE_ESTIMATE.get(aa, 0.0) for aa in part)) / (p_len + 1e-5)
        ctd_props.extend([h_ratio, pos_ratio, neg_ratio, aro_ratio, polar_ratio, gp_ratio, p_hydro, p_charge])

    # 4. 16-dim Kinase Catalytic Motif Profiling
    motifs = [
        ('g_loop', r'[VILM]G[A-Z]G[A-Z]{2}[GAK]'),
        ('vaik', r'[VILM][A-Z][ILVM][K]'),
        ('hrd', r'[HY]RD[LIVM][KRN]'),
        ('dfg', r'DFG|DYG')
    ]
    motif_features = []
    for m_name, pat in motifs:
        m = re.search(pat, seq)
        if m:
            start_pos = m.start()
            rel_pos = start_pos / length
            matched_sub = m.group(0)
            sub_hydro = float(np.mean([KYTE_DOOLITTLE.get(aa, 0.0) for aa in matched_sub])) / 4.5
            sub_charge = float(sum(CHARGE_ESTIMATE.get(aa, 0.0) for aa in matched_sub))
            motif_features.extend([1.0, rel_pos, sub_hydro, sub_charge])
        else:
            motif_features.extend([0.0, 0.0, 0.0, 0.0])

    # 5. 32-dim Conjoint Dipeptide Classification
    adj_matrix = np.zeros((4, 4), dtype=np.float32)
    skip_matrix = np.zeros((4, 4), dtype=np.float32)
    
    for i in range(length - 1):
        c1 = AA_CLASS.get(seq[i])
        c2 = AA_CLASS.get(seq[i + 1])
        if c1 is not None and c2 is not None:
            adj_matrix[c1, c2] += 1.0
            
    for i in range(length - 2):
        c1 = AA_CLASS.get(seq[i])
        c3 = AA_CLASS.get(seq[i + 2])
        if c1 is not None and c3 is not None:
            skip_matrix[c1, c3] += 1.0

    denom1 = max(1.0, length - 1)
    denom2 = max(1.0, length - 2)
    conjoint_features = list((adj_matrix / denom1).flatten()) + list((skip_matrix / denom2).flatten())

    vec = np.array(aac + global_props + ctd_props + motif_features + conjoint_features, dtype=np.float32)
    return vec


def extract_enhanced_drug_features(smiles: str) -> np.ndarray:
    """Compute 2056-dim molecular features (2048-dim Morgan fingerprint + 8-dim global descriptors)."""
    fp = get_morgan_fingerprint(smiles, radius=2, n_bits=2048)
    
    # 8-dim molecular descriptors from SMILES
    s_clean = smiles.strip()
    s_len = len(s_clean)
    num_c = s_clean.count('C') + s_clean.count('c')
    num_n = s_clean.count('N') + s_clean.count('n')
    num_o = s_clean.count('O') + s_clean.count('o')
    num_f = s_clean.count('F')
    num_cl = s_clean.count('Cl') + s_clean.count('cl')
    num_s = s_clean.count('S') + s_clean.count('s')
    num_arom = sum(1 for c in s_clean if c.islower())
    num_rings = sum(1 for c in s_clean if c.isdigit())
    
    desc = [
        float(s_len) / 100.0,
        float(num_c) / max(1.0, s_len),
        float(num_n + num_o) / max(1.0, s_len),
        float(num_f + num_cl) / max(1.0, s_len),
        float(num_s) / max(1.0, s_len),
        float(num_arom) / max(1.0, s_len),
        float(num_rings) / 10.0,
        float(fp.sum()) / 2048.0
    ]
    return np.concatenate([fp, np.array(desc, dtype=np.float32)])


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

    # Check protected files
    before = {p: sha256(ROOT / p) for p in PROTECTED}

    protocol_path = args.protocol.resolve()
    with protocol_path.open("r", encoding="utf-8") as f:
        proto = json.load(f)

    assert proto["protocol_id"] == "protocol-dti-01", "Protocol mismatch"
    assert proto["status"] == "frozen_dti_davis_benchmark", "Protocol not frozen"

    # Load fold memberships
    fold_path = ROOT / proto["isolation_audit"]["fold_memberships_path"]
    with fold_path.open("r", encoding="utf-8") as f:
        folds_data = json.load(f)

    drug_to_fold = {}
    for fold_name, d_ids in folds_data["drug_folds"].items():
        f_idx = int(fold_name.split("_")[1])
        for d_id in d_ids:
            drug_to_fold[str(d_id)] = f_idx

    target_to_fold = {}
    for fold_name, t_ids in folds_data["target_folds"].items():
        f_idx = int(fold_name.split("_")[1])
        for t_id in t_ids:
            target_to_fold[str(t_id)] = f_idx

    # Load source CSV
    davis_csv_path = ROOT / proto["source_data"]["path"]
    drugs_dict = {}
    targets_dict = {}
    pairs_list = []

    with davis_csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d_id = str(row["ID1"])
            t_id = str(row["ID2"])
            smiles = row["X1"]
            seq = "".join(row["X2"].split()).upper()
            kd_val = float(row["Y"])
            pkd_val = compute_pkd(kd_val)

            if d_id not in drugs_dict:
                drugs_dict[d_id] = smiles
            if t_id not in targets_dict:
                targets_dict[t_id] = seq

            d_fold = drug_to_fold[d_id]
            t_fold = target_to_fold[t_id]

            if d_fold <= 4 and t_fold <= 4:
                domain = "train_block"
            elif d_fold == 5 and t_fold == 5:
                domain = "strict_dual_cold_test"
            elif d_fold <= 4 and t_fold == 5:
                domain = "cold_target_test"
            elif d_fold == 5 and t_fold <= 4:
                domain = "cold_drug_test"
            else:
                raise ValueError("Invalid domain split")

            pairs_list.append({
                "drug_id": d_id,
                "target_id": t_id,
                "smiles": smiles,
                "target_seq": seq,
                "kd_nM": kd_val,
                "pkd": pkd_val,
                "drug_fold": d_fold,
                "target_fold": t_fold,
                "domain": domain
            })

    unique_drug_ids = sorted(drugs_dict.keys(), key=lambda x: int(x))
    unique_target_ids = sorted(targets_dict.keys())

    print(f"Extracting enhanced features for {len(unique_drug_ids)} drugs and {len(unique_target_ids)} targets...")

    drug_features = []
    for d_id in unique_drug_ids:
        s = drugs_dict[d_id]
        drug_features.append(extract_enhanced_drug_features(s))
    drug_features = np.array(drug_features, dtype=np.float32)

    target_features = []
    for t_id in unique_target_ids:
        seq = targets_dict[t_id]
        target_features.append(extract_enhanced_kinase_features(seq))
    target_features = np.array(target_features, dtype=np.float32)

    print(f"Drug features shape: {drug_features.shape} (2056-dim)")
    print(f"Target features shape: {target_features.shape} (100-dim)")

    # Write outputs
    args.output.mkdir(parents=True, exist_ok=True)
    np.save(args.output / "drug_features.npy", drug_features)
    np.save(args.output / "target_features.npy", target_features)

    with (args.output / "drug_ids.json").open("w", encoding="utf-8") as f:
        json.dump(unique_drug_ids, f, indent=2)

    with (args.output / "target_ids.json").open("w", encoding="utf-8") as f:
        json.dump(unique_target_ids, f, indent=2)

    with (args.output / "pairs_metadata.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "drug_id", "target_id", "smiles", "kd_nM", "pkd",
            "drug_fold", "target_fold", "domain"
        ])
        writer.writeheader()
        for p in pairs_list:
            writer.writerow({
                "drug_id": p["drug_id"],
                "target_id": p["target_id"],
                "smiles": p["smiles"],
                "kd_nM": p["kd_nM"],
                "pkd": p["pkd"],
                "drug_fold": p["drug_fold"],
                "target_fold": p["target_fold"],
                "domain": p["domain"]
            })

    # Save feature spec
    spec = {
        "drug_feature_type": "Morgan Fingerprint (r=2, 2048-dim) + 8-dim Global PhysChem Descriptors",
        "drug_dim": int(drug_features.shape[1]),
        "target_feature_type": "AAC (20) + Global PhysChem (8) + Segmented CTD (24) + Kinase Motifs (16) + Conjoint Dipeptides (32)",
        "target_dim": int(target_features.shape[1]),
        "total_concatenated_dim": int(drug_features.shape[1] + target_features.shape[1]),
        "num_drugs": len(unique_drug_ids),
        "num_targets": len(unique_target_ids),
        "total_pairs": len(pairs_list)
    }
    with (args.output / "feature_spec.json").open("w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)

    # Manifest
    outputs = {}
    for fname in ["drug_features.npy", "target_features.npy", "drug_ids.json", "target_ids.json", "pairs_metadata.csv", "feature_spec.json"]:
        outputs[fname] = sha256(args.output / fname)

    manifest = {
        "generated_at": utc_now(),
        "protocol_id": proto["protocol_id"],
        "outputs": outputs
    }
    with (args.output / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Verify protected files
    after = {p: sha256(ROOT / p) for p in PROTECTED}
    for p in PROTECTED:
        assert before[p] == after[p], f"Protected file changed: {p}"

    print(f"Enhanced feature extraction complete. Artifacts saved in {args.output}")


if __name__ == "__main__":
    main()
