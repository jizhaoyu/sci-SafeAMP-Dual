"""Tests for shared preparation engine, partitioning gates, and audit artifacts."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from research_data import (
    prepare,
    prepare_frame,
    validate_partition,
    partition,
    ResearchDataError,
    REQUIRED,
)
from research_protocol_config import get_protocol
from research_utils import sha256, write_json, read_json


def create_sample_df(n_dev=30, n_ext=6, cluster_per_sample=True):
    # Generates a valid test DataFrame with distinct sequences
    rows = []
    # 20 distinct residues pool
    chars = "ACDEFGHIKLMNPQRSTVWY"
    for i in range(n_dev):
        seq = chars[i % len(chars)] * 15 + chars[(i + 1) % len(chars)] * 5
        rows.append({
            "sample_id": f"s_dev_{i}",
            "seq": seq,
            "amp": float(i % 2),
            "hemo": float((i // 2) % 2),
            "source_role": "development",
            "source_dataset": "TestDBAASP",
            "cluster_id": i if cluster_per_sample else (i % 2),
            "representative_sample_id": f"s_dev_{i}",
        })
    for i in range(n_ext):
        seq = "M" * 10 + chars[i % len(chars)] * 10
        rows.append({
            "sample_id": f"s_ext_{i}",
            "seq": seq,
            "amp": float(i % 2),
            "hemo": float((i // 2) % 2),
            "source_role": "external",
            "source_dataset": "TestExtDB",
            "cluster_id": 100 + i,
            "representative_sample_id": f"s_ext_{i}",
        })
    return pd.DataFrame(rows)


def test_development_clusters_under_six_blocks_even_if_total_clusters_over_six():
    # Scenario: Combined clusters >= 6, but development has < 6
    df = create_sample_df(n_dev=10, n_ext=10, cluster_per_sample=False)
    # dev only has 2 clusters (0 and 1)
    assert df[df.source_role == "development"].cluster_id.nunique() < 6
    with pytest.raises(ResearchDataError, match="Insufficient independent homology groups"):
        partition(df, folds=5)


def test_missing_class_in_validation_fold_blocks():
    # If a task is single-class in any validation fold, require_classes must block
    df = create_sample_df(n_dev=12, n_ext=2, cluster_per_sample=True)
    # Set all hemo in development to 1.0 (single class)
    df.loc[df.source_role == "development", "hemo"] = 1.0
    with pytest.raises(ResearchDataError, match="both measured classes required for hemo"):
        partition(df, folds=5)


def test_only_external_supplies_amp_negative_blocks():
    # Development has only AMP=1, external has AMP=0
    df = create_sample_df(n_dev=20, n_ext=4, cluster_per_sample=True)
    df.loc[df.source_role == "development", "amp"] = 1.0
    with pytest.raises(ResearchDataError, match="both measured classes required for amp"):
        partition(df, folds=5)


def test_identical_input_writes_deterministic_partitions(tmp_path):
    # Running partition on identical dataframe yields identical split and fold assignments
    df1 = create_sample_df(n_dev=30, n_ext=6, cluster_per_sample=True)
    df2 = create_sample_df(n_dev=30, n_ext=6, cluster_per_sample=True)
    p1 = partition(df1, folds=5, seed=42)
    p2 = partition(df2, folds=5, seed=42)
    pd.testing.assert_frame_equal(p1[["sample_id", "split", "fold"]], p2[["sample_id", "split", "fold"]])


def test_existing_directory_is_rejected_before_writing(tmp_path):
    out = tmp_path / "already_exists"
    out.mkdir()
    fake_csv = tmp_path / "fake.csv"
    fake_csv.write_text("dummy")
    with pytest.raises(ResearchDataError, match="Output exists"):
        prepare(fake_csv, out)
