"""CD-HIT greedy incremental sequence clustering algorithm.

Implements the standard bioinformatics non-redundant partitioning strategy:
1. Sort sequences in descending order of length (with deterministic tie-breaking).
2. The longest sequence forms the representative center of the first cluster.
3. Each subsequent sequence is compared against existing cluster representatives:
   - Evaluates length difference ratio (len(s) / len(rep) >= min_length_ratio, default 0.50,
     analogous to CD-HIT -s/-aL parameter).
   - If sequence identity >= cutoff with any representative, it joins that cluster
     as a subordinate member (subordinates DO NOT act as bridges to other sequences).
   - If it has < cutoff identity with all existing representatives, it becomes
     the representative center of a new cluster.
4. Produces orthogonal clusters, completely eliminating transitive chaining collapse.
"""
from collections import Counter
from typing import Callable, Optional
import numpy as np

from feature_extractor import clean_sequence
from research_data import sequence_identity, ResearchDataError


def cdhit_cluster_sequences(
    sequences: list[str],
    cutoff: float = 0.40,
    min_length_ratio: float = 0.50,
    identity_fn: Optional[Callable[[str, str], float]] = None,
) -> tuple[np.ndarray, list[str], dict]:
    """Perform greedy incremental clustering on peptide sequences.

    Parameters
    ----------
    sequences : list[str]
        List of peptide sequences.
    cutoff : float, optional
        Identity threshold for cluster membership (default 0.40).
    min_length_ratio : float, optional
        Minimum length ratio len(query) / len(rep) required for membership (default 0.50,
        standard CD-HIT parameter to prevent short fragment hijacking). Set to 0.0 to disable.
    identity_fn : callable, optional
        Function to compute identity between two sequences.
        Defaults to `sequence_identity` from `research_data`.

    Returns
    -------
    cluster_ids : np.ndarray
        Integer cluster index for each sequence in the original input order.
    representatives : list[str]
        List of representative sequences (one per cluster).
    summary : dict
        Clustering metrics including total clusters, sizes, and largest cluster share.
    """
    if not 0 < cutoff <= 1.0:
        raise ResearchDataError(f"Identity cutoff must be in (0, 1], got {cutoff}")
    if not 0.0 <= min_length_ratio <= 1.0:
        raise ResearchDataError(f"min_length_ratio must be in [0, 1], got {min_length_ratio}")
    if identity_fn is None:
        identity_fn = sequence_identity

    n = len(sequences)
    if n == 0:
        return np.array([], dtype=int), [], {
            "n_sequences": 0,
            "n_clusters": 0,
            "largest_cluster_size": 0,
            "largest_cluster_pct": 0.0,
            "cluster_sizes": [],
        }

    # Sort indices by length descending, then lexicographically ascending for full determinism
    sorted_indices = sorted(
        range(n),
        key=lambda idx: (-len(sequences[idx]), sequences[idx]),
    )

    cluster_representatives: list[str] = []
    cluster_rep_indices: list[int] = []
    cluster_rep_counts: list[Counter] = []
    cluster_members: list[list[int]] = []

    # Map from original sequence index to cluster ID
    assigned_cluster = np.full(n, -1, dtype=int)

    for idx in sorted_indices:
        seq = sequences[idx]
        seq_len = len(seq)
        seq_count = Counter(seq)
        matched_cluster = -1

        for c_idx, rep_seq in enumerate(cluster_representatives):
            rep_len = len(rep_seq)
            if min_length_ratio > 0.0 and (seq_len / rep_len) < min_length_ratio:
                continue

            min_l = min(seq_len, rep_len)
            # 1-mer upper bound pruning
            upper_bound = sum((seq_count & cluster_rep_counts[c_idx]).values()) / min_l
            if upper_bound < cutoff:
                continue

            ident = identity_fn(seq, rep_seq)
            if ident >= cutoff:
                matched_cluster = c_idx
                break

        if matched_cluster >= 0:
            assigned_cluster[idx] = matched_cluster
            cluster_members[matched_cluster].append(idx)
        else:
            new_c_idx = len(cluster_representatives)
            assigned_cluster[idx] = new_c_idx
            cluster_representatives.append(seq)
            cluster_rep_indices.append(idx)
            cluster_rep_counts.append(seq_count)
            cluster_members.append([idx])

    cluster_sizes = [len(m) for m in cluster_members]
    largest_size = max(cluster_sizes) if cluster_sizes else 0
    largest_pct = round((largest_size / n) * 100, 2) if n > 0 else 0.0

    summary = {
        "n_sequences": n,
        "n_clusters": len(cluster_representatives),
        "cutoff": cutoff,
        "min_length_ratio": min_length_ratio,
        "largest_cluster_size": largest_size,
        "largest_cluster_pct": largest_pct,
        "cluster_sizes": cluster_sizes,
        "representatives": cluster_representatives,
        "representative_original_indices": cluster_rep_indices,
    }

    return assigned_cluster, cluster_representatives, summary
