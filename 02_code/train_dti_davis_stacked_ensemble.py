"""Train enhanced base learners and a non-negative stacking meta-regressor on DAVIS benchmark under frozen protocol."""
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
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.neural_network import MLPRegressor

from dti_source_preflight import PROTECTED, save
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
    mse = float(np.mean((y_true - y_pred) ** 2))
    rmse = float(math.sqrt(mse))
    mae = float(np.mean(np.abs(y_true - y_pred)))

    if np.all(y_pred == y_pred[0]):
        pearson_r = 0.0
        pearson_p = 1.0
        spearman_rho = 0.0
        spearman_p = 1.0
    else:
        pr, pp = scipy.stats.pearsonr(y_true, y_pred)
        sr, sp = scipy.stats.spearmanr(y_true, y_pred)
        pearson_r = float(pr) if not math.isnan(pr) else 0.0
        pearson_p = float(pp) if not math.isnan(pp) else 1.0
        spearman_rho = float(sr) if not math.isnan(sr) else 0.0
        spearman_p = float(sp) if not math.isnan(sp) else 1.0

    ci = compute_concordance_index(y_true, y_pred)

    return {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "pearson_r": round(pearson_r, 4),
        "pearson_p_value": float(pearson_p),
        "spearman_rho": round(spearman_rho, 4),
        "spearman_p_value": float(spearman_p),
        "concordance_index": round(ci, 4)
    }


from dti_stacked_model import StackedDTIPredictor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--features-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError(f"Output directory already exists: {args.output}")

    # Protected file check
    before = {p: sha256(ROOT / p) for p in PROTECTED}

    protocol_path = args.protocol.resolve()
    with protocol_path.open("r", encoding="utf-8") as f:
        proto = json.load(f)

    assert proto["protocol_id"] == "protocol-dti-01", "Protocol ID mismatch"

    features_dir = args.features_dir.resolve()
    with (features_dir / "manifest.json").open("r", encoding="utf-8") as f:
        feat_manifest = json.load(f)

    for fname, expected_h in feat_manifest["outputs"].items():
        assert sha256(features_dir / fname) == expected_h, f"Corrupted file: {fname}"

    # Load drug & target feature arrays
    print("Loading precomputed enhanced features...")
    drug_features = np.load(features_dir / "drug_features.npy")
    target_features = np.load(features_dir / "target_features.npy")

    with (features_dir / "drug_ids.json").open("r", encoding="utf-8") as f:
        drug_ids = json.load(f)
    with (features_dir / "target_ids.json").open("r", encoding="utf-8") as f:
        target_ids = json.load(f)

    drug_to_idx = {d_id: i for i, d_id in enumerate(drug_ids)}
    target_to_idx = {t_id: i for i, t_id in enumerate(target_ids)}

    # Read pairs metadata
    pairs = []
    with (features_dir / "pairs_metadata.csv").open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pairs.append(row)

    total_pairs = len(pairs)
    assert total_pairs == 25772, f"Expected 25772, got {total_pairs}"

    domain_indices = {
        "train_block": [],
        "strict_dual_cold_test": [],
        "cold_target_test": [],
        "cold_drug_test": []
    }
    for idx, row in enumerate(pairs):
        domain_indices[row["domain"]].append(idx)

    total_dim = drug_features.shape[1] + target_features.shape[1]
    print(f"Total concatenated feature dimension: {total_dim}")

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

    print(f"Train samples: {len(y_train)}, Strict Dual-Cold: {len(y_dual_cold)}")

    # Base models configuration
    base_models_config = {
        "ridge_alpha1": Ridge(alpha=1.0, random_state=42),
        "ridge_alpha10": Ridge(alpha=10.0, random_state=42),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            max_iter=60, max_depth=6, learning_rate=0.08, random_state=42
        ),
        "mlp": MLPRegressor(
            hidden_layer_sizes=(128, 64),
            activation="relu",
            max_iter=50,
            early_stopping=True,
            random_state=42
        )
    }
    model_names = list(base_models_config.keys())
    k_models = len(model_names)

    # 1. Generate Out-Of-Fold (OOF) predictions on Train Block for Meta-Learner
    print("\n--- Phase 1: Generating Out-Of-Fold (OOF) predictions via 5-Fold CV ---")
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    oof_predictions = np.zeros((len(y_train), k_models), dtype=np.float32)

    for fold_i, (train_idx, val_idx) in enumerate(kf.split(X_train)):
        print(f"Processing Fold {fold_i + 1}/5...")
        X_f_tr, y_f_tr = X_train[train_idx], y_train[train_idx]
        X_f_val = X_train[val_idx]

        for m_i, m_name in enumerate(model_names):
            fold_model = joblib.load(joblib.dump(base_models_config[m_name], None)[0]) if False else None
            # Recreate clone
            if "ridge" in m_name:
                alpha_val = 10.0 if "10" in m_name else 1.0
                fold_model = Ridge(alpha=alpha_val, random_state=42)
            elif "hist" in m_name:
                fold_model = HistGradientBoostingRegressor(
                    max_iter=60, max_depth=6, learning_rate=0.08, random_state=42
                )
            else:
                fold_model = MLPRegressor(
                    hidden_layer_sizes=(128, 64),
                    activation="relu",
                    max_iter=50,
                    early_stopping=True,
                    random_state=42
                )
            fold_model.fit(X_f_tr, y_f_tr)
            oof_predictions[val_idx, m_i] = fold_model.predict(X_f_val)

    # 2. Train Non-negative Ridge Meta-Learner
    print("\n--- Phase 2: Training Non-negative Stacking Meta-Learner ---")
    meta_model = Ridge(alpha=1.0, positive=True, random_state=42)
    meta_model.fit(oof_predictions, y_train)

    meta_weights = {
        name: round(float(coef), 4) for name, coef in zip(model_names, meta_model.coef_)
    }
    print(f"Meta-learner Intercept: {meta_model.intercept_:.4f}")
    print(f"Meta-learner Non-negative Weights: {meta_weights}")

    # 3. Fit base models on full training set
    print("\n--- Phase 3: Fitting base models on full train block & evaluating domains ---")
    fitted_base_models = {}
    for m_name, model in base_models_config.items():
        t0 = time.time()
        model.fit(X_train, y_train)
        print(f"Fitted {m_name} in {time.time() - t0:.2f}s")
        fitted_base_models[m_name] = model

    # Create bundled stacked predictor
    stacked_predictor = StackedDTIPredictor(
        base_models=fitted_base_models,
        meta_model=meta_model,
        model_names=model_names
    )

    args.output.mkdir(parents=True, exist_ok=True)
    models_dir = args.output / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Save models
    for m_name, model in fitted_base_models.items():
        joblib.dump(model, models_dir / f"{m_name}.joblib")
    joblib.dump(meta_model, models_dir / "meta_model.joblib")
    joblib.dump(stacked_predictor, models_dir / "stacked_ensemble.joblib")

    # Also save a standard Ridge as ridge.joblib for drop-in runtime compatibility
    joblib.dump(fitted_base_models["ridge_alpha1"], models_dir / "ridge.joblib")

    # Evaluate all models across domains
    all_eval_models = {
        **fitted_base_models,
        "stacked_ensemble": stacked_predictor
    }

    metrics_results = {}
    predictions_table = {}

    for m_name, model in all_eval_models.items():
        print(f"\nEvaluating performance: {m_name}...")
        metrics_results[m_name] = {"domains": {}}
        all_preds = np.zeros(total_pairs, dtype=np.float32)

        for dom_name, (X_dom, y_dom) in domains_eval.items():
            dom_preds = model.predict(X_dom)
            dom_metrics = evaluate_predictions(y_dom, dom_preds)
            metrics_results[m_name]["domains"][dom_name] = dom_metrics

            # Place into full pair array
            for i, p_idx in enumerate(domain_indices[dom_name]):
                all_preds[p_idx] = float(dom_preds[i])

            if dom_name == "strict_dual_cold_test":
                print(f"  [Strict Dual-Cold Test] CI={dom_metrics['concordance_index']:.4f}, RMSE={dom_metrics['rmse']:.4f}, Pearson r={dom_metrics['pearson_r']:.4f}")

        predictions_table[m_name] = all_preds

    # Write predictions.csv
    print("\nWriting predictions.csv...")
    fieldnames = ["pair_index", "drug_id", "target_id", "domain", "y_true"] + list(all_eval_models.keys())
    with (args.output / "predictions.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for idx in range(total_pairs):
            row_dict = {
                "pair_index": idx,
                "drug_id": pairs[idx]["drug_id"],
                "target_id": pairs[idx]["target_id"],
                "domain": pairs[idx]["domain"],
                "y_true": pairs[idx]["pkd"]
            }
            for m_name in all_eval_models.keys():
                row_dict[m_name] = round(float(predictions_table[m_name][idx]), 4)
            writer.writerow(row_dict)

    # Compare with Baseline 20261006_v1
    baseline_summary_path = ROOT / "03_experiments/runs/dti_davis_baselines_20261006_v1/metrics_summary.json"
    comparison = {}
    if baseline_summary_path.exists():
        with baseline_summary_path.open("r", encoding="utf-8") as f:
            b_summary = json.load(f)
        b_ridge_dc = b_summary.get("ridge", {}).get("domains", {}).get("strict_dual_cold_test", {})
        new_stack_dc = metrics_results["stacked_ensemble"]["domains"]["strict_dual_cold_test"]
        comparison = {
            "metric": "strict_dual_cold_test",
            "baseline_ridge_ci": b_ridge_dc.get("concordance_index", 0.7262),
            "baseline_ridge_rmse": b_ridge_dc.get("rmse", 0.7958),
            "stacked_ensemble_ci": new_stack_dc["concordance_index"],
            "stacked_ensemble_rmse": new_stack_dc["rmse"],
            "ci_delta": round(new_stack_dc["concordance_index"] - b_ridge_dc.get("concordance_index", 0.7262), 4),
            "rmse_delta": round(new_stack_dc["rmse"] - b_ridge_dc.get("rmse", 0.7958), 4)
        }

    # Save metrics summary
    summary_data = {
        "generated_at": utc_now(),
        "protocol_id": proto["protocol_id"],
        "meta_weights": meta_weights,
        "meta_intercept": round(float(meta_model.intercept_), 4),
        "comparison_with_baseline": comparison,
        "models": metrics_results
    }
    with (args.output / "metrics_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # Manifest
    outputs = {
        "metrics_summary.json": sha256(args.output / "metrics_summary.json"),
        "predictions.csv": sha256(args.output / "predictions.csv")
    }
    for m_name in list(fitted_base_models.keys()) + ["meta_model", "stacked_ensemble", "ridge"]:
        outputs[f"models/{m_name}.joblib"] = sha256(models_dir / f"{m_name}.joblib")

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

    print(f"\nTraining and Stacking complete! Deliverables saved in: {args.output}")


if __name__ == "__main__":
    main()
