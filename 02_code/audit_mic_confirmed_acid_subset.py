"""Re-audit only locally confirmed free-acid candidates; never authorize training."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd
from pypdf import PdfReader
from sklearn.model_selection import StratifiedGroupKFold

from audit_mic_reviewed_subset_hirsch import DisjointSet
from audit_mic_reviewed_subset_ludwig import verify
from public_data import bounds, measurement_label
from research_data import sequence_identity
from research_utils import ROOT, sha256, utc_now, write_json

BASE = ROOT / "03_experiments/audits/mic_reviewed_subset_groups_20261002_v3"
QUEUE = ROOT / "03_experiments/audits/mic_candidate_release_review_20261002_v1"
RAW = ROOT / "03_experiments/audits/mic_primary_candidate_sources_20261002_v1"
PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-01.json"
OLD_PAPERS = [ROOT / f"03_experiments/audits/{name}" for name in (
    "mic_primary_review_pmid33790103_20261002_v2",
    "mic_primary_review_pmid32344933_20261002_v2",
    "mic_primary_review_pmid35735615_20261002_v1")]
ACIDS = {
    "MSI-103-COOH": "KIAGKIAKIAGKIAKIAGKIA",
    "PGLa-COOH": "GMASKAGAIAGKIAKVALKAL",
    "MAP-COOH": "KLALKLALKALKAALKLA",
}


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def original_controls() -> tuple[list[dict], list[dict]]:
    thesis = PdfReader(RAW / "tiltak2009_primary_thesis.pdf")
    form = compact(thesis.pages[45].extract_text() or "")
    mic = compact(thesis.pages[46].extract_text() or "")
    methods = compact(" ".join(thesis.pages[i].extract_text() or "" for i in (29, 31, 32)))
    if (len(thesis.pages) != 117 or "DenizTiltak" not in compact(thesis.pages[0].extract_text() or "")
            or "freierCOOH" not in form.replace("freiemCOOH", "freierCOOH")
            or "Wang-HarzanstellevonRink-Harz" not in methods
            or "salzfreiemLB-Medium" not in methods or "37°CüberNacht" not in methods):
        raise ValueError("Original thesis identity, free-acid synthesis, or assay conditions changed.")
    for name, seq in ACIDS.items():
        if name + seq not in form:
            raise ValueError(f"Original thesis Table 4.1 does not establish the free acid: {name}")
    expected = {
        "Escherichia coli DSM 1103": ("E.coliDSM110316>12888128>128", {"MSI-103-COOH": "8", "PGLa-COOH": ">128", "MAP-COOH": ">128"}),
        "Escherichia coli DH 5alpha": ("E.coliDH5", {"MSI-103-COOH": "16", "PGLa-COOH": ">128", "MAP-COOH": ">128"}),
    }
    if "8>1288168>128" not in mic:
        raise ValueError("Original thesis Table 4.2 DH 5alpha cells changed.")
    rows, reviews = [], []
    for target, (marker, values) in expected.items():
        if marker not in mic:
            raise ValueError(f"Original thesis Table 4.2 target or cells changed: {target}")
        for name, value in values.items():
            rows.append({"record_id": f"KIT1000012217:{name}", "sequence": ACIDS[name],
                         "paper_peptide_name": name, "target": target, "raw_mic": value,
                         "raw_unit": "µg/mL", "medium": "50 uL salt-free LB peptide dilution + 50 uL LB inoculum",
                         "method": "thesis section 3.2.2; overnight 37 C; majority of four wells visibly clear",
                         "assay_study_ids": "doi:10.1351/pac200779040717|doi:10.5445/IR/1000012217|kit:1000012217",
                         "primary_file": "tiltak2009_primary_thesis.pdf",
                         "primary_location": "PDF pp. 30, 32-33, 46-47; Tables 4.1/4.2",
                         "source_url": "https://publikationen.bibliothek.kit.edu/1000012217/923703"})
    cheng = PdfReader(RAW / "cheng2011_primary.pdf")
    table = compact(cheng.pages[2].extract_text() or "")
    cheng_methods = compact(" ".join(cheng.pages[i].extract_text() or "" for i in (1, 2, 3)))
    seq = "GLFDIVKKVVGAIGSL"
    # The PDF text layer encodes the > glyph as N. The saved page render was also checked.
    if (len(cheng.pages) != 12 or f"Aurein2.3-COOH{seq}-COOHN128N128N128" not in table
            or "E.coliUB1005" not in table or "18hat37°C" not in cheng_methods
            or "RinkorWangresin" not in cheng_methods):
        raise ValueError("Cheng Table 1 or synthesis/MIC methods changed.")
    rows.append({"record_id": "DOI10.1016.j.bbamem.2010.11.025:Aurein2.3-COOH", "sequence": seq,
                 "paper_peptide_name": "Aurein 2.3-COOH", "target": "Escherichia coli K12 UB1005",
                 "raw_mic": ">128", "raw_unit": "µg/mL", "medium": "Mueller-Hinton broth",
                 "method": "Methods 2.2.7; 90 uL culture + 10 uL peptide; 18 h 37 C; visible no growth; modal MIC",
                 "assay_study_ids": "doi:10.1016/j.bbamem.2010.11.025",
                 "primary_file": "cheng2011_primary.pdf", "primary_location": "PDF pp. 2-4; Table 1, Methods 2.2.1/2.2.7",
                 "source_url": "https://cmdr.ubc.ca/bobh/wp-content/uploads/2016/11/430.-Cheng-2011.pdf"})
    for name, seq in [*ACIDS.items(), ("Aurein 2.3-COOH", seq)]:
        reviews.append({"paper_peptide_name": name, "sequence": seq, "decision": "local_free_acid_fields_confirmed",
                        "basis": "explicit free-acid molecular identity and original E. coli MIC; text plus visual table check",
                        "training_release": False})
    # Review all selected negative-control leads, including the contradictory source.
    root = ElementTree.parse(RAW / "PMC9532841.xml").getroot()
    text = " ".join(root.itertext())
    if "Rink amide resin" not in text or "COOH" not in text:
        raise ValueError("The latarcin synthesis-versus-structure conflict changed; review again.")
    for name, seq in {"Ltc-3a": "SWKSMAKKLKEYMEKLKQRA", "Lt-MAP1": "LAKKLKEYLEKLV",
                      "Lt-MAP2": "LIKKLKEYLKKLI", "Lt-MAP3": "LAKKLAKYLKKAL"}.items():
        if seq not in text:
            raise ValueError(f"Latarcin sequence changed: {name}")
        reviews.append({"paper_peptide_name": name, "sequence": seq,
                        "decision": "withheld_molecular_form_conflict",
                        "basis": "PMID 36212827 Methods: Rink amide resin; Results: COOH; do not choose one description",
                        "training_release": False})
    return rows, reviews


def run(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite evidence selection: {output}")
    verify(BASE), verify(QUEUE)
    for paper in OLD_PAPERS:
        verify(paper)
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if (protocol["similarity"]["cutoff"] != 0.4 or protocol["validation"]["folds"] != 5
            or protocol["validation"]["seed"] != 42 or protocol["molecule_domain"]["backbone"] != "linear"
            or protocol["label_rule"]["positive_if_upper_bound_ug_ml_lte"] != 32
            or protocol["label_rule"]["negative_if_lower_bound_ug_ml_gte"] != 128):
        raise ValueError("Frozen scientific rules changed.")
    queue = pd.read_csv(QUEUE / "molecule_review_queue.csv")
    queue["selection_decision"] = "withheld_missing_primary_molecular_identity"
    selected_ids = queue.loc[queue.molecular_form_review.eq("primary_free_acid_confirmed"), "sample_id"]
    queue.loc[queue.sample_id.isin(selected_ids), "selection_decision"] = "local_fields_confirmed_not_training_released"
    # Confirmed C-terminal state alone does not establish the complete cysteine-containing assay molecule.
    mask = queue.sequence.eq("GAPKGCWTKSYPPKPCSGKR")
    queue.loc[mask, "pending_items"] = "PeNi12 non-amidated carboxyl end explicit in Discussion; assay disulfide/redox state unestablished"
    queue.loc[queue.primary_evidence_pmid.eq(29259134), "pending_items"] = (
        "Table 1 text/visual recheck complete; original supporting Dataset S3 synthesis mass evidence remains unavailable")
    queue.loc[queue.primary_evidence_pmid.eq(30658410), "pending_items"] = (
        "Original supplement Figure S2 confirms native PLP2 spectra; synthetic MIC isoform/terminal identity and cited assay conditions remain unestablished")
    queue.loc[queue.primary_evidence_pmid.eq(22467870), "pending_items"] = (
        "Native uncyclotide cystine state is not established as unmodified; public full-text APIs returned metadata only; no domain admission")
    molecules = pd.read_csv(BASE / "candidate_molecules.csv")
    observations = pd.read_csv(BASE / "candidate_observations.csv")
    molecules = molecules[molecules.sample_id.isin(selected_ids)].copy()
    molecules = molecules.drop(columns=["homology_component"], errors="ignore")
    observations = observations[observations.sample_id.isin(selected_ids)].copy()
    new_rows, reviews = original_controls()
    for record_id, assays in itertools.groupby(sorted(new_rows, key=lambda row: row["record_id"]), key=lambda row: row["record_id"]):
        assays = list(assays)
        seq = assays[0]["sequence"]
        sample_id = hashlib.sha256(seq.encode("ascii")).hexdigest()[:24]
        if seq in set(molecules.seq) or sample_id in set(molecules.sample_id):
            raise ValueError("New original controls duplicate an existing molecule; explicit merge review required.")
        labels = {measurement_label({"concentration": row["raw_mic"], "unit": {"name": row["raw_unit"]}}, seq, 32, 128) for row in assays}
        if len(labels) != 1 or None in labels:
            raise ValueError("Original control labels conflict or lie in the excluded threshold gap.")
        molecule = {column: "" for column in molecules.columns}
        molecule.update(sample_id=sample_id, seq=seq, amp=labels.pop(), record_ids=json.dumps([record_id]),
                        source_datasets="original_primary_source", study_ids=assays[0]["assay_study_ids"])
        molecules = pd.concat([molecules, pd.DataFrame([molecule])], ignore_index=True)
        for index, row in enumerate(assays):
            low, high = bounds(row["raw_mic"])
            observation = {column: "" for column in observations.columns}
            observation.update({key: row[key] for key in ("record_id", "target", "medium", "method", "raw_mic", "raw_unit", "assay_study_ids")})
            observation.update(sample_id=sample_id, source_dataset="original_primary_source", assay_index=index,
                               eligible=True, derived_label=molecule["amp"], normalized_low_ug_ml=low,
                               normalized_high_ug_ml=high, reference_resolution=row["primary_location"])
            observations = pd.concat([observations, pd.DataFrame([observation])], ignore_index=True)
    # Re-derive every label from the observation; never trust the retained binary fields alone.
    for row in observations.itertuples(index=False):
        seq = molecules.set_index("sample_id").loc[row.sample_id, "seq"]
        label = measurement_label({"concentration": row.raw_mic, "unit": {"name": row.raw_unit}}, seq, 32, 128)
        if label is None or label != int(row.derived_label):
            raise ValueError(f"Observation label cannot be reproduced: {row.record_id}")
    if observations.groupby("sample_id").derived_label.nunique().max() != 1:
        raise ValueError("Opposite observation labels remain for an exact molecule.")
    alphabet = set("ACDEFGHIKLMNPQRSTVWY")
    if (not molecules.seq.is_unique or not molecules.sample_id.is_unique
            or any(not 10 <= len(seq) <= 50 or set(seq) - alphabet for seq in molecules.seq)):
        raise ValueError("Duplicate, noncanonical, or out-of-domain molecule remains.")
    groups = DisjointSet(molecules.sample_id.tolist())
    pairs = []
    for a, b in itertools.combinations(molecules.itertuples(index=False), 2):
        identity = sequence_identity(a.seq, b.seq, identity_mode="alignment")
        pairs.append({"sample_id_a": a.sample_id, "sample_id_b": b.sample_id, "identity": identity,
                      "homology_edge": identity >= 0.4})
        if identity >= 0.4:
            groups.union(a.sample_id, b.sample_id)
    studies: dict[str, set[str]] = {}
    for row in observations.itertuples(index=False):
        for identifier in str(row.assay_study_ids).split("|"):
            if not identifier or identifier == "nan":
                raise ValueError("Missing primary study identity.")
            members = studies.setdefault(identifier, set())
            if members:
                groups.union(row.sample_id, next(iter(members)))
            members.add(row.sample_id)
    roots = sorted({groups.find(sample) for sample in molecules.sample_id})
    molecules["review_component"] = molecules.sample_id.map(lambda sample: roots.index(groups.find(sample)))
    components = molecules.groupby("review_component").agg(molecules=("sample_id", "size"), positives=("amp", "sum"))
    components["negatives"] = components.molecules - components.positives
    positive_groups, negative_groups = int(components.positives.gt(0).sum()), int(components.negatives.gt(0).sum())
    blockers = []
    for count, description in ((len(components), "total components"), (positive_groups, "positive-bearing components"), (negative_groups, "negative-bearing components")):
        if count < 5:
            blockers.append(f"{description}: {count} < 5; five validation folds with both classes are impossible.")
    assignments, folds = [], []
    # Fail before splitting when the necessary conditions cannot hold; do not search seeds.
    if not blockers:
        splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
        for fold, (train_indices, valid_indices) in enumerate(splitter.split(molecules.seq, molecules.amp, molecules.review_component)):
            train, valid = molecules.iloc[train_indices], molecules.iloc[valid_indices]
            both = set(train.amp) == {0, 1} and set(valid.amp) == {0, 1}
            folds.append({"fold": fold, "train_n": len(train), "validation_n": len(valid), "both_classes": both})
            assignments.extend({"sample_id": sample, "fold": fold} for sample in valid.sample_id)
            if not both:
                blockers.append(f"Fixed seed 42 fold {fold} lacks both classes.")
    fold_by_sample = {row["sample_id"]: row["fold"] for row in assignments}
    if assignments:
        cross_homology = sum(row["homology_edge"] and fold_by_sample[row["sample_id_a"]] != fold_by_sample[row["sample_id_b"]] for row in pairs)
        cross_studies = sum(len({fold_by_sample[sample] for sample in members}) > 1 for members in studies.values())
        if cross_homology or cross_studies:
            blockers.append("Cross-fold homology or primary-study leakage detected.")
    else:
        cross_homology = cross_studies = None
    passed = not blockers
    blockers.append("Local molecular evidence is not a training release; full release review and a new immutable training protocol are required.")
    output.mkdir(parents=True)
    for name, frame in (("prior_candidate_decisions.csv", queue), ("original_controls.csv", pd.DataFrame(new_rows)),
                        ("new_source_decisions.csv", pd.DataFrame(reviews)), ("candidate_molecules.csv", molecules),
                        ("candidate_observations.csv", observations), ("all_member_similarity.csv", pd.DataFrame(pairs)),
                        ("component_summary.csv", components.reset_index()),
                        ("fold_assignments.csv", pd.DataFrame(assignments, columns=["sample_id", "fold"]))):
        frame.to_csv(output / name, index=False)
    report = (
        "# 原始游离酸证据筛选后的重新分组\n\n"
        "从原 41 条候选中仅保留 7 条末端形式已局部确认的分子；其余 34 条暂缓纳入，未补写无修饰状态。"
        "新增 4 条原始游离酸对照、7 条 MIC：Aurein 2.3-COOH，以及 MSI-103-COOH、PGLa-COOH、MAP-COOH。"
        "后 3 条来自实验作者 Deniz Tiltak 的 2009 学位论文，表 4.1/4.2 和方法 3.2.2；"
        "第 4 章明确与 2007 论文为同一研究，因此合并研究标识，未计为两套独立实验。\n\n"
        "[Tiltak 原始学位论文](https://publikationen.bibliothek.kit.edu/1000012217)；"
        "[Cheng 原始论文](https://doi.org/10.1016/j.bbamem.2010.11.025)。"
        "原 PDF、表格渲染及哈希保存在来源目录；用于核查数值事实，未取得原文件再次发布的许可。"
        "latarcin 来源的 COOH 与 Rink amide 合成方法互相矛盾，4 条分子暂缓，未入选。\n\n"
        f"筛选后 {len(molecules)} 条分子、{len(observations)} 条测定；完整比较 {len(pairs)} 对，"
        f"形成 {len(components)} 个同源/研究不可拆分组件，含阳性 {positive_groups} 组、含阴性 {negative_groups} 组。"
        "旧 41 条结构通过的结论仅属于未释放候选，不能迁移到本筛选集。"
        "不足五组的类别无法分到五个同时具备两类的验证折；未运行不可能通过的分折，也未调整阈值、seed、折数。\n\n"
        "当前训练释放 0，总状态 `blocked`。跨折审计在未生成有效分折时记为 null，不将未执行伪报为零泄漏。\n\n"
        + "".join(f"- {reason}\n" for reason in blockers))
    (output / "report.md").write_text(report, encoding="utf-8")
    paths = [BASE / "manifest.json", BASE / "candidate_molecules.csv", BASE / "candidate_observations.csv", QUEUE / "manifest.json", PROTOCOL,
             *[paper / "manifest.json" for paper in OLD_PAPERS],
             *[RAW / name for name in ("tiltak2009_primary_thesis.pdf", "tiltak2009_table4_1.png", "tiltak2009_table4_2.png",
                                       "cheng2011_primary.pdf", "cheng2011_table1.png", "PMC9532841.xml",
                                       "PLP2_supplement.zip", "toxins-411586-supplementary-update.pdf", "nagarajan2018_table1_recheck.png")],
             ROOT / "02_code/public_data.py", ROOT / "02_code/research_data.py", ROOT / "02_code/audit_mic_reviewed_subset_hirsch.py"]
    manifest = {"status": "blocked", "generated_at": utc_now(), "audit_protocol_id": "protocol-mic-01",
                "prior_candidate_molecules": 41, "prior_candidates_retained": 7, "prior_candidates_withheld": 34,
                "new_locally_confirmed_free_acid_molecules": 4, "new_conflicting_source_molecules_withheld": 4,
                "candidate_molecules": len(molecules), "candidate_observations": len(observations),
                "positive_molecules": int(molecules.amp.sum()), "negative_molecules": int(len(molecules) - molecules.amp.sum()),
                "all_member_pairs": len(pairs), "homology_edges": sum(row["homology_edge"] for row in pairs),
                "combined_components": len(components), "positive_bearing_components": positive_groups,
                "negative_bearing_components": negative_groups, "fold_structure_gate_passed": passed,
                "folds_generated": bool(assignments), "folds_required": 5, "seed": 42, "cutoff": 0.4,
                "cross_fold_homology_edges": cross_homology, "cross_fold_primary_studies": cross_studies,
                "folds": folds, "blockers": blockers, "records_released_for_training": 0, "training_started": False,
                "script_sha256": sha256(Path(__file__)),
                "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
                "outputs": {path.name: sha256(path) for path in output.iterdir() if path.is_file()}}
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    result = run(parser.parse_args().output)
    print(json.dumps({key: result[key] for key in ("status", "candidate_molecules", "candidate_observations", "combined_components",
                                                "positive_bearing_components", "negative_bearing_components", "blockers")}, ensure_ascii=True, indent=2))
