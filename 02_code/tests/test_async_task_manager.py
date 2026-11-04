"""Unit and integration tests for AsyncJobStore and AsyncTaskManager (P2 Milestone)."""
from __future__ import annotations

import os
import sys
import time
import shutil
import tempfile
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CODE_DIR = PROJECT_ROOT / "02_code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from async_job_store import AsyncJobStore
from async_task_manager import AsyncTaskManager, TaskQueueFullError


@pytest.fixture
def temp_store(tmp_path):
    db_file = tmp_path / "test_jobs.db"
    res_dir = tmp_path / "results"
    store = AsyncJobStore(db_path=db_file, results_dir=res_dir)
    return store


def test_job_store_lifecycle_and_events(temp_store):
    """Test standard task creation, progress updates, events, and completion."""
    task_id, is_new = temp_store.create_task(
        task_type="kinase_profiling",
        params={"drug_smiles": "c1ccccc1", "panel": "core"}
    )
    assert is_new is True
    assert task_id.startswith("task_")

    # Initial state
    t = temp_store.get_task(task_id)
    assert t["status"] == "pending"
    assert t["progress"] == 0.0

    # Start
    temp_store.mark_started(task_id)
    t = temp_store.get_task(task_id)
    assert t["status"] == "running"

    # Progress
    temp_store.update_progress(task_id, stage="计算中", current=5, total=10, message="进度 50%")
    t = temp_store.get_task(task_id)
    assert t["progress"] == 0.5
    assert t["progress_current"] == 5
    assert t["progress_total"] == 10

    # Complete
    summary = {"top_kinase": "ABL1", "top_pkd": 8.5}
    full_res = {"hits": [{"kinase": "ABL1", "pkd": 8.5}], "summary": summary}
    temp_store.complete_task(task_id, result_summary=summary, full_result_payload=full_res)

    t = temp_store.get_task(task_id)
    assert t["status"] == "completed"
    assert t["progress"] == 1.0
    assert t["result_summary"]["top_kinase"] == "ABL1"

    # Verify result retrieval
    saved_res = temp_store.get_task_result(task_id)
    assert saved_res["hits"][0]["kinase"] == "ABL1"

    # Verify event sequence
    events = temp_store.get_task_events(task_id)
    assert len(events) >= 4
    assert events[0]["event_type"] == "task_created"
    assert events[1]["event_type"] == "task_started"
    assert events[2]["event_type"] == "progress_update"
    assert events[-1]["event_type"] == "task_completed"


def test_job_store_idempotency(temp_store):
    """Submitting the same idempotency key should return the existing task ID."""
    t1_id, is_new1 = temp_store.create_task(
        task_type="virtual_screening",
        params={"library": "kinase_privileged"},
        idempotency_key="unique_key_abc_123"
    )
    assert is_new1 is True

    t2_id, is_new2 = temp_store.create_task(
        task_type="virtual_screening",
        params={"library": "kinase_privileged"},
        idempotency_key="unique_key_abc_123"
    )
    assert is_new2 is False
    assert t1_id == t2_id


def test_startup_interruption_recovery(tmp_path):
    """Verify that restarting on a crash marks orphaned running/pending tasks as interrupted."""
    db_file = tmp_path / "crash_test.db"
    res_dir = tmp_path / "results"

    # Simulate running server that crashes
    store1 = AsyncJobStore(db_path=db_file, results_dir=res_dir)
    t1_id, _ = store1.create_task("kinase_profiling", {})
    t2_id, _ = store1.create_task("kinase_profiling", {})
    store1.mark_started(t2_id)

    # Server restarts with auto_recover=True: new service instance marks orphaned jobs
    store2 = AsyncJobStore(db_path=db_file, results_dir=res_dir, auto_recover=True)
    
    t1 = store2.get_task(t1_id)
    t2 = store2.get_task(t2_id)
    assert t1["status"] == "interrupted"
    assert t2["status"] == "interrupted"
    assert "服务异常重启" in t1["error_message"]
    assert "服务异常重启" in t2["error_message"]


def test_task_queue_saturation(temp_store):
    """When pending tasks exceed max_queue_size, TaskQueueFullError must be raised."""
    manager = AsyncTaskManager(store=temp_store, max_workers=1, max_queue_size=3)

    # Fill queue to capacity
    for i in range(3):
        temp_store.create_task("dummy_type", {"idx": i})

    # 4th submission must raise TaskQueueFullError
    with pytest.raises(TaskQueueFullError) as exc_info:
        manager.submit_task("dummy_type", {"idx": 999})
    assert "任务队列已达到上限饱和状态" in str(exc_info.value)


def test_cooperative_cancellation(temp_store):
    """Test cancellation of task via manager and store."""
    manager = AsyncTaskManager(store=temp_store, max_workers=2, max_queue_size=10)
    task_id, _ = manager.submit_task(
        task_type="kinase_profiling",
        params={"drug_smiles": "Cc1ccc(cc1Nc2nccc(n2)c3cccnc3)NC(=O)c4ccc(cc4)CN5CCN(CC5)C", "panel": "core"}
    )

    # Request cancellation immediately
    cancelled = manager.cancel_task(task_id, reason="测试取消")
    assert cancelled is True

    # Allow brief moment for cooperative cancellation to take effect
    for _ in range(20):
        t = manager.get_task_status(task_id)
        if t["status"] in ("cancelled", "completed"):
            break
        time.sleep(0.2)
    assert t["status"] in ("cancelled", "completed")
