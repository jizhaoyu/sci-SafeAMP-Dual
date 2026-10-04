"""Audit the prospectively frozen three-fold amendment; never release training."""
from __future__ import annotations

import argparse
import itertools
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from audit_mic_reviewed_subset_hirsch import DisjointSet
from audit_mic_reviewed_subset_ludwig import verify
from public_data import measurement_label
from research_data import sequence_identity
from research_utils import ROOT, sha256, utc_now, write_json

BASE = ROOT / "03_experiments/audits/mic_extended_acid_cohort_20261002_v1"
PREVIOUS = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v9.json"
PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-06.json"
FREEZE = ROOT / "03_experiments/audits/protocol_mic_06_freeze_20261002_v1.json"
EXPECTED_PROTOCOL_SHA = "5303817532e1b8b0fc3670e2110594ccb4d13aec6af314425a3879efe3441f44"


def load_protocol() -> dict:
    if sha256(PROTOCOL) != EXPECTED_PROTOCOL_SHA:
        raise ValueError("Frozen three-fold protocol changed.")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    parent = ROOT / protocol["parent_protocol_path"]
    if (sha256(parent) != protocol["parent_protocol_file_sha256"]
            or freeze["protocol_file_sha256"] != EXPECTED_PROTOCOL_SHA
            or freeze["three_fold_audit_started"] is not False
            or freeze["model_training_started"] is not False
            or datetime.fromisoformat(freeze["frozen_at"]) >= datetime.fromisoformat(utc_now())):
        raise ValueError("Missing prospective protocol freeze or changed parent.")
    previous = json.loads(parent.read_text(encoding="utf-8"))
    for key in ("task", "target_organism", "assay_endpoint", "raw_measurement_normalization", "label_rule",
                "molecule_domain", "evidence_requirements", "duplicate_policy", "similarity"):
        if protocol[key] != previous[key]:
            raise ValueError(f"Scientific field changed beyond authorized fold amendment: {key}")
    for key, value in previous["validation"].items():
        if key != "folds" and protocol["validation"][key] != value:
            raise ValueError(f"Validation field changed beyond folds: {key}")
    if (protocol["validation"]["folds"], protocol["validation"]["seed"], protocol["validation"]["shuffle"]) != (3, 42, True):
        raise ValueError("Unexpected fixed three-fold design.")
    context = protocol["design_context"]
    if (sha256(ROOT / context["candidate_cohort_manifest"]) != context["candidate_cohort_manifest_sha256"]
            or sha256(PREVIOUS) != context["previous_readiness_sha256"]):
        raise ValueError("Pre-amendment cohort or state changed.")
    return protocol


def run(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite three-fold audit: {output}")
    protocol = load_protocol()
    base = verify(BASE)
    if base["script_sha256"] != sha256(ROOT / "02_code/audit_mic_extended_acid_cohort.py"):
        raise ValueError("Frozen source generator changed.")
    molecules = pd.read_csv(BASE / "candidate_molecules.csv", keep_default_na=False)
    observations = pd.read_csv(BASE / "candidate_observations.csv", keep_default_na=False)
    sequences, labels = molecules.set_index("sample_id").seq.to_dict(), molecules.set_index("sample_id").amp.to_dict()
    if (len(molecules) != base["candidate_molecules"] or len(observations) != base["candidate_observations"]
            or not molecules.seq.is_unique or not molecules.sample_id.is_unique):
        raise ValueError("Bound cohort inventory changed.")
    for row in observations.itertuples(index=False):
        label = measurement_label({"concentration": row.raw_mic, "unit": {"name": row.raw_unit}}, sequences[row.sample_id], 32, 128)
        if label is None or label != int(row.derived_label) or label != labels[row.sample_id]:
            raise ValueError("Unresolved MIC observation label.")
    groups, pairs = DisjointSet(molecules.sample_id.tolist()), []
    for a, b in itertools.combinations(molecules.itertuples(index=False), 2):
        identity = sequence_identity(a.seq, b.seq, identity_mode="alignment")
        edge = identity >= 0.40
        pairs.append({"sample_id_a": a.sample_id, "sample_id_b": b.sample_id, "identity": identity, "homology_edge": edge})
        if edge:
            groups.union(a.sample_id, b.sample_id)
    studies: dict[str, set[str]] = {}
    for sample, identifiers in [*zip(molecules.sample_id, molecules.study_ids), *zip(observations.sample_id, observations.assay_study_ids)]:
        for identifier in identifiers.split("|"):
            if not identifier:
                raise ValueError("Unresolved study identity.")
            members = studies.setdefault(identifier, set())
            if members:
                groups.union(sample, min(members))
            members.add(sample)
    roots = sorted({groups.find(sample) for sample in molecules.sample_id})
    molecules["review_component"] = molecules.sample_id.map(lambda sample: roots.index(groups.find(sample)))
    summary = molecules.groupby("review_component").agg(molecules=("sample_id", "size"), positives=("amp", "sum"))
    summary["negatives"] = summary.molecules - summary.positives
    positive, negative = int(summary.positives.gt(0).sum()), int(summary.negatives.gt(0).sum())
    blockers = [f"{name}: {count} < 3." for count, name in ((len(summary), "total components"),
                (positive, "positive-bearing components"), (negative, "negative-bearing components")) if count < 3]
    assignments, fold_rows, folds = [], [], []
    if not blockers:
        splitter = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)
        for fold, (train_index, valid_index) in enumerate(splitter.split(molecules.seq, molecules.amp, molecules.review_component)):
            train, valid = molecules.iloc[train_index], molecules.iloc[valid_index]
            both = set(train.amp) == {0, 1} and set(valid.amp) == {0, 1}
            folds.append({"fold": fold, "train_n": len(train), "validation_n": len(valid),
                          "train_positive": int(train.amp.sum()), "train_negative": int(len(train)-train.amp.sum()),
                          "validation_positive": int(valid.amp.sum()), "validation_negative": int(len(valid)-valid.amp.sum()),
                          "both_classes": both})
            if not both:
                blockers.append(f"Fixed seed 42 fold {fold} or its training complement lacks a class.")
            assignments.extend({"sample_id": sample, "fold": fold} for sample in valid.sample_id)
            for role, frame in (("train", train), ("validation", valid)):
                fold_rows.extend({"sample_id": r.sample_id, "amp": int(r.amp), "review_component": int(r.review_component),
                                  "fold": fold, "role": role} for r in frame.itertuples(index=False))
    fold_map = {row["sample_id"]: row["fold"] for row in assignments}
    cross_edges = (sum(r["homology_edge"] and fold_map[r["sample_id_a"]] != fold_map[r["sample_id_b"]] for r in pairs)
                   if assignments else None)
    cross_studies = (sum(len({fold_map[s] for s in members}) > 1 for members in studies.values()) if assignments else None)
    if cross_edges or cross_studies:
        blockers.append("Cross-fold all-member homology or primary-study leakage detected.")
    structure_passed = not blockers
    blockers.append("Full primary-evidence release is incomplete; no separate frozen training protocol exists.")
    output.mkdir(parents=True)
    for name, frame in (("candidate_molecules.csv", molecules), ("candidate_observations.csv", observations),
                        ("all_member_similarity.csv", pd.DataFrame(pairs)), ("component_summary.csv", summary.reset_index()),
                        ("fold_assignments.csv", pd.DataFrame(assignments, columns=["sample_id", "fold"])),
                        ("fold_roles.csv", pd.DataFrame(fold_rows, columns=["sample_id", "amp", "review_component", "fold", "role"]))):
        frame.to_csv(output / name, index=False)
    inputs = [BASE / "manifest.json", PROTOCOL, FREEZE, PREVIOUS, ROOT / "02_code/public_data.py",
              ROOT / "02_code/research_data.py", ROOT / "02_code/audit_mic_reviewed_subset_hirsch.py"]
    report = (
        "# 三折前瞻性修订的固定分区审计\n\n"
        "用户明确授权三折可行性修订；protocol-mic-06 和冻结记录先于本审计保存。"
        "以同一 15 条分子、22 条 MIC 重算，标签、分子域、0.40 全员同源和原始研究分组均保持原规则。\n\n"
        f"全部 {len(pairs)} 对，{len(summary)} 个不可拆分组件（含阳性 {positive}、含阴性 {negative}）。"
        f"固定 StratifiedGroupKFold(3, shuffle=True, seed=42) 分区门禁为 {'passed' if structure_passed else 'blocked'}；"
        "没有搜索 seed 或删样本。\n\n"
        "| 折 | 训练阳性/阴性 | 验证阳性/阴性 | 两类条件 |\n| --- | --- | --- | --- |\n"
        + "".join(f"| {r['fold']} | {r['train_positive']}/{r['train_negative']} | {r['validation_positive']}/{r['validation_negative']} | {r['both_classes']} |\n" for r in folds)
        + f"\n跨折超阈值成员边 {cross_edges}；跨折原始研究 {cross_studies}。"
        "完整原始证据释放仍未完成，新训练协议未冻结，训练释放为 0，总状态 blocked。"
        "小样本三折仅适用于探索，不能用于正式双任务、外部泛化或临床结论。\n\n"
        + "".join(f"- {reason}\n" for reason in blockers)
        + "\n复跑：`python 02_code/audit_mic_three_fold.py --output 03_experiments/audits/mic_three_fold_my_run`；输出必须是新目录。\n")
    (output / "report.md").write_text(report, encoding="utf-8")
    manifest = {"status": "blocked", "generated_at": utc_now(), "audit_protocol_id": "protocol-mic-06",
                "protocol_sha256": sha256(PROTOCOL), "candidate_molecules": len(molecules), "candidate_observations": len(observations),
                "positive_molecules": int(molecules.amp.sum()), "negative_molecules": int(len(molecules)-molecules.amp.sum()),
                "all_member_pairs": len(pairs), "homology_edges": sum(r["homology_edge"] for r in pairs),
                "combined_components": len(summary), "positive_bearing_components": positive, "negative_bearing_components": negative,
                "fold_structure_gate_passed": structure_passed, "folds_generated": bool(assignments), "folds": folds,
                "folds_required": 3, "seed": 42, "cutoff": 0.40, "cross_fold_homology_edges": cross_edges,
                "cross_fold_primary_studies": cross_studies, "blockers": blockers, "records_released_for_training": 0,
                "training_started": False, "script_sha256": sha256(Path(__file__)),
                "inputs": {str(p.relative_to(ROOT)): sha256(p) for p in inputs},
                "outputs": {p.name: sha256(p) for p in output.iterdir() if p.is_file()}}
    write_json(output / "manifest.json", manifest)
    return manifest


def publish(cohort: Path, output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite readiness: {output}")
    load_protocol()
    manifest = verify(cohort)
    if manifest["script_sha256"] != sha256(Path(__file__)) or manifest["protocol_sha256"] != EXPECTED_PROTOCOL_SHA:
        raise ValueError("Frozen three-fold audit changed.")
    previous = json.loads(PREVIOUS.read_text(encoding="utf-8"))
    formal = ROOT / "04_paper/research_status.json"
    if sha256(formal) != previous["formal_status_sha256"]:
        raise ValueError("Formal dual-task state changed.")
    # Carry historical provenance, then replace every active gate with this amendment's actual result.
    result = {k: previous[k] for k in ("withdrawn_historical_training", "historical_unreleased_candidate_structure",
                                     "historical_evidence_conflicts", "paper_audits", "additional_source_reviews")}
    gate = {"status": "passed" if manifest["fold_structure_gate_passed"] else "blocked", "folds_required": 3,
            "seed": 42, "cutoff": 0.40, "folds_generated": manifest["folds_generated"], "folds": manifest["folds"],
            "cross_fold_homology_edges": manifest["cross_fold_homology_edges"],
            "cross_fold_primary_studies": manifest["cross_fold_primary_studies"]}
    result.update(schema_version=2, status="blocked", generated_at=utc_now(), supersedes=str(PREVIOUS.relative_to(ROOT)),
                  scope="small-sample three-fold MIC-only feasibility; full evidence release incomplete",
                  audit_protocol_id="protocol-mic-06", audit_protocol_path=str(PROTOCOL.relative_to(ROOT)), audit_protocol_sha256=sha256(PROTOCOL),
                  training_protocol_id=None, training_protocol_status="pending_new_immutable_protocol",
                  candidate_cohort_version=cohort.name, candidate_cohort_manifest=str((cohort / "manifest.json").relative_to(ROOT)),
                  candidate_cohort_manifest_sha256=sha256(cohort / "manifest.json"), candidate_molecules=manifest["candidate_molecules"],
                  candidate_observations=manifest["candidate_observations"],
                  candidate_class_counts={"0": manifest["negative_molecules"], "1": manifest["positive_molecules"]},
                  candidate_all_member_pairs=manifest["all_member_pairs"], candidate_homology_edges=manifest["homology_edges"],
                  candidate_combined_components=manifest["combined_components"],
                  candidate_positive_bearing_components=manifest["positive_bearing_components"],
                  candidate_negative_bearing_components=manifest["negative_bearing_components"],
                  gates={"candidate_structure": gate, "primary_evidence_release": previous["gates"]["primary_evidence_release"],
                         "final_admitted_cohort": {"status": "pending_full_release_review"},
                         "training_protocol": {"status": "pending_new_immutable_protocol"}},
                  historical_five_fold_state={"state": str(PREVIOUS.relative_to(ROOT)), "sha256": sha256(PREVIOUS),
                                             "status": "blocked", "applicable_to_three_fold_amendment": False},
                  blockers=manifest["blockers"], records_released_for_training=0, training_started=False, training_command=None,
                  formal_dual_task_status="blocked", formal_status_generated_at=previous["formal_status_generated_at"],
                  formal_status_sha256=sha256(formal), formal_results_available=False, publication_ready=False,
                  script_sha256=sha256(Path(__file__)),
                  inputs={str(p.relative_to(ROOT)): sha256(p) for p in (cohort / "manifest.json", PROTOCOL, FREEZE, PREVIOUS, formal)})
    write_json(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--publish-state", type=Path)
    args = parser.parse_args()
    result = publish(args.output.resolve(), args.publish_state) if args.publish_state else run(args.output)
    print(json.dumps({k: result[k] for k in ("status", "generated_at", "candidate_molecules", "candidate_observations", "blockers")}, indent=2))
