"""Independently recompute the extended candidate audit; never authorize training."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from audit_mic_reviewed_subset_ludwig import verify
from research_utils import ROOT, sha256, utc_now, write_json
from validate_mic_acid_progress import independent_identity, rows

COHORT = ROOT / "03_experiments/audits/mic_extended_acid_cohort_20261002_v1"
SOURCES = ROOT / "03_experiments/audits/mic_independent_sources_review_20261002_v1"
READY = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v9.json"
DOCS = ("README.md", "docs/REMEDIATION_STATUS.md", "docs/DOCUMENTATION_INDEX.md",
        "docs/handoff/TASK_STATE.md", "03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md")
GENERATORS = {"mic_confirmed_acid_subset_20261002_v1": "audit_mic_confirmed_acid_subset.py",
              SOURCES.name: "audit_mic_independent_sources.py", COHORT.name: "audit_mic_extended_acid_cohort.py"}


def check(condition: bool, message: str):
    if not condition:
        raise ValueError(message)


def validate(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite validation: {output}")
    manifest, source = verify(COHORT), verify(SOURCES)
    frozen = ("mic_confirmed_acid_subset_20261002_v1", "mic_reviewed_subset_groups_20261002_v3",
              "mic_candidate_release_review_20261002_v1", "mic_primary_review_pmid33790103_20261002_v2",
              "mic_primary_review_pmid32344933_20261002_v2", "mic_primary_review_pmid35735615_20261002_v1")
    for name in frozen:
        record = verify(ROOT / "03_experiments/audits" / name)
        if name in GENERATORS:
            check(record["script_sha256"] == sha256(ROOT / "02_code" / GENERATORS[name]), f"Frozen generator changed: {name}")
    for directory, record in ((COHORT, manifest), (SOURCES, source)):
        check(record["script_sha256"] == sha256(ROOT / "02_code" / GENERATORS[directory.name]), "Generator changed")
    ready = json.loads(READY.read_text(encoding="utf-8"))
    for path, digest in ready["inputs"].items():
        check(sha256(ROOT / path) == digest, f"Readiness input changed: {path}")
    check(ready["script_sha256"] == sha256(ROOT / "02_code/audit_mic_extended_acid_cohort.py"), "Readiness generator changed")
    molecules, assays = rows(COHORT / "candidate_molecules.csv"), rows(COHORT / "candidate_observations.csv")
    pairs, stored_summary = rows(COHORT / "all_member_similarity.csv"), rows(COHORT / "component_summary.csv")
    sequences = {row["sample_id"]: row["seq"] for row in molecules}
    labels = {row["sample_id"]: int(row["amp"]) for row in molecules}
    check(len(sequences) == len(set(sequences.values())) == len(molecules) == 15, "Exact duplicates or wrong inventory")
    check(len(assays) == 22 and {row["sample_id"] for row in assays} == set(sequences), "Incomplete observation inventory")
    check(all(10 <= len(seq) <= 50 and set(seq) <= set("ACDEFGHIKLMNPQRSTVWY") for seq in sequences.values()), "Domain violation")
    # Independent implementation of the frozen rounded average mass table, not the label helper.
    masses = dict(zip("ACDEFGHIKLMNPQRSTVWY", (89.09,121.16,133.10,147.13,165.19,75.07,155.16,131.18,
                                              146.19,131.18,149.21,132.12,115.13,146.15,174.20,105.09,
                                              119.12,117.15,204.23,181.19)))
    for row in assays:
        sequence = sequences[row["sample_id"]]
        raw = row["raw_mic"].strip()
        censored = raw.startswith(">")
        number = float(raw.removeprefix(">").removeprefix("="))
        if row["raw_unit"] == "µM":
            factor = (sum(masses[aa] for aa in sequence) - 18.0152 * (len(sequence)-1)) / 1000
        else:
            check(row["raw_unit"].lower() in {"µg/ml", "μg/ml"}, "Unsupported audit unit")
            factor = 1
        low, high = number * factor, math.inf if censored else number * factor
        expected = 1 if high <= 32 else (0 if low >= 128 else None)
        check(expected is not None and expected == int(row["derived_label"]) == labels[row["sample_id"]], "Observation label mismatch")
        check(math.isclose(float(row["normalized_low_ug_ml"]), low, abs_tol=1e-10), "Lower bound mismatch")
        check(float(row["normalized_high_ug_ml"]) == high, "Upper bound mismatch")
        check(row["target"].startswith("Escherichia coli ") and bool(row["assay_study_ids"]), "Missing target/study")
        check(hashlib.sha256(sequence.encode("ascii")).hexdigest()[:24] == row["sample_id"], "Molecule ID mismatch")
    expected_pairs = {frozenset(ids) for ids in itertools.combinations(sequences, 2)}
    actual_pairs = {frozenset((row["sample_id_a"], row["sample_id_b"])) for row in pairs}
    check(len(pairs) == len(actual_pairs) == len(expected_pairs) == 105 and actual_pairs == expected_pairs, "Missing/duplicate all-member pair")
    graph, edge_count = {sample: set() for sample in sequences}, 0
    for row in pairs:
        a, b = row["sample_id_a"], row["sample_id_b"]
        identity = independent_identity(sequences[a], sequences[b])
        edge = identity >= 0.40
        check(abs(identity-float(row["identity"])) < 1e-12 and edge == (row["homology_edge"] == "True"), "Full-matrix identity mismatch")
        if edge:
            graph[a].add(b)
            graph[b].add(a)
            edge_count += 1
    studies = {row["sample_id"]: set(row["study_ids"].split("|")) for row in molecules}
    for row in assays:
        studies[row["sample_id"]].update(row["assay_study_ids"].split("|"))
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
    check({frozenset(c) for c in components} == {frozenset(c) for c in saved_groups.values()}, "Paper/member components mismatch")
    summaries = sorted((len(c), sum(labels[x] == 1 for x in c), sum(labels[x] == 0 for x in c)) for c in components)
    check(summaries == sorted((int(r["molecules"]),int(r["positives"]),int(r["negatives"])) for r in stored_summary), "Component summary mismatch")
    pos, neg = sum(c[1] > 0 for c in summaries), sum(c[2] > 0 for c in summaries)
    check((len(components),pos,neg,edge_count) == (6,3,6,11), "Unexpected extended component counts")
    check(ready["candidate_class_counts"] == {"0":11,"1":4}, "Readiness classes mismatch")
    check((ready["candidate_combined_components"],ready["candidate_positive_bearing_components"],
           ready["candidate_negative_bearing_components"]) == (6,3,6), "Readiness graph mismatch")
    new_assays = rows(SOURCES / "candidate_assays.csv")
    decisions = rows(SOURCES / "record_decisions.csv")
    selected = [row for row in decisions if row["decision"] == "local_fields_confirmed_not_training_released"]
    check(len(selected) == 4 and len(new_assays) == 6 and len(decisions) == 70, "Source inventory mismatch")
    check(set(row["record_id"] for row in selected) == set(row["record_id"] for row in new_assays), "Candidate not selected by source audit")
    check(all(row["training_release"] == "False" for row in decisions), "Unreviewed training release")
    for row in rows(SOURCES / "source_inventory.csv"):
        path = ROOT / "03_experiments/audits/mic_independent_sources_20261002_v1/raw" / row["primary_file"]
        root = ET.parse(path).getroot()
        check(root.find(".//body") is not None and sha256(path) == row["sha256"], "Primary source incomplete or changed")
    check(rows(COHORT / "fold_assignments.csv") == [], "Impossible fold set generated")
    check(ready["status"] == "blocked" and ready["training_started"] is False
          and ready["records_released_for_training"] == 0 and ready["training_protocol_id"] is None
          and ready["training_command"] is None, "Scientific release unexpectedly changed")
    gate = ready["gates"]["candidate_structure"]
    check((gate["folds_required"],gate["seed"],gate["cutoff"]) == (5,42,0.40)
          and gate["status"] == "blocked" and gate["folds_generated"] is False
          and gate["cross_fold_homology_edges"] is None and gate["cross_fold_primary_studies"] is None, "Fold gate mismatch")
    formal_hash = sha256(ROOT / "04_paper/research_status.json")
    check(formal_hash == "846c1fc2452646f3df9c2055b0a4a1b5140132acc2433bb2c304b133b6e8012c", "Formal dual-task state changed")
    stamp = datetime.fromisoformat(ready["generated_at"]).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    for name in DOCS:
        content = (ROOT / name).read_text(encoding="utf-8")
        check(all(token in content for token in (READY.name, stamp, COHORT.name, "protocol-mic-01")), f"Document state mismatch: {name}")
        check("最新机器声明 v8" not in content and "最新机器状态 v8" not in content, f"Stale current claim: {name}")
    result = {"status": "validation_passed_research_still_blocked", "generated_at": utc_now(),
              "independently_recomputed_pairs": len(pairs), "independently_rederived_observations": len(assays),
              "combined_components": len(components), "positive_bearing_components": pos, "negative_bearing_components": neg,
              "homology_edges": edge_count, "primary_sources_verified": 10, "source_decisions_verified": len(decisions),
              "historical_frozen_manifests_verified": len(frozen), "current_state_documents_verified": len(DOCS),
              "formal_status_unchanged": True, "training_started": False, "script_sha256": sha256(Path(__file__)),
              "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in (READY, COHORT / "manifest.json", SOURCES / "manifest.json",
                          ROOT / "02_code/validate_mic_acid_progress.py", *[ROOT / name for name in DOCS])}}
    write_json(output, result)
    output.with_suffix(".md").write_text(
        "# 新来源合并进展的独立复核\n\n"
        "独立完整矩阵/回溯重算 105 对，独立重推导 22 条测定标签与单位转换；研究/同源图及所有组件匹配。"
        "10 篇原始 XML、70 项来源决定、6 个历史冻结清单与 5 份当前状态文档哈希复核通过。"
        "当前含阳性 3、含阴性 6 个组件；无有效五折，跨折检查保持 null。\n\n"
        "本结果是审计软件和来源绑定验证，不是训练许可或模型性能。训练未开始，完整证据释放仍待完成，科研状态 blocked。\n",
        encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(validate(parser.parse_args().output), indent=2))
