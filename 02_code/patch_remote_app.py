#!/usr/bin/env python3
"""Idempotently patch remote app.py with rate limiter, health, and metrics endpoints."""
from pathlib import Path
import re
import sys

TARGET_APP = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/ubuntu/safeamp-server/app.py")

RATE_LIMITER_SNIPPET = """
import time
from rate_limiter import SlidingWindowRateLimiter

rate_limiter = SlidingWindowRateLimiter()
server_start_time = time.time()


@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path

    allowed, remaining, retry_after, limit = rate_limiter.check_rate_limit(client_ip, path)
    if not allowed:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "message": f"Rate limit exceeded ({limit} requests/window). Please retry later.",
                "retry_after_seconds": retry_after
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(retry_after)
            }
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response
"""

ENDPOINTS_SNIPPET = """
@app.get("/api/health")
def api_health():
    \"\"\"Standardized health and liveness probe for monitoring and load balancers.\"\"\"
    return {
        "status": "ok",
        "service": "safeamp-api",
        "version": "2.5.0",
        "timestamp": time.time(),
        "uptime_seconds": round(time.time() - server_start_time, 2),
        "models": {
            "esm_backend": getattr(extractor, "backend", "unknown"),
            "weights_loaded": os.path.exists(weights_path)
        }
    }


@app.get("/api/metrics")
def api_metrics():
    \"\"\"Real-time observability metrics for SafeAMP server.\"\"\"
    limiter_stats = rate_limiter.get_stats()
    return {
        "uptime_seconds": round(time.time() - server_start_time, 2),
        "rate_limiter": limiter_stats,
        "feature_cache": {
            "size": len(getattr(extractor, "_cache", {})),
            "max_size": getattr(extractor, "_cache_max_size", 1000)
        },
        "device": "CPU (Optimized Vectorized SIMD)",
        "framework": f"PyTorch {torch.__version__}"
    }
"""

def main():
    if not TARGET_APP.exists():
        print(f"Error: {TARGET_APP} not found")
        sys.exit(1)

    content = TARGET_APP.read_text(encoding="utf-8")

    # If already patched with erroneous keyword args, fix it immediately
    if "default_limit=" in content:
        content = re.sub(
            r"rate_limiter\s*=\s*SlidingWindowRateLimiter\([^)]*\)",
            "rate_limiter = SlidingWindowRateLimiter()",
            content,
            flags=re.DOTALL
        )
        TARGET_APP.write_text(content, encoding="utf-8")
        print(f"Fixed rate_limiter initialization signature in {TARGET_APP}.")
        return

    if "SlidingWindowRateLimiter" in content and "/api/health" in content:
        print(f"{TARGET_APP} is already patched. Nothing to do.")
        return

    # 1. Insert rate limiter setup after AIPeptideOptimizer initialization
    if "ai_engine = AIPeptideOptimizer(model, extractor)" in content:
        content = content.replace(
            "ai_engine = AIPeptideOptimizer(model, extractor)",
            "ai_engine = AIPeptideOptimizer(model, extractor)\n" + RATE_LIMITER_SNIPPET
        )
    else:
        # Fallback: insert before SequenceRequest
        content = content.replace(
            "class SequenceRequest(BaseModel):",
            RATE_LIMITER_SNIPPET + "\n\nclass SequenceRequest(BaseModel):"
        )

    # 2. Insert endpoints before or after @app.get("/api/system_status")
    if '@app.get("/api/system_status")' in content:
        content = content.replace(
            '@app.get("/api/system_status")',
            ENDPOINTS_SNIPPET + '\n\n@app.get("/api/system_status")'
        )
    else:
        content += "\n" + ENDPOINTS_SNIPPET

    TARGET_APP.write_text(content, encoding="utf-8")
    print(f"Successfully patched {TARGET_APP} with Rate Limiter, Health, and Metrics endpoints.")

if __name__ == "__main__":
    main()
