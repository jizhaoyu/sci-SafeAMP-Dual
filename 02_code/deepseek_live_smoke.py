"""Bounded real DeepSeek calls using nonresearch fixtures and secret-free audit files."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = {
    "fixture_kind": "synthetic_engineering_fixture", "engineering_records": 12,
    "artifact_verified": True, "formal_research_status": "blocked",
    "eligible_external_records": 0, "publication_ready": False,
}
SUMMARY = "Synthetic fixture; not research results."
LIMITATIONS = ["Artifact verification does not release blocked research.", "Publication is not approved."]
PROTECTED = {
    "04_paper/research_status.json": "846c1fc2452646f3df9c2055b0a4a1b5140132acc2433bb2c304b133b6e8012c",
    "03_experiments/deliveries/mic_baseline_20261004_v1/manifest.json": "f8b8606dc807279cc78c6728260f6d3d7da463f2416bf47e8d3bafbdf1789ed3",
    "03_experiments/deliveries/mic_baseline_20261004_v1.zip": "858f6aa9a09dfc822b6a7c155a629ae13caf0e2c922abe3448d81119e3491b2b",
}


@dataclass(frozen=True)
class Config:
    api_key: str
    endpoint: str
    model: str
    credential_source: str


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def endpoint(base_url: str) -> str:
    parsed = urllib.parse.urlsplit(base_url.strip())
    if (parsed.scheme != "https" or parsed.hostname != "api.deepseek.com"
            or parsed.netloc.lower() != "api.deepseek.com" or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Only the official DeepSeek HTTPS host without URL credentials is allowed")
    path = parsed.path.rstrip("/")
    if path not in ("", "/v1", "/chat/completions", "/v1/chat/completions"):
        raise ValueError("Unsupported DeepSeek endpoint path")
    if not path.endswith("/chat/completions"):
        path += "/chat/completions"
    return "https://api.deepseek.com" + path


def load_config(env_file: Path) -> Config:
    values = dict(dotenv_values(env_file, interpolate=False)) if env_file.is_file() else {}
    values.update(os.environ)
    key_name = next((name for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY") if values.get(name)), None)
    if key_name is None:
        raise ValueError("No configured API key; set DEEPSEEK_API_KEY")
    key = str(values[key_name]).strip()
    if not key or any(character.isspace() for character in key) or key.lower() in ("your_api_key", "your-api-key", "replace-me"):
        raise ValueError("Configured API key is empty or a placeholder")
    base = next((values[name] for name in ("DEEPSEEK_BASE_URL", "OPENAI_API_BASE", "OPENAI_BASE_URL") if values.get(name)), "https://api.deepseek.com/v1")
    model = str(values.get("DEEPSEEK_MODEL") or "deepseek-chat").strip()
    if not model or len(model) > 100 or any(character.isspace() for character in model):
        raise ValueError("Invalid configured model name")
    source = "process_environment" if os.environ.get(key_name) else "selected_env_file"
    return Config(key, endpoint(str(base)), model, source)


def redact(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return {name: "[REDACTED]" if str(name).lower() in ("authorization", "api_key", "apikey", "access_token")
                else redact(item, key) for name, item in value.items()}
    if isinstance(value, list):
        return [redact(item, key) for item in value]
    if isinstance(value, str):
        text = value.replace(key, "[REDACTED]") if key else value
        return re.sub(r"\bsk-[A-Za-z0-9_-]{12,}\b", "[REDACTED]", text)
    return value


def write_json(path: Path, value: Any, key: str = "") -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(redact(value, key), ensure_ascii=False, indent=2) + "\n")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def usage_valid(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    names = ("prompt_tokens", "completion_tokens", "total_tokens")
    return all(type(value.get(name)) is int and value[name] > 0 for name in names) and value["total_tokens"] == value["prompt_tokens"] + value["completion_tokens"]


def report_contract(content: str) -> dict:
    try:
        result = json.loads(content)
    except (ValueError, TypeError):
        result = None
    is_object = isinstance(result, dict)
    preserved = is_object and all(type(result.get(k)) is type(v) and result[k] == v for k, v in FIXTURE.items())
    summary = is_object and result.get("summary") == SUMMARY
    limitations = is_object and result.get("limitations") == LIMITATIONS
    fields = is_object and set(result) == set(FIXTURE) | {"summary", "limitations"}
    return {"json_valid": is_object, "fixture_preserved": preserved, "summary_exact": summary,
            "limitations_exact": limitations, "no_unknown_fields": fields,
            "passed": bool(preserved and summary and limitations and fields)}


def execute_case(config: Config, case: str, payload: dict, output: Path) -> dict:
    directory = output / case
    directory.mkdir()
    write_json(directory / "request.json", payload, config.api_key)
    audit = {"case": case, "started_at": now(), "http_status": None, "transport_passed": False,
             "response_schema_passed": False, "output_contract_passed": False, "passed": False}
    started = time.perf_counter()
    body = b""
    response = None
    try:
        request = urllib.request.Request(config.endpoint, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + config.api_key}, method="POST")
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=45) as remote:
            audit["http_status"] = remote.status
            body = remote.read(4 * 1024 * 1024 + 1)
            if len(body) > 4 * 1024 * 1024:
                raise ValueError("Response exceeded audit size bound")
            audit["provider_request_id"] = remote.headers.get("x-request-id")
        response = json.loads(body.decode("utf-8"))
        if not isinstance(response, dict):
            raise ValueError("Response was not an object")
        audit["transport_passed"] = audit["http_status"] == 200
        choices = response.get("choices")
        choice = choices[0] if isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict) else {}
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        content = message.get("content")
        audit.update({"response_id": response.get("id"), "returned_model": response.get("model"),
                      "finish_reason": choice.get("finish_reason"), "usage": response.get("usage"),
                      "response_characters": len(content) if isinstance(content, str) else 0})
        audit["response_schema_passed"] = (isinstance(response.get("id"), str) and bool(response["id"])
            and isinstance(response.get("model"), str) and bool(response["model"])
            and response.get("object") == "chat.completion" and message.get("role") == "assistant"
            and isinstance(content, str) and bool(content.strip()) and choice.get("finish_reason") == "stop"
            and usage_valid(response.get("usage")))
        if isinstance(content, str):
            audit["contract_checks"] = ({"exact_marker": content.strip() == "DEEPSEEK_CONNECTION_OK", "passed": content.strip() == "DEEPSEEK_CONNECTION_OK"}
                                         if case == "connectivity" else report_contract(content))
            audit["output_contract_passed"] = audit["contract_checks"]["passed"]
        audit["passed"] = bool(audit["transport_passed"] and audit["response_schema_passed"] and audit["output_contract_passed"])
    except urllib.error.HTTPError as error:
        audit["http_status"] = error.code
        audit["error_type"] = "HTTPError"
        body = error.read(4096)
        error.close()
    except Exception as error:
        audit["error_type"] = type(error).__name__
    finally:
        audit["duration_seconds_full_response"] = round(time.perf_counter() - started, 4)
        audit["completed_at"] = now()
    write_json(directory / "response.json", response if response is not None else {"error_body": body.decode("utf-8", errors="replace")}, config.api_key)
    write_json(directory / "audit.json", audit, config.api_key)
    return redact(audit, config.api_key)


def payloads(model: str) -> list[tuple[str, dict]]:
    common = {"model": model, "temperature": 0, "stream": False}
    connection = {**common, "max_tokens": 32, "messages": [
        {"role": "system", "content": "This is an API connectivity check. Return only the exact marker requested, without Markdown."},
        {"role": "user", "content": "Return exactly DEEPSEEK_CONNECTION_OK"}]}
    report = {**common, "max_tokens": 512, "response_format": {"type": "json_object"}, "messages": [
        {"role": "system", "content": "You are testing report formatting with a synthetic engineering fixture, not real research. Return JSON only. Copy all fixture keys and values exactly. Add only summary and limitations with these exact values: " + json.dumps({"summary": SUMMARY, "limitations": LIMITATIONS}) + ". Do not invent evidence, measurements, citations or approvals."},
        {"role": "user", "content": "Create a short JSON report from this fictional fixture:\n" + json.dumps(FIXTURE)}]}
    return [("connectivity", connection), ("synthetic_report", report)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        config = load_config(args.env_file.resolve())
        output = args.output.resolve()
        if not output.is_relative_to(ROOT / "03_experiments/audits") or output.exists():
            raise ValueError("Audit output must be a new directory under local audits")
        before = {name: sha(ROOT / name) for name in PROTECTED}
        if before != PROTECTED:
            raise ValueError("Protected research artifacts changed before testing")
        output.mkdir(parents=True, exist_ok=False)
        records = []
        for name, payload in payloads(config.model):
            if records and not records[0]["passed"]:
                records.append({"case": name, "passed": False, "status": "not_run_connectivity_failed"})
                break
            records.append(execute_case(config, name, payload, output))
        after = {name: sha(ROOT / name) for name in PROTECTED}
        summary = {"generated_at": now(), "status": "passed" if all(r["passed"] for r in records) and after == before else "failed",
                   "endpoint": config.endpoint, "requested_model": config.model, "credential_source": config.credential_source,
                   "actual_network_calls": sum("http_status" in r for r in records), "cases": records,
                   "protected_research_files_unchanged": after == before, "protected_sha256": after,
                   "real_research_data_uploaded": False, "peptide_sequences_uploaded": False, "model_fit_calls": 0,
                   "synthetic_fixture_only": True, "web_report_endpoint_deepseek_integration_tested": False,
                   "formal_dual_task_status": "blocked", "publication_ready": False, "credential_rotation_performed": False}
        write_json(output / "summary.json", summary, config.api_key)
        inventory = {str(path.relative_to(output)): sha(path) for path in output.rglob("*") if path.is_file()}
        write_json(output / "manifest.json", {"generated_at": now(), "files": inventory,
            "source_entry_sha256": sha(Path(__file__)), "configuration_secret_stored": False})
        print(json.dumps(redact({"status": summary["status"], "output": str(output), "cases": records,
            "protected_research_files_unchanged": after == before}, config.api_key), ensure_ascii=False, indent=2))
        return 0 if summary["status"] == "passed" else 1
    except Exception as error:
        print(json.dumps({"status": "not_started", "error_type": type(error).__name__}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
