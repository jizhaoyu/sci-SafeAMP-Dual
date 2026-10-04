# Protocol Amendment 01: Adoption of CD-HIT Greedy Incremental Clustering for Non-Redundant Partitioning

**Amendment ID**: PROTOCOL-AMD-01  
**Date**: 2026-09-29  
**Target Protocol**: `docs/research_protocol.md` (Section: Partition and feasibility gates)  
**Status**: Historical exploratory method; superseded by `protocol-amd-02` for formal all-member isolation.  

---

## 1. Rationale & Scientific Problem
In the initial protocol draft, sequence homology grouping used undirected connected components (transitive closure):
$$\forall (u, v) \in E \iff \text{Identity}(u, v) \ge 0.40$$
Under this formulation, any path $s_1 - s_2 - \dots - s_k$ forced all sequences along the path into a single equivalence class. Because antimicrobial peptides strongly share cationic (K, R) and hydrophobic (L, A, I) motifs, and because the sequence identity denominator used $\min(L_1, L_2)$, short peptides acted as universal bridging hubs. Topological audit revealed that on 417 pilot sequences, network density reached 25.93%, with top hub degree 313 (75.2%), collapsing 100% of sequences into a single component.

Transitive connected components are recognized in the bioinformatics literature as inappropriate for peptide family de-redundancy because they trigger the "transitive chaining effect" (Li & Godzik, *Bioinformatics* 2006).

---

## 2. Specification of the Amended Partitioning Procedure
To study representative-based de-redundancy without the connected-component collapse, this historical amendment used a **CD-HIT-style greedy incremental clustering rule**:

1. **Deterministic Ordering**:
   Sequences are sorted in descending order of length, with lexicographical string comparison as the secondary tie-breaker:
   $$(L(s_i) > L(s_j)) \lor (L(s_i) == L(s_j) \land s_i < s_j)$$

2. **Representative Center Initialization**:
   The first (longest) sequence forms the representative center of cluster 1: $R_1 = s_1$.

3. **Incremental Membership Assignment**:
   Each subsequent sequence $s_i$ is compared against all existing cluster representatives $R_1, \dots, R_k$:
   - **Length Ratio Constraint**: Comparison requires $L(s_i) / L(R_j) \ge 0.50$ (CD-HIT parameter `-s 0.50`), preventing short non-homologous fragments from capturing long multi-domain peptides.
   - **Identity Evaluation**:
     $$\text{Identity}(s_i, R_j) = \frac{\text{Matches}(s_i, R_j)}{\min(L(s_i), L(R_j))}$$
     using canonical global Needleman-Wunsch (+2 match, -1 mismatch, -2 gap).
   - If $\text{Identity}(s_i, R_j) \ge 0.40$, $s_i$ is assigned to cluster $C_j$. **Crucially, subordinate members cannot act as bridges to recruit other sequences**.
   - If no representative satisfies the criterion, $s_i$ forms a new representative $R_{k+1} = s_i$.

4. **Multi-Fold Stratification**:
   The resulting $K$ representative clusters ($K \ge 6$) were proposed as units for 5-fold cross-validation and internal holdout assignment. This only constrains comparisons with representatives; it does not prove all-member separation between partitions.

---

## 3. Empirical Verification
On the 417-sequence DBAASP pilot dataset:
- Connected components (pre-amendment): 1 giant cluster containing 417 sequences (100.0%).
- Greedy representative clustering (historical exploratory output): **60 representative clusters**, largest cluster containing 36 sequences (8.63%). This count is not evidence of zero cross-partition similarity among all members.
- Unit test verification: passed in `02_code/tests/test_cdhit_cluster.py`.
