"""Independently verify the three-fold amendment, partitions and blocked release state."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from audit_mic_reviewed_subset_ludwig import verify
from research_utils import ROOT, sha256, utc_now, write_json
from validate_mic_acid_progress import independent_identity, rows

COHORT = ROOT / "03_experiments/audits/mic_three_fold_20261002_v1"
BASE = ROOT / "03_experiments/audits/mic_extended_acid_cohort_20261002_v1"
SOURCES = ROOT / "03_experiments/audits/mic_independent_sources_review_20261002_v1"
READY = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v10.json"
PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-06.json"
FREEZE = ROOT / "03_experiments/audits/protocol_mic_06_freeze_20261002_v1.json"
DOCS = ("README.md", "docs/REMEDIATION_STATUS.md", "docs/DOCUMENTATION_INDEX.md",
        "docs/handoff/TASK_STATE.md", "03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md")
GENERATORS = {
    COHORT.name: "audit_mic_three_fold.py",
    BASE.name: "audit_mic_extended_acid_cohort.py",
    SOURCES.name: "audit_mic_independent_sources.py",
    "mic_confirmed_acid_subset_20261002_v1": "audit_mic_confirmed_acid_subset.py",
}
EXPECTED_PROTOCOL_SHA = "5303817532e1b8b0fc3670e2110594ccb4d13aec6af314425a3879efe3441f44"
EXPECTED_FORMAL_SHA = "846c1fc2452646f3df9c2055b0a4a1b5140132acc2433bb2c304b133b6e8012c"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(output: Path) -> dict:
    output = output.resolve()
    report = output.with_suffix(".md")
    if output.exists() or report.exists():
        raise FileExistsError(f"Refusing to overwrite validation: {output}")
    manifest, base, source = verify(COHORT), verify(BASE), verify(SOURCES)
    frozen_names = (
        "mic_confirmed_acid_subset_20261002_v1", "mic_reviewed_subset_groups_20261002_v3",
        "mic_candidate_release_review_20261002_v1", "mic_primary_review_pmid33790103_20261002_v2",
        "mic_primary_review_pmid32344933_20261002_v2", "mic_primary_review_pmid35735615_20261002_v1",
    )
    for name in frozen_names:
        record = verify(ROOT / "03_experiments/audits" / name)
        if name in GENERATORS:
            check(record["script_sha256"] == sha256(ROOT / "02_code" / GENERATORS[name]), f"Generator changed: {name}")
    for directory, record in ((COHORT, manifest), (BASE, base), (SOURCES, source)):
        check(record["script_sha256"] == sha256(ROOT / "02_code" / GENERATORS[directory.name]), "Frozen generator changed")
    ready = json.loads(READY.read_text(encoding="utf-8"))
    for name, digest in ready["inputs"].items():
        check(sha256(ROOT / name) == digest, f"Readiness input changed: {name}")
    check(ready["script_sha256"] == manifest["script_sha256"], "Readiness generator mismatch")

    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    parent_path = ROOT / protocol["parent_protocol_path"]
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    check(sha256(PROTOCOL) == EXPECTED_PROTOCOL_SHA == manifest["protocol_sha256"]
          == ready["audit_protocol_sha256"] == freeze["protocol_file_sha256"], "Protocol checksum mismatch")
    check(sha256(parent_path) == protocol["parent_protocol_file_sha256"], "Parent protocol changed")
    amendment = ROOT / "docs/amendments/PROTOCOL_MIC_06_THREE_FOLD.md"
    check(sha256(amendment) == freeze["amendment_document_sha256"], "Frozen amendment changed")
    check(datetime.fromisoformat(freeze["frozen_at"]) < datetime.fromisoformat(manifest["generated_at"])
          < datetime.fromisoformat(ready["generated_at"]), "Protocol was not frozen before the audit")
    check(freeze["user_authorized_prospective_revision"] is True
          and freeze["three_fold_audit_started"] is False and freeze["model_training_started"] is False,
          "Missing prospective authorization record")
    for key in ("task", "target_organism", "assay_endpoint", "raw_measurement_normalization", "label_rule",
                "molecule_domain", "evidence_requirements", "duplicate_policy", "similarity"):
        check(protocol[key] == parent[key], f"Scientific field changed: {key}")
    for key, value in parent["validation"].items():
        if key != "folds":
            check(protocol["validation"][key] == value, f"Validation field changed: {key}")
    check((protocol["validation"]["folds"], protocol["validation"]["seed"], protocol["validation"]["shuffle"])
          == (3, 42, True), "Unexpected three-fold design")
    context = protocol["design_context"]
    check(context["model_performance_used_to_choose_design"] is False
          and context["candidate_selection_after_split"] == "forbidden", "Outcome-informed redesign")
    for path_key, hash_key in (("candidate_cohort_manifest", "candidate_cohort_manifest_sha256"),
                               ("previous_readiness", "previous_readiness_sha256")):
        check(sha256(ROOT / context[path_key]) == context[hash_key], "Pre-amendment input changed")

    molecules, assays = rows(COHORT / "candidate_molecules.csv"), rows(COHORT / "candidate_observations.csv")
    old_molecules = rows(BASE / "candidate_molecules.csv")
    without_groups = lambda data: [{key: value for key, value in row.items() if key != "review_component"} for row in data]
    check(without_groups(molecules) == without_groups(old_molecules), "Molecules or labels changed after amendment")
    old_assays = rows(BASE / "candidate_observations.csv")
    check(len(assays) == len(old_assays), "Observation selection changed after amendment")
    numeric_bounds = {"normalized_low_ug_ml", "normalized_high_ug_ml"}
    for current, previous in zip(assays, old_assays):
        # pandas CSV round trips shortened two 400.42361744000004 bounds to 400.42361744.
        # All raw evidence fields remain exact; only normalized floating-point text may differ.
        check({k: v for k, v in current.items() if k not in numeric_bounds}
              == {k: v for k, v in previous.items() if k not in numeric_bounds}, "Raw observation changed after amendment")
        check(all(math.isclose(float(current[k]), float(previous[k]), rel_tol=0, abs_tol=1e-12)
                  for k in numeric_bounds), "Normalized observation changed after amendment")
    sequences = {row["sample_id"]: row["seq"] for row in molecules}
    labels = {row["sample_id"]: int(row["amp"]) for row in molecules}
    check(len(sequences) == len(set(sequences.values())) == len(molecules) == 15, "Wrong molecule inventory")
    check(len(assays) == 22 and {row["sample_id"] for row in assays} == set(sequences), "Incomplete assay inventory")
    check(all(10 <= len(seq) <= 50 and set(seq) <= set("ACDEFGHIKLMNPQRSTVWY") for seq in sequences.values()), "Domain violation")
    masses = dict(zip("ACDEFGHIKLMNPQRSTVWY", (89.09,121.16,133.10,147.13,165.19,75.07,155.16,131.18,
                                              146.19,131.18,149.21,132.12,115.13,146.15,174.20,105.09,
                                              119.12,117.15,204.23,181.19)))
    for row in assays:
        seq = sequences[row["sample_id"]]
        raw = row["raw_mic"].strip()
        number = float(raw.removeprefix(">").removeprefix("="))
        if row["raw_unit"] == "µM":
            factor = (sum(masses[aa] for aa in seq) - 18.0152 * (len(seq) - 1)) / 1000
        else:
            check(row["raw_unit"].lower() in {"µg/ml", "μg/ml"}, "Unsupported unit")
            factor = 1
        low, high = number * factor, math.inf if raw.startswith(">") else number * factor
        expected = 1 if high <= 32 else (0 if low >= 128 else None)
        check(expected is not None and expected == int(row["derived_label"]) == labels[row["sample_id"]], "MIC label mismatch")
        check(math.isclose(float(row["normalized_low_ug_ml"]), low, abs_tol=1e-10)
              and float(row["normalized_high_ug_ml"]) == high, "MIC bounds mismatch")
        check(row["target"].startswith("Escherichia coli ") and bool(row["assay_study_ids"]), "Missing target or study")
        check(hashlib.sha256(seq.encode("ascii")).hexdigest()[:24] == row["sample_id"], "Sequence ID mismatch")

    pairs = rows(COHORT / "all_member_similarity.csv")
    expected_pairs = {frozenset(ids) for ids in itertools.combinations(sequences, 2)}
    actual_pairs = {frozenset((row["sample_id_a"], row["sample_id_b"])) for row in pairs}
    check(len(pairs) == len(actual_pairs) == len(expected_pairs) == 105 and actual_pairs == expected_pairs, "Incomplete pair matrix")
    graph, homology = {sample: set() for sample in sequences}, []
    for row in pairs:
        a, b = row["sample_id_a"], row["sample_id_b"]
        identity = independent_identity(sequences[a], sequences[b])
        edge = identity >= 0.40
        check(abs(identity - float(row["identity"])) < 1e-12 and edge == (row["homology_edge"] == "True"), "Full-matrix identity mismatch")
        if edge:
            graph[a].add(b)
            graph[b].add(a)
            homology.append((a, b))
    studies = {row["sample_id"]: set(row["study_ids"].split("|")) for row in molecules}
    for row in assays:
        studies[row["sample_id"]].update(row["assay_study_ids"].split("|"))
    check(all(ids and "" not in ids for ids in studies.values()), "Unresolved primary-study identifier")
    for a, b in itertools.combinations(sequences, 2):
        if studies[a] & studies[b]:
            graph[a].add(b)
            graph[b].add(a)
    unseen, components = set(sequences), []
    while unseen:
        reached, stack = set(), [min(unseen)]
        while stack:
            sample = stack.pop()
            if sample not in reached:
                reached.add(sample)
                stack.extend(graph[sample] - reached)
        unseen -= reached
        components.append(reached)
    saved_groups = {}
    for row in molecules:
        saved_groups.setdefault(row["review_component"], set()).add(row["sample_id"])
    check({frozenset(c) for c in components} == {frozenset(c) for c in saved_groups.values()}, "Member/study components mismatch")
    summaries = sorted((len(c), sum(labels[x] == 1 for x in c), sum(labels[x] == 0 for x in c)) for c in components)
    stored = rows(COHORT / "component_summary.csv")
    check(summaries == sorted((int(r["molecules"]), int(r["positives"]), int(r["negatives"])) for r in stored), "Component summary mismatch")
    pos, neg = sum(c[1] > 0 for c in summaries), sum(c[2] > 0 for c in summaries)
    check((len(components), pos, neg, len(homology)) == (6, 3, 6, 11), "Unexpected graph counts")

    assignments, roles = rows(COHORT / "fold_assignments.csv"), rows(COHORT / "fold_roles.csv")
    fold_for = {row["sample_id"]: int(row["fold"]) for row in assignments}
    check(len(assignments) == len(fold_for) == 15 and set(fold_for) == set(sequences)
          and set(fold_for.values()) == {0, 1, 2}, "Missing or duplicate validation assignment")
    check(len(roles) == 45 and len({(r["sample_id"], r["fold"]) for r in roles}) == 45, "Missing or duplicate fold role")
    groups_by_id = {row["sample_id"]: row["review_component"] for row in molecules}
    expected_counts = []
    for fold in range(3):
        selected = [r for r in roles if int(r["fold"]) == fold]
        check(len(selected) == 15 and {r["sample_id"] for r in selected} == set(sequences), "Incomplete training complement")
        for row in selected:
            sample = row["sample_id"]
            check(row["role"] == ("validation" if fold_for[sample] == fold else "train")
                  and int(row["amp"]) == labels[sample]
                  and row["review_component"] == groups_by_id[sample], "Fold role mismatch")
        train = [x for x in sequences if fold_for[x] != fold]
        valid = [x for x in sequences if fold_for[x] == fold]
        check({labels[x] for x in train} == {0, 1} and {labels[x] for x in valid} == {0, 1}, "Fold missing a class")
        expected_counts.append({"fold": fold, "train_n": len(train), "validation_n": len(valid),
                                "train_positive": sum(labels[x] == 1 for x in train),
                                "train_negative": sum(labels[x] == 0 for x in train),
                                "validation_positive": sum(labels[x] == 1 for x in valid),
                                "validation_negative": sum(labels[x] == 0 for x in valid), "both_classes": True})
    check(all(len({fold_for[x] for x in c}) == 1 for c in components), "Component split across folds")
    cross_edges = sum(fold_for[a] != fold_for[b] for a, b in homology)
    all_studies = set().union(*studies.values())
    cross_studies = sum(len({fold_for[x] for x in studies if study in studies[x]}) > 1 for study in all_studies)
    check(cross_edges == cross_studies == 0, "Cross-fold member or primary-study leakage")
    ids = [row["sample_id"] for row in molecules]
    splitter = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)
    recomputed = {}
    for fold, (_, validation) in enumerate(splitter.split(np.zeros((15, 1)), [labels[x] for x in ids],
                                                         [int(groups_by_id[x]) for x in ids])):
        recomputed.update({ids[index]: fold for index in validation})
    check(recomputed == fold_for, "Fixed seed partition mismatch")
    check(manifest["folds"] == expected_counts and manifest["fold_structure_gate_passed"] is True
          and manifest["cross_fold_homology_edges"] == manifest["cross_fold_primary_studies"] == 0,
          "Partition manifest mismatch")
    gate = ready["gates"]["candidate_structure"]
    check(gate["status"] == "passed" and (gate["folds_required"], gate["seed"], gate["cutoff"]) == (3, 42, 0.40)
          and gate["folds_generated"] is True and gate["folds"] == expected_counts
          and gate["cross_fold_homology_edges"] == gate["cross_fold_primary_studies"] == 0, "Readiness partition gate mismatch")
    check(ready["candidate_class_counts"] == {"0": 11, "1": 4}
          and (ready["candidate_combined_components"], ready["candidate_positive_bearing_components"],
               ready["candidate_negative_bearing_components"]) == (6, 3, 6), "Readiness cohort mismatch")
    check(ready["gates"]["primary_evidence_release"]["status"] == "blocked"
          and ready["gates"]["primary_evidence_release"]["full_release_review_complete"] is False
          and ready["status"] == "blocked" and ready["records_released_for_training"] == 0
          and ready["training_started"] is False and ready["training_protocol_id"] is None
          and ready["training_command"] is None, "Incomplete evidence unexpectedly authorized training")

    decisions = rows(SOURCES / "record_decisions.csv")
    selected = [r for r in decisions if r["decision"] == "local_fields_confirmed_not_training_released"]
    new_assays = rows(SOURCES / "candidate_assays.csv")
    check(len(decisions) == 70 and len(selected) == 4 and len(new_assays) == 6
          and {r["record_id"] for r in selected} == {r["record_id"] for r in new_assays}
          and all(r["training_release"] == "False" for r in decisions), "Source selection/release mismatch")
    inventory = rows(SOURCES / "source_inventory.csv")
    check(len(inventory) == 10, "Source inventory count mismatch")
    for row in inventory:
        path = ROOT / "03_experiments/audits/mic_independent_sources_20261002_v1/raw" / row["primary_file"]
        check(ET.parse(path).getroot().find(".//body") is not None and sha256(path) == row["sha256"], "Changed or incomplete primary XML")
    check(sha256(ROOT / "04_paper/research_status.json") == EXPECTED_FORMAL_SHA, "Formal dual-task state changed")
    stamp = datetime.fromisoformat(ready["generated_at"]).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    for name in DOCS:
        content = (ROOT / name).read_text(encoding="utf-8")
        check(all(token in content for token in (READY.name, stamp, COHORT.name, "protocol-mic-06")), f"Document state mismatch: {name}")
        check("最新机器声明 v9" not in content and "最新机器状态 v9" not in content, f"Stale current claim: {name}")
    paths = (READY, COHORT / "manifest.json", BASE / "manifest.json", SOURCES / "manifest.json", PROTOCOL, FREEZE,
             amendment, ROOT / "02_code/validate_mic_acid_progress.py", *[ROOT / name for name in DOCS])
    result = {"status": "three_fold_validation_passed_evidence_release_still_blocked", "generated_at": utc_now(),
              "audit_protocol_id": protocol["protocol_id"], "cohort_version": COHORT.name,
              "independently_recomputed_pairs": 105, "independently_rederived_observations": 22,
              "fold_roles_verified": 45, "folds": expected_counts, "cross_fold_homology_edges": cross_edges,
              "cross_fold_primary_studies": cross_studies, "combined_components": 6,
              "positive_bearing_components": pos, "negative_bearing_components": neg,
              "primary_sources_verified": 10, "source_decisions_verified": 70,
              "historical_frozen_manifests_verified": len(frozen_names), "current_state_documents_verified": len(DOCS),
              "formal_status_unchanged": True, "training_started": False, "records_released_for_training": 0,
              "script_sha256": sha256(Path(__file__)),
              "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
              "limitations": ["This independently checks audit arithmetic and partitions, not complete primary-evidence release.",
                              "Each validation fold has only one or two positive molecules; no performance or clinical claim is authorized."]}
    write_json(output, result)
    report.write_text("# 三折前瞻性修订独立复核\n\n"
                      "协议冻结早于首次分区。相同 15 条分子、22 条测定保持原样；独立全矩阵回溯重算 105 对，"
                      "重推导 22 条标签/单位，并复核 45 条训练/验证角色和固定 seed 42 的三折分区。"
                      "每折训练与验证均含两类，跨折同源边和原始研究均为 0。\n\n"
                      "10 篇原始 XML、70 项决定、6 个历史冻结清单与 5 份当前状态文档复核通过。"
                      "分区门禁 passed；完整证据释放仍 blocked，训练释放 0，新训练协议待冻结，未训练。"
                      "原正式双任务状态哈希保持不变。每折仅 1–2 条验证阳性，适用范围为小样本探索。\n",
                      encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    result = validate(parser.parse_args().output)
    print(json.dumps({key: result[key] for key in ("status", "generated_at", "independently_recomputed_pairs",
                                                  "fold_roles_verified", "cross_fold_homology_edges",
                                                  "cross_fold_primary_studies")}, ensure_ascii=True, indent=2))
