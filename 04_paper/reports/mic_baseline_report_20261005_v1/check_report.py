"""Bind a local draft to frozen evidence; never fit models or overwrite outputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BUNDLE = ROOT / "03_experiments/deliveries/mic_baseline_20261004_v1"
CLOSEOUT = ROOT / "03_experiments/audits/project_closeout_20261005_v1"
MANIFEST_SHA = "f8b8606dc807279cc78c6728260f6d3d7da463f2416bf47e8d3bafbdf1789ed3"
ZIP_SHA = "858f6aa9a09dfc822b6a7c155a629ae13caf0e2c922abe3448d81119e3491b2b"
FORMAL_SHA = "846c1fc2452646f3df9c2055b0a4a1b5140132acc2433bb2c304b133b6e8012c"
STATE_SHA = "404e9d90166564ec9c7543022853ae694dabc9022d913fa5d8e10f3b842a2da1"
MARKER = re.compile(r"\[claim:(C\d{3})\] \[evidence:([^\]]+)\]")
MODELS = ("dummy_prior", "logistic_regression", "random_forest")
METRIC_FIELDS = (
    "n", "positive", "negative", "AUROC", "AUPRC", "MCC_at_0_5",
    "balanced_accuracy_at_0_5", "accuracy_at_0_5", "TP", "FP", "TN", "FN",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def sources() -> list[tuple[str, Path, str]]:
    return [
        ("E001", CLOSEOUT / "review/project_delivery_status.json", "本批结案状态；全部字段"),
        ("E002", ROOT / "03_experiments/audits/mic_training_readiness_20261004_v26.json", "MIC v26；全部字段"),
        ("E003", BUNDLE / "protocol.json", "冻结协议；标签、比对、模型、环境、时间与探索声明"),
        ("E004", BUNDLE / "cohort/candidate_molecules.csv", "17 行；sample_id、amp、study_ids、component"),
        ("E005", BUNDLE / "cohort/fold_roles.csv", "全部折角色；训练/验证及类别"),
        ("E006", BUNDLE / "run/pooled_descriptive_metrics.csv", "三个模型全部合并指标及计数"),
        ("E007", BUNDLE / "run/fold_metrics.csv", "九个折模型全部指标及计数"),
        ("E008", BUNDLE / "release/independent_partition_validation.json", "全员隔离、标签冲突及代理复核范围"),
        ("E009", CLOSEOUT / "delivery_check/summary.json", "已有工作区外运行验收；时间、摘要、9 模型、51 OOF、fit=0"),
        ("E010", BUNDLE / "evidence/workspace_sources/02_code/train_mic_baselines.py", "compute_metrics；AP、AUROC、阈值与其他指标实现"),
        ("E011", BUNDLE / "evidence/workspace_sources/02_code/feature_extractor.py", "extract_handcrafted_features 及三个手工特征函数"),
        ("E012", BUNDLE / "evidence/source_index.json", "sources；原文定位、别名及限制；包含方法文献"),
        ("E013", BUNDLE / "evidence/molecule_evidence_review.csv", "分子身份及准入审查"),
        ("E014", BUNDLE / "cohort/candidate_observations.csv", "42 条表述；原值、单位、对象、条件、标签与来源"),
        ("E015", CLOSEOUT / "review/merged_candidate_decisions.csv", "78 条最终决定；30/11/37，非生物学标签"),
        ("E016", BUNDLE / "LICENSE_NOTICE.md", "本地交接及逐项许可限制"),
    ]


def table_rows(text: str, section: str) -> list[list[str]]:
    body = text.split(section, 1)[1].split("\n##", 1)[0]
    return [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in body.splitlines()
        if any(line.startswith(f"| {model} |") for model in MODELS)
    ]


def formatted_metrics(record: dict) -> list[str]:
    return [
        str(int(record[key])) if key in ("n", "positive", "negative", "TP", "FP", "TN", "FN")
        else f"{float(record[key]):.4f}" for key in METRIC_FIELDS
    ]


def inspect() -> tuple[dict, dict, list[dict], dict]:
    require(digest(BUNDLE / "manifest.json") == MANIFEST_SHA, "Bundle manifest changed")
    manifest = load(BUNDLE / "manifest.json")
    require(len(manifest["files"]) == 394, "Unexpected bound inventory")
    for relative, expected in manifest["files"].items():
        path = (BUNDLE / relative).resolve()
        require(path.is_relative_to(BUNDLE.resolve()), "Unsafe bound path")
        require(digest(path) == expected, f"Frozen file changed: {relative}")
    require(digest(BUNDLE.with_suffix(".zip")) == ZIP_SHA, "Delivery archive changed")
    require(digest(ROOT / "04_paper/research_status.json") == FORMAL_SHA, "Formal state changed")
    require(digest(sources()[1][1]) == STATE_SHA, "MIC v26 state changed")
    close, state, protocol = (load(path) for _, path, _ in sources()[:3])
    require(state["training_blocked"] is False and state["result_verification_status"] == "passed", "MIC state incompatible")
    require(close["formal_dual_task_status"] == "blocked" and close["publication_ready"] is False, "Formal boundary incompatible")
    require(close["project_original_dual_task_objective_completed"] is False, "Original objective status changed")
    require(close["eligible_external_records"] == 0 and close["current_batch_search_tasks"] == 0, "Evidence batch changed")
    require(close["cross_cohort_isolation_status"] == "not_run_no_evidence_eligible_records", "External audit status changed")
    require(protocol["protocol_id"] == state["training_protocol_id"] == "protocol-mic-13", "Protocol conflict")
    molecules, observations, roles = (rows(BUNDLE / f"cohort/{name}.csv") for name in ("candidate_molecules", "candidate_observations", "fold_roles"))
    labels = {row["sample_id"]: int(row["amp"]) for row in molecules}
    require(len(labels) == len(molecules) == 17 and sum(labels.values()) == 6, "Cohort counts changed")
    require(len(observations) == 42, "Observation count changed")
    fold_counts = []
    for fold in range(3):
        values = []
        for role in ("train", "validation"):
            selected = [r for r in roles if int(r["fold"]) == fold and r["role"] == role]
            positive = sum(labels[r["sample_id"]] for r in selected)
            values += [len(selected), positive, len(selected) - positive]
        fold_counts.append([fold] + values)
    pooled = rows(BUNDLE / "run/pooled_descriptive_metrics.csv")
    folds = rows(BUNDLE / "run/fold_metrics.csv")
    report = (HERE / "report.md").read_text(encoding="utf-8")
    expected_pooled = [[r["model"]] + formatted_metrics(r) for r in sorted(pooled, key=lambda x: MODELS.index(x["model"]))]
    expected_folds = [[r["model"], r["fold"]] + formatted_metrics(r) for r in sorted(folds, key=lambda x: (MODELS.index(x["model"]), int(x["fold"]))) ]
    require(table_rows(report, "### 3.1") == expected_pooled, "Pooled report table mismatch")
    require(table_rows(report, "### 3.2") == expected_folds, "Fold report table mismatch")
    for record in fold_counts:
        require("| " + " | ".join(map(str, record)) + " |" in report, "Fold class table mismatch")
    oof = rows(BUNDLE / "run/oof_predictions.csv")
    require(len(oof) == 51, "OOF count changed")
    index = load(BUNDLE / "evidence/source_index.json")
    require(len(index["sources"]) == 10, "Source inventory changed")
    for source in index["sources"]:
        require(source["source_url"] in report, "Original source link missing")
        path = (BUNDLE / source["bundle_primary_file"]).resolve()
        require(path.is_relative_to(BUNDLE.resolve()), "Unsafe primary-source path")
        require(digest(path) == source["sha256"], "Primary-source binding changed")
    ids = {identifier for identifier, _, _ in sources()}
    claims = []
    for line_number, line in enumerate(report.splitlines(), 1):
        marker = MARKER.search(line)
        if marker is None:
            continue
        claim, references = marker.groups()
        require(set(references.split(",")).issubset(ids), "Unknown evidence identifier")
        normalized = " ".join(MARKER.sub("", line).split())
        claims.append({"claim_id": claim, "line": line_number, "claim_text_sha256": hashlib.sha256(normalized.encode()).hexdigest(), "evidence_ids": references, "verification_status": "agent_local_check_only_human_pending", "analysis_intent": "followup_exploratory_descriptive"})
    require(len(claims) == 33 and len({r["claim_id"] for r in claims}) == 33, "Missing/duplicate claim anchors")
    missing = []
    for file in (HERE / "report.md", HERE / "demo.md"):
        for target in re.findall(r"\]\((D:/[^)]+)\)", file.read_text(encoding="utf-8")):
            if Path(target).parent == HERE and Path(target).name in ("source_manifest.json", "validation_v1.json"):
                continue  # generated in this build
            if not Path(target).exists():
                missing.append(target)
    require(not missing, f"Missing local links: {missing}")
    facts = {
        "mic_state_generated_at": state["generated_at"], "closeout_state_generated_at": close["generated_at"],
        "protocol_id": protocol["protocol_id"], "protocol_frozen_at": protocol["frozen_at"],
        "data_version": state["data_version"], "molecules": len(molecules), "observation_mentions": len(observations),
        "positive": 6, "negative": 11, "fold_counts": fold_counts, "component_counts": state["component_counts"],
        "all_member_comparisons": state["all_member_comparisons"], "pooled_metrics": pooled, "fold_metrics": folds,
        "formal_dual_task_status": close["formal_dual_task_status"], "eligible_external_records": 0,
        "external_isolation_status": close["cross_cohort_isolation_status"], "publication_ready": False,
    }
    source_manifest = {"schema_version": "1.0", "human_verification_pending": True, "sources": [
        {"evidence_id": identifier, "title": path.name, "source_type": "local_frozen_research_artifact",
         "path": str(path), "sha256": digest(path), "locator": locator,
         "verification": {"status": "unverified_by_accountable_human", "source_opened_by_agent": True,
                          "verified_by": None, "verified_on": None}}
        for identifier, path, locator in sources()
    ]}
    checks = {"status": "passed_local_consistency", "submission_ready": False, "independent_human_review": False,
              "bound_bundle_files_checked": 394, "primary_source_files_checked": 10,
              "report_claim_anchors_checked": 33, "pooled_model_rows_checked": 3, "fold_model_rows_checked": 9,
              "model_fit_calls": 0, "runtime_reexecuted_in_report_stage": False,
              "scope": "file bindings, draft claim anchors, links and exact formatted tables; not new scientific evidence approval"}
    return facts, source_manifest, claims, checks


def write_new(path: Path, value: str) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        stream.write(value)


def encoded(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    facts, evidence, claims, checks = inspect()
    checks["generated_at"] = datetime.now(timezone.utc).isoformat()
    if args.command == "build":
        require(args.output is None, "Build outputs have fixed local names")
        outputs = [HERE / name for name in ("facts.json", "source_manifest.json", "claims.csv", "report_manifest.json", "validation_v1.json")]
        require(not any(p.exists() for p in outputs), "Refusing to overwrite an existing report build")
        write_new(outputs[0], encoded(facts)); write_new(outputs[1], encoded(evidence))
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=list(claims[0])); writer.writeheader(); writer.writerows(claims)
        write_new(outputs[2], buffer.getvalue())
        bindings = {str(path.relative_to(ROOT)): digest(path) for _, path, _ in sources()}
        bindings.update({"04_paper/research_status.json": FORMAL_SHA, str(BUNDLE.with_suffix(".zip").relative_to(ROOT)): ZIP_SHA,
                         str((BUNDLE / "manifest.json").relative_to(ROOT)): MANIFEST_SHA})
        products = {path.name: digest(path) for path in (HERE / "report.md", HERE / "demo.md", HERE / "check_report.py", *outputs[:3])}
        manifest = {"generated_at": checks["generated_at"], "report_version": HERE.name, "submission_ready": False,
                    "human_verification_pending": True, "protocol_id": facts["protocol_id"], "data_version": facts["data_version"],
                    "inputs": bindings, "outputs": products}
        write_new(outputs[3], encoded(manifest))
        checks["report_manifest_sha256"] = digest(outputs[3])
        write_new(outputs[4], encoded(checks))
    else:
        require(args.output is not None, "Verify requires a new --output path")
        output = args.output.resolve()
        require(output.parent == HERE and not output.exists(), "Verification output must be a new file in this report directory")
        manifest = load(HERE / "report_manifest.json")
        require(manifest["submission_ready"] is False and manifest["human_verification_pending"] is True, "Draft boundary changed")
        for relative, expected in manifest["inputs"].items():
            path = (ROOT / relative).resolve()
            require(path.is_relative_to(ROOT), "Unsafe report input")
            require(digest(path) == expected, f"Report input changed: {relative}")
        for name, expected in manifest["outputs"].items():
            path = (HERE / name).resolve()
            require(path.parent == HERE, "Unsafe report output")
            require(digest(path) == expected, f"Report output changed: {name}")
        require(load(HERE / "facts.json") == facts and load(HERE / "source_manifest.json") == evidence, "Evidence/fact registry drift")
        require(rows(HERE / "claims.csv") == [{k: str(v) for k, v in row.items()} for row in claims], "Claim registry drift")
        checks["report_manifest_sha256"] = digest(HERE / "report_manifest.json")
        write_new(output, encoded(checks))
    print(encoded(checks))


if __name__ == "__main__":
    main()
