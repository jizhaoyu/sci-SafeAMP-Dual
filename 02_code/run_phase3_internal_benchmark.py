"""Runs 4-fold controlled comparison of 3 models on internal training block.

12 fits in total:
- HGBContinuousBaseline (regression control)
- LogRegCandidateClassifier (linear binary classifier)
- HGBBinaryClassifier (non-linear binary classifier)

Checks dual-track precision and verifies circuit breaker rules.
"""
import csv
import json
import time
from pathlib import Path
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dti_candidate_classifiers import (
    HGBContinuousBaseline,
    LogRegCandidateClassifier,
    HGBBinaryClassifier,
)
from dti_phase3_evaluator import (
    evaluate_candidate_screening,
    compute_constant_expectation,
    verify_dual_track_metrics,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/dti-phase3-candidate-screening-20261012'
SPLITS_DIR = OUT / 'splits'
REVIEW = ROOT / 'output/dti-internal-validation-review-20261012'
FEAT_DIR = ROOT / '03_experiments/prepared/dti_davis_features_20261006_v1'


def load_dataset():
    with (REVIEW / 'internal_assignments.csv').open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    drug_ids = json.loads((FEAT_DIR / 'drug_ids.json').read_text(encoding='utf-8-sig'))
    target_ids = json.loads((FEAT_DIR / 'target_ids.json').read_text(encoding='utf-8-sig'))
    drug_feats = np.load(FEAT_DIR / 'drug_features.npy', allow_pickle=False)
    target_feats = np.load(FEAT_DIR / 'target_features.npy', allow_pickle=False)
    
    dm = {d: i for i, d in enumerate(drug_ids)}
    tm = {t: i for i, t in enumerate(target_ids)}
    
    di = [dm[r['drug_id']] for r in rows]
    ti = [tm[r['target_id']] for r in rows]
    
    X = np.concatenate([drug_feats[di], target_feats[ti]], axis=1)
    y_cont = np.array([float(r['encoded_pKd']) for r in rows], dtype=np.float64)
    y_bin = (y_cont >= 7.0).astype(int)
    
    return rows, X, y_cont, y_bin


def run_benchmark():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, X, y_cont, y_bin = load_dataset()
    
    with (SPLITS_DIR / 'splits_manifest.json').open(encoding='utf-8') as f:
        manifest = json.load(f)
        
    results = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'folds': len(manifest),
        'total_rows': len(rows),
        'models': ['HGBContinuousBaseline', 'LogRegCandidateClassifier', 'HGBBinaryClassifier'],
        'fold_results': [],
        'summary': {}
    }
    
    domains = ['val_dual_cold', 'val_drug_cold', 'val_target_cold']
    
    print('Starting 4-fold controlled benchmark (12 fits total)...')
    
    for item in manifest:
        fold = item['fold']
        with (SPLITS_DIR / f'fold_{fold}.json').open(encoding='utf-8') as f:
            split_data = json.load(f)
            
        train_idx = np.array(split_data['train_idx'], dtype=np.int64)
        X_tr = X[train_idx]
        y_tr_cont = y_cont[train_idx]
        y_tr_bin = y_bin[train_idx]
        
        # Instantiate 3 models
        models = {
            'HGBContinuousBaseline': HGBContinuousBaseline(max_iter=50, random_state=42),
            'LogRegCandidateClassifier': LogRegCandidateClassifier(C=1.0, random_state=42),
            'HGBBinaryClassifier': HGBBinaryClassifier(max_iter=50, random_state=42),
        }
        
        # Fit
        models['HGBContinuousBaseline'].fit(X_tr, y_tr_cont)
        models['LogRegCandidateClassifier'].fit(X_tr, y_tr_bin)
        models['HGBBinaryClassifier'].fit(X_tr, y_tr_bin)
        
        fold_record = {'fold': fold, 'domain_metrics': {}}
        
        for dom in domains:
            idx = np.array(split_data[f'{dom}_idx'], dtype=np.int64)
            dom_rows = [rows[i] for i in idx]
            X_val = X[idx]
            
            # Constant tie expectation reference
            exp_ref = compute_constant_expectation(dom_rows, k=10)
            
            dom_record = {
                'constant_expectation': exp_ref['macro_expected_p10'],
                'model_scores': {}
            }
            
            for m_name, model in models.items():
                scores = model.predict_score(X_val)
                metrics = evaluate_candidate_screening(dom_rows, scores)
                verif = verify_dual_track_metrics(dom_rows, scores)
                
                dom_record['model_scores'][m_name] = {
                    'macro_p10': metrics['macro_p10'],
                    'macro_p30': metrics['macro_p30'],
                    'macro_ap': metrics['macro_ap'],
                    'c_index': metrics['c_index'],
                    'rmse_uncensored': metrics['rmse_uncensored'],
                    'ap_eligible_drugs': metrics['ap_eligible_drugs'],
                    'ap_excluded_drugs': metrics['ap_excluded_drugs'],
                    'dual_track_passed': verif['passed'],
                    'max_discrepancy': verif['max_discrepancy']
                }
                
            fold_record['domain_metrics'][dom] = dom_record
            
        results['fold_results'].append(fold_record)
        print(f"Fold {fold} complete.")
        
    # Calculate macro average across 4 folds for dual cold
    summary = {}
    for m_name in results['models']:
        p10s = [f['domain_metrics']['val_dual_cold']['model_scores'][m_name]['macro_p10'] for f in results['fold_results']]
        aps = [f['domain_metrics']['val_dual_cold']['model_scores'][m_name]['macro_ap'] for f in results['fold_results']]
        cis = [f['domain_metrics']['val_dual_cold']['model_scores'][m_name]['c_index'] for f in results['fold_results']]
        summary[m_name] = {
            'mean_dual_cold_p10': float(np.mean(p10s)),
            'std_dual_cold_p10': float(np.std(p10s)),
            'mean_dual_cold_ap': float(np.mean(aps)),
            'std_dual_cold_ap': float(np.std(aps)),
            'mean_dual_cold_c_index': float(np.mean(cis)),
        }
        
    exp_p10s = [f['domain_metrics']['val_dual_cold']['constant_expectation'] for f in results['fold_results']]
    summary['constant_expectation'] = {
        'mean_dual_cold_p10': float(np.mean(exp_p10s)),
        'std_dual_cold_p10': float(np.std(exp_p10s))
    }
    
    # Circuit breaker check: did best model beat constant reference?
    best_model_name = max(['LogRegCandidateClassifier', 'HGBBinaryClassifier'],
                          key=lambda m: summary[m]['mean_dual_cold_p10'])
    best_p10 = summary[best_model_name]['mean_dual_cold_p10']
    const_p10 = summary['constant_expectation']['mean_dual_cold_p10']
    
    circuit_breaker = best_p10 < const_p10
    summary['circuit_breaker_triggered'] = circuit_breaker
    summary['best_model'] = best_model_name
    summary['beaten_constant_reference'] = not circuit_breaker
    
    results['summary'] = summary
    
    with (OUT / 'internal_results.json').open('w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
        
    print(f"Benchmark finished. Results saved to {OUT / 'internal_results.json'}")
    return results


if __name__ == '__main__':
    run_benchmark()
