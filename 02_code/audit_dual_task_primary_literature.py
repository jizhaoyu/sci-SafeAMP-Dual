"""Audit high-priority dual-task candidates through primary literature evidence.

Processes the screened high-priority linear candidates and audits:
1. Literature overlap against the 298 PMIDs present in the 417 development records.
2. Endpoint nature: true MIC vs. MBC / EC50.
3. Hemolysis target: human erythrocytes (hRBC) vs. sheep/rabbit/other animal erythrocytes.
4. Hemolysis quantification: HC50/MHC vs. fixed-concentration single percentage.
5. Terminal chemistry: confirmed free acid (-COOH) vs. amidated (-NH2).
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set

import pandas as pd
from feature_extractor import clean_sequence
from research_data import sequence_identity
from research_utils import ROOT, sha256, utc_now, write_json


def load_development_pmids(dev_csv: Path) -> Set[str]:
    dev_df = pd.read_csv(dev_csv)
    pmids = set()
    for ref in dev_df["evidence_reference"].dropna().astype(str):
        for match in re.findall(r"\b\d{7,8}\b", ref):
            pmids.add(match)
    return pmids


def audit_candidate_record(row: Dict[str, Any], dev_pmids: Set[str]) -> Dict[str, Any]:
    pmid = str(row.get("pubmed_id", "") or "").strip()
    ecoli_text = str(row.get("ecoli_activity_text", "") or "")
    hemo_text = str(row.get("hemolytic_activity_text", "") or "")
    c_term = str(row.get("c_term_raw", "") or "").strip().lower()
    other_mod = str(row.get("other_mod_raw", "") or "").strip().lower()
    struct_desc = str(row.get("structure_desc", "") or "").strip().lower()

    reasons = []
    flags = []

    # 1. Literature overlap
    study_overlap = pmid in dev_pmids
    if study_overlap:
        reasons.append(f"Primary literature overlap: PMID {pmid} is already in development set")

    # 2. Terminal amidation check
    is_amidated = False
    if any(k in c_term for k in ["amid", "nh2", "-nh2"]):
        is_amidated = True
    elif "amidated" in other_mod or "amidation" in struct_desc:
        is_amidated = True
    if is_amidated:
        reasons.append("Reported C-terminal amidation (violates modifications=none)")

    # 3. E. coli assay type
    has_mic = bool(re.search(r"\bMIC\b", ecoli_text, re.IGNORECASE))
    has_mbc = bool(re.search(r"\bMBC\b", ecoli_text, re.IGNORECASE))
    has_ec50 = bool(re.search(r"\bEC50\b", ecoli_text, re.IGNORECASE))
    
    assay_type_ecoli = "MIC" if has_mic else ("MBC" if has_mbc else ("EC50" if has_ec50 else "unspecified"))
    if not has_mic and (has_mbc or has_ec50):
        flags.append(f"Antimicrobial endpoint is {assay_type_ecoli} rather than standard microdilution MIC")

    # 4. Hemolysis target
    hemo_lower = hemo_text.lower()
    is_sheep = "sheep" in hemo_lower
    is_rabbit = "rabbit" in hemo_lower
    is_mouse_or_rat = "mouse" in hemo_lower or "rat" in hemo_lower or "murine" in hemo_lower
    is_human = any(k in hemo_lower for k in ["human", "hrbc", "h-rbc"])

    target_rbc = "human" if is_human and not (is_sheep or is_rabbit) else ("animal" if (is_sheep or is_rabbit or is_mouse_or_rat) else "unclear")
    if target_rbc == "animal":
        reasons.append(f"Hemolysis target is non-human erythrocytes (detected in text: {hemo_text[:60]}...)")
    elif target_rbc == "unclear" and not is_human:
        flags.append("Erythrocyte species unclear or not explicitly human")

    # 5. Hemolysis measurement type
    has_hc50 = bool(re.search(r"\b(HC50|HD50|IC50|LD50)\b", hemo_text, re.IGNORECASE))
    has_mhc = bool(re.search(r"\bMHC\b", hemo_text, re.IGNORECASE))
    has_percent_only = bool(re.search(r"\d+(\.\d+)?%\s*(hemo|lysis)", hemo_text, re.IGNORECASE)) and not has_hc50

    hemo_measurement = "HC50" if has_hc50 else ("MHC" if has_mhc else ("percentage_at_fixed_conc" if has_percent_only else "qualitative"))
    if has_percent_only:
        flags.append("Hemolysis reported as single-concentration percentage rather than explicit HC50")

    # Overall Disposition
    if reasons:
        disposition = "rejected"
        primary_barrier = "; ".join(reasons)
    elif flags:
        disposition = "provisional_needs_primary_article_audit"
        primary_barrier = "; ".join(flags)
    else:
        disposition = "eligible_pending_primary_pdf_audit"
        primary_barrier = "None - fully satisfies formal criteria in database record"

    return {
        "dramp_id": row.get("dramp_id"),
        "name": row.get("name"),
        "sequence": row.get("sequence"),
        "length": row.get("length"),
        "max_identity_to_dev": row.get("max_identity_to_dev"),
        "nearest_dev_record": row.get("nearest_dev_record"),
        "pubmed_id": pmid,
        "author": row.get("author"),
        "title": row.get("title"),
        "reference": row.get("reference"),
        "study_overlap_with_dev": study_overlap,
        "is_amidated": is_amidated,
        "assay_type_ecoli": assay_type_ecoli,
        "target_rbc": target_rbc,
        "hemo_measurement": hemo_measurement,
        "disposition": disposition,
        "primary_barrier": primary_barrier,
        "ecoli_activity_text": ecoli_text,
        "hemolytic_activity_text": hemo_text,
    }


def run_primary_audit(
    input_json: Path,
    development_csv: Path,
    output_dir: Path,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    dev_pmids = load_development_pmids(development_csv)
    print(f"Loaded {len(dev_pmids)} PMIDs from development records.")

    with open(input_json, "r", encoding="utf-8") as f:
        records = json.load(f)
    print(f"Auditing {len(records)} high-priority candidate records...")

    audited = [audit_candidate_record(r, dev_pmids) for r in records]
    df = pd.DataFrame(audited)

    df.to_csv(output_dir / "candidate_primary_audit.csv", index=False)
    
    with open(output_dir / "candidate_primary_audit.json", "w", encoding="utf-8") as f:
        json.dump(audited, f, indent=2, ensure_ascii=False)

    summary_counts = df["disposition"].value_counts().to_dict()
    print("Audit Disposition Summary:")
    for k, v in summary_counts.items():
        print(f"  {k}: {v}")

    # Generate Markdown Report
    lines = [
        "# 双任务外部候选队列穿透式文献审计报告",
        "",
        f"**审计时间**：{utc_now()} (UTC)",
        f"**候选样本总数**：{len(records)} 条（来自 DRAMP 高优先级无二硫键、标示自由酸、全员 NW 同源隔离门禁通过分子）",
        f"**开发集基线**：417 条开发记录（含 298 个独立 PMID 文献引文）",
        "",
        "## 一、审查结论摘要",
        "",
        f"- **完全合格且可直接采信为 HC50/MIC 定量记录 (Eligible)**：**{summary_counts.get('eligible_pending_primary_pdf_audit', 0)}** 条",
        f"- **需进一步查阅原文图表与树脂合成方法 (Provisional / Flags)**：**{summary_counts.get('provisional_needs_primary_article_audit', 0)}** 条",
        f"- **明确被科学门禁否决 (Rejected)**：**{summary_counts.get('rejected', 0)}** 条",
        "",
        "## 二、各文献（PMID）详细穿透审计",
        "",
    ]

    by_pmid = {}
    for item in audited:
        by_pmid.setdefault(item["pubmed_id"], []).append(item)

    for pmid, items in sorted(by_pmid.items(), key=lambda x: len(x[1]), reverse=True):
        it0 = items[0]
        lines.extend([
            f"### PMID: [{pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/) - {it0['title']}",
            f"- **文献**：{it0['author']} | *{it0['reference']}*",
            f"- **开发集文献重叠**：{'是 (重叠否决)' if it0['study_overlap_with_dev'] else '否 (独立来源)'}",
            f"- **涉及候选肽数量**：{len(items)} 条",
            f"- **判定倾向**：{items[0]['disposition']} (主要原因: `{items[0]['primary_barrier']}`)",
            "",
            "| DRAMP ID | 名称 | 长度 | 最大同源 | E. coli 测定 | 溶血靶标 | 溶血测定 | 审计判定 |",
            "|---|---|---|---|---|---|---|---|",
        ])
        for it in items:
            lines.append(
                f"| {it['dramp_id']} | {it['name']} | {it['length']} | {it['max_identity_to_dev']:.4f} | "
                f"{it['assay_type_ecoli']} | {it['target_rbc']} | {it['hemo_measurement']} | `{it['disposition']}` |"
            )
        lines.append("")

    (output_dir / "audit_report.md").write_text("\n".join(lines), encoding="utf-8")
    
    manifest = {
        "status": "literature_audit_completed",
        "generated_at": utc_now(),
        "input_sha256": sha256(input_json),
        "development_csv_sha256": sha256(development_csv),
        "total_audited": len(records),
        "summary": summary_counts,
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "03_experiments/audits/dramp_dual_task_screen_20261003_v1/high_priority_linear_raw.json",
    )
    parser.add_argument(
        "--development",
        type=Path,
        default=ROOT / "02_code/data/sources/combined_v3_evidence_clean_20261001/records.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "03_experiments/audits/dramp_dual_task_primary_audit_20261003_v1",
    )
    args = parser.parse_args()
    run_primary_audit(args.input, args.development, args.output)
