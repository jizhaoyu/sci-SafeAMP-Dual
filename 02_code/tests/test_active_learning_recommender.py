"""Unit tests for Uncertainty-Driven Active Learning & Acquisition Recommendation Engine."""
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from active_learning_recommender import (
    compute_expected_improvement,
    evaluate_active_learning_pool,
    ActiveLearningReport
)


def test_expected_improvement_math():
    # EI should be zero or positive
    ei_low = compute_expected_improvement(mu=6.0, sigma=0.2, y_best=8.0)
    assert ei_low >= 0.0

    # Higher mu should yield higher EI for fixed sigma
    ei_mid = compute_expected_improvement(mu=8.0, sigma=0.5, y_best=8.0)
    ei_high = compute_expected_improvement(mu=9.0, sigma=0.5, y_best=8.0)
    assert ei_high > ei_mid > ei_low

    # Zero sigma edge case
    ei_zero_sig = compute_expected_improvement(mu=8.5, sigma=0.0, y_best=8.0, xi=0.1)
    assert abs(ei_zero_sig - 0.4) < 1e-5


def test_evaluate_active_learning_pool():
    seq = "MKKFFDSRREQGGSGLGSGSSGGGGSTSGLGSGYRGAR" + "A"*50 + "VAIK" + "A"*80 + "HRDL" + "A"*20 + "DFG" + "A"*100
    candidate_pool = [
        ("Gefitinib", "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1"),
        ("Imatinib", "Cc1ccc(cc1)Nc2nccc(n2)c3cccnc3NC(=O)c4ccc(cc4)CN5CCN(C)CC5"),
        ("Benzene", "c1ccccc1"),
        ("Aliphatic_Octane", "CCCCCCCC")
    ]

    report = evaluate_active_learning_pool(
        target_sequence=seq,
        candidate_pool=candidate_pool,
        target_name="EGFR_Benchmark",
        y_best=7.0
    )

    assert isinstance(report, ActiveLearningReport)
    assert report.total_evaluated == 4
    assert report.target_name == "EGFR_Benchmark"

    # All candidates must be accounted for across the 4 quadrants
    total_assigned = (
        len(report.confident_hits)
        + len(report.breakthrough_hypotheses)
        + len(report.high_information_gain_blindspots)
        + len(report.known_inactives)
    )
    assert total_assigned == 4

    # Verify Markdown export
    md = report.export_markdown()
    assert "# 主动学习定向验证与高信息增益推荐报告" in md
    assert "EGFR_Benchmark" in md
    assert "高置信度活性领头物清单" in md
    assert "高潜力突破假说清单" in md
    assert "高信息增益认知盲区清单" in md
