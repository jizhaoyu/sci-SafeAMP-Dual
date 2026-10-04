"""Record unresolved MIC range and target annotation in Wang et al. 2025."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd
from pypdf import PdfReader

from research_utils import ROOT, sha256, utc_now, write_json


PMID = "39908380"
DOI = "10.1126/sciadv.adp7171"
ARTICLE_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC11797553/"
SUPPLEMENT_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11797553/supplementaryFiles"
PAPER_PEPTIDES = {
    "DBAASP:24619": ("AMP-3", "IGGKNGGWWGKVRWGLLSLIKGIAGQRLL"),
    "DBAASP:24628": ("AMP-30", "ILPTKWWSWPWIRISW"),
}


def run(records_path: Path, assays_path: Path, xml_path: Path, supplement_path: Path,
        output: Path) -> dict:
    paths = tuple(Path(path).resolve() for path in
                  (records_path, assays_path, xml_path, supplement_path))
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite paper review: {output}")
    if any(not path.is_file() for path in paths):
        raise FileNotFoundError("Frozen inventory or original paper files are missing.")
    records_path, assays_path, xml_path, supplement_path = paths
    article = " ".join(ElementTree.parse(xml_path).getroot().itertext())
    if ("Escherichia coli  GD004" not in article or "1.5625 to 200 μM" not in article
            or "in MHB medium" not in article):
        raise ValueError("Original article does not confirm target or MIC Methods range.")
    reader = PdfReader(supplement_path)
    if len(reader.pages) != 33:
        raise ValueError("Original supplement page count changed.")
    mic_table = "\n".join((reader.pages[i].extract_text() or "") for i in (17, 18))
    sequences = reader.pages[31].extract_text() or ""
    if ("TableS5" not in re.sub(r"\s+", "", mic_table)
            or "GD00" not in mic_table
            or "TableS18" not in re.sub(r"\s+", "", sequences)):
        raise ValueError("Original Table S5 or S18 cannot be identified.")
    records = pd.read_csv(records_path).set_index("record_id")
    assays = pd.read_csv(assays_path)
    selected = assays[
        assays.eligible.eq(True) & assays.derived_label.notna()
        & assays.assay_study_ids.astype(str).str.contains(f"pmid:{PMID}", regex=False)
    ]
    if len(selected) != 2 or set(selected.record_id) != set(PAPER_PEPTIDES):
        raise ValueError("Frozen Wang paper inventory differs from the two reviewed peptides.")
    rows = []
    for assay in selected.itertuples(index=False):
        name, paper_seq = PAPER_PEPTIDES[assay.record_id]
        source = records.loc[assay.record_id]
        if (source.seq != paper_seq or source.modifications != "none"
                or assay.target != "Escherichia coli" or assay.raw_mic != ">400"
                or assay.raw_unit != "µM" or assay.medium != "MHB"):
            raise ValueError(f"Frozen sequence or MIC differs: {assay.record_id}")
        number = name.split("-")[1]
        if re.search(r"(?m)^" + number + r"\s+" + re.escape(paper_seq) + r"\s+", sequences) is None:
            raise ValueError(f"Original Table S18 sequence missing: {assay.record_id}")
        if re.search(r"(?m)^" + re.escape(name) + r"\s+(?:\S+\s+){10}>400\s*$", mic_table) is None:
            raise ValueError(f"Original Table S5 GD004 MIC missing: {assay.record_id}")
        raw_path = ROOT / source.raw_path
        if sha256(raw_path) != source.raw_sha256:
            raise ValueError(f"Raw source hash differs: {assay.record_id}")
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        curated = json.loads(source.assay_conditions)["amp"][int(assay.assay_index)]
        activities = [item for item in raw["targetActivities"] if item.get("id") == curated.get("id")]
        if len(activities) != 1 or activities[0].get("concentration") != ">400":
            raise ValueError(f"Raw MIC activity cannot be matched: {assay.record_id}")
        rows.append({
            "record_id": assay.record_id, "paper_peptide_name": name,
            "paper_sequence": paper_seq, "database_sequence": source.seq,
            "paper_target": "Escherichia coli GD004", "database_target": assay.target,
            "paper_table_s5_mic": ">400", "paper_unit": "µM",
            "paper_methods_highest_declared_concentration_um": 200,
            "database_mic": assay.raw_mic, "database_activity_id": activities[0]["id"],
            "decision": "exclude_pending_range_and_target_resolution",
            "source_raw_path": source.raw_path, "source_raw_sha256": sha256(raw_path),
        })
    review = pd.DataFrame(rows).sort_values("record_id")
    output.mkdir(parents=True)
    review.to_csv(output / "record_review.csv", index=False)
    report = (
        "# Wang 等 2025 原论文阴性候选冲突审计\n\n"
        f"[原论文]({ARTICLE_URL})；[原始补充包]({SUPPLEMENT_URL})。"
        "Supplementary Table S18 可核对 2 条序列；Table S5 的 *E. coli* GD004 "
        "MIC 均记 `>400 µM`，与 DBAASP 原始数值相同。正文明确 GD004 是临床来源菌株，"
        "但冻结数据库目标只写 *E. coli*，须在新来源版本中补齐。\n\n"
        "正文 MIC Methods 声明肽浓度梯度为 1.5625–200 µM，与补充表 `>400 µM` 的"
        "右删失界限不一致。未找到解释前，不把这两条当作已核实阴性，也不计入五折候选；"
        "不以推断或改写阈值消除冲突。训练释放数为 0。\n"
    )
    (output / "report.md").write_text(report, encoding="utf-8")
    manifest = {
        "status": "blocked_paper_range_and_target_resolution", "generated_at": utc_now(),
        "paper": {"pmid": PMID, "doi": DOI, "article_url": ARTICLE_URL,
                  "supplement_url": SUPPLEMENT_URL},
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
        "review": {"records": len(review), "range_conflicts": len(review),
                   "target_annotations_pending": len(review), "records_released_for_training": 0},
        "outputs": {name: sha256(output / name) for name in ("record_review.csv", "report.md")},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=ROOT / "03_experiments/audits/mic_training_source_20261001_v1/records.csv")
    parser.add_argument("--assays", type=Path, default=ROOT / "03_experiments/audits/mic_study_disjoint_20261001_v5/assay_observations.csv")
    raw = ROOT / "03_experiments/audits/mic_primary_review_pmid39908380_20261002_v1/raw"
    parser.add_argument("--xml", type=Path, default=raw / "PMC11797553_fullTextXML.xml")
    parser.add_argument("--supplement", type=Path, default=raw / "supplement/sciadv.adp7171_sm.pdf")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.records, args.assays, args.xml, args.supplement, args.output),
                     ensure_ascii=False, indent=2))
