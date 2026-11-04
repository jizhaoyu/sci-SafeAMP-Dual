"""Integration tests for async endpoints via FastAPI TestClient (P2 Milestone)."""
from __future__ import annotations

import sys
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = PROJECT_ROOT / "05_web_server"
CODE_DIR = PROJECT_ROOT / "02_code"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from research_api import app
from async_endpoints import task_manager

client = TestClient(app)


def test_submit_task_success():
    """Submit a valid kinase_profiling task and receive 202 Accepted."""
    payload = {
        "task_type": "kinase_profiling",
        "params": {
            "drug_smiles": "Cc1ccc(cc1Nc2nccc(n2)c3cccnc3)NC(=O)c4ccc(cc4)CN5CCN(CC5)C",
            "panel": "core"
        }
    }
    resp = client.post("/api/tasks/submit", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert "task_id" in data
    assert data["status"] in ("pending", "running")

    # Query status
    status_resp = client.get(f"/api/tasks/{data['task_id']}")
    assert status_resp.status_code == 200
    st_data = status_resp.json()
    assert st_data["task_id"] == data["task_id"]


def test_submit_task_idempotency():
    """Submitting same idempotency_key twice returns existing task_id with is_new=False."""
    key = f"test_idemp_{time.time()}"
    payload = {
        "task_type": "kinase_profiling",
        "params": {
            "drug_smiles": "Cc1ccc(cc1Nc2nccc(n2)c3cccnc3)NC(=O)c4ccc(cc4)CN5CCN(CC5)C",
            "panel": "core"
        },
        "idempotency_key": key
    }
    resp1 = client.post("/api/tasks/submit", json=payload)
    assert resp1.status_code == 202
    data1 = resp1.json()
    assert data1["is_new"] is True

    resp2 = client.post("/api/tasks/submit", json=payload)
    assert resp2.status_code == 202
    data2 = resp2.json()
    assert data2["is_new"] is False
    assert data2["task_id"] == data1["task_id"]


def test_task_not_found():
    """Non-existent task query returns 404."""
    resp = client.get("/api/tasks/non_existent_task_id_99999")
    assert resp.status_code == 404


def test_cancel_task():
    """Cancel endpoint accepts request and updates task."""
    from async_endpoints import task_manager
    task_id, _ = task_manager.store.create_task("kinase_profiling", {
        "drug_smiles": "Cc1ccc(cc1Nc2nccc(n2)c3cccnc3)NC(=O)c4ccc(cc4)CN5CCN(CC5)C",
        "panel": "core"
    })

    cancel_resp = client.post(f"/api/tasks/{task_id}/cancel", json={"reason": "测试取消"})
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["cancellation_requested"] is True
    task = task_manager.store.get_task(task_id)
    assert task["status"] == "cancelled"

    # Canceling an already terminal task returns consistent schema with cancellation_requested=False
    repeat_cancel = client.post(f"/api/tasks/{task_id}/cancel", json={"reason": "重复取消"})
    assert repeat_cancel.status_code == 200
    assert repeat_cancel.json()["cancellation_requested"] is False


def test_list_tasks():
    """GET /api/tasks lists tasks with correct shape."""
    resp = client.get("/api/tasks?limit=10")
    assert resp.status_code == 200
    tasks = resp.json()
    assert isinstance(tasks, list)
    if tasks:
        assert "task_id" in tasks[0]
        assert "status" in tasks[0]


def test_task_events_endpoint():
    """GET /api/tasks/{task_id}/events returns chronological sequence."""
    payload = {
        "task_type": "kinase_profiling",
        "params": {
            "drug_smiles": "Cc1ccc(cc1Nc2nccc(n2)c3cccnc3)NC(=O)c4ccc(cc4)CN5CCN(CC5)C",
            "panel": "core"
        }
    }
    resp = client.post("/api/tasks/submit", json=payload)
    task_id = resp.json()["task_id"]

    events_resp = client.get(f"/api/tasks/{task_id}/events")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert isinstance(events, list)
    assert len(events) >= 1
    assert events[0]["event_type"] == "task_created"
