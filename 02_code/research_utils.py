"""General research utilities for file paths, hashing, timestamps, and JSON serialization."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    """Return ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def sha256(data: bytes | str | Path) -> str:
    """Compute hex-encoded SHA-256 digest of bytes, string, or file content."""
    if isinstance(data, Path):
        h = hashlib.sha256()
        with open(data, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def read_json(path: str | Path) -> Any:
    """Read JSON file safely with UTF-8 encoding."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, obj: Any, indent: int = 2) -> None:
    """Write object to JSON file with UTF-8 encoding and sorted keys."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent, sort_keys=True, ensure_ascii=False)
