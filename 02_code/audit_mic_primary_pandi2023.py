"""Expose C-terminal chemistry mismatch in two frozen Pandi et al. MIC records."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

from research_utils import ROOT, sha256, utc_now, write_json


PMID = "37938588"
DOI = "10.1038/s41467-023-42434-9"
PAPER_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC10632401/"
SUPPLEMENT_URL = "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-023-42434-9/MediaObjects/41467_2023_42434_MOESM1_ESM.pdf"
TABLE_10 = {"DBAASP:21528": ("AMP #13", "25.0"), "DBAASP:21534": ("AMP #12", "37.5")}
TARGET = "Escherichia coli MG1655"


def run(records_path: Path, assays_path: Path, supplement_path: Path, output: Path) -> dict:
    paths = tuple(Path(path).resolve() for path in (records_path, assays_path, supplement_path))
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite paper review: {output}")
    if any(not path.is_file() for path in paths):
        raise FileNotFoundError("Frozen inventory or original supplement is missing.")
    records_path, assays_path, supplement_path = paths
    records = pd.read_csv(records_path).set_index("record_id")
    if not records.index.is_unique:
        raise ValueError("Frozen source record IDs are not unique.")
    assays = pd.read_csv(assays_path)
    selected = assays[
        assays.eligible.eq(True) & assays.derived_label.notna()
        & assays.assay_study_ids.astype(str).str.contains(f"pmid:{PMID}", regex=False)
    ]
    if len(selected) != 2 or set(selected.record_id) != set(TABLE_10):
        raise ValueError("Frozen paper inventory differs from two reviewed records.")
    reader = PdfReader(supplement_path)
    table = reader.pages[13].extract_text() or ""
    chemistry = reader.pages[27].extract_text() or ""
    if "Supplementary Table 10" not in table or "E. coli MIC" not in table:
        raise ValueError("Original supplementary MIC table is missing.")
    if "Supplementary Fig. 16" not in chemistry or "Supplementary Fig. 17" not in chemistry:
        raise ValueError("Original supplementary synthesis evidence is missing.")

    rows = []
    for assay in selected.itertuples(index=False):
        source = records.loc[assay.record_id]
        paper_name, expected_mic = TABLE_10[assay.record_id]
        if assay.target != TARGET:
            raise ValueError(f"Frozen target differs: {assay.record_id}")
        mic_match = re.search(r"(?m)^" + re.escape(paper_name) + r"\s+([0-9.]+)\s+", table)
        if mic_match is None or mic_match.group(1) != expected_mic:
            raise ValueError(f"Original Table 10 MIC differs: {assay.record_id}")
        paper_form = f"H2N-{source.seq}-CONH2"
        if paper_form not in chemistry:
            raise ValueError(f"Original synthesis caption lacks amidated exact sequence: {assay.record_id}")
        raw_path = ROOT / source.raw_path
        if sha256(raw_path) != source.raw_sha256:
            raise ValueError(f"Raw record hash differs: {assay.record_id}")
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        if raw.get("sequence") != source.seq or not any(
            article.get("pubmed", {}).get("pubmedId") == PMID for article in raw["articles"]
        ):
            raise ValueError(f"Raw sequence or PMID differs: {assay.record_id}")
        # assay_index indexes the curated amp list, not raw targetActivities.
        curated = json.loads(source.assay_conditions)["amp"][int(assay.assay_index)]
        activities = [item for item in raw["targetActivities"] if item.get("id") == curated.get("id")]
        if len(activities) != 1:
            raise ValueError(f"Curated activity ID is absent or duplicated in raw source: {assay.record_id}")
        activity = activities[0]
        if (activity.get("activityMeasureValue") != "MIC"
                or activity.get("targetSpecies", {}).get("name") != TARGET
                or activity.get("concentration") != str(assay.raw_mic)
                or activity.get("unit", {}).get("name") != assay.raw_unit):
            raise ValueError(f"Frozen and raw MIC differ: {assay.record_id}")
        if activity["concentration"] != expected_mic.rstrip("0").rstrip(".") or activity["unit"]["name"] != "µM":
            raise ValueError(f"Raw MIC and original Table 10 differ: {assay.record_id}")
        if source.modifications != "none" or raw.get("cTerminus") is not None:
            raise ValueError(f"Frozen chemistry changed; redo audit: {assay.record_id}")
        rows.append({
            "record_id": assay.record_id, "paper_peptide_name": paper_name,
            "sequence": source.seq, "target": TARGET, "paper_mic": expected_mic,
            "paper_unit": "µM", "database_activity_id": activity["id"],
            "database_mic": activity["concentration"], "database_unit": activity["unit"]["name"],
            "paper_molecular_form": paper_form, "frozen_modifications": source.modifications,
            "raw_c_terminus": raw.get("cTerminus"),
            "decision": "exclude_from_training_molecular_identity_mismatch",
            "source_raw_path": source.raw_path, "source_raw_sha256": sha256(raw_path),
        })
    review = pd.DataFrame(rows).sort_values("record_id")
    output.mkdir(parents=True)
    review.to_csv(output / "record_review.csv", index=False)
    report = (
        "# Pandi 等 2023 原始测定与分子形式冲突审计\n\n"
        f"[原论文]({PAPER_URL})；[出版方补充 PDF]({SUPPLEMENT_URL})。"
        "Supplementary Table 10 的 *E. coli* MIC 与 2 条冻结测定数值相符；"
        "Supplementary Fig. 16–17 的合成信息给出对应完整序列，且均写明 C 端 `-CONH2`。\n\n"
        "- 冻结 `records.csv` 两条均写 `modifications=none`；原始 DBAASP `cTerminus` 均为空。"
        "序列字母虽相同，受测分子的末端化学形式未被来源清单表达。\n"
        "- 两条均暂时排除训练。只有在新版本来源与特征协议明确表达酰胺化、重新核对分子身份和重建隔离审计后，"
        "才能重新评估；不修改旧记录或旧协议。\n"
    )
    (output / "report.md").write_text(report, encoding="utf-8")
    manifest = {
        "status": "excluded_molecular_identity_mismatch", "generated_at": utc_now(),
        "paper": {"pmid": PMID, "doi": DOI, "article_url": PAPER_URL, "supplement_url": SUPPLEMENT_URL},
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
        "review": {"records": len(review), "chemistry_conflicts": len(review),
                   "records_released_for_training": 0},
        "outputs": {name: sha256(output / name) for name in ("record_review.csv", "report.md")},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=ROOT / "03_experiments/audits/mic_training_source_20261001_v1/records.csv")
    parser.add_argument("--assays", type=Path, default=ROOT / "03_experiments/audits/mic_study_disjoint_20261001_v5/assay_observations.csv")
    parser.add_argument("--supplement", type=Path, default=ROOT / "03_experiments/audits/mic_primary_review_pmid37938588_20261002_v1/raw/41467_2023_42434_MOESM1_ESM.pdf")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.records, args.assays, args.supplement, args.output), ensure_ascii=False, indent=2))
