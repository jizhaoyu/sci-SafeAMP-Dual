"""Tests for request tracking middleware and structured audit logging."""
import concurrent.futures
import json
import sys
import uuid
from pathlib import Path
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_code"))
sys.path.insert(0, str(ROOT / "05_web_server"))

import audit_logger
from audit_logger import AUDIT_LOG_FILE, AuditLogMiddleware, read_audit_logs
from inference_runtime import ResearchRuntime
import research_api


def test_default_audit_log_file_location():
    """Verify default audit log path matches ROOT / output / audit / api_audit.jsonl."""
    expected = ROOT / "output" / "audit" / "api_audit.jsonl"
    assert AUDIT_LOG_FILE == expected


def test_request_id_injected_in_response():
    """Test that X-Request-ID is injected in the response headers when none was supplied."""
    client = TestClient(research_api.app)
    res = client.get("/api/system_status")
    assert res.status_code == 200
    req_id = res.headers.get("x-request-id")
    assert req_id is not None
    assert req_id.startswith("req-")
    assert len(req_id) > 4


def test_audit_log_written():
    """Test that api_audit.jsonl contains a valid JSON line with required fields."""
    client = TestClient(research_api.app)
    res = client.get("/api/system_status")
    assert res.status_code == 200
    req_id = res.headers.get("x-request-id")
    assert req_id is not None

    assert AUDIT_LOG_FILE.exists()
    logs = read_audit_logs()
    matching = [entry for entry in logs if entry.get("request_id") == req_id]
    assert len(matching) == 1

    entry = matching[0]
    assert entry["request_id"] == req_id
    assert entry["path"] == "/api/system_status"
    assert entry["method"] == "GET"
    assert entry["status_code"] == 200
    assert "duration_ms" in entry
    assert isinstance(entry["duration_ms"], (int, float))
    assert entry["duration_ms"] >= 0
    assert "timestamp" in entry
    assert "client_ip" in entry


def test_custom_request_id_preserved():
    """Test that client-supplied X-Request-ID is preserved in response and audit log."""
    client = TestClient(research_api.app)
    custom_id = f"my-custom-id-{uuid.uuid4().hex[:8]}"
    res = client.get("/api/system_status", headers={"X-Request-ID": custom_id})
    assert res.status_code == 200
    assert res.headers.get("x-request-id") == custom_id

    logs = read_audit_logs()
    matching = [entry for entry in logs if entry.get("request_id") == custom_id]
    assert len(matching) == 1
    assert matching[0]["request_id"] == custom_id
    assert matching[0]["path"] == "/api/system_status"


def test_audit_log_records_error_status(monkeypatch):
    """Test that 422 and 503 error status codes are accurately recorded in audit log."""
    monkeypatch.setattr(research_api, "runtime", ResearchRuntime())
    client = TestClient(research_api.app)

    # 422 Unprocessable Entity
    res_422 = client.post("/api/predict_batch", json={"sequences": []})
    assert res_422.status_code == 422
    req_422 = res_422.headers.get("x-request-id")
    assert req_422 is not None

    # 503 Model Unavailable
    seq = "ACDEFGHIKLMNPQ"
    res_503 = client.post("/api/predict_batch", json={"sequences": [seq]})
    assert res_503.status_code == 503
    req_503 = res_503.headers.get("x-request-id")
    assert req_503 is not None

    logs = read_audit_logs()
    entries_422 = [e for e in logs if e.get("request_id") == req_422]
    assert len(entries_422) == 1
    assert entries_422[0]["status_code"] == 422
    assert entries_422[0]["path"] == "/api/predict_batch"

    entries_503 = [e for e in logs if e.get("request_id") == req_503]
    assert len(entries_503) == 1
    assert entries_503[0]["status_code"] == 503
    assert entries_503[0]["path"] == "/api/predict_batch"


def test_audit_log_records_unhandled_exception(tmp_path):
    """Test that unhandled exceptions log status 500, error_type, and re-raise."""
    test_log = tmp_path / "unhandled_audit.jsonl"
    app = FastAPI()
    app.add_middleware(AuditLogMiddleware, log_file=test_log)

    @app.get("/crash")
    def crash():
        raise RuntimeError("Simulated unhandled failure")

    # With raise_server_exceptions=False, FastAPI ServerErrorMiddleware returns 500
    client = TestClient(app, raise_server_exceptions=False)
    custom_id = "req-crash-test-01"
    res = client.get("/crash", headers={"X-Request-ID": custom_id})
    assert res.status_code == 500

    logs = read_audit_logs(test_log)
    assert len(logs) == 1
    entry = logs[0]
    assert entry["request_id"] == custom_id
    assert entry["status_code"] == 500
    assert entry["error_type"] == "RuntimeError"
    assert entry["path"] == "/crash"
    assert "duration_ms" in entry

    # Verify re-raise behavior with raise_server_exceptions=True
    client_raise = TestClient(app, raise_server_exceptions=True)
    with pytest.raises(RuntimeError, match="Simulated unhandled failure"):
        client_raise.get("/crash")


def test_concurrent_audit_logging(tmp_path):
    """Verify thread-safe logging under concurrent client requests."""
    test_log = tmp_path / "concurrent_audit.jsonl"
    app = FastAPI()
    app.add_middleware(AuditLogMiddleware, log_file=test_log)

    @app.get("/ping")
    def ping():
        return {"ping": "pong"}

    client = TestClient(app)
    n_requests = 40

    def worker(i: int):
        req_id = f"concurrent-{i}-{uuid.uuid4().hex[:6]}"
        r = client.get("/ping", headers={"X-Request-ID": req_id})
        return r.status_code, req_id

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(worker, range(n_requests)))

    for status, _ in results:
        assert status == 200

    logs = read_audit_logs(test_log)
    assert len(logs) == n_requests
    logged_ids = {entry["request_id"] for entry in logs}
    expected_ids = {req_id for _, req_id in results}
    assert logged_ids == expected_ids
