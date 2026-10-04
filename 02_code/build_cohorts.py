"""Build unified and strictly isolated development and external cohorts.

Combines:
- Development cohort: DBAASP v1 (417 experimental records)
- External cohort: Separately sourced experimental records with full assay provenance

Applies:
1. Exact sequence deduplication against development cohort.
2. Literature / PMID / DOI overlap checking against development cohort.
3. Orthogonal homology isolation under CD-HIT standard (Protocol Amendment 01).
4. Full provenance tracking, raw file checksums, and exclusion auditing.
"""
import argparse
import json
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd

from feature_extractor import clean_sequence
from cdhit_cluster import cdhit_cluster_sequences
from research_data import sequence_identity, validate_records, REQUIRED, TASKS
from research_utils import ROOT, sha256, utc_now, write_json


def extract_dev_pmids_and_dois(dev_df: pd.DataFrame) -> tuple[set[str], set[str]]:
    pmids, dois = set(), set()
    for ref_str in dev_df["evidence_reference"].dropna():
        try:
            articles = json.loads(ref_str) if isinstance(ref_str, str) else []
            for art in articles:
                pubmed = art.get("pubmed") if isinstance(art.get("pubmed"), dict) else {}
                pmid = pubmed.get("pubmedId") or art.get("pubmedId") or art.get("pmid")
                if pmid:
                    pmids.add(str(pmid).strip())
                doi = art.get("doi")
                if doi:
                    dois.add(str(doi).lower().strip())
        except Exception:
            pass
    return pmids, dois


def extract_record_pmids_and_dois(row) -> tuple[set[str], set[str]]:
    pmids, dois = set(), set()
    ref_str = getattr(row, "evidence_reference", None)
    if ref_str and not pd.isna(ref_str):
        try:
            articles = json.loads(ref_str) if isinstance(ref_str, str) else []
            for art in articles:
                if isinstance(art, dict):
                    pubmed = art.get("pubmed") if isinstance(art.get("pubmed"), dict) else {}
                    pmid = pubmed.get("pubmedId") or art.get("pubmedId") or art.get("pmid")
                    if pmid:
                        pmids.add(str(pmid).strip())
                    doi = art.get("doi")
                    if doi:
                        dois.add(str(doi).lower().strip())
        except Exception:
            pass
    url = getattr(row, "source_url", "")
    if url and "doi.org/" in str(url):
        doi_part = str(url).split("doi.org/")[-1].strip().lower()
        if doi_part:
            dois.add(doi_part)
    return pmids, dois


def build_cohorts(
    dev_records_path: Path,
    output_dir: Path,
    external_records_path: Optional[Path] = None,
    cutoff: float = 0.40,
    identity_mode: str = "max",
) -> pd.DataFrame:
    if external_records_path is None:
        raise ValueError("An external candidate records file must be explicitly provided via --external; handwritten default entries are forbidden.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Development Cohort
    dev_records_path = Path(dev_records_path)
    dev_df = pd.read_csv(dev_records_path)
    validate_records(dev_df, verify_raw=True)
    dev_seqs = list(set(dev_df["seq"].map(clean_sequence)))
    dev_pmids, dev_dois = extract_dev_pmids_and_dois(dev_df)

    # Compute CD-HIT representatives of development cohort
    _, dev_reps, _ = cdhit_cluster_sequences(dev_seqs, cutoff=cutoff, min_length_ratio=0.50)
    print(f"[Build Cohorts] Development cohort loaded: {len(dev_df)} records, {len(dev_reps)} CD-HIT cluster representatives.")

    # 2. Load and Validate External Cohort
    external_records_path = Path(external_records_path)
    if not external_records_path.is_file():
        raise FileNotFoundError(f"External records file not found: {external_records_path}")

    ext_candidates = pd.read_csv(external_records_path)
    validate_records(ext_candidates, verify_raw=True)

    external_records = []
    exclusions = []

    for row in ext_candidates.itertuples():
        eid = getattr(row, "record_id")
        try:
            seq = clean_sequence(getattr(row, "seq"))
        except Exception:
            exclusions.append({"id": eid, "reason": "noncanonical_amino_acid"})
            continue

        if not (10 <= len(seq) <= 50):
            exclusions.append({"id": eid, "reason": "length_out_of_range"})
            continue

        if seq in dev_seqs:
            exclusions.append({"id": eid, "reason": "exact_sequence_overlap_with_development"})
            continue

        # Check literature overlap against development
        row_pmids, row_dois = extract_record_pmids_and_dois(row)
        pmid_overlap = row_pmids & dev_pmids
        doi_overlap = row_dois & dev_dois
        if pmid_overlap or doi_overlap:
            exclusions.append({
                "id": eid,
                "reason": f"literature_overlap_with_development (pmid={pmid_overlap}, doi={doi_overlap})"
            })
            continue

        # Check homology isolation against development
        if identity_mode == "max":
            max_id = max(
                (sequence_identity(seq, d, identity_mode="max") for d in dev_seqs),
                default=0.0
            )
        else:
            max_id = max(
                (sequence_identity(seq, r) for r in dev_reps
                 if len(seq)/len(r) >= 0.50 and len(r)/len(seq) >= 0.50),
                default=0.0
            )

        if max_id >= cutoff:
            exclusions.append({"id": eid, "reason": f"homology_cross_isolation_violation_{max_id:.3f}"})
            continue

        external_records.append({col: getattr(row, col) for col in REQUIRED})

    ext_df = pd.DataFrame(external_records, columns=REQUIRED)
    print(f"[Build Cohorts] External cohort curated: {len(ext_df)} records (AMP pos={(ext_df['amp']==1).sum()}, neg={(ext_df['amp']==0).sum()}; Hemo pos={(ext_df['hemo']==1).sum()}, neg={(ext_df['hemo']==0).sum()}).")

    # Combine development and external cohorts
    combined_df = pd.concat([dev_df, ext_df], ignore_index=True)
    combined_records_path = output_dir / "records.csv"
    combined_df.to_csv(combined_records_path, index=False)
    write_json(output_dir / "exclusions.json", exclusions)

    manifest = {
        "status": "cohorts_built",
        "created_at": utc_now(),
        "total_records": len(combined_df),
        "development_records": len(dev_df),
        "external_records": len(ext_df),
        "cutoff": cutoff,
        "identity_mode": identity_mode,
        "development_cdhit_clusters": len(dev_reps),
        "records_sha256": sha256(combined_records_path),
        "external_exclusions": len(exclusions),
    }
    write_json(output_dir / "manifest.json", manifest)
    print(f"[Build Cohorts] Combined dataset written to {combined_records_path} (Total: {len(combined_df)} records).")
    return combined_df


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dev", type=Path, required=True)
    p.add_argument("--external", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--cutoff", type=float, default=0.40)
    p.add_argument("--identity-mode", type=str, default="max")
    a = p.parse_args()
    build_cohorts(a.dev, a.output, external_records_path=a.external, cutoff=a.cutoff, identity_mode=a.identity_mode)
