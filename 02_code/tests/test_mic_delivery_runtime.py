"""Offline replay regressions using copies of the admitted frozen run."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mic_delivery_runtime import DeliveryRuntime, ENVIRONMENT, MODEL_PARAMS, SCOPE

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "03_experiments/runs/mic_goat_baseline_20261004_v2"
COHORT = ROOT / "03_experiments/audits/mic_goat_followup_release_20261004_v1/cohort"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def anchor(bundle):
    path = bundle / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["files"] = {p.relative_to(bundle).as_posix(): digest(p)
                         for p in sorted(bundle.rglob("*")) if p.is_file() and p != path}
    write_json(path, manifest)
    return digest(path)


def rebind_run(bundle):
    """Refresh packaging hashes to reach semantic checks in copied artifacts."""
    run_path = bundle / "run/manifest.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["outputs"] = {name: digest(bundle / "run" / name) for name in run["outputs"]}
    write_json(run_path, run)
    validation_path = bundle / "validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation["run_manifest_sha256"] = digest(run_path)
    write_json(validation_path, validation)
    return anchor(bundle)


@pytest.fixture
def bundle(tmp_path):
    target = tmp_path / "delivery"
    target.mkdir()
    shutil.copytree(RUN, target / "run")
    shutil.copytree(COHORT, target / "cohort")
    for source, destination in (
        (ROOT / "03_experiments/protocols/protocol-mic-13.json", "protocol.json"),
        (ROOT / "03_experiments/audits/protocol_mic_13_freeze_20261004_v1.json", "freeze.json"),
        (ROOT / "03_experiments/audits/mic_goat_run_validation_20261004_v1.json", "validation.json"),
        (ROOT / "02_code/mic_delivery_runtime.py", "runtime.py"),
    ):
        shutil.copy2(source, target / destination)
    protocol = json.loads((target / "protocol.json").read_text(encoding="utf-8"))
    manifest = {"schema_version": 1, "files": {}, "scope": SCOPE,
                "protocol_id": protocol["protocol_id"], "sample_ids": protocol["sample_ids"],
                "model_names": list(MODEL_PARAMS), "environment": ENVIRONMENT,
                "artifacts": {"protocol": "protocol.json", "freeze": "freeze.json", "validation": "validation.json",
                              "molecules": "cohort/candidate_molecules.csv", "observations": "cohort/candidate_observations.csv",
                              "fold_roles": "cohort/fold_roles.csv", "features": "run/fixed_features.npy",
                              "oof": "run/oof_predictions.csv", "fold_metrics": "run/fold_metrics.csv",
                              "pooled_metrics": "run/pooled_descriptive_metrics.csv", "run_manifest": "run/manifest.json"},
                "models": {name: {str(fold): f"run/fold_models/{name}_fold{fold}.joblib" for fold in range(3)}
                           for name in MODEL_PARAMS}}
    write_json(target / "manifest.json", manifest)
    return target, anchor(target)


def test_verify_and_replay_never_fit(bundle):
    path, trusted = bundle
    with patch.object(Pipeline, "fit", side_effect=AssertionError("fit forbidden")), \
         patch.object(StandardScaler, "fit", side_effect=AssertionError("fit forbidden")), \
         patch.object(LogisticRegression, "fit", side_effect=AssertionError("fit forbidden")), \
         patch.object(RandomForestClassifier, "fit", side_effect=AssertionError("fit forbidden")), \
         patch.object(DummyClassifier, "fit", side_effect=AssertionError("fit forbidden")):
        runtime = DeliveryRuntime(path, trusted)
        result = runtime.verify()
        assert result["status"] == "passed"
        assert result["models_reloaded"] == 9
        assert result["oof_rows_independently_recomputed"] == 51
        assert result["fit_calls_during_validation"] == 0
        assert len(result["fold_metrics"]) == 9
        assert len(result["pooled_descriptive_metrics"]) == 3
        sample = json.loads((path / "manifest.json").read_text())["sample_ids"][0]
        rows = runtime.replay(sample)
        assert len(rows) == 3
        assert {row["sample_id"] for row in rows} == {sample}
        assert len({row["fold"] for row in rows}) == 1
        assert len(runtime.replay(model="random_forest")) == 17
        assert len(runtime.replay(sample, "dummy_prior")) == 1
        assert len(runtime.replay()) == 51


@pytest.mark.parametrize("trusted", [None, "", "not-sha256", "0" * 63])
def test_anchor_is_mandatory(bundle, trusted):
    with pytest.raises(ValueError, match="mandatory"):
        DeliveryRuntime(bundle[0], trusted)


@pytest.mark.parametrize("relative", ["../outside.joblib", "/tmp/outside.joblib", "C:/outside.joblib", "run/../outside.joblib", "run\\outside.joblib"])
def test_paths_rejected_before_model_load(bundle, relative):
    path, _ = bundle
    manifest = json.loads((path / "manifest.json").read_text())
    manifest["files"][relative] = "0" * 64
    write_json(path / "manifest.json", manifest)
    with patch("mic_delivery_runtime.joblib.load") as load:
        with pytest.raises(ValueError, match="path"):
            DeliveryRuntime(path, digest(path / "manifest.json")).verify()
        load.assert_not_called()


def test_bad_anchor_and_artifact_digest_rejected_before_load(bundle):
    path, trusted = bundle
    with patch("mic_delivery_runtime.joblib.load") as load:
        with pytest.raises(ValueError, match="manifest SHA256"):
            DeliveryRuntime(path, "0" * 64).verify()
        model = path / "run/fold_models/dummy_prior_fold0.joblib"
        model.write_bytes(model.read_bytes() + b"tampered")
        with pytest.raises(ValueError, match="artifact SHA256"):
            DeliveryRuntime(path, trusted).verify()
        load.assert_not_called()


def test_environment_rejected_before_load(bundle):
    path, _ = bundle
    manifest = json.loads((path / "manifest.json").read_text())
    manifest["environment"] = {**ENVIRONMENT, "python": "3.12.0"}
    write_json(path / "manifest.json", manifest)
    with patch("mic_delivery_runtime.joblib.load") as load:
        with pytest.raises(ValueError, match="environment"):
            DeliveryRuntime(path, digest(path / "manifest.json")).verify()
        load.assert_not_called()


@pytest.mark.parametrize("name,parameter,value", [("logistic_regression", "C", 2.0),
                                                ("random_forest", "min_samples_leaf", 1),
                                                ("dummy_prior", "strategy", "most_frequent")])
def test_model_parameters_rejected_even_with_refreshed_hashes(bundle, name, parameter, value):
    path, _ = bundle
    model_path = path / f"run/fold_models/{name}_fold0.joblib"
    model = joblib.load(model_path)
    estimator = model.steps[-1][1] if isinstance(model, Pipeline) else model
    estimator.set_params(**{parameter: value})
    joblib.dump(model, model_path)
    with pytest.raises(ValueError, match="parameters"):
        DeliveryRuntime(path, rebind_run(path)).verify()


def test_scaler_scope_rejected_even_with_refreshed_hashes(bundle):
    path, _ = bundle
    model_path = path / "run/fold_models/logistic_regression_fold0.joblib"
    model = joblib.load(model_path)
    model.steps[0][1].mean_[0] += 0.1
    joblib.dump(model, model_path)
    with pytest.raises(ValueError, match="Scaler training mean"):
        DeliveryRuntime(path, rebind_run(path)).verify()


def test_dummy_prior_rejected_even_with_refreshed_hashes(bundle):
    path, _ = bundle
    model_path = path / "run/fold_models/dummy_prior_fold0.joblib"
    model = joblib.load(model_path)
    model.class_prior_ = np.asarray([0.5, 0.5])
    joblib.dump(model, model_path)
    with pytest.raises(ValueError, match="Dummy training prior"):
        DeliveryRuntime(path, rebind_run(path)).verify()


def test_feature_order_rejected(bundle):
    path, _ = bundle
    features_path = path / "run/fixed_features.npy"
    features = np.load(features_path)
    features[:, [0, 1]] = features[:, [1, 0]]
    np.save(features_path, features, allow_pickle=False)
    with pytest.raises(ValueError, match="Scaler training"):
        DeliveryRuntime(path, rebind_run(path)).verify()


def test_sample_order_rejected_before_load(bundle):
    path, _ = bundle
    manifest = json.loads((path / "manifest.json").read_text())
    manifest["sample_ids"] = manifest["sample_ids"][::-1]
    write_json(path / "manifest.json", manifest)
    with patch("mic_delivery_runtime.joblib.load") as load:
        with pytest.raises(ValueError, match="identity/order"):
            DeliveryRuntime(path, digest(path / "manifest.json")).verify()
        load.assert_not_called()


def test_missing_fold_model_rejected_before_load(bundle):
    path, _ = bundle
    manifest = json.loads((path / "manifest.json").read_text())
    del manifest["models"]["random_forest"]["2"]
    write_json(path / "manifest.json", manifest)
    with patch("mic_delivery_runtime.joblib.load") as load:
        with pytest.raises(ValueError, match="three fold models"):
            DeliveryRuntime(path, digest(path / "manifest.json")).verify()
        load.assert_not_called()


def test_class_order_rejected_even_with_refreshed_hashes(bundle):
    path, _ = bundle
    model_path = path / "run/fold_models/dummy_prior_fold0.joblib"
    model = joblib.load(model_path)
    model.classes_ = np.asarray([1, 0])
    joblib.dump(model, model_path)
    with pytest.raises(ValueError, match="class order"):
        DeliveryRuntime(path, rebind_run(path)).verify()


def test_unmanifested_file_rejected_before_load(bundle):
    path, trusted = bundle
    (path / "untracked.txt").write_text("extra", encoding="utf-8")
    with patch("mic_delivery_runtime.joblib.load") as load:
        with pytest.raises(ValueError, match="Unmanifested"):
            DeliveryRuntime(path, trusted).verify()
        load.assert_not_called()


def test_fold_coverage_rejected_before_load(bundle):
    path, _ = bundle
    oof_path = path / "run/oof_predictions.csv"
    rows = pd.read_csv(oof_path)
    rows.iloc[:-1].to_csv(oof_path, index=False)
    trusted = rebind_run(path)
    with patch("mic_delivery_runtime.joblib.load") as load:
        with pytest.raises(ValueError, match="OOF coverage"):
            DeliveryRuntime(path, trusted).verify()
        load.assert_not_called()


@pytest.mark.parametrize("filename,column", [("oof_predictions.csv", "probability"), ("fold_metrics.csv", "AUROC"),
                                            ("pooled_descriptive_metrics.csv", "AUPRC")])
def test_predictions_and_metrics_recomputed(bundle, filename, column):
    path, _ = bundle
    output = path / "run" / filename
    rows = pd.read_csv(output, float_precision="round_trip")
    rows.loc[0, column] += 0.01
    rows.to_csv(output, index=False)
    with pytest.raises(ValueError, match="predictions differ|metrics differ"):
        DeliveryRuntime(path, rebind_run(path)).verify()


def test_unknown_sample_model_and_replay_rehash(bundle):
    path, trusted = bundle
    runtime = DeliveryRuntime(path, trusted)
    with pytest.raises(ValueError, match="Unknown sample"):
        runtime.replay("new-sequence")
    with pytest.raises(ValueError, match="Unknown model"):
        runtime.replay(model="best-model")
    runtime.verify()
    (path / "run/report.md").write_text("modified", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256"):
        runtime.replay()


def test_standalone_runtime_in_moved_bundle(bundle, tmp_path):
    path, trusted = bundle
    moved = tmp_path / "moved-away-from-workspace"
    shutil.copytree(path, moved)
    process = subprocess.run([sys.executable, "-I", str(moved / "runtime.py"), "verify", "--bundle", str(moved),
                              "--manifest-sha256", trusted], cwd=tmp_path, capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result["status"] == "passed" and result["models_reloaded"] == 9
    sample = json.loads((moved / "manifest.json").read_text())["sample_ids"][0]
    process = subprocess.run([sys.executable, "-I", str(moved / "runtime.py"), "replay", "--bundle", str(moved),
                              "--manifest-sha256", trusted, "--sample-id", sample], cwd=tmp_path,
                             capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    assert len(json.loads(process.stdout)) == 3
