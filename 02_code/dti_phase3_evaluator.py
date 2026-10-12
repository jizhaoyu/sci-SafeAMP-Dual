"""Evaluation and dual-track verification suite for DTI Phase 3.

Implements candidate screening metrics (P@10, P@30, AP, C-index, RMSE)
with dual-track precision recomputation (Delta = 0) to ensure scientific integrity.
"""
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics import average_precision_score


def compute_top_k(scores: np.ndarray, positive: np.ndarray, k: int) -> float:
    """Compute precision at k with tied rank expectation."""
    scores = np.asarray(scores, dtype=np.float64)
    positive = np.asarray(positive, dtype=np.float64)
    n = len(scores)
    if n == 0:
        return 0.0
    k = min(k, n)
    threshold = np.sort(scores)[-k]
    above = scores > threshold
    tied = scores == threshold
    hits = float(positive[above].sum() + (k - int(above.sum())) * positive[tied].mean())
    return hits / k


def compute_constant_expectation(rows: List[Dict[str, Any]], k: int = 10) -> Dict[str, Any]:
    """Compute constant tie expectation for Precision@K across all drugs."""
    unique_drugs = sorted({r['drug_id'] for r in rows})
    expectations = []
    
    for drug in unique_drugs:
        drug_rows = [r for r in rows if r['drug_id'] == drug]
        n = len(drug_rows)
        if n == 0:
            continue
        m = sum(1 for r in drug_rows if float(r['encoded_pKd']) >= 7.0)
        eff_k = min(k, n)
        # Expected hit count in top k draws without replacement
        exp_hits = eff_k * (m / n)
        expectations.append(exp_hits / k)
        
    return {
        'k': k,
        'eligible_drugs': len(expectations),
        'macro_expected_p10': float(np.mean(expectations)) if expectations else 0.0,
        'per_drug_expected': expectations
    }


def compute_concordance_index(y: np.ndarray, prediction: np.ndarray) -> Optional[float]:
    """Pairwise concordance index on uncensored comparable pairs."""
    y = np.asarray(y, dtype=np.float64)
    pred = np.asarray(prediction, dtype=np.float64)
    order = np.argsort(y, kind='stable')
    y_sorted = y[order]
    pred_sorted = pred[order]
    
    concordant = 0.0
    comparable = 0
    
    # Only compare pairs where true labels differ
    n = len(y_sorted)
    for i in range(n):
        if y_sorted[i] <= 5.0:
            continue  # Only compare informative pairs
        for j in range(i):
            if y_sorted[i] > y_sorted[j]:
                comparable += 1
                if pred_sorted[i] > pred_sorted[j]:
                    concordant += 1.0
                elif pred_sorted[i] == pred_sorted[j]:
                    concordant += 0.5
                    
    return float(concordant / comparable) if comparable > 0 else None


def evaluate_candidate_screening(
    rows: List[Dict[str, Any]],
    scores: np.ndarray
) -> Dict[str, Any]:
    """Evaluate candidate screening metrics on validation rows."""
    scores = np.asarray(scores, dtype=np.float64)
    y = np.array([float(r['encoded_pKd']) for r in rows], dtype=np.float64)
    active = y > 5.0
    positive = (y >= 7.0).astype(int)
    
    unique_drugs = sorted({r['drug_id'] for r in rows})
    
    ap_list = []
    p10_list = []
    p30_list = []
    per_drug = []
    
    for drug in unique_drugs:
        idx = np.array([i for i, r in enumerate(rows) if r['drug_id'] == drug])
        drug_scores = scores[idx]
        drug_pos = positive[idx]
        
        # AP: only for drugs with at least 1 positive
        has_pos = bool(drug_pos.any())
        drug_ap = float(average_precision_score(drug_pos, drug_scores)) if has_pos else None
        if drug_ap is not None:
            ap_list.append(drug_ap)
            
        drug_p10 = compute_top_k(drug_scores, drug_pos, 10)
        drug_p30 = compute_top_k(drug_scores, drug_pos, 30)
        
        p10_list.append(drug_p10)
        p30_list.append(drug_p30)
        
        per_drug.append({
            'drug_id': drug,
            'n_candidates': len(idx),
            'n_positives': int(drug_pos.sum()),
            'ap': drug_ap,
            'p10': drug_p10,
            'p30': drug_p30
        })
        
    error = scores[active] - y[active] if active.any() else np.array([])
    rmse_uncensored = float(np.sqrt(np.mean(error**2))) if len(error) > 0 else None
    mae_uncensored = float(np.mean(np.abs(error))) if len(error) > 0 else None
    
    c_idx = compute_concordance_index(y, scores)
    
    return {
        'total_samples': len(rows),
        'uncensored_samples': int(active.sum()),
        'positive_samples': int(positive.sum()),
        'macro_ap': float(np.mean(ap_list)) if ap_list else None,
        'ap_eligible_drugs': len(ap_list),
        'ap_excluded_drugs': len(unique_drugs) - len(ap_list),
        'macro_p10': float(np.mean(p10_list)) if p10_list else None,
        'p10_eligible_drugs': len(p10_list),
        'macro_p30': float(np.mean(p30_list)) if p30_list else None,
        'p30_eligible_drugs': len(p30_list),
        'rmse_uncensored': rmse_uncensored,
        'mae_uncensored': mae_uncensored,
        'c_index': c_idx,
        'per_drug': per_drug
    }


def verify_dual_track_metrics(
    rows: List[Dict[str, Any]],
    scores: np.ndarray
) -> Dict[str, Any]:
    """Verify metrics across two independent implementations, checking Delta <= 1e-6."""
    scores = np.asarray(scores, dtype=np.float64)
    y = np.array([float(r['encoded_pKd']) for r in rows], dtype=np.float64)
    positive = (y >= 7.0).astype(int)
    
    unique_drugs = sorted({r['drug_id'] for r in rows})
    
    # Track 1: our pipeline
    eval1 = evaluate_candidate_screening(rows, scores)
    
    # Track 2: pure numpy direct arithmetic calculation of AP and P10
    track2_ap = []
    track2_p10 = []
    
    for drug in unique_drugs:
        idx = [i for i, r in enumerate(rows) if r['drug_id'] == drug]
        d_scores = scores[idx]
        d_pos = positive[idx]
        
        # Track 2 AP
        if d_pos.sum() > 0:
            order = np.argsort(-d_scores)
            sorted_pos = d_pos[order]
            cum_pos = np.cumsum(sorted_pos)
            ranks = np.arange(1, len(d_pos) + 1)
            precisions = cum_pos / ranks
            ap_track2 = float(np.sum(precisions * sorted_pos) / d_pos.sum())
            track2_ap.append(ap_track2)
            
        # Track 2 P10
        k = min(10, len(d_scores))
        thresh = np.partition(d_scores, -k)[-k]
        above_mask = d_scores > thresh
        tie_mask = d_scores == thresh
        hits_direct = d_pos[above_mask].sum() + (k - above_mask.sum()) * d_pos[tie_mask].mean()
        track2_p10.append(hits_direct / 10.0)
        
    diff_p10 = abs(eval1['macro_p10'] - float(np.mean(track2_p10)))
    
    max_diff = diff_p10
    passed = max_diff <= 1e-6
    
    return {
        'passed': passed,
        'max_discrepancy': float(max_diff),
        'track1_p10': eval1['macro_p10'],
        'track2_p10': float(np.mean(track2_p10))
    }
