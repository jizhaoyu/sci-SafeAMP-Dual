"""Standalone script to recompute all metrics from predictions.csv and verify against metrics_summary.json.

Protocol v5 Specification:
- Strictly handles zero variance and degenerate cases (returns None/undefined instead of silent 0.0/0.5).
- Distinguishes undefined states: zero label variance, constant prediction collapse, empty inputs.
- Provides explicit sample counts, comparable pairs, and tied pairs.
- Includes automated self-test suite for edge-case verification.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import numpy as np
import pandas as pd
import scipy.stats

ROOT = Path(__file__).resolve().parents[3]
RUN_DIR = ROOT / "03_experiments/runs/dti_davis_rigorous_20261009_v1"
PRED_PATH = RUN_DIR / "predictions.csv"
METRICS_PATH = RUN_DIR / "metrics_summary.json"
OUT_PATH = Path(__file__).resolve().parent / "recomputed_metrics.json"

try:
    import numba
    @numba.njit(fastmath=False)
    def _fast_ci_core(y_true: np.ndarray, y_pred: np.ndarray) -> Tuple[float, float, float]:
        n = len(y_true)
        num = 0.0
        denom = 0.0
        ties = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if y_true[i] > y_true[j]:
                    denom += 1.0
                    if y_pred[i] > y_pred[j]:
                        num += 1.0
                    elif y_pred[i] == y_pred[j]:
                        num += 0.5
                        ties += 1.0
                elif y_true[j] > y_true[i]:
                    denom += 1.0
                    if y_pred[j] > y_pred[i]:
                        num += 1.0
                    elif y_pred[j] == y_pred[i]:
                        num += 0.5
                        ties += 1.0
        return num, denom, ties
except ImportError:
    _fast_ci_core = None


def compute_ci(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """Exact Harrell's Concordance Index with standard 0.5 tie-breaking."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    
    if len(y_true) != len(y_pred):
        raise ValueError(f"Length mismatch: {len(y_true)} vs {len(y_pred)}")
    if len(y_true) < 2:
        return {
            "ci": None,
            "comparable_pairs": 0,
            "tied_pairs": 0,
            "status": "undefined",
            "reason": "insufficient_samples_less_than_2"
        }
    if not (np.all(np.isfinite(y_true)) and np.all(np.isfinite(y_pred))):
        return {
            "ci": None,
            "comparable_pairs": 0,
            "tied_pairs": 0,
            "status": "invalid_input",
            "reason": "non_finite_values_in_input"
        }

    if _fast_ci_core is not None:
        num, denom, ties = _fast_ci_core(y_true, y_pred)
    else:
        n = len(y_true)
        num = 0.0
        denom = 0.0
        ties = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if y_true[i] > y_true[j]:
                    denom += 1.0
                    if y_pred[i] > y_pred[j]:
                        num += 1.0
                    elif y_pred[i] == y_pred[j]:
                        num += 0.5
                        ties += 1.0
                elif y_true[j] > y_true[i]:
                    denom += 1.0
                    if y_pred[j] > y_pred[i]:
                        num += 1.0
                    elif y_pred[j] == y_pred[i]:
                        num += 0.5
                        ties += 1.0

    if denom == 0.0:
        return {
            "ci": None,
            "comparable_pairs": 0,
            "tied_pairs": int(ties),
            "status": "undefined",
            "reason": "zero_true_label_variance_no_comparable_pairs"
        }

    return {
        "ci": float(num / denom),
        "comparable_pairs": int(denom),
        "tied_pairs": int(ties),
        "status": "valid",
        "reason": None
    }


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """Compute comprehensive regression metrics with strict undefined-state handling."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    n = len(y_true)

    if n == 0:
        return {
            "status": "empty_subset",
            "reason": "zero_samples",
            "n_samples": 0,
            "comparable_pairs": 0,
            "tied_pairs": 0,
            "rmse": None,
            "mae": None,
            "pearson_r": None,
            "spearman_rho": None,
            "concordance_index": None,
            "rmse_raw": None,
            "mae_raw": None,
            "pearson_r_raw": None,
            "spearman_rho_raw": None,
            "concordance_index_raw": None,
        }

    if not (np.all(np.isfinite(y_true)) and np.all(np.isfinite(y_pred))):
        return {
            "status": "invalid_input",
            "reason": "non_finite_values_detected",
            "n_samples": n,
            "comparable_pairs": 0,
            "tied_pairs": 0,
            "rmse": None,
            "mae": None,
            "pearson_r": None,
            "spearman_rho": None,
            "concordance_index": None,
            "rmse_raw": None,
            "mae_raw": None,
            "pearson_r_raw": None,
            "spearman_rho_raw": None,
            "concordance_index_raw": None,
        }

    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))

    std_true = float(np.std(y_true))
    std_pred = float(np.std(y_pred))

    ci_info = compute_ci(y_true, y_pred)
    ci_raw = ci_info["ci"]
    ci_rounded = round(ci_raw, 4) if ci_raw is not None else None

    # Correlation checks
    pearson_r_raw: Optional[float] = None
    spearman_rho_raw: Optional[float] = None
    corr_status = "valid"
    corr_reason = None

    if std_true < 1e-9:
        corr_status = "undefined"
        corr_reason = "zero_true_label_variance"
    elif std_pred < 1e-9:
        corr_status = "undefined"
        corr_reason = "constant_prediction_collapse"
    else:
        pr, _ = scipy.stats.pearsonr(y_true, y_pred)
        sr, _ = scipy.stats.spearmanr(y_true, y_pred)
        pearson_r_raw = float(pr) if not math.isnan(pr) else None
        spearman_rho_raw = float(sr) if not math.isnan(sr) else None

    pearson_r = round(pearson_r_raw, 4) if pearson_r_raw is not None else None
    spearman_rho = round(spearman_rho_raw, 4) if spearman_rho_raw is not None else None

    overall_status = "valid"
    if ci_info["status"] != "valid" or corr_status != "valid":
        overall_status = "partial_or_undefined"

    return {
        "status": overall_status,
        "ci_status": ci_info["status"],
        "ci_reason": ci_info["reason"],
        "corr_status": corr_status,
        "corr_reason": corr_reason,
        "n_samples": n,
        "comparable_pairs": ci_info["comparable_pairs"],
        "tied_pairs": ci_info["tied_pairs"],
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "pearson_r": pearson_r,
        "spearman_rho": spearman_rho,
        "concordance_index": ci_rounded,
        "rmse_raw": rmse,
        "mae_raw": mae,
        "pearson_r_raw": pearson_r_raw,
        "spearman_rho_raw": spearman_rho_raw,
        "concordance_index_raw": ci_raw
    }


def run_self_tests():
    """Verify that edge cases behave correctly according to P1-05/R3 specifications."""
    print("Running self-test suite for edge cases...")
    
    # 1. Zero label variance (e.g. y = [5.0, 5.0, 5.0])
    res1 = compute_metrics(np.array([5.0, 5.0, 5.0]), np.array([4.0, 5.0, 6.0]))
    assert res1["concordance_index"] is None, "Expected None CI for zero label variance"
    assert res1["pearson_r"] is None, "Expected None Pearson for zero label variance"
    assert res1["spearman_rho"] is None, "Expected None Spearman for zero label variance"
    assert res1["ci_status"] == "undefined"
    assert res1["comparable_pairs"] == 0
    print("  [PASS] Zero true label variance correctly yields undefined (None) for CI/Pearson/Spearman.")

    # 2. Constant prediction collapse (e.g. pred = [5.0, 5.0, 5.0])
    res2 = compute_metrics(np.array([5.0, 6.0, 7.0]), np.array([5.0, 5.0, 5.0]))
    assert res2["pearson_r"] is None, "Expected None Pearson for constant prediction"
    assert res2["spearman_rho"] is None, "Expected None Spearman for constant prediction"
    assert res2["concordance_index"] == 0.5, "Expected 0.5 CI for constant prediction with ties"
    assert res2["comparable_pairs"] == 3
    assert res2["tied_pairs"] == 3
    print("  [PASS] Constant prediction correctly yields None Pearson and 0.5 CI with all pairs tied.")

    # 3. Empty input
    res3 = compute_metrics(np.array([]), np.array([]))
    assert res3["status"] == "empty_subset"
    assert res3["concordance_index"] is None
    print("  [PASS] Empty subset correctly identified.")

    # 4. Non-finite values
    res4 = compute_metrics(np.array([5.0, np.nan, 7.0]), np.array([5.0, 6.0, 7.0]))
    assert res4["status"] == "invalid_input"
    print("  [PASS] Non-finite input correctly caught.")
    print("Self-test suite completed successfully.\n")


def main():
    run_self_tests()

    print(f"Loading predictions from: {PRED_PATH}")
    df = pd.read_csv(PRED_PATH)
    assert len(df) == 25772, f"Expected 25772 rows, got {len(df)}"
    
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        saved_summary = json.load(f)
        
    models = [
        "ridge_alpha10",
        "ridge_alpha50",
        "hist_gradient_boosting",
        "random_forest",
        "stacked_ensemble"
    ]
    domains = [
        "train_block",
        "strict_dual_cold_test",
        "cold_target_test",
        "cold_drug_test"
    ]
    
    recomputed = {}
    max_delta = 0.0
    delta_details = []
    
    df_active = df[df["true_pkd"] > 5.0]
    print(f"Total pairs: {len(df)}, Active pairs (pKd > 5.0): {len(df_active)} ({len(df_active)/len(df)*100:.2f}%)")
    
    for m in models:
        pred_col = f"pred_{m}"
        assert pred_col in df.columns, f"Missing column {pred_col}"
        recomputed[m] = {"domains": {}, "active_subset_domains": {}}
        
        for dom in domains:
            sub = df[df["domain"] == dom]
            y_t = sub["true_pkd"].values
            y_p = sub[pred_col].values
            m_res = compute_metrics(y_t, y_p)
            recomputed[m]["domains"][dom] = m_res
            
            sub_act = df_active[df_active["domain"] == dom]
            if len(sub_act) > 0:
                act_res = compute_metrics(sub_act["true_pkd"].values, sub_act[pred_col].values)
                recomputed[m]["active_subset_domains"][dom] = act_res
            else:
                recomputed[m]["active_subset_domains"][dom] = compute_metrics(np.array([]), np.array([]))
            
            saved_m = saved_summary.get("models", {}).get(m, {}).get("domains", {}).get(dom, {})
            for k in ["concordance_index", "rmse", "mae", "pearson_r", "spearman_rho"]:
                if k in saved_m and m_res[k] is not None:
                    saved_val = saved_m[k]
                    rec_val = m_res[k]
                    diff = abs(saved_val - rec_val)
                    if diff > max_delta:
                        max_delta = diff
                    if diff > 1e-4:
                        delta_details.append(f"Model {m}, Domain {dom}, Metric {k}: saved={saved_val}, rec={rec_val}, diff={diff}")
                        
    print(f"\nVerification Results on Benchmark Domains:")
    print(f"Max delta between recomputed and saved 4-decimal rounded metrics: {max_delta:.8f}")
    if delta_details:
        print("Discrepancies > 1e-4:")
        for d in delta_details:
            print("  " + d)
    else:
        print("All metrics match within 4-decimal precision (PASS)")
        
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "recomputed_metrics": recomputed,
            "max_delta": max_delta,
            "verified": len(delta_details) == 0,
            "edge_cases_handling": "v5 compliant: undefined states and zero variance strictly handled"
        }, f, indent=2)
    print(f"Recomputed metrics saved to: {OUT_PATH}")


if __name__ == "__main__":
    main()
