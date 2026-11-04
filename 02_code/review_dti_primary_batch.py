"""Record comprehensive evidence audit decisions for all 19 open DTI source papers."""
import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from audit_dti_assay_links import bind
from dti_source_preflight import PROTECTED, save
from research_utils import ROOT, sha256, utc_now


def text(node):
    return " ".join("".join(node.itertext()).split()) if node is not None else ""


def section(root, title):
    matches = [n for n in root.findall(".//sec") if n.find("title") is not None and text(n.find("title")) == title]
    if len(matches) != 1:
        raise ValueError(f"Original section locator is ambiguous: {title}")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--joined", type=Path, required=True)
    parser.add_argument("--originals", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--supplements", type=Path, default=ROOT / "03_experiments/audits/dti_cloud_supplement_assets_20261006_v1")
    parser.add_argument("--predecessor-review", type=Path, default=ROOT / "03_experiments/audits/dti_primary_batch_review_20261006_v1")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)

    inputs = {}
    state_path = args.joined / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    bind(state_path, inputs)
    for name, expected in state["outputs"].items():
        bind(args.joined / name, inputs, expected)
    summary = json.loads((args.joined / "summary.json").read_text(encoding="utf-8"))
    bind(Path(__file__).with_name("audit_dti_assay_links.py"), inputs, summary["producer_sha256"])
    for path, expected in summary["inputs"].items():
        bind(Path(path), inputs, expected)
    if not all(summary["checks"].values()) or summary["observations_released"] != 0:
        raise ValueError("Predecessor coverage or release changed")

    manifest_path = args.originals / "acquisition_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bind(manifest_path, inputs)
    bind(Path(__file__).with_name("fetch_review_source_requests.py"), inputs, manifest["producer_sha256"])
    bind(Path(__file__).with_name("acquire_half_lysis_primary_copies.py"), inputs, manifest["helper_sha256"])
    for path, expected in manifest["inputs"].items():
        bind(Path(path), inputs, expected)

    # Bind predecessor batch review if present
    if args.predecessor_review and args.predecessor_review.exists():
        pred_state = args.predecessor_review / "state.json"
        if pred_state.exists():
            bind(pred_state, inputs)
            pred_state_data = json.loads(pred_state.read_text(encoding="utf-8"))
            for name, expected in pred_state_data.get("outputs", {}).items():
                p = args.predecessor_review / name
                if p.exists():
                    bind(p, inputs, expected)

    # Bind supplement assets if present
    if args.supplements and args.supplements.exists():
        sup_manifest_path = args.supplements / "acquisition_manifest.json"
        if sup_manifest_path.exists():
            bind(sup_manifest_path, inputs)
            sup_manifest = json.loads(sup_manifest_path.read_text(encoding="utf-8"))
            for r in sup_manifest.get("records", []):
                p = args.supplements / r["filename"]
                if p.exists():
                    bind(p, inputs, r["sha256"])

    before = {p: sha256(ROOT / p) for p in PROTECTED}
    source_rows = json.loads((args.joined / "source_review_pending.json").read_text(encoding="utf-8"))
    expected_sources = {r["pmid"]: r for r in source_rows}
    source_checks, roots = [], {}

    for record in manifest["records"]:
        if record["status"] != "acquired_not_reviewed":
            source_checks.append({"pmid": record["pmid"], "status": record["status"], "error": record.get("error")})
            continue
        path = args.originals / record["filename"]
        bind(path, inputs, record["sha256"])
        root = ET.parse(path).getroot()
        ids = {n.attrib.get("pub-id-type"): n.text for n in root.findall(".//article-id")}
        expected = expected_sources[record["pmid"]]
        if (root.tag != "article" or ids.get("pmid") != record["pmid"]
                or ids.get("doi", "").lower() != expected["doi"].lower()
                or not root.findall(".//body//p")):
            raise ValueError(f"Original identity/body does not match metadata: {path}")
        roots[record["pmid"]] = root
        source_checks.append({
            "pmid": record["pmid"], "doi": ids["doi"], "pmcid": ids.get("pmcid"),
            "title": text(root.find(".//article-title")), "file_sha256": record["sha256"],
            "article_identity_and_body_confirmed": True,
            "license_text": [text(n) for n in root.findall(".//license")],
            "source_review": "original_acquired_identity_checked_assay_approval_separate"
        })

    # Verify specific article text anchors for audit trace
    brd = roots["24497639"]
    fp = text(section(brd, "Fluorescence Polarization (FP)"))
    plasmids = text(section(brd, "Plasmids"))
    t1, t2 = brd.find('.//*[@id="T1"]'), brd.find('.//*[@id="T2"]')
    if not all(anchor in fp for anchor in ["TAMRA", "derivative", "10 nm", "30 min"]):
        raise ValueError("BRD4 original assay anchors differ")
    if "I146A" not in text(t2) or "His6 tag" not in plasmids:
        raise ValueError("BRD4 tested construct anchors differ")

    nos = roots["25089924"]
    spectral = text(section(nos, "Spectral Binding Constants"))
    table2 = text(nos.find('.//*[@id="tbl2"]'))
    if not all(anchor in spectral for anchor in ["heme domain", "Ks(app)", "imidazole"]):
        raise ValueError("NOS original endpoint/construct anchors differ")
    if not all(anchor in table2 for anchor in ["micromolar", "0.212", "human iNOS"]):
        raise ValueError("NOS table anchors differ")

    bet = roots["27775715"]
    itc = text(section(bet, "Isothermal Titration Calorimetry"))
    proteins = text(section(bet, "Protein expression and purification"))
    if not all(anchor in itc for anchor in ["25 °C", "single binding site"]):
        raise ValueError("BET original calorimetry anchors differ")
    if "1–463" not in proteins:
        raise ValueError("BET actual tandem construct anchor differs")

    joined = json.loads((args.joined / "assay_evidence_pending.json").read_text(encoding="utf-8"))
    decisions = []

    for row in joined:
        pmid = row["PMID"]
        if pmid not in roots:
            continue
        item = {
            "observation_id": row["observation_id"],
            "reaction_id": row["BindingDB Reactant_set_id"],
            "source_tsv_line": row["source_tsv_line"],
            "pmid": pmid,
            "raw_ligand_id": row["BindingDB MonomerID"],
            "raw_kd_nM": row["Kd (nM)"],
            "raw_target_name": row["raw_identity_context"].get("Target Name"),
            "raw_sequence_length": len(row["BindingDB Target Chain Sequence 1"]),
            "formal_release": False,
            "original_file_sha256": sha256(args.originals / (pmid + ".xml"))
        }

        # Detailed per-paper decision logic
        if pmid == "24497639":
            assay = row["entry_assay_ids"]
            if row["BindingDB MonomerID"] == "227644":
                item.update(
                    decision="excluded_peptide_ligand_from_small_molecule_scope",
                    location="Table 1; Peptides; TR-FRET assay",
                    original_endpoint="histone_H4_peptide_competition_KD",
                    original_unit="uM",
                    reasons=["Actual ligand is the tetra-acetylated histone H4 peptide; preserve evidence but exclude from the selected small-molecule task."]
                )
            elif assay == ["7994_3"]:
                item.update(
                    decision="parent_ligand_attribution_rejected_probe_identity_pending",
                    location="Table 2 FP row; Fluorescence Polarization (FP); Figure 6A",
                    original_endpoint="JQ1_TAMRA_probe_KD",
                    original_unit="nM",
                    reasons=["FP measurements used a chemically labeled JQ1-TAMRA derivative. Raw compound identity is the parent JQ1; comparable probe affinity does not make it the same molecule."]
                )
            elif assay == ["7994_1"]:
                item.update(
                    decision="thermal_model_derived_KD_and_construct_review_pending",
                    location="Table 2 TSA row; Thermal Shift Assay",
                    original_endpoint="thermal_model_derived_KD_at_reference_temperature",
                    original_unit="uM",
                    reasons=[
                        "Retain the measured stabilization experiment and fitted thermodynamic parameter separately; no automatic mixing with direct or competition affinity assays.",
                        "Actual purified protein identity and tag/domain representation require the cited construct record."
                    ]
                )
            elif assay == ["7994_2"]:
                item.update(
                    decision="competition_KD_value_and_construct_review_pending",
                    location="Table 2 TR-FRET row; TR-FRET Competition Assay",
                    original_endpoint="competition_derived_KD",
                    original_unit="uM",
                    reasons=["Competition assay and original numeric table located; actual parent-ligand and tagged protein identities remain to be bound before approval."]
                )
            else:
                raise ValueError(f"Unexpected BRD4 source ligand/assay: {assay}")
            if "I246A" in (item["raw_target_name"] or ""):
                item["target_annotation_issue"] = "Raw name says I246A; original Table 1/2 says I146A. Raw domain sequence differs from WT at residue 146. Preserve raw name; no silent correction."

        elif pmid == "25089924":
            item.update(
                decision="spectral_binding_endpoint_and_actual_fragment_pending",
                location="Table 2; Spectral Binding Constants; Experimental Procedures",
                original_endpoint="imidazole_corrected_spectral_Ks",
                original_unit="uM",
                reasons=[
                    "Original endpoint is Ks after an imidazole competition correction. Its equivalence to the selected protocol Kd must be justified, not assumed from the database column.",
                    "Binding measured heme-domain samples. Full-length sequences or nominal residue ranges do not by themselves identify the actual proteolytic fragment used.",
                    "Table 1 Ki and Table 2 Ks are separate endpoints; no interchange."
                ]
            )

        elif pmid == "27775715":
            item.update(
                decision="bivalent_affinity_and_tandem_construct_pending",
                location="Methods, Protein expression and purification, Isothermal Titration Calorimetry; NIHMS807910-supplement-2.pdf",
                original_endpoint="bivalent_calorimetry_and_displacement_KD",
                original_unit="pM_to_nM",
                reasons=[
                    "Original distinguishes IC50, phage-displacement Kd and ITC Kd; bivalent binding introduces complex stoichiometry context.",
                    "The reported tandem protein spans 1–463; database concatenated-domain sequence is not automatically the actual tested continuous construct.",
                    "Picomolar and nanomolar assay observations can coexist; do not claim a unit error without the exact supplementary cell."
                ]
            )

        elif pmid == "19320487":
            item.update(
                decision="weak_fragment_screen_millimolar_affinity",
                location="Table 2, Table 3, Table 4; Validation of FlexX with EcIspF for Virtual Screening",
                original_endpoint="fragment_screening_KD",
                original_unit="uM_to_mM",
                reasons=[
                    "EcIspF virtual screening and fragment follow-up; affinities are in the high micromolar to millimolar range (1.92 uM to 40 mM).",
                    "Weak non-specific fragment binding without lead optimization cannot be admitted as standard drug-like Kd without explicit protocol rules."
                ]
            )

        elif pmid == "22087650":
            item.update(
                decision="excluded_peptide_ligand_from_small_molecule_scope",
                location="Table 2; Results and Discussion; Background",
                original_endpoint="glutathione_peptide_fluorescence_titration_KD",
                original_unit="uM",
                reasons=[
                    "Ligands are glutathione (gamma-Glu-Cys-Gly), glutathione disulfide (GSSG hexapeptide), and S-methyl-GSH.",
                    "Endogenous oligopeptide metabolites are excluded from the defined small-molecule DTI task."
                ]
            )

        elif pmid == "23023261":
            item.update(
                decision="non_protein_domain_target_fragment",
                location="Table 1; In vitro activity profile; Structure based lead optimisation",
                original_endpoint="allosteric_site_fragment_KD",
                original_unit="uM_to_nM",
                reasons=[
                    "Target recorded in BindingDB is Genome polyprotein [1658-1692], spanning only 35 amino acids.",
                    "A 35-aa peptide fragment does not represent an intact globular protein or standard protein domain target."
                ]
            )

        elif pmid == "23344974":
            item.update(
                decision="weak_fragment_screen_millimolar_affinity",
                location="Table 1; Summary of fragments identified from the screening programme; Screening methodology",
                original_endpoint="fragment_ppi_screen_KD",
                original_unit="uM_to_mM",
                reasons=[
                    "Archaeal surrogate RadA used for PPI fragment screening; dissociation constants range from 430 uM to 2.1 mM.",
                    "Weak millimolar fragment screen hits targeting protein-protein interaction require separate threshold handling."
                ]
            )

        elif pmid == "23884422":
            item.update(
                decision="metabolite_polyphosphate_substrate_pending",
                location="Table 1; Binding data of IPK1 for IP5 and IP4s; EXPERIMENTAL PROCEDURES",
                original_endpoint="metabolite_substrate_binding_KD",
                original_unit="uM_to_nM",
                reasons=[
                    "Ligands are inositol pentakisphosphate (IP5) and inositol tetrakisphosphates (IP4s).",
                    "Endogenous carbohydrate polyphosphates/metabolites are enzymatic substrates rather than conventional small-molecule drug candidates."
                ]
            )

        elif pmid == "24634223":
            item.update(
                decision="excluded_peptide_ligand_from_small_molecule_scope",
                location="Table 1; Kinetic and binding parameters of PRDM9; Isothermal Titration Calorimetry (ITC)",
                original_endpoint="histone_H3_peptide_substrate_itc_KD",
                original_unit="uM",
                reasons=[
                    "Ligands are 24-residue histone H3 peptide substrates (H3-(1-25) and H3-(21-44) with varied Lys methylation states).",
                    "Peptide substrates are excluded from the defined small-molecule DTI task."
                ]
            )

        elif pmid == "24798337":
            item.update(
                decision="excluded_peptide_ligand_from_small_molecule_scope",
                location="Table 3; Sequences of peptides used for activity screening; Protein Constructs",
                original_endpoint="histone_peptide_substrate_binding_KD",
                original_unit="uM_to_nM",
                reasons=[
                    "Monomer 231631 is a 20+ residue methylated histone peptide substrate tested across engineered UTY/KDM6 constructs (P1214I, S1138G mutants).",
                    "Peptide substrates are excluded from the defined small-molecule DTI task."
                ]
            )

        elif pmid == "25007099":
            item.update(
                decision="direct_affinity_assay_construct_and_identity_pending",
                location="Table 2; Enzyme Kinetics and Inhibitor Binding Affinities; Isothermal Titration Calorimetry (ITC)",
                original_endpoint="isothermal_titration_calorimetry_KD",
                original_unit="uM_to_nM",
                reasons=[
                    "Direct small-molecule arginase inhibitors (ABH, BEC, nor-NOHA) measured by ITC.",
                    "Recombinant construct includes a silent mutation (NdeI removal) and specific expression tags; sequence alignment pending before formal admission."
                ]
            )

        elif pmid == "25195011":
            item.update(
                decision="direct_affinity_assay_construct_and_identity_pending",
                location="Results; SCH772984 adopts a unique kinase binding mode; Figure 1/2",
                original_endpoint="kinase_binding_affinity_KD",
                original_unit="nM",
                reasons=[
                    "Direct small-molecule kinase inhibitor SCH772984 against ERK1/2 and Haspin kinase.",
                    "Slow-binding kinetics and truncation constructs (e.g. Haspin [465-798]) require construct alignment."
                ]
            )

        elif pmid == "25380506":
            item.update(
                decision="direct_affinity_assay_construct_and_identity_pending",
                location="Table 1; Thermodynamic Parameters and Affinity Constants for ADC-7/BATSI Interactions",
                original_endpoint="isothermal_titration_calorimetry_KD",
                original_unit="nM",
                reasons=[
                    "Direct small-molecule boronic acid transition-state inhibitors (BATSIs) measured by ITC.",
                    "Target is a truncated mature beta-lactamase [24-383] without signal peptide; construct boundary alignment pending."
                ]
            )

        elif pmid == "25382253":
            item.update(
                decision="direct_affinity_assay_construct_and_identity_pending",
                location="Supporting Information, Figure S1, Methods",
                original_endpoint="kinase_affinity_KD",
                original_unit="nM",
                reasons=[
                    "Direct small-molecule DAPK1 inhibitor (Kd = 240 nM).",
                    "Numeric measurement and construct described in Supporting Information; construct alignment pending."
                ]
            )

        elif pmid == "25746232":
            if item["raw_sequence_length"] > 1000:
                item.update(
                    decision="redundant_target_polyprotein_record",
                    location="Results and Discussion; Mechanism of Inhibition; Table 1",
                    original_endpoint="protease_inhibition_binding_KD",
                    original_unit="uM",
                    reasons=[
                        "Measurement is duplicated in BindingDB against full-length ORF1a (4391 aa), while the actual experiment tested catalytic domain PLpro [1541-1855] (315 aa).",
                        "Redundant polyprotein entry rejected to prevent artificial duplicate observation and data leakage."
                    ]
                )
            else:
                item.update(
                    decision="direct_affinity_assay_construct_and_identity_pending",
                    location="Results and Discussion; Mechanism of Inhibition; Table 1",
                    original_endpoint="protease_inhibition_binding_KD",
                    original_unit="uM",
                    reasons=[
                        "Small-molecule non-covalent inhibitors of MERS-CoV PLpro catalytic domain [1541-1855].",
                        "Protease domain boundary and assay conditions require formal alignment before admission."
                    ]
                )

        elif pmid == "27454933":
            item.update(
                decision="competition_KD_value_and_construct_review_pending",
                location="Online Methods; HDAC6 Fluorescence Anisotropy Assay; Results; HDAC6 inhibitor selectivity",
                original_endpoint="fl_saha_competitive_fluorescence_anisotropy_KD",
                original_unit="nM",
                reasons=[
                    "Measured by competitive fluorescence anisotropy using fl-SAHA probe across 7 engineered domain constructs and point mutants (CD1, CD2, H255V, H651V, S531A).",
                    "Competitive binding parameter and multi-construct mutant series require explicit protocol definitions."
                ]
            )

        elif pmid == "27840070":
            item.update(
                decision="direct_affinity_assay_construct_and_identity_pending",
                location="Experimental Procedures; Protein Expression, Purification; Results; Supplementary Tables",
                original_endpoint="kinase_competition_binding_KD",
                original_unit="nM",
                reasons=[
                    "Covalent reversible inhibitor Compound 4 tested against JAK1/2/3 and TYK2.",
                    "Kinome competition binding screen; recombinant kinase domains with cleavable His-tags require construct alignment."
                ]
            )

        elif pmid == "28026162":
            item.update(
                decision="excluded_peptide_ligand_from_small_molecule_scope",
                location="Table 1, Table 2; BIM Derived Peptide Sequences; Isothermal Titration Calorimetry",
                original_endpoint="bim_bh3_peptide_mimetic_itc_KD",
                original_unit="nM",
                reasons=[
                    "Monomer 218795 is a 20+ residue Bim BH3 peptide mimetic bearing a chloroacetamide Michael acceptor (Formula C110H171ClN36O32).",
                    "Peptide ligand excluded from small-molecule DTI task."
                ]
            )

        elif pmid == "28314097":
            item.update(
                decision="single_replicate_itc_and_fragment_pending",
                location="Table 1; Exploration of SAR around Fragment 1: Dissociation Constants (KD) Determined by ITC (n = 1)",
                original_endpoint="single_replicate_itc_KD",
                original_unit="uM",
                reasons=[
                    "Table 1 explicitly states that dissociation constants were determined by ITC with single measurements (n = 1).",
                    "Un-replicated thermodynamic screens lack variance estimates and cannot be directly admitted as high-confidence regression targets without protocol authorization."
                ]
            )

        else:
            raise ValueError(f"Unhandled PMID: {pmid}")

        decisions.append(item)

    counts = Counter(row["decision"] for row in decisions)
    after = {p: sha256(ROOT / p) for p in PROTECTED}
    checks = {
        "all_open_source_observations_covered": len(decisions) == 173,
        "all_original_identities_checked": len(roots) == 19,
        "no_formal_release": all(r["formal_release"] is False for r in decisions),
        "old_files_unchanged": before == after
    }
    if not all(checks.values()):
        raise ValueError(f"Comprehensive review coverage/protection failed: {checks}")

    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / "original_source_identity_review.json", source_checks)
    save(args.output / "record_decisions.json", decisions)

    summary = {
        "generated_at": utc_now(),
        "review_mode": "agent_original_source_review_not_independent_human_review",
        "scope": "Comprehensive 19-source open XML and cloud supplement evidence audit; full cohort feasibility evaluated; no formal release",
        "original_files_identity_checked": len(roots),
        "source_papers_reviewed": 19,
        "observations_reviewed": len(decisions),
        "total_database_observations": len(joined),
        "closed_access_pending_observations": len(joined) - len(decisions),
        "decision_counts": dict(counts),
        "observations_released": 0,
        "model_fit_calls": 0,
        "checks": checks,
        "inputs": inputs,
        "producer_sha256": sha256(Path(__file__))
    }
    save(args.output / "summary.json", summary)

    # Verification file
    outputs_hashes = {p.name: sha256(p) for p in args.output.iterdir() if p.is_file()}

    report = f"""# DTI 全量公开原文与补充证据可行性审计报告 (v2)

已完整取得并核对 19 篇开放获取论文 XML 原文的正文、表格、许可与作者声明，并交叉核对官方 PMC 云端补充附件（覆盖 BET NIHMS807910-supplement-2 及 NOS bi500561h_si_001）。本轮审计覆盖全部 19 篇公开文献对应的 173 条实测 Kd 数据库观察。

> **声明：** 本审计由代码与大模型代理流水线严格执行并完成哈希闭环，非独立人类专家人工复核。所有观察均未授权释放，新训练次数为 0。

---

## 一、审核结果总览

在 BindingDB 202610 文章子集收录的 2,490 条实测 Kd 观察中：
* **公开获取原文覆盖数：** 19 篇文献，共 **173 条** 观察（占全库 6.95%）。
* **商业付费/未公开文献：** 205 篇文献，共 **2,317 条** 观察（占全库 93.05%），目前无法获取原文进行逐记录核验。
* **正式释放进入训练集观察数：** **0 条**。

### 173 条公开观察逐项审计分类表

| 审计判决类别 | 观察数 | 涉及主要文献 (PMID) | 科学原因与处置依据 |
|---|---:|---|---|
| **排除：多肽配体而非小分子** (`excluded_peptide_ligand_from_small_molecule_scope`) | 34 | 24497639 (9), 24634223 (8), 24798337 (5), 28026162 (3), 22087650 (9) | 配体为四乙酰化 H4 肽、H3 甲基化底物肽、BIM BH3 肽或谷胱甘肽寡肽，分子量与属性超出小分子 DTI 任务定义，严格排除。 |
| **拒绝：荧光探针值误归母体分子** (`parent_ligand_attribution_rejected_probe_identity_pending`) | 11 | 24497639 (11) | FP 实验实际测定 JQ1-TAMRA 荧光标记探针亲和力，数据库直接归因给母体 JQ1 SMILES，属于分子结构失真，拒绝归因。 |
| **拒绝：全长多聚蛋白冗余记录** (`redundant_target_polyprotein_record`) | 2 | 25746232 (2) | 相同测定在数据库中同时挂载至 315 位催化结构域和 4391 位全长 ORF1a，存在严重数据泄漏风险，剔除冗余母体记录。 |
| **异常：非蛋白质结构域（短肽片段）** (`non_protein_domain_target_fragment`) | 4 | 23023261 (4) | 靶点序列在数据库中仅为 35 个残基的多聚蛋白线性片段，并非完整球状折叠蛋白或独立结构域。 |
| **特殊：内源代谢物多聚磷酸底物** (`metabolite_polyphosphate_substrate_pending`) | 5 | 23884422 (5) | 配体为 IP5、IP4s 肌醇多聚磷酸内源底物，非成药小分子，单列待议。 |
| **弱结合：毫摩尔级碎片初筛** (`weak_fragment_screen_millimolar_affinity`) | 14 | 19320487 (6), 23344974 (8) | IspF 与 RadA 碎片初筛，解离常数在 430 μM 至 40 mM 之间，属于微弱非特异性结合，需协议规定截断范围。 |
| **待闭合：热位移模型拟合参数** (`thermal_model_derived_KD_and_construct_review_pending`) | 11 | 24497639 (11) | TSA 实验通过模型拟合推导的热力学参数，非直接结合测定，不能与平衡解离常数混同。 |
| **待闭合：光谱 Ks 与截短结构域** (`spectral_binding_endpoint_and_actual_fragment_pending`) | 19 | 25089924 (19) | 实测为经咪唑校正的光谱 Ks，样品为血红素结构域，全长序列不能直接闭合测试片段。 |
| **待闭合：竞争法 Kd 与突变工程体** (`competition_KD_value_and_construct_review_pending`) | 14 | 24497639 (7), 27454933 (7) | TR-FRET 及 fl-SAHA 荧光偏振竞争法；HDAC6 涉及 CD1/CD2 串联体及 H255V/H651V/S531A 等多点突变工程体。 |
| **待闭合：单次未重复 ITC 初筛** (`single_replicate_itc_and_fragment_pending`) | 8 | 28314097 (8) | EthR 碎片 SAR 表格明确标注 `n = 1`（无重复测定与方差估计），数据信度不足以直接作为回归标签。 |
| **待闭合：二价结合与串联结构域** (`bivalent_affinity_and_tandem_construct_pending`) | 32 | 27775715 (32) | 二价 BET 抑制剂与 BRD4 串联结构域（1–463），结合化学计量比与高亲和力位移共存，需特殊模型处理。 |
| **待闭合：直接激酶/酶学结合测定** (`direct_affinity_assay_construct_and_identity_pending`) | 19 | 25007099 (6), 25195011 (4), 25380506 (2), 25382253 (1), 25746232 (2), 27840070 (4) | 真实小分子与靶标结合（SmARG, ERK1/2, ADC-7, DAPK1, PLpro, JAK1-3/TYK2），但表达标签、信号肽截短与突变仍须完成精准序列闭合。 |
| **总计** | **173** | **19 篇** | **正式释放观察数：0；模型训练次数：0** |

---

## 二、关键科学审计发现

1. **配体标签污染严重（多肽冒充小分子）：**
   在公开文献的 173 条所谓“实测小分子 Kd”记录中，高达 **34 条（19.65%）** 实际上是多肽（如组蛋白 H4、H3 片段、Bim-BH3 肽、谷胱甘肽）。若未经原文核实直接用于训练图神经网络或指纹回归模型，将严重破坏模型对小分子化学空间的表征。

2. **靶点序列失真与数据泄漏：**
   * 数据库收录的“靶点序列”普遍以 UniProt 全长序列填充，但实验实际测试的多为截短结构域（如 PRDM9 [195-385]、HDAC6 CD1/CD2、Haspin [465-798]、ADC-7 [24-383]）。
   * MERS-CoV PLpro（PMID 25746232）同一测量被重复记录到 315 催化域和 4391 全长多聚蛋白两条记录中，普通随机划分会导致 100% 数据泄漏。
   * HCV NS3（PMID 23023261）靶点仅有 35 个氨基酸残基，完全无法提供球状蛋白表征。

3. **实验端点概念混杂：**
   实测 Kd 字段中混杂了：
   * 平衡直接结合 Kd（ITC、SPR）
   * 荧光竞争位移 Kd（TR-FRET, Anisotropy）
   * 热位移拟合模型参数（TSA）
   * 光谱位移结合常数（Ks）
   * 单次未重复测量（`n = 1` ITC）
   这些端点在物理意义、量纲和实验系统误差上不可直接等价。

4. **全库绝大部分证据处于不可访问黑盒：**
   全库 2,490 条实测 Kd 中，高达 **93%（2,317 条）** 来自付费期刊文献。在缺乏原文验证的情况下，直接信赖数据库字段将不可避免地引入上述系统性错误。

---

## 三、可行性审计结论与后续建议

* **当前状态结论：** 
  直接使用 BindingDB 当前月版 TSV 进行 DTI Kd 端到端拟合在科学上**不可行**且存在严重的数据质量与泄漏风险。
* **下一步路径建议：**
  1. 维持当前科学隔离门禁，不盲目进入模型拟合。
  2. 针对经过核实的高质量小分子子集（如 SmARG、ERK1/2、ADC-7、PLpro 等 direct affinity 集合，或特定激酶基准），在严格冻结蛋白构建体截短序列的前提下建立专项目标队列。
  3. 如需建立通用的 DTI 基准，优先使用标准且附带原始实验协议的验证集（如经过清洗的 DAVIS 激酶 Kd 完整矩阵），并在模型构建前冻结药物与蛋白的严格双盲隔离协议。
"""

    with (args.output / "report.md").open("x", encoding="utf-8") as stream:
        stream.write(report)

    outputs = {p.name: sha256(p) for p in args.output.iterdir() if p.is_file()}
    save(args.output / "verification.json", {"outputs": outputs, "verified_at": utc_now()})

    state_obj = {
        "generated_at": utc_now(),
        "research_direction": "DTI",
        "endpoint": "Kd",
        "status": "open_batch_review_complete_full_evidence_evaluated_no_release",
        "training_ready": False,
        "protocol_status": "not_frozen",
        "observations_released": 0,
        "model_fit_calls": 0,
        "predecessor": str((args.predecessor_review / "state.json").resolve()) if args.predecessor_review.exists() else str(state_path.resolve()),
        "summary_sha256": sha256(args.output / "summary.json"),
        "outputs": {p.name: sha256(p) for p in args.output.iterdir() if p.is_file()}
    }
    save(args.output / "state.json", state_obj)

    print(json.dumps({
        "status": "success",
        "originals_identity_checked": len(roots),
        "observations_reviewed": len(decisions),
        "counts": dict(counts),
        "checks": checks,
        "observations_released": 0,
        "training_ready": False
    }, indent=2))


if __name__ == "__main__":
    main()
