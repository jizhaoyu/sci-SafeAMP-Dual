"""Run the frozen exploratory MIC-only baselines against audited fixed folds."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
                             matthews_corrcoef, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_code"))
from feature_extractor import extract_handcrafted_features

DEFAULT_PROTOCOL_PATH = ROOT / "03_experiments/protocols/protocol-mic-05.json"
EXPECTED_AUDIT_PROTOCOL_SHA = "d54227ebb5380039cd07f6ddc979561ef6f99efaecdb7644267e6c7d00dffb97"
EXPECTED_STUDY_PROTOCOL_SHA = "293acc617fc8ab5d09453eb6645eea76dc6e02d899972bf61b85111484bb3d74"
EXPECTED_TRAINING_PROTOCOL_SHA = "8a3533fc64047e679e72d9e07f59d295f44e8c5905da7e822df27210960df24a"
CURRENT_AUDIT_MANIFEST = ROOT / "03_experiments/audits/mic_only_cohort_20261001_v9/manifest.json"
CURRENT_STUDY_MANIFEST = ROOT / "03_experiments/audits/mic_study_disjoint_20261001_v5/manifest.json"
CURRENT_TARGET_AUDIT = ROOT / "03_experiments/audits/mic_only_cohort_20261001_v9/target_identifier_audit.csv"
EXPECTED_TARGET_AUDIT_SHA = "b9b873e4a1c1ff2e97b2bd7305e82fc63f4af4c472e07f28443a04be273af166"


class PrimaryStudyReviewRequired(ValueError):
    """The frozen cohort still lacks primary-study confirmation of its assay targets."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def load_and_validate(protocol_path: Path) -> tuple[dict, pd.DataFrame, str, Path, Path, Path, dict]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    digest = canonical_sha256(protocol)
    if protocol.get("protocol_id") != "protocol-mic-05" or protocol.get("protocol_version") != 1 or digest != EXPECTED_TRAINING_PROTOCOL_SHA:
        raise ValueError("Unexpected training protocol identity/version.")
    if protocol.get("status") != "frozen_exploratory_baseline_training":
        raise ValueError("Training protocol is not frozen for this exploratory run.")
    if (protocol.get("parent_audit_protocol_sha256") != EXPECTED_AUDIT_PROTOCOL_SHA
            or protocol.get("study_audit_protocol_sha256") != EXPECTED_STUDY_PROTOCOL_SHA):
        raise ValueError("Training protocol does not point to the expected immutable audit protocols.")
    audit_path = ROOT / protocol["cohort_manifest"]
    study_path = ROOT / protocol["study_manifest"]
    components_path = ROOT / protocol["combined_components"]
    folds_path = ROOT / protocol["fold_assignments"]
    if audit_path.resolve() != CURRENT_AUDIT_MANIFEST.resolve() or study_path.resolve() != CURRENT_STUDY_MANIFEST.resolve():
        raise ValueError("Historical audits cannot authorize a new exploratory run.")
    for path, hash_key in ((audit_path, "cohort_manifest_sha256"), (study_path, "study_manifest_sha256"),
                           (components_path, "combined_components_sha256"), (folds_path, "fold_assignments_sha256")):
        if sha256(path) != protocol[hash_key]:
            raise ValueError(f"Frozen training input checksum mismatch: {path}")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    study = json.loads(study_path.read_text(encoding="utf-8"))
    if (audit.get("status") != "feasible_for_training_review" or audit.get("protocol_sha256") != EXPECTED_AUDIT_PROTOCOL_SHA
            or audit.get("combined_evidence_gate", {}).get("status") != "passed"
            or audit.get("target_identifier_gate", {}).get("status") != "passed" or audit.get("blockers")):
        raise ValueError("Cohort audit is not in the expected evidence-passed state.")
    if (study.get("status") != "feasible_for_training_review" or study.get("protocol_sha256") != EXPECTED_STUDY_PROTOCOL_SHA
            or study.get("cohort_size") != audit.get("unique_labeled_molecule_count")
            or study.get("cross_fold_homology_edges") != 0 or study.get("cross_fold_primary_studies") != 0
            or study.get("blockers") or not all(fold.get("gate_passed") for fold in study.get("folds", []))):
        raise ValueError("Study-disjoint audit did not pass its fixed gate.")
    for relative_path, expected_sha in study["input_sha256"].items():
        if sha256(ROOT / relative_path) != expected_sha:
            raise ValueError(f"Study-disjoint evidence changed after audit: {relative_path}")
    components = pd.read_csv(components_path)
    folds = pd.read_csv(folds_path)
    required = {"sample_id", "seq", "amp", "homology_component", "combined_component", "primary_study_ids"}
    if not required.issubset(components.columns) or not {"sample_id", "amp", "combined_component", "fold", "role"}.issubset(folds.columns):
        raise ValueError("Study-disjoint components or fold assignment missing required columns.")
    if components.sample_id.duplicated().any() or components.seq.duplicated().any() or len(components) != audit["unique_labeled_molecule_count"]:
        raise ValueError("Expected one unique sequence per audited molecule.")
    if set(folds.fold.astype(int)) != set(range(5)):
        raise ValueError("Expected exactly five fixed folds numbered 0..4.")
    if not folds.role.isin(["train", "validation"]).all() or not folds.amp.isin([0, 1]).all():
        raise ValueError("Unexpected roles or non-binary measured labels in fixed fold input.")
    merged = folds.merge(components[sorted(required)], on="sample_id", how="left", validate="many_to_one", suffixes=("_fold", ""))
    if (len(merged) != len(components) * 5 or merged.seq.isna().any()
            or not merged.amp_fold.eq(merged.amp).all()
            or not merged.combined_component_fold.eq(merged.combined_component).all()):
        raise ValueError("Study-disjoint fold rows do not match the approved molecules and labels.")
    validation = merged[merged.role.eq("validation")].copy()
    if validation.sample_id.duplicated().any() or set(validation.sample_id) != set(components.sample_id):
        raise ValueError("Expected exactly one validation assignment per unique audited molecule.")
    molecules = validation.drop(columns=["role", "amp_fold", "combined_component_fold"]).reset_index(drop=True)
    for fold_id, valid in molecules.groupby("fold"):
        train = molecules[molecules.fold != fold_id]
        assigned = merged[merged.fold.eq(fold_id)]
        if (len(assigned) != len(components) or assigned.sample_id.duplicated().any()
                or set(assigned.sample_id) != set(components.sample_id)):
            raise ValueError(f"Fold {fold_id} does not partition every audited molecule exactly once.")
        if valid.amp.astype(int).nunique() != 2 or train.amp.astype(int).nunique() != 2:
            raise ValueError(f"Fold {fold_id} or its training complement lacks a class.")
        if (set(valid.homology_component) & set(train.homology_component)
                or set(valid.combined_component) & set(train.combined_component)):
            raise ValueError(f"Homology or primary-study component leakage detected for fold {fold_id}.")
        valid_studies = set().union(*(set(value.split("|")) for value in valid.primary_study_ids))
        train_studies = set().union(*(set(value.split("|")) for value in train.primary_study_ids))
        if valid_studies & train_studies:
            raise ValueError(f"Primary-study leakage detected for fold {fold_id}.")
    target_audit_path = ROOT / audit["outputs"]["target_identifier_audit"]
    if target_audit_path.resolve() != CURRENT_TARGET_AUDIT.resolve() or sha256(target_audit_path) != EXPECTED_TARGET_AUDIT_SHA:
        raise ValueError("Frozen target-identifier audit is missing or has changed.")
    target_audit = pd.read_csv(target_audit_path)
    if (not {"record_id", "assay_index", "strain_identifier_status"}.issubset(target_audit.columns)
            or target_audit.empty or target_audit[["record_id", "assay_index", "strain_identifier_status"]].isna().any().any()):
        raise ValueError("Target-identifier audit lacks complete observation-level decisions.")
    provisional = int(target_audit.strain_identifier_status.ne("verified_against_primary_study").sum())
    if provisional:
        raise PrimaryStudyReviewRequired(
            f"Primary-study MIC target verification incomplete for {provisional} assay observations; "
            "protocol-mic-05 is withheld until a new immutable evidence audit and training protocol are approved."
        )
    return protocol, molecules, digest, audit_path, folds_path, study_path, study


def build_models() -> dict:
    return {
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(C=1.0, class_weight="balanced", max_iter=5000, solver="lbfgs", random_state=42),
        ),
        "rbf_svm": make_pipeline(
            StandardScaler(),
            SVC(C=1.0, class_weight="balanced", gamma="scale", kernel="rbf", probability=True, random_state=42),
        ),
        "random_forest": RandomForestClassifier(
            class_weight="balanced", max_depth=None, min_samples_leaf=2, n_estimators=500, n_jobs=1, random_state=42,
        ),
    }


def compute_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    pred = (p >= 0.5).astype(int)
    return {
        "n": int(len(y)), "positive": int(y.sum()), "negative": int(len(y) - y.sum()),
        "AUPRC": float(average_precision_score(y, p)), "AUROC": float(roc_auc_score(y, p)),
        "MCC_at_0_5": float(matthews_corrcoef(y, pred)),
        "balanced_accuracy_at_0_5": float(balanced_accuracy_score(y, pred)),
        "accuracy_at_0_5": float(accuracy_score(y, pred)),
    }


def run(output: Path, protocol_path: Path = DEFAULT_PROTOCOL_PATH) -> dict:
    protocol, folds, protocol_sha, audit_path, folds_path, study_path, study = load_and_validate(protocol_path)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing run directory: {output}")
    output.mkdir(parents=True)
    x = np.vstack([extract_handcrafted_features(seq) for seq in folds.seq.astype(str)])
    y = folds.amp.astype(int).to_numpy()
    if x.shape != (len(folds), 44) or not np.isfinite(x).all():
        raise ValueError(f"Feature matrix invalid: shape={x.shape}")
    predictions, fold_metrics, pooled_metrics = [], [], []
    for model_id, model in build_models().items():
        model_rows = []
        for fold_id in range(5):
            test_mask = folds.fold.astype(int).to_numpy() == fold_id
            train_mask = ~test_mask
            fitted = model
            # Each call gets a fresh estimator so fitted state cannot cross folds.
            from sklearn.base import clone
            fitted = clone(model)
            fitted.fit(x[train_mask], y[train_mask])
            probability = fitted.predict_proba(x[test_mask])[:, 1]
            if not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any():
                raise ValueError(f"Invalid predictions from {model_id}, fold {fold_id}.")
            fold = folds.loc[test_mask]
            metrics = compute_metrics(y[test_mask], probability)
            fold_metrics.append({"model": model_id, "fold": fold_id, **metrics})
            rows = pd.DataFrame({"sample_id": fold.sample_id.to_numpy(), "seq": fold.seq.to_numpy(),
                                 "y_true": y[test_mask], "probability": probability,
                                 "fold": fold_id, "model": model_id})
            predictions.append(rows)
            model_rows.append(rows)
        oof = pd.concat(model_rows, ignore_index=True).sort_values("sample_id")
        if oof.sample_id.nunique() != len(folds) or len(oof) != len(folds):
            raise ValueError(f"OOF coverage is not exactly once per molecule for {model_id}.")
        pooled_metrics.append({"model": model_id, **compute_metrics(oof.y_true.to_numpy(), oof.probability.to_numpy())})
    pred_frame = pd.concat(predictions, ignore_index=True)
    pred_frame.to_csv(output / "oof_predictions.csv", index=False)
    pd.DataFrame(fold_metrics).to_csv(output / "fold_metrics.csv", index=False)
    pd.DataFrame(pooled_metrics).to_csv(output / "pooled_metrics.csv", index=False)
    manifest = {
        "status": "exploratory_baselines_completed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol_id": protocol["protocol_id"], "protocol_sha256": protocol_sha,
        "protocol_path": str(protocol_path.relative_to(ROOT)),
        "audit_protocol_sha256": EXPECTED_AUDIT_PROTOCOL_SHA,
        "audit_manifest_sha256": sha256(audit_path), "fold_assignments_sha256": sha256(folds_path),
        "study_protocol_sha256": EXPECTED_STUDY_PROTOCOL_SHA, "study_manifest_sha256": sha256(study_path),
        "cohort_size": int(len(folds)), "class_counts": {str(k): int(v) for k, v in folds.amp.value_counts().sort_index().items()},
        "fold_sizes": {str(k): int(v) for k, v in folds.fold.value_counts().sort_index().items()},
        "feature_dimensions": int(x.shape[1]), "models": list(build_models()), "tuning": False,
        "formal_study_status": "blocked_unmodified",
        "limitations": ["Exploratory baseline only; not a formal model release or publication-ready result.",
                        *study["warnings"],
                        "Metrics are conditional on this evidence-screened cohort and fixed homology-plus-study components; no inferential CI is reported."],
        "outputs": ["oof_predictions.csv", "fold_metrics.csv", "pooled_metrics.csv", "report.md"],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    pooled = pd.DataFrame(pooled_metrics)
    per_fold = pd.DataFrame(fold_metrics)
    lines = ["# MIC-only 探索性基线训练报告", "", f"生成时间：{manifest['generated_at']}",
             f"协议：`{protocol['protocol_id']}`（SHA-256 `{protocol_sha}`）",
             f"队列：{len(folds)} 条；阳性 {int(y.sum())}、阴性 {int(len(y)-y.sum())}；特征为现有 44 维手工特征。", "",
             "## 汇总 OOF 指标", "", "| 模型 | AUPRC | AUROC | MCC@0.5 | Balanced accuracy@0.5 |", "|---|---:|---:|---:|---:|"]
    for row in pooled.itertuples(index=False):
        lines.append(f"| {row.model} | {row.AUPRC:.4f} | {row.AUROC:.4f} | {row.MCC_at_0_5:.4f} | {row.balanced_accuracy_at_0_5:.4f} |")
    lines += ["", "## 逐折指标", "", "| 模型 | 折 | n | 阳性 | 阴性 | AUPRC | AUROC | MCC@0.5 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in per_fold.itertuples(index=False):
        lines.append(f"| {row.model} | {row.fold} | {row.n} | {row.positive} | {row.negative} | {row.AUPRC:.4f} | {row.AUROC:.4f} | {row.MCC_at_0_5:.4f} |")
    lines += ["", "## 解释边界", "", "这是按冻结的同源加论文隔离分组运行的探索性基线，不是正式研究结果或投稿性能声明。"
              f"最大合并组件 {study['largest_combined_component']}/{len(folds)} 条；验证折规模为 "
              f"{[item['validation_n'] for item in study['folds']]}。汇总 OOF 指标被大折主导，逐折小样本指标波动可能很大。"
              "没有调参、阈值选择、外部验证或置信区间。原双任务正式研究仍保持 blocked。", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New, non-existing versioned output directory")
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL_PATH)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    protocol_path = args.protocol if args.protocol.is_absolute() else ROOT / args.protocol
    manifest = run(output, protocol_path)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
