"""Offline contract regressions; all network results here are explicit test fixtures."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import sys
import urllib.error

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deepseek_live_smoke as smoke


@pytest.mark.parametrize("base", ["https://api.deepseek.com", "https://api.deepseek.com/v1/", "https://api.deepseek.com/v1/chat/completions"])
def test_official_endpoint(base):
    assert smoke.endpoint(base).endswith("/chat/completions")


@pytest.mark.parametrize("base", ["http://api.deepseek.com/v1", "https://example.com/v1", "https://credential@api.deepseek.com/v1", "https://api.deepseek.com/v1?key=fixture", "https://api.deepseek.com:443/v1", "https://api.deepseek.com/other", "https://api.deepseek.com/v1#fragment"])
def test_credentials_are_not_sent_to_unapproved_endpoints(base):
    with pytest.raises(ValueError):
        smoke.endpoint(base)


def test_missing_configuration_fails_before_network(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "environ", {})
    with pytest.raises(ValueError):
        smoke.load_config(tmp_path / "missing.env")


def test_process_config_precedes_selected_env(tmp_path, monkeypatch):
    env = tmp_path / "fixture.env"
    env.write_text("DEEPSEEK_API_KEY=file-fixture\nDEEPSEEK_MODEL=deepseek-chat\n", encoding="utf-8")
    monkeypatch.setattr(os, "environ", {"DEEPSEEK_API_KEY": "process-fixture"})
    config = smoke.load_config(env)
    assert config.api_key == "process-fixture" and config.credential_source == "process_environment"


def report():
    return {**smoke.FIXTURE, "summary": smoke.SUMMARY, "limitations": smoke.LIMITATIONS}


def test_valid_synthetic_report():
    assert smoke.report_contract(json.dumps(report()))["passed"]


@pytest.mark.parametrize("change", [{"formal_research_status": "ready"}, {"publication_ready": True}, {"engineering_records": 13}, {"eligible_external_records": False}, {"summary": "Research passed"}, {"limitations": []}, {"unverified_evidence": "approved"}])
def test_report_cannot_release_research_or_invent_counts(change):
    assert not smoke.report_contract(json.dumps(report() | change))["passed"]


def test_invalid_json_report():
    assert not smoke.report_contract("not JSON")["passed"]


@pytest.mark.parametrize("usage", [None, {}, {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 9}, {"prompt_tokens": True, "completion_tokens": 3, "total_tokens": 4}])
def test_usage_must_be_recorded_and_consistent(usage):
    assert not smoke.usage_valid(usage)


def test_redaction_is_recursive():
    result = smoke.redact({"authorization": "Bearer fixture-credential", "rows": ["fixture-credential", "sk-abcdefghijklmnop"]}, "fixture-credential")
    assert result == {"authorization": "[REDACTED]", "rows": ["[REDACTED]", "[REDACTED]"]}


def test_redirect_never_forwards_authentication():
    assert smoke.NoRedirect().redirect_request(None, None, 302, None, None, "https://example.com") is None


class FakeResponse:
    status = 200
    headers = {"x-request-id": "fixture-request-id"}

    def __init__(self, value):
        self.body = json.dumps(value).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.body[:size]


def api_response(finish_reason="stop", usage=True):
    result = {"id": "fixture-response-id", "model": "fixture-model", "object": "chat.completion", "choices": [{"message": {"role": "assistant", "content": "DEEPSEEK_CONNECTION_OK"}, "finish_reason": finish_reason}]}
    if usage:
        result["usage"] = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    return result


@pytest.mark.parametrize("finish,usage,expected", [("stop", True, True), ("length", True, False), ("stop", False, False)])
def test_response_contract_and_complete_timing(tmp_path, monkeypatch, finish, usage, expected):
    class FakeOpener:
        def open(self, request, timeout):
            assert timeout == 45 and request.get_header("Authorization") == "Bearer fixture-credential"
            return FakeResponse(api_response(finish, usage))
    monkeypatch.setattr(smoke.urllib.request, "build_opener", lambda *args: FakeOpener())
    ticks = iter([10.0, 17.25])
    monkeypatch.setattr(smoke.time, "perf_counter", lambda: next(ticks))
    config = smoke.Config("fixture-credential", "https://api.deepseek.com/chat/completions", "fixture-model", "fixture")
    result = smoke.execute_case(config, "connectivity", smoke.payloads("fixture-model")[0][1], tmp_path)
    assert result["passed"] is expected and result["duration_seconds_full_response"] == 7.25
    assert "fixture-credential" not in "".join(p.read_text() for p in tmp_path.rglob("*.json"))


def test_http_failure_is_recorded_without_credentials(tmp_path, monkeypatch):
    class FakeOpener:
        def open(self, *args, **kwargs):
            raise urllib.error.HTTPError("https://api.deepseek.com", 401, "fixture", {}, io.BytesIO(b"fixture-credential rejected"))
    monkeypatch.setattr(smoke.urllib.request, "build_opener", lambda *args: FakeOpener())
    config = smoke.Config("fixture-credential", "https://api.deepseek.com/chat/completions", "fixture-model", "fixture")
    result = smoke.execute_case(config, "connectivity", smoke.payloads("fixture-model")[0][1], tmp_path)
    assert not result["passed"] and result["http_status"] == 401
    assert "fixture-credential" not in (tmp_path / "connectivity/response.json").read_text()


def test_outputs_are_not_overwritten(tmp_path):
    path = tmp_path / "audit.json"
    smoke.write_json(path, {"fixture": True})
    with pytest.raises(FileExistsError):
        smoke.write_json(path, {"fixture": False})
