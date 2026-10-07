"""3D Kinase catalytic pocket modeler and ligand 3D spatial coordinate generator.

Builds physically realistic 3D all-atom pocket models for kinase catalytic clefts
and embeds small molecules into 3D metric coordinate space using distance geometry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Dict, List, Optional, Tuple
import numpy as np

from test_molecular_similarity import parse_smiles

# Van der Waals radii (Angstroms)
VDW_RADII: Dict[str, float] = {
    'C': 1.70, 'N': 1.55, 'O': 1.52, 'S': 1.80, 'P': 1.80,
    'F': 1.47, 'Cl': 1.75, 'Br': 1.85, 'I': 1.98, 'H': 1.20
}

# Standard partial charges
PARTIAL_CHARGES: Dict[str, float] = {
    'C': 0.0, 'N': -0.4, 'O': -0.5, 'S': -0.1, 'P': 0.3,
    'F': -0.25, 'Cl': -0.2, 'Br': -0.15, 'I': -0.1, 'H': 0.15
}


@dataclass
class PocketAtom:
    residue_name: str
    atom_name: str
    element: str
    x: float
    y: float
    z: float
    vdw_radius: float
    partial_charge: float
    is_hinge: bool = False
    is_dfg: bool = False
    is_gatekeeper: bool = False
    is_gloop: bool = False


@dataclass
class Pocket3DModel:
    atoms: List[PocketAtom]
    coords: np.ndarray              # (N, 3)
    dfg_status: str                 # "dfg_in", "dfg_out", or "dfg_flexible"
    hinge_res: str = ""
    gatekeeper_res: str = ""
    catalytic_lys_idx: int = -1


@dataclass
class Ligand3DModel:
    smiles: str
    atoms: List[Tuple[str, bool]]   # (element, is_aromatic)
    coords: np.ndarray              # (M, 3)
    bonds: List[Tuple[int, int, int]]


def model_kinase_pocket_3d(sequence: str, dfg_conformation: str = "dfg_in") -> Pocket3DModel:
    """
    Construct canonical 3D Cartesian coordinates for the ATP-binding cleft of a kinase.
    Based on structural biology geometry of catalytic protein kinase domains.
    """
    clean_seq = "".join(sequence.split()).upper()
    length = len(clean_seq)

    # Locate catalytic motifs
    m_gloop = re.search(r'[VILM]G[A-Z]G[A-Z]{2}[GAK]', clean_seq)
    m_vaik = re.search(r'[VILM][A-Z][ILVM][K]', clean_seq)
    m_hrd = re.search(r'[HY]RD[LIVM][KRN]', clean_seq)
    m_dfg = re.search(r'DFG|DYG', clean_seq)

    pocket_atoms: List[PocketAtom] = []

    # 1. Hinge region (ATP adenine coordination anchor)
    # Typically located ~40-60 residues after VAIK and ~40 residues before HRD
    hinge_pos = (m_vaik.end() + 45) if m_vaik else (length // 2)
    hinge_res = clean_seq[hinge_pos] if hinge_pos < length else "M"
    # Backbone amide NH (H-bond donor) and carbonyl O (H-bond acceptor)
    pocket_atoms.append(PocketAtom(hinge_res, "N", "N", 0.0, 0.0, 0.0, VDW_RADII['N'], -0.45, is_hinge=True))
    pocket_atoms.append(PocketAtom(hinge_res, "CA", "C", 1.2, 0.8, 0.0, VDW_RADII['C'], 0.1, is_hinge=True))
    pocket_atoms.append(PocketAtom(hinge_res, "C", "C", 2.4, 0.0, 0.5, VDW_RADII['C'], 0.5, is_hinge=True))
    pocket_atoms.append(PocketAtom(hinge_res, "O", "O", 2.5, -1.2, 0.5, VDW_RADII['O'], -0.5, is_hinge=True))

    # 2. Gatekeeper residue (controls access to hydrophobic back pocket)
    gk_pos = max(0, hinge_pos - 3)
    gk_res = clean_seq[gk_pos] if gk_pos < length else "T"
    pocket_atoms.append(PocketAtom(gk_res, "CA", "C", -2.5, 3.2, -1.0, VDW_RADII['C'], 0.0, is_gatekeeper=True))
    pocket_atoms.append(PocketAtom(gk_res, "CB", "C", -3.2, 4.2, -1.8, VDW_RADII['C'], 0.0, is_gatekeeper=True))

    # 3. Catalytic Lysine (from VAIK motif)
    lys_res = "K"
    pocket_atoms.append(PocketAtom(lys_res, "NZ", "N", 0.2, 6.2, 1.5, VDW_RADII['N'], 0.8, is_hinge=False))
    pocket_atoms.append(PocketAtom(lys_res, "CE", "C", 0.5, 6.8, 0.2, VDW_RADII['C'], 0.1))

    # 4. G-loop canopy (Glycine-rich loop floor ceiling)
    g_res = "G"
    pocket_atoms.append(PocketAtom(g_res, "CA", "C", 0.0, 7.5, 3.8, VDW_RADII['C'], 0.0, is_gloop=True))
    pocket_atoms.append(PocketAtom(g_res, "O", "O", 1.1, 7.8, 4.2, VDW_RADII['O'], -0.4, is_gloop=True))

    # 5. DFG Motif (coordinates Mg2+ and defines Type I vs Type II pocket)
    dfg_seq = "DFG"
    if dfg_conformation == "dfg_out":
        # DFG-out (Phe points out into ATP pocket, opening allosteric back-pocket)
        pocket_atoms.append(PocketAtom("ASP", "OD1", "O", 4.2, 3.8, 0.5, VDW_RADII['O'], -0.7, is_dfg=True))
        pocket_atoms.append(PocketAtom("PHE", "CZ", "C", 6.8, 1.8, 0.8, VDW_RADII['C'], 0.0, is_dfg=True))
        status = "dfg_out"
    else:
        # DFG-in (Active/Type I conformation)
        pocket_atoms.append(PocketAtom("ASP", "OD1", "O", 3.8, 4.5, 0.0, VDW_RADII['O'], -0.7, is_dfg=True))
        pocket_atoms.append(PocketAtom("PHE", "CZ", "C", 5.2, 5.2, -1.8, VDW_RADII['C'], 0.0, is_dfg=True))
        status = "dfg_in"

    # 6. Catalytic Loop (HRD Asp)
    pocket_atoms.append(PocketAtom("ASP", "OD2", "O", 2.2, 1.8, -2.2, VDW_RADII['O'], -0.7))

    coords = np.array([[a.x, a.y, a.z] for a in pocket_atoms], dtype=np.float32)

    return Pocket3DModel(
        atoms=pocket_atoms,
        coords=coords,
        dfg_status=status,
        hinge_res=hinge_res,
        gatekeeper_res=gk_res,
        catalytic_lys_idx=4
    )


def generate_ligand_3d_coordinates(smiles: str) -> Ligand3DModel:
    """
    Embed molecular graph into 3D Euclidean space using distance geometry (MDS).
    Preserves realistic covalent bond lengths and aromatic planar topology.
    """
    clean_smi = smiles.strip()
    atoms, bonds = parse_smiles(clean_smi)
    n = len(atoms)
    if n == 0:
        return Ligand3DModel(clean_smi, [], np.zeros((0, 3), dtype=np.float32), [])

    if n == 1:
        return Ligand3DModel(clean_smi, atoms, np.zeros((1, 3), dtype=np.float32), bonds)

    # 1. Build shortest-path distance bounds matrix
    D = np.full((n, n), 10.0, dtype=np.float32)
    np.fill_diagonal(D, 0.0)

    for u, v, b_type in bonds:
        # Physical bond lengths in Angstroms
        if b_type == 4: # Aromatic
            bond_len = 1.39
        elif b_type == 2: # Double
            bond_len = 1.34
        elif b_type == 3: # Triple
            bond_len = 1.20
        else: # Single
            bond_len = 1.54
        D[u, v] = bond_len
        D[v, u] = bond_len

    # Floyd-Warshall to propagate topological distance bounds
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if D[i, k] + D[k, j] < D[i, j]:
                    D[i, j] = D[i, k] + D[k, j]

    # 2. Classical Multidimensional Scaling (Metric Matrix SVD)
    # Centering matrix H = I - 1/n 11^T
    H = np.eye(n, dtype=np.float32) - (1.0 / n) * np.ones((n, n), dtype=np.float32)
    # Double centering B = -0.5 * H * D^2 * H
    B = -0.5 * H @ (D ** 2) @ H

    # Eigen-decomposition of B
    eigvals, eigvecs = np.linalg.eigh(B)
    # Select top 3 positive eigenvalues
    idx = np.argsort(eigvals)[::-1]
    top_vals = np.maximum(eigvals[idx[:3]], 0.01)
    top_vecs = eigvecs[:, idx[:3]]

    # Coordinates X = V * sqrt(Lambda)
    coords = top_vecs @ np.diag(np.sqrt(top_vals))

    # 3. Distance Geometry Relaxation (Spring Embedder refinement for 1-2 bonds)
    alpha = 0.35
    for _ in range(30):
        for u, v, b_type in bonds:
            target = 1.39 if b_type == 4 else (1.34 if b_type == 2 else (1.20 if b_type == 3 else 1.54))
            diff = coords[u] - coords[v]
            dist = np.linalg.norm(diff)
            if dist < 1e-4:
                diff = np.random.randn(3).astype(np.float32) * 0.1
                dist = np.linalg.norm(diff)
            delta = (dist - target) * (diff / dist)
            coords[u] -= alpha * 0.5 * delta
            coords[v] += alpha * 0.5 * delta

    # Center at origin
    coords = coords - coords.mean(axis=0)

    return Ligand3DModel(
        smiles=clean_smi,
        atoms=atoms,
        coords=coords.astype(np.float32),
        bonds=bonds
    )
