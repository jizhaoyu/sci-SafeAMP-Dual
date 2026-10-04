"""Append the unresolved Wang primary-paper review to immutable MIC readiness."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_utils import ROOT, sha256, utc_now, write_json


BASE = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v4.json"
WANG = ROOT / "03_experiments/audits/mic_primary_review_pmid39908380_20261002_v2/manifest.json"


def generate(output: Path) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite training readiness: {output}")
    base = json.loads(BASE.read_text(encoding="utf-8"))
    paper = json.loads(WANG.read_text(encoding="utf-8"))
    if (base["status"] != "blocked" or base["training_started"] is not False
            or base["training_protocol_id"] != "protocol-mic-05"
            or base["reviewed_subset_negative_bearing_components"] != 4
            or base["reviewed_subset_fold_structure_gate_passed"] is not False):
        raise ValueError("Base training gate differs from the frozen reviewed state.")
    if (paper["paper"]["pmid"] != "39908380"
            or paper["status"] != "blocked_paper_range_and_target_resolution"
            or paper["review"] != {
                "records": 2, "range_conflicts": 2,
                "target_annotations_pending": 2,
                "records_released_for_training": 0,
            }):
        raise ValueError("Wang paper review requires a new adjudication.")
    for relative, digest in paper["inputs"].items():
        if sha256(ROOT / relative) != digest:
            raise ValueError(f"Wang paper input changed: {relative}")
    for filename, digest in paper["outputs"].items():
        if sha256(WANG.parent / filename) != digest:
            raise ValueError(f"Wang paper review output changed: {filename}")
    result = dict(base)
    result["paper_audits"] = dict(base["paper_audits"])
    result["paper_audits"]["39908380"] = {
        "status": paper["status"], "manifest": str(WANG.relative_to(ROOT)),
        "sha256": sha256(WANG), "records_released_for_training": 0,
    }
    result.update({
        "generated_at": utc_now(),
        "supersedes": str(BASE.relative_to(ROOT)),
        "blockers": [
            *base["blockers"],
            "Two Wang MIC values in Table S5 are >400 µM for E. coli GD004, while the paper Methods describe a maximum 200 µM concentration; target annotation and concentration range require original-source resolution.",
        ],
        "script_sha256": sha256(Path(__file__)),
    })
    write_json(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.output), ensure_ascii=False, indent=2))
