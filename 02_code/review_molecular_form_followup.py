"""Review synthesis provenance and reject ineligible new source leads, without fit."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

from review_development_assay_endpoints import bind, load, pdf_text, region, write, xml_region
from review_development_primary_followup import require, verify_acquisition, verify_summary
from research_utils import ROOT, sha256, utc_now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing to replace review: {args.output}")
    base, inputs = args.audit_root, {}
    code = Path(__file__).parent
    previous = base / "development_primary_review_v2"
    old = verify_summary(previous, code / "review_development_primary_followup.py", inputs)
    bind(previous / "verification.json", inputs)
    if not load(previous / "verification.json")["passed"] or old["labels_released"] != 0:
        raise ValueError("Predecessor is not a verified no-release review")
    decisions = copy.deepcopy(load(previous / "record_decisions.json"))
    rows = {r["record_id"]: r for r in decisions}
    pending = [r["record_id"] for r in decisions if r["status"].startswith("pending_")]
    if len(pending) != 6:
        raise ValueError("Pending review coverage changed")
    predecessor = previous / "followup_state.json"
    bind(predecessor, inputs)
    if load(predecessor)["prepared"] != str(args.prepared.resolve()):
        raise ValueError("Prepared dataset differs from predecessor")

    probes = {}
    relative = "development_source_followup_acquisition_v1/unubol_2017.pdf"
    text = pdf_text(base, inputs, relative, 2)
    require(text, "Peptide synthesis", "Metabion")
    probes["DBAASP:21172"] = (region(base, inputs, relative, "Peptide synthesis, PDF p.2"),
        "Metabion is named, but this synthesis paragraph does not specify terminal chemistry or stereochemistry. Prior HC50 numerical conflict remains unresolved.")

    relative = "development_primary_acquisition_v1/35877911.xml"
    item, text = xml_region(base, inputs, relative, element_id="sec2dot5dot1-membranes-12-00708")
    require(text, "Antimicrobial Activity", "NaCl")
    probes["DBAASP:19492"] = (item,
        "Antimicrobial methods describe buffer/LB conditions, but this section does not establish RD10 synthesis, termini or cysteine oxidation state. Methods citations are not a specimen certificate.")

    relative = "development_primary_acquisition_v1/36555235.xml"
    item, text = xml_region(base, inputs, relative, element_id="sec4dot1-ijms-23-15594")
    require(text, "Design and Characterization", "CancerPPD")
    probes["DBAASP:20464"] = (item,
        "Section 4.1 describes computational design/characterization; it does not identify the synthesis supplier, terminal chemistry or stereochemistry. The measured supplementary MIC table is retained, without inventing missing methods.")

    relative = "development_primary_acquisition_v1/35606468.xml"
    item, text = xml_region(base, inputs, relative, element_id="Sec5")
    require(text, "Nigrocin-M2", "tribute peptide", "MALDI")
    probes["DBAASP:19286"] = (item,
        "A tribute peptide synthesiser, HPLC and MALDI-TOF are reported; the section does not establish terminal chemistry. Cited synthesis methods for another peptide cannot automatically establish this tested specimen's form.")

    relative = "development_patent_acquisition_v1/US6875744B2.pdf"
    text = pdf_text(base, inputs, relative, 9)
    if not re.search(r"D-\s*or\s*L-amino", text):
        raise ValueError("Patent stereochemical alternatives anchor changed")
    probes["DBAASP:15919"] = (region(base, inputs, relative, "Patent p.9, column 14; form alternatives"),
        "The patent explicitly allows D or L and acid or amide forms in general. These alternatives do not identify the stereochemistry/N terminus of the actual Table 13 FLAK06 AC specimen. Acid versus amide endpoint distinction remains as recorded.")

    relative = "development_pmc_cloud_assets_v1/PMC4131589.1.pdf"
    text = pdf_text(base, inputs, relative, 5)
    require(text, "GL Biochem", "98%")
    probes["DBAASP:8983"] = (region(base, inputs, relative, "Experimental / Material, PDF p.5"),
        "Supplier and HPLC/MS purity are explicit. The material paragraph does not establish complete terminal chemistry and stereochemistry; purity alone does not establish an unmodified molecular form.")
    for record_id in pending:
        item, note = probes[record_id]
        rows[record_id]["form_followup"] = {"region": item, "decision": "not_closed",
                                              "note": note, "molecule_evidence_approved": False}

    acquired = base / "molecular_form_followup_acquisition_v1"
    verify_acquisition(acquired, code / "fetch_review_source_requests.py", inputs)
    bundle_dir = base / "molecular_form_followup_acquisition_v2"
    verify_acquisition(bundle_dir, code / "fetch_review_source_requests.py", inputs)
    thesis_relative = "molecular_form_followup_acquisition_v1/corrie_2023_thesis.pdf"
    thesis = pdf_text(base, inputs, thesis_relative, 87)
    require(thesis, "porcine red blood cells", "PRBC", "HC50")
    for page in (86, 87):
        bind(base / f"molecular_form_followup_visual_v1/corrie_2023_page_{page}.png", inputs)

    star_file = acquired / "bmr34705_3.str"
    star = star_file.read_text(encoding="utf-8")
    require(star, "data_34705", "polypeptide(L)", "EKRWRRLIFNYFX", "10.1016/j.matdes.2022.111364")
    if not re.search(r"13\s+\.\s+NH2\s+\.\s+34705\s+1", star):
        raise ValueError("Deposited terminal chemical component changed")
    raw_candidates = []
    for accession in (20173, 20179):
        path = ROOT / f"02_code/data/sources/dbaasp_v1/raw/peptide_{accession}.json"
        bind(path, inputs)
        raw = load(path)
        if raw["sequence"] == "EKRWRRLIFNYF":
            raise ValueError("Structural source now matches targeted molecule; perform specimen review")
        raw_candidates.append({"record_id": f"DBAASP:{accession}", "name": raw["name"],
                               "sequence": raw["sequence"], "matches_deposited_backbone": False})
    bundle = (bundle_dir / "amp_challenge_official_bundle.js").read_text(encoding="utf-8")
    require(bundle, "Mar to Apr 2027", "Experimental validation (MIC / HC50)", "after the challenge")
    leads = [
        {"source": "Corrie 2023, University of Victoria thesis", "decision": "excluded_from_human_hc50_source_pool",
         "region": region(base, inputs, thesis_relative, "Section 3.3.3, printed p.72 / PDF p.87"),
         "rbc_species": "porcine", "human_hc50_evidence": False,
         "reason": "Original methods use porcine RBCs. Human HEK293 viability is a different endpoint; neither supplies human RBC HC50.",
         "license_note": "Original thesis reserves author copyright; local inspection only, no redistribution permission inferred."},
        {"source": "BMRB 34705 / PDB 7QZV", "decision": "structural_identity_only_no_functional_label",
         "region": region(base, inputs, "molecular_form_followup_acquisition_v1/bmr34705_3.str",
                          "save_entity_1; Entity_comp_index 13; save_chem_comp_NH2; Citation.DOI"),
         "backbone": "EKRWRRLIFNYF", "terminal_component": "NH2", "deposited_polymer_type": "polypeptide(L)",
         "standard_amino_acid_count": 12, "total_deposited_components": 13,
         "functional_assays_present": False, "related_development_records": raw_candidates,
         "reason": "This amidated NMR specimen does not match either Hm-AMP4 or Hm-AMP10. Do not transfer structural chemistry or assay values across molecules in the same publication.",
         "citation_metadata_warning": "Deposited journal label/ISSN are inconsistent with the DOI registration; rely on previously reviewed DOI identity, not automatic journal alias acceptance."},
        {"source": "AMP Challenge official organizer site", "decision": "prospective_release_not_current_assay_evidence",
         "region": region(base, inputs, "molecular_form_followup_acquisition_v2/amp_challenge_official_bundle.js",
                          "timeline wetlab date + recognition Data Sharing and IP text; inspected as text, not executed"),
         "scheduled_experimental_window": "March-April 2027", "measurements_acquired": 0,
         "reason": "The official page schedules experimental validation in 2027 and promises later release. It does not furnish measurements usable as current evidence in this review.",
         "license_note": "Promised CC-BY 4.0 applies to later release, not an acquired current dataset."},
    ]
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/api/ready", timeout=10) as response:
            runtime = {"http_status": response.status, "response": json.loads(response.read())}
    except urllib.error.HTTPError as exc:
        runtime = {"http_status": exc.code, "response": json.loads(exc.read())}
    except (urllib.error.URLError, TimeoutError) as exc:
        runtime = {"http_status": None, "error": str(exc)}
    checked_at = utc_now()
    args.output.mkdir(parents=True, exist_ok=False)
    write(args.output / "record_decisions.json", decisions)
    write(args.output / "source_lead_decisions.json", leads)
    summary = {
        "generated_at": utc_now(), "protocol_id": "protocol-amd-02", "status": "molecular_form_followup_no_release",
        "review_mode": "agent_original_source_review_not_independent_human_review",
        "predecessor_summary": str((previous / "summary.json").resolve()),
        "predecessor_summary_sha256": sha256(previous / "summary.json"),
        "pending_form_probes": len(probes), "form_gaps_closed": 0, "new_sources_reviewed": len(leads),
        "decisions": dict(Counter(r["status"] for r in decisions)), "labels_released": 0,
        "model_fit_calls": 0, "formal_dataset_changed": False,
        "validation_scope": "Six synthesis/form passages and three new source leads; not full-cohort release or independent isolation/model validation",
        "inputs": inputs, "producer_sha256": sha256(Path(__file__)),
        "outputs": {name: sha256(args.output / name) for name in
                    ("record_decisions.json", "source_lead_decisions.json")},
    }
    write(args.output / "summary.json", summary)
    write(args.output / "followup_state.json", {
        "generated_at": summary["generated_at"], "protocol_id": summary["protocol_id"],
        "status": "evidence_and_external_cohort_blocked",
        "scope": "Goal followup audit; not replacement of formal research status",
        "predecessor": {"path": str(predecessor.resolve()), "sha256": sha256(predecessor)},
        "prepared": str(args.prepared.resolve()), "review_summary": str((args.output / "summary.json").resolve()),
        "review_summary_sha256": sha256(args.output / "summary.json"),
        "runtime_checked_at": checked_at, "runtime": runtime,
        "new_evidence_labels": 0, "new_model_fit_calls": 0, "dual_task_ready": False,
    })
    print(json.dumps({"form_probes": len(probes), "new_sources_reviewed": len(leads),
                      "labels_released": 0, "runtime_http_status": runtime["http_status"]}))


if __name__ == "__main__":
    main()
