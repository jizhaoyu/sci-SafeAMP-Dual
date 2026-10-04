"""Review explicitly identified molecular forms and original MIC tables, preserving source conflicts."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd
from pypdf import PdfReader

from audit_mic_primary_hirsch2020 import cells, table
from audit_mic_primary_ludwig2022 import interval
from research_data import sequence_identity
from research_utils import ROOT, sha256, utc_now, write_json


PMID = "39367191"
DOI = "10.1038/s42003-024-06946-4"
PMCID = "PMC11452689"
RAW = ROOT / "03_experiments/audits/mic_primary_candidate_sources_20261002_v1"
REVIEWED = ROOT / "03_experiments/audits/mic_reviewed_subset_groups_20261002_v3"
# Values transcribed from the original PDF page 16 and checked against its text layer.
MICS = {
    "AP": ("19.75", "9.4"), "PROT1": ("3.91", "1.8"),
    "TP2K": ("3.91", "1.8"), "TP2": ("3.91", "1.7"),
    "IND": ("19.75", "10.4"), "LL37": ("18.81", "4.2"),
    "INDa": ("8.78", "4.6"), "R8": ("13.33", "6.0"),
    "PGRLa": ("3.91", "1.9"), "PGLa": ("18.1", "4.6"),
    "PGL": ("90", "38.1"), "GUA2": ("15.68", "5.9"),
    "CP1": ("2.63", "0.8"), "BUF2": (">250", "102.7"),
    "BAC5": ("13.33", "2.6"), "MAG2": ("93.75", "38"),
    "MAG2a": ("8.78", "3.6"),
}


def run(output: Path) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite original-paper audit: {output}")
    xml = RAW / "PMC11452689.xml"
    pdf = RAW / "42003_2024_6946_MOESM1_ESM.pdf"
    rendered = RAW / "42003_2024_6946_table_s1_s2.png"
    article = ElementTree.parse(xml).getroot()
    identifiers = {item.attrib.get("pub-id-type"): item.text for item in article.findall(".//article-id")}
    if any(identifiers.get(kind) != value for kind, value in (("pmid", PMID), ("pmcid", PMCID), ("doi", DOI))):
        raise ValueError("Original article identifiers changed.")
    original_rows = [cells(row) for row in table(article, "Table 1").findall(".//tbody/tr")]
    if len(original_rows) != 17 or {row[1] for row in original_rows} != set(MICS):
        raise ValueError("Original Table 1 molecular inventory differs from 17 peptides.")
    sections = {" ".join(sec.find("title").itertext()): " ".join(sec.itertext())
                for sec in article.findall(".//sec") if sec.find("title") is not None}
    synthesis, method = sections.get("Synthesis and purification", ""), sections.get("MIC measurements", "")
    if not all(token in synthesis for token in ("Wang resin", "free C-terminal", "amidated C-terminal")):
        raise ValueError("Original methods do not explicitly distinguish free-acid and amidated peptides.")
    if not all(token in method for token in ("BW25113", "Müller-Hinton II Broth", "18", "37", "MIC was defined")):
        raise ValueError("Original MIC strain, medium or endpoint changed.")
    license_node = article.find(".//license")
    if license_node is None or "creativecommons.org/licenses/by-nc-nd/4.0/" not in " ".join(license_node.itertext()):
        raise ValueError("Original article license differs from the observed CC BY-NC-ND 4.0; review reuse terms again.")
    reader = PdfReader(pdf)
    if len(reader.pages) != 33:
        raise ValueError("Original supplement page count changed.")
    text = reader.pages[15].extract_text() or ""
    if not all(token in text for token in ("Supplementary Table 1", "BW25113 K-12", "MIC (ug/ml)", "Supplementary Table 2")):
        raise ValueError("Original supplement MIC table or unit missing.")
    table1_text, table2_text = text.split("Supplementary Table 2", 1)
    for abbreviation, (value, micromolar) in MICS.items():
        if not re.search(r"\b" + re.escape(abbreviation) + r"\s+" + re.escape(value) + r"\s+" + re.escape(micromolar) + r"\b", table1_text):
            raise ValueError(f"Original Table S1 numeric row changed: {abbreviation}")
    if not re.search(r"BUF2\s+>2400\s+985\.7\s+250\s+102\.7", table2_text):
        raise ValueError("Original BUF2 Table S2 censoring discrepancy changed; review the source again.")
    records = []
    for name, abbreviation, sequence_form, _ in original_rows:
        form = sequence_form.replace(" ", "")
        if form.endswith("-OH"):
            sequence, chemistry = form.removesuffix("-OH"), "C-terminal free acid"
        elif form.endswith("-NH2"):
            sequence, chemistry = form.removesuffix("-NH2"), "C-terminal amide"
        else:
            raise ValueError(f"Unknown original terminal annotation: {abbreviation}")
        if not 10 <= len(sequence) <= 50 or set(sequence) - set("ACDEFGHIKLMNPQRSTVWY"):
            raise ValueError(f"Unexpected molecular sequence: {abbreviation}")
        value, micromolar = MICS[abbreviation]
        low, high, label = interval(value)
        if chemistry != "C-terminal free acid":
            decision, reason = "excluded", "amidated_molecule_outside_unmodified_domain"
        elif label is None:
            decision, reason = "excluded", "MIC_in_32_128_threshold_gap"
        elif abbreviation == "BUF2":
            decision, reason = "pending", "Table_S1_reports_greater_than_250_but_Table_S2_reports_exact_250"
        else:
            decision, reason = "candidate", "original_sequence_free_acid_and_direct_MIC_support_binary_label"
        records.append({
            "record_id": f"PMID{PMID}:{abbreviation}", "name": name, "abbreviation": abbreviation,
            "sample_id": hashlib.sha256(sequence.encode("ascii")).hexdigest()[:24],
            "sequence": sequence, "molecular_form": chemistry,
            "paper_value": value, "unit": "µg/mL", "paper_alternate_micromolar_value": micromolar,
            "target": "Escherichia coli K-12 BW25113", "medium": "Mueller-Hinton II broth",
            "incubation_hours": 18, "temperature_c": 37, "inoculum_cfu_ml": 5e5,
            "normalized_low_ug_ml": low, "normalized_high_ug_ml": high,
            "derived_binary_label": label, "decision": decision, "reason": reason,
            "assay_study_ids": f"doi:{DOI}|pmid:{PMID}",
            "paper_location": "Main Table 1; supplementary Table S1/S2 page 16; Methods synthesis/MIC",
            "training_release": False,
        })
    frame = pd.DataFrame(records)
    candidates = frame[frame.decision.eq("candidate")]
    if len(candidates) != 6 or not candidates.derived_binary_label.eq(1).all():
        raise ValueError("Expected six positive free-acid candidates, with the negative source withheld.")
    cohort = pd.read_csv(REVIEWED / "candidate_molecules.csv")
    if len(cohort) != 41:
        raise ValueError("Frozen candidate comparison cohort changed.")
    pairs = []
    for candidate in candidates.itertuples(index=False):
        for other in cohort.itertuples(index=False):
            identity = sequence_identity(candidate.sequence, other.seq, identity_mode="alignment")
            pairs.append({"candidate_sample_id": candidate.sample_id, "candidate_abbreviation": candidate.abbreviation,
                          "other_sample_id": other.sample_id, "other_review_component": other.review_component,
                          "identity": identity, "edge_at_0_40": identity >= 0.40})
    pairs = pd.DataFrame(pairs)
    connected_groups = sorted(int(group) for group in pairs.loc[pairs.edge_at_0_40, "other_review_component"].unique())
    output.mkdir(parents=True)
    frame.to_csv(output / "record_review.csv", index=False)
    pairs.to_csv(output / "similarity_reviewed.csv", index=False)
    (output / "report.md").write_text(
        "# Bhaumik 等 2024：明确末端形式的候选证据\n\n"
        f"[原论文](https://pmc.ncbi.nlm.nih.gov/articles/{PMCID}/)，PMID {PMID}，DOI {DOI}，CC BY-NC-ND 4.0。"
        "该来源仅在本地保留证据候选；项目数据再利用及发布范围尚未审查通过。"
        "主文 Table 1 与合成方法逐条区分酸端和酰胺端；补充 Table S1 报告 *E. coli* BW25113 的 MIC，"
        "条件为 Mueller-Hinton II broth、5×10^5 CFU/mL、18 h、37 °C。补充 PDF 第 16 页已渲染和目视复核。\n\n"
        "完整审查 17 条分子：6 条游离酸端阳性候选；8 条酰胺端超出当前分子域，2 条游离酸端处于阈值空档，均排除。"
        "Buforin II 在 Table S1 为 `>250 µg/mL`，在 Table S2 的 E. coli 列为 `250 µg/mL`；两者均落阴性侧，"
        "但原始删失标记不一致，保留待核实，未选取其中一个版本放行。\n\n"
        f"6 条阳性候选与现有 41 条逐成员比较共 246 对，达到 0.40 的边 {int(pairs.edge_at_0_40.sum())}，"
        f"连接现有组件 {connected_groups}。整篇论文必须一起连接，会桥接这些组件；"
        "这些候选尚未合入 v3 队列，不支撑它们也已经通过五折的声明。许可证再利用门禁未通过，"
        "负例删失标记未解决；后续若获准合并仍必须完整重算。训练释放为 0。\n",
        encoding="utf-8")
    inputs = (xml, pdf, rendered, REVIEWED / "manifest.json", REVIEWED / "candidate_molecules.csv",
              ROOT / "02_code/audit_mic_primary_hirsch2020.py", ROOT / "02_code/audit_mic_primary_ludwig2022.py",
              ROOT / "02_code/research_data.py")
    manifest = {
        "status": "blocked_source_reuse_and_censoring_review", "generated_at": utc_now(),
        "paper": {"pmid": PMID, "pmcid": PMCID, "doi": DOI, "license": "CC BY-NC-ND 4.0"},
        "source_reuse_gate": "pending_review_not_authorized_for_training_or_publication",
        "original_molecules_reviewed": len(frame), "positive_free_acid_candidates": len(candidates),
        "negative_free_acid_candidates_withheld": 1, "excluded_amidated": 8, "excluded_threshold_gap": 2,
        "full_reviewed_similarity_pairs": len(pairs), "reviewed_similarity_edges_at_0_40": int(pairs.edge_at_0_40.sum()),
        "connected_reviewed_components": connected_groups,
        "included_in_candidate_cohort_v3": False, "records_released_for_training": 0,
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in inputs},
        "outputs": {name: sha256(output / name) for name in ("record_review.csv", "similarity_reviewed.csv", "report.md")},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output), ensure_ascii=True, indent=2))
