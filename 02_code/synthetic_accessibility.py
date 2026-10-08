"""Synthetic Accessibility (SA Score) estimation module for medicinal chemistry and lead optimization.

Follows the principles of Ertl & Schuffenhauer (J. Cheminform. 2009):
- Fragment contribution & commonality
- Ring system complexity (fused, spiro, bridged, macrocycles)
- Stereocenters & chiral complexity
- Molecular size & heteroatom ratio penalty
Normalized to [1.0, 10.0]:
- 1.0 - 3.5: Highly accessible / commercial starting materials (Easy)
- 3.5 - 5.5: Moderately accessible / typical 3-5 steps (Moderate)
- > 5.5: Challenging synthesis / non-trivial or chiral purification required (Challenging)
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Dict, Any


@dataclass
class SyntheticAccessibilityResult:
    """Synthetic Accessibility calculation result supporting attribute and dict access."""
    sa_score: float
    sa_tier: str
    sa_label: str
    sa_color: str
    details: Dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sa_score": self.sa_score,
            "sa_tier": self.sa_tier,
            "sa_label": self.sa_label,
            "sa_color": self.sa_color,
            "details": self.details
        }


def compute_sa_score(smiles: str) -> SyntheticAccessibilityResult:
    """Compute Synthetic Accessibility score and medchem categorization from SMILES."""
    smi = smiles.strip()
    if not smi:
        return SyntheticAccessibilityResult(
            sa_score=3.0,
            sa_tier="easy",
            sa_label="容易合成 (商业原料/温和反应)",
            sa_color="emerald",
            details={}
        )

    # 1. Molecular size & heavy atom count
    # Remove hydrogens in brackets like [H]
    clean_smi = re.sub(r'\[H\]', '', smi)
    heavy_atoms = len(re.findall(r'[A-Za-z]', clean_smi))
    heavy_atoms = max(1, heavy_atoms)

    # Size penalty: optimal drug-like heavy atom count is 20-35
    if heavy_atoms < 15:
        size_penalty = 1.0 + (15 - heavy_atoms) * 0.05
    elif heavy_atoms <= 38:
        size_penalty = 1.0 + (heavy_atoms - 20) * 0.025
    else:
        size_penalty = 1.45 + (heavy_atoms - 38) * 0.06

    # 2. Ring complexity
    ring_digits = re.findall(r'[0-9]', smi)
    num_ring_closures = len(ring_digits) // 2
    # Check for fused or complex rings (e.g. %10 or multiple closures on same atom)
    fused_penalty = 0.0
    if num_ring_closures > 3:
        fused_penalty += (num_ring_closures - 3) * 0.4
    if num_ring_closures > 5:
        fused_penalty += (num_ring_closures - 5) * 0.6

    # Check for macrocycles (>8 membered rings typically not common in kinase ATP competitive inhibitors)
    macrocycle_penalty = 0.0
    if re.search(r'%[0-9]{2}', smi):
        macrocycle_penalty = 1.2

    # 3. Chiral centers & stereochemistry indicators (@, @@, /, \)
    chiral_centers = len(re.findall(r'@[a-zA-Z]', smi)) + smi.count('@@')
    chiral_penalty = chiral_centers * 0.45

    # 4. Functional group & Fragment ease
    # Penalize uncommon/unstable motifs in standard medchem
    unusual_motifs = 0
    # Peroxides, poly-nitro, hydrazines, quaternary carbons
    if "OO" in smi or "NNN" in smi:
        unusual_motifs += 2.0
    if smi.count("[N+](=O)[O-]") > 1:
        unusual_motifs += 1.0
    # Heavy halogens or unusual atoms
    if "I" in smi or "B" in smi or "Si" in smi:
        unusual_motifs += 0.8

    # Common medchem favorable motifs (bonus / reduction)
    ease_bonus = 0.0
    # Amide bond C(=O)N
    if "C(=O)N" in smi or "NC(=O)" in smi or "C(=O)NC" in smi:
        ease_bonus += 0.4
    # Classical bioisosteres: Morpholine, piperazine, pyridine, phenyl
    if "N1CCOCC1" in smi or "N1CCNCC1" in smi or "n1ccccc1" in smi:
        ease_bonus += 0.35
    # Common kinase aniline core
    if "c1ccccc1" in smi or "c1ccncc1" in smi:
        ease_bonus += 0.25

    # 5. Synthesis raw score assembly
    base_score = 2.20
    raw_score = (base_score * size_penalty) + fused_penalty + macrocycle_penalty + chiral_penalty + unusual_motifs - ease_bonus

    # Clamp to [1.0, 10.0]
    final_score = round(max(1.0, min(10.0, raw_score)), 2)

    # Classification
    if final_score <= 3.50:
        sa_tier = "easy"
        sa_label = "原料易购好合成 (一步/经典反应)"
        sa_color = "emerald"
    elif final_score <= 5.50:
        sa_tier = "moderate"
        sa_label = "常规有机合成路线 (典型3-5步)"
        sa_color = "amber"
    else:
        sa_tier = "challenging"
        sa_label = "合成路线苛刻/多手性拆分"
        sa_color = "rose"

    return SyntheticAccessibilityResult(
        sa_score=final_score,
        sa_tier=sa_tier,
        sa_label=sa_label,
        sa_color=sa_color,
        details={
            "heavy_atoms": heavy_atoms,
            "num_rings": num_ring_closures,
            "chiral_centers": chiral_centers,
            "size_penalty": round(size_penalty, 3),
            "ring_penalty": round(fused_penalty + macrocycle_penalty, 3),
            "ease_bonus": round(ease_bonus, 3)
        }
    )
