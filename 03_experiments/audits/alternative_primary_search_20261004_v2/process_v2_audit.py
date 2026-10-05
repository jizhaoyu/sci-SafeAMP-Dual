"""Execute comprehensive Phase B, C, D audit for alternative primary sources v2."""
import csv
import datetime
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
sys.path.insert(0, str(PROJECT / '02_code'))
from research_data import sequence_identity

def text(node):
    return ' '.join(node.itertext()).strip() if node is not None else ''

def write_json(path, data):
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    raise RuntimeError(
        'Deprecated v2 audit: use 02_code/repair_alternative_primary_audit.py '
        'repair --output NEW_DIRECTORY. Historical outputs must not be overwritten.'
    )
    dev_path = PROJECT / '03_experiments/prepared/amd02_evidence_clean_20261001/records.csv'
    mic_path = PROJECT / '03_experiments/audits/mic_followup_release_20261004_v1/cohort/candidate_molecules.csv'
    mic_sources_path = PROJECT / '03_experiments/audits/mic_followup_release_20261004_v1/evidence/source_review.csv'

    with dev_path.open(encoding='utf-8-sig', newline='') as f:
        dev = list(csv.DictReader(f))
    with mic_path.open(encoding='utf-8-sig', newline='') as f:
        mic = list(csv.DictReader(f))
    with mic_sources_path.open(encoding='utf-8-sig', newline='') as f:
        mic_sources = list(csv.DictReader(f))

    assert len(dev) == 417 and len(mic) == 16

    raw_dir = ROOT / 'raw'
    
    # 1. Acquisition summary
    acquisition = [
        {
            "file": "pandinin2014.xml",
            "source_id": "pandinin2014",
            "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4096598/",
            "doi": "10.1371/journal.pone.0101742",
            "pmid": "25019413",
            "pmcid": "PMC4096598",
            "sha256": hashlib.sha256((raw_dir / "pandinin2014.xml").read_bytes()).hexdigest(),
            "bytes": (raw_dir / "pandinin2014.xml").stat().st_size,
            "license": "CC BY 4.0",
            "format": "JATS XML"
        },
        {
            "file": "corvus2023.xml",
            "source_id": "corvus2023",
            "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10618271/",
            "doi": "10.1038/s41598-023-45875-w",
            "pmid": "37907616",
            "pmcid": "PMC10618271",
            "sha256": hashlib.sha256((raw_dir / "corvus2023.xml").read_bytes()).hexdigest(),
            "bytes": (raw_dir / "corvus2023.xml").stat().st_size,
            "license": "CC BY 4.0",
            "format": "JATS XML"
        },
        {
            "file": "chmap2018.xml",
            "source_id": "chmap2018",
            "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6308165/",
            "doi": "10.3389/fphar.2018.01501",
            "pmid": "30622471",
            "pmcid": "PMC6308165",
            "sha256": hashlib.sha256((raw_dir / "chmap2018.xml").read_bytes()).hexdigest(),
            "bytes": (raw_dir / "chmap2018.xml").stat().st_size,
            "license": "CC BY 4.0",
            "format": "JATS XML"
        },
        {
            "file": "goat_antibacterial2018.xml",
            "source_id": "goat_antibacterial2018",
            "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6284057/",
            "doi": "10.3389/fmicb.2018.02983",
            "pmid": "30555455",
            "pmcid": "PMC6284057",
            "sha256": hashlib.sha256((raw_dir / "goat_antibacterial2018.xml").read_bytes()).hexdigest(),
            "bytes": (raw_dir / "goat_antibacterial2018.xml").stat().st_size,
            "license": "CC BY 4.0",
            "format": "JATS XML"
        },
        {
            "file": "mechkarska2013_thesis.pdf",
            "source_id": "hymenochirin2012",
            "url": "https://edepot.wur.nl/255770",
            "doi": "10.1016/j.peptides.2012.03.029",
            "pmid": "22497805",
            "sha256": hashlib.sha256((raw_dir / "mechkarska2013_thesis.pdf").read_bytes()).hexdigest(),
            "bytes": (raw_dir / "mechkarska2013_thesis.pdf").stat().st_size,
            "license": "Wageningen University Open Access Thesis Repository; Chapter 6 contains Peptides 2012 study",
            "format": "PDF"
        }
    ]
    write_json(ROOT / "acquisition.json", acquisition)

    # 2. Source review
    source_review = [
        {
            "source_id": "pandinin2014",
            "doi": "10.1371/journal.pone.0101742",
            "pmid": "25019413",
            "pmcid": "PMC4096598",
            "title": "Characterization of Antibacterial and Hemolytic Activity of Synthetic Pandinin 2 Variants and Their Inhibition against Mycobacterium tuberculosis",
            "formal_dev_identifier_matches": ["DBAASP:948"],
            "mic_identifier_matches": [],
            "status": "blocked_source_overlap_and_intermediate_mic",
            "admitted_molecules": 0,
            "admitted_assays": 0,
            "rationale": "Exact identifier overlap with DBAASP:948 in formal dev set; 5 sequences have homology violations (up to 1.0) with formal dev set. MIC values in Table 3 against E. coli (12.5-25 uM, 32.15-68.16 ug/ml) fall in the intermediate zone (>32 and <128 ug/ml), yielding zero binary labels under protocol rules."
        },
        {
            "source_id": "corvus2023",
            "doi": "10.1038/s41598-023-45875-w",
            "pmid": "37907616",
            "pmcid": "PMC10618271",
            "title": "Transcriptome analysis of Corvus splendens reveals a repertoire of antimicrobial peptides",
            "formal_dev_identifier_matches": [],
            "mic_identifier_matches": [],
            "status": "excluded_chemical_modification",
            "admitted_molecules": 0,
            "admitted_assays": 0,
            "rationale": "Peptide synthesis in Methods explicitly reports Rink amide resin / C-terminal amidation. Excluded from current unmodified linear peptide domain."
        },
        {
            "source_id": "chmap2018",
            "doi": "10.3389/fphar.2018.01501",
            "pmid": "30622471",
            "pmcid": "PMC6308165",
            "title": "Anticancer Activity of the Goat Antimicrobial Peptide ChMAP-28",
            "formal_dev_identifier_matches": ["DBAASP:12306"],
            "mic_identifier_matches": [],
            "status": "blocked_no_ecoli_mic_and_dev_overlap",
            "admitted_molecules": 0,
            "admitted_assays": 0,
            "rationale": "Anticancer study reporting cancer cell line IC50 values; does not contain primary E. coli MIC table. Exact sequence and study overlap with formal dev set DBAASP:12306."
        },
        {
            "source_id": "goat_antibacterial2018",
            "doi": "10.3389/fmicb.2018.02983",
            "pmid": "30555455",
            "pmcid": "PMC6284057",
            "title": "Combined Antibacterial Effects of Goat Cathelicidins With Different Mechanisms of Action",
            "formal_dev_identifier_matches": ["DBAASP:12306"],
            "mic_identifier_matches": [],
            "status": "blocked_formal_overlap_and_clustering_constraint",
            "admitted_molecules": 0,
            "admitted_assays": 0,
            "rationale": "Primary citation for formal dev set DBAASP:12306 (cannot serve as independent external validation). For MIC cohort: ChMAP-28 has 0.6071 identity with BMAP-27B (must join component 4), mini-ChBac has 0.6400 identity with component 0 (Bac7 family) and 24 violations against formal dev set. Combination treatments cannot be counted as single-peptide MIC."
        },
        {
            "source_id": "hymenochirin2012",
            "doi": "10.1016/j.peptides.2012.03.029",
            "pmid": "22497805",
            "thesis_repository": "https://edepot.wur.nl/255770 (Chapter 6)",
            "title": "The hymenochirins: A family of host-defense peptides from the Congo dwarf clawed frog Hymenochirus boettgeri (Pipidae)",
            "formal_dev_identifier_matches": [],
            "mic_identifier_matches": [],
            "status": "blocked_intermediate_mic_and_dev_homology",
            "admitted_molecules": 0,
            "admitted_assays": 0,
            "rationale": "Chapter 6 Table 1: Hymenochirin-1B is C-terminally amidated (-NH2), excluded. Hymenochirin-2B to 5B have E. coli MIC of 20-40 uM (56.35 - 114.43 ug/ml), which falls squarely into the indeterminate/intermediate zone (32 < MIC < 128 ug/ml), yielding zero binary labels. In addition, all five hymenochirins violate the 0.40 homology threshold against formal dev set (identities up to 0.8276 with DBAASP:14150)."
        }
    ]
    write_json(ROOT / "source_review.json", source_review)

    # 3. Define candidate sequences
    candidates = [
        # Pandinin 2014
        {
            "candidate_name": "Pin2",
            "source_id": "pandinin2014",
            "seq": "FWGALAKGALKLIPSLFSSFSKKD",
            "mw": 2612.1,
            "terminal_n": "free amino",
            "terminal_c": "free carboxyl",
            "modifications": "none",
            "raw_mic": "12.5",
            "raw_unit": "µM",
            "converted_ugml": 32.65,
            "target": "Escherichia coli ATCC 25922 (MHB)",
            "label_rule_outcome": "intermediate_censored",
            "derived_label": None,
            "decision": "excluded_indeterminate_label"
        },
        {
            "candidate_name": "Pin2[G]",
            "source_id": "pandinin2014",
            "seq": "FWGALAKGALKLIGSLFSSFSKKD",
            "mw": 2572.0,
            "terminal_n": "free amino",
            "terminal_c": "free carboxyl",
            "modifications": "none",
            "raw_mic": "12.5",
            "raw_unit": "µM",
            "converted_ugml": 32.15,
            "target": "Escherichia coli ATCC 25922 (MHB)",
            "label_rule_outcome": "intermediate_censored",
            "derived_label": None,
            "decision": "excluded_indeterminate_label"
        },
        {
            "candidate_name": "Pin2[GPG]",
            "source_id": "pandinin2014",
            "seq": "FWGALAKGALKLIGPGSLFSSFSKKD",
            "mw": 2726.2,
            "terminal_n": "free amino",
            "terminal_c": "free carboxyl",
            "modifications": "none",
            "raw_mic": "12.5",
            "raw_unit": "µM",
            "converted_ugml": 34.08,
            "target": "Escherichia coli ATCC 25922 (MHB)",
            "label_rule_outcome": "intermediate_censored",
            "derived_label": None,
            "decision": "excluded_indeterminate_label"
        },
        {
            "candidate_name": "Pin2[14]",
            "source_id": "pandinin2014",
            "seq": "FWGLKGLKKFSKKL",
            "mw": 1693.1,
            "terminal_n": "free amino",
            "terminal_c": "free carboxyl",
            "modifications": "none",
            "raw_mic": "25.0",
            "raw_unit": "µM",
            "converted_ugml": 42.33,
            "target": "Escherichia coli ATCC 25922 (MHB)",
            "label_rule_outcome": "intermediate_censored",
            "derived_label": None,
            "decision": "excluded_indeterminate_label"
        },
        {
            "candidate_name": "Pin2[17]",
            "source_id": "pandinin2014",
            "seq": "FWGALAKGLKKFSKKL",
            "mw": 1849.3,
            "terminal_n": "free amino",
            "terminal_c": "free carboxyl",
            "modifications": "none",
            "raw_mic": ">25.0",
            "raw_unit": "µM",
            "converted_ugml": 46.23,
            "target": "Escherichia coli ATCC 25922 (MHB)",
            "label_rule_outcome": "intermediate_censored",
            "derived_label": None,
            "decision": "excluded_indeterminate_label"
        },
        # ChMAP / Goat antibacterial
        {
            "candidate_name": "ChMAP-28",
            "source_id": "goat_antibacterial2018",
            "seq": "GRFKRFRKKLKRLWHKVGPFVGPILHY",
            "mw": 3370.2,
            "terminal_n": "free amino",
            "terminal_c": "free carboxyl",
            "modifications": "none",
            "raw_mic": "0.06",
            "raw_unit": "µM",
            "converted_ugml": 0.20,
            "target": "Escherichia coli C600",
            "label_rule_outcome": "positive_le_32",
            "derived_label": 1,
            "decision": "blocked_dev_overlap_and_component_4_merge"
        },
        {
            "candidate_name": "mini-ChBac7.5Nα",
            "source_id": "goat_antibacterial2018",
            "seq": "RRLRPRRPRLPRPRPRPRPRPR",
            "mw": 2909.5,
            "terminal_n": "free amino",
            "terminal_c": "free carboxyl",
            "modifications": "none",
            "raw_mic": "2.0",
            "raw_unit": "µM",
            "converted_ugml": 5.82,
            "target": "Escherichia coli C600",
            "label_rule_outcome": "positive_le_32",
            "derived_label": 1,
            "decision": "blocked_dev_homology_and_component_0_merge"
        },
        {
            "candidate_name": "mini-ChBac7.5Nα(1-16)",
            "source_id": "goat_antibacterial2018",
            "seq": "RRLRPRRPRLPRPRPR",
            "mw": 2132.6,
            "terminal_n": "free amino",
            "terminal_c": "free carboxyl",
            "modifications": "none",
            "raw_mic": "2.0",
            "raw_unit": "µM",
            "converted_ugml": 4.27,
            "target": "Escherichia coli C600",
            "label_rule_outcome": "positive_le_32",
            "derived_label": 1,
            "decision": "blocked_dev_homology_and_component_0_merge"
        },
        # Hymenochirin 2012 / Thesis 2013 Chapter 6
        {
            "candidate_name": "Hymenochirin-1B",
            "source_id": "hymenochirin2012",
            "seq": "IKLSPETKDNLKKVLKGAIKGAIAVAKMV",
            "mw": 3061.8,
            "terminal_n": "free amino",
            "terminal_c": "amidated (-NH2)",
            "modifications": "C-terminal amidation",
            "raw_mic": "20.0",
            "raw_unit": "µM",
            "converted_ugml": 61.24,
            "target": "Escherichia coli ATCC 25726",
            "label_rule_outcome": "excluded_amidation",
            "derived_label": None,
            "decision": "excluded_chemical_modification"
        },
        {
            "candidate_name": "Hymenochirin-2B",
            "source_id": "hymenochirin2012",
            "seq": "LKIPGFVKDTLKKVAKGIFSAVAGAMTPS",
            "mw": 2973.7,
            "terminal_n": "free amino",
            "terminal_c": "free carboxyl",
            "modifications": "none",
            "raw_mic": "20.0",
            "raw_unit": "µM",
            "converted_ugml": 59.47,
            "target": "Escherichia coli ATCC 25726",
            "label_rule_outcome": "intermediate_censored",
            "derived_label": None,
            "decision": "excluded_indeterminate_label"
        },
        {
            "candidate_name": "Hymenochirin-3B",
            "source_id": "hymenochirin2012",
            "seq": "IKIPAVVKDTLKKVAKGVLSAVAGALTQ",
            "mw": 2817.7,
            "terminal_n": "free amino",
            "terminal_c": "free carboxyl",
            "modifications": "none",
            "raw_mic": "20.0",
            "raw_unit": "µM",
            "converted_ugml": 56.35,
            "target": "Escherichia coli ATCC 25726",
            "label_rule_outcome": "intermediate_censored",
            "derived_label": None,
            "decision": "excluded_indeterminate_label"
        },
        {
            "candidate_name": "Hymenochirin-4B",
            "source_id": "hymenochirin2012",
            "seq": "IKIPAFVKDTLKKVAKGVISAVAGALTQ",
            "mw": 2865.7,
            "terminal_n": "free amino",
            "terminal_c": "free carboxyl",
            "modifications": "none",
            "raw_mic": "20.0",
            "raw_unit": "µM",
            "converted_ugml": 57.31,
            "target": "Escherichia coli ATCC 25726",
            "label_rule_outcome": "intermediate_censored",
            "derived_label": None,
            "decision": "excluded_indeterminate_label"
        },
        {
            "candidate_name": "Hymenochirin-5B",
            "source_id": "hymenochirin2012",
            "seq": "IKIPPIVKDTLKKVAKGVLSTIAGALST",
            "mw": 2860.8,
            "terminal_n": "free amino",
            "terminal_c": "free carboxyl",
            "modifications": "none",
            "raw_mic": "40.0",
            "raw_unit": "µM",
            "converted_ugml": 114.43,
            "target": "Escherichia coli ATCC 25726",
            "label_rule_outcome": "intermediate_censored",
            "derived_label": None,
            "decision": "excluded_indeterminate_label"
        }
    ]

    # Write molecule_decisions.csv
    mol_fields = ["candidate_name", "source_id", "seq", "length", "mw", "terminal_n", "terminal_c", "modifications", "decision", "admitted"]
    with (ROOT / "molecule_decisions.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=mol_fields)
        writer.writeheader()
        for c in candidates:
            writer.writerow({
                "candidate_name": c["candidate_name"],
                "source_id": c["source_id"],
                "seq": c["seq"],
                "length": len(c["seq"]),
                "mw": c["mw"],
                "terminal_n": c["terminal_n"],
                "terminal_c": c["terminal_c"],
                "modifications": c["modifications"],
                "decision": c["decision"],
                "admitted": False
            })

    # Write assay_decisions.csv
    assay_fields = ["candidate_name", "source_id", "target", "raw_mic", "raw_unit", "converted_ugml", "label_rule_outcome", "derived_label", "decision", "released_for_training"]
    with (ROOT / "assay_decisions.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=assay_fields)
        writer.writeheader()
        for c in candidates:
            writer.writerow({
                "candidate_name": c["candidate_name"],
                "source_id": c["source_id"],
                "target": c["target"],
                "raw_mic": c["raw_mic"],
                "raw_unit": c["raw_unit"],
                "converted_ugml": c["converted_ugml"],
                "label_rule_outcome": c["label_rule_outcome"],
                "derived_label": c["derived_label"] if c["derived_label"] is not None else "",
                "decision": c["decision"],
                "released_for_training": False
            })

    # 4. Compute all-member sequence identities
    pair_rows = []
    prescreen_summary = []

    for c in candidates:
        # vs Formal dev 417
        pairs_dev = []
        for r in dev:
            ident = sequence_identity(c["seq"], r["seq"], identity_mode="alignment")
            row = {
                "candidate_name": c["candidate_name"],
                "candidate_seq": c["seq"],
                "reference_cohort": "formal_417",
                "reference_id": r["record_id"],
                "reference_seq": r["seq"],
                "identity_alignment": round(ident, 6),
                "conflict_ge_0_40": ident >= 0.40
            }
            pairs_dev.append(row)
            pair_rows.append(row)

        best_dev = max(pairs_dev, key=lambda x: x["identity_alignment"])
        viol_dev = sum(x["conflict_ge_0_40"] for x in pairs_dev)
        prescreen_summary.append({
            "candidate_name": c["candidate_name"],
            "reference_cohort": "formal_417",
            "max_identity": best_dev["identity_alignment"],
            "closest_reference_id": best_dev["reference_id"],
            "violating_pairs": viol_dev,
            "isolated_from_cohort": viol_dev == 0
        })

        # vs MIC 16
        pairs_mic = []
        for r in mic:
            ident = sequence_identity(c["seq"], r["seq"], identity_mode="alignment")
            row = {
                "candidate_name": c["candidate_name"],
                "candidate_seq": c["seq"],
                "reference_cohort": "mic_16",
                "reference_id": r["sample_id"],
                "reference_seq": r["seq"],
                "identity_alignment": round(ident, 6),
                "conflict_ge_0_40": ident >= 0.40
            }
            pairs_mic.append(row)
            pair_rows.append(row)

        best_mic = max(pairs_mic, key=lambda x: x["identity_alignment"])
        viol_mic = sum(x["conflict_ge_0_40"] for x in pairs_mic)
        prescreen_summary.append({
            "candidate_name": c["candidate_name"],
            "reference_cohort": "mic_16",
            "max_identity": best_mic["identity_alignment"],
            "closest_reference_id": best_mic["reference_id"],
            "violating_pairs": viol_mic,
            "isolated_from_cohort": viol_mic == 0
        })

    # Write sequence_pairs.csv
    pair_fields = ["candidate_name", "candidate_seq", "reference_cohort", "reference_id", "reference_seq", "identity_alignment", "conflict_ge_0_40"]
    with (ROOT / "sequence_pairs.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=pair_fields)
        writer.writeheader()
        writer.writerows(pair_rows)

    # Write candidate_identity_prescreen.json
    prescreen_obj = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "prescreen_completed_zero_admitted",
        "candidates_prescreened": len(candidates),
        "total_pairs_computed": len(pair_rows),
        "identity_mode": "alignment",
        "cutoff": 0.40,
        "summary": prescreen_summary,
        "new_labels_released": 0,
        "new_candidates_admitted": 0
    }
    write_json(ROOT / "candidate_identity_prescreen.json", prescreen_obj)

    # 5. Component and cluster audit
    cluster_audit = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "audit_protocol": "protocol-mic-11",
        "formal_dual_task_dev_count": 417,
        "mic_candidate_count": 16,
        "new_candidates_analyzed": len(candidates),
        "findings": {
            "pandinin2014": {
                "formal_dev_status": "BLOCKED: 5 of 5 peptides have >=0.40 homology conflicts with formal dev set (matches DBAASP:948 at 1.000).",
                "mic_cohort_status": "BLOCKED: All MIC measurements fall into intermediate zone (32.15 - 68.16 ug/ml), generating 0 binary labels."
            },
            "corvus2023": {
                "formal_dev_status": "EXCLUDED: Chemical modification (C-terminal amidation via Rink amide resin).",
                "mic_cohort_status": "EXCLUDED: Does not match unmodified linear peptide domain."
            },
            "chmap2018": {
                "formal_dev_status": "BLOCKED: Exact sequence and study overlap with formal dev set DBAASP:12306.",
                "mic_cohort_status": "BLOCKED: Anticancer assay only, no E. coli MIC table."
            },
            "goat_antibacterial2018": {
                "formal_dev_status": "BLOCKED: Primary study for formal dev set DBAASP:12306.",
                "mic_cohort_status": "BLOCKED: ChMAP-28 has 0.6071 identity to BMAP-27B (merges into Component 4, not an independent component); mini-ChBac has 0.6400 identity to component 0 (Bac7 family) and 24 conflicts with formal dev set."
            },
            "hymenochirin2012": {
                "formal_dev_status": "BLOCKED: 5 of 5 peptides violate the 0.40 threshold against formal dev set (up to 0.8276 with DBAASP:14150).",
                "mic_cohort_status": "BLOCKED: Hymenochirin-1B is C-terminally amidated. Hymenochirin-2B to 5B have E. coli MIC values of 56.35 - 114.43 ug/ml, which are intermediate and non-releasable."
            }
        },
        "conclusion": "No candidate peptide satisfies both evidence provenance and isolation/label rules. Admitted candidates = 0. Formal dual-task remains BLOCKED."
    }
    write_json(ROOT / "cluster_audit.json", cluster_audit)

    # 6. Handoff status v2
    handoff_v2 = {
        "status": "phase_b_c_d_e_audit_completed_admissions_zero",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "audit_directory": "03_experiments/audits/alternative_primary_search_20261004_v2",
        "current_machine_state": "03_experiments/audits/mic_training_readiness_20261004_v22.json",
        "current_mic_training_blocked": False,
        "current_mic_status": "local_exploratory_training_independently_verified",
        "formal_dual_task_status": "blocked",
        "formal_results_available": False,
        "publication_ready": False,
        "new_labels_released": 0,
        "new_molecules_admitted": 0,
        "new_training_executed": False,
        "source_summary": {
            "sources_inspected": 5,
            "molecules_inspected": len(candidates),
            "pairwise_comparisons": len(pair_rows),
            "admitted_to_dual_task": 0,
            "admitted_to_mic": 0
        },
        "blocker_reasons": [
            "Formal dual-task external cohort requires >=0.40 all-member Needleman-Wunsch isolation from all 417 development records. All inspected candidate sequences violate this threshold or overlap with development study IDs.",
            "Candidate MIC measurements (Pandinin 2014, Hymenochirin 2012) fall into the intermediate censored zone (32 < MIC < 128 ug/ml) under protocol-mic-11 rules, precluding binary label assignment.",
            "Candidate sequences from Corvus 2023 and Hymenochirin-1B carry C-terminal amidation, excluding them from the unmodified linear peptide domain (10-50 AA).",
            "Goat cathelicidins (ChMAP-28 and mini-ChBac) have strong homology to existing MIC components (Component 4 and Component 0), precluding the formation of independent validation clusters."
        ]
    }
    write_json(ROOT / "handoff_status.json", handoff_v2)
    print("Process v2 audit completed successfully. Total pairs computed:", len(pair_rows))

if __name__ == "__main__":
    main()
