import pytest
import numpy as np

from dti_phase3_split_generator import generate_four_fold_isolated_splits


def test_four_fold_entity_isolation():
    # Mini synthetic dataset of pairs
    # 8 drugs, 12 targets, total pairs
    drugs = [f'D_{i}' for i in range(8)]
    targets = [f'T_{j}' for j in range(12)]
    
    rows = []
    for d in drugs:
        for t in targets:
            rows.append({'drug_id': d, 'target_id': t, 'encoded_pKd': 5.0})
            
    splits = generate_four_fold_isolated_splits(rows, n_splits=4, random_state=42)
    assert len(splits) == 4
    
    for fold_i, split in enumerate(splits):
        assert 'train_idx' in split
        assert 'val_drug_cold_idx' in split
        assert 'val_target_cold_idx' in split
        assert 'val_dual_cold_idx' in split
        
        train_drugs = {rows[i]['drug_id'] for i in split['train_idx']}
        train_targets = {rows[i]['target_id'] for i in split['train_idx']}
        
        # 1. val_drug_cold: drugs must be cold, targets may overlap
        val_drug_cold_drugs = {rows[i]['drug_id'] for i in split['val_drug_cold_idx']}
        assert len(val_drug_cold_drugs & train_drugs) == 0, f'Fold {fold_i}: drug leak in cold drug val'
        
        # 2. val_target_cold: targets must be cold, drugs may overlap
        val_target_cold_targets = {rows[i]['target_id'] for i in split['val_target_cold_idx']}
        assert len(val_target_cold_targets & train_targets) == 0, f'Fold {fold_i}: target leak in cold target val'
        
        # 3. val_dual_cold: BOTH drugs and targets must be disjoint from train
        val_dual_drugs = {rows[i]['drug_id'] for i in split['val_dual_cold_idx']}
        val_dual_targets = {rows[i]['target_id'] for i in split['val_dual_cold_idx']}
        assert len(val_dual_drugs & train_drugs) == 0, f'Fold {fold_i}: drug leak in dual cold val'
        assert len(val_dual_targets & train_targets) == 0, f'Fold {fold_i}: target leak in dual cold val'
        
        # Ensure non-empty
        assert len(split['train_idx']) > 0
        assert len(split['val_drug_cold_idx']) > 0
        assert len(split['val_target_cold_idx']) > 0
        assert len(split['val_dual_cold_idx']) > 0


def test_split_determinism():
    drugs = [f'D_{i}' for i in range(4)]
    targets = [f'T_{j}' for j in range(6)]
    rows = [{'drug_id': d, 'target_id': t, 'encoded_pKd': 5.0} for d in drugs for t in targets]
    
    s1 = generate_four_fold_isolated_splits(rows, n_splits=4, random_state=42)
    s2 = generate_four_fold_isolated_splits(rows, n_splits=4, random_state=42)
    
    for f in range(4):
        np.testing.assert_array_equal(s1[f]['train_idx'], s2[f]['train_idx'])
        np.testing.assert_array_equal(s1[f]['val_dual_cold_idx'], s2[f]['val_dual_cold_idx'])
