"""Independently check the filtered candidate audit, immutable hashes and current documents."""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from audit_mic_reviewed_subset_ludwig import verify
from research_utils import ROOT, sha256, utc_now, write_json


COHORT = ROOT / "03_experiments/audits/mic_confirmed_acid_subset_20261002_v1"
READY = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v8.json"
DOCS = ("README.md", "docs/REMEDIATION_STATUS.md", "docs/DOCUMENTATION_INDEX.md",
        "docs/handoff/TASK_STATE.md", "03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md")


def rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def independent_identity(first: str, second: str) -> float:
    """Full score matrix and explicit traceback, independent of the production rolling DP."""
    first, second = sorted((first, second))
    n, m = len(first), len(second)
    scores = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        scores[i][0] = -2 * i
    for j in range(m + 1):
        scores[0][j] = -2 * j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            scores[i][j] = max(scores[i - 1][j - 1] + (2 if first[i - 1] == second[j - 1] else -1),
                               scores[i - 1][j] - 2, scores[i][j - 1] - 2)
    i, j, matches, columns = n, m, 0, 0
    while i or j:
        columns += 1
        if i and j and scores[i][j] == scores[i - 1][j - 1] + (2 if first[i - 1] == second[j - 1] else -1):
            matches += int(first[i - 1] == second[j - 1])
            i, j = i - 1, j - 1
        elif i and scores[i][j] == scores[i - 1][j] - 2:
            i -= 1
        else:
            j -= 1
    return matches / columns


def validate(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite validation: {output}")
    manifest = verify(COHORT)
    readiness = json.loads(READY.read_text(encoding="utf-8"))
    for name, digest in readiness["inputs"].items():
        assert sha256(ROOT / name) == digest, f"Changed readiness input: {name}"
    assert readiness["script_sha256"] == sha256(ROOT / "02_code/mic_training_readiness_v8.py")
    assert manifest["script_sha256"] == sha256(ROOT / "02_code/audit_mic_confirmed_acid_subset.py")
    frozen_directories = (
        "mic_reviewed_subset_groups_20261002_v3", "mic_candidate_release_review_20261002_v1",
        "mic_primary_review_pmid33790103_20261002_v2", "mic_primary_review_pmid32344933_20261002_v2",
        "mic_primary_review_pmid35735615_20261002_v1",
    )
    for name in frozen_directories:
        verify(ROOT / "03_experiments/audits" / name)
    molecules = rows(COHORT / "candidate_molecules.csv")
    observations = rows(COHORT / "candidate_observations.csv")
    pairs = rows(COHORT / "all_member_similarity.csv")
    summary = rows(COHORT / "component_summary.csv")
    sequences = {row["sample_id"]: row["seq"] for row in molecules}
    labels = {row["sample_id"]: int(row["amp"]) for row in molecules}
    assert len(sequences) == len(set(sequences.values())) == len(molecules) == 11
    assert all(10 <= len(seq) <= 50 and set(seq) <= set("ACDEFGHIKLMNPQRSTVWY") for seq in sequences.values())
    assert len(observations) == 16 and {row["sample_id"] for row in observations} == set(sequences)
    for row in observations:
        assert row["raw_unit"].lower() in {"µg/ml", "μg/ml"}, row["raw_unit"]
        value = row["raw_mic"].strip()
        censored = value.startswith(">")
        number = float(value.removeprefix(">").removeprefix("="))
        expected = 0 if number >= 128 else (1 if not censored and number <= 32 else None)
        assert expected is not None and expected == int(row["derived_label"]) == labels[row["sample_id"]]
        assert float(row["normalized_low_ug_ml"]) == number
        assert float(row["normalized_high_ug_ml"]) == (math.inf if censored else number)
        assert row["target"].startswith("Escherichia coli ") and row["assay_study_ids"]
    expected_pairs = {frozenset(ids) for ids in itertools.combinations(sequences, 2)}
    assert len(pairs) == len(expected_pairs) == 55
    assert {frozenset((row["sample_id_a"], row["sample_id_b"])) for row in pairs} == expected_pairs
    graph = {sample: set() for sample in sequences}
    edge_count = 0
    for row in pairs:
        left, right = row["sample_id_a"], row["sample_id_b"]
        identity = independent_identity(sequences[left], sequences[right])
        assert abs(identity - float(row["identity"])) < 1e-12
        edge = identity >= 0.40
        assert edge == (row["homology_edge"] == "True")
        if edge:
            graph[left].add(right)
            graph[right].add(left)
            edge_count += 1
    studies = {row["sample_id"]: set(row["study_ids"].split("|")) for row in molecules}
    for row in observations:
        studies[row["sample_id"]].update(row["assay_study_ids"].split("|"))
    for left, right in itertools.combinations(sequences, 2):
        if studies[left] & studies[right]:
            graph[left].add(right)
            graph[right].add(left)
    groups = []
    unseen = set(sequences)
    while unseen:
        seed = min(unseen)
        reached, stack = set(), [seed]
        while stack:
            sample = stack.pop()
            if sample not in reached:
                reached.add(sample)
                stack.extend(graph[sample] - reached)
        unseen -= reached
        groups.append(reached)
    stored_groups = {}
    for row in molecules:
        stored_groups.setdefault(row["review_component"], set()).add(row["sample_id"])
    assert {frozenset(group) for group in groups} == {frozenset(group) for group in stored_groups.values()}
    computed = sorted((len(group), sum(labels[x] == 1 for x in group), sum(labels[x] == 0 for x in group)) for group in groups)
    assert computed == sorted((int(row["molecules"]), int(row["positives"]), int(row["negatives"])) for row in summary)
    assert edge_count == manifest["homology_edges"] == readiness["candidate_homology_edges"] == 11
    assert len(groups) == 4 and sum(any(labels[x] == 1 for x in group) for group in groups) == 2
    assert sum(any(labels[x] == 0 for x in group) for group in groups) == 4
    assert rows(COHORT / "fold_assignments.csv") == []
    assert readiness["status"] == "blocked" and readiness["training_started"] is False
    assert readiness["records_released_for_training"] == 0 and readiness["training_command"] is None
    gate = readiness["gates"]["candidate_structure"]
    assert (gate["folds_required"], gate["seed"], gate["cutoff"]) == (5, 42, 0.40)
    assert gate["folds_generated"] is False and gate["cross_fold_homology_edges"] is None
    assert gate["cross_fold_primary_studies"] is None
    assert sha256(ROOT / "04_paper/research_status.json") == "846c1fc2452646f3df9c2055b0a4a1b5140132acc2433bb2c304b133b6e8012c"
    stamp = datetime.fromisoformat(readiness["generated_at"]).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    for name in DOCS:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert READY.name in text and stamp in text and COHORT.name in text and "protocol-mic-01" in text, name
    result = {
        "status": "validation_passed_research_still_blocked", "generated_at": utc_now(),
        "independently_recomputed_pairs": len(pairs), "independently_rederived_observations": len(observations),
        "homology_edges": edge_count, "combined_components": len(groups),
        "positive_bearing_components": 2, "negative_bearing_components": 4,
        "historical_frozen_manifests_verified": len(frozen_directories),
        "current_state_documents_verified": len(DOCS), "formal_status_unchanged": True,
        "training_started": False, "records_released_for_training": 0,
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str((ROOT / name).relative_to(ROOT)): sha256(ROOT / name) for name in DOCS},
        "readiness_sha256": sha256(READY), "cohort_manifest_sha256": sha256(COHORT / "manifest.json"),
        "limitations": ["Local field confirmation does not complete independent source/release review.",
                        "This checks audit arithmetic and state consistency, not model performance."],
    }
    write_json(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(validate(parser.parse_args().output), ensure_ascii=True, indent=2))
