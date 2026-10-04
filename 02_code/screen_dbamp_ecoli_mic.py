"""Screen dbAMP 3.0 for numeric E. coli MIC evidence and sequence overlap.

The result is a candidate audit only: labels are not derived and primary-paper
assay conditions remain unverified until each database record is traced back.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import numpy as np

from feature_extractor import STANDARD_AMINO_ACIDS
from research_data import sequence_identity
from research_protocol_config import get_protocol, protocol_digest


MIC_RE = re.compile(
    r"(?P<organism>(?:Escherichia\s+coli|E\.?\s*coli)[^,;&]{0,120}?)\s*"
    r"\(\s*MIC\s*=\s*(?P<value>[^)]{1,60})\)", re.IGNORECASE
)
AA_ORDER = "ACDEFGHIKLMNPQRSTVWY"

try:
    from numba import njit
except ImportError:  # The exact Python reference implementation remains available.
    njit = None


def _identity_kernel_impl(candidates, candidate_codes, candidate_lengths, development, development_codes, development_lengths):
    output = []
    for ci in range(len(candidates)):
        best = -1.0
        best_dev = -1
        for di in range(len(development)):
            if candidates[ci] > development[di]:
                a_codes, a_len = development_codes[di], development_lengths[di]
                b_codes, b_len = candidate_codes[ci], candidate_lengths[ci]
            else:
                a_codes, a_len = candidate_codes[ci], candidate_lengths[ci]
                b_codes, b_len = development_codes[di], development_lengths[di]
            prev_score = [-2 * j for j in range(b_len + 1)]
            prev_matches = [0] * (b_len + 1)
            prev_columns = list(range(b_len + 1))
            for i in range(1, a_len + 1):
                cur_score = [-2 * i] + [0] * b_len
                cur_matches = [0] * (b_len + 1)
                cur_columns = [i] + [0] * b_len
                for j in range(1, b_len + 1):
                    diag = prev_score[j - 1] + (2 if a_codes[i - 1] == b_codes[j - 1] else -1)
                    up = prev_score[j] - 2
                    left = cur_score[j - 1] - 2
                    if diag >= up and diag >= left:
                        cur_score[j] = diag
                        cur_matches[j] = prev_matches[j - 1] + (1 if a_codes[i - 1] == b_codes[j - 1] else 0)
                        cur_columns[j] = prev_columns[j - 1] + 1
                    elif up >= left:
                        cur_score[j] = up
                        cur_matches[j] = prev_matches[j]
                        cur_columns[j] = prev_columns[j] + 1
                    else:
                        cur_score[j] = left
                        cur_matches[j] = cur_matches[j - 1]
                        cur_columns[j] = cur_columns[j - 1] + 1
                prev_score, prev_matches, prev_columns = cur_score, cur_matches, cur_columns
            identity = prev_matches[-1] / prev_columns[-1]
            if identity > best:
                best, best_dev = identity, di
        output.append((best, best_dev))
    return output


if njit is not None:
    _identity_kernel = njit(cache=True)(_identity_kernel_impl)
else:
    _identity_kernel = _identity_kernel_impl


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def screen(source_zip: Path, development_csv: Path, out_dir: Path) -> dict:
    source_zip, development_csv, out_dir = map(Path, (source_zip, development_csv, out_dir))
    if out_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing audit directory: {out_dir}")
    out_dir.mkdir(parents=True)

    with zipfile.ZipFile(source_zip) as archive:
        xlsx_name = next(name for name in archive.namelist() if name.endswith("dbAMP3_pepinfo.xlsx"))
        source = pd.read_excel(io.BytesIO(archive.read(xlsx_name))).fillna("")
    development = pd.read_csv(development_csv)
    dev_sequences = list(dict.fromkeys(development["seq"].astype(str).str.upper()))
    spec = get_protocol("protocol-amd-02")

    records: list[dict] = []
    eligible_sequences: set[str] = set()
    for _, row in source.iterrows():
        seq = str(row.get("Seq", "")).strip().upper()
        if not (10 <= len(seq) <= 50) or not seq or any(aa not in STANDARD_AMINO_ACIDS for aa in seq):
            continue
        targets = str(row.get("Targets", ""))
        matches = list(MIC_RE.finditer(targets))
        if not matches:
            continue
        eligible_sequences.add(seq)
        for ordinal, match in enumerate(matches, 1):
            records.append({
                "dbamp_id": str(row.get("dbAMP_ID", "")).strip(),
                "sequence": seq,
                "observation_index": ordinal,
                "organism_text": match.group("organism").strip(),
                "mic_value_text": match.group("value").strip(),
                "targets_raw": targets,
                "dbamp_source_field": str(row.get("Source", "")).strip(),
                "dbamp_taxonomy_field": str(row.get("Tax", "")).strip(),
                "primary_reference": "not_in_downloaded_workbook; resolve from dbAMP record page",
                "assay_conditions": "not_in_downloaded_workbook",
                "chemistry_modification_status": "not_recorded_in_downloaded_workbook",
                "primary_assay_verification": "pending",
                "label_status": "not_derived",
            })

    candidate_sequences = sorted(eligible_sequences)
    dev_records = development["record_id"].astype(str).tolist()
    dev_sequence_strings = development["seq"].astype(str).str.upper().tolist()
    candidate_codes = np.zeros((len(candidate_sequences), 50), dtype=np.uint8)
    development_codes = np.zeros((len(dev_sequence_strings), 50), dtype=np.uint8)
    for i, seq in enumerate(candidate_sequences):
        candidate_codes[i, :len(seq)] = [AA_ORDER.index(aa) for aa in seq]
    for i, seq in enumerate(dev_sequence_strings):
        development_codes[i, :len(seq)] = [AA_ORDER.index(aa) for aa in seq]
    candidate_lengths = np.asarray([len(seq) for seq in candidate_sequences], dtype=np.int16)
    development_lengths = np.asarray([len(seq) for seq in dev_sequence_strings], dtype=np.int16)
    candidate_sequence_array = np.asarray(candidate_sequences, dtype="U50")
    development_sequence_array = np.asarray(dev_sequence_strings, dtype="U50")
    max_id_rows = _identity_kernel(
        candidate_sequence_array, candidate_codes, candidate_lengths,
        development_sequence_array, development_codes, development_lengths,
    )
    dev_sequence_set = set(dev_sequences := dev_sequence_strings)
    summaries: list[dict] = []
    for seq, (max_id, best_idx) in zip(candidate_sequences, max_id_rows):
        summaries.append({
            "sequence": seq,
            "sequence_length": len(seq),
            "max_development_identity_protocol_amd_02": max_id,
            "closest_development_record_id": dev_records[best_idx],
            "exact_development_sequence_overlap": seq in dev_sequence_set,
            "violates_0_40_cutoff": max_id >= spec.cutoff,
            "chemistry_modification_status": "not_recorded_in_downloaded_workbook",
        })

    observations = pd.DataFrame(records)
    sequence_audit = pd.DataFrame(summaries)
    if len(observations):
        observations = observations.merge(sequence_audit, on=["sequence", "chemistry_modification_status"], how="left", suffixes=("", "_sequence"))
        observations["source_url"] = observations["dbamp_id"].map(lambda value: f"https://ycclab.cuhk.edu.cn/dbAMP/information.php?db={value}")
        observations.to_csv(out_dir / "ecoli_mic_observations.csv", index=False, encoding="utf-8-sig")
    else:
        observations.to_csv(out_dir / "ecoli_mic_observations.csv", index=False, encoding="utf-8-sig")
    sequence_audit.to_csv(out_dir / "unique_sequence_similarity_audit.csv", index=False, encoding="utf-8-sig")

    targets = source["Targets"].astype(str)
    report = {
        "status": "candidate_screen_only",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_database": "dbAMP",
        "source_release": "dbAMP 3.0 (June 2024)",
        "source_download_url": "https://ycclab.cuhk.edu.cn/dbAMP/download/3.0/dbAMP2024.zip",
        "source_file": str(source_zip),
        "source_sha256": sha256(source_zip),
        "source_member": xlsx_name,
        "source_rows": len(source),
        "rows_with_ecoli_text": int(targets.str.contains(r"Escherichia\s+coli|E\.?\s*coli", case=False, regex=True).sum()),
        "rows_with_parsed_ecoli_mic": int(source["Targets"].astype(str).map(lambda value: bool(MIC_RE.search(value))).sum()),
        "parsed_ecoli_mic_observations": len(records),
        "unique_candidate_sequences_10_50_canonical": len(eligible_sequences),
        "development_file": str(development_csv),
        "development_sha256": sha256(development_csv),
        "development_unique_sequences": len(dev_sequences),
        "protocol_id": spec.protocol_id,
        "protocol_digest": protocol_digest(spec),
        "cutoff": spec.cutoff,
        "unique_sequences_exactly_overlapping_development": int(sequence_audit.exact_development_sequence_overlap.sum()) if len(sequence_audit) else 0,
        "unique_sequences_violating_0_40_cutoff": int(sequence_audit.violates_0_40_cutoff.sum()) if len(sequence_audit) else 0,
        "unique_sequences_below_0_40_cutoff": int((~sequence_audit.violates_0_40_cutoff).sum()) if len(sequence_audit) else 0,
        "alignment_engine": "numba-jitted exact mirror of research_data.sequence_identity" if njit is not None else "research_data.sequence_identity equivalent Python kernel",
        "important_gaps": [
            "Downloaded workbook does not include primary references or assay conditions.",
            "Downloaded workbook does not specify peptide modifications/chemistry.",
            "dbAMP record-page evidence and original papers must be reviewed before any record can enter training.",
        ],
        "label_derivation": "none",
        "outputs": ["ecoli_mic_observations.csv", "unique_sequence_similarity_audit.csv", "manifest.json"],
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
