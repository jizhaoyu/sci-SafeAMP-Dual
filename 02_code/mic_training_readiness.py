"""Record MIC-only exploratory training readiness from immutable evidence audits."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_utils import ROOT, read_json, sha256, utc_now, write_json
from train_mic_baselines import (CURRENT_AUDIT_MANIFEST, CURRENT_STUDY_MANIFEST,
                                 PrimaryStudyReviewRequired, canonical_sha256,
                                 load_and_validate)

CURRENT_PRIMARY_REVIEW = ROOT / "03_experiments/audits/mic_primary_review_20261001_v3/manifest.json"


def generate(protocol_path: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite readiness status: {output}")
    try:
        protocol, molecules, protocol_sha, cohort_path, folds_path, study_path, study = load_and_validate(protocol_path)
        blockers = []
    except PrimaryStudyReviewRequired as exc:
        protocol = read_json(protocol_path)
        protocol_sha = canonical_sha256(protocol)
        cohort_path, study_path = CURRENT_AUDIT_MANIFEST, CURRENT_STUDY_MANIFEST
        study = read_json(study_path)
        folds_path = ROOT / protocol["fold_assignments"]
        molecules = None
        blockers = [str(exc)]
    cohort = read_json(cohort_path)
    source_path = (ROOT / cohort["existing_records_path"]).parent / "manifest.json"
    source = read_json(source_path)
    if (source.get("status") != "evidence_screened_subset_pending_full_cohort_audit"
            or source.get("retained_count") != cohort["existing_record_count"]
            or source.get("retained_records_sha256") != cohort["existing_records_sha256"]):
        raise ValueError("Curated source and approved MIC cohort do not match.")
    formal_path = ROOT / "04_paper/research_status.json"
    formal = read_json(formal_path)
    if formal.get("status") != "blocked" or formal.get("protocol_id") != "protocol-amd-02":
        raise ValueError("Formal dual-task status changed; review the separate formal study before publishing readiness.")
    primary_review = read_json(CURRENT_PRIMARY_REVIEW)
    if primary_review.get("status") != "blocked_primary_review_in_progress":
        raise ValueError("Primary-paper review status changed; inspect it before issuing MIC readiness.")
    for relative_path, expected_sha in primary_review["inputs"].items():
        if sha256(ROOT / relative_path) != expected_sha:
            raise ValueError(f"Primary-paper review input changed: {relative_path}")
    for filename, expected_sha in primary_review["outputs"].items():
        if sha256(CURRENT_PRIMARY_REVIEW.parent / filename) != expected_sha:
            raise ValueError(f"Primary-paper review output changed: {filename}")
    conflict_count = int(primary_review["paper_review"]["database_mic_conflicts"])
    if conflict_count:
        blockers.append(f"Primary-paper comparison found {conflict_count} conflicting raw DBAASP MIC observation(s); see the versioned activity review.")
    result = {
        "status": "blocked" if blockers else "ready_for_exploratory_mic_training",
        "generated_at": utc_now(),
        "supersedes": "03_experiments/audits/mic_training_readiness_20261001_v2.json",
        "training_protocol_id": protocol["protocol_id"],
        "training_protocol_sha256": protocol_sha,
        "training_protocol_path": str(protocol_path.resolve().relative_to(ROOT)),
        "source_manifest": str(source_path.resolve().relative_to(ROOT)),
        "source_manifest_sha256": sha256(source_path),
        "cohort_manifest": str(cohort_path.resolve().relative_to(ROOT)),
        "cohort_manifest_sha256": sha256(cohort_path),
        "study_manifest": str(study_path.resolve().relative_to(ROOT)),
        "study_manifest_sha256": sha256(study_path),
        "fold_assignments": str(folds_path.resolve().relative_to(ROOT)),
        "fold_assignments_sha256": sha256(folds_path),
        "primary_review_manifest": str(CURRENT_PRIMARY_REVIEW.relative_to(ROOT)),
        "primary_review_manifest_sha256": sha256(CURRENT_PRIMARY_REVIEW),
        "primary_review_conflicting_raw_observations": conflict_count,
        "molecule_count": len(molecules) if molecules is not None else cohort["unique_labeled_molecule_count"],
        "class_counts": ({str(int(label)): int(count) for label, count in molecules.amp.value_counts().sort_index().items()}
                         if molecules is not None else cohort["amp_label_counts"]),
        "fold_sizes": ({str(int(fold)): int(count) for fold, count in molecules.fold.value_counts().sort_index().items()}
                       if molecules is not None else {str(fold["fold"]): fold["validation_n"] for fold in study["folds"]}),
        "homology_plus_study_components": study["combined_components"],
        "largest_component": study["largest_combined_component"],
        "warnings": study["warnings"],
        "blockers": blockers,
        "training_started": False,
        "formal_dual_task_status": formal["status"],
        "formal_status_sha256": sha256(formal_path),
        "scope": "MIC-only exploratory baseline; training withheld pending primary-study verification",
        "training_command": None if blockers else "python 02_code/train_mic_baselines.py --protocol 03_experiments/protocols/protocol-mic-05.json --output 03_experiments/runs/mic_only_baselines_20261001_v4"
    }
    write_json(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=ROOT / "03_experiments/protocols/protocol-mic-05.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.protocol, args.output), ensure_ascii=False, indent=2))
