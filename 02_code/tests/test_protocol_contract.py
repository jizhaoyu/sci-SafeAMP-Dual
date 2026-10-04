"""Tests for research protocol contract, identity modes, and deterministic clustering."""
import pytest
import pandas as pd
from dataclasses import replace
from research_data import sequence_identity, sequence_length_ratio, assert_cross_isolation, homology_components, validate_partition, ResearchDataError
from cdhit_cluster import cdhit_cluster_sequences
from research_protocol_config import get_protocol, protocol_digest, check_protocol_conflicts, PROTOCOLS


def test_identity_modes_have_distinct_meaning():
    short, long = 'A' * 10, 'A' * 25
    assert sequence_identity(short, long) == pytest.approx(1.0)
    assert sequence_identity(short, long, identity_mode='max') == pytest.approx(0.4)
    assert sequence_identity(long, short, identity_mode='max') == pytest.approx(0.4)


def test_equal_length_representatives_use_ascending_sequence_order():
    sequences = ['W' * 10, 'C' * 10, 'A' * 10]
    _, representatives, _ = cdhit_cluster_sequences(sequences, cutoff=0.4)
    assert representatives == ['A' * 10, 'C' * 10, 'W' * 10]


def test_protocol_specs_frozen_and_digest():
    legacy = get_protocol('legacy-v1')
    assert legacy.protocol_version == 1
    assert legacy.clustering_method == 'transitive'
    d1 = protocol_digest(legacy)
    d2 = protocol_digest(legacy)
    assert d1 == d2
    assert len(d1) == 64
    assert d1 == 'c9bb5d9a1552bc6dc6ec3b26ebfe35ff4687b78906129c4529413e03f5e5dd2e'
    assert protocol_digest(get_protocol('protocol-amd-01')) == 'f20bec998789e304b391f2390ddc1ef44360569c4255c0819ab1f6ae13bdc459'

    with pytest.raises(KeyError):
        get_protocol('non_existent_protocol')


def test_protocol_amd_01_conflict_flagged():
    assert check_protocol_conflicts(get_protocol('legacy-v1'))[0]
    amd = get_protocol('protocol-amd-01')
    has_conflict, reason = check_protocol_conflicts(amd)
    assert has_conflict is True
    assert 'protocol_conflict' in reason


def test_strict_protocol_is_frozen_and_uses_all_members():
    spec = get_protocol('protocol-amd-02')
    assert check_protocol_conflicts(spec) == (False, None)
    assert spec.membership_identity == spec.cross_identity == 'alignment'
    assert spec.cross_scope == 'all_members'
    assert spec.cutoff == 0.40 and spec.folds == 5
    assert check_protocol_conflicts(replace(spec, cross_scope='members_to_representatives'))[0]


def test_alignment_identity_counts_gap_columns():
    assert sequence_identity('ACA', 'CAC', identity_mode='alignment') == pytest.approx(0.5)
    assert sequence_identity('ACA', 'CAC', identity_mode='max') == pytest.approx(2 / 3)
    assert sequence_identity('A' * 10, 'A' * 25, identity_mode='alignment') == pytest.approx(0.4)
    assert sequence_identity('ACA', 'ACA', identity_mode='alignment') == 1.0


def test_short_bridge_is_kept_inside_one_component():
    sequences = ['A' * 10, 'A' * 6 + 'C' * 4, 'C' * 10]
    groups, summary = homology_components(sequences, 0.40, identity_mode='alignment')
    assert len(set(groups)) == 1
    assert summary['above_cutoff_pairs'] == 2


def test_nonrepresentative_cross_partition_pair_is_caught():
    left = pd.DataFrame([{'sample_id': 'left_rep', 'representative_sample_id': 'left_rep', 'seq': 'K' * 10 + 'A' * 10}])
    right = pd.DataFrame([
        {'sample_id': 'right_rep', 'representative_sample_id': 'right_rep', 'seq': 'L' * 10 + 'M' * 10},
        {'sample_id': 'right_member', 'representative_sample_id': 'right_rep', 'seq': 'K' * 10 + 'L' * 10},
    ])
    assert_cross_isolation(left, right, protocol='protocol-amd-01')
    with pytest.raises(ResearchDataError, match='left_rep / right_member'):
        assert_cross_isolation(left, right, protocol='protocol-amd-02')


@pytest.mark.parametrize('leak_location', ['fold', 'external'])
def test_strict_partition_rejects_cross_fold_or_external_pair(leak_location):
    letters = list('ACDEFGHIKLMNPQ')
    rows = []
    for fold in range(5):
        for label in (0, 1):
            index = 2 * fold + label
            rows.append({
                'sample_id': f'dev_{index}', 'seq': letters[index] * 10,
                'amp': label, 'hemo': label, 'source_role': 'development',
                'split': 'development', 'fold': fold, 'cluster_id': index,
            })
    for split, start in (('test', 10), ('external', 12)):
        for label in (0, 1):
            index = start + label
            rows.append({
                'sample_id': f'{split}_{label}', 'seq': letters[index] * 10,
                'amp': label, 'hemo': label,
                'source_role': 'external' if split == 'external' else 'development',
                'split': split, 'fold': -1, 'cluster_id': index,
            })
    frame = pd.DataFrame(rows)
    if leak_location == 'fold':
        frame.loc[frame.sample_id.eq('dev_2'), 'seq'] = 'A' * 9 + 'C'
    else:
        frame.loc[frame.sample_id.eq('external_0'), 'seq'] = 'A' * 9 + 'C'
    with pytest.raises(ResearchDataError, match='Cross-partition sequence similarity'):
        validate_partition(frame, protocol='protocol-amd-02')


def test_symmetric_length_ratio():
    assert sequence_length_ratio('A' * 10, 'A' * 20) == pytest.approx(0.50)
    assert sequence_length_ratio('A' * 20, 'A' * 10) == pytest.approx(0.50)
    assert sequence_length_ratio('A' * 5, 'A' * 20) == pytest.approx(0.25)
    with pytest.raises(ResearchDataError):
        sequence_length_ratio('', 'A' * 10)


def test_cutoff_boundary_exactly_point_four_is_violation():
    # If identity is exactly 0.40, it must be flagged as a violation
    # 'A'*10 and 'A'*25 with max identity has matches=10, max=25 -> exactly 0.40!
    left = pd.DataFrame([{'sample_id': 's1', 'seq': 'A' * 10}])
    right = pd.DataFrame([{'sample_id': 's2', 'seq': 'A' * 25}])
    with pytest.raises(ResearchDataError):
        assert_cross_isolation(left, right, cutoff=0.40)


def test_greedy_does_not_equal_all_member_isolation():
    # Demonstrating non-transitive A-B-C chain:
    # A is rep, B is recruited by A.
    # C is not similar to A, so forms new cluster.
    # But B and C might be similar!
    # A = A*10 + B*10 (20)
    # B = B*10 + C*10 (20)
    # C = C*10 + D*10 (20)
    seqA = 'K' * 10 + 'A' * 10
    seqB = 'L' * 10 + 'A' * 10
    seqC = 'L' * 10 + 'M' * 10
    # seqA and seqB share 'A'*10 -> 10/20 = 0.50 >= 0.40
    # seqB and seqC share 'L'*10 -> 10/20 = 0.50 >= 0.40
    # seqA and seqC share nothing -> 0.0 < 0.40
    assert sequence_identity(seqA, seqB) >= 0.40
    assert sequence_identity(seqB, seqC) >= 0.40
    assert sequence_identity(seqA, seqC) < 0.40
