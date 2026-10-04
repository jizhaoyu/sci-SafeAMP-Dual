"""Trace three frozen Myticalin A6 MICs to Okimura et al. 2021 Tables 1/4."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

from research_utils import ROOT, sha256, utc_now, write_json


PMID = "33790103"
DOI = "10.1248/bpb.b20-00799"
PAPER_URL = "https://www.jstage.jst.go.jp/article/bpb/44/4/44_b20-00799/_article"
PDF_URL = "https://www.jstage.jst.go.jp/article/bpb/44/4/44_b20-00799/_pdf"
TARGET = "Escherichia coli NBRC 12734"
TABLE_ROWS = {
    "DBAASP:18059": ("i", "myticalin A6 (4–26)-OH", "PRLPRIPRLPRYPRYPRWPRHPT", "H-PR LPRIP RLPRY PRYPR WPRHP T-OH"),
    "DBAASP:18062": ("l", "myticalin A6 (11–26)-OH", "RLPRYPRYPRWPRHPT", "H-RLPRY PRYPR WPRHP T-OH"),
    "DBAASP:18063": ("m", "myticalin A6 (16–26)-OH", "PRYPRWPRHPT", "H-PRYPR WPRHP T-OH"),
}


def run(records_path: Path, assays_path: Path, pdf_path: Path, output: Path) -> dict:
    paths = tuple(Path(path).resolve() for path in (records_path, assays_path, pdf_path))
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite paper review: {output}")
    if any(not path.is_file() for path in paths):
        raise FileNotFoundError("Frozen inventory or original paper PDF is missing.")
    records_path, assays_path, pdf_path = paths
    reader = PdfReader(pdf_path)
    if len(reader.pages) != 7:
        raise ValueError("Unexpected original paper PDF page count.")
    sequence_table = reader.pages[2].extract_text() or ""
    mic_table = reader.pages[4].extract_text() or ""
    if "Table 1. Structures" not in sequence_table or "Table 4. Antimicrobial Activities" not in mic_table:
        raise ValueError("Original peptide structure or MIC table is missing.")
    if "E. coli" not in mic_table or "NBRC12734" not in mic_table:
        raise ValueError("Original MIC table target is missing.")
    records = pd.read_csv(records_path).set_index("record_id")
    if not records.index.is_unique:
        raise ValueError("Frozen source record IDs are not unique.")
    assays = pd.read_csv(assays_path)
    selected = assays[
        assays.eligible.eq(True) & assays.derived_label.notna()
        & assays.assay_study_ids.astype(str).str.contains(f"pmid:{PMID}", regex=False)
    ]
    if len(selected) != 3 or set(selected.record_id) != set(TABLE_ROWS):
        raise ValueError("Frozen paper inventory differs from three Table 1/4 rows.")
    rows = []
    for assay in selected.itertuples(index=False):
        source = records.loc[assay.record_id]
        letter, name, paper_seq, literal = TABLE_ROWS[assay.record_id]
        if (assay.target != TARGET or assay.raw_mic != ">128" or assay.raw_unit != "µg/ml"
                or source.modifications != "none" or source.seq != paper_seq):
            raise ValueError(f"Frozen molecule, target, or MIC changed: {assay.record_id}")
        if f"{letter} {name} {literal}" not in sequence_table:
            raise ValueError(f"Original Table 1 lacks exact free-acid sequence: {assay.record_id}")
        mic_pattern = re.escape(f"{letter} {name}") + r"\s+\S+\s+\S+\s+(>128)\s+\S+\s+"
        if re.search(mic_pattern, mic_table) is None:
            raise ValueError(f"Original Table 4 E. coli MIC differs: {assay.record_id}")
        raw_path = ROOT / source.raw_path
        if sha256(raw_path) != source.raw_sha256:
            raise ValueError(f"Raw record hash changed: {assay.record_id}")
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        if raw.get("sequence") != source.seq or not any(
            article.get("pubmed", {}).get("pubmedId") == PMID for article in raw["articles"]
        ):
            raise ValueError(f"Raw sequence or PMID differs: {assay.record_id}")
        curated = json.loads(source.assay_conditions)["amp"][int(assay.assay_index)]
        activities = [item for item in raw["targetActivities"] if item.get("id") == curated.get("id")]
        if len(activities) != 1:
            raise ValueError(f"Curated activity ID is absent or duplicated: {assay.record_id}")
        activity = activities[0]
        if (activity.get("targetSpecies", {}).get("name") != TARGET
                or activity.get("activityMeasureValue") != "MIC"
                or activity.get("concentration") != ">128"
                or activity.get("unit", {}).get("name") != "µg/ml"):
            raise ValueError(f"Raw activity differs from original Table 4: {assay.record_id}")
        rows.append({
            "record_id": assay.record_id, "paper_table_1_name": name,
            "paper_table_1_sequence": paper_seq, "paper_c_terminus": "free_acid_OH",
            "database_sequence": source.seq, "database_modifications": source.modifications,
            "target": TARGET, "paper_table_4_mic": ">128", "paper_unit": "µg/mL",
            "database_activity_id": activity["id"], "database_mic": activity["concentration"],
            "database_unit": activity["unit"]["name"], "sequence_and_mic_match": True,
            "source_raw_path": source.raw_path, "source_raw_sha256": sha256(raw_path),
        })
    review = pd.DataFrame(rows).sort_values("record_id")
    output.mkdir(parents=True)
    review.to_csv(output / "record_review.csv", index=False)
    report = (
        "# Okimura 等 2021 Myticalin A6 原始测定审计\n\n"
        f"[原论文]({PAPER_URL})；[出版方 PDF]({PDF_URL})。"
        "Table 1 的 3 条序列均为游离羧酸端 `-OH`；Table 4 给出 *E. coli* NBRC 12734 "
        "的 3 条 `>128 µg/mL` MIC，与数据库原始活动一致，表中每条有 3 次测定。"
        "逐条依据见 `record_review.csv`。\n\n"
        "此论文提供含阴性的独立来源候选，尚未通过全员同源和五折组审计。"
        "局部论文核查不释放训练记录，也不修改旧协议。\n"
    )
    (output / "report.md").write_text(report, encoding="utf-8")
    manifest = {
        "status": "blocked_primary_review_in_progress", "generated_at": utc_now(),
        "paper": {"pmid": PMID, "doi": DOI, "article_url": PAPER_URL, "pdf_url": PDF_URL},
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
        "review": {"records": len(review), "sequence_and_mic_matches": len(review),
                   "negative_observations": len(review), "records_released_for_training": 0},
        "outputs": {name: sha256(output / name) for name in ("record_review.csv", "report.md")},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=ROOT / "03_experiments/audits/mic_training_source_20261001_v1/records.csv")
    parser.add_argument("--assays", type=Path, default=ROOT / "03_experiments/audits/mic_study_disjoint_20261001_v5/assay_observations.csv")
    parser.add_argument("--pdf", type=Path, default=ROOT / "03_experiments/audits/mic_primary_review_pmid33790103_20261002_v1/raw/44_b20-00799.pdf")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.records, args.assays, args.pdf, args.output), ensure_ascii=False, indent=2))
