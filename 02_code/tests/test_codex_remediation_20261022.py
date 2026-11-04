"""Behavioral regressions for export provenance, cancellable agents and motif topology."""
from __future__ import annotations

import asyncio
import csv
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import time
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "05_web_server"))

from agent_constraints import AgentHardConstraints, UnsupportedConstraintError
from async_job_store import AsyncJobStore
from dti_report_generator import generate_dti_academic_report
import supplementary_dataset_generator as delivery


@pytest.mark.parametrize("task_status", ["missing", "pending", "cancelled"])
def test_orphan_result_file_cannot_certify_model_execution(tmp_path, monkeypatch, task_status):
    """A legacy cache must not override missing/non-completed database execution state."""
    store = AsyncJobStore(tmp_path / "tasks.sqlite", tmp_path / "results")
    if task_status != "missing":
        store.create_task("audit", {}, task_id="orphan")
        if task_status == "cancelled":
            store.cancel_task("orphan")
    monkeypatch.setattr(delivery, "__file__", str(tmp_path / "02_code/generator.py"))
    cache = tmp_path / "output/task_results/orphan_result.json"
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({"model_used": "f1_ridge", "target_name": "ABL1", "baseline": {"smiles": "CCO", "predicted_pkd": 8.88}}))
    package = delivery.SupplementaryDatasetGenerator(tmp_path / "packages", job_store=store).generate_package(task_id="orphan")
    with zipfile.ZipFile(package["zip_path"]) as archive:
        provenance = json.loads(archive.read("provenance.json"))
    assert provenance["execution_verified"] is False
    assert provenance["reproducibility"]["random_seed"] is None


def test_partial_admet_never_invents_missing_measurements():
    report = generate_dti_academic_report("ABL1", {"smiles": "CCO"}, [], admet={"herg_risk": "medium"}, is_verified=False)
    combined = report["markdown_report"] + report["html_report"]
    for invented in ("75.0 / 100", "安全性良好", "12.0", "-3.8", "低风险"):
        assert invented not in combined
    assert "medium" in combined


def test_standalone_report_defaults_to_unverified_without_a_server_task():
    report = generate_dti_academic_report("ABL1", {"smiles": "CCO", "predicted_pkd": 8.88}, [])
    assert "Unverified" in report["markdown_report"]
    assert "Server-Verified" not in report["markdown_report"]


def test_runtime_model_id_survives_workspace_export(tmp_path):
    package = delivery.SupplementaryDatasetGenerator(tmp_path / "packages").generate_package(result_payload={
        "model_used": "rigorous_ridge_alpha10", "target_name": "ABL1",
        "baseline": {"smiles": "CCO", "predicted_pkd": 8.88},
    })
    with zipfile.ZipFile(package["zip_path"]) as archive:
        assert "rigorous_ridge_alpha10 (Unverified)" in archive.read("predictions.csv").decode()


def test_export_does_not_invent_filter_counts_or_generation_metadata(tmp_path):
    package = delivery.SupplementaryDatasetGenerator(tmp_path / "packages").generate_package(result_payload={
        "model_used": "f1_ridge", "baseline": {"smiles": "CCO", "predicted_pkd": 6.0},
        "candidates": [{"smiles": "CCN", "predicted_pkd": 6.2}],
    })
    with zipfile.ZipFile(package["zip_path"]) as archive:
        candidate = list(csv.DictReader(io.StringIO(archive.read("candidates.csv").decode())))[0]
        assert candidate["Source"] == ""
        assert candidate["Scaffold_Type"] == ""
        stages = list(csv.DictReader(io.StringIO(archive.read("figures/fig2_screening_funnel_data.csv").decode())) )
        assert [int(stage["Remaining_Count"]) for stage in stages] == [1, 1, 0]
        assert "100.0%" not in archive.read("README.md").decode()


def test_unscored_records_never_become_fake_distribution_points(tmp_path):
    package = delivery.SupplementaryDatasetGenerator(tmp_path / "packages").generate_package(result_payload={
        "model_used": "f1_ridge", "baseline": {"smiles": "CCO"},
        "candidates": [{"name": "Unscored", "smiles": "CCN"}],
    })
    with zipfile.ZipFile(package["zip_path"]) as archive:
        rows = list(csv.DictReader(io.StringIO(archive.read("figures/fig1_affinity_distribution_data.csv").decode())))
        assert rows == []


@pytest.mark.parametrize("name", ["export_affinity_distribution", "export_screening_funnel", "export_candidate_sar_comparison"])
def test_standalone_plot_helpers_reject_empty_data(tmp_path, name):
    import scientific_figure_exporter as figures
    with pytest.raises(ValueError):
        getattr(figures, name)([], output_dir=tmp_path)


def test_sar_plot_requires_a_reported_baseline_or_delta(tmp_path):
    from scientific_figure_exporter import export_candidate_sar_comparison
    with pytest.raises(ValueError):
        export_candidate_sar_comparison([{"name": "Unknown delta", "predicted_pkd": 6.2}], output_dir=tmp_path)


@pytest.mark.parametrize("motif,smiles,expected", [
    ("C", "Cl", False),
    ("N", "[Na+]", False),
    ("CCO", "CC(O)", True),
    ("C(C)(C)C", "CC(C)C", True),
    ("C1CCCCC1", "C2CCCCC2", True),
])
def test_motifs_match_atom_bond_topology_not_text(motif, smiles, expected):
    assert AgentHardConstraints(must_contain_motif=motif).validate_candidate(smiles)[0] is expected


@pytest.mark.parametrize("smiles", ["c1ccccc1(", "c1ccccc1X", "C1=CC=CC=C1)"])
def test_invalid_candidate_is_rejected_before_motif_matching(smiles):
    assert AgentHardConstraints(must_contain_motif="c1ccccc1").validate_candidate(smiles)[0] is False


def test_stereospecific_query_is_rejected_instead_of_silently_ignored():
    with pytest.raises(UnsupportedConstraintError):
        AgentHardConstraints.from_dict({"must_contain_motif": "N[C@@H](C)O"})


class FixedScorer:
    def predict(self, *args, **kwargs):
        return {"predicted_pkd": 8.2, "predicted_kd_nM": 6.3095734448, "confidence_band": "High"}


@pytest.fixture
def agent_environment(tmp_path, monkeypatch):
    import agent_endpoints as endpoint
    import agent_orchestrator as orchestration
    manager_store = AsyncJobStore(tmp_path / "agent.sqlite", tmp_path / "agent_results")
    monkeypatch.setattr(endpoint.task_manager, "store", manager_store)
    monkeypatch.setattr(endpoint, "active_sessions", {})
    monkeypatch.setattr(orchestration, "ROOT", tmp_path)
    original_class = orchestration.MultiAgentOrchestrator
    def factory(*args, **kwargs):
        return original_class(*args, runtime=FixedScorer(), **kwargs)
    monkeypatch.setattr(endpoint, "MultiAgentOrchestrator", factory)
    return endpoint, orchestration


def request_for(endpoint, **overrides):
    return endpoint.AgentRunRequest(scenario="custom", user_goal="local regression", target_symbol="ABL1", target_sequence="ACDEFGHIKLMNPQRSTVWY", baseline_smiles="CCO", max_iterations=1, **overrides)


def test_agent_registration_failure_never_starts_an_untracked_session(agent_environment, monkeypatch):
    endpoint, _ = agent_environment
    from fastapi import HTTPException
    def unavailable(*args, **kwargs):
        raise OSError("AUDIT: task storage unavailable")
    monkeypatch.setattr(endpoint.task_manager.store, "create_task", unavailable)
    async def run():
        with pytest.raises(HTTPException) as exc:
            await endpoint.run_agent_stream(request_for(endpoint))
        assert exc.value.status_code == 503
        assert not endpoint.active_sessions
    asyncio.run(run())


def test_foreground_active_cancel_reaches_terminal_store_state(agent_environment):
    endpoint, _ = agent_environment
    async def run():
        response = await endpoint.run_agent_stream(request_for(endpoint))
        task = next(iter(endpoint.active_sessions))
        await response.body_iterator.__anext__()
        endpoint.cancel_agent_task(task)
        async for _ in response.body_iterator:
            pass
        record = endpoint.task_manager.store.get_task(task)
        assert record["status"] == "cancelled"
        assert record["result_summary"]["checkpoint_status"] == "none"
    asyncio.run(run())


def test_background_admission_respects_worker_and_waiting_limits(agent_environment, monkeypatch):
    endpoint, _ = agent_environment
    monkeypatch.setattr(endpoint.task_manager, "max_workers", 1)
    monkeypatch.setattr(endpoint.task_manager, "max_queue_size", 1)
    from fastapi import HTTPException
    async def run():
        responses = []
        try:
            responses.append(await endpoint.run_agent_stream(request_for(endpoint, enable_background=True)))
            responses.append(await endpoint.run_agent_stream(request_for(endpoint, enable_background=True)))
            with pytest.raises(HTTPException) as exc:
                responses.append(await endpoint.run_agent_stream(request_for(endpoint, enable_background=True)))
            assert exc.value.status_code == 429
        finally:
            for session in list(endpoint.active_sessions.values()):
                session.cancel()
            for response in responses:
                async for _ in response.body_iterator:
                    pass
    asyncio.run(run())


def test_real_llm_http_roundtrip_preserves_baseline_and_event_loop(agent_environment):
    """Use the real HTTP adapter; only affinity scoring is deterministic, no external service."""
    endpoint, _ = agent_environment
    network_active = threading.Event()
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            network_active.set()
            time.sleep(0.2)
            content = {"modifications": [{"name": "Local aspirin", "smiles": "CC(=O)Oc1ccccc1C(=O)O", "rationale": "local fixture", "modification_type": "local"}]}
            body = json.dumps({"choices": [{"message": {"content": json.dumps(content)}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            network_active.clear()
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    async def run():
        during_network_ticks = []
        stop = asyncio.Event()
        async def heartbeat():
            while not stop.is_set():
                if network_active.is_set():
                    during_network_ticks.append(1)
                await asyncio.sleep(0.01)
        ticker = asyncio.create_task(heartbeat())
        try:
            response = await endpoint.run_agent_stream(request_for(endpoint, llm_mode="online_api", llm_config={"api_key": "local-audit-only", "api_base": f"http://127.0.0.1:{server.server_port}", "model_name": "local-test-model"}))
            task = next(iter(endpoint.active_sessions))
            chunks = [chunk async for chunk in response.body_iterator]
            assert endpoint.task_manager.store.get_task(task)["status"] == "completed"
            assert any("local fixture" in chunk for chunk in chunks)
            assert during_network_ticks, "LLM HTTP I/O blocked the SSE/control event loop"
            prompt = requests[0]["messages"][1]["content"]
            assert "6.3 nM" in prompt
            assert requests[0]["model"] == "local-test-model"
            result = endpoint.task_manager.store.get_task_result(task)
            assert result["generation_audit"][0]["model_name"] == "local-test-model"
        finally:
            stop.set()
            await ticker
    try:
        asyncio.run(run())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
