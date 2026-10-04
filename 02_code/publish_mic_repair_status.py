"""Publish evidence-blocked review state; render one exact current block for all documents."""
import argparse
import difflib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from audit_mic_evidence_repair import DEFAULT_OUTPUT as EVIDENCE, verify_original_materials
from research_evidence_gate import verify_manifest, workspace_path
from research_utils import ROOT, read_json, sha256, utc_now, write_json

DEFAULT_STATE = ROOT / "03_experiments/audits/mic_training_readiness_20261003_v16.json"
HISTORY = ROOT / "03_experiments/audits/gemini_repair_20261003_v1/historical_artifacts.json"
EXTERNAL = ROOT / "03_experiments/audits/dual_task_external_curation_20261003_v2/curation_manifest.json"
DOCS = ("README.md", "docs/REMEDIATION_STATUS.md", "docs/DOCUMENTATION_INDEX.md",
        "docs/handoff/TASK_STATE.md", "03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md")
START = "<!-- RESEARCH_STATUS_CURRENT_START -->"
END = "<!-- RESEARCH_STATUS_CURRENT_END -->"
STATUS = "historical_training_completed_evidence_review_blocked"


def publish(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite research review state: {output}")
    verify_original_materials()
    evidence = verify_manifest(EVIDENCE)
    external = read_json(EXTERNAL)
    for name, expected in external["inputs"].items():
        if sha256(workspace_path(name)) != expected:
            raise ValueError(f"External review input changed: {name}")
    for name, expected in external["outputs"].items():
        if sha256(EXTERNAL.parent / name) != expected:
            raise ValueError(f"External review output changed: {name}")
    history = read_json(HISTORY)
    for name, expected in history["all_artifact_sha256"].items():
        if sha256(workspace_path(name)) != expected:
            raise ValueError(f"Historical artifact changed: {name}")
    formal_path = ROOT / "04_paper/research_status.json"
    formal = read_json(formal_path)
    if (evidence["status"] != "complete_evidence_release_blocked"
            or evidence["full_release_review_complete"] is not False
            or evidence["records_released_for_training"] != 0
            or external["eligible_verified_count"] != 0
            or history["model_fitting_performed"] is not False
            or formal["status"] != "blocked"):
        raise ValueError("Unexpected review facts; do not infer a scientific release")
    inputs = [EVIDENCE / "manifest.json", EXTERNAL, HISTORY, formal_path, Path(__file__),
              ROOT / "02_code/research_evidence_gate.py", ROOT / "02_code/train_mic_three_fold_v3.py",
              ROOT / "02_code/train_mic_esm2_three_fold.py", ROOT / "02_code/extract_mic_esm2_features.py"]
    state = {"schema_version": 4, "status": STATUS, "generated_at": utc_now(),
             "state_path": output.relative_to(ROOT).as_posix(),
             "supersedes": "03_experiments/audits/mic_training_readiness_20261002_v15.json",
             "scope": "Current 17-molecule expansion evidence review; existing 15-molecule baseline is recorded separately",
             "engineering_status": "implemented", "dataset_preparation_status": "blocked",
             "data_version": EVIDENCE.name, "data_dir": EVIDENCE.relative_to(ROOT).as_posix(),
             "historical_candidate_cohort_version": evidence["historical_cohort_version"],
             "audit_protocol_id": "protocol-mic-08", "training_protocol_id": None, "training_command": None,
             "candidate_molecules": evidence["candidate_molecules"], "candidate_observations": evidence["candidate_observations"],
             "external_candidate_count": external["total_audited_candidates"],
             "historical_training_completed": True, "new_training_started": False, "training_blocked": True,
             "records_released_for_training": 0, "new_molecules_evidence_approved": 0,
             "existing_baseline": {"cohort_version": "mic_three_fold_20261002_v1", "training_protocol_id": "protocol-mic-07",
                                   "molecules_evidence_approved": 15, "observations_evidence_approved": 22,
                                   "status": "historical_exploratory_training_completed"},
             "gates": {"primary_evidence_release": {"status": "blocked", "full_release_review_complete": False},
                       "training_protocol": {"status": "blocked", "protocol_id": None},
                       "original_study_isolation": {"status": "requires_reaudit_after_identifier_correction"},
                       "historical_artifact_integrity": {"status": "passed", "verification": HISTORY.relative_to(ROOT).as_posix()},
                       "external_primary_evidence": {"status": "blocked", "eligible_verified_count": 0}},
             "historical_runs": history["runs"],
             "formal_dual_task_status": formal["status"], "formal_protocol_id": formal["protocol_id"],
             "formal_state_path": formal_path.relative_to(ROOT).as_posix(), "formal_state_sha256": sha256(formal_path),
             "formal_run_status": formal["run_status"], "formal_results_available": False, "publication_ready": False,
             "blockers": evidence["blockers"] + ["External candidate measurements and molecular forms have not completed primary-source release."],
             "producer": Path(__file__).relative_to(ROOT).as_posix(),
             "inputs": {p.relative_to(ROOT).as_posix(): sha256(p) for p in inputs}}
    write_json(output, state)
    return state


def render_current_status(state: dict) -> str:
    if (state["status"] != STATUS or state["training_protocol_id"] is not None
            or state["gates"]["training_protocol"]["protocol_id"] is not None
            or state["training_command"] is not None or state["records_released_for_training"] != 0
            or state["training_blocked"] is not True
            or state["gates"]["primary_evidence_release"] != {"status": "blocked", "full_release_review_complete": False}
            or state["formal_results_available"] is not False or state["publication_ready"] is not False):
        raise ValueError("Inconsistent current research state")
    stamp = datetime.fromisoformat(state["generated_at"]).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    return "\n".join((START, "## 当前研究状态（机器生成）", "",
        f"状态来源：`{state['state_path']}`。",
        f"生成时间：{stamp}（Asia/Shanghai）。审查数据版本：`{state['data_version']}`；目录：`{state['data_dir']}`。",
        f"当前状态：`{state['status']}`。来源审查协议：`{state['audit_protocol_id']}`；当前可执行训练协议：`null`；训练命令：`null`。", "",
        "| 状态轴 | 当前结论 |", "|---|---|",
        "| 工程实现 | 已实现；证据门禁已修复为缺失即拒绝 |",
        f"| 扩充队列证据 | `blocked`；{state['candidate_molecules']} 条历史候选、{state['candidate_observations']} 条观察；新增候选完整释放为 {state['new_molecules_evidence_approved']} |",
        "| 历史探索训练 | 手工 9 个模型/51 条 OOF，ESM2 对比 27 个模型/153 条 OOF；产物可复现，17 条准入声明已撤回 |",
        "| 新训练 | `blocked`；扩充队列释放为 0，不提供训练命令 |",
        f"| 外部候选 | {state['external_candidate_count']} 条保留为线索；完整原测定资格批准为 {state['gates']['external_primary_evidence']['eligible_verified_count']} |",
        f"| 原双任务正式研究 | `{state['formal_dual_task_status']}`；`{state['formal_protocol_id']}`；正式运行 `none` |",
        "| 正式结果 / 投稿就绪 | `false` / `false` |", "",
        "旧 15 条基线的完整证据和训练结果保留（protocol-mic-07，15 分子/22 观察）。v12–v15 及下方旧时点结论为历史记录；17 条队列的旧放行/已确证声明不能用于当前研究准入。",
        "历史训练协议：`protocol-mic-09` / `protocol-mic-10`；历史数据：`mic_source_expansion_result_20261002_v2`。",
        "历史运行：`03_experiments/runs/mic_three_fold_20261002_v2`、`03_experiments/runs/mic_three_fold_esm2_20261002_v1`。",
        "本次仅整改证据与软件门禁，未重新训练。下一步补齐逐分子/逐测定原始证据，再冻结新的训练协议。", END))


def updated_document(content: str, state: dict) -> str:
    block = render_current_status(state)
    if START in content:
        left, right = content.index(START), content.index(END) + len(END)
        return content[:left] + block + content[right:]
    first_line, body = content.split("\n", 1)
    replacements = {"最新机器状态 v15": "历史机器状态 v15", "最新机器声明 v15": "历史机器声明 v15",
                    "最新机器声明 v14": "历史机器声明 v14", "最新机器状态 v14": "历史机器状态 v14",
                    "目前为[本地探索训练完成 v12": "历史记录为[本地探索训练完成 v12",
                    "当前 v12": "历史 v12", "RF 识别出 3 条阳性": "RF 的历史预测识别出 4 条阳性",
                    "MIC-only 最新表征探索版本": "MIC-only 历史表征探索版本",
                    "当前 **local_exploratory_esm2_training_completed**": "历史记录 **local_exploratory_esm2_training_completed**"}
    for old, new in replacements.items():
        body = body.replace(old, new)
    return first_line + "\n\n" + block + "\n\n## 历史记录（旧准入声明已由上述审查状态替代）\n\n" + body.lstrip("\n")


def document_patch(state: dict) -> str:
    sections = ["*** Begin Patch"]
    for name in DOCS:
        before = (ROOT / name).read_text(encoding="utf-8")
        after = updated_document(before, state)
        diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm=""))
        if diff:
            sections.append(f"*** Update File: {name}")
            for line in diff[2:]:
                sections.append("@@" if line.startswith("@@") else line)
    sections.append("*** End Patch")
    return "\n".join(sections)


def validate_documents(state: dict) -> None:
    expected = render_current_status(state)
    for name in DOCS:
        content = (ROOT / name).read_text(encoding="utf-8")
        if content.count(START) != 1 or content.count(END) != 1:
            raise ValueError(f"Current state block is missing/duplicated: {name}")
        actual = content[content.index(START):content.index(END) + len(END)]
        if actual != expected:
            raise ValueError(f"Current state facts differ from machine state: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--document-patch", action="store_true")
    parser.add_argument("--check-documents", action="store_true")
    args = parser.parse_args()
    if args.document_patch:
        print(document_patch(read_json(args.state)))
    elif args.check_documents:
        validate_documents(read_json(args.state))
        print({"documents_verified": len(DOCS)})
    else:
        state = publish(args.output)
        print({k: state[k] for k in ("status", "generated_at", "training_blocked", "records_released_for_training")})
