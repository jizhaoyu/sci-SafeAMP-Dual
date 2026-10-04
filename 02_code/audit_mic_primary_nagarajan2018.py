"""Trace three frozen MIC observations to Nagarajan et al. 2018 Table 1.

Table 1 is an image in the original PDF. The three rows below are manual
transcriptions, so this audit does not release a training cohort.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

from research_utils import ROOT, sha256, utc_now, write_json


PMID = "29259134"
DOI = "10.1074/jbc.M117.805499"
PAPER_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC5846155/"
PDF_URL = "https://repository.ias.ac.in/118258/1/PIIS0021925820403904.pdf"
TARGET = "Escherichia coli K12 MG1655"
# Exact sequence, Table 1 peptide name, and E. coli K12 MG1655 MIC in µg/mL.
TABLE_1 = {
    "DBAASP:13184": ("YLARAIRRTLARLLL", "NN2_0018", "32"),
    "DBAASP:13205": ("RRWGRWHRMRRRGR", "NN2_0035", ">128"),
    "DBAASP:13248": ("KRSWDIVKKYVGVVVGTIH", "NN2_R0039", "128"),
}


def run(records_path: Path, assays_path: Path, pdf_path: Path, output: Path) -> dict:
    paths = tuple(Path(path).resolve() for path in (records_path, assays_path, pdf_path))
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite paper review: {output}")
    if any(not path.is_file() for path in paths):
        raise FileNotFoundError("Frozen inventory or original paper PDF is missing.")
    records_path, assays_path, pdf_path = paths
    records = pd.read_csv(records_path).set_index("record_id")
    if not records.index.is_unique:
        raise ValueError("Frozen source record IDs are not unique.")
    assays = pd.read_csv(assays_path)
    selected = assays[
        assays.eligible.eq(True) & assays.derived_label.notna()
        & assays.assay_study_ids.astype(str).str.contains(f"pmid:{PMID}", regex=False)
    ]
    if len(selected) != 3 or set(selected.record_id) != set(TABLE_1):
        raise ValueError("Frozen paper inventory differs from the three manually reviewed rows.")
    reader = PdfReader(pdf_path)
    page = reader.pages[3].extract_text() or ""
    if "Table 1" not in page or "E. coli (K12 MG1655)" not in page:
        raise ValueError("Original PDF Table 1 or target cannot be identified.")

    rows = []
    for assay in selected.itertuples(index=False):
        if assay.target != TARGET:
            raise ValueError(f"Wrong frozen target: {assay.record_id}")
        source = records.loc[assay.record_id]
        paper_seq, paper_name, paper_mic = TABLE_1[assay.record_id]
        raw_path = ROOT / source.raw_path
        if sha256(raw_path) != source.raw_sha256:
            raise ValueError(f"Raw record hash differs: {assay.record_id}")
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        if raw.get("sequence") != source.seq or not any(
            article.get("pubmed", {}).get("pubmedId") == PMID for article in raw["articles"]
        ):
            raise ValueError(f"Sequence or PMID differs in raw record: {assay.record_id}")
        activity = raw["targetActivities"][int(assay.assay_index)]
        if (activity.get("activityMeasureValue") != "MIC"
                or activity.get("targetSpecies", {}).get("name") != TARGET
                or activity.get("concentration") != str(assay.raw_mic)
                or activity.get("unit", {}).get("name") != assay.raw_unit):
            raise ValueError(f"Frozen and raw MIC differ: {assay.record_id}")
        rows.append({
            "record_id": assay.record_id, "paper_table": "Table 1, PDF page 4",
            "paper_peptide_name": paper_name, "paper_sequence": paper_seq,
            "database_sequence": source.seq, "sequence_matches_paper": source.seq == paper_seq,
            "target": TARGET, "paper_mic": paper_mic, "paper_unit": "µg/mL",
            "database_activity_id": activity["id"], "database_mic": activity["concentration"],
            "database_unit": activity["unit"]["name"],
            "database_mic_matches_paper": activity["concentration"] == paper_mic
            and activity["unit"]["name"] == "µg/ml",
            "source_raw_path": source.raw_path, "source_raw_sha256": sha256(raw_path),
            "table_transcription": "manual_single_reviewer_pending_independent_check",
        })
    review = pd.DataFrame(rows).sort_values("record_id")
    if not review.sequence_matches_paper.all() or not review.database_mic_matches_paper.all():
        raise ValueError("Original Table 1 and frozen record differ; investigate conflict.")
    output.mkdir(parents=True)
    review.to_csv(output / "record_review.csv", index=False)
    report = (
        "# Nagarajan 等 2018 原始测定审计\n\n"
        f"[原论文]({PAPER_URL})；[原文 PDF]({PDF_URL})。原文 Table 1（PDF 第 4 页）"
        "列有 *E. coli* K12 MG1655 的逐肽 MIC、序列与名称。\n\n"
        "- 冻结清单关联此论文的 3 条测定，其序列、MIC 数值及单位与 Table 1 和 DBAASP 原始活动一致；"
        "包括 1 条阳性和 2 条阴性。逐条依据见 `record_review.csv`。\n"
        "- Table 1 是图片，由单人目视转录，尚待独立复核；来源化学形式也未完成全队列核查。"
        "本局部审计不释放训练记录，不改变 MIC-only 阻断状态。\n"
    )
    (output / "report.md").write_text(report, encoding="utf-8")
    manifest = {
        "status": "blocked_primary_review_in_progress", "generated_at": utc_now(),
        "paper": {"pmid": PMID, "doi": DOI, "article_url": PAPER_URL, "pdf_url": PDF_URL},
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
        "review": {"records": len(review), "sequence_and_mic_matches": int(
            (review.sequence_matches_paper & review.database_mic_matches_paper).sum()),
            "positive_observations": int(selected.derived_label.eq(1).sum()),
            "negative_observations": int(selected.derived_label.eq(0).sum()),
            "records_released_for_training": 0},
        "outputs": {name: sha256(output / name) for name in ("record_review.csv", "report.md")},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=ROOT / "03_experiments/audits/mic_training_source_20261001_v1/records.csv")
    parser.add_argument("--assays", type=Path, default=ROOT / "03_experiments/audits/mic_study_disjoint_20261001_v5/assay_observations.csv")
    parser.add_argument("--pdf", type=Path, default=ROOT / "03_experiments/audits/mic_primary_review_pmid29259134_20261002_v1/raw/PIIS0021925820403904.pdf")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.records, args.assays, args.pdf, args.output), ensure_ascii=False, indent=2))
