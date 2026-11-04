"""Persistent SQLite Task & Job Store for asynchronous computation tasks.

Features:
- Full state machine: pending -> running -> completed | failed | cancelled | interrupted
- Event sequence numbering and logging
- Idempotent task creation via idempotency_key
- Structured progress tracking (stage, current, total, percentage)
- On-startup recovery: marks orphaned running/pending jobs as 'interrupted'
- Safe result payload persistence to output/task_results/
"""
from __future__ import annotations

import os
import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "output" / "async_jobs.db"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "output" / "task_results"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_task_params(params: Any) -> Any:
    """Recursively redact sensitive credential keys in stored parameters."""
    if isinstance(params, dict):
        sanitized = {}
        for k, v in params.items():
            if any(secret_kw in str(k).lower() for secret_kw in ("api_key", "secret", "password", "token", "credential")):
                sanitized[k] = "******" if v else ""
            else:
                sanitized[k] = _sanitize_task_params(v)
        return sanitized
    elif isinstance(params, list):
        return [_sanitize_task_params(item) for item in params]
    return params


class AsyncJobStore:
    """Thread-safe SQLite-backed job store."""

    def __init__(
        self,
        db_path: Optional[Path | str] = None,
        results_dir: Optional[Path | str] = None,
        auto_recover: bool = False
    ):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.results_dir = Path(results_dir) if results_dir else DEFAULT_RESULTS_DIR
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()
        if auto_recover:
            self.mark_interrupted_on_startup()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def _init_db(self) -> None:
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS async_tasks (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    idempotency_key TEXT UNIQUE,
                    progress REAL DEFAULT 0.0,
                    progress_stage TEXT DEFAULT '',
                    progress_current INTEGER DEFAULT 0,
                    progress_total INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    updated_at TEXT NOT NULL,
                    params_json TEXT,
                    result_summary_json TEXT,
                    result_path TEXT,
                    error_message TEXT,
                    cancellation_requested INTEGER DEFAULT 0
                )
                """)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    event_seq INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    data_json TEXT,
                    FOREIGN KEY(task_id) REFERENCES async_tasks(task_id)
                )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON async_tasks(status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_type ON async_tasks(task_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_task ON task_events(task_id, event_seq)")
                conn.commit()

    def mark_interrupted_on_startup(self) -> int:
        """Find any pending or running tasks from prior crashed process and mark as interrupted."""
        now = _utc_now_iso()
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    UPDATE async_tasks
                    SET status = 'interrupted',
                        error_message = '服务异常重启，未完成任务已自动标记为中断',
                        finished_at = ?,
                        updated_at = ?
                    WHERE status IN ('pending', 'running')
                """, (now, now))
                interrupted_count = cursor.rowcount
                conn.commit()
                return interrupted_count

    def create_task(
        self,
        task_type: str,
        params: Dict[str, Any],
        task_id: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Creates a task or returns existing if idempotency_key matches.
        Returns: (task_id, is_new)
        """
        with self._lock:
            with self._get_connection() as conn:
                if idempotency_key:
                    row = conn.execute(
                        "SELECT task_id FROM async_tasks WHERE idempotency_key = ?",
                        (idempotency_key,)
                    ).fetchone()
                    if row:
                        return row["task_id"], False

                actual_id = task_id or f"task_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = _utc_now_iso()
                sanitized_params = _sanitize_task_params(params)
                params_str = json.dumps(sanitized_params, ensure_ascii=False)

                conn.execute("""
                    INSERT INTO async_tasks (
                        task_id, task_type, status, idempotency_key,
                        progress, progress_stage, progress_current, progress_total,
                        created_at, updated_at, params_json, cancellation_requested
                    ) VALUES (?, ?, 'pending', ?, 0.0, '排队中', 0, 0, ?, ?, ?, 0)
                """, (actual_id, task_type, idempotency_key, now, now, params_str))

                # Emit creation event
                conn.execute("""
                    INSERT INTO task_events (task_id, event_seq, event_type, created_at, data_json)
                    VALUES (?, 1, 'task_created', ?, ?)
                """, (actual_id, now, json.dumps({"task_type": task_type}, ensure_ascii=False)))
                conn.commit()
                return actual_id, True

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                row = conn.execute("SELECT * FROM async_tasks WHERE task_id = ?", (task_id,)).fetchone()
                if not row:
                    return None
                data = dict(row)
                data["cancellation_requested"] = bool(data["cancellation_requested"])
                if data["params_json"]:
                    data["params"] = json.loads(data["params_json"])
                else:
                    data["params"] = {}
                if data["result_summary_json"]:
                    data["result_summary"] = json.loads(data["result_summary_json"])
                else:
                    data["result_summary"] = None
                return data

    def list_tasks(
        self,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                query = "SELECT * FROM async_tasks"
                clauses = []
                args: List[Any] = []
                if task_type:
                    clauses.append("task_type = ?")
                    args.append(task_type)
                if status:
                    clauses.append("status = ?")
                    args.append(status)
                if clauses:
                    query += " WHERE " + " AND ".join(clauses)
                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                args.extend([limit, offset])

                rows = conn.execute(query, args).fetchall()
                results = []
                for r in rows:
                    item = dict(r)
                    item["cancellation_requested"] = bool(item["cancellation_requested"])
                    if item["params_json"]:
                        item["params"] = json.loads(item["params_json"])
                    if item["result_summary_json"]:
                        item["result_summary"] = json.loads(item["result_summary_json"])
                    results.append(item)
                return results

    def mark_started(self, task_id: str) -> bool:
        now = _utc_now_iso()
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE async_tasks
                    SET status = 'running',
                        started_at = COALESCE(started_at, ?),
                        updated_at = ?,
                        progress_stage = '正在执行'
                    WHERE task_id = ? AND status = 'pending'
                """, (now, now, task_id))
                self._record_event_unlocked(conn, task_id, "task_started", {"timestamp": now})
                conn.commit()
                return True

    def update_progress(
        self,
        task_id: str,
        stage: str,
        current: int,
        total: int,
        message: Optional[str] = None
    ) -> None:
        progress_val = 0.0 if total <= 0 else min(1.0, max(0.0, float(current) / float(total)))
        now = _utc_now_iso()
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE async_tasks
                    SET progress = ?,
                        progress_stage = ?,
                        progress_current = ?,
                        progress_total = ?,
                        updated_at = ?
                    WHERE task_id = ? AND status = 'running'
                """, (progress_val, stage, current, total, now, task_id))
                self._record_event_unlocked(conn, task_id, "progress_update", {
                    "stage": stage,
                    "current": current,
                    "total": total,
                    "progress": progress_val,
                    "message": message
                })
                conn.commit()

    def request_cancellation(self, task_id: str) -> bool:
        now = _utc_now_iso()
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    UPDATE async_tasks
                    SET cancellation_requested = 1,
                        updated_at = ?
                    WHERE task_id = ? AND status IN ('pending', 'running')
                """, (now, task_id))
                if cursor.rowcount > 0:
                    self._record_event_unlocked(conn, task_id, "cancellation_requested", {"timestamp": now})
                    conn.commit()
                    return True
                return False

    def is_cancellation_requested(self, task_id: str) -> bool:
        with self._lock:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT cancellation_requested FROM async_tasks WHERE task_id = ?",
                    (task_id,)
                ).fetchone()
                return bool(row["cancellation_requested"]) if row else False

    def cancel_task(
        self,
        task_id: str,
        reason: str = "用户主动取消任务",
        result_summary: Optional[Dict[str, Any]] = None
    ) -> bool:
        now = _utc_now_iso()
        summary_str = json.dumps(result_summary, ensure_ascii=False) if result_summary is not None else None
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    UPDATE async_tasks
                    SET status = 'cancelled',
                        error_message = ?,
                        result_summary_json = COALESCE(?, result_summary_json),
                        finished_at = ?,
                        updated_at = ?,
                        progress_stage = '已取消'
                    WHERE task_id = ? AND status IN ('pending', 'running')
                """, (reason, summary_str, now, now, task_id))
                if cursor.rowcount > 0:
                    self._record_event_unlocked(conn, task_id, "task_cancelled", {"reason": reason})
                    conn.commit()
                    return True
                return False

    def complete_task(
        self,
        task_id: str,
        result_summary: Dict[str, Any],
        full_result_payload: Optional[Dict[str, Any]] = None
    ) -> bool:
        now = _utc_now_iso()
        summary_str = json.dumps(result_summary, ensure_ascii=False)
        tmp_file: Optional[Path] = None
        out_file: Optional[Path] = None
        result_path_str: Optional[str] = None

        if full_result_payload is not None:
            out_file = self.results_dir / f"{task_id}_result.json"
            tmp_file = self.results_dir / f"{task_id}_result.tmp.{uuid.uuid4().hex[:8]}"
            tmp_file.write_text(json.dumps(full_result_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            result_path_str = str(out_file)

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    UPDATE async_tasks
                    SET status = 'completed',
                        progress = 1.0,
                        progress_stage = '已完成',
                        result_summary_json = ?,
                        result_path = ?,
                        finished_at = ?,
                        updated_at = ?
                    WHERE task_id = ? AND status IN ('pending', 'running')
                """, (summary_str, result_path_str, now, now, task_id))
                if cursor.rowcount > 0:
                    if tmp_file is not None and out_file is not None:
                        os.replace(str(tmp_file), str(out_file))
                    self._record_event_unlocked(conn, task_id, "task_completed", {"result_summary": result_summary})
                    conn.commit()
                    return True
                else:
                    if tmp_file is not None and tmp_file.exists():
                        try:
                            tmp_file.unlink()
                        except Exception:
                            pass
                    return False

    def fail_task(self, task_id: str, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> bool:
        now = _utc_now_iso()
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    UPDATE async_tasks
                    SET status = 'failed',
                        error_message = ?,
                        progress_stage = '执行失败',
                        finished_at = ?,
                        updated_at = ?
                    WHERE task_id = ? AND status IN ('pending', 'running')
                """, (error_message, now, now, task_id))
                if cursor.rowcount > 0:
                    self._record_event_unlocked(conn, task_id, "task_failed", {
                        "error": error_message,
                        "details": error_details
                    })
                    conn.commit()
                    return True
                return False

    def get_task_events(self, task_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                rows = conn.execute("""
                    SELECT event_seq, event_type, created_at, data_json
                    FROM task_events
                    WHERE task_id = ?
                    ORDER BY event_seq ASC
                """, (task_id,)).fetchall()
                events = []
                for r in rows:
                    d = dict(r)
                    if d["data_json"]:
                        d["data"] = json.loads(d["data_json"])
                    events.append(d)
                return events

    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self.get_task(task_id)
        if not task:
            return None
        if task.get("result_path") and Path(task["result_path"]).is_file():
            try:
                return json.loads(Path(task["result_path"]).read_text(encoding="utf-8"))
            except Exception as exc:
                raise ValueError(f"Task result file '{task['result_path']}' is corrupted: {exc}")
        return task.get("result_summary")

    def _record_event_unlocked(self, conn: sqlite3.Connection, task_id: str, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        last_seq_row = conn.execute(
            "SELECT MAX(event_seq) as max_seq FROM task_events WHERE task_id = ?",
            (task_id,)
        ).fetchone()
        next_seq = (last_seq_row["max_seq"] or 0) + 1
        now = _utc_now_iso()
        conn.execute("""
            INSERT INTO task_events (task_id, event_seq, event_type, created_at, data_json)
            VALUES (?, ?, ?, ?, ?)
        """, (task_id, next_seq, event_type, now, json.dumps(data or {}, ensure_ascii=False)))
