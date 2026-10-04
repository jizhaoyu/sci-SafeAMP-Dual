"""Record discovery leads without inferring experimental labels from record IDs."""
import argparse
from pathlib import Path
import pandas as pd
from research_utils import ROOT, sha256, utc_now, write_json

def curate_dual_task_evidence(primary_audit_csv: Path, development_csv: Path, output_dir: Path) -> dict:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite external review: {output_dir}")
    df = pd.read_csv(primary_audit_csv, keep_default_na=False)
    rows = []
    for row in df.to_dict("records"):
        rows.append({"dramp_id": row["dramp_id"], "name": row["name"], "sequence": row["sequence"],
                     "pubmed_id": str(row["pubmed_id"]), "max_identity_to_dev": row["max_identity_to_dev"],
                     "nearest_dev_record": row["nearest_dev_record"],
                     "expert_status": "candidate_pending_primary_measurement_evidence",
                     "mic_ug_ml": None, "hc50_ug_ml": None, "amp_label": None, "hemo_label": None,
                     "database_ecoli_text": row.get("ecoli_activity_text", ""),
                     "database_hemo_text": row.get("hemolytic_activity_text", ""),
                     "evidence_note": "Database text is a discovery lead. Original molecular-form and assay evidence are not bound; no quantitative endpoint or binary label is approved."})
    output_dir.mkdir(parents=True, exist_ok=False)
    candidates = pd.DataFrame(rows)
    candidates.to_csv(output_dir / "curated_candidate_evaluations.csv", index=False)
    candidates.iloc[:0].to_csv(output_dir / "verified_eligible_candidates.csv", index=False)
    result = {"status": "external_primary_evidence_review_blocked", "generated_at": utc_now(),
              "audit_protocol_id": "protocol-amd-03", "formal_protocol_id": "protocol-amd-02",
              "total_audited_candidates": len(rows), "eligible_verified_count": 0,
              "records_released_for_training": 0, "formal_status": "blocked",
              "primary_audit_input_sha256": sha256(primary_audit_csv),
              "development_records_sha256": sha256(development_csv),
              "inputs": {str(p.resolve().relative_to(ROOT)): sha256(p) for p in (primary_audit_csv, development_csv)},
              "script_sha256": sha256(Path(__file__)), "outputs": {}}
    (output_dir / "report.md").write_text(
        "# 双任务外部候选证据整改\n\n"
        f"生成时间：{result['generated_at']}；审查协议：protocol-amd-03；正式协议：protocol-amd-02。\n\n"
        f"{len(rows)} 条记录保持候选；完整原测定资格批准为 0。数据库文本和旧审查未绑定原图表、受测分子形式、单位与条件。"
        "删除按 DRAMP ID 自动生成实测值、二值标签及黄金候选结论的分支。旧报告保留为资格声明被后续审查撤销的历史材料。\n\n"
        "序列隔离检查通过不能代替原始测定核实；不生成正式外部评估队列，正式研究继续 blocked。\n", encoding="utf-8")
    result["outputs"] = {p.name: sha256(p) for p in output_dir.iterdir() if p.is_file()}
    write_json(output_dir / "curation_manifest.json", result)
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-audit", type=Path, default=ROOT / "03_experiments/audits/dramp_dual_task_primary_audit_20261003_v1/candidate_primary_audit.csv")
    parser.add_argument("--development", type=Path, default=ROOT / "02_code/data/sources/combined_v3_evidence_clean_20261001/records.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "03_experiments/audits/dual_task_external_curation_20261003_v2")
    args = parser.parse_args()
    result = curate_dual_task_evidence(args.primary_audit, args.development, args.output)
    print({k: result[k] for k in ("status", "total_audited_candidates", "eligible_verified_count")})
