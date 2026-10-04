"""Publish an immutable MIC-only readiness update from paper and group audits."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_utils import ROOT, sha256, utc_now, write_json


BASE = ROOT / "03_experiments/audits/mic_training_readiness_20261001_v3.json"
GROUPS = ROOT / "03_experiments/audits/mic_reviewed_subset_groups_20261002_v1/manifest.json"
PAPER_DIRS = (
    "mic_primary_review_pmid33281785_20261002_v2",
    "mic_primary_review_pmid36551368_20261002_v2",
    "mic_primary_review_pmid29259134_20261002_v2",
    "mic_primary_review_pmid33790103_20261002_v2",
    "mic_primary_review_pmid37938588_20261002_v2",
    "mic_primary_review_pmid40645962_20261002_v2",
)


def generate(output: Path) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite training readiness: {output}")
    base = json.loads(BASE.read_text(encoding="utf-8"))
    if (base["status"] != "blocked" or base["training_protocol_id"] != "protocol-mic-05"
            or base["training_started"] is not False):
        raise ValueError("Base readiness changed; review the frozen training gate.")
    for field, hash_field in (("source_manifest", "source_manifest_sha256"),
                              ("cohort_manifest", "cohort_manifest_sha256"),
                              ("study_manifest", "study_manifest_sha256"),
                              ("fold_assignments", "fold_assignments_sha256"),
                              ("primary_review_manifest", "primary_review_manifest_sha256")):
        if sha256(ROOT / base[field]) != base[hash_field]:
            raise ValueError(f"Frozen readiness input changed: {field}")
    formal_path = ROOT / "04_paper/research_status.json"
    if sha256(formal_path) != base["formal_status_sha256"]:
        raise ValueError("Formal study status changed; review before publishing MIC readiness.")
    groups = json.loads(GROUPS.read_text(encoding="utf-8"))
    if (groups["status"] != "blocked" or groups["fold_structure_gate_passed"]
            or groups["records_released_for_training"] != 0):
        raise ValueError("Reviewed subset group gate changed; inspect its evidence.")
    for relative, digest in groups["inputs"].items():
        if sha256(ROOT / relative) != digest:
            raise ValueError(f"Reviewed subset input changed: {relative}")
    for filename, digest in groups["outputs"].items():
        if sha256(GROUPS.parent / filename) != digest:
            raise ValueError(f"Reviewed subset output changed: {filename}")
    paper_paths = [ROOT / "03_experiments/audits" / name / "manifest.json" for name in PAPER_DIRS]
    paper_audits = {}
    for path in paper_paths:
        paper = json.loads(path.read_text(encoding="utf-8"))
        review = paper["review"]
        if review["records_released_for_training"] != 0:
            raise ValueError(f"Paper-level review unexpectedly released records: {path}")
        paper_audits[paper["paper"]["pmid"]] = {
            "status": paper["status"], "manifest": str(path.relative_to(ROOT)),
            "sha256": sha256(path), "records_released_for_training": 0,
        }
    result = dict(base)
    result.update({
        "status": "blocked", "generated_at": utc_now(),
        "supersedes": str(BASE.relative_to(ROOT)),
        "reviewed_subset_manifest": str(GROUPS.relative_to(ROOT)),
        "reviewed_subset_manifest_sha256": sha256(GROUPS),
        "reviewed_subset_molecules": groups["candidate_molecules"],
        "reviewed_subset_negative_bearing_components": groups["negative_bearing_components"],
        "reviewed_subset_fold_structure_gate_passed": False,
        "paper_audits": paper_audits,
        "blockers": [
            *base["blockers"],
            f"Reviewed subset has only {groups['negative_bearing_components']} independent negative-bearing components for five folds; fixed fold audit lacks both classes in two validation folds.",
            "Two Pandi source molecules are C-terminally amidated but frozen records omit that chemistry; exclude pending a new molecular identity audit.",
            "Eight Guan source-data cells use an undocumented 80 code; only four exact numerical matches were considered for the provisional group audit.",
        ],
        "training_started": False, "training_command": None,
        "scope": "MIC-only exploratory training remains withheld; reviewed subset is feasibility evidence, not a released cohort",
        "script_sha256": sha256(Path(__file__)),
    })
    write_json(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.output), ensure_ascii=False, indent=2))
