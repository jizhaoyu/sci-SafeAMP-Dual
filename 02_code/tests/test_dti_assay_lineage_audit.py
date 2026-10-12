import pytest
from dti_assay_lineage_audit import audit_assay_lineage, determine_project_exit, run_full_lineage_audit


def test_assay_lineage_categorization():
    raw_assays = [
        {'compound': 'Imatinib', 'gene': 'ABL1', 'mutation': '', 'kd': 10.0},
        {'compound': 'Imatinib', 'gene': 'ABL1', 'mutation': 'T315I', 'kd': 5000.0},
        {'compound': 'Gefitinib', 'gene': 'EGFR', 'mutation': 'unspecified', 'kd': 2.0},
    ]
    
    audit_res = audit_assay_lineage(raw_assays)
    assert 'manifest' in audit_res
    assert audit_res['total_records'] == 3
    assert audit_res['closed_exact'] >= 1
    assert audit_res['incomplete_identity'] >= 1


def test_determine_project_exit_a():
    internal_summary = {
        'HGBContinuousBaseline': {'mean_dual_cold_p10': 0.1019},
        'LogRegCandidateClassifier': {'mean_dual_cold_p10': 0.1038},
        'constant_expectation': {'mean_dual_cold_p10': 0.0682},
        'cold_drug_p10': 0.30
    }
    
    exit_type, explanation = determine_project_exit(internal_summary)
    assert exit_type == 'EXIT_A'
    assert '受限' in explanation or 'Cold-drug' in explanation


def test_determine_project_exit_b():
    # T4 Bilinear performance scenario (P@10 >= 0.15, breakthrough)
    internal_summary = {
        'HGBContinuousBaseline': {'mean_dual_cold_p10': 0.1019},
        'LogRegCandidateClassifier': {'mean_dual_cold_p10': 0.1038},
        'BilinearInteractionDTI': {'mean_dual_cold_p10': 0.1615},
        'constant_expectation': {'mean_dual_cold_p10': 0.0682},
        'cold_drug_p10': 0.2885
    }
    
    exit_type, explanation = determine_project_exit(internal_summary)
    assert exit_type == 'EXIT_B'
    assert '突破达成' in explanation or 'BilinearInteractionDTI' in explanation


def test_full_lineage_audit_execution():
    stats = run_full_lineage_audit()
    assert stats['total_pairs'] == 15704
    assert stats['closed_wildtype'] == 14664
    assert stats['closed_mutant'] == 988
    assert stats['restricted_alias'] == 52
