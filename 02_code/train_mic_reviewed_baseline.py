"""Train and independently validate only a prospectively frozen MIC release."""
from __future__ import annotations

import argparse
import itertools
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from feature_extractor import extract_handcrafted_features
from mic_reviewed_release import (FORMAL, NEW_IDS, OLD_RELEASE_ENTRY,
                                  OLD_RELEASE_PROTOCOL, _check_inputs)
from public_data import measurement_label
from research_evidence_gate import require_primary_release, workspace_path
from research_utils import ROOT, read_json, sha256, utc_now, write_json
from train_mic_three_fold_v2 import build_models
from validate_mic_acid_progress import independent_identity


PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-11.json"
FREEZE = ROOT / "03_experiments/audits/protocol_mic_11_freeze_v1.json"
READINESS = ROOT / "03_experiments/audits/mic_training_readiness_20261003_v19.json"
TRAIN_ENTRY = Path(__file__).resolve()


def _fail(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _environment() -> dict:
    import numpy
    import pandas
    return {"python": platform.python_version(), "numpy": numpy.__version__,
            "pandas": pandas.__version__, "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__}


def _make_models(protocol: dict) -> dict:
    declared = protocol["models"]
    old = build_models()
    models = {"logistic_regression": old["logistic_regression"],
              "random_forest": old["random_forest"],
              "dummy_prior": DummyClassifier(strategy="prior")}
    _fail(set(models) == set(declared), "Unexpected predeclared model inventory")
    for name, estimator in models.items():
        effective = estimator.steps[-1][1] if isinstance(estimator, Pipeline) else estimator
        for key, value in declared[name].items():
            _fail(effective.get_params().get(key) == value, f"Frozen parameter changed: {name}.{key}")
    return models


def _load_and_validate(protocol_path: Path, freeze_path: Path) -> tuple[dict, pd.DataFrame, pd.DataFrame, np.ndarray]:
    _fail(protocol_path.is_file() and freeze_path.is_file(), "Training blocked: frozen protocol and freeze record are required")
    protocol = read_json(protocol_path)
    frozen = read_json(freeze_path)
    _fail(protocol["protocol_id"] == "protocol-mic-11"
          and protocol["status"] == "frozen_local_exploratory_baseline_training",
          "Training blocked: unexpected protocol identity/scope")
    _fail(frozen.get("protocol_file_sha256") == sha256(protocol_path)
          and frozen.get("training_entry_sha256") == sha256(TRAIN_ENTRY)
          and frozen.get("model_training_started") is False,
          "Training blocked: protocol/entry freeze mismatch or training preceded freeze")
    require_primary_release(protocol, freeze_path, TRAIN_ENTRY)
    _fail(datetime.fromisoformat(frozen["frozen_at"]) < datetime.now(timezone.utc),
          "Training blocked: freeze timestamp is not before model fitting")
    _fail(protocol["environment"] == _environment(), "Training blocked: environment differs from immutable protocol")
    ready_path = workspace_path(protocol["readiness_state"])
    ready = read_json(ready_path)
    _fail(sha256(ready_path) == protocol["readiness_state_sha256"]
          and ready["status"] == "ready_for_local_exploratory_training"
          and ready["training_blocked"] is False and ready["training_started"] is False
          and ready["records_released_for_training"] > 22,
          "Training blocked: v17 machine readiness does not admit a new cohort")
    for entry in ("cohort_manifest", "evidence_release_manifest", "independent_partition_validation",
                  "molecules", "observations", "fold_roles"):
        path = workspace_path(protocol[entry])
        _fail(sha256(path) == protocol[f"{entry}_sha256"], f"Training blocked: checksum changed: {entry}")
    release = read_json(protocol["evidence_release_manifest"])
    cohort = read_json(protocol["cohort_manifest"])
    partition = read_json(protocol["independent_partition_validation"])
    _fail(release.get("full_release_review_complete") is True
          and release.get("cohort_manifest_sha256") == protocol["cohort_manifest_sha256"]
          and release.get("molecules_evidence_approved", 0) > 15
          and release.get("observations_evidence_approved", 0) > 22,
          "Training blocked: complete, expanded primary evidence release is required")
    _fail(cohort.get("fold_structure_gate_passed") is True
          and cohort.get("cross_fold_homology_edges") == 0
          and cohort.get("cross_fold_primary_studies") == 0,
          "Training blocked: frozen cohort isolation gate failed")
    _fail(partition.get("status") == "passed" and partition.get("cross_fold_homology_edges") == 0
          and partition.get("cross_fold_primary_studies") == 0,
          "Training blocked: independent whole-cohort partition audit failed")
    molecules = pd.read_csv(workspace_path(protocol["molecules"]), keep_default_na=False)
    assays = pd.read_csv(workspace_path(protocol["observations"]), keep_default_na=False)
    roles = pd.read_csv(workspace_path(protocol["fold_roles"]), keep_default_na=False)
    _fail(molecules.sample_id.is_unique and molecules.seq.is_unique and NEW_IDS.intersection(molecules.sample_id),
          "Training blocked: cohort must contain new, unique reviewed molecules")
    _fail(set(molecules.amp.astype(int)) == {0, 1}, "Training blocked: both evidence-derived classes are required")
    labels = molecules.set_index("sample_id").amp.astype(int).to_dict()
    sequences = molecules.set_index("sample_id").seq.to_dict()
    _fail(all(10 <= len(s) <= 50 and set(s) <= set("ACDEFGHIKLMNPQRSTVWY") for s in sequences.values()),
          "Training blocked: molecule violates the frozen molecular domain")
    evidence_dir = workspace_path(protocol["evidence_release_manifest"]).parent
    molecule_review = pd.read_csv(evidence_dir / "molecule_evidence_review.csv", keep_default_na=False)
    assay_review = pd.read_csv(evidence_dir / "assay_evidence_review.csv", keep_default_na=False)
    source_review = pd.read_csv(evidence_dir / "source_review.csv", keep_default_na=False)
    _fail(set(molecule_review.sample_id) == set(sequences) and molecule_review.sample_id.is_unique
          and set(molecule_review.decision) == {"passed_primary_evidence"},
          "Training blocked: molecule level evidence release is incomplete")
    _fail(len(assays) == len(assay_review) == len(protocol["observation_ids"])
          and set(assay_review.decision) == {"passed_primary_evidence"},
          "Training blocked: observation level evidence release is incomplete")
    _fail(set(assay_review.source_id).issubset(set(source_review.source_id)),
          "Training blocked: primary source review is missing")
    for row in molecule_review.itertuples(index=False):
        _fail(row.sequence == sequences[row.sample_id] and int(row.derived_label) == labels[row.sample_id],
              "Training blocked: reviewed molecule identity/derived label mismatch")
        _fail(row.molecular_form == "linear canonical sequence with free amino and carboxyl termini",
              "Training blocked: unsupported or ambiguous molecular form")
    for row in assay_review.to_dict("records"):
        sample_id = row["sample_id"]
        label = measurement_label({"concentration": row["raw_mic"], "unit": {"name": row["raw_unit"]}},
                                  sequences[sample_id], 32.0, 128.0)
        _fail(label is not None and int(row["derived_label"]) == labels[sample_id] == label,
              "Training blocked: measured value does not independently reproduce its class")
        _fail(row["target"].startswith("Escherichia coli ")
              and row["decision"] == "passed_primary_evidence"
              and row["primary_locations"] and sha256(workspace_path(row["primary_file"])) == row["primary_file_sha256"],
              "Training blocked: target, primary locator or raw source digest is missing")
    _fail(set(roles.sample_id) == set(sequences) and set(roles.fold.astype(int)) == {0, 1, 2},
          "Training blocked: incomplete frozen fold roles")
    _fail(all(set(roles.loc[(roles.fold.astype(int) == f) & roles.role.eq(role), "amp"].astype(int)) == {0, 1}
              for f in (0, 1, 2) for role in ("train", "validation")),
          "Training blocked: every fixed train/validation partition must contain both classes")
    _fail(protocol["validation"] == {"folds": 3, "shuffle": True, "seed": 42,
          "identity_cutoff": 0.40, "identity_mode": "alignment", "features": "fixed_handcrafted_44"},
          "Training blocked: split/features changed from frozen specification")
    _make_models(protocol)
    features_spec = protocol["features_spec"]
    _fail(sha256(workspace_path(features_spec["extractor"])) == features_spec["extractor_sha256"],
          "Training blocked: feature implementation changed")
    values = np.vstack([extract_handcrafted_features(seq) for seq in sequences.values()]).astype(np.float64)
    _fail(values.shape == (len(molecules), 44) and np.isfinite(values).all(), "Training blocked: malformed fixed features")
    # Independently reconstruct every pair, the frozen all-member grouping and fold isolation.
    pair_rows = []
    molrows = list(molecules.itertuples(index=False))
    fold_for = roles[roles.role.eq("validation")].set_index("sample_id").fold.astype(int).to_dict()
    for a, b in itertools.combinations(molrows, 2):
        identity = independent_identity(a.seq, b.seq)
        pair_rows.append((a.sample_id, b.sample_id, identity, fold_for[a.sample_id] == fold_for[b.sample_id]))
    _fail(all(score < 0.40 or same_fold for _, _, score, same_fold in pair_rows),
          "Training blocked: independently recomputed cross-fold homology found")
    return protocol, molecules, roles, values


def freeze(cohort_dir: Path, release_dir: Path, partition_audit: Path,
          protocol_path: Path = PROTOCOL, freeze_path: Path = FREEZE) -> tuple[dict, dict]:
    cohort_dir, release_dir, partition_audit = map(lambda p: Path(p).resolve(),
                                                   (cohort_dir, release_dir, partition_audit))
    protocol_path, freeze_path = Path(protocol_path).resolve(), Path(freeze_path).resolve()
    if protocol_path.exists() or freeze_path.exists():
        raise FileExistsError("Refusing to overwrite a frozen protocol or freeze record")
    _fail(all(p.is_relative_to(ROOT) for p in (cohort_dir, release_dir, partition_audit, protocol_path, freeze_path)),
          "Frozen training materials must remain within this workspace")
    pre = read_json(READINESS)
    _fail(pre["status"] == "ready_for_local_exploratory_training" and pre["training_blocked"] is False
          and pre["records_released_for_training"] > 22,
          "Training blocked: current machine readiness does not admit a new expanded cohort")
    _fail(pre["inputs"].get("02_code/train_mic_reviewed_baseline.py") == sha256(TRAIN_ENTRY),
          "Training blocked: entry point is not yet bound by a pre-training readiness state")
    _fail(cohort_dir.is_relative_to(ROOT / "03_experiments/audits"), "Cohort must be inside the audit workspace")
    evidence = read_json(release_dir / "manifest.json")
    cohort = read_json(cohort_dir / "manifest.json")
    audit = read_json(partition_audit)
    _fail(evidence.get("full_release_review_complete") is True
          and evidence.get("status") == "passed_for_local_exploratory_training_protocol_review",
          "Training blocked: complete primary-source release certificate is missing")
    _fail(cohort.get("fold_structure_gate_passed") is True and audit.get("status") == "passed",
          "Training blocked: independent fixed-fold isolation audit is incomplete")
    molecules = pd.read_csv(cohort_dir / "candidate_molecules.csv", keep_default_na=False)
    observations = pd.read_csv(cohort_dir / "candidate_observations.csv", keep_default_na=False)
    roles = pd.read_csv(cohort_dir / "fold_roles.csv", keep_default_na=False)
    old = read_json(OLD_RELEASE_PROTOCOL)
    old_release_dir = workspace_path(old["evidence_release_manifest"]).parent
    old_ids = set(pd.read_csv(old_release_dir / "molecule_evidence_review.csv", keep_default_na=False).sample_id)
    _fail(NEW_IDS.intersection(set(molecules.sample_id)) and set(molecules.sample_id) - old_ids,
          "No newly admitted molecules; do not publish an expansion training protocol")
    source_dir = evidence
    release_hash = sha256(release_dir / "manifest.json")
    protocol = {
        "protocol_id": "protocol-mic-11", "protocol_version": 1,
        "status": "frozen_local_exploratory_baseline_training", "frozen_date": pd.Timestamp.now(tz="UTC").date().isoformat(),
        "authorization": "User selected a fixed local MIC exploratory baseline after full primary evidence and zero-leakage gates.",
        "scope": "small-sample exploratory E. coli MIC classification only; no external validation, clinical claim, dual-task or publication authorization",
        "research_stage": "follow-up exploration; historical protocol-mic-07 and Gemini runs have known results; not retrospective preregistration",
        "cohort_manifest": (cohort_dir / "manifest.json").relative_to(ROOT).as_posix(),
        "cohort_manifest_sha256": sha256(cohort_dir / "manifest.json"),
        "evidence_release_manifest": (release_dir / "manifest.json").relative_to(ROOT).as_posix(),
        "evidence_release_manifest_sha256": release_hash,
        "independent_partition_validation": partition_audit.relative_to(ROOT).as_posix(),
        "independent_partition_validation_sha256": sha256(partition_audit),
        "molecules": (cohort_dir / "candidate_molecules.csv").relative_to(ROOT).as_posix(),
        "molecules_sha256": sha256(cohort_dir / "candidate_molecules.csv"),
        "observations": (cohort_dir / "candidate_observations.csv").relative_to(ROOT).as_posix(),
        "observations_sha256": sha256(cohort_dir / "candidate_observations.csv"),
        "observation_ids": sorted(observations.record_id.astype(str)),
        "fold_roles": (cohort_dir / "fold_roles.csv").relative_to(ROOT).as_posix(),
        "fold_roles_sha256": sha256(cohort_dir / "fold_roles.csv"),
        "validation": {"folds": 3, "shuffle": True, "seed": 42, "identity_cutoff": 0.40,
                       "identity_mode": "alignment", "features": "fixed_handcrafted_44"},
        "features_spec": {"extractor": "02_code/feature_extractor.py",
                          "extractor_sha256": sha256(ROOT / "02_code/feature_extractor.py"), "dimensions": 44},
        "models": {"logistic_regression": {"C": 1.0, "class_weight": "balanced", "max_iter": 5000,
                                            "solver": "lbfgs", "random_state": 42},
                   "random_forest": {"n_estimators": 500, "min_samples_leaf": 2, "max_depth": None,
                                     "class_weight": "balanced", "n_jobs": 1, "random_state": 42},
                   "dummy_prior": {"strategy": "prior"}},
        "decision_threshold": 0.5,
        "metrics": ["AUPRC", "AUROC", "MCC_at_0_5", "balanced_accuracy_at_0_5", "accuracy_at_0_5"],
        "models_training_entry": TRAIN_ENTRY.relative_to(ROOT).as_posix(),
        "training_entry_sha256": sha256(TRAIN_ENTRY), "environment": _environment(),
        "evidence_review": {"new_candidates_released": int(evidence["molecules_evidence_approved"])-15,
                            "observations_evidence_approved": evidence["observations_evidence_approved"],
                            "status": evidence["status"]},
        "formal_state_path": "04_paper/research_status.json", "formal_state_sha256": sha256(FORMAL),
        "readiness_state": READINESS.relative_to(ROOT).as_posix(), "readiness_state_sha256": sha256(READINESS),
        "records_released_for_training": int(evidence["observations_evidence_approved"]),
        "model_selection": "none; report all three predeclared models; no tuning, calibration, feature selection or deployment fit",
    }
    _make_models(protocol)
    freeze_record = {"protocol_id": protocol["protocol_id"], "frozen_at": utc_now(),
                     "protocol_file_sha256": sha256_text(json.dumps(protocol, ensure_ascii=False, sort_keys=True)),
                     "training_entry_sha256": sha256(TRAIN_ENTRY), "model_training_started": False,
                     "cohort_manifest_sha256": protocol["cohort_manifest_sha256"],
                     "evidence_release_manifest_sha256": release_hash,
                     "partition_audit_sha256": sha256(partition_audit)}
    protocol_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(protocol_path, protocol)
    freeze_record["protocol_file_sha256"] = sha256(protocol_path)
    freeze_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(freeze_path, freeze_record)
    return protocol, freeze_record


def sha256_text(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def train(output: Path, protocol_path: Path = PROTOCOL, freeze_path: Path = FREEZE) -> dict:
    output, protocol_path, freeze_path = map(lambda p: Path(p).resolve(), (output, protocol_path, freeze_path))
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite MIC training run: {output}")
    _fail(output.is_relative_to(ROOT / "03_experiments/runs"), "Training outputs must be under local runs")
    protocol, molecules, roles, features = _load_and_validate(protocol_path, freeze_path)
    output.mkdir(parents=True, exist_ok=False)
    models_dir = output / "fold_models"; models_dir.mkdir()
    labels = molecules.amp.astype(int).to_numpy()
    ids = molecules.sample_id.astype(str).tolist()
    positions = {sample: i for i, sample in enumerate(ids)}
    predictions, fold_metrics = [], []
    for fold in range(3):
        selected = roles[roles.fold.astype(int).eq(fold)]
        train_ix = np.asarray([positions[s] for s in selected.loc[selected.role.eq("train"), "sample_id"]], dtype=int)
        valid_ix = np.asarray([positions[s] for s in selected.loc[selected.role.eq("validation"), "sample_id"]], dtype=int)
        for name, estimator in _make_models(protocol).items():
            estimator.fit(features[train_ix], labels[train_ix])
            _fail(estimator.classes_.tolist() == [0, 1], f"Fitted estimator missing a class: {name}/{fold}")
            scores = estimator.predict_proba(features[valid_ix])[:, 1]
            _fail(np.isfinite(scores).all(), f"Non-finite predictions: {name}/{fold}")
            joblib.dump(estimator, models_dir / f"{name}_fold{fold}.joblib")
            for pos, score in zip(valid_ix, scores):
                predictions.append({"model": name, "sample_id": ids[pos], "fold": fold,
                                    "observed_label": int(labels[pos]), "probability": float(score)})
            fold_metrics.append({"model": name, "fold": fold,
                                 **compute_metrics(labels[valid_ix], scores)})
    predicted = pd.DataFrame(predictions)
    _fail(len(predicted) == 3 * len(molecules) and not predicted.duplicated(["model", "sample_id"]).any(),
          "Incomplete fixed-fold OOF output")
    pooled = [{"model": model, **compute_metrics(part.observed_label.to_numpy(), part.probability.to_numpy())}
              for model, part in predicted.groupby("model", sort=True)]
    predicted.to_csv(output / "oof_predictions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(fold_metrics).to_csv(output / "fold_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(pooled).to_csv(output / "pooled_descriptive_metrics.csv", index=False, encoding="utf-8-sig")
    np.save(output / "fixed_features.npy", features, allow_pickle=False)
    (output / "report.md").write_text(
        "# 小样本 E. coli MIC 三折探索性训练\n\n"
        f"协议 `{protocol['protocol_id']}`；{len(molecules)} 个获完整主来源释放的分子；"
        f"{len(protocol['observation_ids'])} 条测定；3 折；每个模型 {len(molecules)} 条 OOF。\n\n"
        "模型按冻结方案全部报告；没有进行调参、概率校准、特征筛选或最佳模型选择。"
        "历史训练结果已知，本运行属于后续探索。描述性结果不能确立临床用途、广泛泛化或外部验证。\n",
        encoding="utf-8")
    manifest = {"status": "local_exploratory_three_fold_training_completed",
                "generated_at": utc_now(), "protocol_id": protocol["protocol_id"],
                "protocol_sha256": sha256(protocol_path), "freeze_sha256": sha256(freeze_path),
                "cohort_manifest_sha256": protocol["cohort_manifest_sha256"],
                "evidence_release_manifest_sha256": protocol["evidence_release_manifest_sha256"],
                "molecules": len(molecules), "observations": len(protocol["observation_ids"]),
                "folds": 3, "oof_rows": len(predicted), "models": list(protocol["models"]),
                "environment": _environment(), "training_started": True,
                "formal_results_available": False, "publication_ready": False,
                "outputs": {p.relative_to(output).as_posix(): sha256(p)
                            for p in sorted(output.rglob("*")) if p.is_file()}}
    write_json(output / "manifest.json", manifest)
    return manifest


def validate(run_dir: Path, output: Path, protocol_path: Path = PROTOCOL, freeze_path: Path = FREEZE) -> dict:
    run_dir, output, protocol_path, freeze_path = map(lambda p: Path(p).resolve(),
                                                       (run_dir, output, protocol_path, freeze_path))
    if output.exists() or output.with_suffix(".md").exists():
        raise FileExistsError("Refusing to overwrite independent run validation")
    _fail(run_dir.is_relative_to(ROOT / "03_experiments/runs"), "Validation expects a local research run")
    protocol, molecules, roles, features = _load_and_validate(protocol_path, freeze_path)
    manifest = read_json(run_dir / "manifest.json")
    _fail(manifest["protocol_sha256"] == sha256(protocol_path)
          and manifest["freeze_sha256"] == sha256(freeze_path)
          and manifest["status"] == "local_exploratory_three_fold_training_completed"
          and manifest["formal_results_available"] is False and manifest["publication_ready"] is False,
          "Historical run provenance/scope mismatch")
    for relative, digest in manifest["outputs"].items():
        path = (run_dir / relative).resolve()
        _fail(path.is_relative_to(run_dir) and path.is_file() and sha256(path) == digest,
              f"Run artifact digest mismatch: {relative}")
    expected_models = {f"fold_models/{name}_fold{fold}.joblib"
                       for name in protocol["models"] for fold in range(3)}
    _fail(set(manifest["outputs"]) == expected_models | {
        "oof_predictions.csv", "fold_metrics.csv", "pooled_descriptive_metrics.csv",
        "fixed_features.npy", "report.md"}, "Unexpected or missing training artifacts")
    actual_artifacts = {path.relative_to(run_dir).as_posix() for path in run_dir.rglob("*") if path.is_file()
                        and path.name != "manifest.json"}
    _fail(actual_artifacts == set(manifest["outputs"]), "Unmanifested files in validated training run")
    stored_features = np.load(run_dir / "fixed_features.npy", allow_pickle=False)
    _fail(stored_features.shape == features.shape and np.allclose(stored_features, features, rtol=0, atol=1e-12),
          "Stored feature values or order changed")
    actual = pd.read_csv(run_dir / "oof_predictions.csv", keep_default_na=False, float_precision="round_trip")
    labels = molecules.set_index("sample_id").amp.astype(int).to_dict()
    fold_for = roles[roles.role.eq("validation")].set_index("sample_id").fold.astype(int).to_dict()
    expected, fold_metrics = [], []
    from validate_mic_three_fold_run import independent_metrics
    from unittest.mock import patch
    with patch.object(LogisticRegression, "fit", side_effect=AssertionError("No fitting during verification")), \
         patch.object(RandomForestClassifier, "fit", side_effect=AssertionError("No fitting during verification")), \
         patch.object(DummyClassifier, "fit", side_effect=AssertionError("No fitting during verification")), \
         patch.object(StandardScaler, "fit", side_effect=AssertionError("No fitting during verification")), \
         patch.object(Pipeline, "fit", side_effect=AssertionError("No fitting during verification")):
        for fold in range(3):
            selected = roles[roles.fold.astype(int).eq(fold)]
            valid_ids = selected.loc[selected.role.eq("validation"), "sample_id"].tolist()
            positions = {str(row.sample_id): index for index, row in enumerate(molecules.itertuples(index=False))}
            ix = np.asarray([positions[s] for s in valid_ids], dtype=int)
            for name in protocol["models"]:
                model = joblib.load(run_dir / "fold_models" / f"{name}_fold{fold}.joblib")
                expected_model = _make_models(protocol)[name]
                _fail(model.get_params(deep=True) == expected_model.get_params(deep=True),
                      f"Frozen model parameters changed: {name}/{fold}")
                scores = model.predict_proba(features[ix])[:, 1]
                frame = actual[(actual.model == name) & (actual.fold.astype(int) == fold)].set_index("sample_id")
                _fail(set(frame.index) == set(valid_ids), "OOF fold membership mismatch")
                _fail(np.allclose(frame.loc[valid_ids, "probability"].to_numpy(dtype=float), scores,
                                  rtol=0, atol=1e-12), "Independent prediction reconstruction differs")
                _fail(all(int(frame.loc[s, "observed_label"]) == labels[s] and fold_for[s] == fold
                          for s in valid_ids), "OOF label or fold mismatch")
                fold_metrics.append({"model": name, "fold": fold,
                                     **independent_metrics(np.asarray([labels[s] for s in valid_ids]), scores)})
                expected.extend((name, s, fold, labels[s], float(score)) for s, score in zip(valid_ids, scores))
    _fail(len(expected) == len(molecules) * 3 == len(actual)
          and not actual.duplicated(["model", "sample_id"]).any(), "Incomplete or duplicate independent OOF rows")
    pooled = [{"model": model, **independent_metrics(part.observed_label.astype(int).to_numpy(),
                                                      part.probability.astype(float).to_numpy())}
              for model, part in actual.groupby("model", sort=True)]
    for filename, expected_rows, key_cols in (
            ("fold_metrics.csv", fold_metrics, ["model", "fold"]),
            ("pooled_descriptive_metrics.csv", pooled, ["model"])):
        stored = pd.read_csv(run_dir / filename, keep_default_na=False)
        target = pd.DataFrame(expected_rows).sort_values(key_cols).reset_index(drop=True)
        stored = stored.sort_values(key_cols).reset_index(drop=True)
        _fail(len(stored) == len(target)
              and stored[key_cols].to_dict("records") == target[key_cols].to_dict("records"),
              f"Independent {filename} inventory differs")
        metric_cols = [column for column in target.columns if column not in key_cols]
        _fail(set(metric_cols).issubset(stored.columns)
              and np.allclose(stored[metric_cols].to_numpy(dtype=float), target[metric_cols].to_numpy(dtype=float),
                              rtol=0, atol=1e-12, equal_nan=True),
              f"Stored {filename} differs from independent metrics")
    checks = {"status": "historical_exploratory_run_independently_revalidated",
              "generated_at": utc_now(), "run_directory": run_dir.relative_to(ROOT).as_posix(),
              "protocol_id": protocol["protocol_id"], "models_reloaded": len(protocol["models"]) * 3,
              "oof_rows_independently_recomputed": len(expected),
              "fit_calls_during_validation": 0, "model_fitting_performed": False,
              "formal_results_available": False, "publication_ready": False,
              "pooled_descriptive_metrics": pooled,
              "inputs": {p.relative_to(ROOT).as_posix(): sha256(p)
                         for p in (run_dir / "manifest.json", protocol_path, freeze_path, TRAIN_ENTRY)},
              "run_manifest_sha256": sha256(run_dir / "manifest.json")}
    write_json(output, checks)
    output.with_suffix(".md").write_text(
        f"# 独立运行复核\n\n{checks['generated_at']}；重载 {checks['models_reloaded']} 个模型，"
        f"独立复算 {checks['oof_rows_independently_recomputed']} 条 OOF；训练/投稿准入均未改变。\n",
        encoding="utf-8")
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("freeze"); p.add_argument("--cohort", type=Path, required=True)
    p.add_argument("--release", type=Path, required=True); p.add_argument("--partition", type=Path, required=True)
    p = commands.add_parser("train"); p.add_argument("--output", type=Path, required=True)
    p = commands.add_parser("validate"); p.add_argument("--run", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "freeze":
        result = freeze(args.cohort, args.release, args.partition)
        print(json.dumps({"protocol_id": result[0]["protocol_id"], "frozen_at": result[1]["frozen_at"]}, indent=2))
    elif args.command == "train":
        print(json.dumps(train(args.output), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(validate(args.run, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
