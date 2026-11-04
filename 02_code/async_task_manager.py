"""Asynchronous Task Manager with bounded concurrency, persistence, and cooperative cancellation.

Enforces:
- Bounded thread pool executor (max_workers=2-4) to prevent CPU/memory thrashing
- Bounded queue depth with TaskQueueFullError (HTTP 429) when saturated
- Cooperative cancellation checkpoints during long-running iterations
- Full integration with AsyncJobStore for state transitions and event logs
- Direct support for kinase profiling (core & 379 kinome panel) and virtual screening
"""
from __future__ import annotations

import os
import sys
import time
import math
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / "02_code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from async_job_store import AsyncJobStore, DEFAULT_DB_PATH
from dti_inference_runtime import DTIInferenceRuntime, CORE_KINASE_PANEL
from smiles_validator import validate_smiles


class TaskQueueFullError(Exception):
    """Raised when the asynchronous task queue has reached capacity."""
    pass


class TaskCancelledException(Exception):
    """Raised when task execution is cancelled cooperatively."""
    pass


class AsyncTaskManager:
    """Manages asynchronous computation tasks."""

    def __init__(
        self,
        store: Optional[AsyncJobStore] = None,
        max_workers: int = 2,
        max_queue_size: int = 20
    ):
        self.store = store or AsyncJobStore(auto_recover=False)
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="AsyncWorker")
        self._futures: Dict[str, Future] = {}
        self._runtime: Optional[DTIInferenceRuntime] = None

    def get_runtime(self) -> DTIInferenceRuntime:
        if self._runtime is None:
            self._runtime = DTIInferenceRuntime()
            self._runtime.load()
        return self._runtime

    def get_pending_count(self) -> int:
        pending_tasks = self.store.list_tasks(status="pending", limit=100)
        return len(pending_tasks)

    def submit_task(
        self,
        task_type: str,
        params: Dict[str, Any],
        task_id: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Submits an asynchronous task.
        Raises TaskQueueFullError if queue capacity is exceeded.
        Returns (task_id, is_new).
        """
        pending_count = self.get_pending_count()
        if pending_count >= self.max_queue_size:
            raise TaskQueueFullError(
                f"任务队列已达到上限饱和状态 (当前等待任务: {pending_count} / 上限: {self.max_queue_size})，请稍后重试。"
            )

        actual_id, is_new = self.store.create_task(
            task_type=task_type,
            params=params,
            task_id=task_id,
            idempotency_key=idempotency_key
        )

        if not is_new:
            return actual_id, False

        # Submit to thread pool
        future = self._executor.submit(self._task_worker, actual_id, task_type, params)
        self._futures[actual_id] = future
        return actual_id, True

    def cancel_task(self, task_id: str, reason: str = "用户主动取消任务") -> bool:
        """Requests cancellation of a task."""
        future = self._futures.get(task_id)
        if future and not future.running():
            # If still queued, cancel future directly
            future.cancel()
        
        # Mark cancellation requested in store
        cancelled = self.store.request_cancellation(task_id)
        # Also attempt immediate cancel if in pending
        task = self.store.get_task(task_id)
        if task and task["status"] == "pending":
            self.store.cancel_task(task_id, reason=reason)
            return True
        return cancelled

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get_task(task_id)

    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get_task_result(task_id)

    def list_tasks(
        self,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        return self.store.list_tasks(task_type=task_type, status=status, limit=limit)

    def _task_worker(self, task_id: str, task_type: str, params: Dict[str, Any]) -> None:
        """Internal execution wrapper running inside thread pool."""
        try:
            # Check if cancelled before even starting
            if self.store.is_cancellation_requested(task_id):
                self.store.cancel_task(task_id, reason="任务在启动前已被请求取消")
                return

            self.store.mark_started(task_id)

            if task_type == "kinase_profiling":
                self._run_kinase_profiling(task_id, params)
            elif task_type == "virtual_screening":
                self._run_virtual_screening(task_id, params)
            elif task_type == "lead_optimization":
                self._run_lead_optimization(task_id, params)
            else:
                self.store.fail_task(task_id, f"不支持的任务类型: '{task_type}'")

        except TaskCancelledException as exc:
            self.store.cancel_task(task_id, reason=str(exc))
        except Exception as exc:
            self.store.fail_task(task_id, f"执行异常: {str(exc)}", error_details={"exception": type(exc).__name__})
        finally:
            self._futures.pop(task_id, None)

    def _check_cancellation(self, task_id: str) -> None:
        if self.store.is_cancellation_requested(task_id):
            raise TaskCancelledException("检测到用户取消请求，任务已安全终止")

    # ==========================================
    # Task Handlers
    # ==========================================

    def _run_kinase_profiling(self, task_id: str, params: Dict[str, Any]) -> None:
        """Kinase selectivity profiling across core panel (16) or full kinome (379)."""
        drug_smiles = params.get("drug_smiles", "").strip()
        model_name = params.get("model_name")
        panel_type = params.get("panel", "core").lower()  # "core" or "all"

        if not drug_smiles:
            raise ValueError("缺少必需参数: drug_smiles 不能为空")

        validate_smiles(drug_smiles)
        runtime = self.get_runtime()

        # Target list determination
        if panel_type == "all":
            targets_to_screen = list(runtime.targets.values())
        else:
            # Core 16 panel
            targets_to_screen = []
            for t_id in CORE_KINASE_PANEL:
                t = runtime.targets.get(t_id)
                if not t:
                    for k, v in runtime.targets.items():
                        if t_id.lower() in k.lower():
                            t = v
                            break
                if t:
                    targets_to_screen.append(t)

        total_targets = len(targets_to_screen)
        if total_targets == 0:
            raise ValueError(f"未检索到任何符合条件的激酶靶标 (panel={panel_type})")

        self.store.update_progress(
            task_id,
            stage=f"激酶谱扫描启动 ({panel_type}: 共 {total_targets} 靶点)",
            current=0,
            total=total_targets,
            message="正在加载激酶特征与模型"
        )

        results = []
        for idx, target in enumerate(targets_to_screen):
            self._check_cancellation(task_id)

            t_name = target["id"]
            t_seq = target["sequence"]

            pred = runtime.predict(drug_smiles, t_seq, model_name=model_name)
            results.append({
                "kinase_name": t_name,
                "target_id": t_name,
                "length": target.get("length", len(t_seq)),
                "predicted_pkd": pred["predicted_pkd"],
                "predicted_kd_nM": pred["predicted_kd_nM"],
                "affinity_tier": pred["affinity_tier"],
                "affinity_tier_code": pred["affinity_tier_code"],
                "domain": pred["domain"],
                "domain_label": pred["domain_label"]
            })

            # Update progress every 5 targets or on last target
            if (idx + 1) % 5 == 0 or (idx + 1) == total_targets:
                self.store.update_progress(
                    task_id,
                    stage=f"激酶谱扫描计算中 ({panel_type})",
                    current=idx + 1,
                    total=total_targets,
                    message=f"已完成 {idx + 1}/{total_targets}，当前: {t_name}"
                )

        # Sort descending by predicted_pkd
        results.sort(key=lambda x: x["predicted_pkd"], reverse=True)

        summary = {
            "total_screened": total_targets,
            "panel": panel_type,
            "top_hit_kinase": results[0]["kinase_name"] if results else None,
            "top_hit_pkd": results[0]["predicted_pkd"] if results else None,
            "high_affinity_count": sum(1 for r in results if r["predicted_pkd"] >= 7.0),
            "moderate_affinity_count": sum(1 for r in results if 6.0 <= r["predicted_pkd"] < 7.0),
            "model_used": results[0].get("model_used") if results else model_name
        }

        full_payload = {
            "task_id": task_id,
            "drug_smiles": drug_smiles,
            "panel": panel_type,
            "summary": summary,
            "hits": results
        }

        self.store.complete_task(task_id, result_summary=summary, full_result_payload=full_payload)

    def _run_virtual_screening(self, task_id: str, params: Dict[str, Any]) -> None:
        """Virtual screening across compound library with batched cancellation checks."""
        from virtual_screening_engine import PRESET_SCREENING_LIBRARIES, screen_virtual_library

        target_symbol = params.get("target_symbol", "ABL1")
        target_sequence = params.get("target_sequence")
        library_id = params.get("library_id", "kinase_privileged")
        custom_compounds = params.get("custom_compounds")
        top_k = int(params.get("top_k", 20))

        if custom_compounds and len(custom_compounds) > 50000:
            raise ValueError(f"分子输入规模超出上限 (当前 {len(custom_compounds)}，单机上限 50,000)")

        self.store.update_progress(
            task_id,
            stage="虚拟筛选初始化",
            current=0,
            total=100,
            message="正在校验靶点序列与化合物库"
        )
        self._check_cancellation(task_id)

        # Execute screening pipeline
        report = screen_virtual_library(
            target_symbol=target_symbol,
            target_sequence=target_sequence,
            library_id=library_id,
            custom_compounds=custom_compounds,
            max_hits=top_k
        )

        self._check_cancellation(task_id)

        hits = report.get("hits", [])
        summary = {
            "target_symbol": report.get("target_symbol", target_symbol),
            "target_name": report.get("target_symbol", target_symbol),
            "total_screened": report.get("total_screened", 0),
            "library_name": report.get("library_name", library_id),
            "top_hits_count": len(hits),
            "clusters_count": report.get("num_clusters", 0),
            "top_compound_name": hits[0].get("name") if hits else None,
            "top_compound_pkd": hits[0].get("predicted_pkd") if hits else None,
            "top_compound_smiles": hits[0].get("smiles") if hits else None,
        }

        full_payload = {
            "task_id": task_id,
            "report": report
        }

        self.store.complete_task(task_id, result_summary=summary, full_result_payload=full_payload)

    def _run_lead_optimization(self, task_id: str, params: Dict[str, Any]) -> None:
        """Lead optimization derivative generation and scoring."""
        from dti_lead_optimizer import DTILeadOptimizer

        parent_smiles = params.get("parent_smiles")
        target_symbol = params.get("target_symbol", "ABL1")
        target_sequence = params.get("target_sequence")
        is_mutant = bool(params.get("is_mutant", False))
        max_derivatives = int(params.get("max_derivatives", 15))
        generation_mode = params.get("generation_mode", "heuristic")
        llm_config = params.get("llm_config")
        model_name = params.get("model_name", "ridge")

        if not parent_smiles:
            raise ValueError("缺少 parent_smiles 参数")

        self.store.update_progress(
            task_id,
            stage="先导优化初始化",
            current=0,
            total=100,
            message=f"母体分子: {parent_smiles[:20]}..."
        )
        self._check_cancellation(task_id)

        optimizer = DTILeadOptimizer()
        res = optimizer.optimize_lead(
            parent_smiles=parent_smiles,
            target_symbol=target_symbol,
            target_sequence=target_sequence,
            is_mutant=is_mutant,
            max_derivatives=max_derivatives,
            generation_mode=generation_mode,
            llm_config=llm_config,
            model_name=model_name
        )

        self._check_cancellation(task_id)

        derivatives = res.get("candidates") or res.get("derivatives") or []
        summary = {
            "parent_smiles": parent_smiles,
            "target_symbol": target_symbol,
            "derivatives_count": len(derivatives),
            "best_derivative_name": derivatives[0]["name"] if derivatives else None,
            "best_predicted_pkd": derivatives[0]["predicted_pkd"] if derivatives else None,
        }

        full_payload = {
            "task_id": task_id,
            "optimization_result": res
        }

        self.store.complete_task(task_id, result_summary=summary, full_result_payload=full_payload)
