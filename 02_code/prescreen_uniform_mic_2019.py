"""Sequence-only prescreen of the 20 peptides in DOI 10.3390/data4010027.

Names and sequences are transcribed from Table 1 of the primary article. No MIC
values or labels are inferred here; the original supplementary CSV is required
before any record can enter an evidence-audited cohort.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pandas as pd

from research_data import sequence_identity
from research_utils import ROOT, sha256, utc_now, write_json


PEPTIDES = {
    "NN2_0000": "EVAKKLLASALKLALAI",
    "NN2_0001": "EDWNHLGAAVHTLKHVYK",
    "NN2_0002": "AIVEQLRKRC",
    "NN2_0003": "KLSASLKHVAHRARHLS",
    "NN2_0004": "ESRAGKLAAKAAFKAAKR",
    "NN2_0005": "EWAAARQVIIHATRKY",
    "NN2_0006": "EILSKALSALSPLAN",
    "NN2_0007": "EKAILSALKLLRLAL",
    "NN2_0008": "ETAKGVAKHLPPAIA",
    "NN2_0009": "KVYARLHAVIKRLHRRLH",
    "NN2_0018": "YLARAIRRTLARLLL",
    "NN2_0022": "EWRVARRAVQRLRHLARRYH",
    "NN2_0024": "ALKKMLRLAKRLS",
    "NN2_0027": "VLSAFHKVIKIIHHISHF",
    "NN2_0029": "RKFRKILHRARKWI",
    "NN2_0035": "RRWGRWHRMRRRGR",
    "NN2_0039": "FWKGLVKAAFKIVHAGS",
    "NN2_0046": "GWKAIHKAAKGIHTYVN",
    "NN2_0050": "SWKKFFKKARSLPKLF",
    "NN2_0055": "YKRWKKWRSKAKKIL",
}


def run(records_path: Path, supplement_path: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing prescreen: {output}")
    development = pd.read_csv(records_path)
    supplement = pd.read_csv(supplement_path)
    if len(development) != 417 or len(supplement) != 4:
        raise ValueError("Unexpected comparison cohort; review the frozen inputs before screening.")
    for frame in (development, supplement):
        if frame.record_id.isna().any() or frame.seq.isna().any():
            raise ValueError("Comparison records require IDs and sequences.")
    if len(PEPTIDES) != 20 or len(set(PEPTIDES.values())) != 20:
        raise ValueError("Expected 20 unique transcribed peptide sequences.")
    comparison = [("development", row.record_id, row.seq) for row in development.itertuples()]
    comparison += [("dramp_candidate", row.record_id, row.seq) for row in supplement.itertuples()]
    output.mkdir(parents=True)
    rows = []
    for name, sequence in PEPTIDES.items():
        identities = [(cohort, record_id, sequence_identity(sequence, other, identity_mode="alignment"))
                      for cohort, record_id, other in comparison]
        nearest = max(identities, key=lambda value: value[2])
        rows.append({
            "peptide": name,
            "sequence": sequence,
            "length_aa": len(sequence),
            "nearest_cohort": nearest[0],
            "nearest_record_id": nearest[1],
            "max_identity": nearest[2],
            "pairs_at_or_above_0_40": sum(identity >= 0.40 for _, _, identity in identities),
            "sequence_isolated_from_comparison": all(identity < 0.40 for _, _, identity in identities),
            "mic_label": "not_curated",
            "evidence_status": "supplementary_mic_and_chemistry_pending",
        })
    with (output / "sequence_prescreen.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "status": "sequence_prescreen_only_not_eligible_for_training",
        "generated_at": utc_now(),
        "source_doi": "10.3390/data4010027",
        "source_article": "https://doi.org/10.3390/data4010027",
        "source_table": "primary article Table 1; sequences transcribed for screening only",
        "sequence_identity_protocol": "protocol-amd-02; global Needleman-Wunsch matches/alignment columns; cutoff 0.40",
        "development_records": len(development),
        "development_sha256": sha256(records_path),
        "dramp_candidate_records": len(supplement),
        "dramp_candidate_sha256": sha256(supplement_path),
        "script_sha256": sha256(Path(__file__)),
        "candidate_count": len(rows),
        "below_cutoff_count": sum(row["sequence_isolated_from_comparison"] for row in rows),
        "at_or_above_cutoff_count": sum(not row["sequence_isolated_from_comparison"] for row in rows),
        "comparisons_evaluated": len(rows) * len(comparison),
        "training_started": False,
        "blockers": ["Supplementary Table S1 MIC values and sequence chemistry not yet verified against the primary source.",
                     "Study overlap, candidate-to-candidate grouping, and full cohort feasibility are not yet audited."],
        "outputs": {"sequence_prescreen": str((output / "sequence_prescreen.csv").resolve().relative_to(ROOT))},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--supplement", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.records, args.supplement, args.output), ensure_ascii=False, indent=2))
