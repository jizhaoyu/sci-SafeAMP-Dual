"""Build a non-formal, source-verified DRAMP supplement candidate table.

Only records with exact sequence/name/MIC matches to primary papers are handled
here. The script leaves the formal dataset untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from assay_records import SingleAssayObservation, evaluate_assay_for_amp
from research_data import REQUIRED, sequence_identity, source_study_ids, validate_records
from research_protocol_config import get_protocol, protocol_digest
from research_utils import ROOT


ARTICLE = {
    "pmid": "22467870",
    "doi": "10.1074/jbc.M111.338970",
    "title": "Novel Cyclotides and Uncyclotides with Highly Shortened Precursors from Chassalia chartacea and Effects of Methionine Oxidation on Bioactivities",
    "journal": "Journal of Biological Chemistry",
    "year": 2012,
    "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3366795/",
}

ARTICLE_PLP2 = {
    "pmid": "30658410",
    "doi": "10.3390/toxins11010050",
    "title": "Mass Spectrometry Analysis and Biological Characterization of the Predatory Ant Odontomachus monticola Venom and Venom Sac Components",
    "journal": "Toxins",
    "year": 2019,
    "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6356579/",
}

ARTICLE_CN_AMP2 = {
    "pmid": "19111587",
    "doi": "10.1016/j.peptides.2008.12.001",
    "title": "Identification and structural insights of three novel antimicrobial peptides isolated from green coconut water",
    "journal": "Peptides",
    "year": 2009,
    "url": "https://doi.org/10.1016/j.peptides.2008.12.001",
    "author_full_text_url": "https://www.researchgate.net/publication/23708261_Identification_and_structural_insights_of_three_novel_antimicrobial_peptides_isolated_from_green_coconut_water",
}

CANDIDATES = {
    "DRAMP00336": {"name": "ChaC7 (Chassatide C7; uncyclotides; Plant defensin)", "mic": "6.4"},
    "DRAMP00337": {"name": "ChaC8 (Chassatide C8; uncyclotides; Plant defensin)", "mic": "6.6"},
    "DRAMP00338": {"name": "ChaC11 (Chassatide C11; uncyclotides; Plant defensin)", "mic": "8.5"},
    "DRAMP21455": {
        "name": "PLP2 (Insects, animals)",
        "mic": "<6.2",
        "pmid": ARTICLE_PLP2["pmid"],
        "target": "Escherichia coli NBRC 14237",
        "conditions": "Synthetic PLP2; Table 3 reports E. coli NBRC 14237 MIC. The paper states antimicrobial assays were conducted as described in PMID 15246874.",
        "assay_method": "MIC assay (method cited to PMID 15246874)",
        "method_reference": {"pmid": "15246874", "doi": "10.1016/j.abb.2004.05.013"},
    },
    "DRAMP00930": {
        "name": "Antimicrobial peptide 2 (Cn-AMP2; Plant defensin)",
        "mic": "170",
        "unit": "µg/mL",
        "pmid": ARTICLE_CN_AMP2["pmid"],
        "target": "Escherichia coli (strain not stated)",
        "conditions": "Purified Cn-AMP2 (fraction F2); growth-inhibition-zone assay on nutrient-medium plates; paper Methods 2.3 and Table 1. E. coli strain identifier not stated.",
        "assay_method": "growth-inhibition-zone assay",
        "medium": "nutrient medium (plate); detailed composition not stated",
        "paper_location": "Methods 2.3; Table 1 MIC; Table 2 sequence",
        "identified_target": False,
    },
}

ARTICLES = {article["pmid"]: article for article in (ARTICLE, ARTICLE_PLP2, ARTICLE_CN_AMP2)}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build(source_xlsx: Path, development_csv: Path, output_dir: Path) -> dict:
    source_xlsx = Path(source_xlsx)
    development_csv = Path(development_csv)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing candidate directory: {output_dir}")
    output_dir.mkdir(parents=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir()
    raw_path = raw_dir / "primary_assay_evidence.json"
    raw_path_relative = raw_path.resolve().relative_to(ROOT).as_posix()

    source = pd.read_excel(source_xlsx).fillna("")
    development = pd.read_csv(development_csv)
    spec = get_protocol("protocol-amd-02")
    records = []
    raw_records = []
    similarity_rows = []
    pending_rows = []

    for accession, expected in CANDIDATES.items():
        matches = source[source["DRAMP_ID"].astype(str).eq(accession)]
        if len(matches) != 1:
            raise ValueError(f"Expected one DRAMP row for {accession}; got {len(matches)}")
        row = matches.iloc[0]
        sequence = str(row["Sequence"]).strip().upper()
        name = str(row["Name"]).strip()
        if name != expected["name"]:
            raise ValueError(f"DRAMP name mismatch for {accession}: {name!r}")
        article = ARTICLES.get(expected.get("pmid", ARTICLE["pmid"]))
        if expected["mic"] not in str(row["Target_Organism"]) or "Escherichia coli" not in str(row["Target_Organism"]):
            raise ValueError(f"Expected E. coli MIC {expected['mic']} not found for {accession}")
        if str(row["Pubmed_ID"]).strip() != article["pmid"]:
            raise ValueError(f"Primary PMID mismatch for {accession}")
        if str(row["Linear/Cyclic/Branched"]).strip().lower() != "linear":
            raise ValueError(f"Peptide is not explicitly linear for {accession}")
        for column in ("N-terminal_Modification", "C-terminal_Modification", "Other_Modifications"):
            value = str(row[column]).strip().lower()
            if value not in {"", "none", "free", "not available", "nan"}:
                raise ValueError(f"Unsupported modification for {accession}: {column}={value}")

        if expected.get("identified_target") is False:
            pending_rows.append({
                "dramp_id": accession,
                "sequence": sequence,
                "primary_pmid": article["pmid"],
                "raw_mic": f"{expected['mic']} {expected['unit']}",
                "issue": "Primary paper names E. coli but gives no strain or isolate identifier; protocol-mic-01 evidence requirement is unmet.",
                "status": "excluded_pending_primary_strain_verification",
            })
            continue

        is_plp2 = accession == "DRAMP21455"
        mic_unit = expected.get("unit", "µM")
        assay = SingleAssayObservation(
            endpoint="amp",
            target_organism_or_cell=expected.get("target", "Escherichia coli ATCC 25922"),
            metric_name="MIC",
            raw_value=expected["mic"],
            raw_unit=mic_unit,
            conditions=expected.get("conditions", "Radial diffusion assay; E. coli ATCC 25922 cultured in trypticase soy broth; see PMID 22467870."),
            reference=f"PMID:{article['pmid']}; DOI:{article['doi']}" + (f"; assay-method reference PMID:{expected['method_reference']['pmid']}" if expected.get("method_reference") else ""),
        )
        evaluate_assay_for_amp(assay, sequence)
        if not assay.eligible or assay.derived_label is None:
            raise ValueError(f"Assay did not yield a definitive label for {accession}: {assay.ineligibility_reason}")

        raw_records.append({
            "id": accession,
            "record_id": f"DRAMP:{accession}",
            "db": "DRAMP",
            "seq": sequence,
            "pmid": article["pmid"],
            "doi": article["doi"],
            "paper_location": expected.get("paper_location", "primary paper results table"),
            "observations": [{
                "endpoint": "amp",
                "target_organism_or_cell": assay.target_organism_or_cell,
                "metric_name": assay.metric_name,
                "raw_value": assay.raw_value,
                "raw_unit": assay.raw_unit,
                "conditions": assay.conditions,
                "reference": assay.reference,
                "assay_method": expected.get("assay_method", "radial diffusion assay"),
                "medium": expected.get("medium", "not stated in the screened record" if is_plp2 else "trypticase soy broth"),
            }],
        })

        max_identity = -1.0
        closest_record = ""
        for dev in development.itertuples():
            identity = sequence_identity(sequence, str(dev.seq), identity_mode="alignment")
            if identity > max_identity:
                max_identity, closest_record = identity, str(dev.record_id)
        dev_studies = set().union(*(source_study_ids(r) for r in development.itertuples()))
        exact_overlap = sequence in set(development["seq"].astype(str).str.upper())
        publication_overlap = (
            f"pmid:{article['pmid']}" in dev_studies
            or f"doi:{article['doi'].lower()}" in dev_studies
        )
        similarity_rows.append({
            "record_id": f"DRAMP:{accession}",
            "sequence": sequence,
            "mic_raw": f"{expected['mic']} {mic_unit}",
            "normalized_mic_ug_ml": assay.normalized_low_ug_ml,
            "normalized_mic_upper_bound_ug_ml": assay.normalized_high_ug_ml,
            "derived_amp_label": assay.derived_label,
            "max_development_identity": max_identity,
            "closest_development_record_id": closest_record,
            "violates_0_40_cutoff": max_identity >= spec.cutoff,
            "exact_development_overlap": exact_overlap,
            "publication_overlap": publication_overlap,
            "primary_pmid": article["pmid"],
        })
        records.append({
            "record_id": f"DRAMP:{accession}",
            "seq": sequence,
            "amp": assay.derived_label,
            "hemo": float("nan"),
            "source_dataset": "DRAMP",
            "source_accession": accession,
            "source_url": f"https://cpu-bioinfor.org/browse/All_Information.php?id={accession}&dataset=General",
            "evidence_reference": json.dumps([{
                "doi": article["doi"],
                "title": article["title"],
                "journal": article["journal"],
                "year": article["year"],
                "pubmed": {"pubmedId": article["pmid"], "pubmedUrl": f"https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/"},
            }] + ([{
                "doi": expected["method_reference"]["doi"],
                "pubmed": {"pubmedId": expected["method_reference"]["pmid"], "pubmedUrl": f"https://pubmed.ncbi.nlm.nih.gov/{expected['method_reference']['pmid']}/"},
                "role": "assay method cited by the primary article",
            }] if expected.get("method_reference") else []), ensure_ascii=False),
            "label_basis": "Ecoli_MIC_ugml_32_128;human_HC50_ugml_100_250;conflicts_missing",
            "assay_conditions": json.dumps({
                "amp": [{"target": assay.target_organism_or_cell,
                         "method": expected.get("assay_method", "radial diffusion assay"),
                         "medium": expected.get("medium", "not stated in the screened record" if is_plp2 else "trypticase soy broth"),
                         "raw_value": assay.raw_value, "raw_unit": assay.raw_unit}],
                "hemo": [],
            }, ensure_ascii=False),
            "modifications": "none",
            "evidence_type": "experimental",
            "is_synthetic": False,
            "source_role": "development",
            "raw_path": raw_path_relative,
            "raw_sha256": "",
        })

    raw_path.write_text(json.dumps({"articles": list(ARTICLES.values()), "records": raw_records}, ensure_ascii=False, indent=2), encoding="utf-8")
    raw_hash = file_sha256(raw_path)
    for record in records:
        record["raw_sha256"] = raw_hash

    candidate_frame = pd.DataFrame(records, columns=REQUIRED)
    candidate_frame = validate_records(candidate_frame, verify_raw=True)
    candidate_path = output_dir / "records.csv"
    candidate_frame.to_csv(candidate_path, index=False, encoding="utf-8-sig")
    pending_path = output_dir / "pending_primary_review.csv"
    pd.DataFrame(pending_rows, columns=["dramp_id", "sequence", "primary_pmid", "raw_mic", "issue", "status"]).to_csv(
        pending_path, index=False, encoding="utf-8-sig")
    similarity_path = output_dir / "similarity_audit.csv"
    pd.DataFrame(similarity_rows).to_csv(similarity_path, index=False, encoding="utf-8-sig")
    candidate_pair_rows = []
    candidate_sequences = candidate_frame["seq"].astype(str).tolist()
    pair_parent = list(range(len(candidate_sequences)))

    def find_root(index: int) -> int:
        while pair_parent[index] != index:
            pair_parent[index] = pair_parent[pair_parent[index]]
            index = pair_parent[index]
        return index

    for i in range(len(candidate_sequences)):
        for j in range(i):
            identity = sequence_identity(candidate_sequences[i], candidate_sequences[j], identity_mode="alignment")
            candidate_pair_rows.append({
                "record_id_a": candidate_frame.iloc[i].record_id,
                "record_id_b": candidate_frame.iloc[j].record_id,
                "identity": identity,
                "same_component_at_0_40": identity >= spec.cutoff,
            })
            if identity >= spec.cutoff:
                pair_parent[find_root(i)] = find_root(j)
    candidate_pair_path = output_dir / "candidate_pair_similarity.csv"
    pd.DataFrame(candidate_pair_rows, columns=["record_id_a", "record_id_b", "identity", "same_component_at_0_40"]).to_csv(candidate_pair_path, index=False, encoding="utf-8-sig")
    candidate_component_count = len({find_root(i) for i in range(len(candidate_sequences))})

    source_file_hash = file_sha256(source_xlsx)
    manifest = {
        "status": "evidence_verified_candidate_supplement_not_formal_release",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_database": "DRAMP",
        "source_release": "DRAMP 3.0 antibacterial export",
        "source_file": str(source_xlsx),
        "source_sha256": source_file_hash,
        "development_file": str(development_csv),
        "development_sha256": file_sha256(development_csv),
        "development_count": len(development),
        "protocol_id": spec.protocol_id,
        "protocol_digest": protocol_digest(spec),
        "cutoff": spec.cutoff,
        "primary_articles": list(ARTICLES.values()),
        "record_count": len(candidate_frame),
        "pending_primary_review_count": len(pending_rows),
        "positive_amp_records": int(candidate_frame.amp.eq(1).sum()),
        "negative_amp_records": int(candidate_frame.amp.eq(0).sum()),
        "missing_hemo_records": int(candidate_frame.hemo.isna().sum()),
        "all_primary_assays_validated_by_project_gate": True,
        "all_records_below_0_40_vs_development": bool((~pd.DataFrame(similarity_rows).violates_0_40_cutoff).all()),
        "candidate_internal_pair_count": len(candidate_pair_rows),
        "candidate_internal_edges_at_0_40": sum(row["same_component_at_0_40"] for row in candidate_pair_rows),
        "candidate_internal_components_at_0_40": candidate_component_count,
        "no_exact_or_publication_overlap_with_development": bool((~pd.DataFrame(similarity_rows).exact_development_overlap & ~pd.DataFrame(similarity_rows).publication_overlap).all()),
        "reason_not_formally_merged": "The current MIC-only cohort and formal prepared cohort remain unchanged; the new supplement needs a full combined-cohort evidence and fold-feasibility audit before use.",
        "outputs": {
            "records": str(candidate_path),
            "pending_primary_review": str(pending_path),
            "similarity_audit": str(similarity_path),
            "candidate_pair_similarity": str(candidate_pair_path),
            "raw_primary_evidence": str(raw_path),
            "raw_primary_evidence_sha256": raw_hash,
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.development, args.output), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
