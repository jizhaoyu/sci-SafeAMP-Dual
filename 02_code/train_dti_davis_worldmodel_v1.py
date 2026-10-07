"""Train biological world model (Uni-Mol + ESM-2) enhanced DTI ensemble on DAVIS benchmark."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import time
import joblib
import numba
import numpy as np
import scipy.stats
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

from dti_source_preflight import PROTECTED, save
from dti_stacked_model import StackedDTIPredictor
from research_utils import ROOT, sha256, utc_now


@numba.njit
def compute_concordance_index(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute pairwise Concordance Index (CI) for affinity prediction."""
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


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute RMSE, MAE, Pearson r, Spearman rho, and CI."""
    diff = y_pred - y_true
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    mae = float(np.mean(np.abs(diff)))

    # Correlation
    r_val, p_val = scipy.stats.pearsonr(y_true, y_pred)
    rho_val, rho_p = scipy.stats.spearmanr(y_true, y_pred)
    ci = compute_concordance_index(y_true, y_pred)

    return {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "pearson_r": round(float(r_val), 4),
        "pearson_p_value": float(p_val),
        "spearman_rho": round(float(rho_val), 4),
        "spearman_p_value": float(rho_p),
        "concordance_index": round(float(ci), 4)
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=ROOT / "03_experiments/protocols/protocol-dti-01.json")
    parser.add_argument("--features-dir", type=Path, default=ROOT / "03_experiments/prepared/dti_davis_worldmodel_features_20261008_v1")
    parser.add_argument("--output", type=Path, default=ROOT / "03_experiments/runs/dti_davis_worldmodel_20261008_v1")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    models_dir = args.output / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    with args.protocol.open("r", encoding="utf-8") as f:
        proto = json.load(f)

    features_dir = args.features_dir.resolve()
    print("Loading world-model enhanced features (Uni-Mol + ESM-2)...")
    drug_features = np.load(features_dir / "drug_features.npy")
    target_features = np.load(features_dir / "target_features.npy")

    with (features_dir / "drug_ids.json").open("r", encoding="utf-8") as f:
        drug_ids = json.load(f)
    with (features_dir / "target_ids.json").open("r", encoding="utf-8") as f:
        target_ids = json.load(f)

    drug_to_idx = {d_id: i for i, d_id in enumerate(drug_ids)}
    target_to_idx = {t_id: i for i, t_id in enumerate(target_ids)}

    pairs = []
    with (features_dir / "pairs_metadata.csv").open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pairs.append(row)

    domain_indices = {
        "train_block": [],
        "strict_dual_cold_test": [],
        "cold_target_test": [],
        "cold_drug_test": []
    }
    for idx, row in enumerate(pairs):
        domain_indices[row["domain"]].append(idx)

    total_dim = drug_features.shape[1] + target_features.shape[1]
    print(f"Total concatenated world model feature dimension: {total_dim}")

    def build_domain_data(indices: list[int]):
        n = len(indices)
        X = np.zeros((n, total_dim), dtype=np.float32)
        y = np.zeros(n, dtype=np.float32)
        drug_dim = drug_features.shape[1]
        for i, idx in enumerate(indices):
            row = pairs[idx]
            d_idx = drug_to_idx[row["drug_id"]]
            t_idx = target_to_idx[row["target_id"]]
            X[i, :drug_dim] = drug_features[d_idx]
            X[i, drug_dim:] = target_features[t_idx]
            y[i] = float(row["pkd"])
        return X, y

    print("Building domain feature matrices...")
    X_train, y_train = build_domain_data(domain_indices["train_block"])
    X_dual_cold, y_dual_cold = build_domain_data(domain_indices["strict_dual_cold_test"])
    X_cold_target, y_cold_target = build_domain_data(domain_indices["cold_target_test"])
    X_cold_drug, y_cold_drug = build_domain_data(domain_indices["cold_drug_test"])

    domains_eval = {
        "train_block": (X_train, y_train),
        "strict_dual_cold_test": (X_dual_cold, y_dual_cold),
        "cold_target_test": (X_cold_target, y_cold_target),
        "cold_drug_test": (X_cold_drug, y_cold_drug)
    }

    base_models_config = {
        "ridge_alpha10": Ridge(alpha=10.0, random_state=42),
        "ridge_alpha50": Ridge(alpha=50.0, random_state=42),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            max_iter=60, max_depth=6, learning_rate=0.08, random_state=42
        )
    }
    model_names = list(base_models_config.keys())
    k_models = len(model_names)

    # 1. 5-Fold OOF Predictions
    print("\n--- Phase 1: Generating OOF Predictions via 5-Fold CV ---")
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    oof_predictions = np.zeros((len(y_train), k_models), dtype=np.float32)

    for fold_i, (train_idx, val_idx) in enumerate(kf.split(X_train)):
        print(f"Processing Fold {fold_i + 1}/5...")
        X_f_tr, y_f_tr = X_train[train_idx], y_train[train_idx]
        X_f_val = X_train[val_idx]

        for m_i, m_name in enumerate(model_names):
            if "ridge" in m_name:
                alpha_val = 50.0 if "50" in m_name else 10.0
                fold_model = Ridge(alpha=alpha_val, random_state=42)
            else:
                fold_model = HistGradientBoostingRegressor(
                    max_iter=60, max_depth=6, learning_rate=0.08, random_state=42
                )
            fold_model.fit(X_f_tr, y_f_tr)
            oof_predictions[val_idx, m_i] = fold_model.predict(X_f_val)

    # 2. Fit Stacking Meta-Learner
    print("\n--- Phase 2: Training Stacking Meta-Learner ---")
    meta_model = Ridge(alpha=1.0, positive=True, random_state=42)
    meta_model.fit(oof_predictions, y_train)

    meta_weights = {
        name: round(float(coef), 4) for name, coef in zip(model_names, meta_model.coef_)
    }
    print(f"Meta-learner Intercept: {meta_model.intercept_:.4f}")
    print(f"Meta-learner Weights: {meta_weights}")

    # 3. Fit base models on full training set
    print("\n--- Phase 3: Fitting models on full train block & evaluating domains ---")
    fitted_base_models = {}
    for m_name, model in base_models_config.items():
        t0 = time.time()
        model.fit(X_train, y_train)
        print(f"Fitted {m_name} in {time.time() - t0:.2f}s")
        fitted_base_models[m_name] = model

    stacked_predictor = StackedDTIPredictor(
        base_models=fitted_base_models,
        meta_model=meta_model,
        model_names=model_names
    )

    # Evaluation
    metrics_summary = {
        "generated_at": utc_now(),
        "protocol_id": proto["protocol_id"],
        "meta_weights": meta_weights,
        "meta_intercept": round(float(meta_model.intercept_), 4),
        "models": {}
    }

    all_models_to_eval = dict(fitted_base_models)
    all_models_to_eval["worldmodel_stacked_ensemble"] = stacked_predictor

    for m_name, model in all_models_to_eval.items():
        metrics_summary["models"][m_name] = {"domains": {}}
        for d_name, (X_d, y_d) in domains_eval.items():
            preds = model.predict(X_d)
            metrics = evaluate_predictions(y_d, preds)
            metrics_summary["models"][m_name]["domains"][d_name] = metrics
            print(f"[{m_name}] {d_name} -> CI: {metrics['concordance_index']:.4f}, RMSE: {metrics['rmse']:.4f}, MAE: {metrics['mae']:.4f}")

    # Save models
    for m_name, model in fitted_base_models.items():
        joblib.dump(model, models_dir / f"{m_name}.joblib")
    joblib.dump(stacked_predictor, models_dir / "worldmodel_stacked_ensemble.joblib")

    with (args.output / "metrics_summary.json").open("w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)

    # Save manifest
    manifest = {
        "status": "completed",
        "protocol_id": proto["protocol_id"],
        "generated_at": utc_now(),
        "models": list(all_models_to_eval.keys()),
        "outputs": {
            "metrics_summary.json": sha256(args.output / "metrics_summary.json"),
            "models/worldmodel_stacked_ensemble.joblib": sha256(models_dir / "worldmodel_stacked_ensemble.joblib")
        }
    }
    with (args.output / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nTraining and evaluation finished! Artifacts saved in {args.output}")


if __name__ == "__main__":
    main()
