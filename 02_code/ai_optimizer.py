"""Exploratory sequence ranking and fixed physicochemical property displays.
No function in this module establishes clinical safety or experimental efficacy.
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
        """Compatibility method name: fixed properties, never model attribution."""
        return [{'pos': i + 1, 'aa': aa, 'hydrophobicity': KYTE_DOOLITTLE[aa],
                 'charge': CHARGE_ESTIMATE.get(aa, 0.),
                 'hydrophobicity_band': 'high' if KYTE_DOOLITTLE[aa] > 2.5 else 'positive' if KYTE_DOOLITTLE[aa] > 0 else 'nonpositive'}
                for i, aa in enumerate(clean_sequence(seq))]

    def optimize_mutations(self, seq: str, top_k: int = 3) -> List[Dict]:
        """
        单点候选搜索；固定概率筛选条件仅用于探索性计算排序。
        """
        cleaned = clean_sequence(seq)
        orig_amp, orig_hemo, orig_tsi = self.evaluate_sequence(cleaned)
        
        # Prespecified substitutions at hydrophobic sites; no mechanistic inference.
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
                
                # Score-only constraints; 0.85 does not mean 85% measured killing.
                if m_amp >= 0.85 and m_hemo < orig_hemo and m_tsi > orig_tsi:
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
                        "hemo_probability_change": round(m_hemo - orig_hemo, 4),
                        "rationale": "该候选仅改善当前模型的计算排序分数；不代表实测降毒、活性保留或膜机制已得到证实。",
                        "validation_status": "exploratory_same_model_scoring"
                    })
                    
        # 按 TSI 收益降序排列
        tested_variants.sort(key=lambda x: x["tsi"], reverse=True)
        return tested_variants[:top_k]

    def generate_scientific_report(self, seq: str) -> Dict:
        """Return measured-source model scores without clinical or mechanistic inference."""
        import hashlib
        cleaned = clean_sequence(seq)
        a, h, score = self.evaluate_sequence(cleaned)
        attrs = self.compute_residue_attributions(cleaned)
        report_id = 'RESEARCH-' + hashlib.sha256(cleaned.encode()).hexdigest()[:12]
        metrics = {'amp_probability': a, 'hemo_probability': h,
                   'ranking_score': score, 'therapeutic_safety_index': score,
                   'net_charge': float(sum(CHARGE_ESTIMATE.get(x, 0.) for x in cleaned)),
                   'mean_hydrophobicity': float(np.mean([KYTE_DOOLITTLE[x] for x in cleaned])),
                   'high_hydrophobicity_residue_count': sum(x['hydrophobicity_band']=='high' for x in attrs),
                   'positive_hydrophobicity_residue_count': sum(x['hydrophobicity_band']=='positive' for x in attrs),
                   'nonpositive_hydrophobicity_residue_count': sum(x['hydrophobicity_band']=='nonpositive' for x in attrs)}
        text = (f'# Computational research report {report_id}\n\n'
                f'AMP endpoint score: {a:.6f}\nHemolysis endpoint score: {h:.6f}\n'
                f'Exploratory ranking score: {score:.6f}\n\n'
                'Scores refer to the declared model endpoints, not measured killing rates, '
                'clinical safety, therapeutic windows, or mechanisms. Residue coloring is '
                'a fixed physicochemical heuristic, not model gradient attribution. '
                'No laboratory experiment was performed by this service. '
                'Same-model candidate scoring is not independent validation.')
        return {'report_id': report_id, 'protocol_version': 'research-v1',
                'sequence': cleaned, 'length': len(cleaned), 'metrics': metrics,
                'clinical_tier': 'Not clinically validated', 'tier_code': 'Research-only',
                'disposition': '计算结果待独立验证', 'disposition_badge': 'warning',
                'mechanism_model': 'Not established',
                'mechanism_deduction': '理化提示不能证明膜作用机制或临床安全性。',
                'residue_attributions': attrs, 'attribution_type': 'physicochemical_heuristic',
                'ai_mutation_solutions': [], 'standard_markdown_report': text}


if __name__ == '__main__':
    import os
    from inference_runtime import ResearchRuntime
    runtime = ResearchRuntime(os.environ.get('SAFEAMP_RUN_DIR')).load()
    optimizer = AIPeptideOptimizer(runtime, runtime.extractor)
    print(optimizer.generate_scientific_report('GIGAVLKVLTTGLPALISWIKRKRQQ')['standard_markdown_report'])
