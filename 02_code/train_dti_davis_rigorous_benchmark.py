"""Rigorous DTA Benchmark Training on Clean Deterministic DAVIS Features.

Key Innovations:
1. P0-1/P0-2/P1-2: Trained on 100% deterministic features without hash collision / length truncation.
2. P0-3: Eliminates pair-level CV leakage. Replaces KFold with GroupKFold(drug_id) in inner loop.
3. P1-1: Fully serializes predictions.csv for all domains and models with pair identifiers.
4. Comprehensive metrics: Concordance Index (Harrell's CI), RMSE, MAE, Pearson r, Spearman rho.
"""
from __future__ import annotations

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple

import hashlib
import joblib
import numpy as np
import pandas as pd
import scipy.stats
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import GroupKFold
from scipy.optimize import nnls

ROOT = Path(r"D:\桌面文件\sci")
sys.path.insert(0, str(ROOT / "02_code"))

# Import accelerated exact Concordance Index
try:
    import numba
    @numba.njit(fastmath=False)
    def _fast_ci_core(y_true, y_pred):
        n = len(y_true)
        num = 0.0
        denom = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if y_true[i] > y_true[j]:
                    denom += 1.0
                    if y_pred[i] > y_pred[j]:
                        num += 1.0
                    elif y_pred[i] == y_pred[j]:
                        num += 0.5
                elif y_true[j] > y_true[i]:
                    denom += 1.0
                    if y_pred[j] > y_pred[i]:
                        num += 1.0
                    elif y_pred[j] == y_pred[i]:
                        num += 0.5
        if denom == 0.0:
            return 0.5
        return num / denom
except ImportError:
    _fast_ci_core = None

def compute_ci(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    if _fast_ci_core is not None:
        return float(_fast_ci_core(y_true, y_pred))
    n = len(y_true)
    num = 0.0
    denom = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            if y_true[i] > y_true[j]:
                denom += 1.0
                if y_pred[i] > y_pred[j]:
                    num += 1.0
                elif y_pred[i] == y_pred[j]:
                    num += 0.5
            elif y_true[j] > y_true[i]:
                denom += 1.0
                if y_pred[j] > y_pred[i]:
                    num += 1.0
                elif y_pred[j] == y_pred[i]:
                    num += 0.5
    if denom == 0.0:
        return 0.5
    return float(num / denom)

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    mse = float(np.mean((y_true - y_pred) ** 2))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    if np.all(y_pred == y_pred[0]):
        pr, pp, sr, sp = 0.0, 1.0, 0.0, 1.0
    else:
        pr, pp = scipy.stats.pearsonr(y_true, y_pred)
        sr, sp = scipy.stats.spearmanr(y_true, y_pred)
    ci = compute_ci(y_true, y_pred)
    return {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "pearson_r": round(float(pr), 4),
        "spearman_rho": round(float(sr), 4),
        "concordance_index": round(ci, 4)
    }

def main():
    print("======================================================================")
    print("STARTING RIGOROUS DTI DAVIS BENCHMARK TRAINING (v1-20261009)")
    print("======================================================================")
    t0 = time.time()

    prepared_dir = ROOT / "03_experiments/prepared/dti_davis_clean_features_20261009_v1"
    run_dir = ROOT / "03_experiments/runs/dti_davis_rigorous_20261009_v1"
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Clean Deterministic Features
    print("Loading clean feature arrays and pair metadata...")
    drug_feats = np.load(prepared_dir / "drug_features.npy")     # (68, 2568)
    target_feats = np.load(prepared_dir / "target_features.npy") # (379, 420)
    with open(prepared_dir / "drug_ids.json", "r", encoding="utf-8") as f:
        drug_ids = json.load(f)
    with open(prepared_dir / "target_ids.json", "r", encoding="utf-8") as f:
        target_ids = json.load(f)
    df_pairs = pd.read_csv(prepared_dir / "pairs_metadata.csv")

    drug_idx_map = {str(d_id): i for i, d_id in enumerate(drug_ids)}
    target_idx_map = {str(t_id): i for i, t_id in enumerate(target_ids)}

    print(f"Loaded {len(drug_ids)} drugs, {len(target_ids)} targets, {len(df_pairs)} pairs.")

    # 2. Construct Combined Interaction Matrix
    print("Constructing 2988-dim combined interaction vectors...")
    d_indices = [drug_idx_map[str(d)] for d in df_pairs["drug_id"]]
    t_indices = [target_idx_map[str(t)] for t in df_pairs["target_id"]]
    X_all = np.hstack([drug_feats[d_indices], target_feats[t_indices]]).astype(np.float32)
    y_all = df_pairs["pkd"].values.astype(np.float32)
    print(f"Full interaction dataset shape: X={X_all.shape}, y={y_all.shape}")

    # Domain masks
    domain_masks = {
        "train_block": (df_pairs["domain"] == "train_block").values,
        "strict_dual_cold_test": (df_pairs["domain"] == "strict_dual_cold_test").values,
        "cold_target_test": (df_pairs["domain"] == "cold_target_test").values,
        "cold_drug_test": (df_pairs["domain"] == "cold_drug_test").values
    }

    train_mask = domain_masks["train_block"]
    X_train = X_all[train_mask]
    y_train = y_all[train_mask]
    train_drug_groups = df_pairs.loc[train_mask, "drug_id"].values

    print(f"Train block: {X_train.shape[0]} pairs, across {len(np.unique(train_drug_groups))} unique drugs.")

    # 3. Define Base Models
    base_models = {
        "ridge_alpha10": Ridge(alpha=10.0, random_state=42),
        "ridge_alpha50": Ridge(alpha=50.0, random_state=42),
        "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=100, min_samples_leaf=20, random_state=42),
        "random_forest": RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    }

    # 4. Rigorous Inner Cross-Validation with GroupKFold
    print("\n----------------------------------------------------------------------")
    print("GATE 4 & INNER OOF: Running 5-fold GroupKFold by drug entity (zero leakage)...")
    print("----------------------------------------------------------------------")
    gkf = GroupKFold(n_splits=5)
    oof_preds = {name: np.zeros(len(X_train), dtype=np.float32) for name in base_models}
    oof_fold_id = np.zeros(len(X_train), dtype=np.int32)
    cv_splits = []

    for fold, (f_tr_idx, f_val_idx) in enumerate(gkf.split(X_train, y_train, groups=train_drug_groups)):
        # Verify strict isolation
        tr_drugs = sorted(list(set(train_drug_groups[f_tr_idx])))
        val_drugs = sorted(list(set(train_drug_groups[f_val_idx])))
        overlap = set(tr_drugs).intersection(set(val_drugs))
        assert len(overlap) == 0, f"Fold {fold} has drug leakage: {overlap}"
        oof_fold_id[f_val_idx] = fold + 1
        cv_splits.append({
            "fold": fold + 1,
            "train_pairs": len(f_tr_idx),
            "val_pairs": len(f_val_idx),
            "train_drugs": [str(x) for x in tr_drugs],
            "val_drugs": [str(x) for x in val_drugs]
        })
        print(f"  Fold {fold+1}/5: Train pairs={len(f_tr_idx)} ({len(tr_drugs)} drugs), Val pairs={len(f_val_idx)} ({len(val_drugs)} drugs). Overlap: 0 (PASS)")

        for name, model_cls in base_models.items():
            model = type(model_cls)(**model_cls.get_params())
            model.fit(X_train[f_tr_idx], y_train[f_tr_idx])
            oof_preds[name][f_val_idx] = model.predict(X_train[f_val_idx])

    # Save OOF Predictions and CV splits
    df_oof = pd.DataFrame({
        "drug_id": train_drug_groups,
        "fold": oof_fold_id,
        "true_pkd": y_train
    })
    for name in base_models:
        df_oof[f"oof_pred_{name}"] = np.round(oof_preds[name], 4)
    oof_csv_path = run_dir / "oof_predictions.csv"
    df_oof.to_csv(oof_csv_path, index=False)
    print(f"OOF predictions saved to: {oof_csv_path} ({len(df_oof)} rows)")

    cv_splits_path = run_dir / "cv_splits.json"
    with open(cv_splits_path, "w", encoding="utf-8") as f:
        json.dump(cv_splits, f, indent=2, ensure_ascii=False)
    print(f"CV split definitions saved to: {cv_splits_path}")

    # Print OOF metrics
    print("\n=== Inner GroupKFold (Cold-Drug OOF) Baseline Metrics ===")
    model_names = list(base_models.keys())
    for name in model_names:
        oof_m = compute_metrics(y_train, oof_preds[name])
        print(f"  {name:25s}: CI={oof_m['concordance_index']:.4f}, RMSE={oof_m['rmse']:.4f}, r={oof_m['pearson_r']:.4f}")

    # 5. Fit Meta-Learner (Non-Negative Least Squares on OOF)
    print("\nFitting Stacking Meta-Learner via NNLS on leak-free OOF predictions...")
    OOF_mat = np.column_stack([oof_preds[name] for name in model_names])
    OOF_with_intercept = np.column_stack([OOF_mat, np.ones(len(OOF_mat))])
    weights, norm_res = nnls(OOF_with_intercept, y_train)

    meta_weights = {name: float(round(weights[i], 4)) for i, name in enumerate(model_names)}
    meta_intercept = float(round(weights[-1], 4))

    print(f"Meta-Learner Weights: {meta_weights}")
    print(f"Meta-Learner Intercept: {meta_intercept}")

    # 6. Fit and Serialize Final Base Models on Full Train Block
    print("\nFitting and serializing final base models on full train block (16,720 pairs)...")
    models_dir = run_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    fitted_base_models = {}
    saved_model_hashes = {}

    for name, model in base_models.items():
        print(f"  Fitting {name}...")
        model.fit(X_train, y_train)
        fitted_base_models[name] = model
        model_file = models_dir / f"{name}.joblib"
        joblib.dump(model, model_file)
        
        # Compute SHA256 of saved model
        h_m = hashlib.sha256()
        with open(model_file, "rb") as mf:
            while chunk := mf.read(65536):
                h_m.update(chunk)
        saved_model_hashes[f"{name}.joblib"] = h_m.hexdigest()
        print(f"    Saved: {model_file.name} (SHA256: {saved_model_hashes[f'{name}.joblib'][:16]}...)")

    # Serialize Stacking Meta-Learner
    meta_model_data = {
        "model_type": "nnls_stacking_meta_learner",
        "base_model_names": model_names,
        "weights": weights.tolist(),
        "meta_weights_dict": meta_weights,
        "meta_intercept": meta_intercept,
        "features_dim": X_all.shape[1],
        "trained_at": "2026-10-09"
    }
    meta_file = models_dir / "stacked_ensemble_meta.joblib"
    joblib.dump(meta_model_data, meta_file)
    h_meta = hashlib.sha256()
    with open(meta_file, "rb") as mf:
        while chunk := mf.read(65536):
            h_meta.update(chunk)
    saved_model_hashes["stacked_ensemble_meta.joblib"] = h_meta.hexdigest()
    print(f"    Saved: {meta_file.name} (SHA256: {h_meta.hexdigest()[:16]}...)")

    # 7. Generate Full Predictions across All 4 Domains
    print("\nGenerating predictions across all 4 evaluation domains...")
    all_preds = {}
    for name, model in fitted_base_models.items():
        all_preds[name] = model.predict(X_all).astype(np.float32)

    # Compute stacked prediction
    stacked_pred = np.zeros(len(X_all), dtype=np.float32)
    for i, name in enumerate(model_names):
        stacked_pred += weights[i] * all_preds[name]
    stacked_pred += meta_intercept
    all_preds["stacked_ensemble"] = stacked_pred.astype(np.float32)

    # 8. Compute and Report Metrics for All Models and Domains
    results_summary = {
        "version": "dti_davis_rigorous_20261009_v1",
        "timestamp": "2026-10-09",
        "inner_cv_protocol": "5-Fold GroupKFold by drug entity (zero inner pair leakage)",
        "meta_weights": meta_weights,
        "meta_intercept": meta_intercept,
        "models": {}
    }

    all_eval_models = list(fitted_base_models.keys()) + ["stacked_ensemble"]
    print("\n======================================================================")
    print("FINAL EVALUATION ACROSS ALL DOMAINS")
    print("======================================================================")

    for m_name in all_eval_models:
        results_summary["models"][m_name] = {"domains": {}}
        print(f"\n--- Model: {m_name} ---")
        for dom_name, mask in domain_masks.items():
            y_t = y_all[mask]
            y_p = all_preds[m_name][mask]
            m = compute_metrics(y_t, y_p)
            results_summary["models"][m_name]["domains"][dom_name] = m
            print(f"  {dom_name:25s}: CI={m['concordance_index']:.4f}, RMSE={m['rmse']:.4f}, Pearson r={m['pearson_r']:.4f}")

    # Save metrics summary
    metrics_json_path = run_dir / "metrics_summary.json"
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2, ensure_ascii=False)
    print(f"\nMetrics summary saved to: {metrics_json_path}")

    # 9. Save Serialized predictions.csv (P1-1 resolution)
    print("\nSaving complete predictions.csv with pair identifiers...")
    df_output = df_pairs[["drug_id", "target_id", "domain", "pkd"]].copy()
    df_output.rename(columns={"pkd": "true_pkd"}, inplace=True)
    for m_name in all_eval_models:
        df_output[f"pred_{m_name}"] = np.round(all_preds[m_name], 4)

    preds_csv_path = run_dir / "predictions.csv"
    df_output.to_csv(preds_csv_path, index=False)
    print(f"Serialized predictions.csv saved to: {preds_csv_path} ({len(df_output)} rows)")

    # 10. Save Complete Training Manifest
    training_manifest = {
        "version": "dti_davis_rigorous_20261009_v1",
        "created_at": "2026-10-09",
        "input_features": {
            "source_dir": str(prepared_dir),
            "features_dim": X_all.shape[1],
            "drug_features_dim": drug_feats.shape[1],
            "target_features_dim": target_feats.shape[1]
        },
        "serialized_models": saved_model_hashes,
        "files": {
            "predictions.csv": {
                "rows": len(df_output),
                "path": str(preds_csv_path)
            },
            "oof_predictions.csv": {
                "rows": len(df_oof),
                "path": str(oof_csv_path)
            },
            "metrics_summary.json": {
                "path": str(metrics_json_path)
            },
            "cv_splits.json": {
                "folds": len(cv_splits),
                "path": str(cv_splits_path)
            }
        }
    }
    manifest_path = run_dir / "training_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(training_manifest, f, indent=2, ensure_ascii=False)
    print(f"Training manifest saved to: {manifest_path}")

    total_time = round(time.time() - t0, 1)
    print(f"\nTraining and benchmark evaluation completed successfully in {total_time}s!")
    print("======================================================================")

if __name__ == "__main__":
    main()
