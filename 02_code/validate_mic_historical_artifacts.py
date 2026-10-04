"""Verify historical predictions without fitting or publishing training eligibility."""
import argparse
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from audit_mic_evidence_repair import ARCHIVE, COHORT, verify_original_materials
from research_utils import ROOT, read_json, sha256, utc_now, write_json
from validate_mic_three_fold_run import independent_metrics

RUNS = (
    ("mic_three_fold_20261002_v2", "protocol-mic-09", "02_code/train_mic_three_fold_v3.py"),
    ("mic_three_fold_esm2_20261002_v1", "protocol-mic-10", "02_code/train_mic_esm2_three_fold.py"),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def close(actual, expected, message: str) -> None:
    require(bool(np.allclose(actual, expected, rtol=0, atol=1e-12)), message)


def validate(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite historical validation: {output}")
    archive = verify_original_materials()
    molecules = pd.read_csv(COHORT / "candidate_molecules.csv", keep_default_na=False)
    roles = pd.read_csv(COHORT / "fold_roles.csv", keep_default_na=False)
    ids = molecules.sample_id.tolist()
    positions = {sid: i for i, sid in enumerate(ids)}
    y = molecules.amp.to_numpy(dtype=int)
    run_reviews, bindings = [], {}

    with ExitStack() as stack:
        for cls in (LogisticRegression, RandomForestClassifier, DummyClassifier, Pipeline, StandardScaler):
            stack.enter_context(patch.object(cls, "fit", side_effect=AssertionError("Historical review forbids fit")))
        for run_name, protocol_id, entry in RUNS:
            run = ROOT / "03_experiments/runs" / run_name
            manifest = read_json(run / "manifest.json")
            protocol_path = ROOT / "03_experiments/protocols" / f"{protocol_id}.json"
            protocol = read_json(protocol_path)
            freeze = read_json(ROOT / f"03_experiments/audits/protocol_mic_{protocol_id[-2:]}_freeze_20261002_v1.json")
            require(sha256(protocol_path) == freeze["protocol_file_sha256"], "Historical protocol changed")
            require(archive["archives"][entry]["sha256"] == freeze["training_entry_sha256"], "Historical source archive does not match freeze")
            for path_key, hash_key in (("cohort_manifest", "cohort_manifest_sha256"),
                                       ("molecules", "molecules_sha256"),
                                       ("observations", "observations_sha256"),
                                       ("fold_roles", "fold_roles_sha256")):
                require(sha256(ROOT / protocol[path_key]) == protocol[hash_key], f"Historical input changed: {path_key}")
            for name, expected in manifest.get("outputs", {}).items():
                require(sha256(run / name) == expected, f"Historical output changed: {name}")
            esm = protocol_id == "protocol-mic-10"
            matrices = ({rep: np.load(run / f"features/{rep}_{dim}.npy", allow_pickle=False)
                         for rep, dim in (("handcrafted", 44), ("esm2_only", 320), ("hybrid", 364))}
                        if esm else {"handcrafted": np.load(run / "fixed_features.npy", allow_pickle=False)})
            if esm:
                for rep in ("handcrafted", "esm2_only"):
                    spec = protocol["representations"][rep]
                    key = "source_path" if rep == "handcrafted" else "feature_path"
                    hash_key = "source_sha256" if rep == "handcrafted" else "feature_sha256"
                    require(sha256(ROOT / spec[key]) == spec[hash_key], "Frozen historical feature source changed")
                    close(matrices[rep], np.load(ROOT / spec[key], allow_pickle=False), "Historical feature copy differs")
                close(matrices["hybrid"], np.concatenate([matrices["handcrafted"], matrices["esm2_only"]], axis=1), "Hybrid differs")
            predictions = pd.read_csv(run / "oof_predictions.csv", keep_default_na=False, float_precision="round_trip")
            if not esm:
                predictions["representation"] = "handcrafted"
            require(len(predictions) == (153 if esm else 51), "Incomplete historical prediction coverage")
            require(not predictions.duplicated(["representation", "model", "sample_id"]).any(), "Duplicate historical OOF rows")
            fold_metrics, pooled_metrics, models = [], [], 0
            for rep, X in matrices.items():
                require(X.shape[0] == len(ids) and np.isfinite(X).all(), "Invalid historical features")
                for name in protocol["models"]:
                    for fold in range(3):
                        selected = roles[roles.fold.eq(fold)]
                        train_ids = selected.loc[selected.role.eq("train"), "sample_id"].tolist()
                        val_ids = selected.loc[selected.role.eq("validation"), "sample_id"].tolist()
                        train, val = [positions[s] for s in train_ids], [positions[s] for s in val_ids]
                        prefix = f"{rep}__" if esm else ""
                        model = joblib.load(run / f"fold_models/{prefix}{name}_fold{fold}.joblib")
                        estimator = model.steps[-1][1] if name == "logistic_regression" else model
                        for key, expected in protocol["models"][name].items():
                            if key != "preprocessing":
                                require(estimator.get_params()[key] == expected, "Historical parameter differs")
                        require(model.classes_.tolist() == [0, 1] and model.n_features_in_ == X.shape[1], "Historical model shape differs")
                        if name == "logistic_regression":
                            scaler = model.steps[0][1]
                            close(scaler.mean_, X[train].mean(axis=0, dtype=np.float64), "Scaler mean is not training-only")
                            close(scaler.var_, X[train].var(axis=0, dtype=np.float64), "Scaler variance is not training-only")
                        if name == "dummy_prior":
                            mean = y[train].mean()
                            close(model.class_prior_, [1-mean, mean], "Dummy prior differs")
                        rows = predictions[predictions.representation.eq(rep) & predictions.model.eq(name) & predictions.fold.eq(fold)]
                        require(len(rows) == len(val_ids) and set(rows.sample_id) == set(val_ids), "Historical validation fold differs")
                        rows = rows.set_index("sample_id").loc[val_ids]
                        require(rows.observed_label.tolist() == y[val].tolist(), "Historical observed labels differ")
                        scores = model.predict_proba(X[val])[:, 1]
                        close(scores, rows.probability.to_numpy(), "Historical OOF prediction differs")
                        fold_metrics.append({"representation": rep, "model": name, "fold": fold,
                                             **independent_metrics(y[val], scores)})
                        models += 1
                    rows = predictions[predictions.representation.eq(rep) & predictions.model.eq(name)]
                    require(len(rows) == len(ids) and set(rows.sample_id) == set(ids), "Historical pooled coverage differs")
                    pooled_metrics.append({"representation": rep, "model": name,
                                           **independent_metrics(rows.observed_label.to_numpy(), rows.probability.to_numpy())})
            for filename, calculated, keys in (("fold_metrics.csv", fold_metrics, ["representation", "model", "fold"]),
                                                ("pooled_descriptive_metrics.csv", pooled_metrics, ["representation", "model"])):
                stored = pd.read_csv(run / filename)
                if not esm:
                    stored["representation"] = "handcrafted"
                require(len(stored) == len(calculated) and not stored.duplicated(keys).any(), "Historical metric inventory differs")
                table = stored.set_index(keys)
                for item in calculated:
                    row = table.loc[tuple(item[k] for k in keys)]
                    for key, value in item.items():
                        if key not in keys and key in stored:
                            close(row[key], value, f"Historical metric differs: {key}")
            bindings.update({p.relative_to(ROOT).as_posix(): sha256(p) for p in run.rglob("*") if p.is_file()})
            run_reviews.append({"run_dir": run.relative_to(ROOT).as_posix(), "historical_training_protocol_id": protocol_id,
                                "historical_cohort_version": "mic_source_expansion_result_20261002_v2",
                                "fold_models_reloaded": models, "oof_rows_recomputed": len(predictions),
                                "artifact_status": "passed", "scientific_admission_status": "blocked",
                                "pooled_descriptive_metrics": pooled_metrics})
    verify_original_materials()
    result = {"status": "historical_artifacts_verified_evidence_review_blocked", "generated_at": utc_now(),
              "binding_scope": "post-review file binding; not a retrospective pre-training freeze",
              "model_fitting_performed": False, "evidence_release_performed": False, "runs": run_reviews,
              "all_artifact_sha256": bindings, "inputs": {ARCHIVE.relative_to(ROOT).as_posix(): sha256(ARCHIVE)},
              "script_sha256": sha256(Path(__file__))}
    write_json(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "03_experiments/audits/gemini_repair_20261003_v1/historical_artifacts.json")
    result = validate(parser.parse_args().output)
    print({"status": result["status"], "models_reloaded": sum(r["fold_models_reloaded"] for r in result["runs"]),
           "oof_rows_recomputed": sum(r["oof_rows_recomputed"] for r in result["runs"])})
