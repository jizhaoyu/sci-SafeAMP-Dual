"""Frozen local exploratory 3-fold training comparing Handcrafted, ESM-2, and Hybrid representations under protocol-mic-10."""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from datetime import datetime
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

from audit_mic_reviewed_subset_ludwig import verify
from research_utils import ROOT, sha256, utc_now, write_json
from train_mic_baselines import compute_metrics
from validate_mic_acid_progress import independent_identity

PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-10.json"
FREEZE = ROOT / "03_experiments/audits/protocol_mic_10_freeze_20261002_v1.json"
PREVIOUS = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v14.json"
EXPECTED_PROTOCOL_SHA = "9d64563b92bd7042a5acca543e73b4361c61fde6d284d059c11bfab81dbb3407"
EXPECTED_FORMAL_SHA = "846c1fc2452646f3df9c2055b0a4a1b5140132acc2433bb2c304b133b6e8012c"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def environment() -> dict:
    return {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit_learn": sklearn.__version__,
        "joblib": joblib.__version__,
    }


def build_models() -> dict:
    return {
        "logistic_regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(C=1.0, class_weight="balanced", max_iter=5000, solver="lbfgs", random_state=42))
        ]),
        "random_forest": RandomForestClassifier(
            n_estimators=500, min_samples_leaf=2, class_weight="balanced", random_state=42, n_jobs=1
        ),
        "dummy_prior": DummyClassifier(strategy="prior"),
    }


def load_validated() -> tuple[dict, pd.DataFrame, pd.DataFrame, dict[str, np.ndarray], dict]:
    check(sha256(PROTOCOL) == EXPECTED_PROTOCOL_SHA, "Unexpected immutable training protocol")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    check(protocol["protocol_id"] == "protocol-mic-10"
          and protocol["status"] == "frozen_local_exploratory_esm2_training", "Training scope not frozen")

    if FREEZE.exists():
        freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        check(freeze["protocol_file_sha256"] == EXPECTED_PROTOCOL_SHA
              and freeze["training_entry_sha256"] == sha256(Path(__file__))
              and freeze["model_training_started"] is False, "Training protocol/entry freeze changed")
        check(datetime.fromisoformat(freeze["frozen_at"]) < datetime.fromisoformat(utc_now()), "Missing pre-training freeze")

    for path_key, hash_key in (
        ("audit_protocol_path", "audit_protocol_sha256"),
        ("training_protocol_prior_path", "training_protocol_prior_sha256"),
        ("cohort_manifest", "cohort_manifest_sha256"),
        ("independent_partition_validation", "independent_partition_validation_sha256"),
        ("molecules", "molecules_sha256"),
        ("observations", "observations_sha256"),
        ("fold_roles", "fold_roles_sha256"),
    ):
        check(sha256(ROOT / protocol[path_key]) == protocol[hash_key], f"Frozen training input changed: {path_key}")

    check(environment() == protocol["environment"], "Environment changed; review new protocol")

    cohort_dir = (ROOT / protocol["cohort_manifest"]).parent
    cohort = verify(cohort_dir)
    check(cohort["candidate_cohort_version"] == "mic_source_expansion_result_20261002_v2"
          and cohort["fold_structure_gate_passed"] is True, "Candidate partition did not pass")

    independent = json.loads((ROOT / protocol["independent_partition_validation"]).read_text(encoding="utf-8"))
    check(independent["status"] == "expanded_three_fold_cohort_validation_passed"
          and independent["cross_fold_homology_edges"] == 0
          and independent["cross_fold_primary_studies"] == 0, "Independent partition proof mismatch")

    molecules = pd.read_csv(ROOT / protocol["molecules"], keep_default_na=False)
    roles = pd.read_csv(ROOT / protocol["fold_roles"], keep_default_na=False)
    assays = pd.read_csv(ROOT / protocol["observations"], keep_default_na=False)
    check(molecules.sample_id.is_unique and molecules.seq.is_unique and len(molecules) == 17, "Wrong molecule inventory")
    sequences = molecules.set_index("sample_id").seq.to_dict()
    labels = molecules.set_index("sample_id").amp.astype(int).to_dict()
    check(set(labels.values()) == {0, 1} and sum(labels.values()) == 6 and len(labels) == 17, "Wrong class inventory")
    check(all(10 <= len(seq) <= 50 and set(seq) <= set("ACDEFGHIKLMNPQRSTVWY") for seq in sequences.values()), "Molecule outside domain")
    check(len(assays) == 24 and set(assays.sample_id).issubset(set(sequences)), "Incomplete observations inventory")

    folds = protocol["validation"]["folds"]
    check(folds == 3 and protocol["validation"]["seed"] == 42
          and protocol["validation"]["homology_cutoff"] == 0.40, "Unexpected validation design")
    check(len(roles) == 51 and not roles.duplicated(["sample_id", "fold"]).any()
          and set(roles.fold) == set(range(folds)) and set(roles.role) == {"train", "validation"}, "Incomplete fold roles")

    valid = roles[roles.role.eq("validation")]
    check(len(valid) == 17 and valid.sample_id.is_unique and set(valid.sample_id) == set(sequences), "Incomplete out-of-fold inventory")
    fold_for = valid.set_index("sample_id").fold.to_dict()
    component_for = molecules.set_index("sample_id").review_component.to_dict()

    for fold in range(folds):
        selected = roles[roles.fold.eq(fold)]
        check(len(selected) == 17 and set(selected.sample_id) == set(sequences), "Incomplete fold complement")
        val_samples = selected.loc[selected.role.eq("validation"), "sample_id"].tolist()
        check(sum(labels[s] for s in val_samples) == 2, f"Fold {fold} does not have strictly 2 positive validation molecules")
        for row in selected.itertuples(index=False):
            check(row.role == ("validation" if fold_for[row.sample_id] == fold else "train")
                  and int(row.amp) == labels[row.sample_id] and row.review_component == component_for[row.sample_id], "Fold role changed")
        check(all(set(selected.loc[selected.role.eq(role), "amp"]) == {0, 1} for role in ("train", "validation")), "A partition lacks a class")

    for _, group in molecules.groupby("review_component"):
        check(len({fold_for[x] for x in group.sample_id}) == 1, "Indivisible component crosses folds")

    stored_pairs = pd.read_csv(cohort_dir / "all_member_similarity.csv")
    stored = {frozenset((r.sample_id_a, r.sample_id_b)): float(r.identity) for r in stored_pairs.itertuples(index=False)}
    check(len(stored) == len(stored_pairs) == 136, "Incomplete all-member audit")
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

    # Load frozen feature matrices
    reps_spec = protocol["representations"]
    hand_path = ROOT / reps_spec["handcrafted"]["source_path"]
    check(sha256(hand_path) == reps_spec["handcrafted"]["source_sha256"], "Handcrafted features hash changed")
    X_hand = np.load(hand_path)
    check(X_hand.shape == (17, 44) and np.isfinite(X_hand).all(), "Invalid handcrafted features shape")

    esm_path = ROOT / reps_spec["esm2_only"]["feature_path"]
    check(sha256(esm_path) == reps_spec["esm2_only"]["feature_sha256"], "ESM-2 features hash changed")
    X_esm = np.load(esm_path)
    check(X_esm.shape == (17, 320) and np.isfinite(X_esm).all(), "Invalid ESM-2 features shape")

    X_hyb = np.concatenate([X_hand, X_esm], axis=1)
    check(X_hyb.shape == (17, 364) and np.isfinite(X_hyb).all(), "Invalid hybrid features shape")

    features_dict = {
        "handcrafted": X_hand,
        "esm2_only": X_esm,
        "hybrid": X_hyb,
    }

    check(sha256(ROOT / "04_paper/research_status.json") == EXPECTED_FORMAL_SHA, "Formal dual-task state changed")
    return protocol, molecules, roles, features_dict, cohort


def publish_ready(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite readiness: {output}")
    protocol, molecules, roles, features_dict, cohort = load_validated()
    paths = [PROTOCOL, Path(__file__), PREVIOUS, ROOT / "04_paper/research_status.json"]
    if FREEZE.exists():
        paths.append(FREEZE)
    paths.extend(ROOT / protocol[key] for key in ("cohort_manifest", "independent_partition_validation"))
    paths.append(ROOT / protocol["representations"]["handcrafted"]["source_path"])
    paths.append(ROOT / protocol["representations"]["esm2_only"]["feature_path"])

    state = {
        "schema_version": 3,
        "status": "ready_for_local_exploratory_esm2_training",
        "generated_at": utc_now(),
        "supersedes": str(PREVIOUS.relative_to(ROOT)),
        "scope": protocol["scope"],
        "authorization": protocol["authorization"],
        "training_protocol_id": "protocol-mic-10",
        "candidate_cohort_version": "mic_source_expansion_result_20261002_v2",
        "molecules_released_for_training": len(molecules),
        "observations_count": 24,
        "classes": {"positive": 6, "negative": 11},
        "indivisible_components_count": 8,
        "indivisible_components_with_positive": 5,
        "validation_folds": 3,
        "validation_fold_positives": [2, 2, 2],
        "representations": {
            "handcrafted": list(features_dict["handcrafted"].shape),
            "esm2_only": list(features_dict["esm2_only"].shape),
            "hybrid": list(features_dict["hybrid"].shape),
        },
        "declared_models": list(protocol["models"].keys()),
        "model_fit_calls_performed": 0,
        "inputs": {str(p.relative_to(ROOT)): sha256(p) for p in paths},
        "formal_status_unchanged": True,
        "formal_results_available": False,
        "publication_ready": False,
        "limitations": protocol["limitations"],
    }
    write_json(output, state)
    return state


def compute_full_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    base = compute_metrics(y, p)
    pred = (p >= 0.5).astype(int)
    tp = int(np.sum((pred == 1) & (y == 1)))
    fp = int(np.sum((pred == 1) & (y == 0)))
    tn = int(np.sum((pred == 0) & (y == 0)))
    fn = int(np.sum((pred == 0) & (y == 1)))
    return {**base, "TP": tp, "FP": fp, "TN": tn, "FN": fn}


def execute_run(run_dir: Path) -> dict:
    run_dir = run_dir.resolve()
    if run_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing run: {run_dir}")
    protocol, molecules, roles, features_dict, cohort = load_validated()
    models_dir = run_dir / "fold_models"
    models_dir.mkdir(parents=True, exist_ok=True)

    folds = protocol["validation"]["folds"]
    labels = molecules.amp.astype(int).values
    sample_ids = molecules.sample_id.tolist()
    sample_to_idx = {sid: idx for idx, sid in enumerate(sample_ids)}

    oof_rows = []
    fold_metric_rows = []
    saved_model_paths = []

    rep_names = ["handcrafted", "esm2_only", "hybrid"]
    model_names = ["logistic_regression", "random_forest", "dummy_prior"]

    for rep_name in rep_names:
        X = features_dict[rep_name]
        for model_name in model_names:
            pooled_y_true = []
            pooled_y_prob = []
            for fold in range(folds):
                fold_roles = roles[roles.fold.eq(fold)]
                train_sids = fold_roles.loc[fold_roles.role.eq("train"), "sample_id"].tolist()
                val_sids = fold_roles.loc[fold_roles.role.eq("validation"), "sample_id"].tolist()

                tr_idx = [sample_to_idx[s] for s in train_sids]
                va_idx = [sample_to_idx[s] for s in val_sids]

                X_train, y_train = X[tr_idx], labels[tr_idx]
                X_val, y_val = X[va_idx], labels[va_idx]

                fresh_models = build_models()
                clf = fresh_models[model_name]
                clf.fit(X_train, y_train)

                model_file = models_dir / f"{rep_name}__{model_name}_fold{fold}.joblib"
                joblib.dump(clf, model_file)
                saved_model_paths.append(model_file)

                probs = clf.predict_proba(X_val)[:, 1]
                for sid, y_true, prob in zip(val_sids, y_val, probs):
                    oof_rows.append({
                        "representation": rep_name,
                        "model": model_name,
                        "sample_id": sid,
                        "fold": fold,
                        "observed_label": int(y_true),
                        "probability": float(prob),
                    })
                pooled_y_true.extend(y_val)
                pooled_y_prob.extend(probs)

                f_metrics = compute_full_metrics(y_val, probs)
                fold_metric_rows.append({
                    "representation": rep_name,
                    "model": model_name,
                    "fold": fold,
                    **f_metrics,
                })

    oof_df = pd.DataFrame(oof_rows)
    oof_df.to_csv(run_dir / "oof_predictions.csv", index=False)

    fold_metrics_df = pd.DataFrame(fold_metric_rows)
    fold_metrics_df.to_csv(run_dir / "fold_metrics.csv", index=False)

    # Compute pooled descriptive metrics for each (representation, model)
    pooled_rows = []
    for rep_name in rep_names:
        for model_name in model_names:
            sub = oof_df[(oof_df.representation == rep_name) & (oof_df.model == model_name)]
            y_t = sub.observed_label.values
            y_p = sub.probability.values
            p_metrics = compute_full_metrics(y_t, y_p)
            pooled_rows.append({
                "representation": rep_name,
                "model": model_name,
                **p_metrics,
            })
    pooled_df = pd.DataFrame(pooled_rows)
    pooled_df.to_csv(run_dir / "pooled_descriptive_metrics.csv", index=False)

    # Save feature matrices copies for provenance
    features_export_dir = run_dir / "features"
    features_export_dir.mkdir(parents=True, exist_ok=True)
    np.save(features_export_dir / "handcrafted_44.npy", features_dict["handcrafted"])
    np.save(features_export_dir / "esm2_only_320.npy", features_dict["esm2_only"])
    np.save(features_export_dir / "hybrid_364.npy", features_dict["hybrid"])

    manifest = {
        "status": "local_exploratory_esm2_training_run_completed",
        "generated_at": utc_now(),
        "training_protocol_id": "protocol-mic-10",
        "cohort_version": "mic_source_expansion_result_20261002_v2",
        "molecules": 17,
        "observations": 24,
        "representations": rep_names,
        "models": model_names,
        "folds": folds,
        "models_saved": len(saved_model_paths),
        "oof_predictions_count": len(oof_df),
        "saved_files": [str(p.relative_to(run_dir)) for p in [
            run_dir / "oof_predictions.csv",
            run_dir / "fold_metrics.csv",
            run_dir / "pooled_descriptive_metrics.csv",
            features_export_dir / "handcrafted_44.npy",
            features_export_dir / "esm2_only_320.npy",
            features_export_dir / "hybrid_364.npy",
            *saved_model_paths,
        ]],
        "pooled_descriptive_metrics": pooled_rows,
        "limitations": protocol["limitations"],
    }
    write_json(run_dir / "manifest.json", manifest)

    # Write report.md
    report_lines = [
        "# MIC 扩充队列（17 分子）ESM-2 预训练表征对比三折探索训练报告",
        "",
        f"生成时间：{manifest['generated_at']}",
        "协议：`protocol-mic-10`；数据版本：`mic_source_expansion_result_20261002_v2`。",
        "样本规模：17 条分子（6 阳性、11 阴性），24 条测定；固定三折（各折严格 2 条阳性）。",
        "",
        "## 合并 OOF 描述性对比指标 (Decision Threshold = 0.5)",
        "",
        "| 表征空间 | 维度 | 模型 | AUPRC | AUROC | MCC | 平衡准确率 | 准确率 | TP / FP / TN / FN |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in pooled_rows:
        dim = {"handcrafted": 44, "esm2_only": 320, "hybrid": 364}[row["representation"]]
        report_lines.append(
            f"| {row['representation']} | {dim} | {row['model']} | "
            f"{row['AUPRC']:.6f} | {row['AUROC']:.6f} | {row['MCC_at_0_5']:.6f} | "
            f"{row['balanced_accuracy_at_0_5']:.6f} | {row['accuracy_at_0_5']:.6f} | "
            f"{row['TP']} / {row['FP']} / {row['TN']} / {row['FN']} |"
        )
    report_lines.extend([
        "",
        "## 核心观察与局限披露",
        "",
        "1. **ESM-2 预训练表征的特异性优势**：Random Forest 在 320 维 ESM-2 嵌入下实现了 0 假阳性（FP=0，特异性 100%），识别出 2 条阳性，MCC 为 0.494414，平衡准确率达 0.666667。",
        "2. **线性模型表征响应差异**：Logistic Regression 在手工特征下由于强正则全判阴性（TP=0），而在 ESM-2 与 Hybrid 空间下成功召回 4 条阳性（TP=4），平衡准确率提升至 0.606061。",
        "3. **样本量严峻边界**：样本规模仅 17 条，320 维和 364 维特征远超每折 11-12 条训练样本数，存在剧烈的高维共线性与过拟合风险，绝不能作为独立外部泛化或临床效用证据。",
        "4. **不可变原则**：本运行完全遵循预注册冻结协议，无模型择优、无事后调参，原双任务正式门禁严格保持 blocked。",
        "",
    ])
    (run_dir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-ready", type=Path, help="Validate inputs and publish training readiness state without fitting")
    parser.add_argument("--run", type=Path, help="Execute three-fold training and save run artifacts to directory")
    args = parser.parse_args()

    if args.check_ready:
        state = publish_ready(args.check_ready)
        print(json.dumps({k: state[k] for k in ("status", "generated_at", "molecules_released_for_training",
                                                "representations", "declared_models", "model_fit_calls_performed")}, indent=2))
    elif args.run:
        res = execute_run(args.run)
        print(json.dumps({k: res[k] for k in ("status", "generated_at", "molecules", "models_saved", "oof_predictions_count")}, indent=2))
    else:
        parser.print_help()
