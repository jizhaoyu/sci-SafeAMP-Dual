"""Antigravity A2A (Agent-to-Agent) Bridge for SafeAMP-Dual & DTI Studio.

Coordinates tasks between the Desktop Antigravity IDE and Headless CLI (`agy.exe`).
Provides real-time streaming output, structured task dispatch, and result recording.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

# Force UTF-8 stdout/stderr under Windows GBK consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def find_agy_binary() -> str:
    """Resolve the absolute path to agy.exe on Windows/Linux."""
    which_path = shutil.which("agy")
    if which_path:
        return which_path
    candidates = [
        Path.home() / "AppData/Local/agy/bin/agy.exe",
        Path.home() / ".gemini/antigravity/bin/agy.exe",
        Path("C:/Users/888/AppData/Local/agy/bin/agy.exe")
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "agy"


ROOT = Path(__file__).resolve().parents[1]
A2A_DIR = ROOT / "output" / "a2a"
TASKS_DIR = A2A_DIR / "tasks"
RESULTS_DIR = A2A_DIR / "results"


def ensure_dirs():
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class A2ATask:
    task_id: str
    title: str
    description: str
    assigned_agent: str  # e.g., "cli-worker", "desktop-architect", "qa-tester"
    model: str = "gemini-3.8-flash-high"
    effort: str = "high"
    created_at: str = ""
    status: str = "pending"  # pending, in_progress, completed, failed
    params: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = utc_now_iso()


def save_task(task: A2ATask) -> Path:
    ensure_dirs()
    path = TASKS_DIR / f"{task.task_id}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(asdict(task), f, ensure_ascii=False, indent=2)
    return path


def list_tasks() -> List[Dict[str, Any]]:
    ensure_dirs()
    tasks = []
    for p in sorted(TASKS_DIR.glob("*.json")):
        try:
            with p.open("r", encoding="utf-8") as f:
                tasks.append(json.load(f))
        except Exception:
            pass
    return tasks


def execute_cli_subagent(
    prompt: str, 
    model: str = "gemini-3.8-flash-high", 
    effort: Optional[str] = None,
    timeout_sec: int = 180
) -> str:
    """Invoke agy.exe headlessly with streaming output to console."""
    agy_bin = find_agy_binary()
    cmd = [
        agy_bin,
        "--dangerously-skip-permissions",
        "--model", model,
        "-p", prompt
    ]
    if effort:
        cmd.extend(["--effort", effort])

    print(f"\n=======================================================")
    print(f"[*] [A2A Bridge] 启动 CLI 子智能体 (模型: {model})")
    print(f"[*] 执行命令: {' '.join(cmd[:4])} -p \"...\"")
    print(f"[*] 正在与 Antigravity CLI 建立双向流式连接...\n")

    start_time = time.time()
    collected_output: List[str] = []

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(ROOT)
        )

        for line in iter(proc.stdout.readline, ""):
            print(f"[CLI Worker] {line}", end="", flush=True)
            collected_output.append(line)

        proc.stdout.close()
        return_code = proc.wait(timeout=timeout_sec)
        elapsed = time.time() - start_time

        if return_code != 0:
            print(f"\n[!] [A2A Bridge] CLI 异常退出 (Exit Code: {return_code})")
        else:
            print(f"\n[OK] [A2A Bridge] CLI 子智能体执行完毕 (总耗时: {elapsed:.2f}s)")

        print("=======================================================\n")
        return "".join(collected_output)

    except Exception as e:
        print(f"\n[!] [A2A Bridge] 调用失败: {e}\n")
        return f"Error: {e}"


def dispatch_a2a_task(task: A2ATask) -> Dict[str, Any]:
    save_task(task)
    print(f"[*] [A2A Task Dispatcher] 正在派发任务 [{task.task_id}]: {task.title}")
    print(f"[*] 任务描述: {task.description}\n")

    output_text = execute_cli_subagent(
        prompt=task.description,
        model=task.model,
        effort=task.effort
    )

    result_record = {
        "task_id": task.task_id,
        "title": task.title,
        "assigned_agent": task.assigned_agent,
        "completed_at": utc_now_iso(),
        "status": "completed" if "Error:" not in output_text else "failed",
        "output_summary": output_text
    }

    result_path = RESULTS_DIR / f"{task.task_id}_result.json"
    with result_path.open("w", encoding="utf-8") as f:
        json.dump(result_record, f, ensure_ascii=False, indent=2)

    print(f"[OK] 回执已保存至: {result_path.relative_to(ROOT)}\n")
    return result_record


if __name__ == "__main__":
    test_task = A2ATask(
        task_id="task_003_agent_studio_check",
        title="Agent Studio 架构核查与协同验证",
        description="请核查当前新增的 A2A Agent Studio 前后端架构完整性，用两句话汇报状态。",
        assigned_agent="cli-worker"
    )
    dispatch_a2a_task(test_task)
