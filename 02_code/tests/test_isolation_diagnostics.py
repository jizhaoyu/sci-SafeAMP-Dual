"""Unit tests for sequence isolation diagnostics and independent NW alignment."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from feature_extractor import clean_sequence
from research_data import sequence_identity
from isolation_diagnostics import (
    independent_needleman_wunsch,
    connected_components_from_edges,
    compute_all_pair_metrics,
    can_exceed_cutoff,
    chunked_all_pairs_diagnostics,
    compute_chunked_isolation_diagnostics,
)


def test_independent_needleman_wunsch_exact_match():
    seq = "GIGAVLKVLTTGLPALISWIKRKRQQ"
    matches, al_len, al_a, al_b = independent_needleman_wunsch(seq, seq)
    assert matches == len(seq)
    assert al_len == len(seq)
    assert al_a == seq
    assert al_b == seq


def test_independent_needleman_wunsch_agreement_with_production():
    test_pairs = [
        ("GIGAVLKVLTTGLPALISWIKRKRQQ", "GIGAVLKVLTTGRPALISWIKRKRQQ"),
        ("KKLRLKIAFK", "KKAKRRLLKK"),
        ("ADADADADAD", "ADAD"),
        ("LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES", "GIGKFLHSAKKFGKAFVGEIMNS"),
    ]
    for s1, s2 in test_pairs:
        s1_c, s2_c = clean_sequence(s1), clean_sequence(s2)
        prod_id = sequence_identity(s1_c, s2_c)
        matches, _, _, _ = independent_needleman_wunsch(s1_c, s2_c)
        ref_id = matches / min(len(s1_c), len(s2_c))
        assert abs(prod_id - ref_id) < 1e-9


def test_connected_components_small_graph():
    # 0-1, 1-2 (comp 1: {0,1,2}); 3-4 (comp 2: {3,4}); 5 (comp 3: {5})
    edges = [(0, 1), (1, 2), (3, 4)]
    n_comps, comp_sizes, roots = connected_components_from_edges(6, edges)
    assert n_comps == 3
    assert comp_sizes == [3, 2, 1]
    assert roots[0] == roots[1] == roots[2]
    assert roots[3] == roots[4]
    assert roots[5] != roots[0] and roots[5] != roots[3]


def test_compute_all_pair_metrics_filter_upper_bound():
    sequences = [
        "KKLRLKIAFK",
        "KKAKRRLLKK",
        "GIGAVLKVLT",
        "WWWWWWWWWW"
    ]
    df_pairs, filter_fn = compute_all_pair_metrics(sequences)
    assert filter_fn == 0
    assert len(df_pairs) == 6
    # Any pair with 0 common residues must have 0 matches
    w_pair = df_pairs[(df_pairs['i'] == 0) & (df_pairs['j'] == 3)].iloc[0]
    assert w_pair['matches'] == 0
    assert w_pair['id_min'] == 0.0


def test_chunked_all_pairs_diagnostics_consistency():
    seqs = [
        "GIGAVLKVLTTGLPALISWIKRKRQQ",
        "GIGAVLKVLTTGRPALISWIKRKRQQ",
        "KKLRLKIAFK",
        "KKAKRRLLKK",
        "ADADADADAD",
        "ADAD",
        "LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES",
        "GIGKFLHSAKKFGKAFVGEIMNS",
        "WWWWWWWWWW",
        "RRWWRRWW",
        "FLPIVGKLLSGLL",
        "GLFDIVKKVVGALGSL",
    ]
    df_pairs, _ = compute_all_pair_metrics(seqs)
    active_edges = df_pairs[df_pairs['id_min'] >= 0.40]
    edge_list = list(zip(active_edges['i'], active_edges['j']))
    expected_n_comps, expected_comp_sizes, _ = connected_components_from_edges(len(seqs), edge_list)
    expected_edge_count = len(active_edges)
    expected_largest_comp = expected_comp_sizes[0] if expected_comp_sizes else 0

    chunked_result = compute_chunked_isolation_diagnostics(seqs, cutoff=0.40, chunk_size=3)

    assert chunked_result['edge_count'] == expected_edge_count
    assert chunked_result['n_components'] == expected_n_comps
    assert chunked_result['largest_component_size'] == expected_largest_comp
    assert chunked_result['comp_sizes'] == expected_comp_sizes
    assert chunked_result['n_nodes'] == len(seqs)

    # Also verify that chunked_all_pairs_diagnostics yields exact same edges
    collected_edges = []
    for chunk in chunked_all_pairs_diagnostics(seqs, cutoff=0.40, chunk_size=3):
        assert len(chunk) <= 3
        for edge in chunk:
            collected_edges.append((edge['i'], edge['j']))
    assert set(collected_edges) == set(edge_list)
    assert len(collected_edges) == expected_edge_count


def test_chunked_empty_and_single_sequence():
    # Empty sequence list
    res_empty = compute_chunked_isolation_diagnostics([])
    assert res_empty['n_nodes'] == 0
    assert res_empty['edge_count'] == 0
    assert res_empty['n_components'] == 0
    assert res_empty['comp_sizes'] == []
    assert res_empty['largest_component_size'] == 0
    assert res_empty['max_degree'] == 0
    assert res_empty['mean_degree'] == 0.0
    assert list(chunked_all_pairs_diagnostics([])) == []

    # Single sequence
    res_single = compute_chunked_isolation_diagnostics(["GIGAVLKVLTTGLPALISWIKRKRQQ"])
    assert res_single['n_nodes'] == 1
    assert res_single['edge_count'] == 0
    assert res_single['n_components'] == 1
    assert res_single['comp_sizes'] == [1]
    assert res_single['largest_component_size'] == 1
    assert res_single['max_degree'] == 0
    assert res_single['mean_degree'] == 0.0
    assert list(chunked_all_pairs_diagnostics(["GIGAVLKVLTTGLPALISWIKRKRQQ"])) == []


def test_can_exceed_cutoff():
    from collections import Counter
    c1 = Counter("AAAAA")
    c2 = Counter("WWWWW")
    assert can_exceed_cutoff(c1, c2, 5, 0.40) is False
    assert can_exceed_cutoff(c1, c1, 5, 0.40) is True
    assert can_exceed_cutoff(Counter(), Counter(), 0, 0.40) is False

