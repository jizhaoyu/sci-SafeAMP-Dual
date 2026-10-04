"""Review the fixed 17-record MIC follow-up without granting evidence by ID."""
from __future__ import annotations

import argparse
import csv
import difflib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from audit_mic_evidence_repair import DEFAULT_OUTPUT as REPAIR, verify_original_materials
from audit_mic_reviewed_subset_ludwig import verify as verify_structure
from publish_mic_repair_status import DOCS, END, START
from public_data import measurement_label
from research_evidence_gate import require_primary_release, verify_manifest, workspace_path
from research_utils import ROOT, read_json, sha256, utc_now, write_json
from validate_mic_acid_progress import independent_identity


STATE16 = ROOT / "03_experiments/audits/mic_training_readiness_20261003_v16.json"
FORMAL = ROOT / "04_paper/research_status.json"
EXPANDED = ROOT / "03_experiments/audits/mic_source_expansion_result_20261002_v2"
REPAIR = ROOT / "03_experiments/audits/mic_evidence_repair_20261003_v1"
EXTERNAL = ROOT / "03_experiments/audits/dual_task_external_curation_20261003_v2/curation_manifest.json"
OLD_RELEASE_PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-07.json"
OLD_RELEASE_FREEZE = ROOT / "03_experiments/audits/protocol_mic_07_freeze_20261002_v2.json"
OLD_RELEASE_ENTRY = ROOT / "02_code/train_mic_three_fold_v2.py"
AUDIT_PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-06.json"
OLD_BASELINE = ROOT / "03_experiments/audits/mic_three_fold_20261002_v1"
OLD_BASELINE_RUN = ROOT / "03_experiments/runs/mic_three_fold_20261002_v1"
SOURCE_MATERIALS = ROOT / "03_experiments/audits/mic_reviewed_source_materials_20261003_v1"
DEFAULT_OUTPUT = ROOT / "03_experiments/audits/mic_reviewed_release_20261003_v3"
STATE17 = ROOT / "03_experiments/audits/mic_training_readiness_20261003_v17.json"
STATE18 = ROOT / "03_experiments/audits/mic_training_readiness_20261003_v18.json"
NEW_STATE = ROOT / "03_experiments/audits/mic_training_readiness_20261003_v19.json"
DOC_START = "<!-- RESEARCH_STATUS_CURRENT_START -->"
DOC_END = "<!-- RESEARCH_STATUS_CURRENT_END -->"
NEW_IDS = {"4e1914c54d14afece198fd5d", "5445b7b645f69b6d7f8abdf3"}


def _check_inputs() -> dict:
    archive = verify_original_materials()
    state = read_json(STATE16)
    for name, digest in state["inputs"].items():
        if sha256(workspace_path(name)) != digest:
            raise ValueError(f"Protected v16 readiness input changed: {name}")
    current = read_json(FORMAL)
    if sha256(FORMAL) != state["formal_state_sha256"] or current["status"] != "blocked":
        raise ValueError("Original formal dual-task state changed")
    repaired = verify_manifest(REPAIR)
    if repaired["status"] != "complete_evidence_release_blocked":
        raise ValueError("Corrected source identifier review is missing")
    protocol = read_json(OLD_RELEASE_PROTOCOL)
    release = require_primary_release(protocol, OLD_RELEASE_FREEZE, OLD_RELEASE_ENTRY)
    old_dir = workspace_path(protocol["evidence_release_manifest"]).parent
    old_ids = set(pd.read_csv(old_dir / "molecule_evidence_review.csv", keep_default_na=False).sample_id)
    new_molecules = pd.read_csv(EXPANDED / "candidate_molecules.csv", keep_default_na=False)
    new_assays = pd.read_csv(EXPANDED / "assay_observations.csv", keep_default_na=False)
    if len(new_molecules) != 17 or len(new_assays) != 24 or not NEW_IDS.issubset(set(new_molecules.sample_id)):
        raise ValueError("The frozen 17-molecule, 24-observation review scope changed")
    if not old_ids.issubset(set(new_molecules.sample_id)):
        raise ValueError("New source cohort omits a member of the released 15-molecule baseline")
    return {"archive": archive, "state16": state, "formal": current, "repair": repaired,
            "protocol07": protocol, "release07": release, "old_release_dir": old_dir,
            "old_ids": old_ids, "molecules17": new_molecules, "assays24": new_assays}


def _candidate_decisions(ctx: dict) -> pd.DataFrame:
    molecules, assays = ctx["molecules17"], ctx["assays24"]
    sources = pd.read_csv(REPAIR / "source_identifier_review.csv", keep_default_na=False)
    bmap_source = sources[sources.source_id.eq("bmap2025")]
    if len(bmap_source) != 1 or (bmap_source.iloc[0].doi, bmap_source.iloc[0].pmid) != ("10.1002/mlf2.70020", "40600060"):
        raise ValueError("BMAP-27B source identity correction no longer matches original XML")
    rows = []
    for sample_id in sorted(NEW_IDS):
        molecule = molecules[molecules.sample_id.eq(sample_id)]
        records = assays[assays.sample_id.eq(sample_id)]
        if len(molecule) != 1 or len(records) != 1:
            raise ValueError(f"Expected one source record for candidate {sample_id}")
        m, a = molecule.iloc[0], records.iloc[0]
        if sample_id == "4e1914c54d14afece198fd5d":
            if (a.record_id, a.target, a.raw_mic, a.raw_unit) != (
                    "chekmenev2006:p1-COO-", "Escherichia coli ATCC 25922", "2-10", "µM"):
                raise ValueError("Piscidin 1 raw endpoint differs from the preserved original record")
            source_file = ROOT / "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/chekmenev2006.pdf"
            source_hash = sha256(source_file)
            status = "withheld_actual_assay_n_terminus_unverified"
            locus = "PDF p. 4 section 2.1 and p. 5 Table 1; actual assay peptide was obtained from UTSW; page 5 table specifies the free-carboxyl form"
            limitation = "The publication separates the structural-study synthesis from the UTSW assay material and reports HPLC purity for the latter; it does not establish that assay specimen's free N terminus. No molecule label is released."
            label = None
        else:
            source_file = ROOT / "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/bmap2025.xml"
            source_hash = sha256(source_file)
            if a.target != "Escherichia coli (CREC6 / clinical isolates & ATCC 25922)" or a.raw_mic != "1.563-6.250":
                raise ValueError("BMAP-27B aggregated record differs from the preserved original")
            status = "withheld_isolate_specific_mic_unverified"
            locus = "XML section mlf270020-sec-0030; original Figure 1 and supplement reference mlf270020-suppl-0009"
            limitation = "The stored article reports a range across CRE strains, while the indexed assay target combines CREC6, clinical isolates and ATCC 25922. The figure image and valid supplementary document could not be retrieved; no isolate-specific value is certified."
            label = None
        rows.append({"sample_id": sample_id, "record_id": a.record_id, "sequence_source": a.source_dataset,
                     "sequence": m.seq, "source_doi": ("10.1016/j.bbamem.2006.03.034" if sample_id.startswith("4e") else "10.1002/mlf2.70020"),
                     "source_pmid": ("16815244" if sample_id.startswith("4e") else "40600060"),
                     "primary_file": source_file.relative_to(ROOT).as_posix(), "primary_file_sha256": source_hash,
                     "primary_locator": locus, "reported_target": a.target, "raw_mic": a.raw_mic,
                     "raw_unit": a.raw_unit, "reported_method_and_conditions": a.medium,
                     "evidence_decision": status, "derived_label": label,
                     "expanded_training_release": False, "decision_basis": limitation})
    return pd.DataFrame(rows)


def review(output: Path = DEFAULT_OUTPUT) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite MIC release review: {output}")
    if not output.is_relative_to(ROOT / "03_experiments/audits"):
        raise ValueError("Review output must stay within the audit directory")
    ctx = _check_inputs()
    candidates = _candidate_decisions(ctx)
    output.mkdir(parents=True)
    candidates.to_csv(output / "new_candidate_review.csv", index=False, encoding="utf-8-sig")
    acquisition = read_json(SOURCE_MATERIALS / "acquisition.json")
    attempts = read_json(SOURCE_MATERIALS / "figure_retrieval_attempts.json")
    files = [STATE16, FORMAL, REPAIR / "manifest.json", EXPANDED / "manifest.json",
             EXPANDED / "candidate_molecules.csv", EXPANDED / "assay_observations.csv",
             OLD_RELEASE_PROTOCOL, OLD_RELEASE_FREEZE, ctx["old_release_dir"] / "manifest.json",
             SOURCE_MATERIALS / "acquisition.json", SOURCE_MATERIALS / "figure_retrieval_attempts.json",
             ROOT / "02_code/audit_mic_evidence_repair.py", Path(__file__)]
    files.extend(ROOT / row.primary_file for row in candidates.itertuples(index=False))
    manifest = {
        "status": "new_candidates_withheld_existing_15_evidence_preserved",
        "generated_at": utc_now(), "audit_protocol_id": "protocol-mic-08",
        "candidate_cohort_version": EXPANDED.name, "candidate_molecules": 17,
        "candidate_observations": 24, "existing_baseline_molecules_evidence_approved": 15,
        "existing_baseline_observations_evidence_approved": 22,
        "new_candidates_reviewed": 2, "new_candidates_released": 0,
        "candidate_release_complete": False, "three_fold_gate_status": "not_run_no_new_eligible_molecules",
        "new_training_protocol_id": None, "training_started": False,
        "supplementary_retrieval": acquisition, "figure_retrieval_attempts": attempts,
        "blockers": candidates.decision_basis.tolist(),
        "inputs": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(set(files))},
        "outputs": {"new_candidate_review.csv": sha256(output / "new_candidate_review.csv")},
        "script_sha256": sha256(Path(__file__)),
    }
    (output / "report.md").write_text(
        "# MIC 新增候选原始证据审查\n\n"
        f"生成时间：{manifest['generated_at']}；审查协议：`protocol-mic-08`；范围：现有 17 条候选中的 2 条新增记录。\n\n"
        "## 结论\n\n"
        "两条新增记录均未达到分子证据释放条件。已释放的 15 条基线仍通过原冻结证书；本次扩充释放 0 条，未生成可训练扩充队列，未启动训练。\n\n"
        "## 逐条结论\n\n"
        "| 记录 | 原始测定线索 | 审查结论 |\n|---|---|---|\n"
        "| Piscidin 1 | PMID 16815244；原文 Table 1 报告 ATCC 25922 的 `p1-COO−`，范围 2–10 µM；p. 4 材料部分称抗菌测定所用材料来自 UTSW | 游离羧基有直接表格依据；实际测试样品的游离氨基端未被来源方法确认，暂缓分子释放 |\n"
        "| BMAP-27B | PMID 40600060；原文报告 CRE 的合并 MIC 范围，候选数据库行将 CREC6、临床分离株和 ATCC 25922 合在一个对象字段中 | 现有字段不足以复核单一菌株的数值；补充文件下载地址返回 HTML 错误页且图像取回失败，继续暂缓 |\n\n"
        "两项未释放记录均没有标签。BMAP-27B 的合并范围保留为来源记录，不分摊或转写为任何单株测定值。逐记录原字段、原始来源位置、摘要和理由见 `new_candidate_review.csv`。\n\n"
        "## 隔离与训练状态\n\n"
        "新增记录均未获释放，所以本轮不把它们送入分组或三折评估。旧 15 条原训练角色由独立审计程序重新核对。若正确来源别名改变既有分组或跨折隔离，仍保持阻断，不重排折以追求通过。\n\n"
        "来源复核为代理原文复核，不代表独立人工评审。原双任务协议 `protocol-amd-02` 及其状态不在本审查的放行范围内。\n",
        encoding="utf-8")
    manifest["outputs"]["report.md"] = sha256(output / "report.md")
    write_json(output / "manifest.json", manifest)
    return manifest


def prepare(review_dir: Path, output: Path) -> dict:
    review_dir, output = Path(review_dir).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite MIC candidate cohort: {output}")
    if not review_dir.is_relative_to(ROOT / "03_experiments/audits") or not output.is_relative_to(ROOT / "03_experiments/audits"):
        raise ValueError("Review and candidate cohort must stay within the audit directory")
    review_manifest = verify_manifest(review_dir)
    if review_manifest["new_candidates_released"] == 0:
        raise ValueError("No newly released molecules; do not create or retrain an expanded cohort")
    raise ValueError("This reviewed cohort contains no implemented primary release certificate; release review is required")


def _updated_state(review_dir: Path, review_manifest: dict, study_audit: dict) -> dict:
    prior = read_json(STATE16)
    return {
        "schema_version": 1, "status": "mic_expansion_blocked_existing_baseline_preserved",
        "generated_at": utc_now(), "state_path": NEW_STATE.relative_to(ROOT).as_posix(),
        "supersedes": STATE16.relative_to(ROOT).as_posix(),
        "engineering_status": "implemented", "dataset_preparation_status": "blocked",
        "data_version": review_dir.name, "data_dir": review_dir.relative_to(ROOT).as_posix(),
        "audit_protocol_id": review_manifest["audit_protocol_id"], "training_protocol_id": None,
        "training_command": None, "candidate_molecules": review_manifest["candidate_molecules"],
        "candidate_observations": review_manifest["candidate_observations"],
        "new_candidates_reviewed": review_manifest["new_candidates_reviewed"],
        "new_candidates_released": review_manifest["new_candidates_released"],
        "training_started": False, "training_blocked": True,
        "records_released_for_training": 0,
        "existing_baseline": prior["existing_baseline"],
        "gates": {"existing_baseline_evidence": "passed",
                  "new_candidate_primary_evidence": "blocked",
                  "updated_all_member_study_isolation": study_audit["status"],
                  "training_protocol": "not_created_without_new_released_data"},
        "existing_baseline_isolation_audit": study_audit,
        "formal_dual_task_status": prior["formal_dual_task_status"],
        "formal_protocol_id": prior["formal_protocol_id"],
        "formal_state_path": prior["formal_state_path"],
        "formal_state_sha256": prior["formal_state_sha256"],
        "formal_run_status": prior["formal_run_status"],
        "formal_results_available": prior["formal_results_available"],
        "publication_ready": prior["publication_ready"],
        "blockers": review_manifest["blockers"] + study_audit["blockers"],
        "producer": Path(__file__).relative_to(ROOT).as_posix(),
        "inputs": {},
    }


def audit_existing_baseline(review_dir: Path) -> dict:
    """Recompute source and member isolation for the certified 15-row cohort."""
    ctx = _check_inputs()
    reviewed = verify_manifest(review_dir)
    if reviewed["candidate_release_complete"] is not False:
        raise ValueError("This status publisher handles the present evidence-blocked review only")
    sources = pd.read_csv(ctx["old_release_dir"] / "source_review.csv", keep_default_na=False)
    molecules = pd.read_csv(ctx["old_release_dir"] / "molecule_evidence_review.csv", keep_default_na=False)
    assays = pd.read_csv(ctx["old_release_dir"] / "assay_evidence_review.csv", keep_default_na=False)
    baseline = pd.read_csv(OLD_BASELINE / "candidate_molecules.csv", keep_default_na=False)
    roles = pd.read_csv(OLD_BASELINE / "fold_roles.csv", keep_default_na=False)
    source_ids = {r.source_id for r in sources.itertuples(index=False)}
    if (set(molecules.sample_id) != ctx["old_ids"] or len(molecules) != 15 or len(assays) != 22
            or not set(assays.sample_id).issubset(ctx["old_ids"])
            or not set(assays.source_id).issubset(source_ids)):
        raise ValueError("Certified 15-molecule evidence coverage is incomplete")
    source_for = {r.source_id: {f"primary_source:{r.source_id}"} for r in sources.itertuples(index=False)}
    # Map corrected primary-study aliases from the separate XML identifier review where present.
    corrected = pd.read_csv(REPAIR / "source_identifier_review.csv", keep_default_na=False)
    for row in corrected.itertuples(index=False):
        if row.identifier_review == "verified_against_primary_xml" and row.study_aliases:
            source_for[row.source_id] = set(row.study_aliases.split("|"))
    grouped = {}
    for row in assays.itertuples(index=False):
        aliases = source_for[row.source_id]
        if not aliases:
            raise ValueError(f"No primary-study aliases for released observation: {row.sample_id}")
        grouped.setdefault(row.sample_id, set()).update(aliases)
    fold_for = roles[roles.role.eq("validation")].set_index("sample_id").fold.to_dict()
    if set(fold_for) != ctx["old_ids"]:
        raise ValueError("Old baseline validation membership is incomplete")
    label_for = baseline.set_index("sample_id").amp.astype(int).to_dict()
    blockers = []
    for fold in (0, 1, 2):
        valid = {sample for sample, assigned in fold_for.items() if int(assigned) == fold}
        train = set(fold_for) - valid
        if {label_for[sample] for sample in valid} != {0, 1}:
            blockers.append(f"Frozen validation fold {fold} lacks a class")
        if {label_for[sample] for sample in train} != {0, 1}:
            blockers.append(f"Frozen training complement {fold} lacks a class")
    pairs = []
    cross_homology, cross_study = 0, 0
    for first, second in itertools.combinations(baseline.itertuples(index=False), 2):
        score = independent_identity(first.seq, second.seq)
        shared = sorted(grouped.get(first.sample_id, set()) & grouped.get(second.sample_id, set()))
        same_fold = int(fold_for[first.sample_id]) == int(fold_for[second.sample_id])
        homology_edge = score >= 0.40
        cross_homology += int(homology_edge and not same_fold)
        cross_study += int(bool(shared) and not same_fold)
        if homology_edge and not same_fold:
            blockers.append(f"Cross-fold similarity >=0.40: {first.sample_id}/{second.sample_id}")
        if shared and not same_fold:
            blockers.append(f"Cross-fold primary study: {first.sample_id}/{second.sample_id}: {','.join(shared)}")
        pairs.append({"sample_id_a": first.sample_id, "sample_id_b": second.sample_id,
                      "identity_alignment_columns": score, "same_frozen_fold": same_fold,
                      "shared_primary_study_aliases": "|".join(shared),
                      "cross_fold_homology": homology_edge and not same_fold,
                      "cross_fold_study": bool(shared) and not same_fold})
    expected_pairs = len(ctx["old_ids"]) * (len(ctx["old_ids"]) - 1) // 2
    if len(pairs) != expected_pairs:
        raise ValueError("Incomplete recomputed all-member identity matrix")
    edges = pd.DataFrame(pairs)
    edges.to_csv(review_dir / "existing_15_pair_reaudit.csv", index=False, encoding="utf-8-sig")
    if cross_homology or cross_study:
        status = "blocked_source_correction_invalidates_frozen_partition"
    else:
        status = "passed_existing_15_historical_partition_preserved"
    review_path = review_dir / "manifest.json"
    manifest = read_json(review_path)
    manifest["outputs"]["existing_15_pair_reaudit.csv"] = sha256(review_dir / "existing_15_pair_reaudit.csv")
    manifest["existing_baseline_isolation_audit"] = {
        "status": status, "all_member_pairs_recomputed": len(pairs),
        "cross_fold_homology_edges": cross_homology,
        "cross_fold_primary_studies": cross_study,
    }
    write_json(review_path, manifest)
    return {"status": status, "molecules": len(ctx["old_ids"]), "observations": len(assays),
            "all_member_pairs_recomputed": len(pairs), "cross_fold_homology_edges": cross_homology,
            "cross_fold_primary_studies": cross_study, "fixed_folds_reused": True,
            "training_performed": False, "blockers": sorted(set(blockers)),
            "pair_audit_sha256": sha256(review_dir / "existing_15_pair_reaudit.csv")}


def render_current_status(state: dict) -> str:
    if state["status"] not in {"mic_expansion_blocked_existing_baseline_preserved",
                                "mic_expansion_blocked_existing_baseline_isolation_failed"} or not state["training_blocked"]:
        raise ValueError("MIC expansion readiness state must remain evidence blocked")
    stamp = pd.Timestamp(state["generated_at"]).tz_convert("Asia/Shanghai").strftime("%Y-%m-%d %H:%M:%S")
    return "\n".join((DOC_START, "## 当前研究状态（机器生成）", "",
        f"状态来源：`{state['state_path']}`。生成时间：{stamp}（Asia/Shanghai）。",
        f"数据版本：`{state['data_version']}`；审查协议：`{state['audit_protocol_id']}`。扩充训练协议及命令：`null`。", "",
        "| 状态 | 当前结论 |", "|---|---|",
        "| 既有 MIC 基线 | protocol-mic-07；15 分子、22 观察；既有探索性训练及独立复核保留 |",
        f"| 本轮新增候选 | {state['new_candidates_reviewed']} 条审查、{state['new_candidates_released']} 条释放；训练释放为 0；训练 `blocked` |",
        f"| 既有基线隔离复核 | `{state['gates']['updated_all_member_study_isolation']}`；全员配对 {state['existing_baseline_isolation_audit']['all_member_pairs_recomputed']}；跨折同源 {state['existing_baseline_isolation_audit']['cross_fold_homology_edges']}；跨折研究 {state['existing_baseline_isolation_audit']['cross_fold_primary_studies']} |",
        f"| 原双任务 | `{state['formal_dual_task_status']}`；protocol-amd-02；正式运行 `{state['formal_run_status']}` |",
        "| 正式结果 / 投稿就绪 | `false` / `false` |", "",
        "历史 Gemini 扩充训练仅作为历史产物；其证据释放声明已撤销，不纳入本状态的当前准入。",
        "未完成的原始证据及隔离事项见机器状态文件 `blockers` 与本版本审查报告。", DOC_END))


def document_patch(state: dict) -> str:
    sections = ["*** Begin Patch"]
    block = render_current_status(state)
    for name in DOCS:
        path = ROOT / name
        before = path.read_text(encoding="utf-8")
        if before.count(START) != 1 or before.count(END) != 1:
            raise ValueError(f"Expected exactly one current status block in {name}")
        left, right = before.index(START), before.index(END) + len(END)
        after = before[:left] + block + before[right:]
        diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm=""))
        if diff:
            sections.append(f"*** Update File: {name}")
            sections.extend("@@" if line.startswith("@@") else line for line in diff[2:])
    sections.append("*** End Patch")
    return "\n".join(sections)


def validate_documents(state: dict) -> None:
    expected = render_current_status(state)
    for name in DOCS:
        body = (ROOT / name).read_text(encoding="utf-8")
        if body.count(DOC_START) != 1 or body.count(DOC_END) != 1:
            raise ValueError(f"Status marker missing or duplicated: {name}")
        block = body[body.index(DOC_START):body.index(DOC_END) + len(DOC_END)]
        if block != expected:
            raise ValueError(f"Current status block differs from v17: {name}")


def publish_state(review_dir: Path, output: Path = NEW_STATE) -> dict:
    review_dir, output = review_dir.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite MIC readiness state: {output}")
    review_manifest = verify_manifest(review_dir)
    study_audit = audit_existing_baseline(review_dir)
    state = _updated_state(review_dir, review_manifest, study_audit)
    state["state_path"] = output.relative_to(ROOT).as_posix()
    if STATE18.exists():
        state["supersedes"] = STATE18.relative_to(ROOT).as_posix()
    elif STATE17.exists():
        state["supersedes"] = STATE17.relative_to(ROOT).as_posix()
    state["inputs"] = {
        str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path)
        for path in (review_dir / "manifest.json", review_dir / "new_candidate_review.csv",
                     review_dir / "existing_15_pair_reaudit.csv", STATE16, FORMAL,
                     OLD_RELEASE_PROTOCOL, OLD_RELEASE_FREEZE, OLD_RELEASE_ENTRY, Path(__file__),
                     ROOT / "02_code/train_mic_reviewed_baseline.py",
                     ROOT / "02_code/tests/test_mic_reviewed_training.py",
                     ROOT / "docs/superpowers/plans/2026-10-03-mic-evidence-release-and-training.md")
    }
    state["inputs"][str(Path("02_code/research_evidence_gate.py"))] = sha256(ROOT / "02_code/research_evidence_gate.py")
    if state["supersedes"] == STATE18.relative_to(ROOT).as_posix():
        state["inputs"][STATE18.relative_to(ROOT).as_posix()] = sha256(STATE18)
    if study_audit["status"] != "passed_existing_15_historical_partition_preserved":
        state["status"] = "mic_expansion_blocked_existing_baseline_isolation_failed"
        state["dataset_preparation_status"] = "blocked"
        state["blockers"].append("Corrected source aliases conflict with the certified 15-molecule fold roles.")
    write_json(output, state)
    return state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("review"); p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p = subs.add_parser("prepare"); p.add_argument("--review", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    p = subs.add_parser("state"); p.add_argument("--review", type=Path, required=True); p.add_argument("--output", type=Path, default=NEW_STATE)
    args = parser.parse_args()
    if args.command == "review": result = review(args.output)
    elif args.command == "prepare": result = prepare(args.review, args.output)
    else: result = publish_state(args.review, args.output)
    print(json.dumps({k: result[k] for k in result if k in
                      {"status", "generated_at", "candidate_molecules", "candidate_observations",
                       "new_candidates_reviewed", "new_candidates_released", "blockers"}}, ensure_ascii=False, indent=2))
