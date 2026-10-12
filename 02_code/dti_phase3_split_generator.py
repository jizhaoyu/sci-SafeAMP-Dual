"""4-fold entity-isolated split generator for DTI Phase 3.

Constructs strict drug-isolated, target-isolated, and dual-cold validation splits
within the internal training block, ensuring zero statistics leakage.
"""
import json
from pathlib import Path
from typing import List, Dict, Any
import numpy as np


def generate_four_fold_isolated_splits(
    rows: List[Dict[str, Any]],
    n_splits: int = 4,
    random_state: int = 42
) -> List[Dict[str, np.ndarray]]:
    """Partition dataset into n_splits with strict entity isolation."""
    rng = np.random.RandomState(random_state)
    
    unique_drugs = sorted({r['drug_id'] for r in rows})
    unique_targets = sorted({r['target_id'] for r in rows})
    
    shuffled_drugs = unique_drugs.copy()
    rng.shuffle(shuffled_drugs)
    
    shuffled_targets = unique_targets.copy()
    rng.shuffle(shuffled_targets)
    
    drug_folds = np.array_split(shuffled_drugs, n_splits)
    target_folds = np.array_split(shuffled_targets, n_splits)
    
    splits = []
    
    drug_to_idx = {r['drug_id']: i for i, r in enumerate(rows)}
    
    for fold_i in range(n_splits):
        val_drugs = set(drug_folds[fold_i])
        val_targets = set(target_folds[fold_i])
        
        train_drugs = set(unique_drugs) - val_drugs
        train_targets = set(unique_targets) - val_targets
        
        train_idx = []
        val_drug_cold_idx = []
        val_target_cold_idx = []
        val_dual_cold_idx = []
        
        for idx, r in enumerate(rows):
            d, t = r['drug_id'], r['target_id']
            in_train_d = d in train_drugs
            in_train_t = t in train_targets
            in_val_d = d in val_drugs
            in_val_t = t in val_targets
            
            if in_train_d and in_train_t:
                train_idx.append(idx)
            elif in_val_d and in_train_t:
                val_drug_cold_idx.append(idx)
            elif in_train_d and in_val_t:
                val_target_cold_idx.append(idx)
            elif in_val_d and in_val_t:
                val_dual_cold_idx.append(idx)
                
        splits.append({
            'fold': fold_i,
            'train_idx': np.array(train_idx, dtype=np.int64),
            'val_drug_cold_idx': np.array(val_drug_cold_idx, dtype=np.int64),
            'val_target_cold_idx': np.array(val_target_cold_idx, dtype=np.int64),
            'val_dual_cold_idx': np.array(val_dual_cold_idx, dtype=np.int64),
        })
        
    return splits


def save_splits(splits: List[Dict[str, np.ndarray]], out_dir: Path):
    """Save split indices to JSON files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for s in splits:
        fold = s['fold']
        fold_dict = {
            'fold': fold,
            'train_size': len(s['train_idx']),
            'val_drug_cold_size': len(s['val_drug_cold_idx']),
            'val_target_cold_size': len(s['val_target_cold_idx']),
            'val_dual_cold_size': len(s['val_dual_cold_idx']),
            'train_idx': s['train_idx'].tolist(),
            'val_drug_cold_idx': s['val_drug_cold_idx'].tolist(),
            'val_target_cold_idx': s['val_target_cold_idx'].tolist(),
            'val_dual_cold_idx': s['val_dual_cold_idx'].tolist(),
        }
        fold_file = out_dir / f'fold_{fold}.json'
        with fold_file.open('w', encoding='utf-8') as f:
            json.dump(fold_dict, f, indent=2)
        manifest.append({
            'fold': fold,
            'file': fold_file.name,
            'train_size': fold_dict['train_size'],
            'val_drug_cold_size': fold_dict['val_drug_cold_size'],
            'val_target_cold_size': fold_dict['val_target_cold_size'],
            'val_dual_cold_size': fold_dict['val_dual_cold_size'],
        })
        
    manifest_file = out_dir / 'splits_manifest.json'
    with manifest_file.open('w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    return manifest_file
