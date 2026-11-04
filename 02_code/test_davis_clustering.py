"""Compute drug clusters and kinase homology clusters for DAVIS."""
import json
import time
import numpy as np
import pandas as pd
import numba
from collections import defaultdict

# 1. Load data
df = pd.read_csv('03_experiments/audits/dti_davis_acquisition_20261006_v2/davis.csv')
drugs_dict = dict(zip(df['ID1'], df['X1']))
targets_dict = dict(zip(df['ID2'], df['X2']))

drug_ids = sorted(drugs_dict.keys())
target_ids = sorted(targets_dict.keys())

print(f"Loaded {len(drug_ids)} unique drugs and {len(target_ids)} unique targets.")

# 2. Molecular similarity
from test_molecular_similarity import get_morgan_fingerprint, tanimoto

fps = {d_id: get_morgan_fingerprint(drugs_dict[d_id]) for d_id in drug_ids}
drug_sim_matrix = np.zeros((len(drug_ids), len(drug_ids)), dtype=np.float32)
for i in range(len(drug_ids)):
    drug_sim_matrix[i, i] = 1.0
    for j in range(i + 1, len(drug_ids)):
        s = tanimoto(fps[drug_ids[i]], fps[drug_ids[j]])
        drug_sim_matrix[i, j] = s
        drug_sim_matrix[j, i] = s

# Connected components for drugs at cutoff 0.40
def get_connected_components(adj_matrix, cutoff):
    n = len(adj_matrix)
    visited = [False] * n
    components = []
    for i in range(n):
        if not visited[i]:
            comp = []
            queue = [i]
            visited[i] = True
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for nbr in range(n):
                    if not visited[nbr] and adj_matrix[curr, nbr] >= cutoff:
                        visited[nbr] = True
                        queue.append(nbr)
            components.append(comp)
    return components

drug_comps_40 = get_connected_components(drug_sim_matrix, 0.40)
print(f"\n--- Drug Clustering (Tanimoto cutoff 0.40) ---")
print(f"Total drug clusters: {len(drug_comps_40)} for {len(drug_ids)} drugs")
print(f"Cluster sizes: {[len(c) for c in sorted(drug_comps_40, key=len, reverse=True)[:10]]}")

# 3. Kinase sequence alignment using Numba
aa_map = {aa: i+1 for i, aa in enumerate('ACDEFGHIKLMNPQRSTVWY')}
encoded_seqs = [np.array([aa_map.get(c, 0) for c in targets_dict[t_id]], dtype=np.int32) for t_id in target_ids]

@numba.njit(parallel=True)
def compute_all_nw_identities(encoded_list, n_targets):
    mat = np.zeros((n_targets, n_targets), dtype=np.float32)
    # diagonal is 1.0
    for i in range(n_targets):
        mat[i, i] = 1.0
        
    for i in numba.prange(n_targets):
        seq1 = encoded_list[i]
        n = len(seq1)
        for j in range(i + 1, n_targets):
            seq2 = encoded_list[j]
            m = len(seq2)
            
            # Global Needleman-Wunsch
            # Score matrix
            score = np.zeros((n + 1, m + 1), dtype=np.int32)
            for ii in range(1, n + 1):
                score[ii, 0] = -2 * ii
            for jj in range(1, m + 1):
                score[0, jj] = -2 * jj
                
            for ii in range(1, n + 1):
                c1 = seq1[ii - 1]
                for jj in range(1, m + 1):
                    c2 = seq2[jj - 1]
                    m_score = 2 if c1 == c2 else -1
                    diag = score[ii - 1, jj - 1] + m_score
                    up = score[ii - 1, jj] - 2
                    left = score[ii, jj - 1] - 2
                    val = diag
                    if up > val:
                        val = up
                    if left > val:
                        val = left
                    score[ii, jj] = val
                    
            # Traceback
            ii = n
            jj = m
            matches = 0
            al_len = 0
            while ii > 0 or jj > 0:
                al_len += 1
                c1 = seq1[ii - 1] if ii > 0 else 0
                c2 = seq2[jj - 1] if jj > 0 else 0
                m_score = 2 if c1 == c2 else -1
                
                if ii > 0 and jj > 0 and score[ii, jj] == score[ii - 1, jj - 1] + m_score:
                    if c1 == c2:
                        matches += 1
                    ii -= 1
                    jj -= 1
                elif ii > 0 and score[ii, jj] == score[ii - 1, jj] - 2:
                    ii -= 1
                else:
                    jj -= 1
                    
            ident = matches / al_len if al_len > 0 else 0.0
            mat[i, j] = ident
            mat[j, i] = ident
            
    return mat

print("\nComputing pairwise Needleman-Wunsch identities across all 379 kinases (71,631 pairs)...")
t0 = time.time()
target_sim_matrix = compute_all_nw_identities(encoded_seqs, len(target_ids))
dt = time.time() - t0
print(f"Completed in {dt:.2f} seconds.")

target_comps_40 = get_connected_components(target_sim_matrix, 0.40)
print(f"\n--- Kinase Homology Clustering (NW Sequence Identity cutoff 0.40) ---")
print(f"Total kinase clusters: {len(target_comps_40)} for {len(target_ids)} targets")
print(f"Top 10 cluster sizes: {[len(c) for c in sorted(target_comps_40, key=len, reverse=True)[:10]]}")

# Save matrices for downstream audit
np.save('03_experiments/audits/dti_davis_acquisition_20261006_v2/drug_sim_matrix.npy', drug_sim_matrix)
np.save('03_experiments/audits/dti_davis_acquisition_20261006_v2/target_sim_matrix.npy', target_sim_matrix)
print("Saved similarity matrices.")
