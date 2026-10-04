"""Compare frozen E. coli MIC observations with Richter et al. Table S1.

This checks primary-paper evidence only. It never changes labels, folds, or the
training gate; a later cohort audit must decide inclusion from source values.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd
from pypdf import PdfReader

from research_utils import ROOT, sha256, utc_now, write_json

PMID = "36551368"
DOI = "10.3390/antibiotics11121710"
ARTICLE_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC9774241/"
SUPPLEMENT_URL = "https://mdpi-res.com/d_attachment/antibiotics/antibiotics-11-01710/article_deploy/antibiotics-11-01710-s001.zip"
XML_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9774241/fullTextXML"
TARGET = "Escherichia coli ATCC 25922"


def run(records_path: Path, assays_path: Path, supplement_path: Path, xml_path: Path, output: Path) -> dict:
    paths = tuple(Path(path).resolve() for path in (records_path, assays_path, supplement_path, xml_path))
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite paper review: {output}")
    if any(not path.is_file() for path in paths):
        raise FileNotFoundError("A frozen inventory or original publication file is missing.")
    records_path, assays_path, supplement_path, xml_path = paths
    records = pd.read_csv(records_path).set_index("record_id")
    if not records.index.is_unique:
        raise ValueError("Frozen source record IDs are not unique.")
    assays = pd.read_csv(assays_path)
    selected = assays[
        assays.eligible.eq(True) & assays.derived_label.notna()
        & assays.assay_study_ids.astype(str).str.contains(f"pmid:{PMID}", regex=False)
    ].copy()
    if len(selected) != 7 or selected.record_id.nunique() != 7 or not selected.target.eq(TARGET).all():
        raise ValueError("Expected seven distinct frozen ATCC 25922 observations linked to this paper.")

    root = ElementTree.parse(xml_path).getroot()
    article_text = " ".join(root.itertext())
    for marker in ("Table S1", "ATCC 25922", "broth microdilution", "porcine red blood cells"):
        if marker not in article_text:
            raise ValueError(f"Original article XML lacks required assay context: {marker}")
    reader = PdfReader(supplement_path)
    if len(reader.pages) < 4:
        raise ValueError("Supplement does not contain the expected Table S1 pages.")
    table = "\n".join((page.extract_text() or "") for page in reader.pages[1:4])
    if "Table S1" not in table or "E. coli ATCC 25922" not in table:
        raise ValueError("Table S1 or its E. coli target column is missing.")

    rows = []
    for assay in selected.itertuples(index=False):
        source = records.loc[assay.record_id]
        source_path = ROOT / source.raw_path
        if sha256(source_path) != source.raw_sha256:
            raise ValueError(f"Raw record hash changed: {assay.record_id}")
        raw = json.loads(source_path.read_text(encoding="utf-8"))
        if raw.get("sequence") != source.seq or not any(
            item.get("pubmed", {}).get("pubmedId") == PMID for item in raw["articles"]
        ):
            raise ValueError(f"Raw sequence or paper PMID differs: {assay.record_id}")
        if int(assay.assay_index) >= len(raw["targetActivities"]):
            raise ValueError(f"Raw activity index out of range: {assay.record_id}")
        activity = raw["targetActivities"][int(assay.assay_index)]
        if (activity.get("activityMeasureValue") != "MIC"
                or activity.get("targetSpecies", {}).get("name") != TARGET
                or activity.get("concentration") != str(assay.raw_mic)
                or activity.get("unit", {}).get("name") != assay.raw_unit):
            raise ValueError(f"Frozen assay does not match its raw MIC activity: {assay.record_id}")
        mic_field = r"[<>]?[0-9.]+(?:-[0-9.]+)?"
        matches = re.findall(
            r"(?m)^" + re.escape(source.seq) + r"\s+([A-Za-z0-9-]+)\s+(" + mic_field + r")\s+"
            + mic_field + r"\s+" + mic_field + r"\s*$", table
        )
        if len(matches) != 1:
            raise ValueError(f"Sequence is absent or duplicated in original Table S1: {assay.record_id}")
        peptide_name, paper_mic = matches[0]
        same_mic = paper_mic == activity["concentration"] and activity["unit"]["name"] == "µg/ml"
        rows.append({
            "record_id": assay.record_id, "paper_peptide_name": peptide_name,
            "sequence": source.seq, "target": TARGET,
            "paper_table_s1_mic": paper_mic, "paper_unit": "µg/mL",
            "database_activity_id": activity["id"], "database_mic": activity["concentration"],
            "database_unit": activity["unit"]["name"], "database_mic_matches_paper": same_mic,
            "database_activity_reference": activity.get("reference", ""),
            "multiple_pmid_assignment": len(re.findall(r"pmid:\d+", assay.assay_study_ids)) > 1,
            "source_raw_path": source.raw_path, "source_raw_sha256": sha256(source_path),
        })

    review = pd.DataFrame(rows).sort_values("record_id")
    if not review.database_mic_matches_paper.all():
        raise ValueError("Original paper and raw database MIC differ; write a conflict audit first.")
    output.mkdir(parents=True)
    review.to_csv(output / "record_review.csv", index=False)
    report = (
        "# Richter 等 2022 原始测定审计\n\n"
        f"[原论文]({ARTICLE_URL})；[出版方补充包]({SUPPLEMENT_URL})。"
        "正文 Methods 确认 *E. coli* ATCC 25922 与肉汤微量稀释法；补充 Table S1 给出三次实验的 MIC。\n\n"
        "- 冻结清单中关联该论文的 7 条测定，肽序列均在 Table S1，表中 *E. coli* MIC 均为 `>128 µg/mL`，"
        "与原始 DBAASP 活动一致。逐条名称、活动 ID、测定引用及原文件哈希见 `record_review.csv`。\n"
        "- `DBAASP:20336` 同时列有 PMID 35884206 和 36551368；Table S1 已证实该值出现在后者，"
        "但保留其双论文出处标识以防跨论文折间泄漏。\n"
        "- `>128` 表示在最高测试浓度下未见抑制，是右删失结果。论文溶血使用猪红细胞，不能当作人红细胞 HC50。\n"
        "- 本审计只证明这 7 条原文对应关系；训练释放数为 0。全队列其余测定及既有冲突仍需处理。\n"
    )
    (output / "report.md").write_text(report, encoding="utf-8")
    manifest = {
        "status": "blocked_primary_review_in_progress", "generated_at": utc_now(),
        "paper": {"pmid": PMID, "doi": DOI, "article_url": ARTICLE_URL,
                  "supplement_url": SUPPLEMENT_URL, "xml_url": XML_URL},
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
        "review": {"records": len(review), "sequence_and_mic_matches": int(review.database_mic_matches_paper.sum()),
                   "multiple_pmid_records": int(review.multiple_pmid_assignment.sum()),
                   "records_released_for_training": 0},
        "outputs": {name: sha256(output / name) for name in ("record_review.csv", "report.md")},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=ROOT / "03_experiments/audits/mic_training_source_20261001_v1/records.csv")
    parser.add_argument("--assays", type=Path, default=ROOT / "03_experiments/audits/mic_study_disjoint_20261001_v5/assay_observations.csv")
    parser.add_argument("--supplement", type=Path, default=ROOT / "03_experiments/audits/mic_primary_review_pmid36551368_20261002_v1/raw/antibiotics-2036844-supplementary.pdf")
    parser.add_argument("--xml", type=Path, default=ROOT / "03_experiments/audits/mic_primary_review_pmid36551368_20261002_v1/raw/PMC9774241_fullTextXML.xml")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.records, args.assays, args.supplement, args.xml, args.output), ensure_ascii=False, indent=2))
