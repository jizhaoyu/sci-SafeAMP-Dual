"""Screen a DRAMP antibacterial export for E. coli MIC evidence.

This is a source-discovery audit only. It never derives model labels or changes
the formal development cohort. Every parsed MIC remains pending verification
against the cited primary experiment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from feature_extractor import STANDARD_AMINO_ACIDS
from research_data import sequence_identity
from research_protocol_config import get_protocol, protocol_digest


MIC_RE = re.compile(
    r"(?P<organism>(?:Escherichia\s+coli|E\.?\s*coli)[^,;)]{0,100}?)\s*"
    r"\(\s*MIC\s*(?:=|:)?\s*(?P<value>[<>≤≥]?\s*[\d.]+(?:\s*[-–]\s*[\d.]+)?)\s*"
    r"(?P<unit>µg|μg|ug|mg|µM|μM|uM|nM|mM)\s*/?\s*(?:ml|mL)?\s*\)",
    re.IGNORECASE,
)
PMID_RE = re.compile(r"\d{5,9}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_unmodified_sequence(row: pd.Series) -> tuple[str | None, str]:
    raw = str(row.get("Sequence", "")).strip().upper()
    if not raw or raw == "NAN" or any(letter not in STANDARD_AMINO_ACIDS for letter in raw):
        return None, "noncanonical_or_missing_sequence"
    if not 10 <= len(raw) <= 50:
        return None, "length_outside_10_50"
    if str(row.get("Linear/Cyclic/Branched", "")).strip().lower() != "linear":
        return None, "not_explicitly_linear"
    allowed = {"", "none", "free", "not available", "nan"}
    for col in ("N-terminal_Modification", "C-terminal_Modification", "Other_Modifications"):
        if str(row.get(col, "")).strip().lower() not in allowed:
            return None, f"modification:{col}"
    return raw, "eligible_for_source_review"


def screen(source_xlsx: Path, development_csv: Path, out_dir: Path) -> dict:
    source_xlsx, development_csv, out_dir = map(Path, (source_xlsx, development_csv, out_dir))
    if out_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing audit directory: {out_dir}")
    out_dir.mkdir(parents=True)

    source = pd.read_excel(source_xlsx).fillna("")
    development = pd.read_csv(development_csv)
    dev_sequences = list(dict.fromkeys(development["seq"].astype(str).str.upper()))
    dev_pmids: set[str] = set()
    for raw_refs in development.get("evidence_reference", pd.Series(dtype=str)).dropna().astype(str):
        try:
            refs = json.loads(raw_refs)
        except (json.JSONDecodeError, TypeError):
            refs = []
        if isinstance(refs, list):
            for article in refs:
                if not isinstance(article, dict):
                    continue
                pubmed = article.get("pubmed") if isinstance(article.get("pubmed"), dict) else {}
                value = pubmed.get("pubmedId") or article.get("pubmedId") or article.get("pmid")
                if value:
                    dev_pmids.add(str(value).strip())
    spec = get_protocol("protocol-amd-02")

    rows: list[dict] = []
    excluded = Counter()
    for _, row in source.iterrows():
        target = str(row.get("Target_Organism", ""))
        matches = list(MIC_RE.finditer(target))
        if not matches:
            excluded["no_parsable_ecoli_mic_text"] += 1
            continue
        seq, gate = clean_unmodified_sequence(row)
        if seq is None:
            excluded[gate] += 1
            continue
        pmids = str(row.get("Pubmed_ID", "")).strip()
        ref = str(row.get("Reference", "")).strip()
        title = str(row.get("Title", "")).strip()
        for ordinal, match in enumerate(matches, 1):
            # Preserve the literal database extract; parsed values are screening aids,
            # not accepted experimental labels.
            rows.append({
                "dramp_id": str(row.get("DRAMP_ID", "")).strip(),
                "sequence": seq,
                "sequence_length": len(seq),
                "observation_index": ordinal,
                "organism_text": match.group("organism").strip(),
                "mic_value_text": match.group("value").strip(),
                "mic_unit_text": match.group("unit").strip(),
                "target_organism_raw": target,
                "pubmed_ids_raw": pmids,
                "pubmed_ids": ";".join(PMID_RE.findall(pmids)),
                "publication_overlap_with_development": bool(set(PMID_RE.findall(pmids)) & dev_pmids),
                "reference_raw": ref,
                "title_raw": title,
                "source_url": f"https://cpu-bioinfor.org/browse/All_Information.php?id={row.get('DRAMP_ID', '')}&dataset=General",
                "sequence_gate": gate,
                "primary_assay_verification": "pending",
                "label_status": "not_derived",
            })

    frame = pd.DataFrame(rows)
    if len(frame):
        frame["exact_dev_sequence_overlap"] = frame.sequence.isin(set(dev_sequences))
        frame["max_dev_identity_protocol_amd_02"] = frame.sequence.map(
            lambda seq: max((sequence_identity(seq, dev, identity_mode="alignment") for dev in dev_sequences), default=0.0)
        )
        frame["violates_0_40_dev_isolation"] = frame.max_dev_identity_protocol_amd_02 >= spec.cutoff
        duplicate_counts = frame.groupby("sequence").dramp_id.transform("nunique")
        frame["duplicate_dramp_sequence"] = duplicate_counts > 1
        frame.to_csv(out_dir / "ecoli_mic_candidates.csv", index=False, encoding="utf-8-sig")
    else:
        frame = pd.DataFrame(columns=[
            "dramp_id", "sequence", "sequence_length", "observation_index", "organism_text",
            "mic_value_text", "mic_unit_text", "target_organism_raw", "pubmed_ids_raw",
            "reference_raw", "title_raw", "source_url", "sequence_gate", "primary_assay_verification",
            "label_status", "exact_dev_sequence_overlap", "max_dev_identity_protocol_amd_02",
            "violates_0_40_dev_isolation", "duplicate_dramp_sequence",
        ])
        frame.to_csv(out_dir / "ecoli_mic_candidates.csv", index=False, encoding="utf-8-sig")

    by_id = frame.drop_duplicates("dramp_id") if len(frame) else frame
    report = {
        "status": "candidate_screen_only",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_database": "DRAMP",
        "source_release_as_labeled_on_official_download_page": "DRAMP 3.0",
        "source_download_url": "https://cpu-bioinfor.org/downloads/download.php?filename=download_data/DRAMP3.0_new/Antibacterial_amps.xlsx",
        "source_file": str(source_xlsx),
        "source_sha256": sha256(source_xlsx),
        "development_file": str(development_csv),
        "development_sha256": sha256(development_csv),
        "development_unique_sequences": len(dev_sequences),
        "protocol_id": spec.protocol_id,
        "protocol_digest": protocol_digest(spec),
        "cutoff": spec.cutoff,
        "input_rows": len(source),
        "rows_with_ecoli_mention": int(source.Target_Organism.astype(str).str.contains(r"Escherichia\s+coli|E\.?\s*coli", case=False, regex=True).sum()),
        "eligible_sequence_record_count": int(len(by_id)),
        "parsed_ecoli_mic_observation_count": int(len(frame)),
        "records_with_primary_references": int(by_id.pubmed_ids_raw.astype(str).str.strip().ne("").sum()) if len(by_id) else 0,
        "exact_sequence_overlap_records": int(by_id.exact_dev_sequence_overlap.sum()) if len(by_id) else 0,
        "publication_overlap_records": int(by_id.publication_overlap_with_development.sum()) if len(by_id) else 0,
        "records_violating_0_40_homology_cutoff": int(by_id.violates_0_40_dev_isolation.sum()) if len(by_id) else 0,
        "unique_candidate_sequences": int(by_id.sequence.nunique()) if len(by_id) else 0,
        "label_derivation": "none; all entries pending primary assay verification",
        "exclusion_counts": dict(excluded),
        "outputs": ["ecoli_mic_candidates.csv", "manifest.json"],
    }
    (out_dir / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(screen(args.source, args.development, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
