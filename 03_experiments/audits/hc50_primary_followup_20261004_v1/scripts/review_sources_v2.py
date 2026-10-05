"""Reproduce a bounded agent review of archived originals; never release training data.

Curated decisions are checked against source regions, not inferred from keywords.
Figure-only sequences remain unverified. A machine hash check is not an independent
human review. All outputs are exclusive and the existing research state is protected.
"""
import argparse
import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
ACQUISITION_SHA = "b84791fc994078261fc50036176869ba39051e77c44e6f6e02e2946c518e7435"
VISUAL_PAGE_SHA = {
    2: "5e8b09a757e5ac371b647e26310364d758ba0d9e630c0dae566ed02b0abf24a9",
    3: "8f531c8a03ae8e4c293e31788a2ca54e69f289f158bd562f1c612d9bc2cd0ebb",
}

# Scope, location and unresolved issue, not a formal molecule approval.
SCREENS = {
    "27542832": ("animal_rbc_only", "Table 1; Table 4; Hemolysis methods; Fig. 8a", "Sheep RBC；单点百分比不能替换人 HC50。E. coli MIC >250 与缓冲液 EC50 是不同端点。"),
    "27917162": ("human_curve_without_numeric_hc50", "Tables 1, 3; Hemolysis assay; Fig. 3", "人红细胞曲线有溶血；未从图估计 HC50。Table 3 是真菌 MIC，不能转为 E. coli MIC。"),
    "28661457": ("endpoint_and_species_conflict", "Tables 2–4; Hemolysis methods", "Table 4 为 HC10 和单点百分比，非 HC50；表注写 human，但方法及结果写 murine，物种冲突未解决。"),
    "30658410": ("single_concentration_hemolysis", "Table 2; Table 3; section 4.5", "Table 3 是 10/50 µM 溶血百分比，没有 HC50；测定方法另引文献，RBC 物种尚未确认。"),
    "30872680": ("endpoint_mismatch", "Table 1; paragraphs Par34, Par37, Par38; Fig. 1", "表中 MIC 实为 MIC80%；人溶血为百分比，不能生成 HC50。AgNP 缀合物不能作为游离肽。"),
    "30486233": ("explicit_human_hc50", "Table 1; section 2.5; section 4.5", "PM III 原文 HC50 已确认，但有二硫键；不满足当前未修饰线性肽边界。"),
    "31234579": ("explicit_human_hc50", "Table 3 AR-F column; synthesis/oxidation methods", "AR-F HC50 已确认；二硫键结构不准入。图中完整序列仍需复核，不能直接确认库存序列。"),
    "32153522": ("explicit_human_hc50", "Table 2 cd4(Q5K,D9K); sections S2.SS1 and S4.SS12", "cd4(Q5K,D9K) HC50 已确认；头尾环化不准入。Fig. 1 完整序列仍需复核。"),
    "32291307": ("animal_rbc_only", "section s4.13; Fig. 4B", "方法使用 mouse RBC；不能从小鼠红细胞曲线产生人 HC50。"),
    "35323465": ("approximate_curve_and_condition_conflict", "Fig. 2A; section 3.3; results hemolysis paragraph", "CT7 在 128 µM 接近 50% 非精确 HC50；结果/图注 1.5 h 与方法 120 min 不一致。序列图待核实。"),
    "36442155": ("explicit_human_hc50", "Table 1; sections sec4.3.1 and sec4.4", "原文测量代码和 HC50 可追溯；环化肽不准入。完整结构不能仅从 R/W 数量构成推断。"),
    "41735465": ("human_rbc_ic50_bound", "Table 1; sections Sec5, Sec14; Supplementary Table S2 needed", "人 RBC 行 IC50 >32 µM 是溶血 50% 的下界，不能当成 MRC5 IC50；未做质量换算。两条完整序列和 NHill 单独行需要补充表。"),
    "21696142": ("explicit_human_hc50", "PDF pages 2–3 Tables 1–2, peptide 3; page 5 methods", "ECP(1–19) 是表 1 的 peptide 3（正文编号存在交换）；HC50 已确认。Rink-amide 合成，不准入游离末端队列。"),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(element):
    return " ".join("".join(element.itertext()).split())


def verify_mapping(base, mapping):
    for relative, expected in mapping.items():
        path = (base / relative).resolve()
        if not path.is_relative_to(base.resolve()) or sha(path) != expected:
            raise ValueError(f"Hash/path mismatch: {relative}")


def csv_write(path, rows):
    if not rows:
        raise ValueError(f"Empty output: {path.name}")
    with path.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build(out):
    if out.exists():
        raise FileExistsError(out)
    if out.resolve() == BASE or out.resolve().is_relative_to(BASE / "acquisition"):
        raise ValueError("Output cannot replace source material")
    acquisition = BASE / "acquisition"
    if sha(acquisition / "manifest.json") != ACQUISITION_SHA:
        raise ValueError("Acquisition manifest binding mismatch")
    manifest = json.loads((acquisition / "manifest.json").read_text(encoding="utf-8"))
    verify_mapping(acquisition, manifest["outputs"])
    verify_mapping(ROOT, manifest["protected"])
    verify_mapping(ROOT, manifest["scripts"])
    additional = json.loads((BASE / "additional_metadata/manifest.json").read_text(encoding="utf-8"))
    verify_mapping(BASE / "additional_metadata", {row["file"]: row["sha256"] for row in additional["requests"] if row.get("file")})
    with (acquisition / "candidate_inventory.csv").open(encoding="utf-8-sig") as stream:
        candidates = list(csv.DictReader(stream))
    ids = {row["candidate_id"] for row in candidates}
    if len(candidates) != 78 or len(ids) != 78:
        raise ValueError("Candidate coverage mismatch")
    sources = {p.stem.split("_")[1]: ET.parse(p).getroot() for p in (acquisition / "raw").glob("*.xml")}
    if len(sources) != 12:
        raise ValueError("Expected twelve acquired XML originals")
    metadata = json.loads((acquisition / "raw/europepmc_metadata.json").read_text(encoding="utf-8"))
    articles = {item["id"]: item for item in metadata["resultList"]["result"]}
    evidence = []

    def region(pmid, selector):
        node = sources[pmid].find(selector)
        if node is None:
            raise ValueError(f"Missing evidence region {pmid}: {selector}")
        text = compact(node)
        evidence.append({"pmid": pmid, "selector": selector, "text": text,
                         "source_sha256": sha(acquisition / f"raw/pmid_{pmid}.xml")})
        return node, text

    # Archive all body/table blocks of screened papers as location-addressed excerpts.
    # References are not used as measurements from the current article.
    for pmid, source in sources.items():
        region(pmid, "./body")
        for table in source.findall(".//table-wrap"):
            region(pmid, f".//table-wrap[@id='{table.attrib['id']}']")

    hc50 = []
    paired = []
    def observation(candidate, pmid, molecule, value, unit, location, conditions, form, binding):
        if candidate not in ids:
            raise ValueError("Observation outside fixed candidate scope")
        filename = "pmid_21696142_author_repository.pdf" if pmid == "21696142" else f"pmid_{pmid}.xml"
        hc50.append({"candidate_id": candidate, "pmid": pmid, "doi": articles[pmid].get("doi", ""),
                     "measured_molecule": molecule, "endpoint": "HC50", "rbc_species": "human",
                     "value_original": value, "unit_original": unit, "location": location,
                     "conditions_reported": conditions, "molecular_form": form,
                     "full_sequence_binding": binding, "source_file": f"acquisition/raw/{filename}",
                     "source_sha256": sha(acquisition / "raw" / filename),
                     "mass_conversion_performed": False, "formal_label": "not_released",
                     "external_admission": "excluded_by_known_molecular_form"})

    _, text = region("30486233", ".//sec[@id='sec2dot5-marinedrugs-16-00466']")
    if "46 µM" not in text:
        raise ValueError("PM III HC50 not reproduced")
    _, method = region("30486233", ".//sec[@id='sec4dot5-marinedrugs-16-00466']")
    if "fresh human red blood cells" not in method:
        raise ValueError("PM III species not reproduced")
    observation("DBAASP_12233", "30486233", "PM III", "46", "µM", "section 2.5; Fig. 2; section 4.5",
                "37°C; 1.5 h; PBS; final RBC 4%; 405 nm", "disulfide_bonded", "Table 1 sequence directly reviewed")

    table, _ = region("31234579", ".//table-wrap[@id='marinedrugs-17-00376-t003']")
    row = next(r for r in table.findall(".//tbody/tr") if compact(r[0]).startswith("HC50"))
    if compact(row[8]) != "60.5":
        raise ValueError("AR-F HC50 column mismatch")
    observation("DBAASP_13515", "31234579", "AR-F", "60.5", "µM", "Table 3 HC50 row, AR-F column; hemolysis methods",
                "37°C; 30 min; PBS; RBC suspension 2.5%; 540 nm", "disulfide_bonded", "Fig. 1 exact sequence pending")

    table, _ = region("32153522", ".//table-wrap[@id='T2']")
    row = next(r for r in table.findall(".//tbody/tr") if compact(r[0]) == "cd4(Q5K,D9K)")
    if compact(row[5]) != "10":
        raise ValueError("KR12 HC50 column mismatch")
    observation("DBAASP_15043", "32153522", "cd4(Q5K,D9K)", "10", "µM", "Table 2 HC50 column; section S4.SS12",
                "human type A RBC; 37°C; 1 h; PBS; 0.25% RBC suspension before mixing; 405 nm",
                "head_to_tail_cyclic", "Fig. 1 exact sequence pending")

    table, _ = region("36442155", ".//table-wrap[@id='tbl1']")
    for candidate, code, name, value, mic in [
        ("DBAASP_20562", "3e", "[R3W7]", "60", "256"),
        ("DBAASP_20565", "4c", "[R4W6]", "75", "128"),
        ("DBAASP_20571", "7a", "[R7W4]", "190", "32"),
        ("DBAASP_20579", "6a", "[R6W4]", "265", "32"),
    ]:
        row = next(r for r in table.findall(".//tbody/tr") if compact(r[0]) == code)
        if compact(row[1]) != name or compact(row[6]) != value or compact(row[5]) != mic:
            raise ValueError(f"Cyclic compound row mismatch: {code}")
        observation(candidate, "36442155", f"{code} {name}", value, "µg/mL", f"Table 1 row {code}, HC50 column; section 4.4",
                    "37°C; 2 h; PBS pH 7.4; 4% RBC suspension mixed 1:1 (final 2%); 567 nm",
                    "cyclic", "original compound code confirmed; exact structural sequence pending")
        paired.append({"candidate_id": candidate, "pmid": "36442155", "endpoint": "MIC",
                       "target": "E. coli ATCC 25922", "value_original": mic, "unit_original": "µg/mL",
                       "location": f"Table 1 row {code}, E. coli column; section 4.3.1",
                       "source_sha256": sha(acquisition / "raw/pmid_36442155.xml"),
                       "formal_label": "not_released"})

    # PDF tables include embedded image text; page images were actually inspected.
    # This is curated visual review, not automated OCR nor independent human review.
    for page, expected in VISUAL_PAGE_SHA.items():
        if sha(BASE / "inspection" / f"ecp_page_{page}.png") != expected:
            raise ValueError("Visually reviewed PDF page changed")
    observation("DBAASP_6545", "21696142", "ECP(1–19), peptide 3 in Table 1", "11.2 ± 0.1", "µM",
                "PDF page 3 Table 2 row 3; page 2 Table 1 row 3; page 5 methods",
                "37°C; 4 h; PBS pH 7.4; 2×10^7 RBC/mL; 570 nm; sigmoid fitting",
                "C_terminal_amide", "Table 1 image sequence directly reviewed")
    paired.append({"candidate_id": "DBAASP_6545", "pmid": "21696142", "endpoint": "reported_MIC100",
                   "target": "E. coli BL2 (as printed)", "value_original": ">10", "unit_original": "µM",
                   "location": "PDF page 3 Table 2 row 3; page 5 MIC determination; 4 h exposure and overnight plating",
                   "source_sha256": sha(acquisition / "raw/pmid_21696142_author_repository.pdf"),
                   "formal_label": "not_released_assay_definition_requires_review"})

    decisions = []
    gaps = []
    observed = {r["candidate_id"] for r in hc50}
    for candidate in candidates:
        pmid = candidate["pmid"]
        screen = SCREENS.get(pmid)
        decision = "excluded_by_known_molecular_form" if candidate["candidate_id"] in observed else "pending"
        reason = screen[2] if screen else "当前获取渠道未取得可审查原文；不声称所有公开渠道均不可获得。"
        if candidate["candidate_id"] == "DBAASP_25709":
            reason += " NHill_AD_C49215 不在主表逐行列出的候选中，不能借用 Hill_BB_C7985 的测定值。"
        if candidate["candidate_id"] == "HIST_DRAMP20968":
            reason = "PubMed 原始摘要明确提到 HC50 300 µg/mL，纠正旧‘未报告’结论；仍缺全文分子形式和方法复核，摘要不作为释放依据。"
        if not pmid:
            reason = "通过原出版者页面核对 DOI 10.1007/s00049-019-00287-z；尚缺原文测定行及分子形式，PMID 不补猜。"
        decisions.append({"candidate_id": candidate["candidate_id"], "name": candidate["name"], "pmid": pmid,
                          "doi": articles.get(pmid, {}).get("doi", "10.1007/s00049-019-00287-z" if not pmid else ""),
                          "screen_status": screen[0] if screen else "original_not_acquired",
                          "review_scope": "agent_primary_endpoint_screen" if screen else "metadata_and_access_only",
                          "source_location": screen[1] if screen else "acquisition/source_acquisition.csv",
                          "decision": decision, "reason": reason, "formal_release": False,
                          "sequence_and_form_release": False, "study_independence": "not_released",
                          "cross_cohort_audit": "not_released; v2 unverified inventory comparisons are provisional"})
        if screen is None:
            gaps.append({"candidate_id": candidate["candidate_id"], "name": candidate["name"], "pmid": pmid,
                         "doi": decisions[-1]["doi"], "acquisition_status": candidate["full_text_acquisition"],
                         "missing": "original assay table, molecule identity, endpoint, conditions and source verification",
                         "next_action": "public publisher/author repository or authorized original files; retain pending"})
    counts = Counter(row["decision"] for row in decisions)
    summary = {"generated_at": datetime.now(timezone.utc).isoformat(), "review_mode": "agent_original_source_review",
               "independent_human_review": False, "candidate_records": len(decisions),
               "source_groups": len({r["pmid"] for r in candidates}), "metadata_pmids": len(articles),
               "original_sources_acquired": 13, "candidates_endpoint_screened": sum(bool(SCREENS.get(r["pmid"])) for r in candidates),
               "candidate_access_gaps": len(gaps), "explicit_human_hc50_observations": len(hc50),
               "decision_counts": dict(counts), "formal_external_released": 0,
               "formal_scientific_status": "blocked", "training_state_changed": False,
               "new_models_trained": 0, "protocol_id": "protocol-amd-02 (unchanged)",
               "data_version": BASE.name, "review_output_version": out.name, "sequence_homology_threshold": ">=0.40 (unchanged)",
               "acquisition_manifest_sha256": ACQUISITION_SHA}
    if summary["candidates_endpoint_screened"] != 20 or len(hc50) != 8:
        raise ValueError("Review coverage mismatch")
    verify_mapping(ROOT, manifest["protected"])
    out.mkdir(parents=True, exist_ok=False)
    csv_write(out / "candidate_decisions.csv", decisions)
    csv_write(out / "original_human_hc50_observations.csv", hc50)
    csv_write(out / "paired_original_mic_observations.csv", paired)
    csv_write(out / "source_access_gaps.csv", gaps)
    with (out / "source_region_excerpts.json").open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, ensure_ascii=False, indent=2)
    with (out / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
    report = ["# HC50 原文跟进：第一批\n", f"生成时间：{summary['generated_at']}；数据版本：{BASE.name}；协议：protocol-amd-02（未修改）。\n",
              "## 本批结果\n", "- 78 条固定候选，对应 41 个已核对 PMID 和 1 个无 PMID 来源；归档全部 41 个 PubMed 元数据响应。",
              "- 获取 12 篇 XML 原文和 1 篇作者机构 PDF，共对 20 条候选完成端点筛查；58 条尚缺本批可审查全文。",
              "- 原文找到 8 条明确的人红细胞 HC50 测定记录，来自 5 篇论文。这是原始测定观察数量，不是正式合格样本数量。",
              "- 8 条均有已知环化、二硫键或酰胺化形式，不满足当前外部队列分子边界；部分完整序列图还待复核。",
              "- 逐记录决定：8 条因已知分子形式排除于当前正式外部队列，70 条 pending；其中 58 条为获取缺口，12 条为已取得原文但未满足完整证据门禁。",
              "- 新释放外部样本 0，新训练 0。原双任务仍 blocked；既有 MIC 探索性训练状态未改动。\n",
              "## 人红细胞 HC50 原始记录\n", "| 候选 | 原测定对象 | HC50 原值 | 原文位置 | 当前边界 |", "|---|---|---|---|---|"]
    for row in hc50:
        report.append(f"| {row['candidate_id']} | {row['measured_molecule']} | {row['value_original']} {row['unit_original']} | PMID {row['pmid']}, {row['location']} | {row['molecular_form']} |")
    report += ["\n## 必须保留的冲突与缺口\n", "- AI-hemocidin 2：表注 human 与方法/结果 murine 冲突；HC10 和单点溶血不是 HC50。",
               "- A1P 和 AMPR-11：原文分别使用 sheep 和 mouse RBC。ToAP2 的人溶血曲线不从图估值；同篇真菌 MIC 不移作 E. coli MIC。",
               "- AY1C/CAY1 及 AgNP 缀合物：Table 1 使用 MIC80% 端点，现行完全抑制规则不兼容；百分比溶血不能转为 HC50。",
               "- CT7：128 µM 近 50% 未写为精确 HC50；1.5 h 图注与 120 min 方法冲突。",
               "- Hermetia：人 RBC 行 IC50 是明确的溶血 50% 端点，可以作为下界线索；NHill 单独行/完整序列待 Supplementary Table S2，不借用另一分子的数值。",
               "- ECP(1–19)：按 Table 1 序列匹配 Table 2 row 3，保留正文编号交换；PDF 方法用 Rink-amide，不遗漏酰胺化。",
               "- Catesbeianin-1：原始 PubMed 摘要明确写 HC50 300 µg/mL，旧缺失声明被推翻；仍待全文核对，不将摘要直接释放。",
               "- Brevinin-2-Ia：出版者核对 DOI 10.1007/s00049-019-00287-z；PMID 不猜填，测定行继续 pending。",
               "- SLAY：Europe PMC 全文渠道失败，PMC 网页返回 challenge；这仅说明本次获取渠道未成功，不说明世界上不存在全文。\n",
               "## 后续顺序\n", "1. 优先取得 SLAY 的原文及补充表（14 条）、HD5 六条的原始测量表、鳟鱼五条的原始测量表。",
               "2. 对 Catesbeianin-1、Brevinin-2-Ia 获取合法全文，核对分子形式、实验对象和数值。",
               "3. 对已取得全文的 12 条 pending 按各自缺口补图、补表、核对端点；冲突未解除继续 pending。",
               "4. 只有完整分子与测定证据复核后才能重建合格队列；随后重跑全员序列、论文别名和历史暴露隔离。\n",
               "## 复核与复跑\n", "本批是代理原文复核，不声称独立人工评审；摘要仅用于检索，未产生任何训练标签。",
               "`scripts/review_sources_v2.py --output <不存在的新目录>` 在运行前核对绑定摘要和覆盖；输出已存在时拒绝覆盖。",
               "汇总来自 summary.json。原始文件、URL、获取时间、许可和失败记录见 acquisition/source_acquisition.csv；完整来源片段见 source_region_excerpts.json。",
               "许可说明：Europe PMC 返回的许可证保留在获取表；作者机构 PDF 未核实开放再分发许可，不作为交付包再分发。",
               "固定 0.40 全员门禁、原协议、历史数据、模型及机器状态保持原样；本轮未把库存相似度结果升级成正式零泄漏结论。\n"]
    with (out / "report.md").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(report))
    bindings = {"acquisition/manifest.json": ACQUISITION_SHA,
                "scripts/review_sources_v2.py": sha(Path(__file__)),
                "metadata_review_notes.json": sha(BASE / "metadata_review_notes.json"),
                "additional_metadata/manifest.json": sha(BASE / "additional_metadata/manifest.json")}
    for path in (BASE / "inspection").glob("*.png"):
        bindings[path.relative_to(BASE).as_posix()] = sha(path)
    final_manifest = {"generated_at": summary["generated_at"], "inputs": bindings,
                      "protected": manifest["protected"],
                      "outputs": {p.name: sha(p) for p in out.iterdir() if p.is_file()}}
    with (out / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(final_manifest, stream, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output.resolve())
