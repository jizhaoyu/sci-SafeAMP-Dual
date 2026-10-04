"""Verify the local training-ready state, frozen science, documents and absence of fitting."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from audit_mic_reviewed_subset_ludwig import verify
from research_utils import ROOT, sha256, utc_now, write_json
from review_mic_three_fold_evidence import review
from train_mic_baselines import DEFAULT_PROTOCOL_PATH, PrimaryStudyReviewRequired, load_and_validate
from train_mic_three_fold_v2 import EXPECTED_FORMAL_SHA, PROTOCOL, check, load_validated, publish_ready

READY = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v11.json"
COHORT = ROOT / "03_experiments/audits/mic_three_fold_20261002_v1"
RELEASE = ROOT / "03_experiments/audits/mic_three_fold_primary_release_20261002_v1"
DOCS = ("README.md", "docs/REMEDIATION_STATUS.md", "docs/DOCUMENTATION_INDEX.md",
        "docs/handoff/TASK_STATE.md", "03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md")


def validate(output: Path) -> dict:
    output = output.resolve()
    report = output.with_suffix(".md")
    if output.exists() or report.exists():
        raise FileExistsError(f"Refusing to overwrite training-ready validation: {output}")
    no_fit = AssertionError("Readiness validation must never fit a model")
    with patch("sklearn.linear_model.LogisticRegression.fit", side_effect=no_fit), \
            patch("sklearn.ensemble.RandomForestClassifier.fit", side_effect=no_fit), \
            patch("sklearn.dummy.DummyClassifier.fit", side_effect=no_fit):
        protocol, molecules, roles, features, cohort = load_validated()
    ready = json.loads(READY.read_text(encoding="utf-8"))
    for name, expected in ready["inputs"].items():
        check(sha256(ROOT / name) == expected, f"Readiness input changed: {name}")
    check(ready["script_sha256"] == sha256(ROOT / "02_code/train_mic_three_fold_v2.py"), "Current readiness implementation changed")
    check(ready["status"] == "ready_for_local_exploratory_training" and ready["blockers"] == []
          and ready["training_blocked"] is False and ready["records_released_for_training"] == 15
          and ready["training_started"] is False, "Incorrect current readiness state")
    check(all(gate["status"] == "passed" for gate in ready["gates"].values()), "A current gate failed")
    check(ready["gates"]["training_entry"]["model_fitting_performed_by_readiness_check"] is False
          and ready["gates"]["primary_evidence_release"]["independent_human_review_claimed"] is False,
          "Unsupported training/reviewer claim")
    check(ready["training_protocol_id"] == protocol["protocol_id"] == "protocol-mic-07"
          and ready["training_protocol_sha256"] == sha256(PROTOCOL), "Training protocol mismatch")
    check(ready["gates"]["candidate_structure"]["folds"] == cohort["folds"]
          and ready["candidate_class_counts"] == {"0": 11, "1": 4}
          and ready["predeclared_models"] == list(protocol["models"]), "Current split/model inventory mismatch")
    release = verify(RELEASE)
    check(release["full_release_review_complete"] is True
          and release["primary_measurement_studies"] == 7 and release["referenced_method_documents"] == 1,
          "Incomplete primary release inventory")
    # Historical generator/source hashes are still verified; historical document snapshots stay frozen.
    historical = (
        "mic_extended_acid_cohort_20261002_v1", "mic_independent_sources_review_20261002_v1",
        "mic_confirmed_acid_subset_20261002_v1", "mic_reviewed_subset_groups_20261002_v3",
        "mic_candidate_release_review_20261002_v1", "mic_primary_review_pmid33790103_20261002_v2",
        "mic_primary_review_pmid32344933_20261002_v2", "mic_primary_review_pmid35735615_20261002_v1",
    )
    for name in historical:
        verify(ROOT / "03_experiments/audits" / name)
    old_rejected = False
    try:
        load_and_validate(DEFAULT_PROTOCOL_PATH)
    except PrimaryStudyReviewRequired:
        old_rejected = True
    check(old_rejected, "Old protocol-mic-05 unexpectedly admitted the withdrawn cohort")
    protected = [READY, RELEASE / "manifest.json", COHORT / "manifest.json", PROTOCOL,
                 ROOT / "04_paper/research_status.json"]
    before = {str(p.relative_to(ROOT)): sha256(p) for p in protected}
    refused = []
    for name, call in (("readiness", lambda: publish_ready(READY)), ("primary_release", lambda: review(RELEASE))):
        try:
            call()
        except FileExistsError:
            refused.append(name)
    check(refused == ["readiness", "primary_release"], "A frozen output could be overwritten")
    check(before == {str(p.relative_to(ROOT)): sha256(p) for p in protected}, "An immutable artifact changed")
    check(sha256(ROOT / "04_paper/research_status.json") == EXPECTED_FORMAL_SHA
          and ready["formal_dual_task_status"] == "blocked" and ready["formal_results_available"] is False
          and ready["publication_ready"] is False, "Formal scope unexpectedly released")
    stamp = datetime.fromisoformat(ready["generated_at"]).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    for name in DOCS:
        content = (ROOT / name).read_text(encoding="utf-8")
        check(all(token in content for token in (READY.name, stamp, "mic_three_fold_20261002_v1",
                                                 "protocol-mic-06", "protocol-mic-07")), f"Document state mismatch: {name}")
        check("最新机器声明 v10" not in content and "最新机器状态 v10" not in content,
              f"Stale current state: {name}")
    paths = [*protected, ROOT / "02_code/train_mic_three_fold_v2.py", *[ROOT / name for name in DOCS]]
    result = {"status": "local_exploratory_training_ready_validation_passed", "generated_at": utc_now(),
              "readiness_state": READY.name, "audit_protocol_id": "protocol-mic-06", "training_protocol_id": "protocol-mic-07",
              "molecules": len(molecules), "observations": 22, "independently_recomputed_pairs": 105,
              "fold_roles_verified": len(roles), "fixed_features_shape": list(features.shape),
              "cross_fold_homology_edges": 0, "cross_fold_primary_studies": 0,
              "primary_measurement_studies": 7, "referenced_method_documents": 1,
              "historical_manifests_verified": len(historical), "current_state_documents_verified": len(DOCS),
              "model_fit_calls_forbidden_during_validation": True, "training_started": False,
              "records_released_for_training": 15, "old_protocol_mic_05_rejected": old_rejected,
              "overwrite_attempts_rejected": refused, "formal_status_unchanged": True,
              "independent_human_review_claimed": False, "script_sha256": sha256(Path(__file__)),
              "inputs": {str(p.relative_to(ROOT)): sha256(p) for p in paths}, "limitations": protocol["limitations"]}
    write_json(output, result)
    report.write_text("# 本地小样本 MIC 训练就绪复核\n\n"
                      f"状态来源 `{READY.name}`，生成时间 {stamp}（Asia/Shanghai）；数据 `mic_three_fold_20261002_v1`，"
                      "审计协议 `protocol-mic-06`、训练协议 `protocol-mic-07`。\n\n"
                      "真实原文证据、冻结队列、全部 105 对、45 条角色、固定模型参数、15×44 特征及五份状态文档均复核通过。"
                      "七个测定研究加一份引用方法逐文件哈希核查，旧版本不覆盖，旧 protocol-mic-05 继续拒绝旧队列。"
                      "验证期间三个模型 fit 方法均被设置为禁止调用，证明就绪检查没有训练模型。\n\n"
                      "当前 ready_for_local_exploratory_training：15 条分子获本地探索释放，尚未训练；"
                      "跨折同源边和原始研究均为 0。分区、证据和训练就绪分别记录，没有靠改变标签/阈值解除门禁。"
                      "每验证折仅 1–2 条阳性，结果不能作为临床或广泛泛化声明。\n\n"
                      "原正式双任务 blocked，正式结果和投稿授权均 false；哈希未改变。原文复核没有宣称独立人工审稿，"
                      "未报告的实验条件保持缺失。\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    result = validate(parser.parse_args().output)
    print(json.dumps({k: result[k] for k in ("status", "generated_at", "records_released_for_training",
                                            "old_protocol_mic_05_rejected", "training_started")}, indent=2))
