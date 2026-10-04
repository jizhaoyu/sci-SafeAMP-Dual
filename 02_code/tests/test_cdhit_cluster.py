"""Unit tests for CD-HIT greedy incremental clustering."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cdhit_cluster import cdhit_cluster_sequences
from feature_extractor import clean_sequence
from research_data import sequence_identity


def test_cdhit_empty_and_single():
    cluster_ids, reps, summary = cdhit_cluster_sequences([])
    assert len(cluster_ids) == 0
    assert summary["n_clusters"] == 0

    cluster_ids, reps, summary = cdhit_cluster_sequences(["GIGAVLKVLTTGLPALISWIKRKRQQ"])
    assert len(cluster_ids) == 1
    assert cluster_ids[0] == 0
    assert reps == ["GIGAVLKVLTTGLPALISWIKRKRQQ"]
    assert summary["n_clusters"] == 1


def test_cdhit_identical_sequences():
    seq = "GIGAVLKVLTTGLPALISWIKRKRQQ"
    cluster_ids, reps, summary = cdhit_cluster_sequences([seq, seq, seq])
    assert len(cluster_ids) == 3
    assert all(cid == 0 for cid in cluster_ids)
    assert len(reps) == 1
    assert summary["n_clusters"] == 1
    assert summary["largest_cluster_size"] == 3


def test_cdhit_orthogonal_sequences():
    seqs = [
        "WWWWWWWWWWWWWWWWWWWW",
        "CCCCCCCCCCCCCCCCCCCC",
        "KKKKKKKKKKKKKKKKKKKK",
        "DDDDDDDDDDDDDDDDDDDD",
    ]
    cluster_ids, reps, summary = cdhit_cluster_sequences(seqs, cutoff=0.40)
    assert summary["n_clusters"] == 4
    assert len(set(cluster_ids)) == 4
    assert summary["largest_cluster_size"] == 1


def test_cdhit_non_transitive_isolation():
    seq_a = "AAAAAAAAAAAAAAAAAAAA"
    seq_d = "DDDDDDDDDDDDDDDDDDDD"
    cluster_ids, reps, summary = cdhit_cluster_sequences([seq_a, seq_d], cutoff=0.40)
    assert summary["n_clusters"] == 2


def test_cdhit_on_dbaasp_pilot():
    records_path = Path(__file__).resolve().parents[1] / "data/sources/dbaasp_v1/records.csv"
    if not records_path.exists():
        pytest.skip("dbaasp_v1 records.csv not present")

    df = pd.read_csv(records_path)
    seqs = df["seq"].dropna().unique().tolist()
    assert len(seqs) == 417

    # With standard CD-HIT length ratio 0.50
    cluster_ids, reps, summary = cdhit_cluster_sequences(seqs, cutoff=0.40, min_length_ratio=0.50)

    # Verifies that CD-HIT successfully generates dozens of balanced orthogonal clusters
    assert summary["n_clusters"] >= 40, f"Expected >= 40 clusters, got {summary['n_clusters']}"
    assert summary["largest_cluster_pct"] < 25.0, f"Largest cluster too dominant: {summary['largest_cluster_pct']}%"
    print(f"\n[Test CD-HIT on 417 seqs] Formed {summary['n_clusters']} clusters. "
          f"Largest cluster: {summary['largest_cluster_size']} ({summary['largest_cluster_pct']}%)")
