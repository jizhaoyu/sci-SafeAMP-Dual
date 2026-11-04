"""Async task API endpoints for long-running computation jobs.

Endpoints:
- POST /api/tasks/submit: Submit a task (429 if queue full)
- GET  /api/tasks/{task_id}: Get task status and progress
- POST /api/tasks/{task_id}/cancel: Request cooperative cancellation
- GET  /api/tasks/{task_id}/events: Get event history
- GET  /api/tasks/{task_id}/result: Get full result payload
- GET  /api/tasks: List recent tasks
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / "02_code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from async_task_manager import AsyncTaskManager, TaskQueueFullError
from async_job_store import AsyncJobStore

router = APIRouter(prefix="/api/tasks", tags=["Async Tasks"])
task_manager = AsyncTaskManager(store=AsyncJobStore(auto_recover=True))


class TaskSubmitRequest(BaseModel):
    task_type: str = Field(..., description="Task type, e.g. kinase_profiling, virtual_screening, lead_optimization")
    params: Dict[str, Any] = Field(default_factory=dict, description="Task execution parameters")
    idempotency_key: Optional[str] = Field(None, description="Optional key for idempotent submission")


class TaskCancelRequest(BaseModel):
    reason: Optional[str] = Field("用户主动取消任务", description="Cancellation reason")


@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_task(req: TaskSubmitRequest):
    """Submits an asynchronous computation task to the bounded queue."""
    try:
        task_id, is_new = task_manager.submit_task(
            task_type=req.task_type,
            params=req.params,
            idempotency_key=req.idempotency_key
        )
        task = task_manager.get_task_status(task_id)
        return {
            "task_id": task_id,
            "is_new": is_new,
            "status": task["status"] if task else "pending",
            "task_type": req.task_type,
            "created_at": task["created_at"] if task else None
        }
    except TaskQueueFullError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交任务失败: {str(exc)}"
        )


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    """Retrieves current status, progress, and metadata for a task."""
    task = task_manager.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"任务未找到: {task_id}")
    return task


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, req: Optional[TaskCancelRequest] = None):
    """Requests cooperative cancellation of a pending or running task."""
    task = task_manager.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"任务未找到: {task_id}")

    if task["status"] in ("completed", "failed", "cancelled", "interrupted"):
        return {
            "task_id": task_id,
            "cancellation_requested": False,
            "message": f"任务已处于终态 ({task['status']})，无需取消",
            "status": task["status"]
        }

    reason = req.reason if req and req.reason else "用户主动取消任务"
    cancelled = task_manager.cancel_task(task_id, reason=reason)
    return {
        "task_id": task_id,
        "cancellation_requested": True,
        "message": "已向任务发送取消指令"
    }


@router.get("/{task_id}/events")
async def get_task_events(task_id: str):
    """Retrieves the event timeline for a task."""
    task = task_manager.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"任务未找到: {task_id}")
    return task_manager.store.get_task_events(task_id)


@router.get("/{task_id}/result")
async def get_task_result(task_id: str):
    """Retrieves the full computation payload of a completed task."""
    task = task_manager.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"任务未找到: {task_id}")

    if task["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务尚未完成，当前状态: '{task['status']}'"
        )

    res = task_manager.get_task_result(task_id)
    if res is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="结果文件不存在或已损坏"
        )
    return res


@router.get("")
async def list_tasks(
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    status: Optional[str] = Query(None, description="Filter by status (pending, running, completed, etc.)"),
    limit: int = Query(50, ge=1, le=200, description="Page limit")
):
    """Lists recent tasks with optional filtering."""
    return task_manager.list_tasks(task_type=task_type, status=status, limit=limit)
