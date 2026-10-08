"""Comprehensive ADMET (Absorption, Distribution, Metabolism, Excretion, Toxicity) Property Predictor.

Implements first-principles and validated QSAR heuristic descriptors for medicinal chemistry:
1. hERG Cardiac Safety (pIC50 & Risk Tier)
2. Cytochrome P450 Inhibition (CYP3A4 & CYP2D6)
3. Blood-Brain Barrier (BBB) Permeability (Clark LogBB model)
4. Aqueous Solubility (Delaney ESOL model, LogS & mg/mL)
5. Caco-2 Cell Membrane Permeability (Papp x 10^-6 cm/s)
6. Holistic ADMET Health Score (0-100) and 5-dimension radar coordinates
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Any, Dict, List, Optional

from synthetic_accessibility import compute_sa_score


@dataclass
class ADMETResult:
    """Holistic ADMET assessment output with quantitative values and clinical risk tiers."""
    smiles: str
    
    # 1. Absorption & Solubility
    solubility_logs: float              # LogS (mol/L)
    solubility_mg_ml: float             # Approximate solubility in mg/mL
    solubility_tier: str                # "high" | "moderate" | "poor"
    solubility_label: str
    
    caco2_papp: float                   # Caco-2 Papp (10^-6 cm/s)
    caco2_tier: str                     # "high" | "moderate" | "low"
    caco2_label: str
    
    # 2. Distribution
    log_bb: float                       # Clark Blood-Brain Barrier partitioning log(C_brain / C_blood)
    bbb_tier: str                       # "cns_penetrant" | "cns_balanced" | "cns_impermeant"
    bbb_label: str
    
    # 3. Metabolism
    cyp3a4_inhibition: str              # "low_risk" | "moderate_risk" | "high_risk"
    cyp3a4_label: str
    cyp2d6_inhibition: str              # "low_risk" | "moderate_risk" | "high_risk"
    cyp2d6_label: str
    
    # 4. Toxicity & Safety
    herg_pic50: float                   # -log10(IC50 in M) for hERG K+ channel
    herg_risk: str                      # "low" | "medium" | "high"
    herg_label: str
    herg_color: str                     # "emerald" | "amber" | "rose"
    
    # 5. Composite Metric & Radar Dimensions (0 - 100 scale)
    admet_health_score: float           # 0 to 100 overall drug health index
    radar_scores: Dict[str, float]      # {solubility, permeability, herg_safety, cyp_stability, synthesis_sa}
    traffic_lights: Dict[str, str]      # Green / Amber / Red summary
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "smiles": self.smiles,
            "solubility_logs": self.solubility_logs,
            "solubility_mg_ml": self.solubility_mg_ml,
            "solubility_tier": self.solubility_tier,
            "solubility_label": self.solubility_label,
            "caco2_papp": self.caco2_papp,
            "caco2_tier": self.caco2_tier,
            "caco2_label": self.caco2_label,
            "log_bb": self.log_bb,
            "bbb_tier": self.bbb_tier,
            "bbb_label": self.bbb_label,
            "cyp3a4_inhibition": self.cyp3a4_inhibition,
            "cyp3a4_label": self.cyp3a4_label,
            "cyp2d6_inhibition": self.cyp2d6_inhibition,
            "cyp2d6_label": self.cyp2d6_label,
            "herg_pic50": self.herg_pic50,
            "herg_risk": self.herg_risk,
            "herg_label": self.herg_label,
            "herg_color": self.herg_color,
            "admet_health_score": self.admet_health_score,
            "radar_scores": self.radar_scores,
            "traffic_lights": self.traffic_lights
        }


def _extract_descriptors(smiles: str) -> Dict[str, float]:
    """Calculate basic physicochemical and atom count descriptors for ADMET models."""
    s = smiles.strip()
    clean_s = re.sub(r'\[H\]', '', s)
    
    num_cl = len(re.findall(r'Cl', s))
    num_br = len(re.findall(r'Br', s))
    sub_hal = re.sub(r'Cl|Br', '', clean_s)
    
    num_c = len(re.findall(r'[Cc]', sub_hal))
    num_n = len(re.findall(r'[Nn]', sub_hal))
    num_o = len(re.findall(r'[Oo]', sub_hal))
    num_f = len(re.findall(r'F', sub_hal))
    num_s = len(re.findall(r'[Ss]', sub_hal))
    num_p = len(re.findall(r'P', sub_hal))
    
    num_double = len(re.findall(r'=', s))
    num_triple = len(re.findall(r'#', s))
    num_rings = len(re.findall(r'[0-9]', s)) // 2
    
    approx_h = max(0, num_c * 2 + 2 - num_double * 2 - num_triple * 4 - num_rings * 2)
    mw = (num_c * 12.011 + num_n * 14.007 + num_o * 15.999 + num_f * 18.998 +
          num_cl * 35.45 + num_br * 79.904 + num_s * 32.06 + num_p * 30.974 + approx_h * 1.008)
    
    # Hydrogen bond donors (HBD) and acceptors (HBA)
    hbd = len(re.findall(r'O[Hh]|N[Hh]|\[nH\]|\[NH\]', s))
    if hbd == 0:
        hbd = max(0, len(re.findall(r'[Nn][^=]', s)) // 3)
    hba = num_n + num_o
    
    # LogP estimate (Ghose-Crippen approximation)
    logp = (num_c * 0.25 + num_cl * 0.65 + num_br * 0.85 + num_f * 0.15 -
            num_n * 0.45 - num_o * 0.40 + num_s * 0.35)
    
    # Topological Polar Surface Area (TPSA, Å²)
    tpsa = num_n * 14.5 + num_o * 18.0 + num_s * 25.0
    
    # Rotatable bonds
    rot_bonds = max(0, len(re.findall(r'[A-Za-z][A-Za-z]', re.sub(r'[0-9()=#]', '', s))) // 3)
    
    # Aromatic atoms & proportion
    aromatic_atoms = len(re.findall(r'[cno]', s))
    heavy_atoms = max(1, num_c + num_n + num_o + num_f + num_cl + num_br + num_s + num_p)
    aromatic_proportion = aromatic_atoms / heavy_atoms
    
    # Basic amine indicator (tertiary or secondary aliphatic amine)
    has_basic_amine = bool(re.search(r'N\dCCN|CCNCC|CN\(C\)C|N1CCNCC1', s))
    
    return {
        "mw": mw,
        "logp": logp,
        "hbd": hbd,
        "hba": hba,
        "tpsa": tpsa,
        "rot_bonds": rot_bonds,
        "heavy_atoms": heavy_atoms,
        "aromatic_proportion": aromatic_proportion,
        "has_basic_amine": 1.0 if has_basic_amine else 0.0
    }


def predict_admet_properties(smiles: str) -> ADMETResult:
    """Predict holistic ADMET profile and compute radar health coordinates."""
    s = smiles.strip()
    if not s:
        # Default benign fallback
        return ADMETResult(
            smiles="",
            solubility_logs=-3.5,
            solubility_mg_ml=0.1,
            solubility_tier="moderate",
            solubility_label="中等水溶性",
            caco2_papp=8.5,
            caco2_tier="moderate",
            caco2_label="中等膜透性",
            log_bb=-0.8,
            bbb_tier="cns_balanced",
            bbb_label="外周优先 (低中枢毒性)",
            cyp3a4_inhibition="low_risk",
            cyp3a4_label="低抑制风险",
            cyp2d6_inhibition="low_risk",
            cyp2d6_label="低抑制风险",
            herg_pic50=4.8,
            herg_risk="low",
            herg_label="心脏安全性良好 (IC50 > 10 µM)",
            herg_color="emerald",
            admet_health_score=78.0,
            radar_scores={"solubility": 70.0, "permeability": 75.0, "herg_safety": 85.0, "cyp_stability": 80.0, "synthesis_sa": 80.0},
            traffic_lights={"solubility": "green", "permeability": "green", "herg_safety": "green", "cyp_stability": "green"}
        )

    desc = _extract_descriptors(s)
    mw = desc["mw"]
    logp = desc["logp"]
    tpsa = desc["tpsa"]
    rb = desc["rot_bonds"]
    ap = desc["aromatic_proportion"]
    basic_amine = desc["has_basic_amine"]

    # 1. Aqueous Solubility (Delaney ESOL model)
    # LogS = 0.16 - 0.63 * LogP - 0.0062 * MW + 0.066 * RB - 0.74 * AP
    logs = 0.16 - (0.63 * logp) - (0.0062 * mw) + (0.066 * rb) - (0.74 * ap)
    logs = round(logs, 2)
    # Convert LogS to approximate mg/mL (S = 10^LogS * MW * 1000 mg/mol)
    conc_mol_l = math.pow(10, logs)
    mg_per_ml = round(conc_mol_l * mw, 3)

    if logs >= -3.5:
        sol_tier = "high"
        sol_label = f"良好水溶性 (LogS {logs} · {mg_per_ml} mg/mL)"
        sol_score = 90.0
    elif logs >= -5.2:
        sol_tier = "moderate"
        sol_label = f"中等水溶性 (LogS {logs} · 常规口服制剂范围)"
        sol_score = 68.0
    else:
        sol_tier = "poor"
        sol_label = f"低水溶性预警 (LogS {logs} · 需助溶剂/前药)"
        sol_score = 35.0

    # 2. Caco-2 Cell Permeability (Papp in 10^-6 cm/s)
    # Heuristic based on TPSA and MW
    papp_raw = 18.0 - (tpsa * 0.11) - (mw * 0.008) + (logp * 1.2)
    papp = round(max(0.2, min(35.0, papp_raw)), 1)
    if papp >= 10.0:
        caco2_tier = "high"
        caco2_label = f"高透膜性 (Papp {papp} · 易口服吸收)"
        perm_score = 90.0
    elif papp >= 3.0:
        caco2_tier = "moderate"
        caco2_label = f"中等透膜性 (Papp {papp})"
        perm_score = 70.0
    else:
        caco2_tier = "low"
        caco2_label = f"低膜透性 (Papp {papp} · 透膜受限)"
        perm_score = 40.0

    # 3. Blood-Brain Barrier (Clark LogBB Model)
    # LogBB = 0.152 * LogP - 0.0148 * TPSA + 0.139
    logbb = round(0.152 * logp - 0.0148 * tpsa + 0.139, 2)
    if logbb >= 0.0:
        bbb_tier = "cns_penetrant"
        bbb_label = f"高血脑屏障透过 (LogBB {logbb} · 适合脑转移靶点)"
    elif logbb >= -1.0:
        bbb_tier = "cns_balanced"
        bbb_label = f"外周/中枢平衡 (LogBB {logbb} · 常规激酶分布)"
    else:
        bbb_tier = "cns_impermeant"
        bbb_label = f"外周限制型 (LogBB {logbb} · 极低中枢神经毒性)"

    # 4. Cytochrome P450 Inhibition (CYP3A4 & CYP2D6)
    # CYP3A4 inhibition correlates with high lipophilicity (LogP > 3.8) and large MW
    if logp > 4.2 or (logp > 3.2 and mw > 480):
        cyp3a4 = "high_risk"
        cyp3a4_label = "CYP3A4 高结合倾向 (需关注药物相互作用 DDI)"
        cyp3a4_score = 45.0
    elif logp > 2.5:
        cyp3a4 = "moderate_risk"
        cyp3a4_label = "CYP3A4 中度代谢底物 (常规范围)"
        cyp3a4_score = 72.0
    else:
        cyp3a4 = "low_risk"
        cyp3a4_label = "CYP3A4 低抑制风险 (代谢洁净)"
        cyp3a4_score = 92.0

    # CYP2D6 inhibition strongly correlates with basic amine centers and lipophilic aromatic core
    if basic_amine and logp > 2.8:
        cyp2d6 = "moderate_risk"
        cyp2d6_label = "CYP2D6 中度亲和倾向 (碱性中心互作)"
        cyp2d6_score = 65.0
    elif basic_amine and logp > 4.0:
        cyp2d6 = "high_risk"
        cyp2d6_label = "CYP2D6 高抑制风险"
        cyp2d6_score = 40.0
    else:
        cyp2d6 = "low_risk"
        cyp2d6_label = "CYP2D6 抑制风险低"
        cyp2d6_score = 90.0

    cyp_stability_score = round((cyp3a4_score + cyp2d6_score) / 2.0, 1)

    # 5. hERG Cardiac Safety (pIC50 = -log10(IC50))
    # Predictive factors: basic aliphatic amine, LogP > 3.5, aromatic rings >= 3
    herg_base = 4.2
    if basic_amine:
        herg_base += 0.95
    if logp > 3.5:
        herg_base += (logp - 3.5) * 0.45
    if ap > 0.45:
        herg_base += 0.35
    if mw > 500:
        herg_base += 0.25
    # Carboxylic acids or polar zwitterions strongly suppress hERG binding
    if "C(=O)O" in s or "S(=O)(=O)O" in s:
        herg_base -= 1.1

    herg_pic50 = round(max(3.8, min(8.5, herg_base)), 2)
    # pIC50 < 5.0 (IC50 > 10 µM) -> Low Risk
    # 5.0 <= pIC50 < 6.0 (1 µM <= IC50 <= 10 µM) -> Medium Risk
    # pIC50 >= 6.0 (IC50 < 1 µM) -> High Risk
    if herg_pic50 < 5.0:
        herg_risk = "low"
        herg_label = f"心脏安全性优良 (hERG pIC50 {herg_pic50} · IC50 > 10 µM)"
        herg_color = "emerald"
        herg_safety_score = 92.0
    elif herg_pic50 < 5.8:
        herg_risk = "medium"
        herg_label = f"中度 hERG 阻断倾向 (pIC50 {herg_pic50} · 需行 Patch-clamp 膜片钳实测)"
        herg_color = "amber"
        herg_safety_score = 65.0
    else:
        herg_risk = "high"
        herg_label = f"高心脏毒性预警 (hERG pIC50 {herg_pic50} · 易致 QT 间期延长)"
        herg_color = "rose"
        herg_safety_score = 30.0

    # 6. Synthesis Feasibility from SA Score
    sa_res = compute_sa_score(s)
    # Map 1.0 (easy) -> 95, 10.0 (difficult) -> 20
    synthesis_sa_score = round(max(20.0, min(98.0, 100.0 - (sa_res.sa_score - 1.0) * 8.5)), 1)

    # 7. Composite ADMET Health Score (0 - 100)
    composite_health = (
        sol_score * 0.22 +
        perm_score * 0.20 +
        herg_safety_score * 0.28 +
        cyp_stability_score * 0.15 +
        synthesis_sa_score * 0.15
    )
    composite_health = round(max(10.0, min(99.0, composite_health)), 1)

    traffic_lights = {
        "solubility": "green" if sol_tier == "high" else "amber" if sol_tier == "moderate" else "red",
        "permeability": "green" if caco2_tier == "high" else "amber" if caco2_tier == "moderate" else "red",
        "herg_safety": "green" if herg_risk == "low" else "amber" if herg_risk == "medium" else "red",
        "cyp_stability": "green" if cyp3a4 != "high_risk" and cyp2d6 != "high_risk" else "amber"
    }

    return ADMETResult(
        smiles=s,
        solubility_logs=logs,
        solubility_mg_ml=mg_per_ml,
        solubility_tier=sol_tier,
        solubility_label=sol_label,
        caco2_papp=papp,
        caco2_tier=caco2_tier,
        caco2_label=caco2_label,
        log_bb=logbb,
        bbb_tier=bbb_tier,
        bbb_label=bbb_label,
        cyp3a4_inhibition=cyp3a4,
        cyp3a4_label=cyp3a4_label,
        cyp2d6_inhibition=cyp2d6,
        cyp2d6_label=cyp2d6_label,
        herg_pic50=herg_pic50,
        herg_risk=herg_risk,
        herg_label=herg_label,
        herg_color=herg_color,
        admet_health_score=composite_health,
        radar_scores={
            "solubility": sol_score,
            "permeability": perm_score,
            "herg_safety": herg_safety_score,
            "cyp_stability": cyp_stability_score,
            "synthesis_sa": synthesis_sa_score
        },
        traffic_lights=traffic_lights
    )
