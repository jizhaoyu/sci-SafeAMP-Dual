"""SE(3) Equivariant Pocket-Ligand Matcher and Geometric Interaction Network.

Models 3D spatial complementarity, soft-core Lennard-Jones steric hindrance,
directional H-bonding with kinase hinge residues, and mutation-induced clash
(e.g., Gatekeeper T790M resistance).
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, List, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn

from fetch_kinase_pocket_3d import (
    Pocket3DModel,
    Ligand3DModel,
    VDW_RADII,
    PARTIAL_CHARGES,
    model_kinase_pocket_3d,
    generate_ligand_3d_coordinates
)


@dataclass
class PocketMatchResult:
    """Quantitative outputs from the SE(3) Equivariant Pocket-Ligand Matcher."""
    geom_features: np.ndarray           # (32,) Invariant geometric feature vector
    dock_score: float                   # Overall geometric complementarity score (higher = tighter binding)
    steric_clash_penalty: float         # Lennard-Jones repulsive energy (lower is better, high = steric clash)
    dispersion_energy: float            # Attractive van der Waals energy (negative, lower = stronger dispersion)
    electrostatic_energy: float         # Coulombic electrostatic interaction energy
    hinge_hbond_score: float            # Directional H-bond match with hinge donor and acceptor (0 to 1)
    gatekeeper_clash: float             # Steric hindrance specifically around gatekeeper (sensitive to T790M)
    docked_coords: np.ndarray           # (M, 3) 3D coordinates of ligand docked into canonical pocket frame


def rbf_expansion(
    distances: np.ndarray,
    num_bins: int = 16,
    d_min: float = 1.5,
    d_max: float = 8.0,
    sigma: float = 0.5
) -> np.ndarray:
    """
    Expand inter-atomic pairwise distances into Radial Basis Functions (Gaussian kernels).
    Input: distances array of any shape.
    Output: (*distances.shape, num_bins)
    """
    centers = np.linspace(d_min, d_max, num_bins, dtype=np.float32)
    diff = distances[..., np.newaxis] - centers
    return np.exp(-0.5 * (diff / sigma) ** 2).astype(np.float32)


def compute_soft_lennard_jones(
    dist: np.ndarray,
    vdw_sum: np.ndarray,
    epsilon: float = 0.15,
    delta: float = 0.85
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Soft-core 12-6 Lennard-Jones potential avoiding singularity at small distances.
    Returns (E_repulsive, E_attractive).
    """
    r_ratio = vdw_sum / (dist + delta)
    e_rep = 4.0 * epsilon * (r_ratio ** 12)
    e_att = -4.0 * epsilon * (r_ratio ** 6)
    e_rep = np.minimum(e_rep, 100.0)
    return e_rep.astype(np.float32), e_att.astype(np.float32)


def kabsch_superposition(P: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Find optimal rotation R and translation t such that Q @ R.T + t aligns with P.
    Both P and Q have shape (K, 3), where K >= 3.
    """
    if len(P) == 0 or len(Q) == 0:
        return np.eye(3, dtype=np.float32), np.zeros(3, dtype=np.float32)

    p_center = P.mean(axis=0)
    q_center = Q.mean(axis=0)

    P_c = P - p_center
    Q_c = Q - q_center

    # Covariance matrix H = Q_c^T @ P_c
    H = Q_c.T @ P_c
    U, S, Vt = np.linalg.svd(H)

    # Correct reflection if det < 0
    d = np.linalg.det(Vt.T @ U.T)
    diag = np.eye(3, dtype=np.float32)
    diag[2, 2] = np.sign(d)

    R = Vt.T @ diag @ U.T
    t = p_center - q_center @ R.T
    return R.astype(np.float32), t.astype(np.float32)


def align_ligand_to_pocket(pocket: Pocket3DModel, ligand: Ligand3DModel) -> np.ndarray:
    """
    Pharmacophore-guided rigid docking alignment into the ATP-binding cleft.
    Aligns ligand H-bond donor/acceptor pairs to hinge donor/acceptor,
    resolving orientation to minimize gatekeeper steric clash and optimize binding geometry.
    """
    coords_lig = ligand.coords.copy()
    n_lig = len(coords_lig)
    if n_lig == 0:
        return coords_lig

    # Pocket Hinge target points:
    # Atom 0: Hinge N (donor) at (0.0, 0.0, 0.0)
    # Atom 3: Hinge O (acceptor) at (2.5, -1.2, 0.5)
    # Atom 1: Hinge CA (anchor) at (1.2, 0.8, 0.0)
    target_triplet = np.vstack([pocket.coords[0], pocket.coords[3], pocket.coords[1]])

    # Heteroatoms in ligand
    hetero = [
        i for i, (elem, _) in enumerate(ligand.atoms) 
        if re.sub(r'[^A-Za-z]', '', elem).upper() in ('N', 'O', 'S', 'F', 'CL', 'BR')
    ]

    adj = {i: [] for i in range(n_lig)}
    for u, v, _ in ligand.bonds:
        adj[u].append(v)
        adj[v].append(u)

    candidates = []
    for i_idx, u in enumerate(hetero):
        for v in hetero[i_idx + 1:]:
            d = np.linalg.norm(coords_lig[u] - coords_lig[v])
            if 2.0 <= d <= 4.2:
                nbrs = list(set(adj[u] + adj[v]))
                for w in nbrs:
                    if w not in (u, v):
                        area = np.linalg.norm(np.cross(coords_lig[v] - coords_lig[u], coords_lig[w] - coords_lig[u]))
                        if area > 0.2:
                            candidates.append((u, v, w))
                            candidates.append((v, u, w))

    if not candidates:
        # Fallback: Inertia tensor alignment to canonical pocket center
        coords_c = coords_lig - coords_lig.mean(axis=0)
        cov = coords_c.T @ coords_c
        _, eigvecs = np.linalg.eigh(cov)
        if np.linalg.det(eigvecs) < 0:
            eigvecs[:, 2] *= -1.0
        
        pocket_center = pocket.coords.mean(axis=0)
        best_dock = coords_c + pocket_center
        min_clash = float('inf')

        # Test the 4 proper rotation flips
        for signs in [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]:
            R_flip = eigvecs @ np.diag(signs)
            docked_cand = coords_c @ R_flip.T + pocket_center
            diff = pocket.coords[:, np.newaxis, :] - docked_cand[np.newaxis, :, :]
            clash = np.sum(np.maximum(0.0, 2.2 - np.linalg.norm(diff, axis=-1)) ** 2)
            if clash < min_clash:
                min_clash = clash
                best_dock = docked_cand
        return best_dock.astype(np.float32)

    # Evaluate all candidate triplets deterministically
    best_dock = None
    best_score = -float('inf')

    for u, v, w in candidates:
        source_triplet = np.vstack([coords_lig[u], coords_lig[v], coords_lig[w]])
        R, t = kabsch_superposition(target_triplet, source_triplet)
        docked = coords_lig @ R.T + t

        diff = pocket.coords[:, np.newaxis, :] - docked[np.newaxis, :, :]
        dist = np.linalg.norm(diff, axis=-1)
        
        # Scoring: reward H-bond distances (~2.9 A) to hinge, penalize steric clashes
        clash = np.sum(np.maximum(0.0, 2.2 - dist) ** 2)
        hbond = float(np.exp(-0.5 * ((dist[0, u] - 2.9) / 0.5) ** 2) + np.exp(-0.5 * ((dist[3, v] - 2.9) / 0.5) ** 2))
        
        # Check Gatekeeper proximity
        gk_indices = [i for i, a in enumerate(pocket.atoms) if a.is_gatekeeper]
        gk_clash = np.sum(np.maximum(0.0, 2.4 - dist[gk_indices, :]) ** 2) if gk_indices else 0.0

        score = hbond - 0.1 * clash - 0.5 * gk_clash
        if score > best_score:
            best_score = score
            best_dock = docked

    return (best_dock if best_dock is not None else coords_lig).astype(np.float32)


def compute_equivariant_pocket_match(pocket: Pocket3DModel, ligand: Ligand3DModel) -> PocketMatchResult:
    """
    Compute SE(3)-invariant geometric and biophysical interaction features
    between 3D kinase pocket and docked ligand.
    """
    # 1. Dock ligand into pocket frame
    docked = align_ligand_to_pocket(pocket, ligand)
    m_lig = len(docked)
    n_poc = len(pocket.coords)

    if m_lig == 0 or n_poc == 0:
        return PocketMatchResult(
            geom_features=np.zeros(32, dtype=np.float32),
            dock_score=0.0,
            steric_clash_penalty=0.0,
            dispersion_energy=0.0,
            electrostatic_energy=0.0,
            hinge_hbond_score=0.0,
            gatekeeper_clash=0.0,
            docked_coords=docked
        )

    # 2. Compute pairwise distances between all pocket atoms and ligand atoms
    diff = pocket.coords[:, np.newaxis, :] - docked[np.newaxis, :, :]  # (N, M, 3)
    dist = np.linalg.norm(diff, axis=-1)  # (N, M)

    # 3. Inter-atomic VDW radii and Partial Charges (with robust element normalization)
    def clean_element(tok: str) -> str:
        s = re.sub(r'[^A-Za-z]', '', tok).capitalize()
        return s if s in VDW_RADII else 'C'

    p_vdw = np.array([a.vdw_radius for a in pocket.atoms], dtype=np.float32)[:, np.newaxis]  # (N, 1)
    p_chg = np.array([a.partial_charge for a in pocket.atoms], dtype=np.float32)[:, np.newaxis]

    l_vdw = np.array([VDW_RADII.get(clean_element(elem), 1.70) for elem, _ in ligand.atoms], dtype=np.float32)[np.newaxis, :]  # (1, M)
    l_chg = np.array([PARTIAL_CHARGES.get(clean_element(elem), 0.0) for elem, _ in ligand.atoms], dtype=np.float32)[np.newaxis, :]

    vdw_sum = p_vdw + l_vdw  # (N, M)

    # 4. Lennard-Jones soft-core energies
    e_rep, e_att = compute_soft_lennard_jones(dist, vdw_sum)
    total_e_rep = float(np.sum(e_rep))
    total_e_att = float(np.sum(e_att))

    # 5. Electrostatic Coulomb interaction (softened)
    e_coulomb = (p_chg * l_chg) / (dist + 1.2) * 14.4  # (N, M) in kcal/mol scaling
    total_elec = float(np.sum(e_coulomb))

    # 6. RBF expansion (contact pairs within 7.0 A)
    contact_mask = dist <= 7.0
    contact_dists = dist[contact_mask]
    if len(contact_dists) > 0:
        rbf_vals = rbf_expansion(contact_dists, num_bins=16)  # (P, 16)
        rbf_hist = np.sum(rbf_vals, axis=0) / (m_lig + 1e-5)  # Normalized by ligand size
    else:
        rbf_hist = np.zeros(16, dtype=np.float32)

    # 7. Directional Hinge H-bond score
    dist_donor = dist[0, :]  # Distance from Hinge N to all ligand atoms
    dist_acceptor = dist[3, :]  # Distance from Hinge O to all ligand atoms
    
    donor_hbond = np.max(np.exp(-0.5 * ((dist_donor - 2.9) / 0.4) ** 2))
    acceptor_hbond = np.max(np.exp(-0.5 * ((dist_acceptor - 2.9) / 0.4) ** 2))
    hinge_score = float(0.5 * (donor_hbond + acceptor_hbond))

    # 8. Gatekeeper Steric Clash (Index 4, 5, etc. are gatekeeper atoms)
    gk_indices = [i for i, a in enumerate(pocket.atoms) if a.is_gatekeeper]
    if gk_indices:
        gk_dist = dist[gk_indices, :]  # (G, M)
        # Steric constriction / clash threshold for gatekeeper entrance
        gk_clash = float(np.sum(np.maximum(0.0, 4.8 - gk_dist) ** 2))
        min_gk_dist = float(np.min(gk_dist))
    else:
        gk_clash = 0.0
        min_gk_dist = 5.0

    # 9. Contact Surface and Buried Fraction
    buried_fraction = float(np.mean(np.any(dist <= 4.5, axis=0)))
    catalytic_lys_dist = float(np.min(dist[pocket.catalytic_lys_idx, :])) if pocket.catalytic_lys_idx >= 0 else 5.0

    # 10. Construct 32-dimensional SE(3) Invariant Feature Vector
    geom_features = np.zeros(32, dtype=np.float32)
    geom_features[0:16] = rbf_hist

    geom_features[16] = np.log1p(total_e_rep)
    geom_features[17] = total_e_att
    geom_features[18] = total_elec
    geom_features[19] = total_e_att + total_elec - 0.5 * total_e_rep

    geom_features[20] = float(donor_hbond)
    geom_features[21] = float(acceptor_hbond)
    geom_features[22] = hinge_score
    geom_features[23] = float(np.exp(-0.5 * ((catalytic_lys_dist - 3.5) / 1.0) ** 2))

    geom_features[24] = float(np.log1p(gk_clash))
    geom_features[25] = float(min_gk_dist)
    geom_features[26] = float(np.exp(-min_gk_dist))
    geom_features[27] = float(1.0 if min_gk_dist < 4.5 else 0.0)

    geom_features[28] = buried_fraction
    geom_features[29] = float(len(contact_dists)) / (m_lig + 1e-5)
    geom_features[30] = float(np.std(docked, axis=0).mean())

    # Overall geometric complementarity dock score
    dock_score = float(
        2.5 * hinge_score 
        + 1.5 * buried_fraction 
        - 0.05 * total_e_rep 
        - 1.5 * gk_clash 
        - 0.02 * total_e_att
    )
    geom_features[31] = dock_score

    return PocketMatchResult(
        geom_features=geom_features,
        dock_score=dock_score,
        steric_clash_penalty=total_e_rep,
        dispersion_energy=total_e_att,
        electrostatic_energy=total_elec,
        hinge_hbond_score=hinge_score,
        gatekeeper_clash=gk_clash,
        docked_coords=docked
    )


def predict_pocket_match_dti(
    sequence: str,
    smiles: str,
    gatekeeper_override: Optional[str] = None,
    dfg_conformation: str = "dfg_in"
) -> PocketMatchResult:
    """End-to-end 3D pocket geometric docking and scoring from sequence and SMILES."""
    pocket = model_kinase_pocket_3d(sequence, dfg_conformation=dfg_conformation, gatekeeper_override=gatekeeper_override)
    ligand = generate_ligand_3d_coordinates(smiles)
    return compute_equivariant_pocket_match(pocket, ligand)


class EquivariantPocketMatcherNN(nn.Module):
    """
    PyTorch SE(3) Geometric Graph & Interaction Predictor.
    Maps 32-dim invariant geometric interaction descriptors to binding affinity delta.
    """
    def __init__(self, in_features: int = 32, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.SiLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.SiLU(),
            nn.Linear(hidden_dim // 2, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
