"""Publish readiness for the evidence-filtered cohort without inheriting old fold approval."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from audit_mic_reviewed_subset_ludwig import verify
from research_utils import ROOT, sha256, utc_now, write_json


BASE = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v7.json"
COHORT = ROOT / "03_experiments/audits/mic_confirmed_acid_subset_20261002_v1"
PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-01.json"
FORMAL = ROOT / "04_paper/research_status.json"
LEAD = ROOT / "03_experiments/audits/mic_primary_candidate_sources_20261002_v1/PMC8329280.xml"
LEAD_REVIEW = ROOT / "03_experiments/audits/mic_cateslytin_source_review_20261002_v1.md"


def generate(output: Path) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite readiness: {output}")
    base = json.loads(BASE.read_text(encoding="utf-8"))
    cohort = verify(COHORT)
    if cohort["script_sha256"] != sha256(ROOT / "02_code/audit_mic_confirmed_acid_subset.py"):
        raise ValueError("The frozen cohort generator changed.")
    formal = json.loads(FORMAL.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    molecules = pd.read_csv(COHORT / "candidate_molecules.csv")
    observations = pd.read_csv(COHORT / "candidate_observations.csv")
    components = pd.read_csv(COHORT / "component_summary.csv")
    total = len(components)
    positive = int(components.positives.gt(0).sum())
    negative = int(components.negatives.gt(0).sum())
    counts = {str(int(label)): int(count) for label, count in molecules.amp.value_counts().sort_index().items()}
    if (base["status"] != "blocked" or base["training_started"] is not False
            or base["records_released_for_training"] != 0
            or base["gates"]["candidate_structure"]["status"] != "passed"
            or cohort["status"] != "blocked" or cohort["fold_structure_gate_passed"] is not False
            or cohort["folds_generated"] is not False or cohort["folds"] != []
            or cohort["cross_fold_homology_edges"] is not None
            or cohort["cross_fold_primary_studies"] is not None
            or cohort["records_released_for_training"] != 0 or cohort["training_started"] is not False
            or (cohort["folds_required"], cohort["seed"], cohort["cutoff"]) != (5, 42, 0.40)
            or (total, positive, negative) != (cohort["combined_components"],
                                               cohort["positive_bearing_components"],
                                               cohort["negative_bearing_components"])
            or len(molecules) != cohort["candidate_molecules"]
            or len(observations) != cohort["candidate_observations"]
            or sum(components.molecules) != len(molecules)
            or counts != {"0": int(components.negatives.sum()), "1": int(components.positives.sum())}
            or min(total, positive, negative) >= 5
            or formal["status"] != "blocked" or formal["run_status"] != "none"
            or formal["formal_results_available"] is not False or formal["publication_ready"] is not False
            or sha256(FORMAL) != base["formal_status_sha256"]
            or protocol["protocol_id"] != "protocol-mic-01"):
        raise ValueError("A source gate changed; audit before publishing readiness.")
    paths = (BASE, COHORT / "manifest.json", PROTOCOL, FORMAL,
             ROOT / "02_code/audit_mic_confirmed_acid_subset.py", LEAD, LEAD_REVIEW)
    result = {
        "schema_version": 2, "status": "blocked", "generated_at": utc_now(),
        "supersedes": str(BASE.relative_to(ROOT)),
        "scope": "MIC-only evidence-filtered exploratory candidates; no training release",
        "audit_protocol_id": protocol["protocol_id"], "audit_protocol_path": str(PROTOCOL.relative_to(ROOT)),
        "audit_protocol_sha256": sha256(PROTOCOL),
        "training_protocol_id": None, "training_protocol_status": "pending_new_immutable_protocol",
        "withdrawn_historical_training": base["withdrawn_historical_training"],
        "candidate_cohort_version": COHORT.name,
        "candidate_cohort_manifest": str((COHORT / "manifest.json").relative_to(ROOT)),
        "candidate_cohort_manifest_sha256": sha256(COHORT / "manifest.json"),
        "candidate_molecules": len(molecules), "candidate_observations": len(observations),
        "candidate_class_counts": counts, "candidate_all_member_pairs": cohort["all_member_pairs"],
        "candidate_homology_edges": cohort["homology_edges"],
        "candidate_combined_components": total,
        "candidate_positive_bearing_components": positive, "candidate_negative_bearing_components": negative,
        "historical_unreleased_candidate_structure": {
            "manifest": base["candidate_cohort_manifest"],
            "sha256": base["candidate_cohort_manifest_sha256"],
            "molecules": base["candidate_molecules"], "observations": base["candidate_observations"],
            "structure_status": "passed", "applicable_to_current_cohort": False,
        },
        "gates": {
            "candidate_structure": {
                "status": "blocked", "folds_required": 5, "seed": 42, "cutoff": 0.40,
                "folds_generated": False, "folds": [],
                "cross_fold_homology_edges": None, "cross_fold_primary_studies": None,
                "reason": "Fewer than five indivisible components and five components containing each class.",
                "necessary_additional_components_lower_bound": {
                    "total": max(0, 5 - total), "positive_bearing": max(0, 5 - positive),
                    "negative_bearing": max(0, 5 - negative),
                    "sufficient_for_fixed_folds": False,
                },
            },
            "primary_evidence_release": {
                "status": "blocked", "locally_confirmed_free_acid_molecules": len(molecules),
                "prior_candidates_withheld": cohort["prior_candidates_withheld"],
                "new_conflicting_source_molecules_withheld": cohort["new_conflicting_source_molecules_withheld"],
                "full_release_review_complete": False,
                "manifest": str((COHORT / "manifest.json").relative_to(ROOT)),
                "sha256": sha256(COHORT / "manifest.json"),
            },
            "final_admitted_cohort": {"status": "pending_full_release_review_and_new_data"},
            "training_protocol": {"status": "pending_new_immutable_protocol"},
        },
        "blockers": cohort["blockers"], "historical_evidence_conflicts": base["historical_evidence_conflicts"],
        "paper_audits": base["paper_audits"],
        "additional_source_reviews": {
            "free_acid_controls": {"molecules": 4, "observations": 7, "training_release": False},
            "latarcin2022": {"status": "withheld_conflicting_terminal_identity", "molecules": 4},
            "cateslytin2021": {"status": "withheld_missing_primary_terminal_identity", "molecules": 2,
                               "report": str(LEAD_REVIEW.relative_to(ROOT)), "training_release": False},
        },
        "records_released_for_training": 0, "training_started": False, "training_command": None,
        "formal_dual_task_status": formal["status"], "formal_status_generated_at": formal["generated_at"],
        "formal_status_sha256": sha256(FORMAL), "formal_results_available": False, "publication_ready": False,
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
    }
    write_json(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    result = generate(parser.parse_args().output)
    print(json.dumps({key: result[key] for key in ("status", "generated_at", "candidate_molecules",
                                                 "candidate_observations", "gates", "training_started")}, indent=2))
