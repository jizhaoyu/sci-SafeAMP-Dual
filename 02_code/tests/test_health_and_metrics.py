"""Unit tests for /api/health, /api/metrics and rate limit middleware."""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_web_server"))
from research_api import app, rate_limiter


@pytest.fixture
def client():
    rate_limiter.reset()
    return TestClient(app)


def test_api_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "SafeAMP-Dual-Backend"
    assert "uptime_seconds" in data
    assert "checks" in data
    assert data["checks"]["api_gateway"] == "ok"
    assert data["checks"]["process"] == "alive"


def test_api_ready_endpoint(client, monkeypatch):
    import research_api
    # 1. Unloaded runtime: 503
    response = client.get("/api/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["code"] == "MODEL_NOT_READY"

    # 2. Mock loaded runtime: 200
    class MockRuntime:
        def status(self):
            return {
                "status": "healthy",
                "dual_task_model": {"weights_loaded": True, "status": "Validated"},
                "reason": None
            }
    monkeypatch.setattr(research_api, "runtime", MockRuntime())
    res_ready = client.get("/api/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"


def test_api_metrics_endpoint(client):
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "SafeAMP-Dual"
    assert "feature_cache" in data
    assert data["feature_cache"]["status"] == "not_integrated"
    assert "batch_jobs" in data
    assert "rate_limiter" in data
    assert "uptime_seconds" in data


def test_rate_limiting_middleware_429(client):
    # Set artificial tight quota and enable enforcement in test
    rate_limiter.limits["/api/predict_batch"] = (3, 10)
    rate_limiter.enforce_in_tests = True
    try:
        # 3 allowed
        for _ in range(3):
            res = client.post("/api/predict_batch", json={"sequences": ["GIGAVLKVLTTGLPALISWIKRKRQQ"]})
            assert res.status_code in (200, 503)  # 503 if model unloaded, but not 429!
            assert "X-RateLimit-Limit" in res.headers
            assert "X-RateLimit-Remaining" in res.headers

        # 4th must trigger 429
        res = client.post("/api/predict_batch", json={"sequences": ["GIGAVLKVLTTGLPALISWIKRKRQQ"]})
        assert res.status_code == 429
        data = res.json()
        assert data["code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in res.headers
        assert int(res.headers["Retry-After"]) >= 1
    finally:
        rate_limiter.enforce_in_tests = False
        rate_limiter.reset()
