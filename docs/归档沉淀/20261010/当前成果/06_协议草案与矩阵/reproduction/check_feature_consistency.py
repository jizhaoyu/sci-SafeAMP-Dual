"""Feature consistency, tensor shape, and cross-process reproducibility check.

Protocol v5 Specification:
- Explicit shape assertions: Drug (2568,), Target (420,).
- Explicit finite value validation: np.all(np.isfinite(...)).
- Explicit process exit codes: sys.exit(0) on PASS, sys.exit(1) on FAIL.
- Accurate target metadata: CDK2 (298), SRC (536), MET(Y1235D) (1390),
  INSR (1382), EGFR(T790M) (1210), MTOR (2549).
- Explicit sliding-window pooling documentation: overlapping residues receive higher effective weight
  in equal-weighted window mean pooling; 100% sequence coverage does not prove 3D active site conformation recovery.
- Strict bounded execution: 10 drugs, 6 targets, local weights only, no downloads.
"""
from __future__ import annotations

import os
import sys
import json
import time
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SYS_PY = sys.executable

WORK_DIR = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "03_experiments/prepared/dti_davis_clean_features_20261009_v1"
OUT_JSON = WORK_DIR / "feature_consistency_audit.json"

SELECTED_DRUG_IDS = [
    "5291", "44259", "123631", "126565", "151194",
    "153999", "156414", "3038522", "6918454", "10184653"
]

SELECTED_TARGET_ENTITIES = [
    {"id": "CDK2", "expected_len": 298, "category": "short_kinase"},
    {"id": "SRC", "expected_len": 536, "category": "medium_kinase"},
    {"id": "MET(Y1235D)", "expected_len": 1390, "category": "long_mutant_kinase"},
    {"id": "INSR", "expected_len": 1382, "category": "long_kinase"},
    {"id": "EGFR(T790M)", "expected_len": 1210, "category": "long_mutant_kinase"},
    {"id": "MTOR", "expected_len": 2549, "category": "ultra_long_kinase"}
]

WORKER_CODE = """
import sys, json
from pathlib import Path
import numpy as np

ROOT = Path(r"{root}")
sys.path.insert(0, str(ROOT / "02_code"))

from extract_worldmodel_features import (
    extract_worldmodel_drug_features,
    extract_worldmodel_kinase_features
)

drugs_data = json.loads(Path(r"{drugs_file}").read_text(encoding="utf-8"))
targets_data = json.loads(Path(r"{targets_file}").read_text(encoding="utf-8"))

out = {{"drugs": {{}}, "targets": {{}}}}

for d_id, smiles in drugs_data.items():
    feat = extract_worldmodel_drug_features(smiles)
    if feat.shape != (2568,):
        raise ValueError(f"Drug {{d_id}} invalid shape {{feat.shape}}, expected (2568,)")
    if not np.all(np.isfinite(feat)):
        raise ValueError(f"Drug {{d_id}} contains non-finite values")
    out["drugs"][d_id] = feat.tolist()

for t_id, seq in targets_data.items():
    feat = extract_worldmodel_kinase_features(seq)
    if feat.shape != (420,):
        raise ValueError(f"Target {{t_id}} invalid shape {{feat.shape}}, expected (420,)")
    if not np.all(np.isfinite(feat)):
        raise ValueError(f"Target {{t_id}} contains non-finite values")
    out["targets"][t_id] = feat.tolist()

Path(r"{out_file}").write_text(json.dumps(out), encoding="utf-8")
"""


def main():
    print("=" * 65)
    print("RESTRICTED FEATURE CONSISTENCY & REPRODUCIBILITY CHECK (v5)")
    print("=" * 65)
    
    df_davis = pd.read_csv(ROOT / "03_experiments/audits/dti_davis_acquisition_20261006_v2/davis.csv")
    
    drug_map = {}
    for d_id in SELECTED_DRUG_IDS:
        rows = df_davis[df_davis["ID1"].astype(str) == str(d_id)]
        assert len(rows) > 0, f"Drug {d_id} not found"
        drug_map[str(d_id)] = rows.iloc[0]["X1"]
        
    target_map = {}
    for item in SELECTED_TARGET_ENTITIES:
        t_id = item["id"]
        rows = df_davis[df_davis["ID2"] == t_id]
        assert len(rows) > 0, f"Target {t_id} not found in davis.csv"
        seq = rows.iloc[0]["X2"]
        act_len = len(seq)
        assert act_len == item["expected_len"], (
            f"Target {t_id} length mismatch: got {act_len}, expected {item['expected_len']}"
        )
        target_map[t_id] = seq
        
    print(f"Pre-selected {len(drug_map)} drugs:")
    for k, v in drug_map.items():
        print(f"  Drug {k:10s}: len(SMILES)={len(v):3d}")
        
    print(f"\nPre-selected {len(target_map)} targets (exact matching):")
    for item in SELECTED_TARGET_ENTITIES:
        t_id = item["id"]
        v = target_map[t_id]
        print(f"  Target {t_id:14s}: len(Seq)={len(v):4d} aa [{item['category']}]")

    print("\n[NOTE on Sliding-Window Pooling Mechanism]:")
    print("  Sequences > 1022 aa are split using window=1022, step=512.")
    print("  Each window is pooled by mean token representation, then windows are averaged equally.")
    print("  Residues in overlap regions are counted multiple times, receiving higher effective weight.")
    print("  This represents heuristic multi-window pooling, not strict per-residue uniform pooling.")
    print("  Sampling does not contain tight boundary entities (1021/1023 aa), noted as coverage limitation.")

    drugs_tmp = WORK_DIR / "sample_drugs.json"
    targets_tmp = WORK_DIR / "sample_targets.json"
    drugs_tmp.write_text(json.dumps(drug_map), encoding="utf-8")
    targets_tmp.write_text(json.dumps(target_map), encoding="utf-8")
    
    p1_out = WORK_DIR / "proc1_features.json"
    p2_out = WORK_DIR / "proc2_features.json"
    
    # Run Process 1
    t0 = time.time()
    print("\nRunning Process 1 in independent subprocess...")
    code1 = WORKER_CODE.format(
        root=str(ROOT),
        drugs_file=str(drugs_tmp),
        targets_file=str(targets_tmp),
        out_file=str(p1_out)
    )
    env = os.environ.copy()
    env["TORCH_HOME"] = str(ROOT / ".torch_blocked")  # Prevent weight download
    res1 = subprocess.run([SYS_PY, "-c", code1], capture_output=True, text=True, cwd=str(ROOT), env=env)
    if res1.returncode != 0:
        print("Process 1 failed with stderr:\n", res1.stderr)
        sys.exit(1)
    p1_time = time.time() - t0
    print(f"Process 1 completed in {p1_time:.2f}s")
    
    # Run Process 2
    t1 = time.time()
    print("Running Process 2 in second independent subprocess...")
    code2 = WORKER_CODE.format(
        root=str(ROOT),
        drugs_file=str(drugs_tmp),
        targets_file=str(targets_tmp),
        out_file=str(p2_out)
    )
    res2 = subprocess.run([SYS_PY, "-c", code2], capture_output=True, text=True, cwd=str(ROOT), env=env)
    if res2.returncode != 0:
        print("Process 2 failed with stderr:\n", res2.stderr)
        sys.exit(1)
    p2_time = time.time() - t1
    print(f"Process 2 completed in {p2_time:.2f}s")
    
    # Load outputs
    p1_data = json.loads(p1_out.read_text(encoding="utf-8"))
    p2_data = json.loads(p2_out.read_text(encoding="utf-8"))
    
    # Check Cross-Process Concordance
    print("\nEvaluating Cross-Process Feature Concordance (Process 1 vs Process 2):")
    cross_proc_deltas = {}
    
    for d_id in drug_map:
        arr1 = np.array(p1_data["drugs"][d_id], dtype=np.float32)
        arr2 = np.array(p2_data["drugs"][d_id], dtype=np.float32)
        assert arr1.shape == (2568,), f"Drug {d_id} arr1 invalid shape {arr1.shape}"
        assert arr2.shape == (2568,), f"Drug {d_id} arr2 invalid shape {arr2.shape}"
        assert np.all(np.isfinite(arr1)), f"Drug {d_id} contains non-finite values in arr1"
        assert np.all(np.isfinite(arr2)), f"Drug {d_id} contains non-finite values in arr2"
        delta = float(np.max(np.abs(arr1 - arr2)))
        cross_proc_deltas[f"drug_{d_id}"] = delta
        print(f"  Drug {d_id:10s} (2568D, finite=True): max_abs_delta = {delta:.2e}")
        
    for t_id in target_map:
        arr1 = np.array(p1_data["targets"][t_id], dtype=np.float32)
        arr2 = np.array(p2_data["targets"][t_id], dtype=np.float32)
        assert arr1.shape == (420,), f"Target {t_id} arr1 invalid shape {arr1.shape}"
        assert arr2.shape == (420,), f"Target {t_id} arr2 invalid shape {arr2.shape}"
        assert np.all(np.isfinite(arr1)), f"Target {t_id} contains non-finite values in arr1"
        assert np.all(np.isfinite(arr2)), f"Target {t_id} contains non-finite values in arr2"
        delta = float(np.max(np.abs(arr1 - arr2)))
        cross_proc_deltas[f"target_{t_id}"] = delta
        print(f"  Target {t_id:14s} (420D, finite=True): max_abs_delta = {delta:.2e}")
        
    # Check Offline Saved Tensor Concordance
    print("\nEvaluating Online vs Offline Saved Tensors (20261009 clean features):")
    clean_drug_feats = np.load(CLEAN_DIR / "drug_features.npy")
    clean_drug_ids = json.loads((CLEAN_DIR / "drug_ids.json").read_text(encoding="utf-8"))
    clean_drug_idx = {str(k): i for i, k in enumerate(clean_drug_ids)}
    
    clean_target_feats = np.load(CLEAN_DIR / "target_features.npy")
    clean_target_ids = json.loads((CLEAN_DIR / "target_ids.json").read_text(encoding="utf-8"))
    clean_target_idx = {str(k): i for i, k in enumerate(clean_target_ids)}
    
    offline_deltas = {}
    for d_id in drug_map:
        idx = clean_drug_idx[str(d_id)]
        arr_off = clean_drug_feats[idx]
        arr_on = np.array(p1_data["drugs"][d_id], dtype=np.float32)
        assert arr_off.shape == (2568,), f"Offline drug shape mismatch {arr_off.shape}"
        delta = float(np.max(np.abs(arr_off - arr_on)))
        offline_deltas[f"drug_{d_id}"] = delta
        print(f"  Drug {d_id:10s} vs offline: max_abs_delta = {delta:.2e}")
        
    for t_id in target_map:
        idx = clean_target_idx[str(t_id)]
        arr_off = clean_target_feats[idx]
        arr_on = np.array(p1_data["targets"][t_id], dtype=np.float32)
        assert arr_off.shape == (420,), f"Offline target shape mismatch {arr_off.shape}"
        delta = float(np.max(np.abs(arr_off - arr_on)))
        offline_deltas[f"target_{t_id}"] = delta
        print(f"  Target {t_id:14s} vs offline: max_abs_delta = {delta:.2e}")

    max_cross_proc = max(cross_proc_deltas.values())
    max_offline = max(offline_deltas.values())
    
    passed = (max_cross_proc < 1e-5) and (max_offline < 1e-4)
    
    result = {
        "status": "PASS" if passed else "FAIL",
        "exit_code": 0 if passed else 1,
        "sample_counts": {
            "drugs": len(drug_map),
            "targets": len(target_map)
        },
        "target_entities_metadata": SELECTED_TARGET_ENTITIES,
        "shape_checks": {
            "drug_shape": [2568],
            "target_shape": [420],
            "finite_values_all": True
        },
        "pooling_mechanism_note": (
            "Sliding window (window=1022, step=512) equal-weighted window mean pooling. "
            "Overlapping residues have higher effective weight. "
            "Does not prove 3D catalytic site conformation restoration."
        ),
        "sampling_limitation": "No tight boundary entities (1021/1023 aa) included in sample.",
        "p1_runtime_sec": round(p1_time, 2),
        "p2_runtime_sec": round(p2_time, 2),
        "max_cross_proc_delta": max_cross_proc,
        "max_offline_delta": max_offline,
        "cross_proc_deltas": cross_proc_deltas,
        "offline_deltas": offline_deltas
    }
    
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nAudit Summary:")
    print(f"  Status: {result['status']} (Exit Code {result['exit_code']})")
    print(f"  Max Cross-Process Delta: {max_cross_proc:.2e}")
    print(f"  Max Offline Delta: {max_offline:.2e}")
    print(f"  Saved to: {OUT_JSON}")
    
    for f in [drugs_tmp, targets_tmp, p1_out, p2_out]:
        if f.exists():
            f.unlink()

    if not passed:
        print("Feature consistency check FAILED.")
        sys.exit(1)
    else:
        print("Feature consistency check PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
