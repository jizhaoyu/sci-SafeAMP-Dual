"""Release-review the fixed candidate evidence without training or changing the cohort."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from audit_mic_reviewed_subset_ludwig import verify
from public_data import measurement_label
from research_utils import ROOT, sha256, utc_now, write_json

COHORT = ROOT / "03_experiments/audits/mic_three_fold_20261002_v1"
RECHECK = ROOT / "03_experiments/audits/mic_release_source_recheck_20261002_v1"
VALIDATION = ROOT / "03_experiments/audits/mic_three_fold_validation_20261002_v1.json"
PREFIX = "03_experiments/audits/"
SOURCES = {
    "okimura2021": ("mic_primary_review_pmid33790103_20261002_v1/raw/44_b20-00799.pdf",
                    "59d827548f7917a6fec690a6161b7438ed3fd16f12ecf2782e6ec7406b7a7299",
                    "https://doi.org/10.1248/bpb.b20-00799", "PDF pp. 2, 3, 5; Tables 1, 2, 4; antimicrobial activity; reference 18",
                    "Table 1 explicitly H-sequence-OH; Table 2 acetate salt; no covalent terminal modification",
                    "broth microdilution; primary article cites Goto 1990; cited method separately checked",
                    "CAMHB is database metadata; referenced standard specifies cation-supplemented MHB; article-specific deviations not reported"),
    "goto1990": ("mic_release_source_recheck_20261002_v1/goto1990_referenced_mic_method.pdf",
                 "ee68735c5659ade076b44fb64fb494e7c965f48ac1a184cca70ba2a0bfa5505e",
                 "https://doi.org/10.11250/chemotherapy1953.38.102", "PDF pp. 2-3; sections 2, 5, 6",
                 "method reference only; not an additional peptide study", "referenced MIC method verified",
                 "Conditions in a cited standard are recorded as referenced-method conditions, not direct observations of the 2021 experiment"),
    "hirsch2020": ("mic_primary_review_pmid32344933_20261002_v1/raw/PMC7284870_fullTextXML.xml",
                   "a5718ea66e9dff8a0eee9fec70cd9dad62f9b0f3ae4f4406734066abbba5564d",
                   "https://doi.org/10.3390/microorganisms8050626", "Tables 1, 2; Methods 2.2, 2.4; Table 5 baseline consistency check",
                   "Table 2 explicitly -OH; Table 1 acid is 41 aa, amidated analogue is different 40 aa molecule",
                   "broth MIC; 18 h; 37 C; CAMB; no-growth by visual/OD600; Table 2 n=4",
                   "Only individual free-acid peptide MIC used; colistin/polymyxin mixtures, amidated analogue and population MIC50/MIC90 excluded"),
    "ludwig2022": ("mic_primary_candidate_sources_20261002_v1/PMC9221748.xml",
                   "711469c8b20611059bf3bbc3e21615e2248c771a31d8af21dd528a3f96ef0b17",
                   "https://doi.org/10.3390/cimb44060174", "Table 1; Methods 2.2, 2.3",
                   "Table 1 sequence-OH; Methods 2.2 explicitly Wang resin and C-terminal acids",
                   "broth MIC; 20 +/- 2 h; 37 C; 25% MHBII or LB as recorded; at least twice in triplicate; no-growth OD600",
                   "Api802 threshold-gap and Api806 opposing medium labels excluded as whole molecules in the frozen prior review; no phage-combination endpoint used"),
    "cheng2011": ("mic_primary_candidate_sources_20261002_v1/cheng2011_primary.pdf",
                  "ef89ce5ef9c3b8497b61f0e990df5892f7306ce5a9604e7470a2859f7a80c090",
                  "https://doi.org/10.1016/j.bbamem.2010.11.025", "PDF pp. 2-4; Table 1; Methods 2.2.1, 2.2.7",
                  "Table 1 explicitly sequence-COOH; synthesis describes appropriate Rink/Wang resin; acid distinguished from amide parent",
                  "broth MIC; Mueller-Hinton; 18 h; 37 C; visible no growth; modal MIC from repeat experiments",
                  "MIC replicate count not specified; do not infer from counts reported for CD/NMR experiments"),
    "tiltak2009": ("mic_primary_candidate_sources_20261002_v1/tiltak2009_primary_thesis.pdf",
                   "3de5ad15f6827f71dc10b38c216fa2d82db24f2f0799255334e57153b3dc3247",
                   "https://publikationen.bibliothek.kit.edu/1000012217", "PDF pp. 30, 32-33, 46-47; Tables 4.1, 4.2; section 3.2.2",
                   "Chapter 4 explicitly free COOH variants; Table 4.1 complete sequences; Wang versus Rink described",
                   "broth MIC; LB/salt-free LB as recorded; overnight 37 C; majority of four wells visually clear",
                   "Author identifies chapter 4 as the same experiments published in Strandberg 2007; thesis and article aliases remain one study"),
    "zhang2021": ("mic_independent_sources_20261002_v1/raw/PMC8203924.xml",
                  "15122ee960fb2d43f6427b88601aa1c61392077cf9f679f88cc7022bf612708c",
                  "https://doi.org/10.3389/fmicb.2021.624465", "Materials; Figure 1; Table 2; ATCC Standard Strains method; PDF pp. 3, 5-7",
                  "Figure 1 unmodified NH2/COOH peptide controls; Wang resin; text explicitly lack of C-terminal amidation",
                  "MIC; LB; 20 h; 37 C; without light; complete growth inhibition; triplicate",
                  "Table 1 IC50, phthalocyanine conjugates, light-assisted endpoints and engineered reporter-strain endpoints excluded"),
    "sharma2013": ("mic_independent_sources_20261002_v1/raw/PMC3782441.xml",
                   "3d98fcc3b04b389b0658f59a79272efd435ec297fb29f5a6ef3e89ea6bed8e21",
                   "https://doi.org/10.1371/journal.pone.0075582", "Peptide synthesis; MIC method; Table 2; Figure 3A; PDF pp. 2-3, 6-7",
                   "All synthetic peptides on hydroxymethylphenoxymethylpolystyrene acid linker; TFA cleavage; bare peptides distinguished from K-tritrpticin-DT immunogen",
                   "broth MIC; phosphate then LB; initial 2 h at 37 C; growth prevented at OD600",
                   "Post-LB incubation time and MIC replicate count not reported; radial-diffusion zones are not MIC; synthetic 12PhD1 peptide, not a phage particle"),
}
# Transcribed from the primary tables/figures, independently of the candidate CSV labels.
MOLECULES = {
    "PRLPRIPRLPRYPRYPRWPRHPT": ("okimura2021", "Myticalin A6 (4-26)-OH, Table 1 row i", ["Escherichia coli NBRC 12734"], [">128"], "µg/ml"),
    "RLPRYPRYPRWPRHPT": ("okimura2021", "Myticalin A6 (11-26)-OH, row l", ["Escherichia coli NBRC 12734"], [">128"], "µg/ml"),
    "PRYPRWPRHPT": ("okimura2021", "Myticalin A6 (16-26)-OH, row m", ["Escherichia coli NBRC 12734"], [">128"], "µg/ml"),
    "GFLKKVGKKLEGASDLTRDATIQTIAVAQAAANVAATAKQG": ("hirsch2020", "EtCec3-OH, Table 2 acid column", ["Escherichia coli D31", "Escherichia coli ATCC 25922"], [">1024", ">1024"], "µg/mL"),
    "GNNRPVYIPRPRPPHPRL": ("ludwig2022", "Api801", ["Escherichia coli Rosetta DE3 pLysS"], ["2"], "µg/mL"),
    "GNNRPIYIPRPRPPHPRPIRV": ("ludwig2022", "Api805", ["Escherichia coli Rosetta DE3 pLysS"], ["4"], "µg/mL"),
    "MNNRPIYIPRPRPPHPAL": ("ludwig2022", "Api810, 25% MHBII then LB", ["Escherichia coli Rosetta DE3 pLysS"] * 2, ["128", ">128"], "µg/mL"),
    "GLFDIVKKVVGAIGSL": ("cheng2011", "Aurein 2.3-COOH", ["Escherichia coli K12 UB1005"], [">128"], "µg/mL"),
    "KLALKLALKALKAALKLA": ("tiltak2009", "MAP-COOH", ["Escherichia coli DSM 1103", "Escherichia coli DH 5alpha"], [">128", ">128"], "µg/mL"),
    "KIAGKIAKIAGKIAKIAGKIA": ("tiltak2009", "MSI-103-COOH", ["Escherichia coli DSM 1103", "Escherichia coli DH 5alpha"], ["8", "16"], "µg/mL"),
    "GMASKAGAIAGKIAKVALKAL": ("tiltak2009", "PGLa-COOH", ["Escherichia coli DSM 1103", "Escherichia coli DH 5alpha"], [">128", ">128"], "µg/mL"),
    "GGGKKKKKRWRWRW": ("zhang2021", "1, G3K5(RW)3", ["Escherichia coli ATCC 8739"], [">215.6"], "µM"),
    "GGGRWRWRWKKKKK": ("zhang2021", "2, G3(RW)3K5", ["Escherichia coli ATCC 8739"], [">215.6"], "µM"),
    "VRRFPWWWPFLRR": ("sharma2013", "Tritrpticin, Figure 3A", ["Escherichia coli BL21λD3", "Escherichia coli ATCC 25922"], ["3.12", "3.12"], "µM"),
    "YHDRPPPRPFKH": ("sharma2013", "12PhD1, Figure 3A", ["Escherichia coli BL21λD3", "Escherichia coli ATCC 25922"], ["400", "400"], "µM"),
}


def review(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite primary evidence release review: {output}")
    cohort = verify(COHORT)
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if (cohort["fold_structure_gate_passed"] is not True
            or validation["status"] != "three_fold_validation_passed_evidence_release_still_blocked"
            or validation["inputs"][str((COHORT / "manifest.json").relative_to(ROOT))] != sha256(COHORT / "manifest.json")):
        raise ValueError("Expected independently verified frozen three-fold candidate cohort")
    molecules = pd.read_csv(COHORT / "candidate_molecules.csv", keep_default_na=False)
    observations = pd.read_csv(COHORT / "candidate_observations.csv", keep_default_na=False)
    if set(molecules.seq) != set(MOLECULES) or len(molecules) != 15 or len(observations) != 22:
        raise ValueError("Frozen source recheck does not cover the entire candidate inventory")
    inputs = {str(path.relative_to(ROOT)): sha256(path) for path in (COHORT / "manifest.json", VALIDATION)}
    source_rows = []
    for source_id, data in SOURCES.items():
        relative, expected_hash, url, location, chemistry, method, limitation = data
        path = ROOT / PREFIX / relative
        if sha256(path) != expected_hash:
            raise ValueError(f"Primary source changed after visual/XML recheck: {path}")
        inputs[str(path.relative_to(ROOT))] = expected_hash
        source_rows.append({"source_id": source_id, "primary_file": str(path.relative_to(ROOT)), "sha256": expected_hash,
                            "source_url": url, "primary_locations": location, "molecular_evidence": chemistry,
                            "method_evidence": method, "limitations_and_scope": limitation})
    proof_files = [*RECHECK.glob("*.png")]
    for name in ("tiltak2009_table4_1.png", "tiltak2009_table4_2.png", "cheng2011_table1.png"):
        proof_files.append(ROOT / PREFIX / "mic_primary_candidate_sources_20261002_v1" / name)
    for name in ("zhang2021_page6.png", "zhang2021_page7.png", "sharma2013_page3.png", "sharma2013_page6.png", "sharma2013_page7.png"):
        proof_files.append(ROOT / PREFIX / "mic_independent_sources_20261002_v1/raw" / name)
    for path in proof_files:
        inputs[str(path.relative_to(ROOT))] = sha256(path)
    molecule_rows, assay_rows = [], []
    for molecule in molecules.itertuples(index=False):
        source_id, name, targets, raw_values, unit = MOLECULES[molecule.seq]
        source = SOURCES[source_id]
        selected = observations[observations.sample_id.eq(molecule.sample_id)]
        actual = list(zip(selected.target, selected.raw_mic.astype(str), selected.raw_unit))
        expected = list(zip(targets, raw_values, [unit] * len(targets)))
        if sorted(actual) != sorted(expected):
            raise ValueError(f"MIC raw value/unit/target mismatch with primary transcription: {name}")
        derived = set()
        for row in selected.to_dict(orient="records"):
            label = measurement_label({"concentration": row["raw_mic"], "unit": {"name": row["raw_unit"]}}, molecule.seq, 32, 128)
            if label is None or label != int(row["derived_label"]) or label != int(molecule.amp):
                raise ValueError(f"Primary MIC label cannot be released: {name}")
            derived.add(label)
            assay_rows.append({**row, "source_id": source_id, "primary_peptide_name": name,
                               "sequence": molecule.seq, "primary_file": PREFIX + source[0],
                               "primary_file_sha256": source[1], "primary_locations": source[3],
                               "primary_method_conditions": source[5], "condition_limitations": source[6],
                               "raw_value_unit_target_rechecked": True, "decision": "passed_primary_evidence"})
        if len(derived) != 1:
            raise ValueError("Unresolved within-molecule MIC labels")
        molecule_rows.append({"sample_id": molecule.sample_id, "sequence": molecule.seq, "source_id": source_id,
                              "primary_peptide_name": name, "primary_file": PREFIX + source[0],
                              "primary_file_sha256": source[1], "primary_locations": source[3],
                              "molecular_form": "linear canonical sequence with free amino and carboxyl termini",
                              "molecular_evidence": source[4], "condition_limitations": source[6],
                              "derived_label": int(molecule.amp), "observations_rechecked": len(selected),
                              "decision": "passed_primary_evidence", "human_reviewer_signoff": "not_claimed"})
    # Table 5 has additional baseline checks of the same EtCec3 acid molecule, with no conflicting class.
    # They do not create a new molecule or a new study, and combinations are excluded by endpoint.
    supporting = pd.DataFrame([
        {"source_id": "hirsch2020", "primary_location": "Table 5 EtCec3-OH without colistin",
         "target": target, "raw_mic": ">1024", "raw_unit": "µg/mL", "derived_label": 0,
         "role": "supporting_same_molecule_consistency_not_additional_training_sample"}
        for target in ("Escherichia coli ATCC 25922", "Escherichia coli RKI 131/08")
    ])
    output.mkdir(parents=True)
    pd.DataFrame(source_rows).to_csv(output / "source_review.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(molecule_rows).to_csv(output / "molecule_evidence_review.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(assay_rows).to_csv(output / "assay_evidence_review.csv", index=False, encoding="utf-8-sig")
    supporting.to_csv(output / "supporting_endpoint_review.csv", index=False, encoding="utf-8-sig")
    (output / "report.md").write_text(
        "# 固定三折候选的完整原始证据释放复核\n\n"
        "15 条分子、22 条冻结 MIC 已逐条对应七个原始测定研究的序列、游离酸形式、菌株、原值和单位。"
        "PDF 表格/结构图作第二遍目视核对，XML 表格与方法直接核查；另取得 Okimura 引用的 Goto 1990 MIC 方法，"
        "共八份原始文档，全部原文件和图像以 SHA-256 绑定。数据库类别和模型输出没有参与标签。\n\n"
        "每条 MIC 重新按原 32/128 µg/mL 规则推导；全部标签一致，无空档或相反标签。"
        "原 15 条分子与 22 条 MIC 的选择不变，使用已独立重算通过的固定三折及 0.40 全员隔离。"
        "Hirsch Table 5 的两个无 colistin 基线同属 EtCec3-OH，均 >1024 µg/mL，与冻结标签一致，"
        "单列为补充一致性证据；含抗生素混合、酰胺端和群体 MIC50/MIC90 均不替代当前端点。\n\n"
        "条件缺失如实保留：Sharma 后续 LB 培养时间/重复数及 Cheng MIC 重复次数未报告；"
        "Okimura 引用方法的条件与文章本身报告区分，不能把标准条件写成现场实验观察。"
        "此复核仅释放本地小样本探索的证据门禁，不宣称独立人工审稿、正式结果、临床效用或投稿许可，"
        "也不授予原论文文件再次发布的权利。15 条分子各验证折仅 1–2 条阳性。\n\n"
        "证据状态 passed_for_local_exploratory_training_protocol_review；训练仍需另行冻结协议和入口。\n",
        encoding="utf-8")
    result = {"status": "passed_for_local_exploratory_training_protocol_review", "generated_at": utc_now(),
              "audit_protocol_id": "protocol-mic-06", "cohort_version": COHORT.name,
              "cohort_manifest_sha256": sha256(COHORT / "manifest.json"),
              "full_release_review_complete": True, "molecules_evidence_approved": 15,
              "observations_evidence_approved": 22, "primary_measurement_studies": 7,
              "referenced_method_documents": 1, "supporting_baseline_checks": 2,
              "primary_review_mode": "agent_second_pass_primary_source_review_with_independent_arithmetic_validation",
              "independent_human_review_claimed": False, "scope": "local small-sample exploratory training protocol review only",
              "candidate_selection_changed": False, "model_performance_used": False,
              "records_released_for_training": 0, "training_started": False,
              "script_sha256": sha256(Path(__file__)), "inputs": inputs,
              "outputs": {p.name: sha256(p) for p in sorted(output.iterdir()) if p.is_file()}}
    write_json(output / "manifest.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    result = review(parser.parse_args().output)
    print(json.dumps({k: result[k] for k in ("status", "generated_at", "molecules_evidence_approved",
                                            "observations_evidence_approved", "records_released_for_training")}, indent=2))
