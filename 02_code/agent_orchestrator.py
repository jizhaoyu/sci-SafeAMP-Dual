"""Antigravity A2A Multi-Agent Orchestrator with Hard Constraint Steering & Control Protocol.

Implements a state-graph multi-agent autonomous optimization loop:
- SupervisorNode: Global strategy, stopping criteria, dynamic routing & convergence check
- MolecularDesignerNode: MedChem mutations, bioisostere swaps, peptide variants
- DTIAuditorNode: Gated affinity predictions (ESM2/Bilinear/Ridge)
- SafetyAuditorNode: ADMET profiling, cytotoxicity & hemolysis assessment
- HardConstraintGate: Programmatic verification of MW, motifs, pKd, SA (rejects non-compliant)
- WetlabReporterNode: Final Pareto frontier, evidence pack, 96-well dispatch
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import sys
from typing import Any, AsyncGenerator, Dict, List, Optional, TypedDict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_code"))

from dti_inference_runtime import DTIInferenceRuntime
from dti_lead_optimizer import DTILeadOptimizer, MEDCHEM_RULES
from admet_predictor import predict_admet_properties
from synthetic_accessibility import compute_sa_score
from agent_constraints import (
    AgentHardConstraints, 
    UnsupportedConstraintError, 
    InvalidConstraintUpdateError,
    AgentCheckpoint
)

logger = logging.getLogger("agent_orchestrator")


class CandidateRecord(TypedDict):
    id: str
    generation: int
    molecule_type: str        # "small_molecule" | "peptide"
    smiles: str
    target_symbol: str
    predicted_pkd: float
    predicted_kd_nM: float
    confidence_band: str
    sa_score: float           # Synthetic Accessibility (1-10)
    solubility_logs: float
    solubility_tier: str
    caco2_tier: str
    log_bb: float
    bbb_tier: str
    admet_score: float        # Holistic ADMET health score (0-100)
    hemolysis_risk_pct: float
    hemolysis_provenance: str # "heuristic_estimate"
    hemolysis_note: str
    modifications: str
    rationale: str
    parent_id: Optional[str]
    timestamp: str
    passed_hard_constraints: bool
    constraint_failure_reason: Optional[str]


class AgentState(TypedDict):
    task_id: str
    scenario: str             # "kinase_escape" | "safeamp_evolution" | "custom"
    user_goal: str
    target_symbol: str
    target_sequence: str
    baseline_smiles: str
    current_agent: str
    iteration: int
    max_iterations: int
    target_pkd: float
    min_admet_score: float
    max_hemolysis_pct: float
    constraints_version: int
    constraints: Dict[str, Any]
    candidates: List[CandidateRecord]
    current_best: Optional[CandidateRecord]
    pareto_frontier: List[CandidateRecord]
    step_count: int
    is_converged: bool
    final_verdict: Optional[Dict[str, Any]]
    checkpoints: List[Dict[str, Any]]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Global lazy runtime singleton
_runtime: Optional[DTIInferenceRuntime] = None

def get_runtime() -> DTIInferenceRuntime:
    global _runtime
    if _runtime is None:
        _runtime = DTIInferenceRuntime()
        _runtime.load()
    return _runtime


class MultiAgentOrchestrator:
    """Multi-Agent State Graph Engine with Real-Time SSE Event Broadcasting and Interactive Steering."""

    def __init__(
        self, 
        runtime: Optional[DTIInferenceRuntime] = None,
        initial_constraints: Optional[AgentHardConstraints] = None,
        llm_mode: str = "heuristic_only",
        llm_config: Optional[Dict[str, Any]] = None
    ):
        self.runtime = runtime or get_runtime()
        self.lead_optimizer = DTILeadOptimizer(self.runtime)
        self.constraints = initial_constraints or AgentHardConstraints()
        self.llm_mode = llm_mode or "heuristic_only"
        self.llm_config = llm_config or {}
        
        # Interactive steering control states
        self.pause_requested = False
        self.is_paused = False
        self.cancellation_requested = False
        self.current_state: Optional[AgentState] = None
        self.checkpoints: List[AgentCheckpoint] = []
        self.persisted_checkpoint_count = 0

    def pause(self) -> None:
        """Requests the pipeline to pause at the nearest iteration/candidate boundary."""
        self.pause_requested = True

    def resume(self) -> None:
        """Resumes pipeline execution after a confirmed pause."""
        self.is_paused = False
        self.pause_requested = False

    def cancel(self) -> None:
        """Requests cancellation of the active multi-agent pipeline."""
        self.cancellation_requested = True

    def update_constraints(self, new_constraints_data: Dict[str, Any], expected_version: int) -> AgentHardConstraints:
        """
        Updates hard constraints during confirmed pause state.
        Validates against version collision and programmatic support.
        Re-evaluates current parent/best against new constraints.
        """
        if not self.is_paused:
            raise InvalidConstraintUpdateError("只能在流水线处于已确认暂停状态下更新硬约束")

        if expected_version != self.constraints.version:
            raise InvalidConstraintUpdateError(
                f"约束版本冲突: 提交预期版本 {expected_version} 与当前版本 {self.constraints.version} 不符"
            )

        new_constraints = AgentHardConstraints.from_dict(new_constraints_data, current_version=self.constraints.version)
        self.constraints = new_constraints

        # Re-verify current_best against the new constraint version
        if self.current_state and self.current_state.get("current_best"):
            curr = self.current_state["current_best"]
            passed, reason = self.constraints.validate_candidate(
                curr["smiles"],
                predicted_pkd=curr["predicted_pkd"],
                hemolysis_risk_pct=curr["hemolysis_risk_pct"],
                sa_score=curr["sa_score"]
            )
            if not passed:
                logger.warning(
                    f"当前最优候选 {curr['id']} 不满足新约束: {reason}。正在回溯历史最佳合规候选作为新母体..."
                )
                fallback = None
                # Search past candidates for a compliant molecule
                for c in sorted(self.current_state["candidates"], key=lambda x: x["predicted_pkd"], reverse=True):
                    c_pass, _ = self.constraints.validate_candidate(
                        c["smiles"],
                        predicted_pkd=c["predicted_pkd"],
                        hemolysis_risk_pct=c["hemolysis_risk_pct"],
                        sa_score=c["sa_score"]
                    )
                    if c_pass:
                        fallback = c
                        break
                if fallback:
                    self.current_state["current_best"] = fallback
                    logger.info(f"已回退至符合新约束的历史母体: {fallback['id']}")

        return self.constraints

    def evaluate_molecule(
        self, 
        smiles: str, 
        target_sequence: str, 
        target_symbol: str,
        gen: int,
        modifications: str = "Baseline",
        rationale: str = "Initial baseline molecule",
        parent_id: Optional[str] = None
    ) -> CandidateRecord:
        """Evaluate a molecule through DTI affinity gate, ADMET safety models, and hard constraint check."""
        pred = self.runtime.predict(smiles, target_sequence)
        admet = predict_admet_properties(smiles)
        sa_res = compute_sa_score(smiles)

        # Estimate hemolysis risk from basic amines & solubility heuristics
        basic_sites = len(re.findall(r'N(?=[A-Z0-9])', smiles))
        calc_hemolysis = max(0.5, min(35.0, (basic_sites * 1.8) - (admet.solubility_logs * 1.5)))

        cid = f"GEN{gen}_{abs(hash(smiles)) % 100000:05d}"
        
        # Hard constraint gate evaluation
        passed_hard, failure_reason = self.constraints.validate_candidate(
            smiles=smiles,
            predicted_pkd=float(pred["predicted_pkd"]),
            hemolysis_risk_pct=round(calc_hemolysis, 2),
            sa_score=float(sa_res.sa_score)
        )

        return {
            "id": cid,
            "generation": gen,
            "molecule_type": "small_molecule",
            "smiles": smiles,
            "target_symbol": target_symbol,
            "predicted_pkd": float(pred["predicted_pkd"]),
            "predicted_kd_nM": float(pred["predicted_kd_nM"]),
            "confidence_band": str(pred.get("confidence_band", "High")),
            "sa_score": float(sa_res.sa_score),
            "solubility_logs": float(admet.solubility_logs),
            "solubility_tier": admet.solubility_tier,
            "caco2_tier": admet.caco2_tier,
            "log_bb": float(admet.log_bb),
            "bbb_tier": admet.bbb_tier,
            "admet_score": float(admet.admet_health_score),
            "hemolysis_risk_pct": round(calc_hemolysis, 2),
            "hemolysis_provenance": "heuristic_estimate",
            "hemolysis_note": "基于脂水分配与碱性位点经验启发的未校准粗略估计，不得作为体外实验溶血率或安全性放行证据",
            "modifications": modifications,
            "rationale": rationale,
            "parent_id": parent_id,
            "timestamp": utc_now_iso(),
            "passed_hard_constraints": passed_hard,
            "constraint_failure_reason": failure_reason,
        }

    async def run_pipeline_stream(
        self, 
        initial_state: AgentState
    ) -> AsyncGenerator[str, None]:
        """Main asynchronous multi-agent generator yielding SSE formatted events with steering checkpoints."""
        self.current_state = initial_state
        state = initial_state
        state.setdefault("generation_audit", [])
        task_id = state["task_id"]

        def sse(event_type: str, data: Dict[str, Any]) -> str:
            payload = json.dumps({"event": event_type, "task_id": task_id, "timestamp": utc_now_iso(), **data}, ensure_ascii=False)
            return f"event: {event_type}\ndata: {payload}\n\n"

        # Check early cancellation
        if self.cancellation_requested:
            yield sse("task_cancelled", {"message": "任务在启动前已被请求取消"})
            return

        # 1. Pipeline Initialized
        yield sse("init", {
            "message": f"多智能体协同流水线已就绪。目标: {state['user_goal']}",
            "scenario": state["scenario"],
            "target_symbol": state["target_symbol"],
            "max_iterations": state["max_iterations"],
            "constraints_version": self.constraints.version,
            "constraints": self.constraints.to_dict()
        })
        await asyncio.sleep(0.15)

        # 2. Evaluate Baseline
        yield sse("agent_thought", {
            "agent": "supervisor",
            "thought": f"首先激活基线测评：正在分析原始分子在靶点 {state['target_symbol']} 催化域的亲和力与 ADMET 药代基线..."
        })
        await asyncio.sleep(0.2)

        baseline_cand = self.evaluate_molecule(
            smiles=state["baseline_smiles"],
            target_sequence=state["target_sequence"],
            target_symbol=state["target_symbol"],
            gen=0,
            modifications="原始先导化合物 (Baseline)",
            rationale="启动基线对照测定"
        )
        state["candidates"].append(baseline_cand)
        state["current_best"] = baseline_cand
        state["pareto_frontier"] = [baseline_cand]

        yield sse("candidate_evaluated", {
            "agent": "dti_auditor",
            "candidate": baseline_cand,
            "is_best": True,
            "passed_hard_constraints": baseline_cand["passed_hard_constraints"],
            "constraint_failure_reason": baseline_cand["constraint_failure_reason"]
        })
        await asyncio.sleep(0.2)

        # 3. Autonomous Optimization Loop with Steering Checkpoints
        while state["iteration"] < state["max_iterations"] and not state["is_converged"] and state["step_count"] < 15:
            # Check cancellation
            if self.cancellation_requested:
                yield sse("task_cancelled", {
                    "iteration": state["iteration"],
                    "message": "用户主动终止了协同流水线"
                })
                return

            # Check pause request
            if self.pause_requested:
                self.is_paused = True
                yield sse("agent_paused", {
                    "iteration": state["iteration"],
                    "constraints_version": self.constraints.version,
                    "constraints": self.constraints.to_dict(),
                    "current_best": state["current_best"],
                    "message": "流水线已确认暂停，当前等待人工指令与硬约束更新"
                })

                while self.is_paused and not self.cancellation_requested:
                    await asyncio.sleep(0.2)

                if self.cancellation_requested:
                    yield sse("task_cancelled", {
                        "iteration": state["iteration"],
                        "message": "暂停期间用户主动终止了协同流水线"
                    })
                    return

                yield sse("agent_resumed", {
                    "iteration": state["iteration"],
                    "constraints_version": self.constraints.version,
                    "constraints": self.constraints.to_dict(),
                    "current_best": state["current_best"],
                    "message": "流水线已恢复执行，已应用最新硬约束门禁"
                })

            state["iteration"] += 1
            state["step_count"] += 1
            gen = state["iteration"]

            # --- Node 1: Supervisor ---
            state["current_agent"] = "supervisor"
            best_pkd = state["current_best"]["predicted_pkd"] if state["current_best"] else 0.0
            gap = max(0.0, state["target_pkd"] - best_pkd)
            
            yield sse("agent_thought", {
                "agent": "supervisor",
                "iteration": gen,
                "thought": (
                    f"【第 {gen}/{state['max_iterations']} 轮推演】当前最优 pKd={best_pkd:.3f}（目标 ≥ {state['target_pkd']}），"
                    f"亲和力差额 ΔpKd={gap:.3f}。约束版本: v{self.constraints.version}。正在唤起 MolecularDesigner 智能体生成针对性结构优化候选群..."
                )
            })
            await asyncio.sleep(0.25)

            # --- Node 2: Molecular Designer ---
            state["current_agent"] = "designer"
            parent_smiles = state["current_best"]["smiles"] if state["current_best"] else state["baseline_smiles"]
            
            yield sse("agent_thought", {
                "agent": "designer",
                "iteration": gen,
                "thought": f"基于最优母核 {state['current_best']['id'] if state['current_best'] else 'Baseline'} 检索电子等排体与药物化学变换规则库（含氟代扫描、变构疏水口袋填充、吗啉环增溶微调）..."
            })
            await asyncio.sleep(0.25)

            # Generate candidate variations based on llm_mode
            mutated_specs = []
            effective_mode = state.get("llm_mode") or self.llm_mode
            if effective_mode == "offline_mock":
                mutated_specs = [
                    {
                        "smiles": parent_smiles + "(F)",
                        "rule_name": "Offline Mock: 氟代电子等排体",
                        "rationale": "离线模拟候选，不来自实际大模型调用"
                    },
                    {
                        "smiles": parent_smiles + "C(=O)N",
                        "rule_name": "Offline Mock: 酰胺氢键供体",
                        "rationale": "离线模拟候选，不来自实际大模型调用"
                    }
                ]
            elif effective_mode == "online_api":
                cfg = state.get("llm_config") or self.llm_config or {}
                provider = cfg.get("provider", "online_api")
                logger.info(f"Online API mode dispatched with provider: {provider}")
                import dti_lead_optimizer
                llm_error = None
                try:
                    llm_cands, audit_meta = await asyncio.to_thread(
                        dti_lead_optimizer.generate_llm_candidates,
                        smiles=parent_smiles,
                        target_name=state.get("target_symbol", "Kinase"),
                        baseline_pkd=best_pkd or 6.0,
                        baseline_kd_nM=state["current_best"]["predicted_kd_nM"],
                        optimization_goal=state.get("user_goal", "Optimize affinity and ADMET"),
                        custom_instruction=state.get("scenario", ""),
                        llm_config=cfg,
                        max_candidates=4
                    )
                    state["generation_audit"].append({"iteration": gen, "mode": "online_api", "provider": provider, **audit_meta})
                    for c in llm_cands:
                        mutated_specs.append({
                            "smiles": c.get("smiles"),
                            "rule_name": f"Online LLM ({provider}): {c.get('name', '衍生体')}",
                            "rationale": c.get("rationale") or f"在线大模型 ({provider}) 生成设计"
                        })
                except Exception as exc:
                    logger.warning(f"Online LLM candidate generation failed: {exc}. Falling back to rule-based generation with honest provenance.")
                    llm_error = str(exc)
                    state["generation_audit"].append({"iteration": gen, "mode": "heuristic_fallback", "provider": provider, "fallback_reason": llm_error})

                if not mutated_specs:
                    # Honest rule-based fallback without forging fake online LLM generation claims
                    fallback_smiles = parent_smiles + "(F)" if "c" in parent_smiles else parent_smiles + "C"
                    mutated_specs.append({
                        "smiles": fallback_smiles,
                        "rule_name": f"Fallback (Rule-Based) [LLM Error: {llm_error or '无有效候选'}]",
                        "rationale": f"在线模型调用失败 ({llm_error})，降级回退至启发式药物化学规则生成并如实记录来源"
                    })
            else:
                for rule in MEDCHEM_RULES[:4]:
                    try:
                        new_smi = rule["transform"](parent_smiles)
                        if new_smi and new_smi != parent_smiles:
                            mutated_specs.append({
                                "smiles": new_smi,
                                "rule_name": rule["name"],
                                "rationale": rule["description"]
                            })
                    except Exception:
                        continue

            # Fallback if no rule matched
            if not mutated_specs:
                mutated_specs.append({
                    "smiles": parent_smiles + "C",
                    "rule_name": "烷基侧链微调",
                    "rationale": "常规甲基衍生探索结合口袋边缘相互作用"
                })

            yield sse("agent_thought", {
                "agent": "designer",
                "iteration": gen,
                "thought": f"成功设计出 {len(mutated_specs)} 款高潜力变构衍生物，移交 DTI Auditor & Safety Auditor 亲和力门禁进行双冷泛化预测..."
            })
            await asyncio.sleep(0.2)

            # --- Node 3 & 4: DTI Auditor & Safety Auditor with Hard Constraint Gate ---
            state["current_agent"] = "dti_auditor"
            new_candidates: List[CandidateRecord] = []

            for spec in mutated_specs:
                if self.cancellation_requested:
                    break

                cand = self.evaluate_molecule(
                    smiles=spec["smiles"],
                    target_sequence=state["target_sequence"],
                    target_symbol=state["target_symbol"],
                    gen=gen,
                    modifications=spec["rule_name"],
                    rationale=spec["rationale"],
                    parent_id=state["current_best"]["id"] if state["current_best"] else None
                )
                state["candidates"].append(cand)
                new_candidates.append(cand)

                # Check if this candidate is eligible to become the new global best
                # MUST strictly pass hard constraints to become current_best!
                is_improved = False
                if cand["passed_hard_constraints"]:
                    if state["current_best"] is None or cand["predicted_pkd"] > state["current_best"]["predicted_pkd"]:
                        if cand["admet_score"] >= state["min_admet_score"] - 15.0:
                            state["current_best"] = cand
                            is_improved = True

                yield sse("candidate_evaluated", {
                    "agent": "safety_auditor",
                    "candidate": cand,
                    "is_best": state["current_best"] is not None and cand["id"] == state["current_best"]["id"],
                    "passed_hard_constraints": cand["passed_hard_constraints"],
                    "constraint_failure_reason": cand["constraint_failure_reason"]
                })
                await asyncio.sleep(0.2)

            # Candidate multi-objective ranking (filter only compliant candidates for pareto if available)
            compliant_cands = [c for c in state["candidates"] if c["passed_hard_constraints"]]
            ranking_pool = compliant_cands if compliant_cands else state["candidates"]
            all_cands = sorted(ranking_pool, key=lambda c: (c["predicted_pkd"], c["admet_score"]), reverse=True)
            state["pareto_frontier"] = all_cands[:5]

            # Save Checkpoint
            checkpoint = AgentCheckpoint(
                task_id=task_id,
                generation=gen,
                parent_id=state["current_best"]["id"] if state["current_best"] else None,
                parent_smiles=state["current_best"]["smiles"] if state["current_best"] else state["baseline_smiles"],
                constraints_version=self.constraints.version,
                best_pkd=state["current_best"]["predicted_pkd"] if state["current_best"] else 0.0,
                candidates_count=len(state["candidates"]),
                timestamp=utc_now_iso()
            )
            self.checkpoints.append(checkpoint)
            try:
                ckpt_dir = ROOT / "output" / "agent_checkpoints"
                ckpt_dir.mkdir(parents=True, exist_ok=True)
                ckpt_file = ckpt_dir / f"{task_id}_gen_{gen}.json"
                ckpt_file.write_text(json.dumps(checkpoint.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
                if not ckpt_file.exists() or ckpt_file.stat().st_size == 0:
                    raise IOError(f"Checkpoint file {ckpt_file} was not written properly.")
                if json.loads(ckpt_file.read_text(encoding="utf-8")) != checkpoint.to_dict():
                    raise IOError("Checkpoint readback differs from the execution state")
                self.persisted_checkpoint_count += 1
            except Exception as e:
                logger.error(f"Failed to persist checkpoint to disk: {e}")
                state["checkpoint_error"] = str(e)
                yield sse("agent_error", {
                    "agent": "supervisor",
                    "error": f"检查点持久化失败: {str(e)}"
                })

            # --- Supervisor Convergence Check ---
            curr_best = state["current_best"]
            if (curr_best and 
                curr_best["passed_hard_constraints"] and
                curr_best["predicted_pkd"] >= state["target_pkd"] and 
                curr_best["admet_score"] >= state["min_admet_score"] and 
                curr_best["hemolysis_risk_pct"] <= state["max_hemolysis_pct"]):
                state["is_converged"] = True
                yield sse("agent_thought", {
                    "agent": "supervisor",
                    "iteration": gen,
                    "thought": f"【收敛判定】核心计算指标与硬约束全部满足：最优候选 {curr_best['id']} 预测 pKd={curr_best['predicted_pkd']:.3f}，ADMET评分={curr_best['admet_score']:.1f}。已收敛并归档候选排序。"
                })
                break
            else:
                yield sse("iteration_complete", {
                    "iteration": gen,
                    "current_best": state["current_best"],
                    "candidates_tested": len(state["candidates"]),
                    "compliant_count": len(compliant_cands),
                    "pareto_size": len(state["pareto_frontier"]),
                    "candidate_ranking": state["pareto_frontier"],
                    "constraints_version": self.constraints.version
                })
                await asyncio.sleep(0.25)

        # --- Node 5: Wetlab Reporter Node ---
        state["current_agent"] = "reporter"
        best = state["current_best"] or state["candidates"][0]
        baseline = state["candidates"][0]

        delta_pkd = best["predicted_pkd"] - baseline["predicted_pkd"]
        kd_fold = (baseline["predicted_kd_nM"] / max(0.001, best["predicted_kd_nM"])) if best["predicted_kd_nM"] > 0 else 1.0

        verdict = {
            "converged": state["is_converged"],
            "total_iterations": state["iteration"],
            "total_candidates_screened": len(state["candidates"]),
            "constraints_applied": self.constraints.to_dict(),
            "checkpoint_status": "failed" if state.get("checkpoint_error") else ("persisted" if self.persisted_checkpoint_count else "none"),
            "checkpoint_error": state.get("checkpoint_error"),
            "generation_audit": state["generation_audit"],
            "baseline": {
                "id": baseline["id"],
                "smiles": baseline["smiles"],
                "pkd": baseline["predicted_pkd"],
                "kd_nM": baseline["predicted_kd_nM"],
                "admet_score": baseline["admet_score"]
            },
            "best_molecule": best,
            "improvements": {
                "delta_pkd": round(delta_pkd, 3),
                "kd_fold_enhancement": round(kd_fold, 1),
                "admet_safety_status": "In-Silico Pass (计算通过，待实测)" if best["admet_score"] >= state["min_admet_score"] else "In-Silico Moderate (需优化)",
                "recommended_plate": f"PLT-A2A-{datetime.now().strftime('%m%d')}-01",
                "assay_method": "SPR 表面等离子共振法 / 激酶荧光偏振竞争抑制测定",
                "ranking_method": "候选多目标排序 (非严格Pareto非支配集，严格受硬约束门禁过滤)",
                "evidence_level": "计算设计假说 (需湿法生化验证)"
            },
            "candidate_ranking": state["pareto_frontier"],
            "pareto_frontier": state["pareto_frontier"]
        }
        state["final_verdict"] = verdict

        yield sse("agent_thought", {
            "agent": "reporter",
            "thought": (
                f"【学术交付与投产建议】已完成多轮推演归档。先导物经结构修饰后模型预测亲和力提升 {delta_pkd:+.3f} pKd，"
                f"结合活性预测改善约 {kd_fold:.1f} 倍（计算假说，待实测）。已整理候选优选排序并生成微孔板实验参考条码【{verdict['improvements']['recommended_plate']}】。"
            )
        })
        await asyncio.sleep(0.2)

        # Final Event
        yield sse("finished", {
            "verdict": verdict,
            "candidate_ranking": state["pareto_frontier"],
            "pareto_frontier": state["pareto_frontier"]
        })
