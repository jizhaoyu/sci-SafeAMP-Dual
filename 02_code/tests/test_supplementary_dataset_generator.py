"""Unit and integration tests for Supplementary Research Dataset & Delivery Package (P5A Milestone)."""
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CODE_DIR = PROJECT_ROOT / "02_code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from supplementary_dataset_generator import (
    SupplementaryDatasetGenerator,
    verify_supplementary_package,
    _compute_sha256
)


@pytest.fixture
def temp_output_dir(tmp_path):
    out = tmp_path / "supp_output"
    out.mkdir(parents=True, exist_ok=True)
    return out


@pytest.fixture
def sample_payload():
    return {
        "target_name": "ABL1",
        "model_used": "f1_ridge",
        "baseline": {
            "name": "Dasatinib",
            "smiles": "CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO",
            "predicted_pkd": 8.12,
            "predicted_kd_nM": 7.59,
            "sa_score": 2.95,
            "domain": "Target_Within_Train_Domain"
        },
        "candidates": [
            {
                "id": "cand_001",
                "name": "Dasatinib-4-Fluoro",
                "smiles": "CC1=C(C(=C(F)C=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO",
                "modification_type": "Para-Fluorination",
                "source": "heuristic_rule",
                "scaffold_type": "scaffold_retention",
                "parent_similarity": 0.89,
                "predicted_pkd": 8.55,
                "delta_pkd": 0.43,
                "predicted_kd_nM": 2.82,
                "sa_score": 3.05,
                "sa_tier": "easy",
                "admet": {
                    "admet_health_score": 78.5,
                    "herg_risk": "low"
                }
            },
            {
                "id": "cand_002",
                "name": "Dasatinib-CF3-Hopping",
                "smiles": "CC1=C(C(=CC=C1)C(F)(F)F)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CC",
                "modification_type": "Core Ring Substitution",
                "source": "llm_generative",
                "scaffold_type": "scaffold_hopping",
                "parent_similarity": 0.36,
                "predicted_pkd": 8.25,
                "delta_pkd": 0.13,
                "predicted_kd_nM": 5.62,
                "sa_score": 3.42,
                "sa_tier": "moderate",
                "admet": {
                    "admet_health_score": 72.0,
                    "herg_risk": "low"
                }
            }
        ],
        "audit_metrics": {
            "total_candidates_evaluated": 2,
            "validity_rate": 1.0,
            "scaffold_retention_count": 1,
            "scaffold_hopping_count": 1,
            "mean_pairwise_diversity": 0.58,
            "average_affinity_delta_pkd": 0.28
        },
        "excluded_records": [
            {
                "smiles": "C1=CC=CC=C1",
                "stage": "Affinity Gate",
                "reason": "Predicted pKd below minimum threshold (pKd < 6.0)"
            }
        ]
    }


def test_generate_package_from_payload_and_verify_zip(temp_output_dir, sample_payload):
    """Verify package generation, complete directory tree, and non-recursive SHA256 checksums."""
    generator = SupplementaryDatasetGenerator(output_base_dir=temp_output_dir)
    res = generator.generate_package(
        result_payload=sample_payload,
        target_name="ABL1",
        author="BioAI Verification Lab"
    )

    assert "package_id" in res
    assert "zip_path" in res
    assert Path(res["zip_path"]).exists()
    assert res["total_files"] >= 15

    # Verify using built-in verifier
    ver_result = verify_supplementary_package(Path(res["zip_path"]))
    assert ver_result["is_valid"] is True
    assert len(ver_result["errors"]) == 0
    assert len(ver_result["verified_files"]) >= 15

    # Check mandatory files present in verified files list
    verified = set(ver_result["verified_files"])
    assert "README.md" in verified
    assert "data_dictionary.csv" in verified
    assert "predictions.csv" in verified
    assert "candidates.csv" in verified
    assert "excluded_records.csv" in verified
    assert "provenance.json" in verified
    assert "figures/fig1_affinity_distribution.svg" in verified
    assert "figures/fig1_affinity_distribution.pdf" in verified
    assert "figures/fig1_affinity_distribution_data.csv" in verified
    assert "wetlab/96_well_plate_dispatch.csv" in verified
    assert "reports/research_report.html" in verified
    assert "reports/research_report.md" in verified


def test_non_recursive_sha256sums_integrity(temp_output_dir, sample_payload):
    """Ensure SHA256SUMS file does not list itself and manifest.json is included in checksums."""
    generator = SupplementaryDatasetGenerator(output_base_dir=temp_output_dir)
    res = generator.generate_package(result_payload=sample_payload, target_name="ABL1")

    pkg_dir = Path(res["package_dir"])
    sums_file = pkg_dir / "SHA256SUMS"
    assert sums_file.exists()

    sums_content = sums_file.read_text(encoding="utf-8")
    assert "SHA256SUMS" not in sums_content
    assert "manifest.json" in sums_content  # manifest.json must be verified in SHA256SUMS

    lines = [line.strip() for line in sums_content.splitlines() if line.strip()]
    for line in lines:
        h, rel = line.split(maxsplit=1)
        target = pkg_dir / rel
        assert target.exists()
        assert _compute_sha256(target) == h


def test_tamper_detection_in_package(temp_output_dir, sample_payload):
    """Verify that tampering with any file in the ZIP package is detected by the verifier."""
    generator = SupplementaryDatasetGenerator(output_base_dir=temp_output_dir)
    res = generator.generate_package(result_payload=sample_payload, target_name="ABL1")
    zip_path = Path(res["zip_path"])

    # Extract, tamper with predictions.csv, and re-pack
    tamper_dir = temp_output_dir / "tamper_tmp"
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(tamper_dir)

    pred_file = tamper_dir / "predictions.csv"
    pred_file.write_text(pred_file.read_text(encoding="utf-8") + "\n# TAMPERED LINE\n", encoding="utf-8")

    tampered_zip = temp_output_dir / "tampered.zip"
    with zipfile.ZipFile(tampered_zip, "w") as z:
        for root, _, files in shutil.os.walk(tamper_dir):
            for file in files:
                full_p = Path(root) / file
                rel = full_p.relative_to(tamper_dir)
                z.write(full_p, arcname=str(rel))

    shutil.rmtree(tamper_dir, ignore_errors=True)

    # Verifier must detect tampering
    ver_res = verify_supplementary_package(tampered_zip)
    assert ver_res["is_valid"] is False
    assert any("Hash mismatch on predictions.csv" in err for err in ver_res["errors"])


def test_manifest_tamper_detection(temp_output_dir, sample_payload):
    """Verify that tampering with manifest.json alone is detected and invalidated."""
    generator = SupplementaryDatasetGenerator(output_base_dir=temp_output_dir)
    res = generator.generate_package(result_payload=sample_payload, target_name="ABL1")
    zip_path = Path(res["zip_path"])

    tamper_dir = temp_output_dir / "tamper_manifest_tmp"
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(tamper_dir)

    manifest_file = tamper_dir / "manifest.json"
    m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    m_data["author"] = "Tampered Author"
    manifest_file.write_text(json.dumps(m_data, indent=2), encoding="utf-8")

    tampered_zip = temp_output_dir / "manifest_tampered.zip"
    with zipfile.ZipFile(tampered_zip, "w") as z:
        for root, _, files in shutil.os.walk(tamper_dir):
            for file in files:
                full_p = Path(root) / file
                rel = full_p.relative_to(tamper_dir)
                z.write(full_p, arcname=str(rel))

    shutil.rmtree(tamper_dir, ignore_errors=True)

    ver_res = verify_supplementary_package(tampered_zip)
    assert ver_res["is_valid"] is False
    assert any("Hash mismatch on manifest.json" in err for err in ver_res["errors"])


def test_refuse_empty_unverified_export(temp_output_dir):
    """Verify that formal export without verified computation or task results is strictly rejected."""
    generator = SupplementaryDatasetGenerator(output_base_dir=temp_output_dir)
    with pytest.raises(ValueError, match="未提供有效|拒绝导出"):
        generator.generate_package()


def test_generate_package_from_task_id(temp_output_dir, sample_payload):
    """Verify package generator resolves task result from task_id cache."""
    task_id = "test_task_p5a_001"
    task_dir = PROJECT_ROOT / "output" / "task_results"
    task_dir.mkdir(parents=True, exist_ok=True)
    task_file = task_dir / f"{task_id}.json"

    try:
        task_file.write_text(json.dumps(sample_payload), encoding="utf-8")

        generator = SupplementaryDatasetGenerator(output_base_dir=temp_output_dir)
        res = generator.generate_package(task_id=task_id)

        assert res["package_id"] is not None
        assert Path(res["zip_path"]).exists()

        ver = verify_supplementary_package(Path(res["zip_path"]))
        assert ver["is_valid"] is True
    finally:
        if task_file.exists():
            task_file.unlink()


def test_export_supplementary_package_endpoint(sample_payload):
    """Verify HTTP endpoint for exporting and downloading supplementary packages."""
    from fastapi.testclient import TestClient
    SERVER_DIR = PROJECT_ROOT / "05_web_server"
    if str(SERVER_DIR) not in sys.path:
        sys.path.insert(0, str(SERVER_DIR))
    from research_api import app

    client = TestClient(app)
    resp = client.post(
        "/api/dti/export_supplementary_package",
        json={
            "result_payload": sample_payload,
            "target_name": "ABL1",
            "author": "Endpoint Integration Test"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "package_id" in data
    assert "zip_sha256" in data

    # Test download endpoint
    pkg_id = data["package_id"]
    dl_resp = client.get(f"/api/dti/download_package/{pkg_id}")
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"] == "application/zip"
    assert len(dl_resp.content) > 1000

