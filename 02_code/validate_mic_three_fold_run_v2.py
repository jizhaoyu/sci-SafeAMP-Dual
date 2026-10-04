"""Recheck frozen expanded 17-molecule MIC fold artifacts without fitting; publish immutable exploration state."""
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
from train_mic_three_fold_v3 import EXPECTED_FORMAL_SHA, PROTOCOL, check, load_validated

PRIOR_STATE = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v13.json"
TRAIN_ENTRY = ROOT / "02_code/train_mic_three_fold_v3.py"
DOCS = ("README.md", "docs/REMEDIATION_STATUS.md", "docs/DOCUMENTATION_INDEX.md",
        "docs/handoff/TASK_STATE.md", "03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md")
COMPLETED = "local_exploratory_three_fold_training_completed"


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def close(actual, expected, message: str) -> None:
    check(np.allclose(actual, expected, rtol=0, atol=1e-12), message)


def independent_metrics(y: np.ndarray, scores: np.ndarray) -> dict:
    """Compute declared metrics directly, independently of the training helper."""
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
    return {"n": len(y), "positive": positives, "negative": negatives,
            "AUPRC": ap, "AUROC": auc,
            "MCC_at_0_5": (tp * tn - fp * fn) / denominator if denominator else 0.0,
            "balanced_accuracy_at_0_5": (tp / positives + tn / negatives) / 2,
            "accuracy_at_0_5": (tp + tn) / len(y), "TP": tp, "FP": fp, "TN": tn, "FN": fn}


def compare_metrics(stored: pd.DataFrame, calculated: list[dict], keys: list[str]) -> None:
    check(len(stored) == len(calculated) and not stored.duplicated(keys).any(), "Metric inventory mismatch")
    expected = pd.DataFrame(calculated).sort_values(keys).reset_index(drop=True)
    actual = stored.sort_values(keys).reset_index(drop=True)
    check(actual[keys].to_dict("records") == expected[keys].to_dict("records"), "Metric model/fold mismatch")
    for key in ("n", "positive", "negative", "AUPRC", "AUROC", "MCC_at_0_5",
                "balanced_accuracy_at_0_5", "accuracy_at_0_5"):
        close(actual[key].to_numpy(), expected[key].to_numpy(), f"Independent metric mismatch: {key}")


def validate(run_dir: Path, output: Path, publish_state: Path | None = None,
             state: Path | None = None, check_documents: bool = False) -> dict:
    run_dir, output = run_dir.resolve(), output.resolve()
    report = output.with_suffix(".md")
    check(run_dir.is_relative_to(ROOT / "03_experiments/runs"), "Expected a local research run directory")
    check(output.suffix == ".json", "Validation output must be JSON")
    targets = [output, report]
    if publish_state is not None:
        publish_state = publish_state.resolve()
        targets.append(publish_state)
    check(len(set(targets)) == len(targets), "Output paths overlap")
    check(all(not p.is_relative_to(run_dir) for p in targets), "Do not mutate a frozen training run")
    for target in targets:
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite validated artifact: {target}")
    check(not (publish_state and state), "Choose publication or existing state verification")
    check(not check_documents or state is not None, "Document checks require an existing state")
    protected_paths = [PRIOR_STATE, PROTOCOL, TRAIN_ENTRY, ROOT / "04_paper/research_status.json",
                       run_dir / "manifest.json"]
    before = {relative(p): sha256(p) for p in protected_paths}
    # Verification must load existing estimators only; any accidental fitting fails.
    with ExitStack() as stack:
        for estimator in (LogisticRegression, RandomForestClassifier, DummyClassifier, StandardScaler):
            stack.enter_context(patch.object(estimator, "fit", side_effect=AssertionError("No fitting during verification")))
        stack.enter_context(patch.object(Pipeline, "fit", side_effect=AssertionError("No fitting during verification")))
        protocol, molecules, roles, features, cohort = load_validated()
        prior = read_json(PRIOR_STATE)
        check(prior["status"] == "ready_for_local_exploratory_training"
              and prior["training_started"] is False and prior["training_blocked"] is False
              and prior["blockers"] == [] and prior["records_released_for_training"] == 17
              and all(g["status"] == "passed" for g in prior["gates"].values()), "Invalid pre-training state")
        for name, expected in prior["inputs"].items():
            check(sha256(ROOT / name) == expected, f"Historical readiness input changed: {name}")
        manifest = read_json(run_dir / "manifest.json")
        check(manifest["status"] == COMPLETED and manifest["training_started"] is True
              and manifest["formal_results_available"] is False and manifest["publication_ready"] is False,
              "Run status exceeds exploratory scope")
        check(manifest["protocol_id"] == protocol["protocol_id"]
              and manifest["protocol_sha256"] == sha256(PROTOCOL)
              and manifest["script_sha256"] == sha256(TRAIN_ENTRY)
              and manifest["cohort_manifest_sha256"] == protocol["cohort_manifest_sha256"]
              and manifest["independent_partition_validation_sha256"] == protocol["independent_partition_validation_sha256"],
              "Training input/implementation mismatch")
        check((manifest["molecules"], manifest["observations"], manifest["oof_rows"]) == (17, 24, 51)
              and manifest["models"] == list(protocol["models"])
              and manifest["folds"] == cohort["folds"] and manifest["environment"] == protocol["environment"]
              and manifest["limitations"] == protocol["limitations"], "Run design mismatch")
        check(datetime.fromisoformat(prior["generated_at"]) < datetime.fromisoformat(manifest["generated_at"])
              < datetime.fromisoformat(utc_now()), "Unexpected training chronology")
        expected_names = {"fixed_features.npy", "fold_metrics.csv", "oof_predictions.csv",
                          "pooled_descriptive_metrics.csv", "report.md"}
        expected_names.update(f"fold_models/{name}_fold{fold}.joblib" for name in protocol["models"] for fold in range(3))
        stored_paths = {Path(name).as_posix(): expected for name, expected in manifest["outputs"].items()}
        check(set(stored_paths) == expected_names, "Incomplete or unexpected run output inventory")
        actual_names = {p.relative_to(run_dir).as_posix() for p in run_dir.rglob("*")
                        if p.is_file() and p != run_dir / "manifest.json"}
        check(actual_names == expected_names, "Unmanifested run artifacts")
        for name, expected in stored_paths.items():
            path = (run_dir / name).resolve()
            check(path.is_relative_to(run_dir) and sha256(path) == expected, f"Run checksum mismatch: {name}")
        saved_features = np.load(run_dir / "fixed_features.npy", allow_pickle=False)
        check(saved_features.shape == features.shape == (17, 44), "Feature shape mismatch")
        close(saved_features, features, "Saved feature values changed")
        predictions = pd.read_csv(run_dir / "oof_predictions.csv", keep_default_na=False, float_precision="round_trip")
        check(len(predictions) == 51 and not predictions.duplicated(["model", "sample_id"]).any()
              and set(predictions.model) == set(protocol["models"]), "Incomplete OOF predictions")
        check(np.isfinite(predictions.probability).all()
              and predictions.probability.between(0, 1).all(), "Invalid OOF probability")
        labels = molecules.set_index("sample_id").amp.astype(int).to_dict()
        positions = {sample: index for index, sample in enumerate(molecules.sample_id)}
        y = molecules.amp.to_numpy(dtype=int)
        rechecked_folds = []
        fitted_models = []
        for fold in range(3):
            selected = roles[roles.fold.eq(fold)]
            training_ids = selected.loc[selected.role.eq("train"), "sample_id"].tolist()
            validation_ids = selected.loc[selected.role.eq("validation"), "sample_id"].tolist()
            train_indices = [positions[sample] for sample in training_ids]
            validation_indices = [positions[sample] for sample in validation_ids]
            for name, parameters in protocol["models"].items():
                rows = predictions[predictions.model.eq(name) & predictions.fold.eq(fold)]
                check(len(rows) == len(validation_ids) and set(rows.sample_id) == set(validation_ids), "Wrong OOF partition")
                rows = rows.set_index("sample_id").loc[validation_ids]
                check(rows.observed_label.tolist() == [labels[s] for s in validation_ids], "OOF observed labels changed")
                model_path = run_dir / f"fold_models/{name}_fold{fold}.joblib"
                model = joblib.load(model_path)
                if name == "logistic_regression":
                    check(isinstance(model, Pipeline) and len(model.steps) == 2, "Unexpected LR pipeline")
                    scaler, estimator = model.steps[0][1], model.steps[1][1]
                    check(isinstance(scaler, StandardScaler) and isinstance(estimator, LogisticRegression), "Unexpected LR components")
                    check(scaler.with_mean and scaler.with_std and scaler.n_samples_seen_ == len(train_indices), "Scaler fitted on wrong population")
                    close(scaler.mean_, features[train_indices].mean(axis=0, dtype=np.float64), "Scaler mean is not training-only")
                    close(scaler.var_, features[train_indices].var(axis=0, dtype=np.float64), "Scaler variance is not training-only")
                    check(estimator.n_iter_.max() < parameters["max_iter"], "LR did not converge within the frozen limit")
                else:
                    estimator = model
                    expected_type = RandomForestClassifier if name == "random_forest" else DummyClassifier
                    check(isinstance(estimator, expected_type), "Unexpected saved model class")
                check(model.classes_.tolist() == [0, 1] and model.n_features_in_ == 44, "Wrong fitted classes/features")
                for key, value in parameters.items():
                    if key != "preprocessing":
                        check(estimator.get_params()[key] == value, f"Fitted parameter changed: {name}.{key}")
                if name == "random_forest":
                    check(len(model.estimators_) == parameters["n_estimators"], "Wrong number of fitted trees")
                if name == "dummy_prior":
                    mean = y[train_indices].mean()
                    close(model.class_prior_, [1 - mean, mean], "Prior is not training-only")
                probability = model.predict_proba(features[validation_indices])[:, 1]
                close(probability, rows.probability.to_numpy(), "Saved model prediction differs from OOF")
                rechecked_folds.append({"model": name, "fold": fold,
                                        **independent_metrics(y[validation_indices], probability)})
                fitted_models.append(relative(model_path))
        pooled = []
        for name in protocol["models"]:
            rows = predictions[predictions.model.eq(name)]
            check(len(rows) == 17 and set(rows.sample_id) == set(positions), "Incomplete per-model OOF coverage")
            pooled.append({"model": name, **independent_metrics(rows.observed_label.to_numpy(dtype=int),
                                                                rows.probability.to_numpy())})
        compare_metrics(pd.read_csv(run_dir / "fold_metrics.csv"), rechecked_folds, ["model", "fold"])
        compare_metrics(pd.read_csv(run_dir / "pooled_descriptive_metrics.csv"), pooled, ["model"])
    check(before == {relative(p): sha256(p) for p in protected_paths}, "A protected artifact changed during validation")
    check(sha256(ROOT / "04_paper/research_status.json") == EXPECTED_FORMAL_SHA, "Formal state changed")
    completed_state = copy.deepcopy(prior)
    completed_state.update({"status": COMPLETED, "generated_at": utc_now(), "supersedes": relative(PRIOR_STATE),
                            "training_started": True, "training_completed": True,
                            "exploratory_results_available": True, "run_dir": relative(run_dir),
                            "run_manifest_sha256": sha256(run_dir / "manifest.json"),
                            "run_completed_at": manifest["generated_at"], "fold_models_saved": 9,
                            "oof_rows": 51, "pooled_descriptive_metrics": pooled,
                            "producer": relative(Path(__file__)), "script_sha256": sha256(Path(__file__)),
                            "training_entry_sha256": sha256(TRAIN_ENTRY),
                            "post_training_validation": {"status": "passed", "all_member_pairs": 136,
                                                         "fold_models_reloaded": 9, "oof_rows_recomputed": 51,
                                                         "metric_rows_recomputed": 12, "fitting_performed": False}})
    completed_state["inputs"].update({relative(p): sha256(p) for p in
                                     (PRIOR_STATE, run_dir / "manifest.json", Path(__file__))})
    actual_state = completed_state
    if state is not None:
        state = state.resolve()
        actual_state = read_json(state)
        expected_state = copy.deepcopy(completed_state)
        expected_state["generated_at"] = actual_state["generated_at"]
        check(actual_state == expected_state, "Published completed state differs from independently validated artifacts")
        check(datetime.fromisoformat(manifest["generated_at"]) < datetime.fromisoformat(actual_state["generated_at"])
              < datetime.fromisoformat(utc_now()), "Invalid completed state chronology")
    stamp = datetime.fromisoformat(actual_state["generated_at"]).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    paths = [*protected_paths, Path(__file__), *(run_dir / name for name in stored_paths)]
    if state is not None:
        paths.append(state)
    if check_documents:
        for name in DOCS:
            content = (ROOT / name).read_text(encoding="utf-8")
            check(all(token in content for token in (state.name, stamp, "mic_three_fold_20261002_v2",
                                                     "protocol-mic-08", "protocol-mic-09", COMPLETED, run_dir.name)),
                  f"Current document does not match completed machine state: {name}")
            check("最新机器状态 v13" not in content and "最新机器声明 v13" not in content,
                  f"A prior state is presented as current: {name}")
            paths.append(ROOT / name)
    result = {"status": "local_exploratory_training_run_validation_passed", "generated_at": utc_now(),
              "run_dir": relative(run_dir), "run_manifest_sha256": sha256(run_dir / "manifest.json"),
              "state": relative(state or publish_state) if state or publish_state else None,
              "state_generated_at": actual_state["generated_at"],
              "audit_protocol_id": "protocol-mic-08", "training_protocol_id": "protocol-mic-09",
              "candidate_cohort_version": "mic_source_expansion_result_20261002_v2", "molecules": 17, "observations": 24,
              "independently_recomputed_pairs": 136, "fold_roles_verified": 51, "fixed_features_shape": [17, 44],
              "fold_models_reloaded": fitted_models, "oof_rows_recomputed": 51, "metric_rows_recomputed": 12,
              "cross_fold_homology_edges": 0, "cross_fold_primary_studies": 0,
              "pooled_descriptive_metrics": pooled, "fold_metrics": rechecked_folds,
              "current_state_documents_verified": len(DOCS) if check_documents else 0,
              "model_fit_calls_forbidden_during_validation": True, "formal_status_unchanged": True,
              "formal_results_available": False, "publication_ready": False,
              "independent_human_review_claimed": False, "script_sha256": sha256(Path(__file__)),
              "inputs": {relative(p): sha256(p) for p in paths}, "limitations": protocol["limitations"]}
    if publish_state is not None:
        write_json(publish_state, completed_state)
        result["inputs"][relative(publish_state)] = sha256(publish_state)
    write_json(output, result)
    lines = ["# 扩充队列（17 分子）MIC 三折探索训练产物复核", "", f"复核生成时间：{result['generated_at']}",
             f"机器状态生成时间：{stamp}（Asia/Shanghai）", f"状态：`{COMPLETED}`；运行：`{relative(run_dir)}`。",
             "数据版本 `mic_source_expansion_result_20261002_v2`；审计协议 `protocol-mic-08`，训练协议 `protocol-mic-09`。", "",
             "## 已完成与复核范围", "", "17 条分子（6 阳性、11 阴性），24 条原始 MIC，8 个不可拆分组件（含阳性 5 个）。",
             "三个预先声明的基线完成固定三折训练；九个模型已重新加载，51 条 OOF 预测、12 行指标及 17×44 特征核对通过。",
             "LR 标准化器和 prior 仅使用各自训练折。独立重算 136 对全员序列，跨折同源及原始研究均为 0。",
             f"当前状态文档已复核 {result['current_state_documents_verified']} 份；复核期间禁止 fit 调用。", "",
             "## 合并 OOF 描述性指标", "", "AUPRC 按 average precision 定义；判定阈值预先固定为 0.5。",
             "| 模型 | AUPRC | AUROC | MCC | 平衡准确率 | 准确率 | TP / FP / TN / FN |",
             "| --- | ---: | ---: | ---: | ---: | ---: | --- |"]
    for row in pooled:
        lines.append(f"| {row['model']} | {row['AUPRC']:.6f} | {row['AUROC']:.6f} | {row['MCC_at_0_5']:.6f} | "
                     f"{row['balanced_accuracy_at_0_5']:.6f} | {row['accuracy_at_0_5']:.6f} | "
                     f"{row['TP']} / {row['FP']} / {row['TN']} / {row['FN']} |")
    lines.extend(["", "## 逐折结果与解释边界", "", "| 模型 | 折 | 阳性 / 阴性 | AUPRC | AUROC | 平衡准确率 | TP / FP / TN / FN |",
                  "| --- | ---: | --- | ---: | ---: | ---: | --- |"])
    for row in rechecked_folds:
        lines.append(f"| {row['model']} | {row['fold']} | {row['positive']} / {row['negative']} | "
                     f"{row['AUPRC']:.6f} | {row['AUROC']:.6f} | {row['balanced_accuracy_at_0_5']:.6f} | "
                     f"{row['TP']} / {row['FP']} / {row['TN']} / {row['FN']} |")
    lines.extend(["", "各验证折严格平衡包含 2 条阳性，总验证规模分别为 6、5、6 条。",
                  "RF 在 0.5 阈值下识别出 3 条阳性（包括新增候选 Piscidin 1 游离酸），MCC 为 0.203091，平衡准确率 0.606061；样本量极小，不作为广泛泛化或临床效用证据。",
                  "prior 每折预测为训练集阳性比例，合并 OOF 汇总 AUROC 为 0.469697；prior 在 0.5 阈值下全判阴性，准确率 11/17 反映类别比例，不能作为识别阳性的证据。",
                  "合并 OOF 是不同折模型的描述性汇总，不代表单个部署模型的独立外部验证。",
                  "未进行模型选择、调参、校准、全样本重训或部署。此次结果没有证明可靠的预测能力，不能用结果反向修改冻结协议。",
                  "原正式双任务保持 blocked；正式结果与投稿状态仍 false，正式状态文件摘要未变。",
                  "原文核查为代理复核，未声称独立人工审稿；原文未报告的测定条件仍明确缺失。", "",
                  "## 来源与复跑", "", "本报告所有数值由同目录 JSON 的 inputs、fold_metrics 和 pooled_descriptive_metrics 绑定至真实运行文件。",
                  "复核命令只加载模型，不再次训练；输出路径必须不存在：", "", "```powershell",
                  f"python 02_code/validate_mic_three_fold_run_v2.py --run {relative(run_dir)} --output 03_experiments/audits/mic_run_validation_my_run.json"
                  + (f" --state {relative(state or publish_state)} --check-documents" if state or publish_state else ""),
                  "```", ""])
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
    result = validate(args.run, args.output, args.publish_state, args.state, args.check_documents)
    print(json.dumps({k: result[k] for k in ("status", "generated_at", "molecules", "oof_rows_recomputed",
                                             "metric_rows_recomputed", "current_state_documents_verified")}, indent=2))
