"""Audit eight frozen MIC observations against Ross et al. 2020.

Figure 1 sequences below are manually transcribed from the publisher PDF.
Table 1 E. coli BL21 MIC values are parsed from that same PDF. This paper-level
audit never releases a cohort or changes a training protocol.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

from research_utils import ROOT, sha256, utc_now, write_json


PMID = "33281785"
DOI = "10.3389/fmicb.2020.589666"
ARTICLE_URL = f"https://www.frontiersin.org/journals/microbiology/articles/{DOI}/full"
PDF_URL = f"https://www.frontiersin.org/journals/microbiology/articles/{DOI}/pdf"
PAPER_SEQUENCES = {
    "Syn-sordellicin-16": "WGTNRIAKELRRYIRKVGRIARKAW",
    "Syn-sordellicin-41": "AGRQWIAKYLRREIRKRGRKAVIAW",
    "Syn-sordellicin-88": "AGTNRIAKELRRYIRKVGRIARKKW",
    "Syn-larvacin-40": "AWTEKIFNRLKKTINEGKKIAKRAW",
    "Syn-larvacin-69": "AGKETIRQFLKKTIQEKGKRAKIWW",
    "Syn-xiamencin-20": "AGRQALTKYLLEELRKRWKKAFIAW",
    "Syn-enterocin-24": "AGSERIWKELKKYIKKGKKVIRAAW",
    "Syn-enterocin-46": "AGRESIKAYLKKEIKKKWKRIVAAW",
}


def run(records_path: Path, assays_path: Path, pdf_path: Path, output: Path) -> dict:
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite paper review: {output}")
    for path in (records_path, assays_path, pdf_path):
        if not Path(path).is_file():
            raise FileNotFoundError(path)

    records = pd.read_csv(records_path)
    assays = pd.read_csv(assays_path)
    selected = assays[
        assays.eligible.eq(True)
        & assays.derived_label.notna()
        & assays.assay_study_ids.astype(str).str.contains(f"pmid:{PMID}", regex=False)
    ].copy()
    if len(selected) != 8 or selected.record_id.nunique() != 8:
        raise ValueError("Frozen Ross 2020 inventory is not eight distinct MIC observations.")

    reader = PdfReader(pdf_path)
    if len(reader.pages) < 6:
        raise ValueError("Publisher PDF has no Figure 1 / Table 1 pages.")
    table_text = reader.pages[5].extract_text() or ""
    if "E. coli (BL21)" not in table_text or "TABLE 1" not in table_text:
        raise ValueError("Publisher PDF Table 1 cannot be identified.")
    if len(PAPER_SEQUENCES) != len(set(PAPER_SEQUENCES.values())):
        raise ValueError("Manual Figure 1 transcription contains duplicate sequences.")
    by_sequence = {sequence: name for name, sequence in PAPER_SEQUENCES.items()}
    rows = []
    for row in selected.itertuples(index=False):
        if row.target != "Escherichia coli BL21":
            raise ValueError(f"Frozen assay target is not E. coli BL21: {row.record_id}")
        source = records[records.record_id.eq(row.record_id)]
        if len(source) != 1:
            raise ValueError(f"Missing or duplicate source record: {row.record_id}")
        source = source.iloc[0]
        paper_name = by_sequence.get(source.seq)
        if paper_name is None:
            raise ValueError(f"Figure 1 sequence not mapped: {row.record_id}")
        match = re.search(r"(?m)^" + re.escape(paper_name) + r"\s+([<>]?[0-9.]+)\s+µM\b", table_text)
        if match is None:
            raise ValueError(f"Table 1 MIC not found: {paper_name}")
        raw_path = ROOT / source.raw_path
        if sha256(raw_path) != source.raw_sha256:
            raise ValueError(f"Frozen source hash differs from raw DBAASP file: {row.record_id}")
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        if raw.get("sequence") != source.seq or not any(
            article.get("pubmed", {}).get("pubmedId") == PMID for article in raw["articles"]
        ):
            raise ValueError(f"Raw sequence or primary-paper PMID differs: {row.record_id}")
        activities = [activity for activity in raw["targetActivities"]
                      if activity.get("activityMeasureValue") == "MIC"
                      and activity.get("targetSpecies", {}).get("name") == "Escherichia coli BL21"]
        if len(activities) != 1:
            raise ValueError(f"Expected one raw BL21 MIC activity: {row.record_id}")
        activity = activities[0]
        if raw["targetActivities"][int(row.assay_index)]["id"] != activity["id"]:
            raise ValueError(f"Frozen assay index selects a different raw activity: {row.record_id}")
        if activity["concentration"] != str(row.raw_mic) or activity["unit"]["name"] != row.raw_unit:
            raise ValueError(f"Frozen assay differs from its raw DBAASP activity: {row.record_id}")
        paper_mic = match.group(1)
        rows.append({
            "record_id": row.record_id,
            "paper_peptide_name": paper_name,
            "record_sequence": source.seq,
            "paper_figure_1_sequence": PAPER_SEQUENCES[paper_name],
            "sequence_matches_paper": source.seq == PAPER_SEQUENCES[paper_name],
            "target": row.target,
            "paper_table_1_mic": paper_mic,
            "paper_unit": "µM",
            "database_activity_id": activity["id"],
            "database_mic": activity["concentration"],
            "database_unit": activity["unit"]["name"],
            "database_mic_matches_paper": activity["concentration"] == paper_mic and activity["unit"]["name"] == "µM",
            "source_raw_path": source.raw_path,
            "source_raw_sha256": sha256(raw_path),
            "figure_sequence_transcription": "manual_single_reviewer_pending_independent_check",
        })

    review = pd.DataFrame(rows).sort_values("record_id")
    if not review.sequence_matches_paper.all() or not review.database_mic_matches_paper.all():
        raise ValueError("A sequence or MIC mismatch needs explicit conflict reporting.")
    output.mkdir(parents=True)
    review.to_csv(output / "record_review.csv", index=False)
    manifest = {
        "status": "blocked_primary_review_in_progress",
        "generated_at": utc_now(),
        "paper": {"pmid": PMID, "doi": DOI, "article_url": ARTICLE_URL, "pdf_url": PDF_URL,
                  "article_license": "CC BY 4.0 as stated on the publisher article page"},
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.relative_to(ROOT)): sha256(path)
                   for path in (records_path, assays_path, pdf_path)},
        "review": {"records": len(review), "figure_1_sequences_matching": int(review.sequence_matches_paper.sum()),
                   "table_1_bl21_mic_matching": int(review.database_mic_matches_paper.sum()),
                   "database_mic_conflicts": int((~review.database_mic_matches_paper).sum()),
                   "records_released_for_training": 0},
        "limitations": ["Figure 1 image sequences were transcribed by one reviewer and need independent confirmation.",
                        "The paper-level match does not resolve the frozen cohort's remaining studies or its training gate.",
                        "The study used sheep blood for hemolysis; this is not a human erythrocyte HC50 source."],
        "outputs": {"record_review.csv": sha256(output / "record_review.csv")},
    }
    write_json(output / "manifest.json", manifest)
    (output / "report.md").write_text(
        "# Ross et al. 2020 原始论文审计\n\n"
        f"- PMID：{PMID}；DOI：{DOI}。\n"
        f"- 原文：[Frontiers 论文]({ARTICLE_URL})；[出版方 PDF]({PDF_URL})。\n"
        f"- Figure 1 的 8 条序列与冻结记录对应；Table 1 的 8 条 *E. coli* BL21 MIC 与 DBAASP 原始活动数值对应。"
        "逐条 ID、序列、数值与原始文件哈希见 `record_review.csv`。\n"
        "- Figure 1 是图片，序列由单人目视转录，尚待独立复核。论文的溶血实验使用绵羊血，"
        "不可当作人红细胞 HC50。此审计不放行训练；当前队列其余论文和既有冲突继续阻断。\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=ROOT / "03_experiments/audits/mic_training_source_20261001_v1/records.csv")
    parser.add_argument("--assays", type=Path, default=ROOT / "03_experiments/audits/mic_study_disjoint_20261001_v5/assay_observations.csv")
    parser.add_argument("--pdf", type=Path, default=ROOT / "03_experiments/audits/mic_primary_review_pmid33281785_20261001_v1/raw/ross_2020_frontiers.pdf")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.records, args.assays, args.pdf, args.output), ensure_ascii=False, indent=2))
