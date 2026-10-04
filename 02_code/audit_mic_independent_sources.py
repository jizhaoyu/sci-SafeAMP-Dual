"""Review frozen primary sources; derive MIC labels without granting training release."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
from pypdf import PdfReader

from public_data import MOLECULAR_WEIGHTS, bounds, measurement_label
from research_utils import ROOT, sha256, utc_now, write_json

RAW = ROOT / "03_experiments/audits/mic_independent_sources_20261002_v1/raw"
PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-01.json"


def text(node) -> str:
    return " ".join("".join(node.itertext()).split())


def cells(table) -> list[list[str]]:
    return [[text(cell) for cell in row if cell.tag in {"td", "th"}] for row in table.findall(".//tr")]


def molecular_weight(sequence: str) -> float:
    return sum(MOLECULAR_WEIGHTS[aa] for aa in sequence) - 18.0152 * (len(sequence) - 1)


def run(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite primary-source review: {output}")
    articles, inventory, tables = {}, [], []
    for path in sorted(RAW.glob("*.xml")):
        root = ET.parse(path).getroot()
        article = root if root.tag == "article" else root.find(".//article")
        if article is None or article.find("body") is None:
            raise ValueError(f"Metadata or access challenge is not a primary source: {path}")
        ids = {n.get("pub-id-type"): n.text for n in article.findall("./front/article-meta/article-id")}
        pmcid = ids["pmcid"]
        articles[pmcid] = article
        acquisition = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=2992949"
                       if path.name == "Peptides2010_efetch.xml" else
                       f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML")
        inventory.append({"primary_file": path.name, "pmcid": pmcid, "pmid": ids["pmid"], "doi": ids["doi"],
                          "title": text(article.find("./front/article-meta/title-group/article-title")),
                          "source_url": acquisition, "primary_url": "https://doi.org/" + ids["doi"],
                          "license_as_reported": " ".join(text(n) for n in article.findall("./front/article-meta/permissions/license")),
                          "sha256": sha256(path), "body_present": True})
        for table in article.findall(".//table-wrap"):
            for index, row in enumerate(cells(table)):
                tables.append({"pmcid": pmcid, "primary_file": path.name, "table_id": table.get("id"),
                               "row_index": index, "cells_json": json.dumps(row, ensure_ascii=False)})
    by_id = {row["pmcid"]: row for row in inventory}
    decisions, assays = [], []

    def decision(pmcid, name, sequence, status, basis, location, value="", unit=""):
        source = by_id[pmcid]
        row = {"record_id": f"{pmcid}:{name}", "pmcid": pmcid, "pmid": source["pmid"], "doi": source["doi"],
               "paper_peptide_name": name, "sequence": sequence, "decision": status, "basis": basis,
               "primary_file": source["primary_file"], "primary_location": location,
               "raw_mic_as_reported": value, "raw_unit_as_reported": unit, "training_release": False}
        decisions.append(row)
        return row

    def assay(record, target, value, medium, method):
        sequence = record["sequence"]
        if not 10 <= len(sequence) <= 50 or set(sequence) - set(MOLECULAR_WEIGHTS):
            raise ValueError("Candidate outside frozen canonical length domain.")
        label = measurement_label({"concentration": value, "unit": {"name": "µM"}}, sequence, 32, 128)
        if label is None:
            raise ValueError("Candidate label falls in the threshold gap.")
        low, high = bounds(value)
        factor = molecular_weight(sequence) / 1000
        assays.append({**record, "sample_id": hashlib.sha256(sequence.encode("ascii")).hexdigest()[:24],
                       "target": target, "endpoint": "MIC", "raw_mic": value, "raw_unit": "µM",
                       "normalized_low_ug_ml": low * factor, "normalized_high_ug_ml": high * factor,
                       "normalization": "protocol-mic-01 linear canonical average molecular weight; not rounded table mass",
                       "molecular_weight_da": factor * 1000, "medium": medium, "method": method,
                       "molecular_form": "linear L peptide; free N terminus; C-terminal free acid; no covalent modification",
                       "assay_study_ids": f"doi:{record['doi']}|pmid:{record['pmid']}", "derived_label": label})

    # Zhang: full original structures, free ends, dark MIC, and the exact table cells were checked.
    zhang = articles["PMC8203924"]
    body = text(zhang.find("body"))
    if any(marker not in body for marker in ("Wang resin", "lack of C-terminal amidation", "without light", "ATCC 8739")):
        raise ValueError("Zhang synthesis or assay evidence changed.")
    ztable = zhang.find(".//table-wrap[@id='tab2']")
    zrows = cells(ztable)[2:]
    if zrows[:2] != [["1, G3K5(RW)3", "1,855.1", "107.8", "107.8", ">215.6"],
                     ["2, G3(RW)3K5", "1,855.1", "107.8", "107.8", ">215.6"]]:
        raise ValueError("Zhang Table 2 MIC control cells changed.")
    pdf = PdfReader(RAW / "zhang2021_primary.pdf")
    if len(pdf.pages) != 13 or ">215.6" not in pdf.pages[6].extract_text():
        raise ValueError("Zhang visual-table PDF changed.")
    for row, sequence in zip(zrows[:2], ("GGGKKKKKRWRWRW", "GGGRWRWRWKKKKK")):
        record = decision("PMC8203924", row[0], sequence, "local_fields_confirmed_not_training_released",
                          "Figure 1 compounds 1/2 have free NH2/COOH; Wang resin and lack of amidation explicit; Table 2 dark MIC",
                          "PDF pp. 3, 5-7; Materials, ATCC Standard Strains; Figure 1; Table 2", row[-1], "µM")
        assay(record, "Escherichia coli ATCC 8739", row[-1], "LB; twofold peptide dilutions",
              "100 uL inoculum + 900 uL peptide; final 1e6 CFU/mL; 20 h, 37 C, shaking without light; complete growth inhibition; triplicate")
    for row in zrows[2:]:
        decision("PMC8203924", row[0], "", "excluded_covalent_phthalocyanine_conjugate",
                 "Pc chemical conjugates are outside modifications=none; preserve original compound numbering even where captions disagree",
                 "Table 2 / Figure 1", row[-1], "µM")
    decision("PMC8203924", "bioluminescent assays", "", "excluded_endpoint_ic50",
             "IC50 under dark/light conditions is not MIC", "Tables 1/3")

    # Sharma: do not confuse bare assay peptides with the K-tritrpticin-DT immunogen.
    sharma = articles["PMC3782441"]
    sbody = text(sharma.find("body"))
    compact = re.sub(r"\s+", "", sbody)
    if ("hydroxymethylphenoxymethylpolysterene" not in compact or "trifluoroacetic acid" not in sbody
            or "VRRFPWWWPFLRR" not in compact or "Addition of LB medium" not in sbody):
        raise ValueError("Sharma synthesis or MIC evidence changed.")
    stable = cells(sharma.find(".//table-wrap[@id='pone-0075582-t002']"))
    if stable[1:] != [["E. coli BL21λD3", "3.12", "400"], ["E. coli ATCC25922", "3.12", "400"]]:
        raise ValueError("Sharma Table 2 cells changed.")
    pdf = PdfReader(RAW / "sharma2013_primary.pdf")
    # Figure 3A is a raster: sequence was read from the original rendered page,
    # not OCR or a database. Bind that manual transcription to the exact source.
    if ("Figure 3." not in pdf.pages[6].extract_text() or "400" not in pdf.pages[5].extract_text()
            or sha256(RAW / "sharma2013_primary.pdf") != "5a96665935a39d8bda3617d786fd1d372f64782630f9288481e3346da573188b"
            or sha256(RAW / "sharma2013_page7.png") != "4cc64d492522661e197d3a6dd50b0546cc7d0537eefcbc66fcadab0945805f33"):
        raise ValueError("The visually reviewed original sequence image or MIC table changed.")
    for name, sequence, column in (("Tritrpticin", "VRRFPWWWPFLRR", 1), ("12PhD1", "YHDRPPPRPFKH", 2)):
        record = decision("PMC3782441", name, sequence, "local_fields_confirmed_not_training_released",
                          "All peptides SPPS on hydroxymethylphenoxymethylpolystyrene (Wang-type acid linker) with TFA cleavage; Figure 3A sequence checked; bare MIC peptides distinguished from immunogen",
                          "PDF pp. 2-3, 6-7; Peptide synthesis; MIC method; Table 2; Figure 3A", stable[1][column], "µM")
        for row, target in zip(stable[1:], ("Escherichia coli BL21λD3", "Escherichia coli ATCC 25922")):
            assay(record, target, row[column], "10 mM phosphate buffer, then LB medium",
                  "~1e4 bacterial cells in 100 uL; 2 h at 37 C, then LB; growth prevention at OD600; post-LB incubation and MIC replicate count not reported")
    decision("PMC3782441", "K-tritrpticin-DT", "", "excluded_covalent_immunogen_no_mic",
             "N-terminal Lys/glutaraldehyde toxoid immunogen used for antibody generation; not Table 2 MIC molecule", "Synthesis/Immunization")
    decision("PMC3782441", "unrelated EHGTPPRVMSSM control", "EHGTPPRVMSSM", "excluded_no_numerical_mic",
             "No clearance in radial diffusion is not a quantitative MIC label", "Figure 3 / Figure S3")

    # Preserve the complete Equinin MIC90 inventory without resolving unit/sequence inconsistencies by guess.
    equinin = articles["PMC12842892"]
    for row in cells(equinin.find(".//table-wrap[@id='marinedrugs-24-00046-t001']"))[2:]:
        decision("PMC12842892", row[0], row[1], "withheld_unit_endpoint_and_sequence_review",
                 "Table 1 MIC90 in ug/mL differs from method dose range in uM; several detailed synthesis sequences also disagree; >100 ug/mL does not establish >=128",
                 "Table 1; Methods 3.3.1; detailed synthesis", row[2], "MIC90 / µg mL−1")
    # AamAP1-Lys: retain both strains; do not cherry-pick the 4 ug/mL result.
    for name, status in (("AamAP1-Lys", "excluded_whole_molecule_threshold_gap"),
                         ("AamAP1-Lys-NH2", "excluded_c_terminal_amidation")):
        decision("PMC11840929", name, "FLFKLIPKAIKKLISKFK", status,
                 "Free acid has MIC 4 at ATCC700928 and 35 at ATCC25922; whole acid molecule withheld. Amidated version outside frozen domain",
                 "Table 1; peptide synthesis", "4|35" if "-NH2" not in name else "4|9", "µg/mL")
    # Other sources remain evidence leads, never substitutes for the four confirmed candidates.
    for name in ("Hst5", "Hst8"):
        decision("PMC12787115", name, "", "withheld_terminal_identity_unestablished",
                 "Commercial histatin origin does not establish actual assay terminal form; metal-complex results cannot be inherited",
                 "Table 2; Materials/ITC", ">165" if name == "Hst5" else "160", "µM")
    for name in ("Hst5 + Cu(II)", "Hst8 + Cu(II)"):
        decision("PMC12787115", name, "", "excluded_metal_complex", "Metal complex outside unmodified molecule domain", "Table 2")
    for name in ("LBP14", "LBP14-RKRR", "L7", "R7", "A7", "G7"):
        decision("PMC10654507", name, "", "withheld_table_method_concentration_conflict",
                 "Methods explicitly declare 0.5,1,2,4,8,16,32,64 uM final doses; Table 2 uses 1.13,2.26,4.53,18.1,36.2 uM; no silent unit correction. Ser-Wang synthesis also cannot establish the parent Lys/Arg-ending molecules",
                 "Tables 1/2; Peptide synthesis; Determination of MIC/MBC")
    for name in ("LBP14 + L7", "LBP14-RKRR + L7"):
        decision("PMC10654507", name, "", "excluded_two_molecule_mixture", "A cocktail is not one sequence observation", "Table 2 footnote a")
    for name in ("A6", "G6", "N6", "LBP14", "LBPN6", "N6CK", "A6CK", "G6CK"):
        decision("PMC6978316", name, "", "withheld_molecular_identity_or_cystine_state",
                 "Commercial peptide synthesis does not establish terminal form; cysteine-containing constructs require bond-state review; >64 is not >=128 proof",
                 "Table 2; peptide synthesis")
    for row in cells(articles["PMC6023086"].find(".//table-wrap[@id='biomolecules-08-00019-t002']"))[1:]:
        status = "excluded_amidated_or_noncanonical_molecule" if "NH" in row[1] else "withheld_sequence_and_terminal_identity_review"
        decision("PMC6023086", row[0], row[1], status,
                 "Amidated/noncanonical rows outside frozen domain. Magainin F5W name and printed F-containing sequence require resolution and terminal-form proof",
                 "Table 2; Materials 4.1", row[-1], "µM")
    for name in ("Buforin IIb", "Buf IIIb", "Buf IIIb-L", "Buf IIIb-F", "Buf IIIb-Y", "Magainin II"):
        decision("PMC3597565", name, "", "withheld_synthetic_terminal_identity_unestablished",
                 "Synthetic Table 2 MIC molecule terminal identity unreported; recombinant display/pepsin mixtures do not establish synthetic molecule identity",
                 "Tables 1/2; Peptide synthesis")
    for name in ("E6", "HHC10"):
        decision("PMC2992949", name, "", "pending_original_sequence_image_and_mic_figure_review",
                 "Native SUMO cleavage is promising; original sequence images, K12 target and quantitative MIC bars still need review",
                 "Figures 1C, 4E, 5C; Antimicrobial activity")

    output.mkdir(parents=True)
    for name, frame in (("source_inventory.csv", pd.DataFrame(inventory)), ("original_table_cells.csv", pd.DataFrame(tables)),
                        ("record_decisions.csv", pd.DataFrame(decisions)), ("candidate_assays.csv", pd.DataFrame(assays))):
        frame.to_csv(output / name, index=False)
    report = (
        "# 独立原始来源补充审计\n\n"
        "本轮保存 10 篇有完整正文的原始 XML，逐表原始单元格、来源 URL、许可原文与哈希均单列。"
        "未获取的 Tritrpticin 2006 / poly(Arg-His) 2004 原文接口、Dermcidin 原文接口只保留为访问线索，未生成候选。\n\n"
        "## 局部证据确认\n\n"
        "- [Zhang 2021](https://doi.org/10.3389/fmicb.2021.624465)：G3K5(RW)3、G3(RW)3K5，均为游离酸阴性对照；"
        "ATCC 8739 的暗条件 MIC >215.6 µM。图 1 明确自由末端，表 2 与方法已核对；Pc 接枝和 IC50 均排除。\n"
        "- [Sharma 2013](https://doi.org/10.1371/journal.pone.0075582)：Tritrpticin 的 MIC 3.12 µM，12PhD1 的 MIC 400 µM；"
        "各有 BL21λD3、ATCC 25922 两条测定。Figure 3A 与 Table 2 目视核对，合成使用羟甲基苯氧甲基聚苯乙烯酸型树脂和 TFA 裂解；"
        "同研究整体分组。免疫原 K-tritrpticin-DT 与径向扩散对照均排除。后续 LB 培养时间/重复数未报告，保持缺失。\n\n"
        "以上 4 条分子、6 条 MIC 为局部确认候选；标签按冻结协议的平均分子量规则重推导，不手写类别。"
        "这不是完整训练释放，所有记录 training_release=false。\n\n"
        "## 明确暂缓项\n\n"
        "Equinin 的 MIC90/单位及部分序列冲突；LBP/L7 的方法剂量与表格数值冲突；AamAP1-Lys 的 35 µg/mL 空档测定导致整个酸型分子暂缓；"
        "Histatin、Buforin 等受测末端不明。完整决定见 record_decisions.csv，未仅挑选阳性或阴性结果。"
        "候选仍需完整证据释放和研究/全员分组门禁，阈值、分子域、折数、seed 均未调整。\n\n"
        "## 复跑\n\n"
        "`python 02_code/audit_mic_independent_sources.py --output 03_experiments/audits/mic_independent_review_my_run`\n"
        "输出路径必须不存在；原始文件仅供本地核查，未将所有来源文件的公开访问等同于再发布授权。\n")
    (output / "report.md").write_text(report, encoding="utf-8")
    paths = [PROTOCOL, ROOT / "02_code/public_data.py", *sorted(path for path in RAW.iterdir() if path.is_file())]
    manifest = {"status": "local_review_complete_training_not_released", "generated_at": utc_now(),
                "audit_protocol_id": "protocol-mic-01", "primary_articles": len(inventory),
                "reviewed_records": len(decisions), "candidate_molecules": len({r["sample_id"] for r in assays}),
                "candidate_observations": len(assays), "records_released_for_training": 0, "training_started": False,
                "script_sha256": sha256(Path(__file__)),
                "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
                "outputs": {path.name: sha256(path) for path in output.iterdir() if path.is_file()}}
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    result = run(parser.parse_args().output)
    print(json.dumps({k: result[k] for k in ("status", "primary_articles", "reviewed_records", "candidate_molecules", "candidate_observations")}, indent=2))
