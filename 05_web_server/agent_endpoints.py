"""FastAPI endpoints for A2A Multi-Agent Orchestrator with SSE Streaming & Steering Control."""
from __future__ import annotations

import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import sys
import uuid
import weakref
from typing import Any, Dict, List, Optional, Literal

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_code"))

from agent_orchestrator import MultiAgentOrchestrator, AgentState, utc_now_iso
from agent_constraints import (
    AgentHardConstraints,
    UnsupportedConstraintError,
    InvalidConstraintUpdateError
)
from async_endpoints import task_manager

logger = logging.getLogger("agent_endpoints")
router = APIRouter(prefix="/api/agent", tags=["A2A Multi-Agent"])

# Active orchestrator sessions mapped by task_id
active_sessions: Dict[str, MultiAgentOrchestrator] = {}
background_tasks: Dict[str, asyncio.Task] = {}
_background_limits = weakref.WeakKeyDictionary()


def _finish_agent_task(task_id: str, orch: MultiAgentOrchestrator) -> None:
    """Persist execution facts for both normal completion and cooperative cancellation."""
    state = orch.current_state or {}
    error = state.get("checkpoint_error")
    checkpoint_status = "failed" if error else ("persisted" if getattr(orch, "persisted_checkpoint_count", 0) else "none")
    summary = {
        "converged": state.get("is_converged", False),
        "total_iterations": state.get("iteration", 0),
        "best_pkd": (state.get("current_best") or {}).get("predicted_pkd"),
        "checkpoint_status": checkpoint_status,
    }
    if error:
        summary["checkpoint_error"] = error
    if getattr(orch, "cancellation_requested", False) or task_manager.store.is_cancellation_requested(task_id):
        task_manager.store.cancel_task(task_id, reason="智能体任务已取消", result_summary=summary)
        return
    if not state.get("final_verdict"):
        task_manager.store.fail_task(task_id, "智能体执行已结束但未生成最终结果")
        return
    verdict = {**state["final_verdict"], "checkpoint_status": checkpoint_status}
    if error:
        verdict["checkpoint_error"] = error
    task_manager.store.complete_task(task_id, summary, verdict)


class AgentRunRequest(BaseModel):
    scenario: str = Field("kinase_escape", description="Pre-set scenario: kinase_escape | safeamp_evolution | custom")
    user_goal: str = Field(..., description="High-level scientific optimization goal")
    target_symbol: str = Field(..., description="Target kinase symbol (e.g., EGFR, ABL1)")
    target_sequence: str = Field(..., description="Target amino acid sequence")
    baseline_smiles: str = Field(..., description="Lead starting molecule SMILES or peptide sequence")
    max_iterations: int = Field(4, ge=1, le=8, description="Max autonomous evolution generations")
    target_pkd: float = Field(8.5, ge=5.0, le=12.0, description="Target pKd binding threshold")
    min_admet_score: float = Field(65.0, ge=0.0, le=100.0, description="Min holistic ADMET health score")
    max_hemolysis_pct: float = Field(8.0, ge=0.5, le=50.0, description="Max acceptable hemolysis percentage")
    initial_constraints: Optional[Dict[str, Any]] = Field(None, description="Optional initial hard constraints")
    llm_mode: Optional[str] = Field("heuristic_only", description="Agent LLM dispatch mode: 'heuristic_only' | 'offline_mock' | 'online_api'")
    llm_config: Optional[Dict[str, Any]] = Field(None, description="LLM execution configuration (provider, api_base, model_name, temperature)")
    enable_background: Optional[bool] = Field(False, description="Run detached in background async job store with persistent checkpoint tracking")

    @validator("llm_mode")
    def validate_llm_mode(cls, v):
        allowed = {"heuristic_only", "offline_mock", "online_api"}
        if v is not None and v not in allowed:
            raise ValueError(f"Invalid llm_mode: '{v}'. Must be one of: {sorted(allowed)}")
        return v or "heuristic_only"


class ConstraintUpdateRequest(BaseModel):
    constraints: Dict[str, Any] = Field(..., description="Key-value mapping of updated hard constraints")
    expected_version: int = Field(..., description="Expected current constraint version to prevent race conditions")


AGENT_PRESETS = [
    {
        "id": "egfr_t790m_escape",
        "title": "奥希替尼对抗 EGFR(T790M) 耐药突变自主改构",
        "scenario": "kinase_escape",
        "target_symbol": "EGFR(T790M)",
        "target_sequence": "MRRHPKLTELATKLARLQKELDVVLQHKERLEKEAQKLEKELKKLKQENEVLKQENEQLKQEIELLKKEIELLKKEIEQLKQENEKLKQE",
        "baseline_smiles": "CN1CCN(CC1)C2=CC(=C(C=C2)NC(=O)C=C)NC3=NC=CC(=N3)C4=CN(C5=CC=CC=C54)C",
        "default_goal": "针对肺癌 T790M 门控耐药突变，改构克服空间位阻，将 pKd 提升至 ≥ 8.8，并维持良好水溶性与 hERG 心脏安全性",
        "target_pkd": 8.8,
        "min_admet_score": 68.0,
        "max_hemolysis_pct": 5.0,
        "tag": "肺癌靶向"
    },
    {
        "id": "abl1_t315i_gatekeeper",
        "title": "伊马替尼对抗 ABL1(T315I) 守门残基突破",
        "scenario": "kinase_escape",
        "target_symbol": "ABL1(T315I)",
        "target_sequence": "MLEICLKLVGCKSKKGLSSSSSCYLEEALQRPVASDFEPQGLSEAARWNSKENLLAGPSENDPNLFVALYDFVASGDNTLSITKGEKLRVLGYNHNGEWCEAQTKNGQGWVPSNYITPVNSLEKHSWYHGPVSRNAAEYLLSSGINGSFLVRESESSPGQRSISLRYEGRVYHYRINTASDGKLYVSSESRFNTLAELVHHHSTVADGLITTLHYPAPKRNKPTI",
        "baseline_smiles": "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5",
        "default_goal": "克服慢粒白血病 T315I 守门突变缺失苏氨酸氧配位的问题，引入刚性碳碳三键或氟代等排体，追求 pKd ≥ 8.5",
        "target_pkd": 8.5,
        "min_admet_score": 65.0,
        "max_hemolysis_pct": 6.0,
        "tag": "慢粒白血病"
    },
    {
        "id": "safeamp_dual_evolution",
        "title": "双靶广谱低溶血抗菌肽协同演化",
        "scenario": "safeamp_evolution",
        "target_symbol": "Bacterial_Membrane_Kinase",
        "target_sequence": "MRRVLILVLFLFVALAQSLVQGKKLAKLAKKWAKLAKKFL",
        "baseline_smiles": "KWKKLLKKLLKKLLKKL",
        "default_goal": "在增强耐药菌膜靶向与激酶抑制的同时，将哺乳动物红细胞溶血率控制在 < 5.0%，实现双靶平衡",
        "target_pkd": 8.2,
        "min_admet_score": 75.0,
        "max_hemolysis_pct": 4.5,
        "tag": "SafeAMP-Dual"
    }
]


@router.get("/presets")
def get_agent_presets():
    """Get curated scientific multi-agent optimization presets."""
    return {"presets": AGENT_PRESETS}


@router.post("/stream")
async def run_agent_stream(req: AgentRunRequest):
    """Run multi-agent autonomous optimization with real-time SSE event stream and task tracking."""
    capacity = max(1, task_manager.max_workers + task_manager.max_queue_size)
    if len(active_sessions) >= capacity:
        raise HTTPException(status_code=429, detail="智能体任务队列已满，请等待现有任务结束")
    task_id = f"A2A_{uuid.uuid4().hex[:10]}"
    
    # Initialize hard constraints
    initial_constraints = None
    if req.initial_constraints:
        try:
            initial_constraints = AgentHardConstraints.from_dict(req.initial_constraints)
        except UnsupportedConstraintError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    orch = MultiAgentOrchestrator(
        initial_constraints=initial_constraints,
        llm_mode=req.llm_mode or "heuristic_only",
        llm_config=req.llm_config
    )
    active_sessions[task_id] = orch

    # Register in P2 task manager (created status until pipeline entered)
    try:
        task_manager.store.create_task(
            task_type="agent_workflow",
            params=req.model_dump(),
            task_id=task_id
        )
    except Exception as exc:
        active_sessions.pop(task_id, None)
        logger.error("Failed to register agent task: %s", exc)
        raise HTTPException(status_code=503, detail="任务存储不可用，智能体任务未启动") from exc

    initial_state: AgentState = {
        "task_id": task_id,
        "scenario": req.scenario,
        "user_goal": req.user_goal,
        "target_symbol": req.target_symbol,
        "target_sequence": req.target_sequence,
        "baseline_smiles": req.baseline_smiles,
        "current_agent": "supervisor",
        "iteration": 0,
        "max_iterations": req.max_iterations,
        "target_pkd": req.target_pkd,
        "min_admet_score": req.min_admet_score,
        "max_hemolysis_pct": req.max_hemolysis_pct,
        "constraints_version": orch.constraints.version,
        "constraints": orch.constraints.to_dict(),
        "candidates": [],
        "current_best": None,
        "pareto_frontier": [],
        "step_count": 0,
        "is_converged": False,
        "final_verdict": None,
        "checkpoints": [],
        "enable_background": bool(req.enable_background),
        "llm_config": req.llm_config or {},
        "llm_mode": req.llm_mode or "heuristic_only",
    }

    if req.enable_background:
        bg_queue: asyncio.Queue = asyncio.Queue(maxsize=64)
        detached = False
        loop = asyncio.get_running_loop()
        if loop not in _background_limits:
            _background_limits[loop] = asyncio.Semaphore(max(1, task_manager.max_workers))
        limiter = _background_limits[loop]

        def publish(chunk):
            if detached:
                return
            if bg_queue.full():
                bg_queue.get_nowait()
            bg_queue.put_nowait(chunk)

        async def _background_worker():
            acquired = False
            try:
                await limiter.acquire()
                acquired = True
                if getattr(orch, "cancellation_requested", False):
                    _finish_agent_task(task_id, orch)
                    publish(f"event: task_cancelled\ndata: {json.dumps({'task_id': task_id, 'event': 'task_cancelled'})}\n\n")
                    return
                task_manager.store.mark_started(task_id)
                async for sse_chunk in orch.run_pipeline_stream(initial_state):
                    if task_manager.store.is_cancellation_requested(task_id):
                        orch.cancel()
                    publish(sse_chunk)
                _finish_agent_task(task_id, orch)
            except asyncio.CancelledError:
                orch.cancel()
                _finish_agent_task(task_id, orch)
                raise
            except Exception as exc:
                logger.error(f"Agent background task error in {task_id}: {exc}")
                task_manager.store.fail_task(task_id, str(exc))
                err_payload = json.dumps({"event": "error", "task_id": task_id, "error": str(exc)}, ensure_ascii=False)
                publish(f"event: error\ndata: {err_payload}\n\n")
            finally:
                if acquired:
                    limiter.release()
                active_sessions.pop(task_id, None)
                background_tasks.pop(task_id, None)
                publish(None)

        # Launch detached worker
        background_tasks[task_id] = asyncio.create_task(_background_worker())

        async def event_generator():
            nonlocal detached
            try:
                while True:
                    chunk = await bg_queue.get()
                    if chunk is None:
                        break
                    yield chunk
            except (GeneratorExit, asyncio.CancelledError):
                logger.info(f"Client disconnected from SSE stream for background task {task_id}; task continues in background.")
                return
            finally:
                detached = True

    else:
        async def event_generator():
            try:
                task_manager.store.mark_started(task_id)
                async for sse_chunk in orch.run_pipeline_stream(initial_state):
                    if task_manager.store.is_cancellation_requested(task_id):
                        orch.cancel()
                    yield sse_chunk
                _finish_agent_task(task_id, orch)
            except (GeneratorExit, asyncio.CancelledError):
                logger.info(f"Client disconnected early from SSE stream for task {task_id}. Cooperatively cancelling.")
                orch.cancel()
                _finish_agent_task(task_id, orch)
                raise
            except Exception as exc:
                logger.error(f"Agent stream error in {task_id}: {exc}")
                task_manager.store.fail_task(task_id, str(exc))
                err_payload = json.dumps({"event": "error", "task_id": task_id, "error": str(exc)}, ensure_ascii=False)
                yield f"event: error\ndata: {err_payload}\n\n"
            finally:
                active_sessions.pop(task_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.post("/{task_id}/pause")
def pause_agent_task(task_id: str):
    """Requests cooperative pause of an active multi-agent pipeline."""
    session = active_sessions.get(task_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到活跃的智能体任务: {task_id}")
    session.pause()
    return {
        "task_id": task_id,
        "message": "已发送暂停指令，智能体将在当前轮次/候选评估边界确认暂停",
        "pause_requested": True
    }


@router.post("/{task_id}/resume")
def resume_agent_task(task_id: str):
    """Resumes an active multi-agent pipeline from a confirmed pause state."""
    session = active_sessions.get(task_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到活跃的智能体任务: {task_id}")
    session.resume()
    return {
        "task_id": task_id,
        "message": "已发送恢复指令，智能体将应用最新硬约束继续执行",
        "is_paused": False
    }


@router.post("/{task_id}/cancel")
def cancel_agent_task(task_id: str):
    """Requests cooperative cancellation of an active multi-agent pipeline."""
    session = active_sessions.get(task_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到活跃的智能体任务: {task_id}")
    session.cancel()
    task_manager.store.request_cancellation(task_id)
    task_manager.store.request_cancellation(task_id)
    return {
        "task_id": task_id,
        "message": "已发送取消指令，流水线将安全终止并保存当前成果",
        "cancellation_requested": True
    }


@router.post("/{task_id}/constraints")
def update_agent_constraints(task_id: str, req: ConstraintUpdateRequest):
    """
    Updates verifiable hard constraints for an active agent pipeline.
    Must be called while pipeline is in confirmed pause state.
    """
    session = active_sessions.get(task_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到活跃的智能体任务: {task_id}")

    try:
        new_constraints = session.update_constraints(req.constraints, expected_version=req.expected_version)
        return {
            "task_id": task_id,
            "message": f"硬约束已成功更新至 v{new_constraints.version}",
            "version": new_constraints.version,
            "constraints": new_constraints.to_dict()
        }
    except UnsupportedConstraintError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except InvalidConstraintUpdateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/{task_id}/constraints")
def get_agent_constraints(task_id: str):
    """Retrieves active constraints and version for an agent session."""
    session = active_sessions.get(task_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到活跃的智能体任务: {task_id}")
    return {
        "task_id": task_id,
        "version": session.constraints.version,
        "is_paused": session.is_paused,
        "pause_requested": session.pause_requested,
        "constraints": session.constraints.to_dict()
    }


@router.get("/{task_id}/checkpoints")
def get_agent_checkpoints(task_id: str):
    """Retrieves persisted disk checkpoints and active memory checkpoints for an agent session."""
    session = active_sessions.get(task_id)
    memory_ckpts = [c.to_dict() for c in session.checkpoints] if session else []

    # Read from persisted disk directory
    disk_ckpts = []
    ckpt_dir = ROOT / "output" / "agent_checkpoints"
    if ckpt_dir.exists():
        for p in sorted(ckpt_dir.glob(f"{task_id}_gen_*.json")):
            try:
                disk_ckpts.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                pass

    return {
        "task_id": task_id,
        "in_memory_count": len(memory_ckpts),
        "disk_count": len(disk_ckpts),
        "checkpoints": disk_ckpts if disk_ckpts else memory_ckpts
    }
