"""Kinase Conformation Adapter and Induced-Fit Free Energy Scoring Engine.

Models DFG-loop conformational dynamics (DFG-in active vs DFG-out inactive/allosteric states),
classifies inhibitor binding modalities (Type I, Type II, Covalent), and computes
thermodynamic reorganization penalties for induced-fit binding.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Any, Dict, Optional, Tuple
import numpy as np

from fetch_kinase_pocket_3d import model_kinase_pocket_3d, generate_ligand_3d_coordinates
from equivariant_pocket_matcher import (
    compute_equivariant_pocket_match,
    PocketMatchResult
)

# Standard thermodynamic conversion: 1 pKd unit ~ 2.303 * R * T ~ 1.363 kcal/mol at 298.15 K
KCAL_PER_PKD = 1.363


@dataclass
class InducedFitResult:
    """Biophysical result from the Kinase Conformation Adapter."""
    binding_mode: str               # "type_i", "type_ii", or "covalent"
    preferred_conformation: str     # "dfg_in" or "dfg_out"
    dfg_flip_penalty_kcal: float    # Conformational free energy penalty (kcal/mol)
    effective_pkd_delta: float      # Effective delta contribution in pKd units
    base_dock_score: float          # Raw geometric complementarity score
    induced_fit_score: float        # Calibrated induced-fit affinity score
    details: Dict[str, Any] = field(default_factory=dict)


def classify_inhibitor_binding_mode(smiles: str) -> str:
    """
    Classify small molecule kinase inhibitor binding modality from SMILES:
    - "covalent": Michael acceptor (acrylamide) targeted to catalytic Cys (e.g., Osimertinib, Afatinib)
    - "type_ii": Extended urea / benzamide linker occupying allosteric back-pocket (e.g., Imatinib, Sorafenib)
    - "type_i": ATP-competitive hinge binder occupying standard cleft (e.g., Gefitinib, Erlotinib, Dasatinib)
    """
    clean_smi = smiles.strip()

    # 1. Covalent Michael acceptor (acrylamide: C=C-C=O or C(=O)C=C)
    if re.search(r'C\(=O\)C=C|NC\(=O\)C=C|C=CC\(=O\)', clean_smi, re.IGNORECASE):
        return "covalent"

    # 2. Urea motif: hallmark of Sorafenib / Regorafenib / Lenvatinib
    if re.search(r'NC\(=[OS]\)N', clean_smi, re.IGNORECASE):
        return "type_ii"

    # 3. Extended amide with allosteric CF3 or extended biaryl-piperazine tail: Imatinib, Nilotinib, Ponatinib
    if re.search(r'[NC]\(=O\)[NC].{0,10}c\d?ccc\(cc\d?\).{0,15}(CN\d?CCN|C\(F\)\(F\)F)', clean_smi, re.IGNORECASE):
        return "type_ii"
    if re.search(r'NC\(=O\)c\d?ccc\(cc\d?\)CN\d?CCN', clean_smi, re.IGNORECASE):
        return "type_ii"

    return "type_i"


def estimate_kinase_dfg_penalty(sequence: str) -> float:
    """
    Estimate the conformational free energy reorganization penalty (kcal/mol)
    required for the kinase to transition from DFG-in to DFG-out state.
    
    Biophysical principles:
    - Kinases with flexible activation loops (Abl, Kit, VEGFR/KDR, PDGFR, DDR, BRAF)
      readily adopt DFG-out (penalty: 1.2 to 2.2 kcal/mol).
    - Kinases with rigid regulatory domains or salt-bridges (EGFR, ERBB2, CDK2, AKT)
      have high barriers to DFG-out (penalty: 4.5 to 6.0 kcal/mol).
    - Default kinases: ~2.8 kcal/mol.
    """
    clean_seq = "".join(sequence.split()).upper()

    # EGFR family signature (ERBB)
    if re.search(r'VAIK.{20,60}HRDLAARN.{10,30}DFGLAKL', clean_seq):
        return 5.2

    # CDK / MAPK family signature
    if re.search(r'HRDLKPEN|HRDLKPQN', clean_seq):
        return 4.6

    # ABL / KIT / PDGFR / VEGFR signature (flexible DFG loop, accessible Type II pocket)
    if re.search(r'DFGLSR|DFGLAR|DFGLAY', clean_seq):
        return 1.6

    # Specific known motifs:
    # Abl kinase SHNYIT...
    if "SHNYIT" in clean_seq or "FGLSRLMT" in clean_seq:
        return 1.4

    # KDR / VEGFR2
    if "VDFGLARDI" in clean_seq or "KDR" in clean_seq:
        return 1.8

    # General default
    return 2.8


def compute_induced_fit_interaction(
    sequence: str,
    smiles: str,
    gatekeeper_override: Optional[str] = None
) -> InducedFitResult:
    """
    Compute induced-fit interaction score taking into account DFG conformational flipping
    and inhibitor binding modality.
    """
    binding_mode = classify_inhibitor_binding_mode(smiles)
    flip_penalty_kcal = estimate_kinase_dfg_penalty(sequence)
    ligand = generate_ligand_3d_coordinates(smiles)

    # 1. Dock into DFG-in conformation
    pocket_in = model_kinase_pocket_3d(sequence, dfg_conformation="dfg_in", gatekeeper_override=gatekeeper_override)
    res_in = compute_equivariant_pocket_match(pocket_in, ligand)

    # 2. Dock into DFG-out conformation
    pocket_out = model_kinase_pocket_3d(sequence, dfg_conformation="dfg_out", gatekeeper_override=gatekeeper_override)
    res_out = compute_equivariant_pocket_match(pocket_out, ligand)

    # 3. Reconcile thermodynamic affinity based on modality
    if binding_mode == "type_ii":
        # Type II inhibitors require DFG-out pocket to accommodate their extended tail
        preferred_conf = "dfg_out"
        # The conformational penalty reduces binding affinity
        penalty_pkd = flip_penalty_kcal / KCAL_PER_PKD
        base_score = res_out.dock_score
        induced_score = base_score - penalty_pkd
        effective_delta = -penalty_pkd
    elif binding_mode == "covalent":
        # Covalent inhibitors bind DFG-in and form irreversible adduct with catalytic cysteine
        preferred_conf = "dfg_in"
        # Covalent bond formation provides free energy bonus
        covalent_bonus = 1.8  # ~ 1.8 pKd units affinity gain
        base_score = res_in.dock_score
        induced_score = base_score + covalent_bonus
        effective_delta = covalent_bonus
    else: # type_i
        # Type I inhibitors bind the active DFG-in cleft
        preferred_conf = "dfg_in"
        base_score = res_in.dock_score
        induced_score = base_score
        effective_delta = 0.0

    return InducedFitResult(
        binding_mode=binding_mode,
        preferred_conformation=preferred_conf,
        dfg_flip_penalty_kcal=flip_penalty_kcal,
        effective_pkd_delta=float(effective_delta),
        base_dock_score=float(base_score),
        induced_fit_score=float(induced_score),
        details={
            "score_dfg_in": float(res_in.dock_score),
            "score_dfg_out": float(res_out.dock_score),
            "hinge_score": float(res_in.hinge_hbond_score if preferred_conf == "dfg_in" else res_out.hinge_hbond_score),
            "gatekeeper_clash": float(res_in.gatekeeper_clash if preferred_conf == "dfg_in" else res_out.gatekeeper_clash)
        }
    )
