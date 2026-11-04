"""Train Tobit-Ranking DTI Model on DAVIS Benchmark under Frozen Protocol protocol-dti-01.

Conducts end-to-end training and stratified evaluation across 4 domains:
1. train_block
2. strict_dual_cold_test
3. cold_target_test
4. cold_drug_test

Audits the Negative Shrinkage Bias reduction in strong binders (pKd >= 7.0).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import time
from typing import Any, Dict

import numpy as np
import scipy.stats
from sklearn.linear_model import Ridge

from dti_source_preflight import PROTECTED
from dti_tobit_ranking_model import TobitRankingRegressor
from research_utils import ROOT, sha256, utc_now


def load_dataset(features_dir: Path):
    features_manifest_path = features_dir / "manifest.json"
    with features_manifest_path.open("r", encoding="utf-8") as f:
        feat_manifest = json.load(f)

    for fname, expected_hash in feat_manifest["outputs"].items():
        actual_hash = sha256(features_dir / fname)
        assert actual_hash == expected_hash, f"Features file corrupted: {fname}"

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

    assert len(pairs) == 25772, f"Expected 25772 pairs, got {len(pairs)}"

    domain_indices = {
        "train_block": [],
        "strict_dual_cold_test": [],
        "cold_target_test": [],
        "cold_drug_test": [],
    }
    for idx, row in enumerate(pairs):
        domain_indices[row["domain"]].append(idx)

    def _build_domain(indices: list[int]):
        n = len(indices)
        X = np.zeros((n, 2056 + 100), dtype=np.float32)
        y = np.zeros(n, dtype=np.float32)
        for i, idx in enumerate(indices):
            row = pairs[idx]
            d_idx = drug_to_idx[row["drug_id"]]
            t_idx = target_to_idx[row["target_id"]]
            X[i, :2056] = drug_features[d_idx]
            X[i, 2056:] = target_features[t_idx]
            y[i] = float(row["pkd"])
        return X, y

    domains = {dom: _build_domain(idxs) for dom, idxs in domain_indices.items()}
    return domains, pairs


def compute_stratified_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    def _calc(t: np.ndarray, p: np.ndarray) -> Dict[str, float]:
        if len(t) == 0:
            return {"count": 0, "rmse": 0.0, "mae": 0.0, "mean_bias": 0.0, "ci": 0.5, "spearman": 0.0}
        diff = p - t
        rmse = float(np.sqrt(np.mean(diff**2)))
        mae = float(np.mean(np.abs(diff)))
        mean_bias = float(np.mean(diff))

        # Concordance index
        ci = TobitRankingRegressor.compute_ci_fast(t, p)

        # Spearman
        if len(t) > 2 and np.std(p) > 1e-6 and np.std(t) > 1e-6:
            rho, _ = scipy.stats.spearmanr(t, p)
            spearman = float(rho) if not np.isnan(rho) else 0.0
        else:
            spearman = 0.0

        return {
            "count": int(len(t)),
            "rmse": rmse,
            "mae": mae,
            "mean_bias": mean_bias,
            "ci": ci,
            "spearman": spearman,
        }

    cens = y_true <= 5.0
    act = y_true > 5.0
    strong = y_true >= 7.0

    return {
        "overall": _calc(y_true, y_pred),
        "censored_pairs": _calc(y_true[cens], y_pred[cens]),
        "active_pairs": _calc(y_true[act], y_pred[act]),
        "strong_binders": _calc(y_true[strong], y_pred[strong]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--features-dir",
        type=Path,
        default=ROOT / "03_experiments/prepared/dti_davis_enhanced_features_20261007_v1",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output/dti-tobit-upgrade-20261011",
    )
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--ranking-weight", type=float, default=0.40)
    parser.add_argument("--active-weight", type=float, default=2.8)
    parser.add_argument("--strong-binder-boost", type=float, default=1.8)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{utc_now()}] Loading DAVIS enhanced features (2156D)...")
    domains, pairs = load_dataset(args.features_dir)
    X_train, y_train = domains["train_block"]

    print(f"Training Block: {X_train.shape[0]} pairs, 2156D features.")
    print(f"Strict Dual-Cold Test: {domains['strict_dual_cold_test'][0].shape[0]} pairs.")
    print(f"Cold Target Test: {domains['cold_target_test'][0].shape[0]} pairs.")
    print(f"Cold Drug Test: {domains['cold_drug_test'][0].shape[0]} pairs.")

    # Model A: Baseline Ridge Regressor (MSE loss)
    print("\n" + "=" * 70)
    print("Fitting Baseline Model: L2 Ridge Regressor (Standard MSE Loss)...")
    t0 = time.time()
    baseline_ridge = Ridge(alpha=50.0, random_state=42)
    baseline_ridge.fit(X_train, y_train)
    t_ridge = time.time() - t0
    print(f"Ridge fitted in {t_ridge:.2f}s.")

    # Model B: Tobit-Ranking Engine (Residual MLP backbone, Tobit NLL + Pairwise CI Loss)
    print("\n" + "=" * 70)
    print("Fitting Upgraded Model: Tobit-Ranking Engine (Residual MLP + Tobit NLL + Pairwise CI)...")
    t0 = time.time()
    # Create internal validation split from train_block for early stopping
    np.random.seed(42)
    val_idx = np.random.choice(len(y_train), size=int(0.15 * len(y_train)), replace=False)
    train_mask = np.ones(len(y_train), dtype=bool)
    train_mask[val_idx] = False

    tobit_model = TobitRankingRegressor(
        in_features=2156,
        architecture="residual_mlp",
        censoring_threshold=5.0,
        active_weight=args.active_weight,
        strong_binder_boost=args.strong_binder_boost,
        ranking_weight=args.ranking_weight,
        l2_reg=1e-4,
        lr=args.lr,
        batch_size=args.batch_size,
        max_epochs=args.epochs,
        early_stopping_patience=8,
        verbose=True,
    )
    tobit_model.fit(
        X_train[train_mask],
        y_train[train_mask],
        X_val=X_train[~train_mask],
        y_val=y_train[~train_mask],
    )
    t_tobit = time.time() - t0
    print(f"Tobit-Ranking model trained in {t_tobit:.2f}s.")

    # Evaluation comparison across all 4 domains
    comparison_results = {}
    csv_rows = []

    print("\n" + "=" * 70)
    print("STRATIFIED EVALUATION ACROSS BENCHMARK DOMAINS")
    print("=" * 70)

    for dom_name, (X_eval, y_eval) in domains.items():
        # Ridge predictions
        pred_ridge = baseline_ridge.predict(X_eval)
        eval_ridge = compute_stratified_metrics(y_eval, pred_ridge)

        # Tobit-Ranking predictions
        pred_tobit = tobit_model.predict(X_eval)
        eval_tobit = compute_stratified_metrics(y_eval, pred_tobit)

        comparison_results[dom_name] = {
            "baseline_ridge_mse": eval_ridge,
            "tobit_ranking_engine": eval_tobit,
        }

        # Print comparison table for this domain
        print(f"\n--- Domain: {dom_name.upper()} (N={len(y_eval)}) ---")
        print(f"{'Subset':<16} | {'Metric':<12} | {'Ridge (MSE)':<15} | {'Tobit-Ranking':<15} | {'Delta / Improvement'}")
        print("-" * 80)

        for subset in ["overall", "censored_pairs", "active_pairs", "strong_binders"]:
            r_sub = eval_ridge[subset]
            t_sub = eval_tobit[subset]
            for metric in ["rmse", "mae", "mean_bias", "ci", "spearman"]:
                r_val = r_sub[metric]
                t_val = t_sub[metric]
                delta = t_val - r_val
                # formatting
                sign = "+" if delta > 0 else ""
                print(
                    f"{subset:<16} | {metric:<12} | {r_val:<15.4f} | {t_val:<15.4f} | {sign}{delta:.4f}"
                )
                csv_rows.append(
                    {
                        "domain": dom_name,
                        "subset": subset,
                        "sample_count": r_sub["count"],
                        "metric": metric,
                        "baseline_ridge_val": round(r_val, 4),
                        "tobit_ranking_val": round(t_val, 4),
                        "delta": round(delta, 4),
                    }
                )

    # Save detailed JSON evaluation report
    eval_json_path = args.output_dir / "stratified_benchmark_comparison.json"
    with eval_json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": utc_now(),
                "benchmark": "DAVIS",
                "total_pairs": len(pairs),
                "evaluation": comparison_results,
                "model_parameters": {
                    "architecture": tobit_model.architecture,
                    "ranking_weight": tobit_model.ranking_weight,
                    "censoring_threshold": tobit_model.censoring_threshold,
                    "max_epochs": tobit_model.max_epochs,
                },
            },
            f,
            indent=2,
        )
    print(f"\n[Artifact Saved] JSON Comparison Report: {eval_json_path}")

    # Save CSV comparison report
    eval_csv_path = args.output_dir / "stratified_benchmark_comparison.csv"
    with eval_csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"[Artifact Saved] CSV Comparison Report: {eval_csv_path}")

    # Save trained Tobit-Ranking checkpoint for runtime integration
    ckpt_path = args.output_dir / "dti_tobit_ranking_model.pt"
    tobit_model.save_checkpoint(ckpt_path)
    print(f"[Artifact Saved] Model Checkpoint: {ckpt_path}")

    # Summary analysis of Strong Binders Mean Bias
    print("\n" + "=" * 70)
    print("KEY SCIENTIFIC AUDIT: STRONG BINDERS (pKd >= 7.0) NEGATIVE BIAS MITIGATION")
    print("=" * 70)
    for dom in ["strict_dual_cold_test", "cold_target_test"]:
        b_ridge = comparison_results[dom]["baseline_ridge_mse"]["strong_binders"]["mean_bias"]
        b_tobit = comparison_results[dom]["tobit_ranking_engine"]["strong_binders"]["mean_bias"]
        ci_ridge = comparison_results[dom]["baseline_ridge_mse"]["overall"]["ci"]
        ci_tobit = comparison_results[dom]["tobit_ranking_engine"]["overall"]["ci"]
        print(f"Domain [{dom}]:")
        print(f"  Ridge Strong Binder Mean Bias : {b_ridge:+.4f} pKd")
        print(f"  Tobit Strong Binder Mean Bias : {b_tobit:+.4f} pKd (Bias reduction: {abs(b_ridge) - abs(b_tobit):+.4f} pKd)")
        print(f"  Overall CI (Ranking Power)    : {ci_ridge:.4f} -> {ci_tobit:.4f} (Delta: {ci_tobit - ci_ridge:+.4f})")
    print("=" * 70)


if __name__ == "__main__":
    main()
