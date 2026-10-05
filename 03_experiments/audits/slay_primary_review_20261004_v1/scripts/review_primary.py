"""Bounded SLAY endpoint review. This entry never derives labels or releases data."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from acquire_public_sources import BASE, ROOT, PREVIOUS, PREVIOUS_SHA, sha

DOI = "10.1016/j.cell.2017.12.009"
URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC5786472/"
INVENTORY = PREVIOUS.parent / "acquisition/candidate_inventory.csv"


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with path.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    out = parser.parse_args().output.resolve()
    if out.exists():
        raise FileExistsError(out)
    inputs, protected = {}, {}
    if sha(PREVIOUS / "manifest.json") != PREVIOUS_SHA:
        raise ValueError("Previous review manifest changed")
    # Protect previous review, acquisition and source bindings without rewriting them.
    for folder in [PREVIOUS, PREVIOUS.parent / "acquisition",
                   ROOT / "03_experiments/audits/gemini_hc50_external_review_20261004_v2"]:
        manifest_name = "input_manifest.json" if folder.name.endswith("review_20261004_v2") else "manifest.json"
        manifest = folder / manifest_name
        data = json.loads(manifest.read_text(encoding="utf-8"))
        protected[manifest.relative_to(ROOT).as_posix()] = sha(manifest)
        for key in ["protected", "files", "protected_v1"]:
            protected.update(data.get(key, {}))
        for name, expected in data.get("outputs", {}).items():
            protected[(folder / name).relative_to(ROOT).as_posix()] = expected
    # Acquisition manifests bind each response (including non-PDF challenge pages).
    for name in ["acquisition", "alternate_acquisition", "figure_acquisition"]:
        folder = BASE / name
        manifest = folder / ("manifest_v2.json" if name == "figure_acquisition" else "manifest.json")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        inputs[manifest.relative_to(ROOT).as_posix()] = sha(manifest)
        if "previous_manifest_sha256" in data:
            inputs[(folder / "manifest.json").relative_to(ROOT).as_posix()] = data["previous_manifest_sha256"]
        for filename, expected in data["outputs"].items():
            inputs[(folder / filename).relative_to(ROOT).as_posix()] = expected
    for name, expected in {**inputs, **protected}.items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"Changed input: {name}")
    original = BASE / "acquisition/raw/pmc_article.html"
    soup = BeautifulSoup(original.read_bytes(), "html.parser")
    table = soup.find(id="T2")
    if "MBC (μM)" not in table.get_text(" ", strip=True):
        raise ValueError("Primary table is not the expected MBC table")
    primary = {}
    for row in table.find_all("tr"):
        cells = [cell.get_text("", strip=True) for cell in row.find_all("td")]
        if len(cells) == 11:
            primary[cells[0]] = cells
    # Independently parse BioC's embedded XML table, rather than its flattened text.
    bioc = ET.parse(BASE / "acquisition/raw/bioc_article.xml").getroot()
    bioc_table = next(p.find("infon[@key='xml']").text for p in bioc.iter("passage")
                      if p.findtext("infon[@key='id']") == "T2" and p.findtext("infon[@key='type']") == "table")
    xml_rows = {}
    for row in ET.fromstring(bioc_table).findall("./tbody/tr"):
        cells = ["".join(cell.itertext()).strip() for cell in row.findall("td")]
        xml_rows[cells[0]] = cells
    sections = {sid: soup.find(id=sid).get_text(" ", strip=True) for sid in ["S10", "S11", "S30", "S32", "F5", "T2"]}
    required = {"S10": ["Supplementary Table 2", "P3–P22 did not show activity", "data not shown"],
                "S11": ["all well under 20% hemolysis"], "F5": ["50 μM"],
                "S32": ["human red blood", "0.5 mL", "0.4 mL", "540 nm"],
                "S30": [">90% purity", "Genscript", "Mueller-Hinton"]}
    for sid, phrases in required.items():
        if not all(phrase in sections[sid] for phrase in phrases):
            raise ValueError(f"Primary-source anchor changed: {sid}")
    inventory = {r["candidate_id"]: r for r in read_csv(INVENTORY)}
    previous_rows = read_csv(PREVIOUS / "candidate_decisions.csv")
    subset = [row for row in previous_rows if row["pmid"] == "29307492"]
    if len(subset) != 14 or len({r["candidate_id"] for r in subset}) != 14:
        raise ValueError("Expected fourteen unique fixed candidates")
    observations, identities, decisions = [], [], []
    source_path = original.relative_to(ROOT).as_posix()
    for candidate in subset:
        cid, name = candidate["candidate_id"], candidate["name"].removeprefix("SLAY-")
        cells = primary[name]
        if cells != xml_rows[name]:
            raise ValueError(f"HTML/BioC table disagreement: {name}")
        if cells[1] != inventory[cid]["sequence"]:
            raise ValueError(f"Original/inventory sequence conflict: {cid}")
        identities.append({"candidate_id": cid, "peptide": name, "sequence": cells[1],
                           "sequence_matches_inventory": True, "source_location": f"Table 2, row {name}, Sequence",
                           "source_file": source_path, "source_sha256": sha(original),
                           "synthetic_supplier": "GenScript", "reported_purity": ">90%",
                           "terminal_chemistry": "not_explicitly_confirmed",
                           "stereochemistry": "not_explicitly_confirmed",
                           "disulfide_status": "not_inferred_from_cysteine_count",
                           "full_molecular_identity_released": False})
        for index, target in [(7, "E. coli W3110"), (10, "NDM E. coli (paper designation)")]:
            raw = cells[index]
            operator = ">" if raw.startswith(">") else "<=" if raw.startswith("≤") else "="
            observations.append({"candidate_id": cid, "peptide": name, "endpoint": "MBC",
                                 "target": target, "raw_value": raw, "operator": operator,
                                 "reported_value": raw.lstrip(">≤"), "unit": "µM",
                                 "source_location": f"Table 2, row {name}, {target}",
                                 "source_file": source_path, "source_sha256": sha(original),
                                 "doi": DOI, "pmid": "29307492", "pmcid": "PMC5786472",
                                 "conditions": "Tris-based assay medium; methods S30; representative of three independent experiments",
                                 "formal_mic_label": "", "formal_hc50_label": "", "formal_release": False})
        row = dict(candidate)
        row.update(doi=DOI, screen_status="primary_mbc_and_single_point_hemolysis_reviewed",
                   review_scope="agent_original_source_review; figure visually inspected; not independent human review",
                   source_location=f"Table 2 row {name}; S10; Figure 5C; S30; S32",
                   decision="current_source_insufficient_for_dual_release",
                   reason="主表为MBC；人红细胞图为50 µM名义单点溶血，未提供数值HC50；S2/S3未取得，数值MIC及完整分子形式仍待核实。此结论仅约束已审查来源，不断言其他研究没有HC50。",
                   formal_release="False", sequence_and_form_release="False",
                   study_independence="one_measurement_study; not yet audited against development study aliases",
                   cross_cohort_audit="not_released; verified sequence alone does not imply external eligibility")
        decisions.append(row)
    updated = {row["candidate_id"]: row for row in decisions}
    merged = [updated.get(row["candidate_id"], row) for row in previous_rows]
    prior_summary = json.loads((PREVIOUS / "summary.json").read_text(encoding="utf-8"))
    summary = {"generated_at": datetime.now(timezone.utc).isoformat(), "data_version": BASE.name,
               "protocol_id": "protocol-amd-02", "homology_boundary": ">=0.40 unchanged",
               "review_mode": "agent_original_source_review", "independent_human_review": False,
               "fixed_batch_candidates": 14, "sequence_matches": len(identities),
               "new_measurement_studies_reviewed": 1, "mbc_observations": len(observations),
               "numeric_mic_observations_released": 0, "new_numeric_human_hc50_observations": 0,
               "formal_external_released": 0, "formal_scientific_status": "blocked",
               "model_fit_calls": 0, "training_state_changed": False,
               "supplement_s2_s3_status": "not_acquired; PMC non-PDF challenge; alternate public routes 403",
               "merged_candidate_records": len(merged),
               "merged_decision_counts": dict(Counter(row["decision"] for row in merged)),
               "merged_candidates_endpoint_screened": sum(row["screen_status"] != "original_not_acquired" for row in merged),
               "remaining_original_access_gaps": sum(row["screen_status"] == "original_not_acquired" for row in merged),
               "prior_explicit_human_hc50_observations": prior_summary["explicit_human_hc50_observations"]}
    # The individual % bars were inspected for identity/endpoint, never digitized.
    hemolysis = [{"candidate_id": row["candidate_id"], "peptide": row["name"].removeprefix("SLAY-"),
                  "endpoint": "single_point_percent_hemolysis", "target": "human red blood cells",
                  "figure_location": "Figure 5C", "nominal_concentration_raw": "50 µM (caption)",
                  "percent_value": "", "hc50_value": "", "formal_hc50_label": "",
                  "group_statement": "P3–P18 well under 20%; no individual numerical extraction" if row["name"] != "SLAY-P2" else "not covered by P3–P18 statement; no numerical extraction",
                  "concentration_ambiguity": "Caption states 50 µM; methods describe 50 µM peptide solution before 0.5 mL + 0.4 mL mixing; final concentration not resolved",
                  "source_file": source_path, "source_sha256": sha(original), "formal_release": False}
                 for row in subset]
    mic = [{"candidate_id": row["candidate_id"], "peptide": row["name"].removeprefix("SLAY-"),
            "endpoint": "MIC", "target": "strain-specific values pending Table S2",
            "raw_value": "", "unit": "", "formal_mic_label": "", "formal_release": False,
            "evidence": "P2 qualitatively active in Mueller-Hinton; numeric value pending S2" if row["name"] == "SLAY-P2" else "P3–P22 inactive in Mueller-Hinton, data not shown; not a numeric censored MIC",
            "source_location": "S10, SLAY Hits are Active in Synthetic Form",
            "source_file": source_path, "source_sha256": sha(original)} for row in subset]
    out.mkdir(parents=True, exist_ok=False)
    write_csv(out / "sequence_identity_review.csv", identities)
    write_csv(out / "mbc_observations.csv", observations)
    write_csv(out / "mic_endpoint_gaps.csv", mic)
    write_csv(out / "single_point_hemolysis_review.csv", hemolysis)
    write_csv(out / "candidate_decisions.csv", decisions)
    write_csv(out / "merged_candidate_decisions.csv", merged)
    write_json(out / "source_regions.json", {"source_file": source_path, "source_sha256": sha(original), "sections": sections,
                                             "figure_inspection": "Panel C visually verified all fourteen peptide labels, percent hemolysis axis; bars not digitized",
                                             "license": "not verified; local evidence review only; no redistribution authorization asserted"})
    write_json(out / "summary.json", summary)
    report = f"""# SLAY 原始证据审查\n\n生成时间：{summary['generated_at']}。数据版本：`{BASE.name}`；协议：`protocol-amd-02`（未修改）。模式：代理原文及图像复核，不声称独立人工评审。\n\n## 结论\n\n本批固定 14 条候选全部与[原文 Table 2]({URL}#T2)序列一致；原文 HTML 与官方 BioC 嵌入表逐格一致。存档 28 条 *E. coli* MBC 表述（每分子 W3110 和 NDM 两列），均不转换为 MIC。14 条属于同一测量研究，尚未通过开发集研究别名独立性审计。\n\n[Figure 5C 与人红细胞方法]({URL}#F5)只有名义 50 µM 单点溶血；无数值 HC50。图像已逐项核对肽名，没有读图估算数值或反推 HC50。P3–P18 组低于 20% 的正文陈述不扩展到 P2。图注浓度与方法混合前浓度存在歧义，已保留；不擅自计算并替换。\n\nTable S2 才是数值 MIC 来源。本批公共渠道未取得 S2/S3；PMC PDF 请求返回下载挑战页，Europe PMC PDF 和出版方页面返回 403。仅是这些渠道的访问结果，不代表材料不存在。P2 的定性活性不补写数值；另外 13 条在 Mueller-Hinton 中“无活性、数据未展示”的陈述不改写为数值下界或阴性标签。\n\n完整末端、立体化学、二硫键状态未明确核实；GenScript 和 >90% 纯度不能替代分子身份。许可未确认，仅本地核查，不声明可再分发。\n\n## 本批决定与累计跟进\n\n- 14 条：`current_source_insufficient_for_dual_release`；缺 HC50、数值 MIC 和完整分子身份，均未释放。结论只针对已审查来源。\n- 既定 78 条清单累计筛查 {summary['merged_candidates_endpoint_screened']} 条；仍有 {summary['remaining_original_access_gaps']} 条当前渠道缺原文。\n- 累计分类：{json.dumps(summary['merged_decision_counts'], ensure_ascii=False)}。上批已找到的 8 条人 HC50 记录保持原结论，未新增 HC50。\n- 正式外部新增 0；原双任务 `blocked`；MIC 探索训练及其状态原样保留，没有训练新模型。\n\n## 产物与后续\n\n逐条决定见 `candidate_decisions.csv`；累计清单见 `merged_candidate_decisions.csv`；分子核对、MBC、MIC缺口及单点溶血分别存表。原文、来源响应与摘要保存在上一层的三个 acquisition 目录。`verification.json` 记录覆盖、逐值检查及保护文件摘要核查。\n\n继续优先审查累计清单中的真实人红细胞剂量曲线和未取得原文的研究。SLAY 的 S2/S3 保留补充获取任务；即使取得 MIC，仍需另有可核实 HC50、完整分子身份、研究与全员同源隔离，不能自动准入。\n\n复跑（替换为不存在的目录）：\n\n```powershell\npython 03_experiments/audits/slay_primary_review_20261004_v1/scripts/review_primary.py --output 03_experiments/audits/slay_primary_review_20261004_v1/review_my_run\n```\n"""
    with (out / "report.md").open("x", encoding="utf-8") as stream:
        stream.write(report)
    inputs[Path(__file__).relative_to(ROOT).as_posix()] = sha(Path(__file__))
    write_json(out / "manifest.json", {"generated_at": summary["generated_at"], "inputs": inputs,
               "protected": protected, "outputs": {p.name: sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
