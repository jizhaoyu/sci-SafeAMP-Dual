import pytest
import numpy as np

from dti_phase3_evaluator import (
    evaluate_candidate_screening,
    compute_constant_expectation,
    verify_dual_track_metrics
)


def test_dual_track_metrics_precision():
    # Synthetic test data for 3 drugs
    # Drug 0: 10 items, 2 positives
    # Drug 1: 15 items, 0 positives (should be excluded from AP, but included in P@10)
    # Drug 2: 20 items, 5 positives
    rows = []
    scores = []
    
    # Drug 0
    for i in range(10):
        y = 7.5 if i < 2 else 5.0
        rows.append({'drug_id': 'D0', 'target_id': f'T{i}', 'encoded_pKd': y})
        scores.append(10.0 - i)  # perfect order
        
    # Drug 1: all negative
    for i in range(15):
        rows.append({'drug_id': 'D1', 'target_id': f'T{i}', 'encoded_pKd': 5.0})
        scores.append(float(i))
        
    # Drug 2
    for i in range(20):
        y = 8.0 if i < 5 else 5.0
        rows.append({'drug_id': 'D2', 'target_id': f'T{i}', 'encoded_pKd': y})
        scores.append(20.0 - i)
        
    scores = np.array(scores)
    
    metrics = evaluate_candidate_screening(rows, scores)
    
    # Check dual-track verification
    verification = verify_dual_track_metrics(rows, scores)
    assert verification['passed'] is True
    assert verification['max_discrepancy'] <= 1e-6
    
    # AP should only cover D0 and D2 (2 eligible drugs)
    assert metrics['ap_eligible_drugs'] == 2
    assert metrics['ap_excluded_drugs'] == 1
    assert metrics['macro_ap'] is not None
    assert metrics['macro_ap'] > 0.0
    
    # P@10 should cover all 3 drugs
    assert metrics['p10_eligible_drugs'] == 3
    assert metrics['macro_p10'] is not None


def test_constant_expectation():
    rows = []
    # D0: 10 items, 2 positives -> P@10 exp = 2/10 = 0.2
    for i in range(10):
        rows.append({'drug_id': 'D0', 'target_id': f'T{i}', 'encoded_pKd': 7.5 if i < 2 else 5.0})
    # D1: 10 items, 0 positives -> P@10 exp = 0
    for i in range(10):
        rows.append({'drug_id': 'D1', 'target_id': f'T{i}', 'encoded_pKd': 5.0})
        
    exp = compute_constant_expectation(rows, k=10)
    # Average of 0.2 and 0.0 = 0.1
    assert pytest.approx(exp['macro_expected_p10'], abs=1e-6) == 0.1
