"""Immutable research protocol specifications, configurations, and cryptographic digests.

Defines formal protocol profiles for homology clustering, sequence identity normalization,
partition stratification, and cross-set isolation.
"""
from dataclasses import dataclass, asdict
import hashlib
import json
from typing import Literal, Optional


@dataclass(frozen=True)
class ProtocolSpec:
    protocol_id: str
    protocol_version: int
    clustering_method: Literal['transitive', 'greedy_nw']
    membership_identity: Literal['min', 'max', 'alignment']
    min_length_ratio: float
    cross_identity: Literal['min', 'max', 'alignment']
    cross_scope: Literal['all_members', 'members_to_representatives']
    cutoff: float = 0.40
    folds: int = 5
    partition_seed: int = 42
    alignment: str = 'global_nw_match2_mismatch-1_gap-2_canonical_diagonal_first'


PROTOCOLS: dict[str, ProtocolSpec] = {
    'legacy-v1': ProtocolSpec(
        protocol_id='legacy-v1',
        protocol_version=1,
        clustering_method='transitive',
        membership_identity='min',
        min_length_ratio=0.0,
        cross_identity='min',
        cross_scope='all_members',
        cutoff=0.40,
        folds=5,
        partition_seed=42,
        alignment='global_nw_match2_mismatch-1_gap-2_canonical_diagonal_first',
    ),
    'protocol-amd-01': ProtocolSpec(
        protocol_id='protocol-amd-01',
        protocol_version=2,
        clustering_method='greedy_nw',
        membership_identity='min',
        min_length_ratio=0.50,
        cross_identity='min',
        cross_scope='members_to_representatives',
        cutoff=0.40,
        folds=5,
        partition_seed=42,
        alignment='global_nw_match2_mismatch-1_gap-2_canonical_diagonal_first',
    ),
    'protocol-amd-02': ProtocolSpec(
        protocol_id='protocol-amd-02',
        protocol_version=3,
        clustering_method='transitive',
        membership_identity='alignment',
        min_length_ratio=0.0,
        cross_identity='alignment',
        cross_scope='all_members',
        cutoff=0.40,
        folds=5,
        partition_seed=42,
        alignment='global_nw_match2_mismatch-1_gap-2_canonical_diagonal_first',
    ),
}


def get_protocol(protocol_id: str) -> ProtocolSpec:
    """Retrieve frozen ProtocolSpec by identifier."""
    if protocol_id not in PROTOCOLS:
        raise KeyError(f"Unknown protocol ID: '{protocol_id}'. Available: {list(PROTOCOLS.keys())}")
    return PROTOCOLS[protocol_id]


def protocol_digest(spec: ProtocolSpec) -> str:
    """Compute deterministic SHA-256 digest of frozen protocol specification."""
    serialized = json.dumps(asdict(spec), sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(serialized).hexdigest()


def check_protocol_conflicts(spec: ProtocolSpec) -> tuple[bool, Optional[str]]:
    """Check whether a protocol contains unresolved scientific conflicts.
    
    Returns (has_conflict, conflict_reason).
    """
    if spec.protocol_id == 'legacy-v1':
        return (
            True,
            'protocol_conflict: legacy-v1 is historical and lacks the frozen alignment-column, all-member zero-leakage contract.'
        )
    if spec.protocol_id == 'protocol-amd-01':
        return (
            True,
            "protocol_conflict: cross_scope 'members_to_representatives' vs all-member zero leakage claim and min/max denominator ambiguity require formal scientific protocol sign-off."
        )
    if spec.protocol_id not in PROTOCOLS or spec != PROTOCOLS[spec.protocol_id]:
        return (True, 'protocol_conflict: protocol specification is not a registered frozen version.')
    if spec.protocol_id == 'protocol-amd-02' and not (
        spec.clustering_method == 'transitive'
        and spec.membership_identity == spec.cross_identity == 'alignment'
        and spec.cross_scope == 'all_members'
        and spec.min_length_ratio == 0.0
        and spec.cutoff == 0.40
        and spec.folds == 5
    ):
        return (True, 'protocol_conflict: strict all-member isolation settings are incomplete.')
    return (False, None)
