"""Unit tests for BatchTaskManager."""
import sys
import time
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_code"))

from batch_task_manager import BatchJobStatus, BatchTaskManager


def test_basic_job_lifecycle():
    manager = BatchTaskManager(max_workers=2)
    sequences = ["AAAA", "CCCC", "DDDD"]

    def worker(seq):
        return {"seq": seq, "len": len(seq)}

    job_id = manager.submit_job(sequences, worker)
    assert job_id.startswith("job-")

    deadline = time.time() + 5.0
    status = None
    while time.time() < deadline:
        status = manager.get_status(job_id)
        assert status is not None
        if status["status"] == BatchJobStatus.COMPLETED.value:
            break
        time.sleep(0.02)

    assert status is not None
    assert status["status"] == "completed"
    assert status["total"] == 3
    assert status["completed"] == 3
    assert status["failed_count"] == 0
    assert len(status["results"]) == 3
    assert status["results"] == [
        {"seq": "AAAA", "len": 4},
        {"seq": "CCCC", "len": 4},
        {"seq": "DDDD", "len": 4},
    ]
    assert status["errors"] == []
    assert "created_at" in status
    assert "updated_at" in status
    manager.shutdown(wait=True)


def test_job_cancellation():
    manager = BatchTaskManager(max_workers=2)
    sequences = [f"SEQ_{i}" for i in range(20)]

    def slow_worker(seq):
        time.sleep(0.05)
        return {"seq": seq}

    job_id = manager.submit_job(sequences, slow_worker)
    time.sleep(0.03)

    cancelled = manager.cancel_job(job_id)
    assert cancelled is True

    deadline = time.time() + 5.0
    status = None
    while time.time() < deadline:
        status = manager.get_status(job_id)
        if status and status["status"] == BatchJobStatus.CANCELLED.value:
            break
        time.sleep(0.02)

    assert status is not None
    assert status["status"] == "cancelled"
    assert status["completed"] < 20
    manager.shutdown(wait=True)


def test_job_error_handling():
    manager = BatchTaskManager(max_workers=2)
    sequences = ["VALID_A", "FAIL_1", "VALID_B", "FAIL_2"]

    def flaky_worker(seq):
        if "FAIL" in seq:
            raise ValueError(f"Processing failed for {seq}")
        return {"seq": seq, "status": "ok"}

    job_id = manager.submit_job(sequences, flaky_worker)

    deadline = time.time() + 5.0
    status = None
    while time.time() < deadline:
        status = manager.get_status(job_id)
        assert status is not None
        if status["status"] == BatchJobStatus.COMPLETED.value:
            break
        time.sleep(0.02)

    assert status is not None
    assert status["status"] == "completed"
    assert status["total"] == 4
    assert status["completed"] == 4
    assert status["failed_count"] == 2
    assert len(status["results"]) == 2
    assert [r["seq"] for r in status["results"]] == ["VALID_A", "VALID_B"]
    assert len(status["errors"]) == 2
    assert status["errors"][0]["index"] == 1
    assert status["errors"][0]["sequence"] == "FAIL_1"
    assert "Processing failed for FAIL_1" in status["errors"][0]["error"]
    assert status["errors"][1]["index"] == 3
    assert status["errors"][1]["sequence"] == "FAIL_2"
    assert "Processing failed for FAIL_2" in status["errors"][1]["error"]
    manager.shutdown(wait=True)


def test_unknown_job_id():
    manager = BatchTaskManager(max_workers=1)
    assert manager.get_status("non-existent-id") is None
    assert manager.cancel_job("non-existent-id") is False
    manager.shutdown(wait=True)
