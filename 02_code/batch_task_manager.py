"""Asynchronous batch task manager for high-throughput prediction jobs."""
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class BatchJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchTaskManager:
    """Manages thread-safe asynchronous execution of batch prediction jobs."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()
        self._jobs: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _current_timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def submit_job(self, sequences: List[str], worker_fn: Callable[[str], Any]) -> str:
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        now = self._current_timestamp()
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": BatchJobStatus.QUEUED.value,
                "total": len(sequences),
                "completed": 0,
                "failed_count": 0,
                "results": [],
                "errors": [],
                "created_at": now,
                "updated_at": now,
                "_cancel_flag": False,
                "_sequences": list(sequences),
                "_worker_fn": worker_fn,
            }
        self._executor.submit(self._execute_job, job_id)
        return job_id

    def _execute_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if job["_cancel_flag"]:
                job["status"] = BatchJobStatus.CANCELLED.value
                job["updated_at"] = self._current_timestamp()
                return
            job["status"] = BatchJobStatus.RUNNING.value
            job["updated_at"] = self._current_timestamp()
            sequences = list(job["_sequences"])
            worker_fn = job["_worker_fn"]

        try:
            for idx, seq in enumerate(sequences):
                with self._lock:
                    if job["_cancel_flag"]:
                        job["status"] = BatchJobStatus.CANCELLED.value
                        job["updated_at"] = self._current_timestamp()
                        return

                try:
                    res = worker_fn(seq)
                    with self._lock:
                        if job["_cancel_flag"]:
                            job["status"] = BatchJobStatus.CANCELLED.value
                            job["updated_at"] = self._current_timestamp()
                            return
                        job["results"].append(res)
                        job["completed"] += 1
                        job["updated_at"] = self._current_timestamp()
                except Exception as exc:
                    with self._lock:
                        if job["_cancel_flag"]:
                            job["status"] = BatchJobStatus.CANCELLED.value
                            job["updated_at"] = self._current_timestamp()
                            return
                        job["errors"].append({
                            "index": idx,
                            "sequence": seq[:15],
                            "error": str(exc),
                        })
                        job["failed_count"] += 1
                        job["completed"] += 1
                        job["updated_at"] = self._current_timestamp()

            with self._lock:
                if job["_cancel_flag"]:
                    job["status"] = BatchJobStatus.CANCELLED.value
                else:
                    job["status"] = BatchJobStatus.COMPLETED.value
                job["updated_at"] = self._current_timestamp()
        except Exception as fatal_exc:
            with self._lock:
                job["status"] = BatchJobStatus.FAILED.value
                job["errors"].append({
                    "index": -1,
                    "sequence": "",
                    "error": f"Fatal execution error: {str(fatal_exc)}",
                })
                job["updated_at"] = self._current_timestamp()

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return {
                k: (list(v) if isinstance(v, list) else v)
                for k, v in job.items()
                if not k.startswith("_")
            }

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            job["_cancel_flag"] = True
            job["status"] = BatchJobStatus.CANCELLED.value
            job["updated_at"] = self._current_timestamp()
            return True

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)
