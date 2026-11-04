"""Supplementary Research Dataset and Publication Package Generator.

Produces comprehensive, 100% auditable Supplementary Materials packages
compliant with journal submission guidelines (e.g., Nature, J. Med. Chem.).
Includes:
  - README.md & data_dictionary.csv
  - predictions.csv, candidates.csv, excluded_records.csv
  - High-res vector/PDF figures with underlying CSV data tables
  - Wet-lab 96-well microplate dispatch and liquid handling manifests
  - Academic report in Markdown & print-ready HTML
  - manifest.json and non-recursive SHA256SUMS
  - Standard zip archive export
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import logging
import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scientific_figure_exporter import (
    export_affinity_distribution,
    export_screening_funnel,
    export_candidate_sar_comparison
)
from dti_report_generator import generate_dti_academic_report
from wetlab_dispatch_generator import generate_96_well_dispatch

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_BASE = Path(__file__).resolve().parents[1] / "output" / "supplementary_packages"


def _compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class SupplementaryDatasetGenerator:
    """Orchestrates creation of peer-review ready Supplementary Dataset ZIP packages."""

    def __init__(self, output_base_dir: Optional[Path] = None, job_store: Optional[Any] = None):
        self.output_base = Path(output_base_dir or DEFAULT_OUTPUT_BASE)
        self.output_base.mkdir(parents=True, exist_ok=True)
        self.job_store = job_store

    def generate_package(
        self,
        task_id: Optional[str] = None,
        result_payload: Optional[Dict[str, Any]] = None,
        target_name: Optional[str] = None,
        author: str = "DTI BioAI Research Team"
    ) -> Dict[str, Any]:
        """Generate a complete supplementary dataset package."""
        payload = self._resolve_payload(task_id, result_payload)
        is_verified = payload.get("verified", False)
        actual_target = payload.get("target_name") or payload.get("report", {}).get("target_symbol") or payload.get("target_symbol")

        # Lineage & target identity locking:
        # A server-verified execution cannot have its target identity overridden by a client query parameter.
        if is_verified and actual_target:
            t_name = actual_target
        else:
            t_name = target_name or payload.get("target_name") or "Target Kinase"

        model_used = payload.get("model_used") or "stacked_ensemble"
        baseline = payload.get("baseline") or {}
        candidates = payload.get("candidates") or []
        audit_metrics = payload.get("audit_metrics") or {}

        package_id = f"pkg_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        pkg_dir = self.output_base / package_id
        pkg_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. README.md
            self._write_readme(pkg_dir, package_id, t_name, model_used, author, baseline, audit_metrics, is_verified=is_verified)

            # 2. data_dictionary.csv
            self._write_data_dictionary(pkg_dir)

            # 3. predictions.csv
            self._write_predictions_csv(
                pkg_dir, baseline, candidates, t_name, model_used,
                task_type=payload.get("task_type", "lead_optimization"),
                is_verified=is_verified
            )

            # 4. candidates.csv
            self._write_candidates_csv(pkg_dir, candidates, baseline)

            # 5. excluded_records.csv
            self._write_excluded_records_csv(pkg_dir, payload)

            # 6. provenance.json
            self._write_provenance_json(
                pkg_dir, package_id, payload.get("task_id"), t_name, model_used,
                baseline, audit_metrics, author, is_verified=is_verified
            )

            # 7. Scientific Figures (SVG, PDF, PNG + CSV)
            self._generate_figures(pkg_dir, baseline, candidates, audit_metrics, t_name)

            # 8. Wet-lab Microplate Layouts
            dispatch_baseline = baseline if (baseline.get("smiles") or baseline.get("predicted_pkd")) else (candidates[0] if candidates else {})
            self._generate_wetlab_dispatch(pkg_dir, dispatch_baseline, candidates, t_name)

            # 9. Reports (Markdown & Standalone HTML)
            self._generate_reports(pkg_dir, dispatch_baseline, candidates, t_name, model_used, author, is_verified=is_verified)

            # 10. Generate manifest.json & SHA256SUMS
            manifest_data, sums_file = self._build_manifest_and_sums(pkg_dir, package_id, author)

            # 11. Create ZIP Archive
            zip_path = self.output_base / f"{package_id}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(pkg_dir):
                    for file in files:
                        full_p = Path(root) / file
                        rel_p = full_p.relative_to(pkg_dir)
                        zipf.write(full_p, arcname=str(rel_p))

            zip_sha256 = _compute_sha256(zip_path)

            return {
                "package_id": package_id,
                "package_dir": str(pkg_dir),
                "zip_path": str(zip_path),
                "zip_sha256": zip_sha256,
                "total_files": len(manifest_data["files"]),
                "created_at": datetime.datetime.now().isoformat(),
                "manifest": manifest_data
            }

        except Exception as exc:
            logger.exception("Failed to generate supplementary package: %s", exc)
            raise

    def _is_registered_model(self, model_name: str) -> bool:
        """Check if model name matches registered and benchmarked DTI models."""
        if not model_name or not isinstance(model_name, str):
            return False
        name = model_name.strip()
        VALID_MODELS = {
            "stacked_ensemble", "f1_ridge", "linear_tobit", "tobit_ranking_model",
            "bilinear_esm2", "bilinear_esm2_interaction", "ridge", "ridge_alpha10",
            "ridge_alpha50", "hist_gradient_boosting", "mlp", "random_forest",
            "extra_trees", "svm_rbf", "rigorous_stacked_ensemble",
            "worldmodel_stacked_ensemble", "dummy_mean",
        }
        rigorous_ids = {f"rigorous_{base}" for base in (
            "ridge_alpha10", "ridge_alpha50", "hist_gradient_boosting", "random_forest", "stacked_ensemble"
        )}
        return name in VALID_MODELS or name in rigorous_ids

    def _resolve_payload(
        self,
        task_id: Optional[str],
        result_payload: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Resolve result payload from direct input or task result store with strict authentication."""
        raw_payload = None
        server_verified = False
        resolved_task_id = None

        candidate_tid = task_id or (result_payload.get("task_id") if isinstance(result_payload, dict) else None)
        if candidate_tid:
            # Check SQLite task store first
            try:
                store = self.job_store
                if store is None:
                    from async_job_store import AsyncJobStore
                    store = AsyncJobStore(auto_recover=False)
                t_record = store.get_task(candidate_tid)
                full_res = store.get_task_result(candidate_tid)
                if t_record and t_record.get("status") == "completed" and full_res:
                    raw_payload = full_res
                    server_verified = True
                    resolved_task_id = candidate_tid
            except Exception as e:
                logger.warning("Could not read from async store: %s", e)

            # Check disk files
            if not server_verified:
                for fname in (f"{candidate_tid}_result.json", f"{candidate_tid}.json"):
                    result_file = Path(__file__).resolve().parents[1] / "output" / "task_results" / fname
                    if result_file.exists():
                        try:
                            with open(result_file, "r", encoding="utf-8") as f:
                                raw_payload = json.load(f)
                                # A cache alone does not prove successful execution. In particular,
                                # it must never override a pending/cancelled/missing database record.
                                server_verified = False
                                resolved_task_id = None
                                break
                        except Exception as e:
                            logger.warning("Error reading task result file %s: %s", result_file, e)

            if not raw_payload and not result_payload:
                raise ValueError(f"Task result for '{candidate_tid}' not found on disk or store.")

        if not raw_payload:
            if result_payload:
                raw_payload = result_payload
                server_verified = False
                resolved_task_id = None
            else:
                raise ValueError("未提供有效的计算任务 ID 或预测结果载荷。正式科研交付材料严禁导出无来源的默认伪造数据。")

        # 1. Strict model registration check
        model_used = raw_payload.get("model_used")
        report = raw_payload.get("report")
        if not model_used and isinstance(report, dict):
            model_used = report.get("model_used")
        if not model_used:
            if not server_verified:
                raise ValueError("未指定推理模型名称 (model_used)。直接输入材料必须明确指定已注册的推理模型名称。")
            model_used = "stacked_ensemble"

        if not self._is_registered_model(model_used):
            raise ValueError(f"未注册或未执行的模型: '{model_used}'，拒绝导出正式科研交付材料。必须使用经基准验证的注册推理模型。")

        # 2. Virtual screening / hits task schema adaptation
        report_dict = report if isinstance(report, dict) else {}
        has_hits = ("hits" in report_dict) or ("hits" in raw_payload)

        if has_hits:
            raw_hits = report_dict.get("hits") if "hits" in report_dict else raw_payload.get("hits")
            raw_hits = raw_hits or []
            if not raw_hits and not raw_payload.get("candidates"):
                raise ValueError("筛选任务报告中未包含任何命中结果 (hits 为空)，拒绝导出空结果科研包。")

            target_symbol = report_dict.get("target_symbol") or raw_payload.get("target_name") or "Target Kinase"
            model_name = report_dict.get("model_used") or raw_payload.get("model_used") or model_used

            adapted_candidates = []
            for idx, hit in enumerate(raw_hits):
                c_pkd = hit.get("predicted_pkd")
                c_kd = hit.get("predicted_kd_nM")
                if c_kd is None and c_pkd is not None:
                    try:
                        c_kd = round(10 ** (9 - float(c_pkd)), 2)
                    except Exception:
                        c_kd = None
                admet_obj = hit.get("admet") or {}
                adapted_candidates.append({
                    "id": hit.get("id") or f"HIT_{idx+1:03d}",
                    "name": hit.get("name") or f"Hit_{idx+1}",
                    "smiles": hit.get("smiles", ""),
                    "modification_type": f"Screening Hit (Cluster {hit.get('cluster_id', 1)})",
                    "source": hit.get("vendor_source") or "screening_run",
                    "scaffold_type": f"Cluster_{hit.get('cluster_id', 1)}",
                    "parent_similarity": hit.get("parent_similarity"),
                    "predicted_pkd": c_pkd,
                    "predicted_kd_nM": c_kd,
                    "delta_pkd": hit.get("delta_pkd"),
                    "sa_score": hit.get("sa_score"),
                    "sa_tier": hit.get("sa_label", "moderate"),
                    "admet": admet_obj,
                    "domain": hit.get("domain", ""),
                    "affinity_tier": "high_affinity" if (c_pkd is not None and float(c_pkd) >= 7.0) else "moderate_affinity"
                })

            excluded = []
            for f in report_dict.get("failed_compounds", []):
                excluded.append({
                    "id": f.get("name") or f.get("smiles", "Unknown"),
                    "smiles": f.get("smiles", ""),
                    "stage": "Screening Gate",
                    "reason": f.get("reason", "Filtered during screening")
                })
            for ex in report_dict.get("excluded_below_threshold", []):
                excluded.append({
                    "id": ex.get("name") or ex.get("smiles", "Unknown"),
                    "smiles": ex.get("smiles", ""),
                    "stage": "Affinity Threshold Filter",
                    "reason": f"Predicted pKd ({ex.get('predicted_pkd')}) below threshold"
                })

            total_screened = report_dict.get("total_screened", len(adapted_candidates))
            audit_metrics = {
                "total_candidates_evaluated": total_screened,
                "reported_hit_count": len(adapted_candidates),
                "hit_rate": round(len(adapted_candidates) / total_screened, 4) if total_screened else None,
            }

            return {
                "task_id": resolved_task_id,
                "target_name": target_symbol,
                "model_used": model_name,
                "baseline": {},
                "candidates": adapted_candidates,
                "excluded_records": excluded,
                "audit_metrics": audit_metrics,
                "task_type": "virtual_screening",
                "verified": server_verified
            }

        # 3. Standard lead optimization schema validation
        baseline = raw_payload.get("baseline") or {}
        candidates = raw_payload.get("candidates") or []
        if not baseline.get("predicted_pkd") and not candidates:
            raise ValueError("提供的计算结果为空或未包含有效的预测亲和力数据。拒绝导出无来源数据。")

        raw_payload["verified"] = server_verified
        raw_payload["task_id"] = resolved_task_id
        raw_payload["model_used"] = model_used
        raw_payload["task_type"] = raw_payload.get("task_type", "lead_optimization")

        return raw_payload

    def _write_readme(
        self,
        pkg_dir: Path,
        pkg_id: str,
        target_name: str,
        model_used: str,
        author: str,
        baseline: Dict[str, Any],
        audit_metrics: Dict[str, Any],
        is_verified: bool = True
    ):
        if is_verified:
            disclaimer_section = """
> **CRITICAL SCIENTIFIC DISCLAIMER**:
> All affinity values (`pKd`, `Kd_nM`, `ΔpKd`) reported in this package represent machine learning predictions and molecular simulations derived from the DAVIS Kinome benchmark and rigorous DTI inference runtimes. 
> These values serve as **design hypotheses** and prioritized candidates for wet-lab in vitro binding assays (e.g., SPR, ITC, KinomeScan). They do **NOT** represent confirmed clinical measurements or approved therapeutic claims."""
        else:
            disclaimer_section = """
> **CRITICAL SCIENTIFIC INTEGRITY WARNING**:
> All affinity values (`pKd`, `Kd_nM`, `ΔpKd`) reported in this package represent user-supplied or unverified external candidate records without authenticated server-side runtime model execution (no verified task_id).
> These records are tagged as **(Unverified)**. They serve as unverified external input hypotheses and MUST NOT be treated as benchmarked model runtime predictions."""

        validity = audit_metrics.get('validity_rate')
        validity_text = f"{float(validity) * 100:.1f}%" if validity is not None else "N/A"
        readme_content = f"""# Supplementary Dataset & Peer-Review Package

- **Package ID**: `{pkg_id}`
- **Target Kinase**: `{target_name}`
- **Evaluation Model**: `{model_used if is_verified else f"{model_used} (Unverified)"}`
- **Verification Status**: `{'Server-Verified Model Execution' if is_verified else 'Unverified User-Provided Input'}`
- **Corresponding Author / Lab**: `{author}`
- **Generated Timestamp**: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`

---

## 1. Scientific Purpose & Protocol Governance

This supplementary data package provides the computational and biophysical lineage for kinase inhibitor affinity evaluation, de novo design, and lead optimization.
{disclaimer_section}

---

## 2. Directory Structure & File Manifest

| File / Folder | Format | Description |
|---|---|---|
| `README.md` | Markdown | Study overview, scientific provenance, and validation disclaimers |
| `data_dictionary.csv` | CSV | Standardized column names, definitions, data types, and units |
| `predictions.csv` | CSV | Machine learning affinity scores for baseline and derived candidates |
| `candidates.csv` | CSV | Detailed candidate molecular structures, sources, and SAR properties |
| `excluded_records.csv` | CSV | Candidates filtered out due to syntax, molecular weight, or hard constraints |
| `provenance.json` | JSON | Machine-readable experiment parameters, seeds, and model checksums |
| `figures/` | SVG/PDF/CSV | Publication-grade vector figures and underlying numerical tables |
| `wetlab/` | CSV | 96-well microplate layout and automated liquid handler picklists |
| `reports/` | MD/HTML | Full academic research brief and printable standalone HTML disclosure |
| `manifest.json` | JSON | File inventory with MIME types and individual file SHA-256 hashes |
| `SHA256SUMS` | Text | Non-recursive SHA-256 integrity checksums for all package assets |

---

## 3. Computational Metrics Summary

- **Baseline Lead**: `{baseline.get('name', 'Reference Lead')}` (SMILES: `{baseline.get('smiles', '')}`)
- **Baseline pKd**: `{baseline.get('predicted_pkd', 'N/A')}` (`{baseline.get('predicted_kd_nM', 'N/A')} nM`)
- **Scaffold Retention Count**: `{audit_metrics.get('scaffold_retention_count', 'N/A')}`
- **Scaffold Hopping Count**: `{audit_metrics.get('scaffold_hopping_count', 'N/A')}`
- **Mean Pairwise Diversity**: `{audit_metrics.get('mean_pairwise_diversity', 'N/A')}`
- **Validity Rate**: `{validity_text}`
"""
        (pkg_dir / "README.md").write_text(readme_content, encoding="utf-8")

    def _write_data_dictionary(self, pkg_dir: Path):
        dict_rows = [
            ["Column_Name", "Data_Type", "Units", "Source_Method", "Description"],
            ["Candidate_ID", "String", "None", "System UUID", "Unique identifier for candidate compound"],
            ["Name", "String", "None", "Design Engine", "Descriptive chemical or code name of the molecule"],
            ["SMILES", "String", "None", "RDKit Standard", "Canonical Simplified Molecular Input Line Entry System string"],
            ["Modification_Type", "String", "None", "MedChem Rule / Prompt", "Targeted chemical transformation or bioisosteric substitution"],
            ["Source", "String", "None", "Provenance Tracker", "Generation provenance ('heuristic_rule' or 'llm_generative')"],
            ["Scaffold_Type", "String", "None", "Morgan Tanimoto", "'scaffold_retention' (Sim >= 0.40) or 'scaffold_hopping' (Sim < 0.40)"],
            ["Parent_Similarity", "Float", "Tanimoto [0, 1]", "RDKit Morgan Fingerprint", "Structural similarity against baseline lead molecule"],
            ["Predicted_pKd", "Float", "-log10(M)", "DTI Inference Model", "Predicted binding affinity pKd = -log10(Kd)"],
            ["Predicted_Kd_nM", "Float", "nM", "Calculated: 10^(9-pKd)", "Dissociation constant in nanomolar concentration"],
            ["Delta_pKd", "Float", "pKd shift", "Predicted_pKd - Base_pKd", "Affinity change relative to reference lead baseline"],
            ["SA_Score", "Float", "Scale 1-10", "Ertl/Schuffenhauer SA", "Synthetic accessibility score (1: readily synthesizable, 10: difficult)"],
            ["SA_Tier", "String", "None", "SA Categorizer", "Categorical synthesis complexity: 'easy', 'moderate', or 'challenging'"],
            ["ADMET_Health_Score", "Float", "Scale 0-100", "ADMET Ensemble", "Composite drug-likeness and pharmacokinetic compliance score"],
            ["HERG_Risk", "String", "None", "Cardiotoxicity Filter", "hERG potassium channel cardiotoxicity risk flag ('low', 'medium', 'high')"],
            ["Exclusion_Reason", "String", "None", "Gatekeeper", "Detailed rationale why candidate was rejected by hard constraints"]
        ]
        with open(pkg_dir / "data_dictionary.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(dict_rows)

    def _write_predictions_csv(
        self,
        pkg_dir: Path,
        baseline: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        target_name: str,
        model_used: str,
        task_type: str = "lead_optimization",
        is_verified: bool = True
    ):
        with open(pkg_dir / "predictions.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Entity_Type", "Compound_Name", "SMILES", "Target_Symbol",
                "Predicted_pKd", "Predicted_Kd_nM", "Delta_pKd", "Model_Used", "Affinity_Tier", "Domain"
            ])

            # Only write baseline row if baseline has actual data (do not fabricate fake baseline row)
            has_baseline = bool(baseline and (baseline.get("predicted_pkd") is not None or baseline.get("smiles")))
            base_pkd = float(baseline.get("predicted_pkd")) if (has_baseline and baseline.get("predicted_pkd") is not None) else None

            if has_baseline:
                base_kd = baseline.get("predicted_kd_nM")
                if base_kd is None and base_pkd is not None:
                    try:
                        base_kd = round(10 ** (9 - float(base_pkd)), 2)
                    except Exception:
                        base_kd = ""
                base_tier = baseline.get("affinity_tier") or ("high_affinity" if (base_pkd is not None and float(base_pkd) >= 7.0) else "moderate_affinity" if base_pkd is not None else "")
                writer.writerow([
                    "Baseline_Lead",
                    baseline.get("name", "Reference Lead"),
                    baseline.get("smiles", ""),
                    target_name,
                    base_pkd if base_pkd is not None else "",
                    base_kd if base_kd is not None else "",
                    0.0 if base_pkd is not None else "",
                    model_used if is_verified else f"{model_used} (Unverified)",
                    base_tier,
                    baseline.get("domain", "")  # Do not pad fake domain!
                ])

            # Candidates / Hits
            for c in candidates:
                c_pkd = c.get("predicted_pkd")
                c_kd = c.get("predicted_kd_nM")
                if c_kd is None and c_pkd is not None:
                    try:
                        c_kd = round(10 ** (9 - float(c_pkd)), 2)
                    except Exception:
                        c_kd = ""
                c_delta = c.get("delta_pkd")
                if c_delta is None and c_pkd is not None and base_pkd is not None:
                    try:
                        c_delta = round(float(c_pkd) - float(base_pkd), 4)
                    except Exception:
                        c_delta = ""

                c_tier = c.get("affinity_tier") or ("high_affinity" if (c_pkd is not None and float(c_pkd) >= 7.0) else "moderate_affinity" if c_pkd is not None else "")
                entity_type = "Screening_Hit" if task_type == "virtual_screening" else "Candidate_Derivative"

                c_target = c.get("target_symbol") or target_name
                writer.writerow([
                    entity_type,
                    c.get("name", "Derivative"),
                    c.get("smiles", ""),
                    c_target,
                    round(float(c_pkd), 4) if c_pkd is not None else "",
                    round(float(c_kd), 2) if (c_kd is not None and c_kd != "") else "",
                    round(float(c_delta), 4) if (c_delta is not None and c_delta != "") else "",
                    model_used if is_verified else f"{model_used} (Unverified)",
                    c_tier,
                    c.get("domain", "")  # Leave empty if not provided!
                ])

    def _write_candidates_csv(
        self,
        pkg_dir: Path,
        candidates: List[Dict[str, Any]],
        baseline: Dict[str, Any]
    ):
        with open(pkg_dir / "candidates.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Candidate_ID", "Name", "SMILES", "Modification_Type", "Source",
                "Scaffold_Type", "Parent_Similarity", "Predicted_pKd", "Delta_pKd",
                "SA_Score", "SA_Tier", "ADMET_Health_Score", "HERG_Risk"
            ])
            has_baseline = bool(baseline and baseline.get("predicted_pkd") is not None)
            base_pkd = float(baseline.get("predicted_pkd")) if has_baseline else None

            for idx, c in enumerate(candidates):
                c_pkd = c.get("predicted_pkd")
                c_delta = c.get("delta_pkd")
                if c_delta is None and c_pkd is not None and base_pkd is not None:
                    try:
                        c_delta = round(float(c_pkd) - float(base_pkd), 4)
                    except Exception:
                        c_delta = ""
                admet = c.get("admet") or {}
                sa_score = c.get("sa_score")
                admet_score = admet.get("admet_health_score")
                sim = c.get("parent_similarity")

                writer.writerow([
                    c.get("id", f"CAND_{idx+1:03d}"),
                    c.get("name", f"Candidate_{idx+1}"),
                    c.get("smiles", ""),
                    c.get("modification_type", ""),
                    c.get("source", ""),
                    c.get("scaffold_type", ""),
                    round(float(sim), 3) if sim is not None else "",
                    round(float(c_pkd), 4) if c_pkd is not None else "",
                    round(float(c_delta), 4) if (c_delta is not None and c_delta != "") else "",
                    round(float(sa_score), 2) if sa_score is not None else "",
                    c.get("sa_tier", "") if sa_score is not None else "",
                    round(float(admet_score), 1) if admet_score is not None else "",
                    admet.get("herg_risk", "") if admet_score is not None else ""
                ])

    def _write_excluded_records_csv(self, pkg_dir: Path, payload: Dict[str, Any]):
        excluded = payload.get("excluded_records") or []
        with open(pkg_dir / "excluded_records.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Record_ID", "Identifier_or_SMILES", "Stage_Excluded", "Exclusion_Reason"])
            if not excluded:
                # Add documented empty/zero rejection placeholder row
                writer.writerow(["EXCL_NONE", "None", "Pre-Filter", "No candidates violated hard chemical constraints in this run."])
            else:
                for idx, item in enumerate(excluded):
                    writer.writerow([
                        f"EXCL_{idx+1:03d}",
                        item.get("smiles") or item.get("id", "Unknown"),
                        item.get("stage", "Hard Constraint Verification"),
                        item.get("reason", "Violated hard parameter thresholds")
                    ])

    def _write_provenance_json(
        self,
        pkg_dir: Path,
        pkg_id: str,
        task_id: Optional[str],
        target_name: str,
        model_used: str,
        baseline: Dict[str, Any],
        audit_metrics: Dict[str, Any],
        author: str,
        is_verified: bool = True
    ):
        prov = {
            "package_id": pkg_id,
            "task_id": task_id if is_verified else None,
            "execution_verified": is_verified,
            "created_at": datetime.datetime.now().isoformat(),
            "target_kinase": target_name,
            "model_used": model_used if is_verified else f"{model_used} (Unverified)",
            "author": author,
            "reproducibility": {
                "evaluation_protocol": "protocol-dti-01.json" if is_verified else None,
                "dataset_benchmark": "DAVIS Kinome 379 Targets" if is_verified else None,
                "random_seed": 42 if is_verified else None,
                "rdkit_sanitization_enabled": False,
                "sanitization_method": "internal_grammar_and_valence_validator",
                "verification_status": "server_executed" if is_verified else "unverified_external_input",
                "integrity_warning": None if is_verified else "Unverified external input; not generated by backend runtime execution."
            },
            "baseline_reference": {
                "name": baseline.get("name"),
                "smiles": baseline.get("smiles"),
                "predicted_pkd": baseline.get("predicted_pkd"),
                "predicted_kd_nM": baseline.get("predicted_kd_nM")
            },
            "audit_metrics": audit_metrics
        }
        with open(pkg_dir / "provenance.json", "w", encoding="utf-8") as f:
            json.dump(prov, f, indent=2, ensure_ascii=False)

    def _generate_figures(
        self,
        pkg_dir: Path,
        baseline: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        audit_metrics: Dict[str, Any],
        target_name: str
    ):
        fig_dir = pkg_dir / "figures"
        fig_dir.mkdir(parents=True, exist_ok=True)

        has_baseline = bool(baseline and baseline.get("predicted_pkd") is not None)
        base_pkd = float(baseline.get("predicted_pkd")) if has_baseline else None
        cand_scores = [float(c["predicted_pkd"]) for c in candidates if c.get("predicted_pkd") is not None]
        scores = ([base_pkd] if base_pkd is not None else []) + cand_scores
        # Do not pass empty data to legacy plotting helpers that insert example values.
        if scores:
            export_affinity_distribution(
                predictions_or_scores=scores,
                baseline_pkd=base_pkd,
                output_dir=fig_dir,
                target_name=target_name,
                filename_prefix="fig1_affinity_distribution"
            )
        else:
            (fig_dir / "fig1_affinity_distribution_data.csv").write_text("Index,Target_Name,Predicted_pKd,Estimated_Kd_nM\n", encoding="utf-8")
            (fig_dir / "fig1_unavailable.txt").write_text("No affinity scores were provided; no distribution plot was generated.\n", encoding="utf-8")

        # Figure 2: Screening Funnel
        funnel_stages = [
            {"stage": "1. Exported candidate records", "count": len(candidates)},
            {"stage": "2. Records with reported pKd", "count": len(cand_scores)},
            {"stage": "3. Reported pKd >= 7", "count": sum(score >= 7.0 for score in cand_scores)}
        ]
        export_screening_funnel(
            funnel_stages=funnel_stages,
            output_dir=fig_dir,
            filename_prefix="fig2_screening_funnel"
        )

        # Figure 3: SAR Comparison
        sar_records = []
        for candidate in candidates:
            delta = candidate.get("delta_pkd")
            if delta is None and base_pkd is not None and candidate.get("predicted_pkd") is not None:
                delta = float(candidate["predicted_pkd"]) - base_pkd
            if delta is not None and candidate.get("predicted_pkd") is not None and candidate.get("scaffold_type") and candidate.get("source"):
                sar_records.append({**candidate, "delta_pkd": delta})
        if sar_records:
            export_candidate_sar_comparison(candidates=sar_records, baseline_pkd=base_pkd, output_dir=fig_dir, filename_prefix="fig3_sar_comparison")
        else:
            (fig_dir / "fig3_sar_comparison_data.csv").write_text("Rank,Candidate_Name,Predicted_pKd,Delta_pKd,Scaffold_Type,Source\n", encoding="utf-8")
            (fig_dir / "fig3_unavailable.txt").write_text("Required affinity, scaffold or source metadata was not reported; no SAR gain plot was generated.\n", encoding="utf-8")

    def _generate_wetlab_dispatch(
        self,
        pkg_dir: Path,
        baseline: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        target_name: str
    ):
        wetlab_dir = pkg_dir / "wetlab"
        wetlab_dir.mkdir(parents=True, exist_ok=True)

        dispatch_res = generate_96_well_dispatch(
            target_name=target_name,
            baseline=baseline,
            candidates=candidates
        )

        # Save 96-well microplate layout CSV
        with open(wetlab_dir / "96_well_plate_dispatch.csv", "w", newline="", encoding="utf-8") as f:
            f.write(dispatch_res["csv_content"])

        # Save Labcyte Echo / Tecan liquid handler picklist CSV
        import io
        echo_io = io.StringIO()
        echo_writer = csv.writer(echo_io)
        echo_writer.writerow([
            "Source_Plate_Barcode", "Source_Well", "Destination_Plate_Barcode",
            "Destination_Well", "Transfer_Volume_nL", "Sample_ID", "Compound_Name"
        ])
        for w in dispatch_res.get("wells", []):
            echo_writer.writerow([
                w.get("plate_barcode", "PLATE-SRC"),
                w.get("well_id", "A01"),
                f"DEST-{target_name.upper()}-01",
                w.get("well_id", "A01"),
                250,
                w.get("compound_id", "CMPD"),
                w.get("compound_name", "Lead")
            ])
        with open(wetlab_dir / "liquid_handler_echo.csv", "w", newline="", encoding="utf-8") as f:
            f.write(echo_io.getvalue())

    def _generate_reports(
        self,
        pkg_dir: Path,
        baseline: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        target_name: str,
        model_used: str,
        author: str,
        is_verified: bool = True
    ):
        rep_dir = pkg_dir / "reports"
        rep_dir.mkdir(parents=True, exist_ok=True)

        report_res = generate_dti_academic_report(
            target_name=target_name,
            baseline=baseline,
            candidates=candidates,
            author=author,
            model_name=model_used,
            is_verified=is_verified
        )

        (rep_dir / "research_report.md").write_text(report_res["markdown_report"], encoding="utf-8")
        (rep_dir / "research_report.html").write_text(report_res["html_report"], encoding="utf-8")

    def _build_manifest_and_sums(
        self,
        pkg_dir: Path,
        pkg_id: str,
        author: str
    ) -> Tuple[Dict[str, Any], Path]:
        """Index all files, write manifest.json, and write non-recursive SHA256SUMS covering all deliverables."""
        file_entries = []

        # 1. Collect all payload files except manifest.json and SHA256SUMS
        payload_files = sorted([p for p in pkg_dir.rglob("*") if p.is_file()])

        for p in payload_files:
            rel = p.relative_to(pkg_dir)
            rel_str = str(rel).replace("\\", "/")
            if rel_str in ("manifest.json", "SHA256SUMS"):
                continue

            file_hash = _compute_sha256(p)
            file_size = p.stat().st_size
            ext = p.suffix.lower()
            mime = "text/plain"
            if ext == ".csv": mime = "text/csv"
            elif ext == ".json": mime = "application/json"
            elif ext == ".md": mime = "text/markdown"
            elif ext == ".html": mime = "text/html"
            elif ext == ".svg": mime = "image/svg+xml"
            elif ext == ".pdf": mime = "application/pdf"
            elif ext == ".png": mime = "image/png"

            file_entries.append({
                "path": rel_str,
                "size_bytes": file_size,
                "sha256": file_hash,
                "mime_type": mime
            })

        # 2. Write manifest.json FIRST
        manifest_data = {
            "package_id": pkg_id,
            "created_at": datetime.datetime.now().isoformat(),
            "author": author,
            "total_files": len(file_entries) + 2,  # including manifest.json and SHA256SUMS
            "files": file_entries
        }
        manifest_file = pkg_dir / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        # 3. Write SHA256SUMS for ALL deliverables including manifest.json (excluding only SHA256SUMS itself)
        all_deliverables = sorted([p for p in pkg_dir.rglob("*") if p.is_file()])
        sums_lines = []
        for p in all_deliverables:
            rel = p.relative_to(pkg_dir)
            rel_str = str(rel).replace("\\", "/")
            if rel_str == "SHA256SUMS":
                continue
            h = _compute_sha256(p)
            sums_lines.append(f"{h}  {rel_str}")

        sums_file = pkg_dir / "SHA256SUMS"
        sums_file.write_text("\n".join(sums_lines) + "\n", encoding="utf-8")

        return manifest_data, sums_file


def verify_supplementary_package(zip_path: Path) -> Dict[str, Any]:
    """Verify integrity, non-recursive SHA256SUMS, and completeness of a supplementary ZIP package."""
    z_path = Path(zip_path)
    if not z_path.exists():
        return {"is_valid": False, "errors": [f"File not found: {z_path}"], "verified_files": []}

    errors: List[str] = []
    verified_files: List[str] = []

    temp_extract = z_path.parent / f"_verify_tmp_{uuid.uuid4().hex[:6]}"
    try:
        with zipfile.ZipFile(z_path, "r") as zipf:
            zipf.extractall(temp_extract)

        sums_file = temp_extract / "SHA256SUMS"
        if not sums_file.exists():
            errors.append("Missing required 'SHA256SUMS' file in archive.")
            return {"is_valid": False, "errors": errors, "verified_files": []}

        # Check required files
        for req in ["README.md", "manifest.json", "data_dictionary.csv", "predictions.csv", "candidates.csv"]:
            if not (temp_extract / req).exists():
                errors.append(f"Missing mandatory deliverable: {req}")

        # Verify each line in SHA256SUMS
        lines = sums_file.read_text(encoding="utf-8").strip().splitlines()
        manifest_verified = False
        for line in lines:
            if not line.strip():
                continue
            parts = line.strip().split(maxsplit=1)
            if len(parts) != 2:
                errors.append(f"Malformed checksum line: {line}")
                continue
            expected_hash, rel_path = parts[0], parts[1].strip()
            target_f = temp_extract / rel_path
            if not target_f.exists():
                errors.append(f"File listed in SHA256SUMS does not exist: {rel_path}")
                continue

            actual_hash = _compute_sha256(target_f)
            if actual_hash != expected_hash:
                errors.append(f"Hash mismatch on {rel_path}: expected {expected_hash}, got {actual_hash}")
            else:
                verified_files.append(rel_path)
                if rel_path == "manifest.json":
                    manifest_verified = True

        if not manifest_verified:
            errors.append("manifest.json was not verified in SHA256SUMS.")

        # Check for unexpected extra files in archive not in SHA256SUMS
        all_extracted = set(str(p.relative_to(temp_extract)).replace("\\", "/") for p in temp_extract.rglob("*") if p.is_file())
        expected_set = set(verified_files) | {"SHA256SUMS"}
        extra_files = all_extracted - expected_set
        if extra_files:
            errors.append(f"Archive contains unindexed extra files: {sorted(list(extra_files))}")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "verified_files": verified_files,
            "total_verified": len(verified_files)
        }

    finally:
        shutil.rmtree(temp_extract, ignore_errors=True)
