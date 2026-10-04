"""Generate MIC-only readiness with distinct candidate structure and evidence-release gates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from audit_mic_reviewed_subset_ludwig import verify
from research_utils import ROOT, sha256, utc_now, write_json


BASE = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v6.json"
STRUCTURE = ROOT / "03_experiments/audits/mic_reviewed_subset_groups_20261002_v3"
EVIDENCE = ROOT / "03_experiments/audits/mic_candidate_release_review_20261002_v1"
PAPER = ROOT / "03_experiments/audits/mic_primary_review_pmid35735615_20261002_v1"
AUDIT_PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-01.json"
FORMAL = ROOT / "04_paper/research_status.json"


def generate(output: Path) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite readiness: {output}")
    base = json.loads(BASE.read_text(encoding="utf-8"))
    structure, evidence, paper = verify(STRUCTURE), verify(EVIDENCE), verify(PAPER)
    formal = json.loads(FORMAL.read_text(encoding="utf-8"))
    protocol = json.loads(AUDIT_PROTOCOL.read_text(encoding="utf-8"))
    if (base["status"] != "blocked" or base["training_started"] is not False
            or structure["candidate_molecules"] != 41 or structure["candidate_observations"] != 54
            or structure["fold_structure_gate_passed"] is not True
            or structure["cross_fold_homology_edges"] != 0 or structure["cross_fold_primary_studies"] != 0
            or evidence["status"] != "blocked_primary_evidence_release"
            or evidence["locally_confirmed_free_acid_molecules"] != 7
            or evidence["pending_primary_molecular_form_molecules"] != 34
            or any(item["records_released_for_training"] != 0 for item in (structure, evidence, paper))
            or formal["status"] != "blocked" or formal["run_status"] != "none"
            or formal["formal_results_available"] is not False or formal["publication_ready"] is not False
            or protocol["protocol_id"] != "protocol-mic-01"):
        raise ValueError("A source gate changed; audit before publishing readiness.")
    molecules = pd.read_csv(STRUCTURE / "candidate_molecules.csv")
    paper_audits = dict(base["paper_audits"])
    paper_audits["35735615"] = {
        "status": paper["status"], "manifest": str((PAPER / "manifest.json").relative_to(ROOT)),
        "sha256": sha256(PAPER / "manifest.json"), "records_released_for_training": 0,
    }
    paths = (BASE, STRUCTURE / "manifest.json", EVIDENCE / "manifest.json",
             PAPER / "manifest.json", AUDIT_PROTOCOL, FORMAL,
             ROOT / "02_code/audit_mic_reviewed_subset_ludwig.py")
    result = {
        "schema_version": 2, "status": "blocked", "generated_at": utc_now(),
        "supersedes": str(BASE.relative_to(ROOT)),
        "scope": "MIC-only exploratory candidate cohort; no training release or formal dual-task result",
        "audit_protocol_id": "protocol-mic-01", "audit_protocol_path": str(AUDIT_PROTOCOL.relative_to(ROOT)),
        "audit_protocol_sha256": sha256(AUDIT_PROTOCOL),
        "training_protocol_id": None, "training_protocol_status": "pending_new_immutable_protocol",
        "withdrawn_historical_training": {
            "protocol_id": base["training_protocol_id"], "protocol_path": base["training_protocol_path"],
            "protocol_sha256": base["training_protocol_sha256"],
            "molecules": base["molecule_count"], "status": "withheld_primary_evidence_incomplete",
        },
        "candidate_cohort_version": "mic_reviewed_subset_groups_20261002_v3",
        "candidate_cohort_manifest": str((STRUCTURE / "manifest.json").relative_to(ROOT)),
        "candidate_cohort_manifest_sha256": sha256(STRUCTURE / "manifest.json"),
        "candidate_molecules": len(molecules), "candidate_observations": structure["candidate_observations"],
        "candidate_class_counts": {str(int(label)): int(count) for label, count in molecules.amp.value_counts().sort_index().items()},
        "candidate_all_member_pairs": structure["all_member_pairs"],
        "candidate_combined_components": structure["combined_components"],
        "candidate_negative_bearing_components": structure["negative_bearing_components"],
        "candidate_positive_bearing_components": structure["positive_bearing_components"],
        "gates": {
            "candidate_structure": {"status": "passed", "folds": structure["folds"],
                                    "cross_fold_homology_edges": 0, "cross_fold_primary_studies": 0},
            "primary_evidence_release": {"status": "blocked", "locally_confirmed_free_acid_molecules": 7,
                                         "pending_primary_molecular_form_molecules": 34,
                                         "manifest": str((EVIDENCE / "manifest.json").relative_to(ROOT)),
                                         "sha256": sha256(EVIDENCE / "manifest.json")},
            "final_admitted_cohort": {"status": "pending_evidence_selection_and_reaudit"},
            "training_protocol": {"status": "pending_new_immutable_protocol"},
        },
        "blockers": evidence["blockers"], "historical_evidence_conflicts": base["blockers"][:5],
        "paper_audits": paper_audits, "records_released_for_training": 0,
        "training_started": False, "training_command": None,
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
    args = parser.parse_args()
    result = generate(args.output)
    print(json.dumps({key: result[key] for key in ("status", "generated_at", "candidate_molecules", "candidate_observations",
                                                "gates", "records_released_for_training", "training_started")}, ensure_ascii=True, indent=2))
