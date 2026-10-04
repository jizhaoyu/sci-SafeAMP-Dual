"""Compare one high-priority MIC study against its original supplementary data.

This is a paper-level evidence audit, not a training release. It never changes
the frozen cohort or a prior readiness decision.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

from public_data import measurement_label
from research_utils import ROOT, sha256, utc_now, write_json

PMID = "42206144"
DOI = "10.1038/s42256-026-01237-5"
PAPER_URL = f"https://www.nature.com/articles/s42256-026-01237-5"
SUPPLEMENT_PDF_URL = (
    "https://media.springernature.com/original/springer-static/esm/"
    "art%3A10.1038%2Fs42256-026-01237-5/MediaObjects/42256_2026_1237_MOESM1_ESM.pdf"
)
SUPPLEMENT_CSV_URL = (
    "https://media.springernature.com/original/springer-static/esm/"
    "art%3A10.1038%2Fs42256-026-01237-5/MediaObjects/42256_2026_1237_MOESM3_ESM.csv"
)
TARGET_COLUMNS = {
    "Escherichia coli ATCC 11775": "E. coli ATCC 11775",
    "Escherichia coli AIC221": "E. coli AIC221",
    "Escherichia coli AIC222": "E. coli AIC222 - CRE",
}


def paper_key(identifiers: str) -> str:
    pmids = sorted(set(re.findall(r"pmid:(\d+)", identifiers)))
    dois = sorted(set(re.findall(r"doi:([^|]+)", identifiers)))
    article_ids = sorted(set(re.findall(r"dbaasp_article:(\d+)", identifiers)))
    if len(pmids) == 1:
        return f"pmid:{pmids[0]}"
    if len(pmids) > 1:
        return "ambiguous_multiple_pmids:" + "|".join(pmids)
    if len(dois) == 1:
        return f"doi:{dois[0]}"
    if len(article_ids) == 1:
        return f"dbaasp_article:{article_ids[0]}:bibliographic_id_missing"
    return "unresolved_primary_study"


def source_sequence(reader: PdfReader, name: str) -> tuple[str | None, str | None]:
    matches = []
    pattern = re.compile(r"(?<![A-Za-z0-9-])" + re.escape(name) + r"\s+([ACDEFGHIKLMNPQRSTVWY]{10,50})\b")
    for page_number in (3, 4, 14):
        text = reader.pages[page_number - 1].extract_text() or ""
        matches.extend((match.group(1), page_number) for match in pattern.finditer(text))
    sequences = {value for value, _ in matches}
    if len(sequences) != 1:
        return None, None
    sequence = next(iter(sequences))
    return sequence, ",".join(str(page) for _, page in matches)


def run(records_path: Path, assays_path: Path, pdf_path: Path, csv_path: Path, output: Path) -> dict:
    output = Path(output)
    products = [output / name for name in ("paper_queue.csv", "paper_assays.csv", "raw_activity_review.csv",
                                           "record_review.csv", "manifest.json", "report.md")]
    if any(path.exists() for path in products):
        raise FileExistsError("Refusing to overwrite any existing primary-review product.")
    for path in (records_path, assays_path, pdf_path, csv_path):
        if not Path(path).is_file():
            raise FileNotFoundError(path)

    records = pd.read_csv(records_path)
    assays = pd.read_csv(assays_path)
    eligible = assays[assays.eligible.eq(True) & assays.derived_label.notna()].copy()
    if len(eligible) != 458 or eligible[["record_id", "assay_index", "assay_study_ids"]].isna().any().any():
        raise ValueError("The frozen 458-observation inventory changed or is incomplete.")
    eligible["paper_key"] = eligible.assay_study_ids.astype(str).map(paper_key)
    queue = eligible.groupby("paper_key", dropna=False).agg(
        observation_count=("record_id", "size"), record_count=("record_id", "nunique"),
        positive_observations=("derived_label", "sum"), target_count=("target", "nunique")
    ).reset_index().sort_values(["record_count", "observation_count", "paper_key"], ascending=[False, False, True])
    queue["review_status"] = queue.paper_key.map(lambda value: "partially_reviewed" if value == f"pmid:{PMID}" else "not_reviewed")

    selected = eligible[eligible.paper_key.eq(f"pmid:{PMID}")].copy()
    if selected.record_id.nunique() != 10 or len(selected) != 21:
        raise ValueError("The selected paper no longer maps to the expected 10 records and 21 observations.")
    source = records[records.record_id.isin(selected.record_id)].copy()
    if len(source) != 10 or source.record_id.duplicated().any():
        raise ValueError("Selected paper record mapping changed.")
    reader = PdfReader(pdf_path)
    if len(reader.pages) < 14:
        raise ValueError("Supplement PDF is incomplete.")
    supplement = pd.read_csv(csv_path).rename(columns={"Unnamed: 0": "peptide_name"})
    if supplement.peptide_name.duplicated().any() or not set(TARGET_COLUMNS.values()).issubset(supplement.columns):
        raise ValueError("Supplement CSV has duplicate names or missing E. coli columns.")
    supplement = supplement.set_index("peptide_name")
    reference = selected.set_index(["record_id", "target"])
    if reference.index.duplicated().any():
        raise ValueError("More than one database observation maps to the same peptide and strain.")

    paper_rows, activity_rows, record_rows = [], [], []
    for record in source.itertuples(index=False):
        raw_path = ROOT / record.raw_path
        if sha256(raw_path) != record.raw_sha256:
            raise ValueError(f"DBAASP raw record hash changed for {record.record_id}.")
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        name = str(raw.get("name", ""))
        raw_activities = {target: [] for target in TARGET_COLUMNS}
        for activity in raw.get("targetActivities", []):
            target_name = activity.get("targetSpecies", {}).get("name", "")
            if target_name in TARGET_COLUMNS and activity.get("activityMeasureValue") == "MIC":
                raw_activities[target_name].append(activity)
        if any(not values for values in raw_activities.values()):
            raise ValueError(f"Raw DBAASP E. coli observation coverage changed for {record.record_id}.")
        paper_seq, paper_pages = source_sequence(reader, name)
        sequence_match = paper_seq == record.seq
        if name not in supplement.index:
            raise ValueError(f"Original data table has no peptide name {name!r}.")
        record_rows_current = []
        for target, paper_column in TARGET_COLUMNS.items():
            paper_mic = str(supplement.loc[name, paper_column]).strip()
            paper_label = measurement_label(
                {"concentration": paper_mic, "unit": {"name": "µM"}}, record.seq, 32, 128
            ) if sequence_match else None
            key = (record.record_id, target)
            curated_row = reference.loc[key] if key in reference.index else None
            matching_activities = []
            for raw_activity in raw_activities[target]:
                db_mic = str(raw_activity.get("concentration", "")).strip()
                db_unit = str(raw_activity.get("unit", {}).get("name", "")).strip()
                if db_unit not in {"µM", "μM", "uM"}:
                    raise ValueError(f"Unexpected raw DBAASP unit for {record.record_id} / {target}: {db_unit}.")
                matches = db_mic == paper_mic
                matching_activities.append(matches)
                activity_rows.append({
                    "record_id": record.record_id, "peptide_name": name,
                    "raw_activity_id": raw_activity.get("id"), "target": target,
                    "database_mic": db_mic, "database_unit": db_unit,
                    "database_note": str(raw_activity.get("note", "")),
                    "database_derived_label": measurement_label(raw_activity, record.seq, 32, 128),
                    "paper_mic": paper_mic, "paper_unit": "µmol/L",
                    "database_mic_matches_paper": matches,
                    "curated_binary_observation_present": bool(
                        curated_row is not None and str(curated_row.raw_mic).strip() == db_mic
                    ),
                })
            conflicting_count = matching_activities.count(False)
            status = ("sequence_mismatch_or_unresolved" if not sequence_match else
                      "duplicate_database_target_conflict" if conflicting_count and len(matching_activities) > 1 else
                      "database_mic_conflict" if conflicting_count else
                      "source_observation_concordant_pending_chemistry")
            record_rows_current.append({
                "record_id": record.record_id, "peptide_name": name, "sequence": record.seq,
                "paper_sequence": paper_seq or "", "paper_sequence_pdf_pages": paper_pages or "",
                "sequence_match": sequence_match, "target": target, "paper_mic": paper_mic,
                "paper_unit": "µmol/L", "paper_derived_label": paper_label,
                "database_mic": "|".join(str(item.get("concentration", "")).strip() for item in raw_activities[target]),
                "database_raw_activity_ids": "|".join(str(item.get("id", "")) for item in raw_activities[target]),
                "database_notes": "|".join(str(item.get("note", "")) for item in raw_activities[target]),
                "database_observation_count": len(raw_activities[target]),
                "database_conflicting_observation_count": conflicting_count,
                "database_observation_present": True,
                "database_mic_matches_paper": conflicting_count == 0,
                "curated_binary_observation_present": curated_row is not None,
                "curated_binary_mic": str(curated_row.raw_mic).strip() if curated_row is not None else "",
                "curated_binary_label": curated_row.derived_label if curated_row is not None else None,
                "review_status": status,
            })
        paper_rows.extend(record_rows_current)
        labels = {row["paper_derived_label"] for row in record_rows_current if row["paper_derived_label"] is not None}
        paper_record_label = next(iter(labels)) if len(labels) == 1 else None
        conflicts = [row["target"] for row in record_rows_current if row["database_conflicting_observation_count"]]
        record_rows.append({
            "record_id": record.record_id, "peptide_name": name,
            "sequence_match": sequence_match, "paper_sequence_pdf_pages": paper_pages or "",
            "database_label": int(record.amp), "paper_rederived_record_label": paper_record_label,
            "paper_label_conflict": len(labels) > 1, "database_mic_conflict_targets": "|".join(conflicts),
            "review_status": "primary_value_conflict" if conflicts else
                             "paper_sequence_unresolved" if not sequence_match else
                             "primary_values_concordant_pending_chemistry_review",
        })
    observations = pd.DataFrame(paper_rows).sort_values(["record_id", "target"])
    activity_review = pd.DataFrame(activity_rows).sort_values(["record_id", "target", "raw_activity_id"])
    reviewed = pd.DataFrame(record_rows).sort_values("record_id")
    output.mkdir(parents=True, exist_ok=True)
    queue.to_csv(products[0], index=False, encoding="utf-8-sig")
    observations.to_csv(products[1], index=False, encoding="utf-8-sig")
    activity_review.to_csv(products[2], index=False, encoding="utf-8-sig")
    reviewed.to_csv(products[3], index=False, encoding="utf-8-sig")
    summary = {
        "status": "blocked_primary_review_in_progress", "generated_at": utc_now(),
        "paper": {"pmid": PMID, "doi": DOI, "article_url": PAPER_URL,
                  "supplement_pdf_url": SUPPLEMENT_PDF_URL, "supplement_csv_url": SUPPLEMENT_CSV_URL,
                  "article_license": "CC BY 4.0 as stated on the publisher article page"},
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.resolve().relative_to(ROOT)): sha256(path) for path in
                   (records_path, assays_path, pdf_path, csv_path)},
        "paper_review": {
            "records": len(reviewed), "paper_ecoli_observations": len(observations),
            "database_observations": len(activity_review),
            "curated_binary_observations": int(observations.curated_binary_observation_present.sum()),
            "sequence_matches": int(reviewed.sequence_match.sum()),
            "database_mic_matches": int(activity_review.database_mic_matches_paper.eq(True).sum()),
            "database_mic_conflicts": int(activity_review.database_mic_matches_paper.eq(False).sum()),
            "paper_targets_with_database_conflicts": int(observations.database_conflicting_observation_count.gt(0).sum()),
            "raw_observations_not_in_binary_inventory": int(activity_review.curated_binary_observation_present.eq(False).sum()),
            "records_fully_released_for_training": 0,
        },
        "remaining_review": "Primary-paper assay conditions and terminal chemistry require record-level confirmation; one database MIC conflicts with the source. All other studies remain unreviewed.",
        "outputs": {path.name: sha256(path) for path in products[:4]},
    }
    write_json(products[4], summary)
    products[5].write_text(
        "# MIC 原始论文逐测定核对：PMID 42206144\n\n"
        f"生成时间：{summary['generated_at']}；状态：`{summary['status']}`。\n\n"
        f"原论文：[DOI {DOI}]({PAPER_URL})；序列来自补充 PDF 的表 1、表 2；"
        "MIC 来自补充 Data 1 CSV，单位 µmol/L，菌株定义与微量肉汤稀释法见原论文 Methods。\n\n"
        f"10 条数据库记录的序列均与原文相符；30 个论文靶标对应 {len(activity_review)} 条原始数据库测定，其中 "
        f"{summary['paper_review']['database_mic_matches']} 条 MIC 与原表一致、"
        f"{summary['paper_review']['database_mic_conflicts']} 条冲突。当前二值训练清单保留 "
        f"{summary['paper_review']['curated_binary_observations']} 条测定；另 "
        f"{summary['paper_review']['raw_observations_not_in_binary_inventory']} 条未进入二值清单。\n\n"
        "冲突：`DBAASP:25512` / Hydrodamin-3-6 / E. coli AIC222：原始数据库有 `16 µM` "
        "（活动 ID 202714，备注 CRE）及 `>64 µM`（活动 ID 202721，备注 VRE）两条，"
        "原论文补充 CSV 仅有 `16 µM`。后者进入了旧二值清单；不猜测 VRE 条目本应属于哪个菌株，"
        "也不直接修补旧数据。\n\n"
        "本次未核实末端化学形式及所有实验条件是否逐记录一致，不能据此释放训练。"
        "完整逐靶标、逐原始活动和逐记录结果见 `paper_assays.csv`、`raw_activity_review.csv` 与 `record_review.csv`；"
        "其余论文按 `paper_queue.csv` 继续。\n",
        encoding="utf-8",
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=ROOT / "03_experiments/audits/mic_training_source_20261001_v1/records.csv")
    parser.add_argument("--assays", type=Path, default=ROOT / "03_experiments/audits/mic_study_disjoint_20261001_v5/assay_observations.csv")
    parser.add_argument("--pdf", type=Path, default=ROOT / "03_experiments/audits/mic_primary_review_20261001_v1/raw/42256_2026_1237_MOESM1_ESM.pdf")
    parser.add_argument("--csv", type=Path, default=ROOT / "03_experiments/audits/mic_primary_review_20261001_v1/raw/42256_2026_1237_MOESM3_ESM.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "03_experiments/audits/mic_primary_review_20261001_v1")
    args = parser.parse_args()
    print(json.dumps(run(args.records, args.assays, args.pdf, args.csv, args.output), ensure_ascii=False, indent=2))
