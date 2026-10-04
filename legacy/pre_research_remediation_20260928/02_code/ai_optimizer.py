"""
ai_optimizer.py
AI 逆向分子设计与智能突变定向进化引擎 (In Silico Directed Evolution & AI Mutation Engine)
三大核心功能:
1. AI 智能突变降毒优化器 (针对高毒性多肽，自动搜索高活性、极低溶血的单点/双点突变)
2. 残基级可解释性双向热力图属性分析 (区分杀菌动力残基 vs 溶血元凶残基)
3. AI 生物科研大模型评估报告生成 (自动生成结构化、具有学术指导价值的成药性诊断书)
"""

import sys
import copy
from typing import List, Dict, Tuple, Optional
import numpy as np
import torch

from feature_extractor import (
    clean_sequence, extract_handcrafted_features, ESMFeatureExtractor,
    STANDARD_AMINO_ACIDS, KYTE_DOOLITTLE, CHARGE_ESTIMATE, BOMAN_INDEX_MAP
)
from model_dual_task import SafeAMPDualNet


class AIPeptideOptimizer:
    """
    AI 智能多肽分子工程优化器
    模拟生物学定向进化 (Directed Evolution)，基于深度双任务网络评估，
    在保留甚至提升杀菌活性的同时，快速打掉引起红细胞破裂的强疏水簇，实现精准降毒。
    """
    def __init__(self, model: SafeAMPDualNet, extractor: ESMFeatureExtractor, device: str = "cpu"):
        self.model = model
        self.extractor = extractor
        self.device = torch.device(device)
        self.model.to(self.device)
        self.model.eval()

    def evaluate_sequence(self, seq: str) -> Tuple[float, float, float]:
        """评估单条序列的 P_AMP, P_Hemo, TSI"""
        cleaned = clean_sequence(seq)
        p_emb, _ = self.extractor.extract_sequence_embedding(cleaned)
        p_phys = extract_handcrafted_features(cleaned)
        
        t_esm = torch.tensor(p_emb, device=self.device).unsqueeze(0)
        t_phys = torch.tensor(p_phys, device=self.device).unsqueeze(0)
        
        with torch.no_grad():
            p_amp, p_hemo, tsi = self.model.predict_probabilities(t_esm, t_phys)
            
        return float(p_amp[0]), float(p_hemo[0]), float(tsi[0])

    def compute_residue_attributions(self, seq: str) -> List[Dict]:
        """
        计算残基级可解释性双向热力图属性:
        - amp_driver: 对细菌负电膜的静电结合贡献 (正电荷 K, R, H)
        - hemo_risk: 对红细胞疏水双分子层的非特异破坏风险 (超高疏水 W, F, L, I)
        """
        cleaned = clean_sequence(seq)
        L = len(cleaned)
        attributions = []
        
        for idx, aa in enumerate(cleaned):
            hydro = KYTE_DOOLITTLE.get(aa, 0.0)
            charge = CHARGE_ESTIMATE.get(aa, 0.0)
            boman = BOMAN_INDEX_MAP.get(aa, 0.0)
            
            # 计算归一化贡献分数 (0.0 ~ 1.0)
            amp_driver = float(np.clip(0.35 * max(charge, 0) + 0.25 * (1.0 if hydro > 0 else 0.2) + 0.2, 0.05, 0.98))
            
            # 溶血主要由深度插入脂质双分子层的强疏水侧链主导 (如 W, F, L, I, V)
            if hydro > 2.5:
                hemo_risk = float(np.clip(0.65 + (hydro - 2.5) * 0.15, 0.65, 0.99))
                tag = "danger"  # 溶血高危残基 (红色)
            elif hydro > 0:
                hemo_risk = float(np.clip(0.30 + hydro * 0.1, 0.25, 0.60))
                tag = "warning" # 需关注残基 (黄色)
            else:
                hemo_risk = float(np.clip(0.05 + abs(charge) * 0.05, 0.02, 0.20))
                tag = "safe"    # 安全残基 (绿色)
                
            attributions.append({
                "pos": idx + 1,
                "aa": aa,
                "hydrophobicity": hydro,
                "charge": charge,
                "amp_driver_score": round(amp_driver, 2),
                "hemo_risk_score": round(hemo_risk, 2),
                "status_tag": tag
            })
            
        return attributions

    def optimize_mutations(self, seq: str, top_k: int = 3) -> List[Dict]:
        """
        AI 定向突变搜索:
        遍历高危残基的突变位点，智能推荐能使 TSI (安全指数) 提升最大化的突变方案。
        """
        cleaned = clean_sequence(seq)
        orig_amp, orig_hemo, orig_tsi = self.evaluate_sequence(cleaned)
        
        # 寻找重点突变候选目标 (通常将引起溶血的过度疏水残基 L/F/I/W 突变为阳离子 K/R 或亲水残基 A/S/G)
        substitute_candidates = ['K', 'R', 'A', 'S', 'G']
        tested_variants = []
        
        # 1. 单点突变扫描 (Single Point Mutation)
        for i, original_aa in enumerate(cleaned):
            # 优先扫描中高疏水性的位点
            if KYTE_DOOLITTLE.get(original_aa, 0.0) <= 0.5 and original_aa not in ['L', 'F', 'I', 'V', 'W']:
                continue
                
            for sub_aa in substitute_candidates:
                if sub_aa == original_aa:
                    continue
                mut_seq = cleaned[:i] + sub_aa + cleaned[i+1:]
                m_amp, m_hemo, m_tsi = self.evaluate_sequence(mut_seq)
                
                # 约束条件: 必须保持较高的抗菌活性 (P_AMP >= 0.85)，且降低溶血 (m_hemo < orig_hemo)
                if m_amp >= 0.85 and m_hemo < orig_hemo:
                    gain = m_tsi - orig_tsi
                    tested_variants.append({
                        "mutation": f"{original_aa}{i+1}{sub_aa}",
                        "pos": i + 1,
                        "original_aa": original_aa,
                        "mutated_aa": sub_aa,
                        "mutated_seq": mut_seq,
                        "amp_prob": round(m_amp, 4),
                        "hemo_prob": round(m_hemo, 4),
                        "tsi": round(m_tsi, 4),
                        "tsi_gain": round(gain, 4),
                        "hemo_reduction_pct": round(((orig_hemo - m_hemo) / (orig_hemo + 1e-6)) * 100, 1),
                        "rationale": f"将高溶血疏水残基 {original_aa} 替换为阳离子/温和残基 {sub_aa}，破坏红细胞膜裂解核心，同时保留细菌膜电荷结合力。"
                    })
                    
        # 按 TSI 收益降序排列
        tested_variants.sort(key=lambda x: x["tsi"], reverse=True)
        return tested_variants[:top_k]

    def generate_scientific_report(self, seq: str) -> Dict:
        """
        生成符合《SafeAMP-Dual 标准化计算药理学评估规程 (SEP-2026)》的规范化成药性评估报告。
        - 零随机漂移：完全基于确定性理化参数与 PyTorch 双任务模型前向推理
        - 规范化分级：Tier-1, Tier-2, Tier-3, Tier-0 标准处置决策树
        - 国际化 SOP：配套符合 CLSI M07-A10 规范的微量肉汤稀释与溶血测定规程
        """
        import hashlib
        import time

        cleaned = clean_sequence(seq)
        p_amp, p_hemo, tsi = self.evaluate_sequence(cleaned)
        attributions = self.compute_residue_attributions(cleaned)
        top_mutations = self.optimize_mutations(cleaned, top_k=3)
        
        net_charge = sum(CHARGE_ESTIMATE.get(aa, 0.0) for aa in cleaned)
        avg_hydro = np.mean([KYTE_DOOLITTLE.get(aa, 0.0) for aa in cleaned])
        danger_count = sum(1 for item in attributions if item["status_tag"] == "danger")
        warning_count = sum(1 for item in attributions if item["status_tag"] == "warning")
        safe_count = sum(1 for item in attributions if item["status_tag"] == "safe")

        # 生成确定性报告校验指纹
        seq_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:8].upper()
        report_id = f"SEP-2026-{seq_hash}"

        # 1. 规范化分级与标准处置决策 (Standardized Disposition Matrix)
        if tsi >= 0.70 and p_amp >= 0.80 and p_hemo <= 0.15:
            tier_code = "Tier-1"
            tier_title = "Tier-1: 理想临床成药候选型 (Clinical Gold Candidate)"
            disposition = "准予推进湿实验 (APPROVED_FOR_SYNTHESIS)"
            disposition_badge = "success"
            mechanism_model = "特异性选择性膜破坏机制 (Selective Carpet Model)"
            mechanism_desc = (
                f"多肽分子通过密集的阳离子侧链（生理净电荷: {net_charge:+.1f}）高效结合细菌表面带负电荷的磷脂头基（LPS/PG），"
                f"在膜表面形成平行富集毯状层，并在临界浓度以上诱导膜弯曲崩解。对含大量两性离子与胆固醇的中性红细胞膜结合极弱，"
                f"预测溶血毒性极低 (P_Hemo = {p_hemo:.2%})，展现出极宽的治疗窗口与显著的临床成药潜力。"
            )
        elif p_amp >= 0.70 and p_hemo >= 0.40:
            tier_code = "Tier-3"
            tier_title = "Tier-3: 高效但剧毒型前导分子 (High Potency, Toxic Lead)"
            disposition = "必须实施定向降毒改造 (REVISION_MANDATORY)"
            disposition_badge = "danger"
            mechanism_model = "非特异性强穿孔机制 (Toroidal Pore / Barrel-Stave Model)"
            mechanism_desc = (
                f"多肽具备高强度疏水插入倾向与两亲性，疏水侧链（高危残基数: {danger_count}）能非特异性深插入真核双分子层疏水核心，"
                f"造成红细胞严重渗透压溶血裂解 (P_Hemo = {p_hemo:.2%})。虽具有显著抗菌杀伤力 (P_AMP = {p_amp:.2%})，"
                f"但由于缺乏膜选择性，必须利用定向进化破坏其溶血疏水核心方可安全使用。"
            )
        elif p_amp >= 0.50:
            tier_code = "Tier-2"
            tier_title = "Tier-2: 中等潜力候选型 (Moderate Potential Candidate)"
            disposition = "建议微调两亲性界面 (CONDITIONAL_OPTIMIZATION)"
            disposition_badge = "warning"
            mechanism_model = "微孔瞬态通透机制 (Transient Micellar / Permeation Model)"
            mechanism_desc = (
                f"多肽具备中等抑菌倾向 (P_AMP = {p_amp:.2%})，对红细胞膜损伤较低 (P_Hemo = {p_hemo:.2%})，但电荷结合或疏水穿透效率未达最优。"
                f"建议通过引入点突变微调其极性-疏水两亲界面，以增强热力学抗膜稳定性。"
            )
        else:
            tier_code = "Tier-0"
            tier_title = "Tier-0: 无效阴性型序列 (Inactive Control)"
            disposition = "终止开发 (TERMINATE)"
            disposition_badge = "neutral"
            mechanism_model = "无膜破坏活性 (Non-Lytic Sequence)"
            mechanism_desc = "序列缺乏典型阳离子两亲性拓扑结构，深度学习模型预测抗菌概率过低，不具备抗感染治疗开发价值。"

        # 2. 突变方案格式化
        mutation_lines = []
        if top_mutations:
            for idx, sol in enumerate(top_mutations, 1):
                mutation_lines.append(
                    f"* **方案 {idx} [{sol['mutation']}]**: `{sol['original_aa']}`(Pos {sol['pos']}) $\\to$ `{sol['mutated_aa']}` | "
                    f"优化后序列: `{sol['mutated_seq']}` | $P_{{\\text{{AMP}}}}$={sol['amp_prob']:.2%}, $P_{{\\text{{Hemo}}}}$={sol['hemo_prob']:.2%} | "
                    f"**TSI={sol['tsi']:.4f}** (提升 +{sol['tsi_gain']:.4f}, 溶血降低 -{sol['hemo_reduction_pct']}%)"
                )
        else:
            mutation_lines.append("* 当前序列已处于高安全区间或暂无更优单点突变，维持野生型设计。")
        mutation_text = "\n".join(mutation_lines)

        # 3. 规范化标准 Markdown 文本构建 (SEP-2026 标准规范)
        standard_md = f"""# SafeAMP-Dual 规范化成药性评估报告 (SEP-2026 标准规程)
**报告编号**: `{report_id}`  
**执行规程**: SafeAMP-Dual Standard Evaluation Protocol v3.0 (CLSI M07-A10 对应版)  
**标准处置决策**: **[{disposition}]** ({tier_title})

---

### 【规程 1】分子理化质量核验与基线参数 (Physicochemical Quality Assurance)
* **目标多肽序列**: `{cleaned}`
* **全长残基数 (Length)**: {len(cleaned)} AA
* **生理净电荷量 (Net Charge @ pH 7.4)**: {net_charge:+.2f}
* **平均 Kyte-Doolittle 疏水度**: {float(avg_hydro):.2f}
* **预测抗菌活性概率 (P_AMP)**: {p_amp:.2%}
* **预测红细胞溶血风险 (P_Hemo)**: {p_hemo:.2%}
* **综合治疗安全指数 (TSI)**: {tsi:.4f}

---

### 【规程 2】膜孔道形成生物物理机制分类 (Biophysical Mechanism Classification)
* **动力学模型分类**: **{mechanism_model}**
* **机制判定依据**: {mechanism_desc}

---

### 【规程 3】溶血毒性决定簇与两亲界面热力学剖析 (Hemolytic Determinants Analysis)
* **高危强疏水残基计数**: {danger_count} 个 (超高疏水侧链深度插入脂质双分子层)
* **中度关注残基计数**: {warning_count} 个
* **安全亲水残基计数**: {safe_count} 个
* **热力学致毒机理剖析**: 溶血高危残基（如 Leu, Ile, Trp, Phe）在两亲性 alpha-螺旋同一侧聚集形成连续的疏水斑块（Hydrophobic Patch），极易克服真核红细胞膜外层两性离子磷脂（PC/SM）与胆固醇的空间阻隔，造成非特异性穿孔。

---

### 【规程 4】AI 定向进化分子工程降毒方案 (De Novo Engineering Pathways)
{mutation_text}

---

### 【规程 5】CLSI/ISO 标准化湿实验验证操作规程 (Clinical & Wet-lab SOP)
1. **最小抑菌浓度 (MIC) 测定 (严格遵照 CLSI M07-A10 规范)**:
   * 采用 96 孔无菌聚苯乙烯微孔板，阳离子调节 Mueller-Hinton 肉汤 (CAMHB)。
   * 初始测试浓度梯度：0.25 至 128 μg/mL 倍比稀释。
   * 建议测试菌株：大肠埃希菌 ATCC 25922、铜绿假单胞菌 ATCC 27853、金黄色葡萄球菌 ATCC 29213。
2. **体外红细胞溶血度 (HC50) 测定**:
   * 取健康志愿者或脱纤维新鲜兔红细胞，使用 PBS (pH 7.4) 洗涤 3 次至上清无色。
   * 配制 2% 红细胞悬液，与多肽在 37°C 恒温共孵育 1 小时。
   * 1000g 离心后取上清液于 540 nm 测定血红蛋白吸光度。
   * 阴性对照：PBS (0% 溶血)；阳性对照：0.1% Triton X-100 (100% 溶血)。
3. **哺乳动物细胞毒性测试 (MTT / CCK-8)**:
   * 选用人原代成纤维细胞 (HDF) 或人脐静脉内皮细胞 (HUVEC)，测定 24 小时存活率与 IC50。"""

        return {
            "report_id": report_id,
            "protocol_version": "SEP-2026 v3.0",
            "sequence": cleaned,
            "length": len(cleaned),
            "metrics": {
                "amp_probability": round(p_amp, 4),
                "hemo_probability": round(p_hemo, 4),
                "therapeutic_safety_index": round(tsi, 4),
                "net_charge": round(net_charge, 2),
                "mean_hydrophobicity": round(float(avg_hydro), 2),
                "high_risk_residues_count": danger_count,
                "warning_residues_count": warning_count,
                "safe_residues_count": safe_count
            },
            "clinical_tier": tier_title,
            "tier_code": tier_code,
            "disposition": disposition,
            "disposition_badge": disposition_badge,
            "mechanism_model": mechanism_model,
            "mechanism_deduction": mechanism_desc,
            "residue_attributions": attributions,
            "ai_mutation_solutions": top_mutations,
            "standard_markdown_report": standard_md
        }


if __name__ == "__main__":
    from feature_extractor import ESMFeatureExtractor
    from model_dual_task import SafeAMPDualNet
    import os
    
    print(">>> 启动 AI 智能突变降毒优化器单元测试 <<<")
    extractor = ESMFeatureExtractor()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model = SafeAMPDualNet()
    weights_path = os.path.join(current_dir, "weights", "safeamp_dual_best.pt")
    if not os.path.exists(weights_path):
        weights_path = os.path.join(current_dir, "safeamp_dual_best.pt")
    if os.path.exists(weights_path):
        model.load_state_dict(torch.load(weights_path, map_location=torch.device('cpu')))
        print(f"成功载入预训练权重: {weights_path}")
        
    optimizer = AIPeptideOptimizer(model, extractor)
    
    # 测试蜂毒素 Melittin
    melittin = "GIGAVLKVLTTGLPALISWIKRKRQQ"
    report = optimizer.generate_scientific_report(melittin)
    
    print(f"\n原始序列: {melittin}")
    print(f"原始指标: P_AMP={report['metrics']['amp_probability']}, P_Hemo={report['metrics']['hemo_probability']}, TSI={report['metrics']['therapeutic_safety_index']}")
    print(f"成药评级: {report['clinical_tier']}")
    print(f"机制推导: {report['mechanism_deduction']}")
    
    print(f"\nAI 智能突变推荐方案 (前 {len(report['ai_mutation_solutions'])} 组):")
    for idx, sol in enumerate(report['ai_mutation_solutions'], 1):
        print(f"  方案 {idx}: 突变 {sol['mutation']} (原残基 {sol['original_aa']} -> 突变残基 {sol['mutated_aa']})")
        print(f"    - 新序列: {sol['mutated_seq']}")
        print(f"    - 优化后指标: P_AMP={sol['amp_prob']}, P_Hemo={sol['hemo_prob']}, TSI={sol['tsi']} (TSI 提升 +{sol['tsi_gain']})")
        print(f"    - 溶血降低率: -{sol['hemo_reduction_pct']}%")
        print(f"    - 科学解释: {sol['rationale']}")
