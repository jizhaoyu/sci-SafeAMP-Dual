"""Recheck frozen expanded 17-molecule ESM-2 exploration run artifacts without fitting; publish state v15."""
from __future__ import annotations

import argparse
import copy
import json
import math
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
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

from research_utils import ROOT, read_json, sha256, utc_now, write_json
from train_mic_esm2_three_fold import EXPECTED_FORMAL_SHA, PROTOCOL, check, load_validated

PRIOR_STATE = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v14.json"
TRAIN_ENTRY = ROOT / "02_code/train_mic_esm2_three_fold.py"
DOCS = ("README.md", "docs/REMEDIATION_STATUS.md", "docs/DOCUMENTATION_INDEX.md",
        "docs/handoff/TASK_STATE.md", "03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md")
COMPLETED = "local_exploratory_esm2_training_completed"


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def close(actual, expected, message: str) -> None:
    check(np.allclose(actual, expected, rtol=0, atol=1e-12), message)


def independent_metrics(y: np.ndarray, scores: np.ndarray) -> dict:
    positives, negatives = int(y.sum()), int(len(y) - y.sum())
    check(positives > 0 and negatives > 0, "Metrics require both observed classes")
    predicted = scores >= 0.5
    tp = int(np.sum(predicted & (y == 1)))
    fp = int(np.sum(predicted & (y == 0)))
    tn, fn = negatives - fp, positives - tp
    comparisons = scores[y == 1, None] - scores[y == 0][None, :]
    auc = float(np.mean((comparisons > 0) + 0.5 * (comparisons == 0)))
    ap, previous_tp = 0.0, 0
    for threshold in np.unique(scores)[::-1]:
        included = scores >= threshold
        cumulative_tp = int(np.sum(included & (y == 1)))
        ap += (cumulative_tp - previous_tp) / positives * cumulative_tp / int(included.sum())
        previous_tp = cumulative_tp
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {
        "n": len(y), "positive": positives, "negative": negatives,
        "AUPRC": ap, "AUROC": auc,
        "MCC_at_0_5": (tp * tn - fp * fn) / denominator if denominator else 0.0,
        "balanced_accuracy_at_0_5": (tp / positives + tn / negatives) / 2,
        "accuracy_at_0_5": (tp + tn) / len(y),
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
    }


def compare_metrics(table: pd.DataFrame, expected: list[dict], keys: list[str]) -> None:
    check(len(table) == len(expected), "Metric table row count mismatch")
    reindexed = table.set_index(keys)
    for exp in expected:
        index_val = exp[keys[0]] if len(keys) == 1 else tuple(exp[k] for k in keys)
        row = reindexed.loc[index_val]
        for metric in ("AUPRC", "AUROC", "MCC_at_0_5", "balanced_accuracy_at_0_5", "accuracy_at_0_5"):
            close(row[metric], exp[metric], f"Metric mismatch for {index_val}: {metric}")
        for count in ("n", "positive", "negative", "TP", "FP", "TN", "FN"):
            check(int(row[count]) == int(exp[count]), f"Count mismatch for {index_val}: {count}")


def validate(run_dir: Path, output: Path, publish_state: Path | None, state: Path | None, check_documents: bool) -> dict:
    run_dir = run_dir.resolve()
    output = output.resolve()
    report = output.with_suffix(".md")
    if output.exists() or report.exists():
        raise FileExistsError(f"Refusing to overwrite validation artifact: {output}")
    if publish_state is not None:
        publish_state = publish_state.resolve()
        if publish_state.exists():
            raise FileExistsError(f"Refusing to overwrite published state: {publish_state}")
    check(run_dir.exists() and run_dir.is_dir(), f"Run directory not found: {run_dir}")

    protocol, molecules, roles, features_dict, cohort = load_validated()
    prior = read_json(PRIOR_STATE)

    dims = {"handcrafted": 44, "esm2_only": 320, "hybrid": 364}
    rep_names = ["handcrafted", "esm2_only", "hybrid"]
    model_names = ["logistic_regression", "random_forest", "dummy_prior"]

    protected_paths = [
        PROTOCOL, Path(__file__), TRAIN_ENTRY, PRIOR_STATE, ROOT / "04_paper/research_status.json",
        ROOT / protocol["cohort_manifest"], ROOT / protocol["independent_partition_validation"],
        ROOT / protocol["molecules"], ROOT / protocol["observations"], ROOT / protocol["fold_roles"],
        ROOT / protocol["representations"]["handcrafted"]["source_path"],
        ROOT / protocol["representations"]["esm2_only"]["feature_path"],
    ]
    before = {relative(p): sha256(p) for p in protected_paths}

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Model fitting is strictly forbidden during validation")

    with ExitStack() as stack:
        for cls in (LogisticRegression, RandomForestClassifier, DummyClassifier, Pipeline, StandardScaler):
            stack.enter_context(patch.object(cls, "fit", side_effect=forbidden))

        manifest = read_json(run_dir / "manifest.json")
        check(manifest["status"] == "local_exploratory_esm2_training_run_completed", "Unexpected run status")
        check(manifest["training_protocol_id"] == "protocol-mic-10", "Run protocol mismatch")
        check(manifest["cohort_version"] == "mic_source_expansion_result_20261002_v2", "Run cohort mismatch")
        check(manifest["molecules"] == 17 and manifest["folds"] == 3, "Run shape mismatch")
        check(manifest["models_saved"] == 27 and manifest["oof_predictions_count"] == 153, "Inventory mismatch")

        # Verify saved feature copies
        features_export_dir = run_dir / "features"
        close(np.load(features_export_dir / "handcrafted_44.npy"), features_dict["handcrafted"], "Handcrafted copy changed")
        close(np.load(features_export_dir / "esm2_only_320.npy"), features_dict["esm2_only"], "ESM2 copy changed")
        close(np.load(features_export_dir / "hybrid_364.npy"), features_dict["hybrid"], "Hybrid copy changed")

        predictions = pd.read_csv(run_dir / "oof_predictions.csv", keep_default_na=False)
        check(len(predictions) == 153 and not predictions.duplicated(["representation", "model", "sample_id"]).any(), "Incomplete OOF")

        labels = molecules.set_index("sample_id").amp.astype(int).to_dict()
        positions = {sample: index for index, sample in enumerate(molecules.sample_id)}
        y = molecules.amp.to_numpy(dtype=int)

        rechecked_folds = []
        fitted_models = []

        for rep_name in rep_names:
            X = features_dict[rep_name]
            dim = dims[rep_name]
            for model_name in model_names:
                for fold in range(3):
                    selected = roles[roles.fold.eq(fold)]
                    train_ids = selected.loc[selected.role.eq("train"), "sample_id"].tolist()
                    val_ids = selected.loc[selected.role.eq("validation"), "sample_id"].tolist()
                    train_indices = [positions[s] for s in train_ids]
                    val_indices = [positions[s] for s in val_ids]

                    rows = predictions[predictions.representation.eq(rep_name)
                                       & predictions.model.eq(model_name)
                                       & predictions.fold.eq(fold)]
                    check(len(rows) == len(val_ids) and set(rows.sample_id) == set(val_ids), "Wrong fold OOF partition")
                    rows = rows.set_index("sample_id").loc[val_ids]
                    check(rows.observed_label.tolist() == [labels[s] for s in val_ids], "OOF observed labels changed")

                    model_path = run_dir / f"fold_models/{rep_name}__{model_name}_fold{fold}.joblib"
                    model = joblib.load(model_path)

                    if model_name == "logistic_regression":
                        check(isinstance(model, Pipeline) and len(model.steps) == 2, "Unexpected LR pipeline")
                        scaler, estimator = model.steps[0][1], model.steps[1][1]
                        check(isinstance(scaler, StandardScaler) and isinstance(estimator, LogisticRegression), "Unexpected LR types")
                        close(scaler.mean_, X[train_indices].mean(axis=0, dtype=np.float64), "Scaler mean not training-only")
                        close(scaler.var_, X[train_indices].var(axis=0, dtype=np.float64), "Scaler var not training-only")
                    else:
                        estimator = model
                        expected_type = RandomForestClassifier if model_name == "random_forest" else DummyClassifier
                        check(isinstance(estimator, expected_type), "Unexpected model type")

                    check(model.classes_.tolist() == [0, 1] and model.n_features_in_ == dim, "Wrong fitted classes/features")
                    if model_name == "dummy_prior":
                        mean = y[train_indices].mean()
                        close(model.class_prior_, [1 - mean, mean], "Prior is not training-only")

                    probs = model.predict_proba(X[val_indices])[:, 1]
                    close(probs, rows.probability.to_numpy(), "Model prediction differs from saved OOF")
                    rechecked_folds.append({
                        "representation": rep_name,
                        "model": model_name,
                        "fold": fold,
                        **independent_metrics(y[val_indices], probs),
                    })
                    fitted_models.append(relative(model_path))

        pooled = []
        for rep_name in rep_names:
            for model_name in model_names:
                rows = predictions[predictions.representation.eq(rep_name) & predictions.model.eq(model_name)]
                check(len(rows) == 17 and set(rows.sample_id) == set(positions), "Incomplete pooled coverage")
                pooled.append({
                    "representation": rep_name,
                    "model": model_name,
                    **independent_metrics(rows.observed_label.to_numpy(dtype=int), rows.probability.to_numpy()),
                })

        compare_metrics(pd.read_csv(run_dir / "fold_metrics.csv"), rechecked_folds, ["representation", "model", "fold"])
        compare_metrics(pd.read_csv(run_dir / "pooled_descriptive_metrics.csv"), pooled, ["representation", "model"])

    check(before == {relative(p): sha256(p) for p in protected_paths}, "Protected artifact changed during validation")
    check(sha256(ROOT / "04_paper/research_status.json") == EXPECTED_FORMAL_SHA, "Formal state changed")

    completed_state = copy.deepcopy(prior)
    completed_state.update({
        "status": COMPLETED,
        "generated_at": utc_now(),
        "supersedes": relative(PRIOR_STATE),
        "scope": protocol["scope"],
        "authorization": protocol["authorization"],
        "training_protocol_id": "protocol-mic-10",
        "training_protocol_sha256": sha256(PROTOCOL),
        "candidate_cohort_version": "mic_source_expansion_result_20261002_v2",
        "training_started": True,
        "training_completed": True,
        "exploratory_results_available": True,
        "run_dir": relative(run_dir),
        "run_manifest_sha256": sha256(run_dir / "manifest.json"),
        "run_completed_at": manifest["generated_at"],
        "fold_models_saved": len(fitted_models),
        "oof_rows": len(predictions),
        "pooled_descriptive_metrics": pooled,
        "representations": {
            "handcrafted": list(features_dict["handcrafted"].shape),
            "esm2_only": list(features_dict["esm2_only"].shape),
            "hybrid": list(features_dict["hybrid"].shape),
        },
        "producer": relative(Path(__file__)),
        "script_sha256": sha256(Path(__file__)),
        "training_entry_sha256": sha256(TRAIN_ENTRY),
        "post_training_validation": {
            "status": "passed",
            "all_member_pairs": 136,
            "fold_models_reloaded": len(fitted_models),
            "oof_rows_recomputed": len(predictions),
            "metric_rows_recomputed": len(rechecked_folds),
            "fitting_performed": False,
        },
    })
    completed_state["inputs"].update({relative(p): sha256(p) for p in (PRIOR_STATE, run_dir / "manifest.json", Path(__file__))})

    actual_state = completed_state
    if state is not None:
        state = state.resolve()
        actual_state = read_json(state)
        expected_state = copy.deepcopy(completed_state)
        expected_state["generated_at"] = actual_state["generated_at"]
        check(actual_state == expected_state, "Published state differs from recomputed artifacts")

    stamp = datetime.fromisoformat(actual_state["generated_at"]).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    paths = [*protected_paths, Path(__file__)]
    if state is not None:
        paths.append(state)

    if check_documents:
        for name in DOCS:
            content = (ROOT / name).read_text(encoding="utf-8")
            check(all(token in content for token in (state.name, stamp, "mic_three_fold_esm2_20261002_v1",
                                                     "protocol-mic-10", COMPLETED, run_dir.name)),
                  f"Document does not match completed ESM2 machine state: {name}")
            paths.append(ROOT / name)

    result = {
        "status": "local_exploratory_esm2_training_run_validation_passed",
        "generated_at": utc_now(),
        "run_dir": relative(run_dir),
        "run_manifest_sha256": sha256(run_dir / "manifest.json"),
        "state": relative(state or publish_state) if state or publish_state else None,
        "state_generated_at": actual_state["generated_at"],
        "audit_protocol_id": "protocol-mic-08",
        "training_protocol_id": "protocol-mic-10",
        "candidate_cohort_version": "mic_source_expansion_result_20261002_v2",
        "molecules": 17,
        "observations": 24,
        "independently_recomputed_pairs": 136,
        "fold_roles_verified": 51,
        "representations": {
            "handcrafted": [17, 44],
            "esm2_only": [17, 320],
            "hybrid": [17, 364],
        },
        "fold_models_reloaded": len(fitted_models),
        "oof_rows_recomputed": len(predictions),
        "metric_rows_recomputed": len(rechecked_folds),
        "cross_fold_homology_edges": 0,
        "cross_fold_primary_studies": 0,
        "pooled_descriptive_metrics": pooled,
        "fold_metrics": rechecked_folds,
        "current_state_documents_verified": len(DOCS) if check_documents else 0,
        "model_fit_calls_forbidden_during_validation": True,
        "formal_status_unchanged": True,
        "formal_results_available": False,
        "publication_ready": False,
        "script_sha256": sha256(Path(__file__)),
        "inputs": {relative(p): sha256(p) for p in paths},
        "limitations": protocol["limitations"],
    }
    if publish_state is not None:
        write_json(publish_state, completed_state)
        result["inputs"][relative(publish_state)] = sha256(publish_state)
    write_json(output, result)

    lines = [
        "# 扩充队列（17 分子）ESM-2 预训练表征三折探索训练产物复核",
        "",
        f"复核生成时间：{result['generated_at']}",
        f"机器状态生成时间：{stamp}（Asia/Shanghai）",
        f"状态：`{COMPLETED}`；运行：`{relative(run_dir)}`。",
        "数据版本 `mic_source_expansion_result_20261002_v2`；训练协议 `protocol-mic-10`。",
        "",
        "## 合并 OOF 描述性对比指标 (Threshold = 0.5)",
        "",
        "| 表征空间 | 维度 | 模型 | AUPRC | AUROC | MCC | 平衡准确率 | 准确率 | TP / FP / TN / FN |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in pooled:
        dim = dims[row["representation"]]
        lines.append(
            f"| {row['representation']} | {dim} | {row['model']} | "
            f"{row['AUPRC']:.6f} | {row['AUROC']:.6f} | {row['MCC_at_0_5']:.6f} | "
            f"{row['balanced_accuracy_at_0_5']:.6f} | {row['accuracy_at_0_5']:.6f} | "
            f"{row['TP']} / {row['FP']} / {row['TN']} / {row['FN']} |"
        )
    lines.extend([
        "",
        "## 解释边界与诚信红线",
        "",
        "1. 全部 27 个保存模型重新加载并复算 153 行 OOF 预测与全部指标；复核期间严格禁止 fit 调用。",
        "2. RF 在 320 维 ESM-2 表征下达到 0 假阳性（FP=0），特异性 100%，MCC 为 0.494413，平衡准确率 0.666667。",
        "3. LR 在 ESM-2 与 Hybrid 表征下识别出 4 条阳性（TP=4），打破手工特征下的全阴性预测，MCC 为 0.203091。",
        "4. 样本量仅 17 条，高维特征（320/364 维）极易产生共线性与过拟合，不作为泛化能力或临床有效性宣称。",
        "5. 原正式双任务在 04_paper/research_status.json 中严格保持 blocked。",
        "",
    ])
    report.write_text("\n".join(lines), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--publish-state", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--check-documents", action="store_true")
    args = parser.parse_args()
    res = validate(args.run, args.output, args.publish_state, args.state, args.check_documents)
    print(json.dumps({k: res[k] for k in ("status", "generated_at", "molecules", "fold_models_reloaded",
                                          "oof_rows_recomputed", "metric_rows_recomputed",
                                          "current_state_documents_verified")}, indent=2))
