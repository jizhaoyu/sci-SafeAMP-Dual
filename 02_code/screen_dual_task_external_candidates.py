"""Dual-task external candidate screening and penetration audit script.

Evaluates natural/synthetic peptides from DRAMP for simultaneous:
1. E. coli antimicrobial activity (MIC)
2. Human erythrocyte hemolytic activity (HC50 / hemolysis)
3. Strict all-member homology separation against the 417 development records (<0.40 NW identity under protocol-amd-02)
4. Chemical form analysis (terminal modifications, cyclization, disulfide bonds)
5. Primary literature tracing (PMID, DOI, experimental conditions)
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from feature_extractor import clean_sequence
from research_data import sequence_identity
from research_protocol_config import get_protocol, protocol_digest
from research_utils import ROOT, sha256, utc_now, write_json

CANONICAL_20 = set("ACDEFGHIKLMNPQRSTVWY")


def is_canonical_peptide(seq: str, min_len: int = 10, max_len: int = 50) -> bool:
    if not isinstance(seq, str):
        return False
    clean = seq.strip().upper()
    if not (min_len <= len(clean) <= max_len):
        return False
    return set(clean).issubset(CANONICAL_20)


def extract_ecoli_text(row: pd.Series) -> str:
    parts = []
    for col in ["Activity", "Target_Organism", "Comments"]:
        val = str(row.get(col, "") or "").strip()
        if val and val.lower() != "nan":
            parts.append(val)
    return " | ".join(parts)


def extract_hemo_text(row: pd.Series) -> str:
    parts = []
    for col in ["Hemolytic_activity", "Cytotoxicity", "Comments"]:
        val = str(row.get(col, "") or "").strip()
        if val and val.lower() != "nan":
            parts.append(val)
    return " | ".join(parts)


def check_dual_relevance(row: pd.Series) -> Tuple[bool, bool, str, str]:
    ecoli_text = extract_ecoli_text(row)
    hemo_text = extract_hemo_text(row)

    # E. coli check
    ecoli_match = bool(re.search(r"\b(e\.?\s*coli|escherichia\s+coli)\b", ecoli_text, re.IGNORECASE))

    # Hemolytic / Human RBC check
    hemo_kw = bool(re.search(r"(hemo|haemo|erythrocyte|rbc|red blood cell)", hemo_text, re.IGNORECASE))
    human_kw = bool(re.search(r"(human|hrbc|h-rbc|blood|rbc|erythrocyte)", hemo_text, re.IGNORECASE))
    
    # Needs both hemolytic indication and relevant erythrocyte assay context
    hemo_match = hemo_kw and human_kw

    return ecoli_match, hemo_match, ecoli_text, hemo_text


def classify_modifications(row: pd.Series) -> Dict[str, str]:
    c_term = str(row.get("C-terminal_Modification", "") or "").strip()
    n_term = str(row.get("N-terminal_Modification", "") or "").strip()
    other_mod = str(row.get("Other_Modifications", "") or "").strip()
    structure = str(row.get("Structure", "") or "").strip()
    struct_desc = str(row.get("Structure_Description", "") or "").strip()
    topology = str(row.get("Linear/Cyclic/Branched", "") or "").strip()
    seq = str(row.get("Sequence", "") or "").strip()

    c_count = seq.count("C")
    
    # Amidation check
    is_amidated = False
    c_term_lower = c_term.lower()
    if any(k in c_term_lower for k in ["amid", "nh2", "-nh2"]):
        is_amidated = True
    elif "amidated" in other_mod.lower() or "amidation" in struct_desc.lower():
        is_amidated = True

    # Cyclization / Disulfide check
    has_disulfide = False
    if "disulfide" in struct_desc.lower() or "bridge" in struct_desc.lower() or c_count >= 2:
        has_disulfide = True
    is_cyclic = False
    if "cyclic" in topology.lower() or "cyclic" in structure.lower() or "cyclotide" in str(row.get("Family", "")).lower():
        is_cyclic = True

    # High priority candidate: Linear, no reported C-terminal amidation, <= 1 Cys
    is_high_priority_linear = (
        not is_amidated
        and not is_cyclic
        and c_count <= 1
        and c_term_lower in ["none", "", "free", "free acid", "-cooh", "c-terminal free acid", "nan"]
    )

    return {
        "c_term_raw": c_term,
        "n_term_raw": n_term,
        "other_mod_raw": other_mod,
        "topology": topology,
        "structure_desc": struct_desc,
        "cys_count": str(c_count),
        "is_amidated": str(is_amidated),
        "has_disulfide": str(has_disulfide),
        "is_cyclic": str(is_cyclic),
        "is_high_priority_linear": str(is_high_priority_linear),
    }


def run_dual_task_screen(
    dramp_excel: Path,
    development_csv: Path,
    output_dir: Path,
    homology_cutoff: float = 0.40,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading development records from {development_csv}...")
    dev_df = pd.read_csv(development_csv)
    dev_records = []
    for _, r in dev_df.iterrows():
        clean_s = clean_sequence(r["seq"])
        dev_records.append({"record_id": r["record_id"], "seq": clean_s})

    print(f"Loaded {len(dev_records)} development records.")

    print(f"Loading DRAMP records from {dramp_excel}...")
    dramp_df = pd.read_excel(dramp_excel)
    print(f"Loaded {len(dramp_df)} DRAMP records.")

    # 1. Prescreen: valid sequence, length 10-50, canonical 20 aa
    valid_candidates = []
    for _, row in dramp_df.iterrows():
        raw_seq = str(row.get("Sequence", "") or "").strip().upper()
        if not is_canonical_peptide(raw_seq, 10, 50):
            continue

        ecoli_match, hemo_match, ecoli_text, hemo_text = check_dual_relevance(row)
        if not (ecoli_match and hemo_match):
            continue

        valid_candidates.append((row, raw_seq, ecoli_text, hemo_text))

    print(f"Prescreened {len(valid_candidates)} candidates matching dual assay criteria.")

    # 2. Homology screening against all 417 development records
    results = []
    for row, seq, ecoli_text, hemo_text in valid_candidates:
        dramp_id = str(row.get("DRAMP_ID", "")).strip()
        name = str(row.get("Name", "")).strip()

        # Compute NW identity against all development records
        identities = []
        nearest_dev_id = ""
        max_identity = 0.0

        for dev in dev_records:
            ident = sequence_identity(seq, dev["seq"], identity_mode="alignment")
            if ident > max_identity:
                max_identity = ident
                nearest_dev_id = dev["record_id"]

        mod_info = classify_modifications(row)

        pmid = str(row.get("Pubmed_ID", "") or "").strip()
        ref = str(row.get("Reference", "") or "").strip()
        author = str(row.get("Author", "") or "").strip()
        title = str(row.get("Title", "") or "").strip()

        res_entry = {
            "dramp_id": dramp_id,
            "name": name,
            "sequence": seq,
            "length": len(seq),
            "max_identity_to_dev": max_identity,
            "nearest_dev_record": nearest_dev_id,
            "violates_cutoff": max_identity >= homology_cutoff,
            "passes_homology_cutoff": max_identity < homology_cutoff,
            **mod_info,
            "pubmed_id": pmid,
            "author": author,
            "title": title,
            "reference": ref,
            "ecoli_activity_text": ecoli_text,
            "hemolytic_activity_text": hemo_text,
        }
        results.append(res_entry)

    res_df = pd.DataFrame(results)

    # Sort: passes cutoff first, is_high_priority_linear first, then lowest identity
    res_df["is_linear_flag"] = res_df["is_high_priority_linear"].map({"True": 1, "False": 0})
    res_df["passes_cutoff_flag"] = res_df["passes_homology_cutoff"].map({True: 1, False: 0})
    res_df = res_df.sort_values(
        by=["passes_cutoff_flag", "is_linear_flag", "max_identity_to_dev"],
        ascending=[False, False, True],
    ).drop(columns=["is_linear_flag", "passes_cutoff_flag"])

    # Split into passing vs failing
    passing_df = res_df[res_df["passes_homology_cutoff"]].copy()
    high_priority_linear = passing_df[passing_df["is_high_priority_linear"] == "True"].copy()

    # Save outputs
    res_df.to_csv(output_dir / "all_screened_dual_candidates.csv", index=False)
    passing_df.to_csv(output_dir / "homology_passed_candidates.csv", index=False)
    high_priority_linear.to_csv(output_dir / "high_priority_linear_candidates.csv", index=False)

    summary_stats = {
        "total_dramp_records": len(dramp_df),
        "dual_assay_relevant_canonical_10_50": len(valid_candidates),
        "homology_cutoff": homology_cutoff,
        "homology_passed_count": len(passing_df),
        "homology_failed_count": len(res_df) - len(passing_df),
        "passing_high_priority_linear_count": len(high_priority_linear),
        "passing_disulfide_or_cyclic_count": len(passing_df) - len(high_priority_linear),
    }

    manifest = {
        "status": "screen_completed",
        "generated_at": utc_now(),
        "dramp_source_sha256": sha256(dramp_excel),
        "development_records_sha256": sha256(development_csv),
        "statistics": summary_stats,
    }
    write_json(output_dir / "screen_manifest.json", manifest)

    # Write report
    report_lines = [
        "# DRAMP 外部候选队列穿透式审查报告",
        "",
        f"**审查时间**：{manifest['generated_at']} (UTC)",
        f"**比对协议**：`protocol-amd-02` (Global NW, denominator = alignment length, cutoff = {homology_cutoff})",
        f"**开发集基线**：417 条开发记录 ({development_csv.name})",
        "",
        "## 一、核心筛选统计结论",
        "",
        f"- **DRAMP 原始多肽总数**：{summary_stats['total_dramp_records']} 条",
        f"- **同时包含 E. coli 与溶血活性描述且符合 10-50 aa 标准天然残基的多肽**：{summary_stats['dual_assay_relevant_canonical_10_50']} 条",
        f"- **通过全员同源隔离门禁 (< 0.40) 的候选多肽**：**{summary_stats['homology_passed_count']}** 条",
        f"- **被全员同源门禁排除 (≥ 0.40) 的候选多肽**：{summary_stats['homology_failed_count']} 条",
        f"- **在同源合格候选中的高优先级潜在线性自由酸候选**：**{summary_stats['passing_high_priority_linear_count']}** 条",
        f"- **在同源合格候选中的二硫键/环肽/酰胺化候选**：{summary_stats['passing_disulfide_or_cyclic_count']} 条",
        "",
        "## 二、高优先级潜在天然线性多肽列表 (Top Candidates)",
        "",
    ]

    for idx, row in high_priority_linear.head(15).reset_index(drop=True).iterrows():
        report_lines.extend([
            f"### {idx+1}. {row['dramp_id']} - {row['name']}",
            f"- **序列**：`{row['sequence']}` (长度: {row['length']})",
            f"- **与 417 开发集最大相似度**：`{row['max_identity_to_dev']:.4f}` (最接近开发记录: `{row['nearest_dev_record']}`)",
            f"- **端点与拓扑**：N端=`{row['n_term_raw']}`，C端=`{row['c_term_raw']}`，拓扑=`{row['topology']}`，Cys数=`{row['cys_count']}`",
            f"- **PMID / 参考文献**：`{row['pubmed_id']}` | {row['reference']}",
            f"- **E. coli 活性文本**：{row['ecoli_activity_text'][:120]}...",
            f"- **溶血活性文本**：{row['hemolytic_activity_text'][:120]}...",
            "",
        ])

    (output_dir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Screening complete. Summary: {summary_stats}")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dramp",
        type=Path,
        default=ROOT / "02_code/data/sources/dramp_mic_screen_20261001/raw/Antibacterial_amps.xlsx",
    )
    parser.add_argument(
        "--development",
        type=Path,
        default=ROOT / "02_code/data/sources/combined_v3_evidence_clean_20261001/records.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "03_experiments/audits/dramp_dual_task_screen_20261003_v1",
    )
    parser.add_argument("--cutoff", type=float, default=0.40)
    args = parser.parse_args()
    run_dual_task_screen(args.dramp, args.development, args.output, args.cutoff)
