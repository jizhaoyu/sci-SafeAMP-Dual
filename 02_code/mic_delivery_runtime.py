"""Verify a trusted MIC evidence bundle and replay admitted holdout predictions.

This file is copied to the delivery as runtime.py. It is independent of the
research workspace and never trains an estimator or scores new sequences.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import platform
import re
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ENVIRONMENT = {"python": "3.11.9", "numpy": "2.4.4", "pandas": "3.0.2",
               "scikit_learn": "1.8.0", "joblib": "1.5.3"}
MODEL_PARAMS = {
    "logistic_regression": {"C": 1.0, "class_weight": "balanced", "max_iter": 5000,
                            "solver": "lbfgs", "random_state": 42},
    "random_forest": {"n_estimators": 500, "min_samples_leaf": 2, "max_depth": None,
                      "class_weight": "balanced", "n_jobs": 1, "random_state": 42},
    "dummy_prior": {"strategy": "prior"},
}
SCOPE = "admitted_cohort_oof_replay_only"
ARTIFACT_KEYS = {"protocol", "freeze", "validation", "molecules", "observations",
                 "fold_roles", "features", "oof", "fold_metrics", "pooled_metrics", "run_manifest"}


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _environment():
    return {"python": platform.python_version(), "numpy": np.__version__,
            "pandas": pd.__version__, "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__}


def _close(actual, expected, message):
    actual, expected = np.asarray(actual), np.asarray(expected)
    _check(actual.shape == expected.shape and
           np.allclose(actual, expected, rtol=0, atol=1e-12), message)


def _integers(values, message):
    numeric = np.asarray(values, dtype=float)
    _check(np.isfinite(numeric).all() and np.equal(numeric, np.floor(numeric)).all(), message)
    return numeric.astype(int)


def _metrics(y, scores):
    """Calculate all declared metrics without the original training helpers."""
    positives, negatives = int(y.sum()), int(len(y) - y.sum())
    _check(positives > 0 and negatives > 0, "Metrics require both classes")
    predicted = scores >= 0.5
    tp = int(np.sum(predicted & (y == 1)))
    fp = int(np.sum(predicted & (y == 0)))
    tn, fn = negatives - fp, positives - tp
    differences = scores[y == 1, None] - scores[y == 0][None, :]
    auc = float(np.mean((differences > 0) + 0.5 * (differences == 0)))
    ap, previous_tp = 0.0, 0
    for threshold in np.unique(scores)[::-1]:
        included = scores >= threshold
        current_tp = int(np.sum(included & (y == 1)))
        ap += (current_tp - previous_tp) / positives * current_tp / int(included.sum())
        previous_tp = current_tp
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {"n": len(y), "positive": positives, "negative": negatives,
            "AUPRC": ap, "AUROC": auc,
            "MCC_at_0_5": (tp * tn - fp * fn) / denominator if denominator else 0.0,
            "balanced_accuracy_at_0_5": (tp / positives + tn / negatives) / 2,
            "accuracy_at_0_5": (tp + tn) / len(y), "TP": tp, "FP": fp, "TN": tn, "FN": fn}


def _compare_metrics(stored, calculated, keys):
    expected = pd.DataFrame(calculated).sort_values(keys).reset_index(drop=True)
    _check(set(stored.columns) == set(expected.columns), "Metric column inventory differs")
    _check(len(stored) == len(expected) and not stored.duplicated(keys).any(), "Metric coverage differs")
    actual = stored.sort_values(keys).reset_index(drop=True)
    _check(actual[keys].to_dict("records") == expected[keys].to_dict("records"), "Metric keys differ")
    columns = [c for c in expected.columns if c not in keys]
    _close(actual[columns].to_numpy(float), expected[columns].to_numpy(float), "Independent metrics differ")


class DeliveryRuntime:
    """Load only after an independently supplied manifest digest is verified."""

    def __init__(self, bundle, manifest_sha256):
        _check(isinstance(manifest_sha256, str) and re.fullmatch(r"[0-9a-f]{64}", manifest_sha256),
               "A trusted manifest SHA256 is mandatory")
        self.bundle = Path(bundle).resolve()
        self.manifest_sha256 = manifest_sha256

    def _path(self, relative):
        _check(isinstance(relative, str) and relative and "\\" not in relative and ":" not in relative,
               "Unsafe bundle path")
        path = PurePosixPath(relative)
        _check(not path.is_absolute() and all(p not in ("", ".", "..") for p in relative.split("/")),
               "Bundle path escapes or is not canonical")
        target = self.bundle.joinpath(*path.parts)
        _check(target.resolve().is_relative_to(self.bundle), "Bundle path escapes root")
        for parent in (target, *target.parents):
            if parent == self.bundle:
                break
            _check(not parent.is_symlink(), "Bundle symlinks are forbidden")
        _check(target.is_file(), "Bundle artifact is missing: " + relative)
        return target

    def _verify_files(self):
        _check(self.bundle.is_dir(), "Bundle directory is missing")
        manifest_path = self._path("manifest.json")
        _check(_sha256(manifest_path) == self.manifest_sha256, "Trusted manifest SHA256 differs")
        manifest = _read_json(manifest_path)
        _check(manifest.get("schema_version") == 1 and manifest.get("scope") == SCOPE,
               "Unsupported bundle schema or scope")
        files = manifest.get("files")
        _check(isinstance(files, dict) and files and "manifest.json" not in files, "Invalid file inventory")
        for name, digest in files.items():
            _check(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest), "Invalid artifact SHA256")
            _check(_sha256(self._path(name)) == digest, "Bundle artifact SHA256 differs: " + name)
        actual = set()
        for path in self.bundle.rglob("*"):
            _check(not path.is_symlink(), "Bundle symlinks are forbidden")
            if path.is_file():
                actual.add(path.relative_to(self.bundle).as_posix())
        _check(actual == set(files) | {"manifest.json"}, "Unmanifested or missing bundle files")
        artifacts = manifest.get("artifacts", {})
        _check(set(artifacts) == ARTIFACT_KEYS and len(set(artifacts.values())) == len(artifacts),
               "Artifact inventory differs")
        _check(all(path in files for path in artifacts.values()), "Unbound artifact path")
        _check(manifest.get("environment") == ENVIRONMENT == _environment(), "Frozen runtime environment differs")
        _check(manifest.get("protocol_id") == "protocol-mic-13", "Unexpected protocol identity")
        _check(manifest.get("model_names") == list(MODEL_PARAMS), "Model inventory or order differs")
        models = manifest.get("models", {})
        _check(set(models) == set(MODEL_PARAMS), "Expected three models")
        model_paths = []
        for name in MODEL_PARAMS:
            _check(isinstance(models[name], dict) and set(models[name]) == {"0", "1", "2"},
                   "Expected three fold models: " + name)
            for fold in range(3):
                relative = models[name][str(fold)]
                _check(relative in files, "Unbound model path")
                self._path(relative)
                model_paths.append(relative)
        _check(len(set(model_paths)) == 9, "Expected nine unique fold models")
        return manifest

    def _load_inputs(self, manifest):
        paths = {name: self._path(path) for name, path in manifest["artifacts"].items()}
        protocol, freeze, run, validation = (_read_json(paths[name]) for name in
                                            ("protocol", "freeze", "run_manifest", "validation"))
        _check(protocol.get("protocol_id") == freeze.get("protocol_id") == run.get("protocol_id") ==
               validation.get("protocol_id") == manifest["protocol_id"], "Protocol identities differ")
        _check(protocol.get("status") == "frozen_local_exploratory_baseline_training" and
               freeze.get("model_training_started") is False, "Invalid frozen scope")
        _check(protocol.get("environment") == run.get("environment") == manifest["environment"],
               "Protocol/run environment differs")
        _check(protocol.get("models") == MODEL_PARAMS and protocol.get("decision_threshold") == 0.5,
               "Frozen model parameters or threshold differ")
        _check(protocol.get("features_spec", {}).get("dimensions") == 44 and
               protocol.get("validation") == {"folds": 3, "shuffle": True, "seed": 42,
                    "identity_cutoff": 0.4, "identity_mode": "alignment", "features": "fixed_handcrafted_44"},
               "Frozen feature or partition specification differs")
        protocol_sha, freeze_sha = _sha256(paths["protocol"]), _sha256(paths["freeze"])
        _check(freeze.get("protocol_file_sha256") == run.get("protocol_sha256") ==
               validation.get("protocol_sha256") == protocol_sha and
               run.get("freeze_sha256") == validation.get("freeze_sha256") == freeze_sha,
               "Protocol/freeze binding differs")
        _check(freeze.get("training_entry_sha256") == protocol.get("training_entry_sha256") and
               freeze.get("dependency_sha256") == protocol.get("dependency_sha256"), "Frozen dependency binding differs")
        _check(datetime.fromisoformat(freeze["frozen_at"]) < datetime.fromisoformat(run["generated_at"]),
               "Run predates freeze")
        _check(run.get("status") == "local_exploratory_three_fold_training_completed" and
               run.get("training_started") is True and run.get("formal_results_available") is False and
               run.get("publication_ready") is False, "Run research scope differs")
        _check((run.get("molecules"), run.get("observations"), run.get("folds"), run.get("oof_rows")) ==
               (17, 42, 3, 51) and run.get("models") == manifest["model_names"], "Run inventory differs")
        _check(validation.get("status") == "passed" and validation.get("models_reloaded") == 9 and
               validation.get("oof_rows_independently_recomputed") == 51 and
               validation.get("fit_calls_during_validation") == 0 and
               validation.get("scaler_training_range_verified") is True and
               validation.get("formal_results_available") is False and validation.get("publication_ready") is False and
               validation.get("run_manifest_sha256") == _sha256(paths["run_manifest"]), "Validation binding differs")
        run_parent = paths["run_manifest"].parent
        run_files = {p.relative_to(run_parent).as_posix() for p in run_parent.rglob("*")
                     if p.is_file() and p != paths["run_manifest"]}
        expected = {"fixed_features.npy", "fold_metrics.csv", "oof_predictions.csv",
                    "pooled_descriptive_metrics.csv", "report.md"}
        expected |= {f"fold_models/{name}_fold{fold}.joblib" for name in MODEL_PARAMS for fold in range(3)}
        _check(run_files == set(run.get("outputs", {})) == expected, "Run output inventory differs")
        for name, digest in run["outputs"].items():
            path = self._path((run_parent / name).relative_to(self.bundle).as_posix())
            _check(_sha256(path) == digest, "Run artifact binding differs: " + name)
        for key, filename in (("features", "fixed_features.npy"), ("oof", "oof_predictions.csv"),
                              ("fold_metrics", "fold_metrics.csv"), ("pooled_metrics", "pooled_descriptive_metrics.csv")):
            _check(paths[key] == run_parent / filename, "Run artifact location differs")
        for name in MODEL_PARAMS:
            for fold in range(3):
                _check(self._path(manifest["models"][name][str(fold)]) ==
                       run_parent / f"fold_models/{name}_fold{fold}.joblib", "Fold model location differs")
        for key in ("molecules", "observations", "fold_roles"):
            _check(protocol.get(key + "_sha256") == _sha256(paths[key]), "Frozen cohort binding differs: " + key)
        mol, obs, roles, oof = (pd.read_csv(paths[key], keep_default_na=False, float_precision="round_trip")
                                for key in ("molecules", "observations", "fold_roles", "oof"))
        ids = mol.sample_id.tolist()
        _check(len(mol) == 17 and mol.sample_id.is_unique and mol.seq.is_unique and
               ids == manifest.get("sample_ids") == protocol.get("sample_ids"), "Sample identity/order differs")
        y = _integers(mol.amp, "Noninteger molecular labels")
        _check(set(y) == {0, 1} and int(y.sum()) == 6, "Class inventory differs")
        _check(len(obs) == 42 and sorted(obs.record_id.astype(str)) == protocol.get("observation_ids") and
               set(obs.sample_id) == set(ids), "Observation coverage differs")
        obs["derived_label"] = _integers(obs.derived_label, "Noninteger observation labels")
        positions = {sample: i for i, sample in enumerate(ids)}
        for row in obs.itertuples(index=False):
            _check(row.derived_label == y[positions[row.sample_id]] and
                   row.sequence == mol.iloc[positions[row.sample_id]].seq, "Observation identity/label differs")
        roles["fold"] = _integers(roles.fold, "Noninteger folds")
        roles["amp"] = _integers(roles.amp, "Noninteger role labels")
        _check(len(roles) == 51 and not roles.duplicated(["fold", "sample_id"]).any() and
               set(roles.fold) == {0, 1, 2} and set(roles.role) == {"train", "validation"} and
               set(roles.sample_id) == set(ids), "Fold coverage differs")
        expected_roles = []
        splitter = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)
        for fold, (train, valid) in enumerate(splitter.split(np.zeros((17, 1)), y, mol.component)):
            for role, indices in (("train", train), ("validation", valid)):
                _check(set(y[indices]) == {0, 1}, "Partition must contain both classes")
                expected_roles.extend((ids[i], fold, role) for i in indices)
        _check(sorted(expected_roles) == sorted(zip(roles.sample_id, roles.fold, roles.role)),
               "Fold roles do not reproduce the fixed split")
        for row in roles.itertuples(index=False):
            pos = positions[row.sample_id]
            _check(row.amp == y[pos] and row.component == mol.iloc[pos].component, "Role metadata differs")
        features = np.load(paths["features"], allow_pickle=False)
        _check(features.shape == (17, 44) and features.dtype == np.dtype("float64") and
               np.isfinite(features).all(), "Invalid fixed features")
        _check(set(oof.columns) == {"model", "sample_id", "fold", "observed_label", "probability"} and
               len(oof) == 51 and not oof.duplicated(["model", "sample_id"]).any() and
               set(oof.model) == set(MODEL_PARAMS) and set(oof.sample_id) == set(ids), "OOF coverage differs")
        oof["fold"] = _integers(oof.fold, "Noninteger OOF folds")
        oof["observed_label"] = _integers(oof.observed_label, "Noninteger OOF labels")
        _check(np.isfinite(oof.probability).all() and oof.probability.between(0, 1).all(), "Invalid OOF probabilities")
        return paths, mol, roles, features, oof, validation

    def _verify_model(self, model, name, features, labels, train):
        constructors = {"logistic_regression": LogisticRegression, "random_forest": RandomForestClassifier,
                        "dummy_prior": DummyClassifier}
        if name == "logistic_regression":
            _check(type(model) is Pipeline and len(model.steps) == 2 and
                   [name for name, _ in model.steps] == ["standardscaler", "logisticregression"],
                   "Unexpected LR pipeline")
            scaler, estimator = (step for _, step in model.steps)
            _check(type(scaler) is StandardScaler and scaler.get_params(deep=False) ==
                   StandardScaler().get_params(deep=False), "Unexpected scaler parameters")
            _check(model.get_params(deep=False)["memory"] is None and not model.verbose, "Unexpected pipeline parameters")
            _close(scaler.mean_, features[train].mean(axis=0), "Scaler training mean differs")
            _close(scaler.var_, features[train].var(axis=0), "Scaler training variance differs")
            # sklearn treats near-constant features as constant using this bound.
            variance = features[train].var(axis=0)
            mean = features[train].mean(axis=0)
            bound = len(train) * np.finfo(float).eps * variance + (len(train) * mean * np.finfo(float).eps) ** 2
            scale = np.sqrt(variance)
            scale[variance <= bound] = 1.0
            _close(scaler.scale_, scale, "Scaler scale differs")
            _check(np.ndim(scaler.n_samples_seen_) == 0 and int(scaler.n_samples_seen_) == len(train) and
                   scaler.n_features_in_ == 44, "Scaler training range differs")
        else:
            estimator = model
        expected = constructors[name](**MODEL_PARAMS[name])
        _check(type(estimator) is constructors[name] and
               estimator.get_params(deep=False) == expected.get_params(deep=False), "Model parameters differ: " + name)
        _check(estimator.classes_.tolist() == [0, 1] and estimator.n_features_in_ == 44,
               "Model class order or feature dimensions differ")
        if name == "random_forest":
            _check(len(estimator.estimators_) == 500 and estimator.n_outputs_ == 1, "RF fitted inventory differs")
        if name == "dummy_prior":
            _close(estimator.class_prior_, np.bincount(labels[train], minlength=2) / len(train), "Dummy training prior differs")

    def verify(self):
        """Rehash and independently recompute every OOF prediction and metric."""
        manifest = self._verify_files()
        paths, mol, roles, features, oof, validation = self._load_inputs(manifest)
        ids = mol.sample_id.tolist()
        positions = {sample: i for i, sample in enumerate(ids)}
        labels = mol.amp.to_numpy(dtype=int)
        calculated, fold_metrics = [], []
        with ExitStack() as stack:
            for cls in (Pipeline, StandardScaler, LogisticRegression, RandomForestClassifier, DummyClassifier):
                stack.enter_context(patch.object(cls, "fit", side_effect=AssertionError("No fit during offline verification")))
            for fold in range(3):
                part = roles[roles.fold == fold]
                train = np.asarray([positions[s] for s in part.loc[part.role == "train", "sample_id"]])
                valid_ids = part.loc[part.role == "validation", "sample_id"].tolist()
                valid = np.asarray([positions[s] for s in valid_ids])
                for name in MODEL_PARAMS:
                    model = joblib.load(self._path(manifest["models"][name][str(fold)]))
                    self._verify_model(model, name, features, labels, train)
                    probabilities = np.asarray(model.predict_proba(features[valid]), dtype=float)
                    _check(probabilities.shape == (len(valid), 2) and np.isfinite(probabilities).all() and
                           ((probabilities >= 0) & (probabilities <= 1)).all(), "Invalid model probabilities")
                    _close(probabilities.sum(axis=1), np.ones(len(valid)), "Class probabilities do not sum to one")
                    scores = probabilities[:, 1]
                    rows = oof[(oof.model == name) & (oof.fold == fold)].set_index("sample_id")
                    _check(len(rows) == len(valid) and set(rows.index) == set(valid_ids), "OOF fold membership differs")
                    _close(rows.loc[valid_ids, "probability"].to_numpy(float), scores, "OOF predictions differ")
                    _check(rows.loc[valid_ids, "observed_label"].tolist() == labels[valid].tolist(), "OOF labels differ")
                    calculated.extend({"model": name, "sample_id": ids[pos], "fold": fold,
                                       "observed_label": int(labels[pos]), "probability": float(score)}
                                      for pos, score in zip(valid, scores))
                    fold_metrics.append({"model": name, "fold": fold, **_metrics(labels[valid], scores)})
        frame = pd.DataFrame(calculated)
        pooled = [{"model": name, **_metrics(part.observed_label.to_numpy(), part.probability.to_numpy())}
                  for name, part in frame.groupby("model", sort=True)]
        _compare_metrics(pd.read_csv(paths["fold_metrics"], float_precision="round_trip"), fold_metrics, ["model", "fold"])
        _compare_metrics(pd.read_csv(paths["pooled_metrics"], float_precision="round_trip"), pooled, ["model"])
        _compare_metrics(pd.DataFrame(validation["pooled_descriptive_metrics"]), pooled, ["model"])
        # Do not cache trusted state across replay calls: each call rechecks disk.
        self._recomputed = calculated
        return {"status": "passed", "generated_at": datetime.now(timezone.utc).isoformat(),
                "protocol_id": manifest["protocol_id"], "manifest_sha256": self.manifest_sha256,
                "models_reloaded": 9, "oof_rows_independently_recomputed": len(calculated),
                "fit_calls_during_validation": 0, "scaler_training_range_verified": True,
                "fold_metrics": fold_metrics, "pooled_descriptive_metrics": pooled,
                "scope": SCOPE, "formal_results_available": False, "publication_ready": False}

    def replay(self, sample_id=None, model=None):
        """Return recomputed scores from each admitted sample's unique holdout."""
        self.verify()
        _check(sample_id is None or sample_id in {row["sample_id"] for row in self._recomputed},
               "Unknown sample: only admitted cohort OOF replay is supported")
        _check(model is None or model in MODEL_PARAMS, "Unknown model")
        return [dict(row) for row in self._recomputed
                if (sample_id is None or row["sample_id"] == sample_id) and
                   (model is None or row["model"] == model)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("verify", "replay"):
        item = sub.add_parser(command)
        item.add_argument("--bundle", required=True, type=Path)
        item.add_argument("--manifest-sha256", required=True)
        if command == "replay":
            item.add_argument("--sample-id")
            item.add_argument("--model")
    args = parser.parse_args()
    runtime = DeliveryRuntime(args.bundle, args.manifest_sha256)
    result = runtime.verify() if args.command == "verify" else runtime.replay(args.sample_id, args.model)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
