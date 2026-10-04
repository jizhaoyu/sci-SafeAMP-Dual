"""Curate independent external validation cohort from measured assay records.

Enforces:
1. Canonical 10-50 AA linear unmodified monomeric peptides.
2. Verified binary experimental endpoints (E. coli MIC, human erythrocyte HC50).
3. Complete provenance: record_id, raw_path, raw_sha256, accession, DOI/PMID, label basis.
4. Source role explicitly set to 'external'.
5. All-member sequence and primary-study isolation against development cohort.
"""
import argparse
import json
from pathlib import Path
from typing import Optional
import pandas as pd

from feature_extractor import clean_sequence
from research_data import sequence_identity, source_study_ids, REQUIRED
from research_utils import ROOT, sha256, utc_now, write_json
from evidence_validation import validate_source_evidence, derive_external_labels, DEFAULT_DISALLOWED_DOIS


def build_external_cohort(
    dev_records_path: Path,
    output_dir: Path,
    raw_entries_path: Optional[Path] = None,
    cutoff: float = 0.40,
) -> pd.DataFrame:
    if raw_entries_path is None:
        raise ValueError("External cohort curation requires explicit raw experimental assay input; handwritten default entries are forbidden.")
    if cutoff != 0.40:
        raise ValueError('The frozen strict protocol requires cutoff=0.40.')

    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ValueError('Output exists; use a new versioned external cohort directory.')
    output_dir.mkdir(parents=True)

    # 1. Load development cohort to check orthogonality
    dev_df = pd.read_csv(dev_records_path)
    dev_seqs = sorted(set(dev_df["seq"].map(clean_sequence)))
    dev_studies = set().union(*(source_study_ids(row) for row in dev_df.itertuples()))

    # 2. Load candidate entries
    raw_entries_path = Path(raw_entries_path)
    if not raw_entries_path.is_file():
        raise FileNotFoundError(f"Raw external entries file not found: {raw_entries_path}")

    raw_data = json.loads(raw_entries_path.read_text(encoding="utf-8"))
    entries = raw_data if isinstance(raw_data, list) else raw_data.get("records", [])

    rel_raw_path = str(raw_entries_path.resolve())
    try:
        rel_raw_path = str(raw_entries_path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        pass
    raw_sha = sha256(raw_entries_path)

    external_records = []
    rejections = []

    for entry in entries:
        if not isinstance(entry, dict):
            rejections.append({"id": None, "reason": "invalid_raw_entry"})
            continue
        eid = entry.get("id") or entry.get("record_id")
        if not eid:
            rejections.append({"id": None, "reason": "missing_record_identifier"})
            continue
        try:
            seq = clean_sequence(entry["seq"])
        except Exception:
            rejections.append({"id": eid, "reason": "noncanonical_amino_acid"})
            continue

        db = entry.get("db", "CuratedBenchmark")
        if str(db).upper() == 'DBAASP':
            rejections.append({"id": eid, "reason": "development_database_cannot_be_external_source"})
            continue
        acc = entry.get("acc", eid)

        # Length check
        if not (10 <= len(seq) <= 50):
            rejections.append({"id": eid, "reason": "length_out_of_range"})
            continue

        # Original measurements, not typed binary labels, determine inclusion.
        amp_val, hemo_val, assay_issues = derive_external_labels(entry, seq)
        if assay_issues:
            rejections.append({"id": eid, "reason": "; ".join(assay_issues)})
            continue

        doi = str(entry.get('doi') or '').lower().strip()
        pmid = str(entry.get('pmid') or '').strip()
        if not doi and not pmid:
            rejections.append({"id": eid, "reason": "missing_primary_assay_reference"})
            continue
        if any(disallowed in doi for disallowed in DEFAULT_DISALLOWED_DOIS):
            rejections.append({"id": eid, "reason": "database_summary_doi_is_not_primary_assay_reference"})
            continue
        study_ids = ({f'doi:{doi}'} if doi else set()) | ({f'pmid:{pmid}'} if pmid else set())
        if study_ids & dev_studies:
            rejections.append({"id": eid, "reason": "primary_study_overlap_with_development"})
            continue

        # Compare each candidate to every development member with the frozen identity.
        if seq in dev_seqs:
            rejections.append({"id": eid, "reason": "exact_dev_overlap"})
            continue

        max_identity = max(
            (sequence_identity(seq, dev_seq, identity_mode='alignment') for dev_seq in dev_seqs),
            default=0.0,
        )
        if max_identity >= cutoff:
            rejections.append({"id": eid, "reason": f"all_member_homology_to_development_{max_identity:.3f}"})
            continue

        record = {
            "record_id": f"EXT_{db}_{acc}",
            "seq": seq,
            "amp": amp_val,
            "hemo": hemo_val,
            "source_dataset": f"Curated_{db}",
            "source_accession": acc,
            "source_url": f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "evidence_reference": json.dumps([{"source": db, "id": acc, "doi": doi, "pmid": pmid}]),
            "label_basis": "Ecoli_MIC_ugml_32_128;human_HC50_ugml_100_250;derived_from_raw_assays",
            "assay_conditions": json.dumps(entry.get("assays") or entry.get("observations") or []),
            "modifications": "none",
            "evidence_type": "experimental",
            "is_synthetic": False,
            "source_role": "external",
            "raw_path": rel_raw_path,
            "raw_sha256": raw_sha,
        }
        external_records.append(record)

    ext_df = pd.DataFrame(external_records, columns=REQUIRED)
    if not ext_df.empty:
        validate_source_evidence(ext_df)
    ext_df.to_csv(output_dir / "records.csv", index=False)
    write_json(output_dir / "exclusions.json", rejections)

    manifest = {
        "status": "curated" if len(ext_df) else "blocked",
        "created_at": utc_now(),
        "total_curated_records": len(ext_df),
        "amp_positive": int((ext_df["amp"] == 1).sum()),
        "amp_negative": int((ext_df["amp"] == 0).sum()),
        "hemo_positive": int((ext_df["hemo"] == 1).sum()),
        "hemo_negative": int((ext_df["hemo"] == 0).sum()),
        "rejections": len(rejections),
        "records_sha256": sha256(output_dir / "records.csv"),
        "raw_input_sha256": raw_sha,
        "identity_mode": "alignment",
        "cutoff": cutoff,
    }
    write_json(output_dir / "source_manifest.json", manifest)
    return ext_df


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dev", type=Path, required=True)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--cutoff", type=float, default=0.40)
    args = p.parse_args()
    build_external_cohort(args.dev, args.output, raw_entries_path=args.raw, cutoff=args.cutoff)
