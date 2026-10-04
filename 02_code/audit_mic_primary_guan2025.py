"""Compare Guan et al. 2025 frozen MIC records with original source data.

Source-data value 80 is not interpreted as a measured 80 µM MIC or >64.
Only exact numerical matches are candidates for a later, separately frozen cohort.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree

import openpyxl
import pandas as pd
from pypdf import PdfReader

from research_utils import ROOT, sha256, utc_now, write_json


PMID = "40645962"
DOI = "10.1038/s41467-025-60051-6"
PAPER_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC12254355/"
SUPPLEMENT_URL = "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-025-60051-6/MediaObjects/41467_2025_60051_MOESM1_ESM.pdf"
SOURCE_DATA_URL = "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-025-60051-6/MediaObjects/41467_2025_60051_MOESM7_ESM.xlsx"
PAPER_NAMES = {
    "DBAASP:24269": "UniprotKB-4", "DBAASP:24274": "UniprotKB-8",
    "DBAASP:24290": "ISOB-5", "DBAASP:24292": "ISOB-7",
    "DBAASP:24303": "Conoserver-16",
}
TARGET_COLUMNS = {
    "Escherichia coli ATCC 11775": "E. coli ATCC 11775",
    "Escherichia coli AIC221": "E. coli AIC221",
    "Escherichia coli AIC222": "E. coli AIC222",
}


def run(records_path: Path, assays_path: Path, supplement_path: Path, source_data_path: Path,
        xml_path: Path, output: Path) -> dict:
    paths = tuple(Path(path).resolve() for path in
                  (records_path, assays_path, supplement_path, source_data_path, xml_path))
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite paper review: {output}")
    if any(not path.is_file() for path in paths):
        raise FileNotFoundError("Frozen inventory or original article files are missing.")
    records_path, assays_path, supplement_path, source_data_path, xml_path = paths
    article = " ".join(ElementTree.parse(xml_path).getroot().itertext())
    for phrase in ("in LB medium", "1 to 64", "three independent replicates"):
        if phrase not in article:
            raise ValueError(f"Original MIC methods do not confirm: {phrase}")
    table = PdfReader(supplement_path).pages[2].extract_text() or ""
    if "Supplementary Table 2" not in table:
        raise ValueError("Original sequence table is missing.")
    workbook = openpyxl.load_workbook(source_data_path, read_only=True, data_only=True)
    if "Figure 2a" not in workbook:
        raise ValueError("Original source-data MIC sheet is missing.")
    values = list(workbook["Figure 2a"].values)
    headers = list(values[0])
    if any(header not in headers for header in TARGET_COLUMNS.values()):
        raise ValueError("Expected E. coli target columns are absent.")
    by_name = {row[0]: row for row in values[1:] if row[0]}

    records = pd.read_csv(records_path).set_index("record_id")
    if not records.index.is_unique:
        raise ValueError("Frozen source record IDs are not unique.")
    assays = pd.read_csv(assays_path)
    selected = assays[
        assays.eligible.eq(True) & assays.derived_label.notna()
        & assays.assay_study_ids.astype(str).str.contains(f"pmid:{PMID}", regex=False)
    ]
    if len(selected) != 12 or set(selected.record_id) != set(PAPER_NAMES):
        raise ValueError("Frozen Guan paper inventory differs from expected 12 observations.")
    rows = []
    for assay in selected.itertuples(index=False):
        source = records.loc[assay.record_id]
        name = PAPER_NAMES[assay.record_id]
        if f"{name} {source.seq}" not in table:
            raise ValueError(f"Original Table 2 lacks the exact sequence: {assay.record_id}")
        if assay.target not in TARGET_COLUMNS:
            raise ValueError(f"Unexpected target: {assay.target}")
        source_value = by_name[name][headers.index(TARGET_COLUMNS[assay.target])]
        if source_value is None:
            raise ValueError(f"Original source data missing: {name}, {assay.target}")
        raw_path = ROOT / source.raw_path
        if sha256(raw_path) != source.raw_sha256:
            raise ValueError(f"Raw record hash changed: {assay.record_id}")
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        if raw.get("sequence") != source.seq or not any(
            item.get("pubmed", {}).get("pubmedId") == PMID for item in raw["articles"]
        ):
            raise ValueError(f"Raw sequence or PMID differs: {assay.record_id}")
        curated = json.loads(source.assay_conditions)["amp"][int(assay.assay_index)]
        activity = [item for item in raw["targetActivities"] if item.get("id") == curated.get("id")]
        if len(activity) != 1 or activity[0].get("concentration") != str(assay.raw_mic):
            raise ValueError(f"Frozen assay cannot be linked to raw activity: {assay.record_id}")
        exact_match = str(assay.raw_mic) == str(source_value) and assay.raw_unit == "µM"
        if not exact_match and not (str(assay.raw_mic) == ">64" and source_value == 80):
            raise ValueError(f"Raw MIC is neither an exact match nor the unresolved 80 code: {assay.record_id}")
        if assay.medium != "LBB" or activity[0].get("medium", {}).get("description") != "Luria Bertani Broth":
            raise ValueError(f"Frozen medium changed; redo review: {assay.record_id}")
        rows.append({
            "record_id": assay.record_id, "paper_peptide_name": name,
            "sequence": source.seq, "target": assay.target,
            "source_figure_2a_value": source_value,
            "database_mic": assay.raw_mic, "database_unit": assay.raw_unit,
            "exact_mic_match": exact_match,
            "source_80_code_unresolved": source_value == 80,
            "paper_assay_medium": "LB", "frozen_assay_medium": assay.medium,
            "medium_matches_paper": True,
            "decision": ("candidate_exact_value_pending_full_cohort_audit" if exact_match
                         else "exclude_pending_source_80_code_definition"),
            "source_raw_path": source.raw_path, "source_raw_sha256": sha256(raw_path),
        })
    review = pd.DataFrame(rows).sort_values(["record_id", "target"])
    output.mkdir(parents=True)
    review.to_csv(output / "record_review.csv", index=False)
    report = (
        "# Guan 等 2025 原始测定及条件冲突审计\n\n"
        f"[原论文]({PAPER_URL})、[补充序列表]({SUPPLEMENT_URL})、"
        f"[出版方 Source Data]({SOURCE_DATA_URL})。补充 Table 2 的 5 条序列与冻结记录对应；"
        "Source Data 的 Figure 2a 含 12 个相关 *E. coli* 格子。\n\n"
        f"- {int(review.exact_mic_match.sum())} 条数值与数据库逐值一致；"
        f"{int(review.source_80_code_unresolved.sum())} 条数据库记 `>64 µM`、绘图源文件存 `80`。"
        "原文只说明测试范围 1–64 µM，未找到 `80` 的数据字典；不把它猜作测定值或右删失编码。\n"
        "- 原论文 Methods 明确 MIC 采用 LB 培养基；DBAASP 原始记录的 `LBB` 释义为 Luria Bertani Broth，"
        "培养基一致。精确数值匹配项仅作下一版候选；`80` 编码项暂不入选。\n"
        "- 不修改旧协议、标签、五折或训练状态。\n"
    )
    (output / "report.md").write_text(report, encoding="utf-8")
    manifest = {
        "status": "blocked_source_80_code_unresolved", "generated_at": utc_now(),
        "paper": {"pmid": PMID, "doi": DOI, "article_url": PAPER_URL,
                  "supplement_url": SUPPLEMENT_URL, "source_data_url": SOURCE_DATA_URL},
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
        "review": {"records": review.record_id.nunique(), "observations": len(review),
                   "exact_source_data_values": int(review.exact_mic_match.sum()),
                   "unresolved_source_80_codes": int(review.source_80_code_unresolved.sum()),
                   "medium_conflicts": int((~review.medium_matches_paper).sum()),
                   "records_released_for_training": 0},
        "outputs": {name: sha256(output / name) for name in ("record_review.csv", "report.md")},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=ROOT / "03_experiments/audits/mic_training_source_20261001_v1/records.csv")
    parser.add_argument("--assays", type=Path, default=ROOT / "03_experiments/audits/mic_study_disjoint_20261001_v5/assay_observations.csv")
    raw = ROOT / "03_experiments/audits/mic_primary_review_pmid40645962_20261002_v1/raw"
    parser.add_argument("--supplement", type=Path, default=raw / "41467_2025_60051_MOESM1_ESM.pdf")
    parser.add_argument("--source-data", type=Path, default=raw / "41467_2025_60051_MOESM7_ESM.xlsx")
    parser.add_argument("--xml", type=Path, default=raw / "PMC12254355_fullTextXML.xml")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.records, args.assays, args.supplement, args.source_data,
                         args.xml, args.output), ensure_ascii=False, indent=2))
