"""Thermodynamic Physics Engine and MM-GBSA Delta-Learning Module.

Computes binding free energy from first-principles biophysics:
  Delta_G_bind = Delta_E_MM (vdw + elec) + Delta_G_solv (GB polar + SA non-polar) - T*Delta_S
Calibrates statistical deep-learning predictions against physical thermodynamics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Dict, List, Optional, Tuple
import numpy as np

from fetch_kinase_pocket_3d import (
    Pocket3DModel,
    Ligand3DModel,
    VDW_RADII,
    PARTIAL_CHARGES,
    model_kinase_pocket_3d,
    generate_ligand_3d_coordinates
)
from equivariant_pocket_matcher import align_ligand_to_pocket

# Conversion constant: 1 pKd unit ~ 1.363 kcal/mol at 298.15 K
KCAL_PER_PKD = 1.363


@dataclass
class MMGBSAResult:
    """Decomposed thermodynamic binding free energy components."""
    delta_g_bind: float             # Total binding free energy (kcal/mol), negative = spontaneous binding
    delta_e_vdw: float              # Van der Waals interaction energy (kcal/mol)
    delta_e_elec: float             # Electrostatic Coulomb energy (kcal/mol)
    delta_g_gb: float               # Polar Generalized Born desolvation energy (kcal/mol)
    delta_g_sa: float               # Non-polar hydrophobic surface desolvation energy (kcal/mol)
    minus_t_delta_s: float          # Conformational entropy loss penalty (kcal/mol)
    predicted_pkd: float            # Physically estimated pKd (-delta_g_bind / 1.363)
    physics_descriptors: np.ndarray # (8,) Vector of physical observables for delta learning


def count_rotatable_bonds(ligand: Ligand3DModel) -> int:
    """
    Count rotatable acyclic single bonds for conformational entropy estimation.
    Excludes terminal bonds (e.g. -CH3, -OH) and bonds within rings (aromatic or aliphatic).
    """
    n_atoms = len(ligand.atoms)
    if n_atoms < 3:
        return 0

    adj = {i: [] for i in range(n_atoms)}
    for u, v, _ in ligand.bonds:
        adj[u].append(v)
        adj[v].append(u)

    def is_in_ring(u: int, v: int) -> bool:
        # Check if there is an alternate path between u and v
        visited = {u}
        queue = [nbr for nbr in adj[u] if nbr != v]
        while queue:
            curr = queue.pop(0)
            if curr == v:
                return True
            visited.add(curr)
            for nbr in adj[curr]:
                if nbr not in visited and nbr not in queue:
                    queue.append(nbr)
        return False

    degree = [len(adj[i]) for i in range(n_atoms)]
    rot_bonds = 0
    for u, v, b_type in ligand.bonds:
        # Only single bonds bound to non-terminal heavy atoms
        if b_type == 1:
            if degree[u] > 1 and degree[v] > 1:
                # Exclude bonds in rings (both aromatic and aliphatic like piperazine/morpholine)
                if not is_in_ring(u, v):
                    rot_bonds += 1

    return max(0, rot_bonds)


def compute_mmgbsa_binding_free_energy(
    pocket: Pocket3DModel,
    ligand: Ligand3DModel,
    docked_coords: Optional[np.ndarray] = None,
    epsilon_in: float = 4.0,
    epsilon_solv: float = 78.5,
    gamma_sa: float = 0.0072
) -> MMGBSAResult:
    """
    Compute rigorous MM-GBSA binding free energy decomposition.
    """
    if docked_coords is None:
        coords_lig = align_ligand_to_pocket(pocket, ligand)
    else:
        coords_lig = docked_coords

    n_poc = len(pocket.coords)
    m_lig = len(coords_lig)

    if n_poc == 0 or m_lig == 0:
        return MMGBSAResult(
            delta_g_bind=0.0,
            delta_e_vdw=0.0,
            delta_e_elec=0.0,
            delta_g_gb=0.0,
            delta_g_sa=0.0,
            minus_t_delta_s=0.0,
            predicted_pkd=0.0,
            physics_descriptors=np.zeros(8, dtype=np.float32)
        )

    # 1. Pairwise inter-molecular distances (N, M)
    diff = pocket.coords[:, np.newaxis, :] - coords_lig[np.newaxis, :, :]
    dist = np.linalg.norm(diff, axis=-1)  # (N, M)

    # 2. Van der Waals radii and charges
    def get_clean_vdw(elem: str) -> float:
        cleaned = re.sub(r'[^A-Za-z]', '', elem).capitalize()
        return VDW_RADII.get(cleaned, 1.70)

    def get_clean_chg(elem: str) -> float:
        cleaned = re.sub(r'[^A-Za-z]', '', elem).capitalize()
        return PARTIAL_CHARGES.get(cleaned, 0.0)

    p_radii = np.array([a.vdw_radius for a in pocket.atoms], dtype=np.float32)[:, np.newaxis]
    p_chg = np.array([a.partial_charge for a in pocket.atoms], dtype=np.float32)[:, np.newaxis]

    l_radii = np.array([get_clean_vdw(elem) for elem, _ in ligand.atoms], dtype=np.float32)[np.newaxis, :]
    l_chg = np.array([get_clean_chg(elem) for elem, _ in ligand.atoms], dtype=np.float32)[np.newaxis, :]

    r_vdw = p_radii + l_radii  # (N, M)

    # 3. Delta E_MM: Van der Waals (Lennard-Jones 6-12 capped)
    eps = 0.15
    ratio = r_vdw / (dist + 0.85)
    e_vdw_matrix = 4.0 * eps * (ratio ** 12 - ratio ** 6)
    # Clip repulsive collisions to 20 kcal/mol per pair to represent soft relaxation
    e_vdw_matrix = np.clip(e_vdw_matrix, -2.5, 20.0)
    delta_e_vdw = float(np.sum(e_vdw_matrix))

    # 4. Delta E_MM: Coulombic Electrostatics
    # Conversion: 332.0637 kcal*A / (mol*e^2) in dielectric medium epsilon_in
    coulomb_const = 332.0637 / epsilon_in
    e_elec_matrix = (coulomb_const * p_chg * l_chg) / (dist + 1.0)
    delta_e_elec = float(np.sum(e_elec_matrix))

    # 5. Delta G_GB: Polar Solvation via Still Generalized Born Model
    # Effective Born radii
    alpha_p = p_radii * 1.3
    alpha_l = l_radii * 1.3
    alpha_prod = alpha_p * alpha_l
    f_gb = np.sqrt(dist ** 2 + alpha_prod * np.exp(-0.25 * (dist ** 2) / (alpha_prod + 1e-4)))
    gb_factor = -0.5 * (1.0 / epsilon_in - 1.0 / epsilon_solv) * 332.0637
    # Desolvation cost of bringing opposite partial charges out of water
    delta_g_gb = float(np.sum(gb_factor * (p_chg * l_chg) / f_gb))

    # 6. Delta G_SA: Non-polar Hydrophobic Desolvation (Buried SASA)
    # Contact area per atom within 4.5 A
    contact_counts = np.sum(dist <= 4.5, axis=0)  # (M,)
    # An exposed carbon has ~ 30 A^2 SASA; each close contact buries ~ 12 A^2
    buried_sasa = np.sum(np.minimum(30.0, contact_counts * 12.0))
    # Hydrophobic burial provides favorable binding energy (-gamma * SASA)
    delta_g_sa = float(-gamma_sa * buried_sasa)

    # 7. -T * Delta S: Conformational Entropy Penalty
    # Base translational/rotational penalty: 2.8 kcal/mol
    # Rotatable bond freezing penalty: ~ 0.35 kcal/mol per rotatable bond
    n_rot = count_rotatable_bonds(ligand)
    minus_t_delta_s = float(2.8 + n_rot * 0.35)

    # 8. Total Binding Free Energy Delta G_bind
    delta_g_bind = float(delta_e_vdw + delta_e_elec + delta_g_gb + delta_g_sa + minus_t_delta_s)

    # 9. Predicted pKd = -Delta G / 1.363, bounded in physically reasonable range [2.0, 14.0]
    predicted_pkd = float(np.clip(-delta_g_bind / KCAL_PER_PKD, 2.0, 14.0))

    # 10. Construct 8-dimensional Physical Descriptors Vector
    physics_descriptors = np.array([
        delta_g_bind,
        delta_e_vdw,
        delta_e_elec,
        delta_g_gb,
        delta_g_sa,
        minus_t_delta_s,
        float(n_rot),
        float(buried_sasa)
    ], dtype=np.float32)

    return MMGBSAResult(
        delta_g_bind=delta_g_bind,
        delta_e_vdw=delta_e_vdw,
        delta_e_elec=delta_e_elec,
        delta_g_gb=delta_g_gb,
        delta_g_sa=delta_g_sa,
        minus_t_delta_s=minus_t_delta_s,
        predicted_pkd=predicted_pkd,
        physics_descriptors=physics_descriptors
    )


def predict_physical_affinity_dti(
    sequence: str,
    smiles: str,
    dfg_conformation: str = "dfg_in"
) -> MMGBSAResult:
    """Predict physical binding free energy directly from sequence and SMILES."""
    pocket = model_kinase_pocket_3d(sequence, dfg_conformation=dfg_conformation)
    ligand = generate_ligand_3d_coordinates(smiles)
    return compute_mmgbsa_binding_free_energy(pocket, ligand)


def calibrate_with_physics(
    ml_predicted_pkd: float,
    physics_res: MMGBSAResult,
    weight_physics: float = 0.20
) -> float:
    """
    Physics Delta-learning calibration:
    Combines high-capacity statistical deep-learning predictions with
    first-principles thermodynamic constraints to prevent unphysical hallucinations.
    """
    calibrated = (1.0 - weight_physics) * ml_predicted_pkd + weight_physics * physics_res.predicted_pkd
    return float(calibrated)
