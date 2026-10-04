"""Request tracking middleware and structured audit logging."""
import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from research_utils import ROOT, utc_now

AUDIT_LOG_FILE = ROOT / "output" / "audit" / "api_audit.jsonl"
_file_lock = threading.Lock()


class AuditLogMiddleware(BaseHTTPMiddleware):
    """FastAPI/Starlette middleware for X-Request-ID propagation, latency timing,
    and structured JSONL audit logging.
    """

    def __init__(self, app, log_file: Optional[Path] = None):
        super().__init__(app)
        self._custom_log_file = Path(log_file) if log_file is not None else None
        self._lock = _file_lock

    @property
    def log_file(self) -> Path:
        if self._custom_log_file is not None:
            return self._custom_log_file
        # Allow dynamic monkeypatching of module-level AUDIT_LOG_FILE
        return AUDIT_LOG_FILE

    def _append_log(self, entry: Dict[str, Any]) -> None:
        target_file = self.log_file
        target_file.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with self._lock:
            with open(target_file, "a", encoding="utf-8") as f:
                f.write(line)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        raw_id = request.headers.get("x-request-id")
        request_id = raw_id.strip() if raw_id and raw_id.strip() else f"req-{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            log_entry = {
                "timestamp": utc_now(),
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
            }
            self._append_log(log_entry)
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            log_entry = {
                "timestamp": utc_now(),
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
                "error_type": type(exc).__name__,
            }
            try:
                self._append_log(log_entry)
            except Exception:
                pass
            raise


def read_audit_logs(log_file: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Read all structured audit log entries from the specified or default file."""
    path = Path(log_file) if log_file is not None else AUDIT_LOG_FILE
    if not path.is_file():
        return []
    with _file_lock:
        content = path.read_text(encoding="utf-8")
    entries = []
    for line in content.splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries
