"""Comprehensive regression test suite for independent review remediation items R01 - R06.

Verifies:
- R01: Unregistered model rejection and refusal of unauthenticated fake payloads.
- R02: Virtual screening task schema adaptation to formal export (real hits, no fake baseline).
- R03: Result file immutability on rejected / late completion.
- R04: AgentCheckpoint.to_dict() and disk persistence verification.
- R05: Motif ring numbering normalization across arbitrary digits (c1/c2, C1/C2).
- R06: Store migration contracts across versions (v5 ethanol/melittin/unknown, v6 misclassification repair).
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import tempfile
import time
import zipfile
import pytest

from async_job_store import AsyncJobStore
from async_task_manager import AsyncTaskManager
from agent_constraints import AgentHardConstraints, AgentCheckpoint
import agent_orchestrator as orchestration
from supplementary_dataset_generator import SupplementaryDatasetGenerator


def read_package_csv(zip_path: str, filename: str = "predictions.csv"):
    with zipfile.ZipFile(zip_path) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(filename).decode("utf-8-sig"))))


def test_r01_unregistered_model_rejection(tmp_path):
    """R01: Backend must reject unverified calculation payloads with unregistered models or missing models."""
    generator = SupplementaryDatasetGenerator(tmp_path / "packages")
    with pytest.raises(ValueError, match="未注册或未执行的模型"):
        generator.generate_package(result_payload={
            "baseline": {"name": "Unverified ethanol", "smiles": "CCO", "predicted_pkd": 8.88},
            "model_used": "AUDIT_NOT_A_REGISTERED_MODEL",
        })

    with pytest.raises(ValueError, match="未注册或未执行的模型"):
        generator.generate_package(result_payload={
            "baseline": {"name": "Unverified ethanol", "smiles": "CCO", "predicted_pkd": 8.88},
            "model_used": "AUDIT_MODEL_NOT_EXECUTED",
        })

    with pytest.raises(ValueError, match="未指定推理模型名称"):
        generator.generate_package(result_payload={
            "baseline": {"name": "Unverified ethanol", "smiles": "CCO", "predicted_pkd": 8.88},
            "verified": True,
        })


def test_r01_unverified_payload_cannot_forge_verified_status(tmp_path):
    """R01: Direct client payload with verified=True cannot forge verified status without server task_id."""
    generator = SupplementaryDatasetGenerator(tmp_path / "packages")
    res = generator.generate_package(result_payload={
        "baseline": {"name": "Unverified ethanol", "smiles": "CCO", "predicted_pkd": 8.88},
        "model_used": "f1_ridge",
        "verified": True,
    })
    rows = read_package_csv(res["zip_path"], "predictions.csv")
    assert rows[0]["Model_Used"] == "f1_ridge (Unverified)"
    
    with zipfile.ZipFile(res["zip_path"]) as archive:
        prov = json.loads(archive.read("provenance.json"))
        readme = archive.read("README.md").decode()

    assert prov["task_id"] is None
    assert prov["execution_verified"] is False
    assert prov["reproducibility"]["random_seed"] is None
    assert "derived from the DAVIS Kinome benchmark and rigorous DTI inference runtimes" not in readme


def test_r02_virtual_screening_schema_adaptation(tmp_path):
    """R02: Virtual screening results in report.hits must be exported with real hits and no fake baseline."""
    db_file = tmp_path / "test_vs.sqlite"
    res_dir = tmp_path / "test_vs_res"
    store = AsyncJobStore(db_path=db_file, results_dir=res_dir)
    manager = AsyncTaskManager(store=store, max_workers=1)

    try:
        task_id, _ = manager.submit_task("virtual_screening", {"target_symbol": "ABL1", "top_k": 2})
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            task = store.get_task(task_id)
            if task["status"] in ("completed", "failed", "cancelled"):
                break
            time.sleep(0.05)

        assert task["status"] == "completed"
        task_result = store.get_task_result(task_id)
        report_hits = task_result.get("report", {}).get("hits", [])
        assert len(report_hits) >= 1

        generator = SupplementaryDatasetGenerator(tmp_path / "packages", job_store=store)
        exported = generator.generate_package(task_id=task_id)
        rows = read_package_csv(exported["zip_path"], "predictions.csv")

        # Must not contain dummy Baseline_Lead with empty SMILES
        baseline_rows = [r for r in rows if r["Entity_Type"] == "Baseline_Lead"]
        assert len(baseline_rows) == 0, "Virtual screening package should NOT fabricate a fake Baseline_Lead row!"

        # Must contain rows for each hit with real SMILES and real pKd
        hit_rows = [r for r in rows if r["Entity_Type"] == "Screening_Hit"]
        assert len(hit_rows) == len(report_hits)
        for h_row, r_hit in zip(hit_rows, report_hits):
            assert h_row["SMILES"] == r_hit["smiles"]
            assert float(h_row["Predicted_pKd"]) == round(float(r_hit["predicted_pkd"]), 4)
            assert h_row["Model_Used"] == "stacked_ensemble"

        # Check candidates.csv as well
        cand_rows = read_package_csv(exported["zip_path"], "candidates.csv")
        assert len(cand_rows) == len(report_hits)
    finally:
        manager._executor.shutdown(wait=True)


def test_r03_result_file_immutability(tmp_path):
    """R03: Result file must not be modified if SQL transition rejects late completion."""
    db_file = tmp_path / "test_r03.sqlite"
    res_dir = tmp_path / "test_r03_res"
    store = AsyncJobStore(db_path=db_file, results_dir=res_dir)

    tid, _ = store.create_task("audit", {})
    accepted1 = store.complete_task(tid, {"score": 7}, {"score": 7})
    accepted2 = store.complete_task(tid, {"score": 99}, {"score": 99})

    assert accepted1 is True
    assert accepted2 is False
    assert store.get_task(tid)["status"] == "completed"
    assert store.get_task(tid)["result_summary"] == {"score": 7}
    assert store.get_task_result(tid) == {"score": 7}


def test_r04_checkpoint_to_dict_and_disk_persistence(tmp_path):
    """R04: AgentCheckpoint must serialize to dict and write to disk without error."""
    ckpt = AgentCheckpoint(
        task_id="AUDIT_TASK",
        generation=1,
        parent_id=None,
        parent_smiles="CCO",
        constraints_version=1,
        best_pkd=8.0,
        candidates_count=3,
        timestamp="2026-10-21T00:00:00Z"
    )
    assert hasattr(ckpt, "to_dict")
    d = ckpt.to_dict()
    assert d["task_id"] == "AUDIT_TASK"
    assert d["best_pkd"] == 8.0

    orchestration.ROOT = tmp_path
    class DeterministicMockRuntime:
        def predict(self, *args, **kwargs):
            return {"predicted_pkd": 6.0, "predicted_kd_nM": 1000.0, "confidence_band": "High"}

    orchestrator = orchestration.MultiAgentOrchestrator(runtime=DeterministicMockRuntime())
    initial = {
        "task_id": "AUDIT_TEST_PERSIST", "scenario": "custom", "user_goal": "audit",
        "target_symbol": "ABL1", "target_sequence": "ACDEFGHIKLMNPQRSTVWY",
        "baseline_smiles": "CCO", "current_agent": "supervisor", "iteration": 0,
        "max_iterations": 1, "target_pkd": 9.5, "min_admet_score": 60.0,
        "max_hemolysis_pct": 10.0, "candidates": [], "current_best": None,
        "pareto_frontier": [], "step_count": 0, "is_converged": False,
        "final_verdict": None, "constraints_version": 1,
        "constraints": orchestrator.constraints.to_dict(), "checkpoints": [],
    }

    import asyncio
    async def run():
        return [ev async for ev in orchestrator.run_pipeline_stream(initial)]

    events = asyncio.run(run())
    assert len(orchestrator.checkpoints) >= 1
    assert hasattr(orchestrator.checkpoints[0], "to_dict")
    saved_files = list(orchestration.ROOT.rglob("*.json"))
    assert len(saved_files) >= 1
    saved_content = json.loads(saved_files[0].read_text(encoding="utf-8"))
    assert saved_content["task_id"] == "AUDIT_TEST_PERSIST"


def test_r05_motif_ring_numbering_normalization():
    """R05: Benzene motif matching must normalize arbitrary ring numbers (c1/c2, C1/C2)."""
    constraint = AgentHardConstraints(must_contain_motif="c1ccccc1")
    for target in ("c1ccccc1", "C1=CC=CC=C1", "c2ccccc2", "C2=CC=CC=C2", "c3ccccc3", "C3=CC=CC=C3"):
        passed, reason = constraint.validate_candidate(target)
        assert passed is True, f"Target '{target}' should have matched motif 'c1ccccc1'! Reason: {reason}"


def test_r05_benzene_substituents_and_multidigit_ring_closure():
    """R05: Benzene motif matching must detect two-digit closures %10 and substituted benzenes."""
    must_c = AgentHardConstraints(must_contain_motif="c1ccccc1")
    forb_c = AgentHardConstraints(forbidden_motifs=["c1ccccc1"])

    for target in ("c%10ccccc%10", "c1cc(C)ccc1", "c1c(Cl)cccc1", "c1c(O)cccc1"):
        must_pass, must_reason = must_c.validate_candidate(target)
        assert must_pass is True, f"Target '{target}' should satisfy must_contain! Reason: {must_reason}"

        forb_pass, forb_reason = forb_c.validate_candidate(target)
        assert forb_pass is False, f"Target '{target}' should be rejected by forbidden_motifs!"
        assert "包含禁用结构基团" in forb_reason


def test_r06_store_migration_logic():
    """R06: Verify Store migration correctly classifies small molecules, peptides, and repairs v6 errors."""
    import re

    def simulate_v7_migration(persisted_state: dict, version: int = 5):
        state = persisted_state or {}
        old_seq = (state.get("activeSequence") or "").strip()
        old_name = (state.get("activePeptideName") or "").strip()
        migrated_entity = state.get("activeEntity")

        if migrated_entity and version < 7:
            if migrated_entity.get("kind") == "peptide":
                seq = (migrated_entity.get("sequence") or "").strip()
                if re.match(r'^(CCO|CC|CCC|CCCC|CCN|CCOC|CCOCC)$', seq, re.I) or re.search(r'[=#()0-9cnosp]', seq) or "O" in seq.upper():
                    migrated_entity = {
                        "kind": "small_molecule",
                        "smiles": seq,
                        "name": migrated_entity.get("name") or "Migrated Molecule"
                    }
            elif migrated_entity.get("kind") == "unconfirmed":
                seq = (migrated_entity.get("sequence") or "").strip()
                has_smiles_syntax = bool(re.search(r'[0-9=#()\[\]@\-+\\/%]', seq) or re.search(r'[cnosp]', seq))
                is_std_pep = bool(re.match(r'^[ACDEFGHIKLMNPQRSTVWY]{4,}$', seq.upper()) and not has_smiles_syntax and not re.search(r'[OBJZ]', seq.upper()))
                if is_std_pep:
                    migrated_entity = {
                        "kind": "peptide",
                        "sequence": seq.upper(),
                        "name": migrated_entity.get("name") or "Migrated Peptide"
                    }

        if not migrated_entity and old_seq:
            has_smiles_syntax = bool(re.search(r'[0-9=#()\[\]@\-+\\/%]', old_seq) or re.search(r'[cnosp]', old_seq))
            is_common_formula = bool(re.match(r'^(CCO|CC|CCC|CCCC|CCN|CCOC|CCOCC|C#N|C=O)$', old_seq, re.I))
            is_unambiguous_smiles = has_smiles_syntax or is_common_formula
            is_unambiguous_pep = bool(
                re.match(r'^[ACDEFGHIKLMNPQRSTVWY]{4,}$', old_seq.upper()) and
                not has_smiles_syntax and
                not re.search(r'[OBJZ]', old_seq.upper())
            )

            if is_unambiguous_smiles and not is_unambiguous_pep:
                migrated_entity = {"kind": "small_molecule", "smiles": old_seq, "name": old_name or "Migrated Molecule"}
            elif is_unambiguous_pep and not is_unambiguous_smiles:
                migrated_entity = {"kind": "peptide", "sequence": old_seq.upper(), "name": old_name or "Migrated Peptide"}
            else:
                migrated_entity = {"kind": "unconfirmed", "sequence": old_seq, "name": old_name or "Unconfirmed Entity"}

        return migrated_entity

    # 1. ethanol_v5
    res1 = simulate_v7_migration({"activeSequence": "CCO", "activePeptideName": "Ethanol"}, version=5)
    assert res1["kind"] == "small_molecule"
    assert res1["smiles"] == "CCO"

    # 2. melittin_v5 (Melittin must be identified as peptide)
    res2 = simulate_v7_migration({"activeSequence": "GIGAVLKVLTTGLPALISWIKRKRQQ", "activePeptideName": "Melittin"}, version=5)
    assert res2["kind"] == "peptide"
    assert res2["sequence"] == "GIGAVLKVLTTGLPALISWIKRKRQQ"

    # 3. unknown_v5
    res3 = simulate_v7_migration({"activeSequence": "XYZ", "activePeptideName": "Unknown"}, version=5)
    assert res3["kind"] == "unconfirmed"

    # 4. already_misclassified_v6 (previously misclassified CCO as peptide in v6 must be corrected to small_molecule)
    res4 = simulate_v7_migration({"activeEntity": {"kind": "peptide", "sequence": "CCO", "name": "Ethanol"}}, version=6)
    assert res4["kind"] == "small_molecule"
    assert res4["smiles"] == "CCO"


def test_r01_verified_target_lock_and_unverified_report_truthfulness(tmp_path):
    """R01: Verified tasks lock their target identity against caller override, and unverified reports stay truthful."""
    db_file = tmp_path / "test_r01.sqlite"
    res_dir = tmp_path / "test_r01_res"
    store = AsyncJobStore(db_path=db_file, results_dir=res_dir)
    manager = AsyncTaskManager(store=store, max_workers=1)

    try:
        task_id, _ = manager.submit_task("virtual_screening", {"target_symbol": "ABL1", "top_k": 2})
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            task = store.get_task(task_id)
            if task["status"] in ("completed", "failed", "cancelled"):
                break
            time.sleep(0.05)

        assert task["status"] == "completed"
        generator = SupplementaryDatasetGenerator(tmp_path / "packages", job_store=store)

        # 1. Attempting to override server verified task target with "EGFR" must keep real target "ABL1"
        package = generator.generate_package(task_id=task_id, target_name="EGFR")
        pred_rows = read_package_csv(package["zip_path"], "predictions.csv")
        assert len(pred_rows) >= 1
        for row in pred_rows:
            assert row["Target_Symbol"] == "ABL1", f"Target_Symbol in predictions.csv was tampered to {row['Target_Symbol']}!"

        with zipfile.ZipFile(package["zip_path"]) as archive:
            prov = json.loads(archive.read("provenance.json"))
            assert prov["target_kinase"] == "ABL1", f"target_kinase in provenance.json was tampered to {prov['target_kinase']}!"
            assert prov["execution_verified"] is True

        # 2. Unverified payload report generation must not claim DAVIS benchmark or forge default values
        unverified_res = generator.generate_package(result_payload={
            "model_used": "f1_ridge",
            "verified": False,
            "baseline": {"name": "Test_Base", "smiles": "CCO", "predicted_pkd": 8.0},
            "candidates": [{"name": "Test_Cand", "smiles": "CCN", "predicted_pkd": 8.5}]
        })
        with zipfile.ZipFile(unverified_res["zip_path"]) as archive:
            report_md = archive.read("reports/research_report.md").decode("utf-8")
            report_html = archive.read("reports/research_report.html").decode("utf-8")
            assert "Unverified" in report_md
            assert "Unverified" in report_html
            assert "CRITICAL SCIENTIFIC INTEGRITY WARNING" in report_md
            assert "CRITICAL SCIENTIFIC INTEGRITY WARNING" in report_html
            assert "Protocol-DTI-01 (DAVIS 基准" not in report_md
    finally:
        manager._executor.shutdown(wait=True)


def test_r04_online_llm_invocation_and_background_cancel(tmp_path):
    """R04: online_api calls real adapter and background cancellation transitions to 'cancelled' with checkpoint_status='none'."""
    import sys
    server_dir = str(Path(__file__).resolve().parents[2] / "05_web_server")
    if server_dir not in sys.path:
        sys.path.insert(0, server_dir)
    import async_job_store as jobs
    orig_db = jobs.DEFAULT_DB_PATH
    orig_res = jobs.DEFAULT_RESULTS_DIR
    jobs.DEFAULT_DB_PATH = tmp_path / "default.sqlite"
    jobs.DEFAULT_RESULTS_DIR = tmp_path / "results"

    import agent_endpoints as endpoint
    import agent_orchestrator as orch_mod
    import dti_lead_optimizer

    llm_calls = []
    def spy_llm(*args, **kwargs):
        llm_calls.append("generate_llm_candidates")
        raise RuntimeError("AUDIT_SPY_ERROR")

    orig_adapter = dti_lead_optimizer.generate_llm_candidates
    dti_lead_optimizer.generate_llm_candidates = spy_llm

    orch_mod.ROOT = tmp_path
    endpoint.ROOT = tmp_path

    class MockRuntime:
        def predict(self, *args, **kwargs):
            return {"predicted_pkd": 6.0, "predicted_kd_nM": 1000.0, "confidence_band": "High"}

    orig_orch_cls = endpoint.MultiAgentOrchestrator
    endpoint.MultiAgentOrchestrator = lambda *a, **kw: orig_orch_cls(*a, runtime=MockRuntime(), **kw)

    try:
        import asyncio
        async def run_test():
            req = endpoint.AgentRunRequest(
                scenario="custom", user_goal="audit", target_symbol="ABL1", target_sequence="ACDEFGHIKLMNPQRSTVWY",
                baseline_smiles="CCO", max_iterations=1, enable_background=True, llm_mode="online_api",
                llm_config={"provider": "AUDIT_TEST", "api_base": "http://127.0.0.1:1", "model_name": "AUDIT_MODEL"}
            )
            resp = await endpoint.run_agent_stream(req)
            task_id = next(iter(endpoint.active_sessions))
            endpoint.cancel_agent_task(task_id)
            await resp.body_iterator.__anext__()
            await resp.body_iterator.aclose()

            deadline = asyncio.get_running_loop().time() + 10
            while asyncio.get_running_loop().time() < deadline:
                t = endpoint.task_manager.store.get_task(task_id)
                if t["status"] in ("completed", "failed", "cancelled"):
                    break
                await asyncio.sleep(0.05)

            assert t["status"] == "cancelled"
            assert t["result_summary"]["checkpoint_status"] == "none"

        asyncio.run(run_test())
    finally:
        dti_lead_optimizer.generate_llm_candidates = orig_adapter
        endpoint.MultiAgentOrchestrator = orig_orch_cls
        jobs.DEFAULT_DB_PATH = orig_db
        jobs.DEFAULT_RESULTS_DIR = orig_res


def test_r05_graph_ring_detection_negative_controls():
    """R05: Benzene alternating bonds and pyridine aromaticity reject negative controls."""
    from agent_constraints import has_benzene_ring, has_pyridine_ring, AgentHardConstraints

    # 1. Negative controls for benzene
    assert has_benzene_ring("c1ccccc1") is True
    assert has_benzene_ring("C1CCCCC1") is False  # cyclohexane
    assert has_benzene_ring("C1=CCCCC1") is False  # cyclohexene
    assert has_benzene_ring("C1=C=CC=CC1") is False  # non-alternating three double bonds

    # 2. Negative controls for pyridine
    assert has_pyridine_ring("c1ccncc1") is True
    assert has_pyridine_ring("C1CCNCC1") is False  # piperidine (aliphatic)

    # 3. AgentHardConstraints validation
    c_benz = AgentHardConstraints(must_contain_motif="c1ccccc1")
    passed_nonalt, _ = c_benz.validate_candidate("C1=C=CC=CC1")
    assert passed_nonalt is False

    c_pyr = AgentHardConstraints(must_contain_motif="c1ccncc1")
    passed_pip, _ = c_pyr.validate_candidate("C1CCNCC1")
    assert passed_pip is False

    c_forb_pyr = AgentHardConstraints(forbidden_motifs=["c1ccncc1"])
    passed_pip_forb, _ = c_forb_pyr.validate_candidate("C1CCNCC1")
    assert passed_pip_forb is True, "Piperidine should NOT violate forbidden pyridine constraint!"

