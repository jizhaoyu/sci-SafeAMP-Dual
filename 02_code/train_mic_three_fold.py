"""Frozen local MIC exploration; validate all gates before any model fitting."""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier

from audit_mic_reviewed_subset_ludwig import verify
from feature_extractor import extract_handcrafted_features
from public_data import measurement_label
from research_utils import ROOT, sha256, utc_now, write_json
from train_mic_baselines import build_models, compute_metrics
from validate_mic_acid_progress import independent_identity

PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-07.json"
FREEZE = ROOT / "03_experiments/audits/protocol_mic_07_freeze_20261002_v1.json"
PREVIOUS = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v10.json"
EXPECTED_PROTOCOL_SHA = "a07a98c5fd62b46dc1740cd2ec290a50a3db1725844aaded78f08a2dfb1822f3"
EXPECTED_FORMAL_SHA = "846c1fc2452646f3df9c2055b0a4a1b5140132acc2433bb2c304b133b6e8012c"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def environment() -> dict:
    return {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__, "joblib": joblib.__version__}


def declared_models(protocol: dict) -> dict:
    existing = build_models()
    models = {name: existing[name] for name in ("logistic_regression", "random_forest")}
    models["dummy_prior"] = DummyClassifier(strategy="prior")
    check(set(models) == set(protocol["models"]), "Unexpected model inventory")
    for name, model in models.items():
        estimator = model.steps[-1][1] if name == "logistic_regression" else model
        for key, value in protocol["models"][name].items():
            if key != "preprocessing":
                check(estimator.get_params()[key] == value, f"Model parameter changed: {name}.{key}")
    return models


def load_validated() -> tuple[dict, pd.DataFrame, pd.DataFrame, np.ndarray, dict]:
    check(sha256(PROTOCOL) == EXPECTED_PROTOCOL_SHA, "Unexpected immutable training protocol")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    check(protocol["protocol_id"] == "protocol-mic-07"
          and protocol["status"] == "frozen_local_exploratory_baseline_training", "Training scope not frozen")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    check(freeze["protocol_file_sha256"] == EXPECTED_PROTOCOL_SHA
          and freeze["training_entry_sha256"] == sha256(Path(__file__))
          and freeze["model_training_started"] is False, "Training protocol/entry freeze changed")
    check(datetime.fromisoformat(freeze["frozen_at"]) < datetime.fromisoformat(utc_now()), "Missing pre-training freeze")
    for path_key, hash_key in (("audit_protocol_path", "audit_protocol_sha256"),
                               ("cohort_manifest", "cohort_manifest_sha256"),
                               ("evidence_release_manifest", "evidence_release_manifest_sha256"),
                               ("independent_partition_validation", "independent_partition_validation_sha256"),
                               ("molecules", "molecules_sha256"), ("fold_roles", "fold_roles_sha256"),
                               ("baseline_implementation", "baseline_implementation_sha256")):
        check(sha256(ROOT / protocol[path_key]) == protocol[hash_key], f"Frozen training input changed: {path_key}")
    features_spec = protocol["features"]
    check(sha256(ROOT / features_spec["feature_extractor"]) == features_spec["feature_extractor_sha256"], "Feature implementation changed")
    check(environment() == protocol["environment"], "Environment changed; prospectively review a new protocol")
    declared_models(protocol)  # Inspect fixed parameters; no fitting occurs here.
    cohort_dir = (ROOT / protocol["cohort_manifest"]).parent
    release_dir = (ROOT / protocol["evidence_release_manifest"]).parent
    cohort, release = verify(cohort_dir), verify(release_dir)
    check(cohort["script_sha256"] == sha256(ROOT / "02_code/audit_mic_three_fold.py")
          and release["script_sha256"] == sha256(ROOT / "02_code/review_mic_three_fold_evidence.py"), "Audit implementation changed")
    check(cohort["audit_protocol_id"] == protocol["audit_protocol_id"]
          and cohort["protocol_sha256"] == protocol["audit_protocol_sha256"]
          and cohort["fold_structure_gate_passed"] is True, "Candidate partition did not pass")
    check(release["status"] == "passed_for_local_exploratory_training_protocol_review"
          and release["full_release_review_complete"] is True
          and release["candidate_selection_changed"] is False
          and release["cohort_manifest_sha256"] == protocol["cohort_manifest_sha256"]
          and (release["molecules_evidence_approved"], release["observations_evidence_approved"]) == (15, 22), "Primary evidence release failed")
    check(datetime.fromisoformat(release["generated_at"]) < datetime.fromisoformat(freeze["frozen_at"]), "Training froze before evidence review finished")
    independent = json.loads((ROOT / protocol["independent_partition_validation"]).read_text(encoding="utf-8"))
    helper = ROOT / "02_code/validate_mic_acid_progress.py"
    check(independent["inputs"][str(helper.relative_to(ROOT))] == sha256(helper), "Independent identity implementation changed")
    check(independent["inputs"][str((cohort_dir / "manifest.json").relative_to(ROOT))] == protocol["cohort_manifest_sha256"], "Independent partition proof mismatch")
    molecules = pd.read_csv(ROOT / protocol["molecules"], keep_default_na=False)
    roles = pd.read_csv(ROOT / protocol["fold_roles"], keep_default_na=False)
    assays = pd.read_csv(cohort_dir / "candidate_observations.csv", keep_default_na=False)
    check(molecules.sample_id.is_unique and molecules.seq.is_unique and len(molecules) == 15, "Wrong training molecule inventory")
    sequences = molecules.set_index("sample_id").seq.to_dict()
    labels = molecules.set_index("sample_id").amp.astype(int).to_dict()
    check(set(labels.values()) == {0, 1} and sum(labels.values()) == 4, "Wrong class inventory")
    check(all(10 <= len(seq) <= 50 and set(seq) <= set("ACDEFGHIKLMNPQRSTVWY") for seq in sequences.values()), "Molecule outside frozen domain")
    reviewed_molecules = pd.read_csv(release_dir / "molecule_evidence_review.csv", keep_default_na=False)
    reviewed_assays = pd.read_csv(release_dir / "assay_evidence_review.csv", keep_default_na=False)
    check(len(reviewed_molecules) == 15 and reviewed_molecules.sample_id.is_unique
          and set(reviewed_molecules.sample_id) == set(sequences)
          and set(reviewed_molecules.decision) == {"passed_primary_evidence"}, "Incomplete molecule evidence release")
    for row in reviewed_molecules.itertuples(index=False):
        check(row.sequence == sequences[row.sample_id] and int(row.derived_label) == labels[row.sample_id], "Evidence molecule/label mismatch")
    keys = ["sample_id", "record_id", "assay_index", "target", "raw_mic", "raw_unit", "derived_label", "assay_study_ids"]
    check(len(assays) == len(reviewed_assays) == 22
          and assays[keys].to_dict(orient="records") == reviewed_assays[keys].to_dict(orient="records")
          and set(reviewed_assays.decision) == {"passed_primary_evidence"}, "Incomplete raw MIC evidence release")
    for row in assays.itertuples(index=False):
        label = measurement_label({"concentration": row.raw_mic, "unit": {"name": row.raw_unit}}, sequences[row.sample_id], 32, 128)
        check(label is not None and label == labels[row.sample_id] == int(row.derived_label), "Unresolved primary MIC label")
    folds = protocol["validation"]["folds"]
    check(folds == 3 and protocol["validation"]["seed"] == 42
          and protocol["validation"]["homology_cutoff"] == 0.40, "Unexpected validation design")
    check(len(roles) == 45 and not roles.duplicated(["sample_id", "fold"]).any()
          and set(roles.fold) == set(range(folds)) and set(roles.role) == {"train", "validation"}, "Incomplete fold roles")
    valid = roles[roles.role.eq("validation")]
    check(len(valid) == 15 and valid.sample_id.is_unique and set(valid.sample_id) == set(sequences), "Incomplete out-of-fold inventory")
    fold_for = valid.set_index("sample_id").fold.to_dict()
    component_for = molecules.set_index("sample_id").review_component.to_dict()
    for fold in range(folds):
        selected = roles[roles.fold.eq(fold)]
        check(len(selected) == 15 and set(selected.sample_id) == set(sequences), "Incomplete fold complement")
        for row in selected.itertuples(index=False):
            check(row.role == ("validation" if fold_for[row.sample_id] == fold else "train")
                  and int(row.amp) == labels[row.sample_id] and row.review_component == component_for[row.sample_id], "Fold role changed")
        check(all(set(selected.loc[selected.role.eq(role), "amp"]) == {0, 1} for role in ("train", "validation")), "A partition lacks a class")
    for _, group in molecules.groupby("review_component"):
        check(len({fold_for[x] for x in group.sample_id}) == 1, "Indivisible component crosses folds")
    stored_pairs = pd.read_csv(cohort_dir / "all_member_similarity.csv")
    stored = {frozenset((r.sample_id_a, r.sample_id_b)): float(r.identity) for r in stored_pairs.itertuples(index=False)}
    check(len(stored) == len(stored_pairs) == 105, "Incomplete all-member audit")
    for a, b in itertools.combinations(sequences, 2):
        identity = independent_identity(sequences[a], sequences[b])
        check(abs(stored[frozenset((a, b))] - identity) < 1e-12, "Independent identity mismatch")
        check(identity < 0.40 or fold_for[a] == fold_for[b], "Cross-fold homology leakage")
    studies = {r.sample_id: set(r.study_ids.split("|")) for r in molecules.itertuples(index=False)}
    for row in assays.itertuples(index=False):
        studies[row.sample_id].update(row.assay_study_ids.split("|"))
    check(all(ids and "" not in ids for ids in studies.values()), "Unresolved study identity")
    for a, b in itertools.combinations(sequences, 2):
        check(not (studies[a] & studies[b]) or fold_for[a] == fold_for[b], "Cross-fold primary-study leakage")
    features = np.stack([extract_handcrafted_features(seq) for seq in molecules.seq])
    check(features.shape == (15, 44) and np.isfinite(features).all(), "Invalid fixed features")
    check(sha256(ROOT / "04_paper/research_status.json") == EXPECTED_FORMAL_SHA, "Formal dual-task state changed")
    return protocol, molecules, roles, features, cohort


def publish_ready(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite training readiness: {output}")
    protocol, molecules, roles, features, cohort = load_validated()
    paths = [PROTOCOL, FREEZE, Path(__file__), PREVIOUS, ROOT / "04_paper/research_status.json"]
    paths.extend(ROOT / protocol[key] for key in ("cohort_manifest", "evidence_release_manifest", "independent_partition_validation"))
    state = {"schema_version": 3, "status": "ready_for_local_exploratory_training", "generated_at": utc_now(),
             "supersedes": str(PREVIOUS.relative_to(ROOT)), "scope": protocol["scope"],
             "audit_protocol_id": "protocol-mic-06", "audit_protocol_sha256": protocol["audit_protocol_sha256"],
             "training_protocol_id": "protocol-mic-07", "training_protocol_sha256": EXPECTED_PROTOCOL_SHA,
             "candidate_cohort_version": "mic_three_fold_20261002_v1", "candidate_cohort_manifest": protocol["cohort_manifest"],
             "evidence_release_manifest": protocol["evidence_release_manifest"], "candidate_molecules": 15,
             "candidate_observations": 22, "candidate_class_counts": {"0": 11, "1": 4},
             "candidate_all_member_pairs": 105, "candidate_combined_components": 6,
             "candidate_positive_bearing_components": 3, "candidate_negative_bearing_components": 6,
             "gates": {"candidate_structure": {"status": "passed", "folds_required": 3, "seed": 42, "cutoff": 0.40,
                                                "folds": cohort["folds"], "cross_fold_homology_edges": 0, "cross_fold_primary_studies": 0},
                       "primary_evidence_release": {"status": "passed", "full_release_review_complete": True,
                                                    "molecules_approved": 15, "observations_approved": 22,
                                                    "independent_human_review_claimed": False},
                       "final_admitted_cohort": {"status": "passed", "same_as_frozen_three_fold_candidate": True},
                       "training_protocol": {"status": "passed", "protocol_id": "protocol-mic-07"},
                       "fixed_features": {"status": "passed", "shape": list(features.shape)},
                       "training_entry": {"status": "passed", "model_fitting_performed_by_readiness_check": False}},
             "blockers": [], "training_blocked": False, "records_released_for_training": 15, "training_started": False,
             "predeclared_models": list(protocol["models"]), "environment": environment(),
             "training_command": "python 02_code/train_mic_three_fold.py --output 03_experiments/runs/mic_three_fold_my_run",
             "formal_dual_task_status": "blocked", "formal_status_sha256": EXPECTED_FORMAL_SHA,
             "formal_results_available": False, "publication_ready": False, "limitations": protocol["limitations"],
             "script_sha256": sha256(Path(__file__)), "inputs": {str(p.relative_to(ROOT)): sha256(p) for p in paths}}
    write_json(output, state)
    return state


def run(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite training run: {output}")
    protocol, molecules, roles, features, cohort = load_validated()
    output.mkdir(parents=True)
    model_dir = output / "fold_models"
    model_dir.mkdir()
    y = molecules.amp.to_numpy(dtype=int)
    ids = molecules.sample_id.to_list()
    positions = {sample: index for index, sample in enumerate(ids)}
    predictions, fold_metrics = [], []
    for fold in range(3):
        selected = roles[roles.fold.eq(fold)]
        train = np.array([positions[x] for x in selected.loc[selected.role.eq("train"), "sample_id"]])
        validation = np.array([positions[x] for x in selected.loc[selected.role.eq("validation"), "sample_id"]])
        for name, model in declared_models(protocol).items():
            # LR's scaler lives inside the pipeline and sees only this training complement.
            model.fit(features[train], y[train])
            check(model.classes_.tolist() == [0, 1], "Unexpected fitted classes")
            probabilities = model.predict_proba(features[validation])[:, 1]
            check(np.isfinite(probabilities).all(), "Invalid model probability")
            joblib.dump(model, model_dir / f"{name}_fold{fold}.joblib")
            for index, probability in zip(validation, probabilities):
                predictions.append({"model": name, "sample_id": ids[index], "fold": fold,
                                    "observed_label": int(y[index]), "probability": float(probability)})
            fold_metrics.append({"model": name, "fold": fold, **compute_metrics(y[validation], probabilities)})
    predicted = pd.DataFrame(predictions)
    check(len(predicted) == 45 and not predicted.duplicated(["model", "sample_id"]).any(), "Incomplete OOF predictions")
    pooled = [{"model": name, **compute_metrics(frame.observed_label.to_numpy(), frame.probability.to_numpy())}
              for name, frame in predicted.groupby("model", sort=False)]
    predicted.to_csv(output / "oof_predictions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(fold_metrics).to_csv(output / "fold_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(pooled).to_csv(output / "pooled_descriptive_metrics.csv", index=False, encoding="utf-8-sig")
    np.save(output / "fixed_features.npy", features, allow_pickle=False)
    (output / "report.md").write_text("# 小样本 MIC 三折探索训练\n\n"
                                     "三个预先声明的基线完成固定三折训练，15 条样本各有一条 OOF 预测。"
                                     "仅用于方法探索和程序复现；每验证折只有 1–2 条阳性，不能声称广泛泛化或临床价值。"
                                     "原正式双任务仍 blocked，未进行外部验证、模型选择、调参或部署。\n", encoding="utf-8")
    result = {"status": "local_exploratory_three_fold_training_completed", "generated_at": utc_now(),
              "protocol_id": protocol["protocol_id"], "protocol_sha256": EXPECTED_PROTOCOL_SHA,
              "cohort_manifest_sha256": protocol["cohort_manifest_sha256"],
              "evidence_release_manifest_sha256": protocol["evidence_release_manifest_sha256"],
              "molecules": 15, "observations": 22, "folds": cohort["folds"], "oof_rows": 45,
              "models": list(protocol["models"]), "environment": environment(), "training_started": True,
              "formal_results_available": False, "publication_ready": False, "limitations": protocol["limitations"],
              "script_sha256": sha256(Path(__file__)),
              "outputs": {str(p.relative_to(output)): sha256(p) for p in sorted(output.rglob("*")) if p.is_file()}}
    write_json(output / "manifest.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check-ready", action="store_true", help="Verify all gates and generate readiness without fitting")
    args = parser.parse_args()
    result = publish_ready(args.output) if args.check_ready else run(args.output)
    print(json.dumps({k: result[k] for k in ("status", "generated_at", "training_started")}, indent=2))
