"""Tests for DTI inference runtime performance optimizations (norm caching, O(1) feature lookup)."""
import numpy as np
import pytest
from dti_inference_runtime import DTIInferenceRuntime


def test_precomputed_target_norms_equal_runtime_norms():
    runtime = DTIInferenceRuntime()
    runtime.load()
    
    assert hasattr(runtime, "_train_target_norms")
    assert runtime._train_target_norms is not None
    assert runtime._train_target_feats is not None
    assert len(runtime._train_target_norms) == len(runtime._train_target_feats)
    
    expected = np.linalg.norm(runtime._train_target_feats, axis=1)
    np.testing.assert_allclose(runtime._train_target_norms, expected, rtol=1e-5, atol=1e-7)


def test_domain_diagnosis_consistency():
    runtime = DTIInferenceRuntime()
    runtime.load()

    # Known training drug & target
    drug_id = list(runtime.drugs.keys())[0]
    target_id = list(runtime.targets.keys())[0]
    drug_smiles = runtime.drugs[drug_id]["smiles"]
    target_seq = runtime.targets[target_id]["sequence"]

    domain, max_d_sim, max_t_sim = runtime.diagnose_domain(drug_smiles, target_seq)
    assert domain in ["train_block", "strict_dual_cold_test", "cold_target_test", "cold_drug_test"]
    assert 0.0 <= max_d_sim <= 1.0
    assert 0.0 <= max_t_sim <= 1.0
