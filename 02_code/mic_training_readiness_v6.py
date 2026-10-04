"""Publish immutable MIC readiness after original EtCec3 candidate review."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_utils import ROOT, sha256, utc_now, write_json


BASE = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v5.json"
GROUPS = ROOT / "03_experiments/audits/mic_reviewed_subset_groups_20261002_v2/manifest.json"
PAPER = ROOT / "03_experiments/audits/mic_primary_review_pmid32344933_20261002_v2/manifest.json"


def generate(output: Path) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite MIC readiness: {output}")
    base = json.loads(BASE.read_text(encoding="utf-8"))
    groups = json.loads(GROUPS.read_text(encoding="utf-8"))
    paper = json.loads(PAPER.read_text(encoding="utf-8"))
    if (base["status"] != "blocked" or base["training_started"] is not False
            or base["training_protocol_id"] != "protocol-mic-05"
            or groups["status"] != "blocked"
            or groups["candidate_molecules"] != 38
            or groups["negative_bearing_components"] != 5
            or groups["positive_bearing_components"] != 5
            or groups["fold_structure_gate_passed"] is not False
            or groups["records_released_for_training"] != 0
            or paper["status"] != "candidate_primary_evidence_verified_not_released"
            or paper["records_released_for_training"] != 0):
        raise ValueError("Source audit gate changed; review before publishing readiness.")
    for manifest in (groups, paper):
        for relative, digest in manifest["inputs"].items():
            if sha256(ROOT / relative) != digest:
                raise ValueError(f"Source input changed: {relative}")
        directory = GROUPS.parent if manifest is groups else PAPER.parent
        for name, digest in manifest["outputs"].items():
            if sha256(directory / name) != digest:
                raise ValueError(f"Source output changed: {directory / name}")
    old_blocker = next((item for item in base["blockers"]
                        if item.startswith("Reviewed subset has only 4 independent")), None)
    if old_blocker is None:
        raise ValueError("Base negative-component blocker differs from the frozen version.")
    result = dict(base)
    result["paper_audits"] = dict(base["paper_audits"])
    result["paper_audits"]["32344933"] = {
        "status": paper["status"], "manifest": str(PAPER.relative_to(ROOT)),
        "sha256": sha256(PAPER), "records_released_for_training": 0,
    }
    result.update({
        "status": "blocked", "generated_at": utc_now(),
        "supersedes": str(BASE.relative_to(ROOT)),
        "reviewed_subset_manifest": str(GROUPS.relative_to(ROOT)),
        "reviewed_subset_manifest_sha256": sha256(GROUPS),
        "reviewed_subset_molecules": groups["candidate_molecules"],
        "reviewed_subset_negative_bearing_components": 5,
        "reviewed_subset_positive_bearing_components": 5,
        "reviewed_subset_fold_structure_gate_passed": False,
        "blockers": [item for item in base["blockers"] if item != old_blocker] + [
            "EtCec3-OH adds a fifth independent negative-bearing group to the reviewed subset, but fixed seed-42 fivefold assignment still has one validation fold with zero positives.",
            "The 38-molecule candidate subset needs complete primary-paper review and a new immutable cohort and training protocol before any model run.",
        ],
        "training_started": False, "training_command": None,
        "scope": "MIC-only exploratory training remains withheld; original EtCec3 evidence is a candidate, not a released training record",
        "script_sha256": sha256(Path(__file__)),
    })
    write_json(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.output), ensure_ascii=True, indent=2))
