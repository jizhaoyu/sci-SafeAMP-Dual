"""Unit tests for sliding window rate limiter."""
import sys
import time
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_web_server"))
from rate_limiter import SlidingWindowRateLimiter


def test_rate_limiter_basic_allow():
    limiter = SlidingWindowRateLimiter(limits={"/api/": (5, 10)})
    for i in range(5):
        allowed, remaining, retry_after, limit = limiter.check_rate_limit("1.2.3.4", "/api/test")
        assert allowed is True
        assert remaining == 5 - (i + 1)
        assert retry_after == 0


def test_rate_limiter_blocks_on_exceed():
    limiter = SlidingWindowRateLimiter(limits={"/api/": (3, 5)})
    # Consume 3
    for _ in range(3):
        allowed, _, _, _ = limiter.check_rate_limit("1.2.3.4", "/api/test")
        assert allowed is True

    # 4th request must be rejected
    allowed, remaining, retry_after, limit = limiter.check_rate_limit("1.2.3.4", "/api/test")
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0
    assert limit == 3


def test_rate_limiter_health_bypass():
    limiter = SlidingWindowRateLimiter(limits={"/api/": (1, 60)})
    # Health checks should never be rate limited
    for _ in range(10):
        allowed, _, _, _ = limiter.check_rate_limit("1.2.3.4", "/api/health")
        assert allowed is True


def test_rate_limiter_separate_ips_and_tiers():
    limiter = SlidingWindowRateLimiter(limits={
        "/api/ai_report": (2, 10),
        "/api/": (5, 10),
    })

    # IP 1 uses up AI report quota
    assert limiter.check_rate_limit("1.1.1.1", "/api/ai_report")[0] is True
    assert limiter.check_rate_limit("1.1.1.1", "/api/ai_report")[0] is True
    assert limiter.check_rate_limit("1.1.1.1", "/api/ai_report")[0] is False

    # IP 2 still has quota for AI report
    assert limiter.check_rate_limit("2.2.2.2", "/api/ai_report")[0] is True

    # IP 1 still has quota for general API
    assert limiter.check_rate_limit("1.1.1.1", "/api/predict_batch")[0] is True


def test_optimize_lead_route_is_strictly_rate_limited():
    limiter = SlidingWindowRateLimiter()
    for _ in range(6):
        allowed, _, _, limit = limiter.check_rate_limit("1.2.3.4", "/api/dti/optimize_lead")
        assert allowed is True
        assert limit == 6
    allowed, remaining, retry_after, limit = limiter.check_rate_limit("1.2.3.4", "/api/dti/optimize_lead")
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0
    assert limit == 6
