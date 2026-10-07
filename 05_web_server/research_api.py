"""Research endpoints. Missing validated evidence is an explicit HTTP 503."""
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'02_code'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from feature_extractor import clean_sequence
from ai_optimizer import AIPeptideOptimizer
from helical_wheel import compute_helical_wheel_data
from inference_runtime import ResearchRuntime, ModelUnavailable
from batch_task_manager import BatchTaskManager
from audit_logger import AuditLogMiddleware
from rate_limiter import SlidingWindowRateLimiter
from feature_cache import SequenceFeatureCache
from llm_connection import check_connection, ConnectionCheckError
from starlette.concurrency import run_in_threadpool
from dti_endpoints import router as dti_router

SERVER_START_TIME = time.time()
rate_limiter = SlidingWindowRateLimiter()

app=FastAPI(title='SafeAMP-Dual & DTI research prototype',version='4.2.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.add_middleware(AuditLogMiddleware)
app.include_router(dti_router)

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

runtime=ResearchRuntime(os.environ.get('SAFEAMP_RUN_DIR'))
batch_manager=BatchTaskManager(max_workers=2)

@app.post('/api/llm/test_connection')
async def api_llm_test_connection(request: Request):
    # Manual decoding keeps FastAPI validation errors from echoing credentials.
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

class SequenceRequest(BaseModel):
    sequence: str=Field(min_length=3,max_length=4096)
class BatchPredictionRequest(BaseModel):
    sequences: list[str]=Field(min_length=1,max_length=128)
class LLMReportRequest(SequenceRequest):
    api_key: Optional[str]=None
    base_url: Optional[str]=None
    model_name: Optional[str]=None

def validate_sequence(value, idx=None):
    prefix = f'Sequence at index {idx}: ' if idx is not None else ''
    try:
        try:
            seq = clean_sequence(value)
        except ValueError as exc:
            raise ValueError(f'{prefix}{exc}') from exc
        if not 10 <= len(seq) <= 50:
            raise ValueError(f'{prefix}Research model domain is 10–50 residues.')
        return seq
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

def engine():
    try:runtime.load()
    except ModelUnavailable as exc:raise HTTPException(503,{'code':'MODEL_NOT_VALIDATED','message':str(exc)}) from exc
    return AIPeptideOptimizer(runtime,runtime.extractor)

@app.get('/api/system_status')
def api_system_status():return runtime.status()

@app.get('/api/health')
def api_health():
    """Standardized Kubernetes/Nginx process liveness probe."""
    return {
        "status": "healthy",
        "service": "SafeAMP-Dual-Backend",
        "version": "4.2.0",
        "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
        "checks": {
            "api_gateway": "ok",
            "process": "alive",
            "feature_cache": "ready",
            "batch_manager": "ready" if batch_manager else "offline",
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
    """Model and research runtime readiness probe. Returns 200 if loaded, 503 if unconfigured or unvalidated."""
    status_info = runtime.status()
    is_ready = status_info.get("status") == "healthy" and status_info.get("dual_task_model", {}).get("weights_loaded", False)
    if not is_ready:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "code": "MODEL_NOT_READY",
                "reason": status_info.get("reason", "Model weights not loaded or run not validated"),
                "system_status": status_info,
            }
        )
    return {
        "status": "ready",
        "system_status": status_info,
    }

@app.get('/api/metrics')
def api_metrics():
    """Real-time observability metrics for system monitoring."""
    cache_obj = SequenceFeatureCache()
    stats = cache_obj.get_stats()
    stats["status"] = "not_integrated"
    stats["note"] = "SequenceFeatureCache is not integrated with research runtime inference; real hit rates unavailable"
    with batch_manager._lock:
        active_jobs = sum(1 for j in batch_manager._jobs.values() if j.get("status") in ("running", "queued"))
        completed_jobs = sum(1 for j in batch_manager._jobs.values() if j.get("status") == "completed")
        failed_jobs = sum(1 for j in batch_manager._jobs.values() if j.get("status") == "failed")
        total_jobs = len(batch_manager._jobs)

    return {
        "service": "SafeAMP-Dual",
        "version": "4.2.0",
        "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
        "feature_cache": stats,
        "batch_jobs": {
            "total_submitted": total_jobs,
            "active": active_jobs,
            "completed": completed_jobs,
            "failed": failed_jobs,
        },
        "rate_limiter": {
            "active_tracked_keys": len(rate_limiter._history),
        },
    }

@app.post('/api/predict_batch')
def api_predict_batch(req:BatchPredictionRequest):
    sequences=[validate_sequence(x, idx=i) for i, x in enumerate(req.sequences)]
    e=engine();result=[]
    for seq in sequences:
        a,h,score=e.evaluate_sequence(seq)
        result.append({'sequence':seq,'length':len(seq),'amp_probability':a,'hemo_probability':h,
                       'ranking_score':score,'therapeutic_safety_index':score,'is_safe':None,
                       'is_short':False,'short_note':'','residues':e.compute_residue_attributions(seq),
                       'attribution_type':'physicochemical_heuristic','provenance':runtime.metadata,
                       'warning':'Research prediction; no clinical safety or measured efficacy claim. Legacy TSI field is a ranking score.'})
    return result

@app.post('/api/ai_optimize')
def api_ai_optimize(req:SequenceRequest):
    seq=validate_sequence(req.sequence);e=engine()
    return {'status':'exploratory','original_sequence':seq,'solutions':e.optimize_mutations(seq),
            'provenance':runtime.metadata,'warning':'Same-model ranking is not independent experimental validation.'}

@app.post('/api/ai_report')
def api_ai_report(req:LLMReportRequest):
    seq=validate_sequence(req.sequence);e=engine()
    report=e.generate_scientific_report(seq)
    report['provenance']=runtime.metadata
    if req.api_key:report['custom_llm_error']='This research endpoint returns evidence-bounded local reports; no sequence was sent externally.'
    return report

@app.post('/api/helical_wheel')
def api_helical_wheel(req:SequenceRequest):
    try:
        seq=clean_sequence(req.sequence)
        if not 3<=len(seq)<=50:raise ValueError('Interactive physicochemical projection supports 3–50 canonical residues.')
        return compute_helical_wheel_data(seq)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@app.post('/api/batch_jobs')
def api_submit_batch_job(req:BatchPredictionRequest):
    sequences=[validate_sequence(x, idx=i) for i, x in enumerate(req.sequences)]
    engine()

    def _worker(seq: str):
        e = engine()
        a, h, score = e.evaluate_sequence(seq)
        return {
            'sequence': seq,
            'length': len(seq),
            'amp_probability': a,
            'hemo_probability': h,
            'ranking_score': score,
            'therapeutic_safety_index': score,
            'is_safe': None,
            'is_short': False,
            'short_note': '',
            'residues': e.compute_residue_attributions(seq),
            'attribution_type': 'physicochemical_heuristic',
            'provenance': runtime.metadata,
            'warning': 'Research prediction; no clinical safety or measured efficacy claim. Legacy TSI field is a ranking score.'
        }

    job_id = batch_manager.submit_job(sequences, _worker)
    return {"job_id": job_id, "status": "queued", "total": len(sequences)}

@app.get('/api/batch_jobs/{job_id}')
def api_get_batch_job(job_id: str):
    job = batch_manager.get_status(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job

@app.delete('/api/batch_jobs/{job_id}')
def api_cancel_batch_job(job_id: str):
    cancelled = batch_manager.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(404, "Job not found")
    return {"job_id": job_id, "status": "cancelled"}
