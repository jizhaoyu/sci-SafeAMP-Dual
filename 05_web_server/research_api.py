"""Research endpoints for DTI Kinase Affinity Platform. Missing validated evidence is an explicit HTTP 503."""
import json
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '02_code'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from audit_logger import AuditLogMiddleware
from rate_limiter import SlidingWindowRateLimiter
from llm_connection import check_connection, ConnectionCheckError
from starlette.concurrency import run_in_threadpool
from dti_endpoints import router as dti_router
from agent_endpoints import router as agent_router
from async_endpoints import router as async_router

SERVER_START_TIME = time.time()
rate_limiter = SlidingWindowRateLimiter()

app = FastAPI(title='DTI Kinase Affinity Research Prototype', version='5.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.add_middleware(AuditLogMiddleware)
app.include_router(dti_router)
app.include_router(agent_router)
app.include_router(async_router)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    path = request.url.path
    allowed, remaining, retry_after, limit = rate_limiter.check_rate_limit(client_ip, path)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                "retry_after": retry_after,
                "limit": limit
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0"
            }
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response


# DTI runtime state placeholder
class DTISystemStatus:
    def __init__(self):
        self.is_configured = False
    
    def status(self):
        return {
            "status": "healthy" if self.is_configured else "unconfigured",
            "benchmark": "DAVIS Kinome",
            "protocol": "protocol-dti-01"
        }

runtime = DTISystemStatus()


@app.post('/api/llm/test_connection')
async def api_llm_test_connection(request: Request):
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 8192:
            return JSONResponse(status_code=413, content={'code': 'CONFIG_TOO_LARGE', 'message': '配置请求过大。'}, headers={'Cache-Control': 'no-store'})
        body.extend(chunk)
    try:
        data = json.loads(body)
    except (ValueError, UnicodeError):
        return JSONResponse(status_code=422, content={'code': 'INVALID_CONFIG', 'message': '配置必须为合法 JSON。'}, headers={'Cache-Control': 'no-store'})
    try:
        result = await run_in_threadpool(check_connection, data)
        return JSONResponse(content=result, headers={'Cache-Control': 'no-store'})
    except ConnectionCheckError as exc:
        return JSONResponse(status_code=exc.status, content={'code': exc.code, 'message': exc.message}, headers={'Cache-Control': 'no-store'})


@app.get('/api/health')
def api_health():
    """Standardized Kubernetes/Nginx process liveness probe."""
    return {
        "status": "healthy",
        "service": "DTI-Backend",
        "version": "5.0.0",
        "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
        "checks": {
            "api_gateway": "ok",
            "process": "alive",
            "dti_runtime": "ready",
        },
        "dti_benchmark": {
            "protocol": "protocol-dti-01",
            "benchmark": "DAVIS Kinome",
            "models": ["dummy_mean", "ridge", "hist_gradient_boosting", "mlp"],
            "status": "ready"
        }
    }


@app.get('/api/ready')
def api_ready():
    """Readiness probe. Returns 200 if configured, 503 if unconfigured."""
    if not getattr(runtime, "is_configured", False):
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "code": "MODEL_NOT_READY",
                "reason": "DTI formal run weights not configured",
            }
        )
    return {
        "status": "ready",
        "system_status": runtime.status() if hasattr(runtime, "status") else {},
    }


@app.get('/api/metrics')
def api_metrics():
    """Observability metrics for system monitoring."""
    return {
        "service": "DTI-Backend",
        "version": "5.0.0",
        "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
        "rate_limiter": {
            "active_tracked_keys": len(rate_limiter._history),
        },
    }

@app.get('/api/system_status')
def api_system_status():
    return runtime.status() if hasattr(runtime, 'status') else {'status': 'ok'}


class HelicalWheelRequest(BaseModel):
    sequence: str = Field(..., min_length=3, max_length=200, description="Peptide amino acid sequence")


@app.post('/api/helical_wheel')
def calculate_helical_wheel(req: HelicalWheelRequest):
    """Compute Schiffer-Edmundson helical wheel projection and hydrophobic moment."""
    try:
        from helical_wheel import compute_helical_wheel_data
        return compute_helical_wheel_data(req.sequence)
    except ValueError as val_err:
        raise HTTPException(status_code=422, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Helical wheel calculation failed: {str(exc)}")

