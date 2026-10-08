"""AI-assisted and heuristic small-molecule lead optimizer for DTI kinase affinity."""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from typing import Dict, List, Optional
import numpy as np

from dti_inference_runtime import DTIInferenceRuntime
from test_molecular_similarity import get_morgan_fingerprint
from synthetic_accessibility import compute_sa_score

logger = logging.getLogger(__name__)


def _sub_phenyl(s: str, rep_template: str) -> str:
    def repl(m):
        n = m.group(1)
        return rep_template.format(n=n)
    return re.sub(r'c([0-9])ccccc\1', repl, s, count=1)


MEDCHEM_RULES = [
    {
        "name": "对位氟化衍生物 (4-Fluoro Bioisostere)",
        "modification_type": "氟原子取代 (Fluorine Scanning)",
        "description": "在末端苯环的对位引入电负性极强的 -F 原子，阻断 CYP450 氧化代谢位点，增强偶极矩与局部结合亲和力。",
        "transform": lambda s: _sub_phenyl(s, 'c{n}ccc(F)cc{n}') if re.search(r'c([0-9])ccccc\1', s) else (s + 'F' if 'c' in s else s)
    },
    {
        "name": "三氟甲基修饰物 (Trifluoromethyl Analog)",
        "modification_type": "亲脂性增效 (CF3 Substitution)",
        "description": "引入 -CF3 基团占据激酶疏水变构口袋（Back Pocket / Hydrophobic Pocket II），增强范德华堆积与膜穿透性。",
        "transform": lambda s: _sub_phenyl(s, 'c{n}ccc(C(F)(F)F)cc{n}') if re.search(r'c([0-9])ccccc\1', s) else (s + 'C(F)(F)F' if 'c' in s else s)
    },
    {
        "name": "二甲基叔胺微调 (Dimethylamino Derivative)",
        "modification_type": "碱性中心修饰 (Basic Center Modulation)",
        "description": "将伯胺/仲胺进行甲基化修饰，调节分子 pKa 与亲脂性，降低脱靶结合可能并增强代谢稳定性。",
        "transform": lambda s: s.replace('(N)', '(N(C)C)', 1) if '(N)' in s else (s.replace('N', 'N(C)C', 1) if 'N(C)C' not in s else s)
    },
    {
        "name": "吗啉环增溶侧链 (Morpholine Tail Addition)",
        "modification_type": "溶剂区极性尾巴 (Solvent Exposure Tuning)",
        "description": "在分子末端引入经典吗啉乙氧基增溶尾巴（如吉非替尼/阿法替尼模式），伸向激酶溶剂暴露区，改善水溶性并形成潜在弱相互作用。",
        "transform": lambda s: _sub_phenyl(s, 'c{n}ccc(OCCN1CCOCC1)cc{n}') if re.search(r'c([0-9])ccccc\1', s) else s
    },
    {
        "name": "氰基生物电子等排体 (Cyano Bioisostere)",
        "modification_type": "氢键受体增强 (Nitrile Bioisosterism)",
        "description": "引入刚性弱吸电子氰基（-C#N），与激酶催化口袋铰链区主链 NH 形成定向极性相互作用。",
        "transform": lambda s: _sub_phenyl(s, 'c{n}ccc(C#N)cc{n}') if re.search(r'c([0-9])ccccc\1', s) else (s + 'C#N' if 'c' in s else s)
    }
]


def generate_heuristic_candidates(smiles: str) -> List[dict]:
    """Generate 3-5 structurally valid candidate analogs using established medicinal chemistry rules."""
    candidates = []
    seen_smiles = {smiles}

    for idx, rule in enumerate(MEDCHEM_RULES):
        try:
            cand_smiles = rule["transform"](smiles)
            if cand_smiles != smiles and cand_smiles not in seen_smiles:
                # Test fingerprint generation to ensure validity
                fp = get_morgan_fingerprint(cand_smiles)
                if (fp > 0).sum() > 0:
                    candidates.append({
                        "name": rule["name"],
                        "modification_type": rule["modification_type"],
                        "smiles": cand_smiles,
                        "rationale": rule["description"]
                    })
                    seen_smiles.add(cand_smiles)
        except Exception:
            continue

    # Fallback if regex transformations failed on non-standard smiles
    if len(candidates) < 2:
        for suffix, name, desc in [
            ("(F)", "单氟取代物", "芳环引入氟原子"),
            ("(C(F)(F)F)", "三氟甲基修饰物", "引入疏水 CF3 基团"),
            ("(OCCN1CCOCC1)", "吗啉环增溶修饰", "引入经典激酶抑制剂极性增溶尾巴")
        ]:
            c_smiles = smiles + suffix
            try:
                fp = get_morgan_fingerprint(c_smiles)
                if (fp > 0).sum() > 0 and c_smiles not in seen_smiles:
                    candidates.append({
                        "name": name,
                        "modification_type": "结构延伸",
                        "smiles": c_smiles,
                        "rationale": desc
                    })
                    seen_smiles.add(c_smiles)
            except Exception:
                pass

    return candidates


def generate_llm_candidates(
    smiles: str,
    target_name: str,
    baseline_pkd: float,
    baseline_kd_nM: float,
    optimization_goal: str,
    custom_instruction: str,
    llm_config: dict
) -> List[dict]:
    """Call external LLM to generate novel analogs with chemical rationale."""
    api_key = llm_config.get("api_key", "").strip()
    base_url = (llm_config.get("base_url") or llm_config.get("api_base") or "https://api.deepseek.com").rstrip("/")
    model_name = (llm_config.get("model_name") or llm_config.get("model") or "deepseek-chat").strip()
    
    if not base_url.endswith("/chat/completions"):
        base_url += "/chat/completions"

    system_prompt = (
        "You are a world-class medicinal chemist and computational drug discovery specialist. "
        "Your task is to design rational derivative analogs (modified SMILES) of a starting kinase inhibitor "
        "to optimize its binding affinity and selectivity against a specific target kinase.\n"
        "Output ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "modifications": [\n'
        "    {\n"
        '      "name": "Short Name (e.g. 4-Fluoro Analog)",\n'
        '      "modification_type": "Fluorination / Ring extension / ...",\n'
        '      "smiles": "Valid complete canonical SMILES string",\n'
        '      "rationale": "Clear medicinal chemistry rationale in Chinese"\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    user_prompt = (
        f"Starting Molecule SMILES: {smiles}\n"
        f"Target Kinase: {target_name}\n"
        f"Current Predicted Affinity: pKd = {baseline_pkd:.2f} (Kd ≈ {baseline_kd_nM:.1f} nM)\n"
        f"Optimization Goal: {optimization_goal}\n"
        f"Special Instructions: {custom_instruction or 'None'}\n"
        "Please propose 3 to 4 distinct modified molecules with valid, synthetically accessible SMILES."
    )

    payload = {
        "model": model_name,
        "temperature": 0.3,
        "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    req = urllib.request.Request(
        base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        data = json.loads(body)
        raw_content = data["choices"][0]["message"]["content"]

    # Strip markdown code fences if present, then extract JSON
    cleaned = re.sub(r'```(?:json)?\s*', '', raw_content)
    cleaned = re.sub(r'```', '', cleaned)
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
    if not match:
        raise ValueError("LLM response did not contain valid JSON")
    
    parsed = json.loads(match.group(0))
    mods = parsed.get("modifications", [])
    
    valid_candidates = []
    for m in mods:
        s = m.get("smiles", "").strip()
        if s and s != smiles:
            try:
                # Test validity
                fp = get_morgan_fingerprint(s)
                if (fp > 0).sum() > 0:
                    valid_candidates.append({
                        "name": m.get("name", "AI 优化衍生分子"),
                        "modification_type": m.get("modification_type", "AI 结构优化"),
                        "smiles": s,
                        "rationale": m.get("rationale", "大模型药化分析推荐改构方案")
                    })
            except Exception:
                continue

    if not valid_candidates:
        raise ValueError("No synthetically parseable candidate SMILES returned by LLM")

    return valid_candidates


class DTILeadOptimizer:
    def __init__(self, runtime: DTIInferenceRuntime):
        self.runtime = runtime

    def optimize(
        self,
        drug_smiles: str,
        target_sequence: str,
        target_name: str = "Target Kinase",
        optimization_goal: str = "提升亲和力与结合强度",
        custom_instruction: str = "",
        model_name: str = "ridge",
        llm_config: Optional[dict] = None
    ) -> dict:
        self.runtime.load()

        # Step 1: Baseline prediction
        baseline_pred = self.runtime.predict(drug_smiles, target_sequence, model_name=model_name)
        base_pkd = baseline_pred["predicted_pkd"]
        base_kd = baseline_pred["predicted_kd_nM"]

        # Step 2: Generate candidate derivatives
        mode_used = "heuristic_medchem_rules"
        fallback_reason = None
        candidates = []

        if llm_config and llm_config.get("api_key"):
            try:
                candidates = generate_llm_candidates(
                    smiles=drug_smiles,
                    target_name=target_name,
                    baseline_pkd=base_pkd,
                    baseline_kd_nM=base_kd,
                    optimization_goal=optimization_goal,
                    custom_instruction=custom_instruction,
                    llm_config=llm_config
                )
                mode_used = f"llm_generative_{llm_config.get('provider', 'custom')}"
            except Exception as exc:
                fallback_reason = f"大模型接口调用异常: {str(exc)}"
                logger.warning("LLM generation failed (%s), falling back to heuristic medchem rules.", exc)
                candidates = generate_heuristic_candidates(drug_smiles)
                mode_used = "heuristic_fallback"
        else:
            candidates = generate_heuristic_candidates(drug_smiles)

        # Step 3: Quantitative scoring loop
        scored_candidates = []
        for idx, cand in enumerate(candidates):
            c_smiles = cand["smiles"]
            try:
                pred = self.runtime.predict(c_smiles, target_sequence, model_name=model_name)
                c_pkd = pred["predicted_pkd"]
                c_kd = pred["predicted_kd_nM"]
                delta_pkd = round(c_pkd - base_pkd, 3)
                fold_change = round(base_kd / c_kd, 2) if c_kd > 0 else 1.0

                if delta_pkd > 0.1:
                    status = "亲和力显著增强"
                    status_code = "improved"
                elif delta_pkd < -0.1:
                    status = "亲和力有所减弱"
                    status_code = "decreased"
                else:
                    status = "亲和力基本持平"
                    status_code = "neutral"

                sa_info = compute_sa_score(c_smiles)

                scored_candidates.append({
                    "id": f"cand_{idx + 1}",
                    "name": cand["name"],
                    "modification_type": cand["modification_type"],
                    "smiles": c_smiles,
                    "rationale": cand["rationale"],
                    "predicted_pkd": c_pkd,
                    "predicted_kd_nM": c_kd,
                    "delta_pkd": delta_pkd,
                    "fold_change": fold_change,
                    "affinity_tier": pred["affinity_tier"],
                    "affinity_tier_code": pred["affinity_tier_code"],
                    "domain": pred["domain"],
                    "status": status,
                    "status_code": status_code,
                    "sa_score": sa_info["sa_score"],
                    "sa_tier": sa_info["sa_tier"],
                    "sa_label": sa_info["sa_label"],
                    "sa_color": sa_info["sa_color"]
                })
            except Exception as e:
                continue

        # Sort candidates by predicted pKd descending
        scored_candidates.sort(key=lambda x: x["predicted_pkd"], reverse=True)

        best_cand = scored_candidates[0] if scored_candidates else None
        max_gain = round(best_cand["delta_pkd"], 3) if best_cand else 0.0
        base_sa = compute_sa_score(drug_smiles)

        return {
            "mode": mode_used,
            "fallback_reason": fallback_reason,
            "target_name": target_name,
            "model_used": model_name,
            "baseline": {
                "smiles": drug_smiles,
                "predicted_pkd": base_pkd,
                "predicted_kd_nM": base_kd,
                "affinity_tier": baseline_pred["affinity_tier"],
                "affinity_tier_code": baseline_pred["affinity_tier_code"],
                "domain": baseline_pred["domain"],
                "sa_score": base_sa["sa_score"],
                "sa_tier": base_sa["sa_tier"],
                "sa_label": base_sa["sa_label"],
                "sa_color": base_sa["sa_color"]
            },
            "candidates": scored_candidates,
            "summary": {
                "candidates_evaluated": len(scored_candidates),
                "best_candidate": best_cand["name"] if best_cand else "无",
                "max_affinity_gain_pkd": max_gain,
                "best_kd_nM": best_cand["predicted_kd_nM"] if best_cand else base_kd
            }
        }
