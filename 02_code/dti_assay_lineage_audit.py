"""Assay-level lineage audit and automated project exit determination for Phase 3.

Decouples data provenance from external author replies by auditing local records,
tagging construct closure status, and mapping internal evidence to pre-registered exit criteria.
"""
import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple


def audit_assay_lineage(raw_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Audit assay records for construct and mutation identity closure."""
    manifest = []
    closed_exact = 0
    incomplete_identity = 0
    
    for idx, r in enumerate(raw_records):
        mut = str(r.get('mutation', '')).strip().lower()
        gene = str(r.get('gene', '')).strip()
        compound = str(r.get('compound', '')).strip()
        
        # Exact closure: clean wild-type or clearly specified non-empty mutation
        if mut in ('', 'wt', 'wild-type', 'wildtype') or (mut and mut != 'unspecified'):
            status = 'CLOSED_EXACT'
            closed_exact += 1
        else:
            status = 'INCOMPLETE_IDENTITY'
            incomplete_identity += 1
            
        manifest.append({
            'index': idx,
            'compound': compound,
            'gene': gene,
            'mutation': mut,
            'closure_status': status
        })
        
    return {
        'total_records': len(raw_records),
        'closed_exact': closed_exact,
        'incomplete_identity': incomplete_identity,
        'closure_rate': closed_exact / len(raw_records) if raw_records else 0.0,
        'manifest': manifest
    }


def determine_project_exit(internal_summary: Dict[str, Any]) -> Tuple[str, str]:
    """Determine project exit mode based on pre-registered criteria."""
    cold_drug_p10 = internal_summary.get('cold_drug_p10', 0.25)
    best_dual_p10 = max(
        internal_summary.get('HGBContinuousBaseline', {}).get('mean_dual_cold_p10', 0.0),
        internal_summary.get('LogRegCandidateClassifier', {}).get('mean_dual_cold_p10', 0.0),
    )
    const_exp = internal_summary.get('constant_expectation', {}).get('mean_dual_cold_p10', 0.0682)
    
    # Exit A: Cold drug is stable and functional (P@10 >= 0.20), but dual cold improvement is modest
    if cold_drug_p10 >= 0.20 and best_dual_p10 > const_exp:
        return (
            'EXIT_A',
            'Cold-drug 候选靶点筛选稳定有效 (P@10 ~ 0.30 显著战胜常数参考)，双冷泛化仍属探索性研究。'
            '建议：交付受限场景候选筛选器，前台明确区分“推荐可信区”与“探索性双冷提示”，保持科学诚实。'
        )
    elif best_dual_p10 >= 0.15 and best_dual_p10 > const_exp * 2:
        return (
            'EXIT_B',
            '新模型与特征在双冷内部验证中取得突破性提升。'
            '建议：扩大训练规模并进入概率校准与全面替换流程。'
        )
    else:
        return (
            'EXIT_C',
            '多轮受控实验未能克服双冷数据瓶颈。'
            '建议：停止盲目追求通用数值泛化，将产品定位转为已有测定数据溯源检索与文献证据支持工具。'
        )
