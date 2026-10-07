"""Uncertainty-Driven Active Learning & Acquisition Recommendation Engine.

Maps the model's epistemic boundaries and guides wet-lab iterative synthesis
using Bayesian Acquisition Functions (Expected Improvement, UCB, Max Uncertainty)
and Four-Quadrant Exploration-Exploitation categorization.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy.stats import norm

from dti_inference_runtime import DTIInferenceRuntime


@dataclass
class CandidateEvaluation:
    """Evaluation metrics for a candidate small molecule in the active learning loop."""
    smiles: str
    name: str
    mean_pkd: float
    uncertainty_sigma: float
    expected_improvement: float
    ucb_score: float
    quadrant: str                       # "confident_hits", "breakthrough_hypotheses", "epistemic_blindspots", "known_inactives"
    quadrant_label: str
    recommendation_reason: str


@dataclass
class ActiveLearningReport:
    """Comprehensive Active Learning synthesis guidance report."""
    target_name: str
    target_sequence_length: int
    total_evaluated: int
    y_best_reference: float
    confident_hits: List[CandidateEvaluation]
    breakthrough_hypotheses: List[CandidateEvaluation]
    high_information_gain_blindspots: List[CandidateEvaluation]
    known_inactives: List[CandidateEvaluation]

    def export_markdown(self) -> str:
        """Render a publication-grade markdown dispatch summary."""
        lines = []
        lines.append(f"# 主动学习定向验证与高信息增益推荐报告: {self.target_name}")
        lines.append(f"* **评估候选分子总数**: {self.total_evaluated} 个")
        lines.append(f"* **当前最优亲和力基准 ($y^*$)**: {self.y_best_reference:.2f} pKd")
        lines.append("")
        
        lines.append("## 一、高置信度活性领头物清单 (High Confidence Hits - 适合直接体外复核)")
        if not self.confident_hits:
            lines.append("*暂无符合象限条件的候选物。*")
        else:
            lines.append("| 序号 | 分子名称 / 标识 | 预测亲和力 (pKd) | 不确定度 (±σ) | UCB 评分 | 推荐建议 |")
            lines.append("|:---:|:---|:---:|:---:|:---:|:---|")
            for i, c in enumerate(self.confident_hits[:5], 1):
                lines.append(f"| {i} | `{c.name}` | **{c.mean_pkd:.2f}** | ±{c.uncertainty_sigma:.2f} | {c.ucb_score:.2f} | {c.recommendation_reason} |")
        lines.append("")

        lines.append("## 二、高潜力突破假说清单 (High Potential Breakthroughs - 兼具高上限与探索价值)")
        if not self.breakthrough_hypotheses:
            lines.append("*暂无符合象限条件的候选物。*")
        else:
            lines.append("| 序号 | 分子名称 / 标识 | 预测期望 (pKd) | 不确定度 (±σ) | 期望提升 (EI) | 推荐建议 |")
            lines.append("|:---:|:---|:---:|:---:|:---:|:---|")
            for i, c in enumerate(self.breakthrough_hypotheses[:5], 1):
                lines.append(f"| {i} | `{c.name}` | **{c.mean_pkd:.2f}** | ±{c.uncertainty_sigma:.2f} | {c.expected_improvement:.3f} | {c.recommendation_reason} |")
        lines.append("")

        lines.append("## 三、高信息增益认知盲区清单 (Epistemic Blindspots - 优先合成以最大化压缩模型全局不确定度)")
        if not self.high_information_gain_blindspots:
            lines.append("*暂无符合象限条件的候选物。*")
        else:
            lines.append("| 序号 | 分子名称 / 标识 | 预测期望 (pKd) | 不确定度 (±σ) | 认知盲区定位 | 推荐建议 |")
            lines.append("|:---:|:---|:---:|:---:|:---:|:---|")
            for i, c in enumerate(self.high_information_gain_blindspots[:5], 1):
                lines.append(f"| {i} | `{c.name}` | {c.mean_pkd:.2f} | **±{c.uncertainty_sigma:.2f}** | 强化学空间外推 | {c.recommendation_reason} |")
        lines.append("")

        return "\n".join(lines)


def compute_expected_improvement(mu: float, sigma: float, y_best: float, xi: float = 0.05) -> float:
    """Calculate Expected Improvement (EI) acquisition function."""
    if sigma < 1e-6:
        return float(max(0.0, mu - y_best - xi))
    diff = mu - y_best - xi
    z = diff / sigma
    ei = diff * float(norm.cdf(z)) + sigma * float(norm.pdf(z))
    return float(max(0.0, ei))


def evaluate_active_learning_pool(
    target_sequence: str,
    candidate_pool: List[Tuple[str, str]],  # List of (name, smiles)
    target_name: str = "Target_Kinase",
    y_best: float = 7.50,
    beta_ucb: float = 1.96,
    xi_ei: float = 0.05,
    runtime: Optional[DTIInferenceRuntime] = None
) -> ActiveLearningReport:
    """
    Evaluate a candidate pool of small molecules against a target kinase,
    calculating ensemble mean, epistemic variance, acquisition values, and quadrant classification.
    """
    if runtime is None:
        runtime = DTIInferenceRuntime()
    runtime.load()

    clean_seq = "".join(target_sequence.split()).upper()
    evaluated: List[CandidateEvaluation] = []

    # Models used to evaluate ensemble consensus
    eval_models = [m for m in ["worldmodel_stacked_ensemble", "stacked_ensemble", "ridge_alpha10"] if m in runtime.models]
    if not eval_models:
        eval_models = list(runtime.models.keys())[:3]

    for name, smiles in candidate_pool:
        preds = []
        for m_name in eval_models:
            res = runtime.predict(smiles, clean_seq, model_name=m_name)
            preds.append(res["predicted_pkd"])

        mu = float(np.mean(preds))
        # Ensemble variance
        ens_var = float(np.var(preds)) if len(preds) > 1 else 0.04
        
        # Domain distance penalty (epistemic uncertainty increases when out-of-distribution)
        domain, max_d_sim, max_t_sim = runtime.diagnose_domain(smiles, clean_seq)
        dist_penalty = (1.0 - min(max_d_sim, max_t_sim)) ** 2 * 0.15
        
        sigma = float(math.sqrt(ens_var + dist_penalty + 0.02))  # Total uncertainty

        ei = compute_expected_improvement(mu, sigma, y_best=y_best, xi=xi_ei)
        ucb = float(mu + beta_ucb * sigma)

        # Four-Quadrant Categorization
        # Median thresholds: mu >= 7.0 (Kd <= 100 nM), sigma >= 0.35
        is_high_mu = mu >= 7.0
        is_high_sigma = sigma >= 0.35

        if is_high_mu and not is_high_sigma:
            quadrant = "confident_hits"
            q_label = "象限 I: 高置信度活性分子"
            reason = "预测亲和力高且各基线世界模型高度达成一致，推荐立即推进湿实验表征。"
        elif is_high_mu and is_high_sigma:
            quadrant = "breakthrough_hypotheses"
            q_label = "象限 II: 高潜力突破假说"
            reason = "具备突破当前亲和力上限的可能，但存在模型间分歧，具有极高探索价值。"
        elif not is_high_mu and is_high_sigma:
            quadrant = "epistemic_blindspots"
            q_label = "象限 III: 认知盲区高信息增益"
            reason = "处于模型认知边界，合成并测试该类分子将最大化压缩后续迭代不确定度。"
        else:
            quadrant = "known_inactives"
            q_label = "象限 IV: 确定性无效分子"
            reason = "模型一致确定无结合活性，建议直接排除以节约实验成本。"

        evaluated.append(CandidateEvaluation(
            smiles=smiles,
            name=name,
            mean_pkd=round(mu, 3),
            uncertainty_sigma=round(sigma, 3),
            expected_improvement=round(ei, 4),
            ucb_score=round(ucb, 3),
            quadrant=quadrant,
            quadrant_label=q_label,
            recommendation_reason=reason
        ))

    # Split into quadrants and sort by respective priority metric
    hits = sorted([c for c in evaluated if c.quadrant == "confident_hits"], key=lambda x: x.mean_pkd, reverse=True)
    breakthroughs = sorted([c for c in evaluated if c.quadrant == "breakthrough_hypotheses"], key=lambda x: x.expected_improvement, reverse=True)
    blindspots = sorted([c for c in evaluated if c.quadrant == "epistemic_blindspots"], key=lambda x: x.uncertainty_sigma, reverse=True)
    inactives = sorted([c for c in evaluated if c.quadrant == "known_inactives"], key=lambda x: x.mean_pkd)

    return ActiveLearningReport(
        target_name=target_name,
        target_sequence_length=len(clean_seq),
        total_evaluated=len(evaluated),
        y_best_reference=y_best,
        confident_hits=hits,
        breakthrough_hypotheses=breakthroughs,
        high_information_gain_blindspots=blindspots,
        known_inactives=inactives
    )
