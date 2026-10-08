"""Active Learning Wet-lab Assay Feedback and Empirical Bayes Recalibration Engine.

Ingests wet-lab biological test results (measured Kd / IC50 values), calculates prediction
residuals, applies Tanimoto-kernel residual propagation, shrinks posterior uncertainty,
and updates Bayesian acquisition rankings (EI / UCB).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
import numpy as np

from test_molecular_similarity import get_morgan_fingerprint, tanimoto


def calibrate_with_wetlab_feedback(
    target_name: str,
    candidates: List[Dict[str, Any]],
    measurements: List[Dict[str, Any]],
    y_best_reference: float = 7.50
) -> Dict[str, Any]:
    """Recalibrate candidate predictions and acquisition functions using wet-lab assay measurements."""
    if not measurements:
        return {
            "status": "no_measurements",
            "message": "未提供湿实验实测数据，保持模型原始推断。",
            "calibrated_candidates": candidates,
            "metrics": {}
        }

    # 1. Process and normalize wet-lab measurements
    processed_assays = []
    for m in measurements:
        smi = m.get("smiles", "").strip()
        if not smi:
            continue

        kd_nM = float(m.get("measured_kd_nM", 0.0))
        if "measured_pkd" in m and float(m["measured_pkd"]) > 0:
            meas_pkd = float(m["measured_pkd"])
        elif kd_nM > 0:
            meas_pkd = round(-math.log10(kd_nM * 1e-9), 3)
        else:
            meas_pkd = 5.0

        fp = get_morgan_fingerprint(smi)
        processed_assays.append({
            "smiles": smi,
            "name": m.get("name", "Assayed Compound"),
            "measured_kd_nM": kd_nM,
            "measured_pkd": meas_pkd,
            "notes": m.get("notes", "Wet-lab Assay"),
            "fingerprint": fp
        })

    if not processed_assays:
        return {
            "status": "no_valid_assays",
            "message": "未能解析有效的实测化合物 SMILES 或浓度值。",
            "calibrated_candidates": candidates,
            "metrics": {}
        }

    # 2. Match with predictions to compute model accuracy & residuals on tested set
    residuals = []
    assayed_pairs = []
    
    for a in processed_assays:
        # Match with candidate list or fallback
        matched_cand = next((c for c in candidates if c.get("smiles") == a["smiles"]), None)
        pred_pkd = float(matched_cand.get("predicted_pkd", 7.0)) if matched_cand else 7.0
        res_i = a["measured_pkd"] - pred_pkd
        residuals.append(res_i)
        assayed_pairs.append({
            "name": a["name"],
            "smiles": a["smiles"],
            "pred_pkd": pred_pkd,
            "meas_pkd": a["measured_pkd"],
            "residual": round(res_i, 3)
        })

    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(np.square(residuals))))
    mean_bias = float(np.mean(residuals))

    # Updated global best reference
    all_meas_pkds = [a["measured_pkd"] for a in processed_assays]
    updated_y_best = max(y_best_reference, max(all_meas_pkds))

    # 3. Kernel residual interpolation & posterior uncertainty shrinkage
    calibrated_list = []
    
    for orig_idx, cand in enumerate(candidates):
        c_smi = cand.get("smiles", "")
        c_fp = get_morgan_fingerprint(c_smi)
        prior_pkd = float(cand.get("predicted_pkd", 7.0))
        prior_sigma = float(cand.get("uncertainty_sigma", 0.45))

        # Check if this candidate itself was assayed
        exact_match = next((a for a in processed_assays if a["smiles"] == c_smi), None)
        if exact_match:
            calibrated_pkd = exact_match["measured_pkd"]
            calibrated_sigma = 0.05  # Experimental measurement has very low residual uncertainty
            shift = round(calibrated_pkd - prior_pkd, 3)
            is_verified = True
        else:
            # Spatial Kernel interpolation: weighted average of residuals based on Tanimoto^2
            sims = [tanimoto(c_fp, a["fingerprint"]) for a in processed_assays]
            max_sim = max(sims) if sims else 0.0

            weights = [s ** 2.5 for s in sims]
            weight_sum = sum(weights) + 0.15

            # Kernel smoothed residual shift
            kernel_shift = sum(w * r for w, r in zip(weights, residuals)) / weight_sum
            # Scale shift by confidence of nearest neighbor
            effective_shift = kernel_shift * min(1.0, max_sim * 1.5)

            calibrated_pkd = round(prior_pkd + effective_shift, 3)
            shift = round(effective_shift, 3)

            # Posterior uncertainty shrinks near measured chemicals
            shrinkage_factor = math.sqrt(max(0.12, 1.0 - 0.75 * (max_sim ** 2)))
            calibrated_sigma = round(prior_sigma * shrinkage_factor, 3)
            is_verified = False

        # Compute updated Kd
        calibrated_kd = round(math.pow(10, 9.0 - calibrated_pkd), 2)

        # Recalculate Expected Improvement (EI)
        # EI = (mu - y*) * Phi(Z) + sigma * phi(Z)
        diff = calibrated_pkd - updated_y_best
        if calibrated_sigma > 1e-4:
            z = diff / calibrated_sigma
            # Standard Gaussian cdf and pdf approximations
            phi = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
            phi_cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
            calibrated_ei = round(max(0.0, diff * phi_cdf + calibrated_sigma * phi), 4)
        else:
            calibrated_ei = round(max(0.0, diff), 4)

        # Recalculate UCB score
        calibrated_ucb = round(calibrated_pkd + 1.96 * calibrated_sigma, 3)

        updated_cand = dict(cand)
        updated_cand.update({
            "prior_pkd": prior_pkd,
            "calibrated_pkd": calibrated_pkd,
            "calibrated_kd_nM": calibrated_kd,
            "delta_calibration": shift,
            "prior_uncertainty_sigma": prior_sigma,
            "calibrated_uncertainty_sigma": calibrated_sigma,
            "calibrated_ei": calibrated_ei,
            "calibrated_ucb": calibrated_ucb,
            "is_experimentally_verified": is_verified,
            "original_rank": orig_idx + 1
        })
        calibrated_list.append(updated_cand)

    # 4. Sort calibrated candidates by calibrated pKd descending
    calibrated_list.sort(key=lambda c: (c["calibrated_pkd"], c["calibrated_ei"]), reverse=True)

    # Annotate rank shifts
    for new_rank, c in enumerate(calibrated_list):
        c["new_rank"] = new_rank + 1
        c["rank_shift"] = c["original_rank"] - c["new_rank"]  # Positive means promoted

    promoted_cands = [c for c in calibrated_list if c["rank_shift"] > 0][:5]

    narrative = (
        f"成功闭环回流 {len(processed_assays)} 个湿实验实测数据点。"
        f"在已测候选物集上，模型平均绝对误差 MAE = {mae:.3f} pKd，均方根误差 RMSE = {rmse:.3f} pKd，"
        f"系统性偏差 Bias = {'+' if mean_bias > 0 else ''}{mean_bias:.3f} pKd。"
        f"贝叶斯核传播已动态校准未测候选分子的局部均值与不确定性，并重排优化阶梯榜。"
    )

    return {
        "status": "success",
        "target_name": target_name,
        "assayed_count": len(processed_assays),
        "updated_y_best": round(updated_y_best, 3),
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mean_bias": round(mean_bias, 4),
        "assayed_evaluations": assayed_pairs,
        "calibrated_candidates": calibrated_list,
        "promoted_candidates": promoted_cands,
        "narrative": narrative
    }
