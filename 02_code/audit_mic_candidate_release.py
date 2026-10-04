"""Publish a molecule-by-molecule evidence queue; structural feasibility cannot release training."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from audit_mic_reviewed_subset_ludwig import verify
from research_utils import ROOT, sha256, utc_now, write_json


STRUCTURE = ROOT / "03_experiments/audits/mic_reviewed_subset_groups_20261002_v3"
VERIFIED_FORM_PMIDS = {"33790103", "32344933", "35735615"}
PAPER_DECISIONS = {
    "33281785": ("original_article_MIC_and_image_sequence_match", "terminal_form_not_explicit_in_read_synthesis_section; image_sequence_pending_independent_check"),
    "36551368": ("original_supplement_sequence_and_MIC_match", "complete_molecular_form_review_pending; cysteine_containing_candidate_assay_redox_state_pending"),
    "29259134": ("original_image_table_sequence_and_MIC_match", "image_table_pending_independent_check; terminal_form_not_explicit_in_read_synthesis_section"),
    "42206144": ("original_supplement_sequence_and_MIC_match_excluding_conflicting_record", "terminal_form_not_explicit_in_original_synthesis; full_record_conditions_review_pending"),
    "40645962": ("four_exact_original_source_data_cells_only", "terminal_form_not_explicit_in_original_synthesis; remaining_source_80_cells_unresolved"),
    "22467870": ("prior_primary_table_candidate_pending_source_recheck", "native_uncyclotide_disulfide_and_mass_state_pending; database_none_does_not_establish_unmodified_molecule"),
    "30658410": ("original_article_MIC_table_match", "synthetic_assay_molecule_must_be_matched_to_native_mass_and_sequence; referenced_method_conditions_pending"),
    "33790103": ("original_tables_sequence_MIC_and_free_acid_match", "local_fields_confirmed; full_cohort_release_pending"),
    "32344933": ("original_tables_sequence_MIC_and_free_acid_match", "local_fields_confirmed; full_cohort_release_pending"),
    "35735615": ("original_structured_table_sequence_MIC_and_free_acid_match", "local_fields_confirmed; full_cohort_release_pending"),
}
ORIGINAL_METHODS = {
    "33281785": ROOT / "03_experiments/audits/mic_primary_candidate_sources_20261002_v1/PMC7689250.xml",
    "40645962": ROOT / "03_experiments/audits/mic_primary_review_pmid40645962_20261002_v1/raw/PMC12254355_fullTextXML.xml",
    "42206144": ROOT / "03_experiments/audits/mic_primary_candidate_sources_20261002_v1/PMC13201158.xml",
    "30658410": ROOT / "03_experiments/audits/mic_primary_candidate_sources_20261002_v1/PMC6356579.xml",
}


def run(output: Path) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite evidence queue: {output}")
    structure = verify(STRUCTURE)
    if (structure["candidate_molecules"] != 41 or structure["candidate_observations"] != 54
            or structure["fold_structure_gate_passed"] is not True
            or structure["cross_fold_homology_edges"] != 0 or structure["cross_fold_primary_studies"] != 0
            or structure["records_released_for_training"] != 0):
        raise ValueError("The expected candidate structural audit changed.")
    molecules = pd.read_csv(STRUCTURE / "candidate_molecules.csv")
    observations = pd.read_csv(STRUCTURE / "candidate_observations.csv")
    rows = []
    for molecule in molecules.itertuples(index=False):
        selected = observations[observations.sample_id.eq(molecule.sample_id)]
        pmids = sorted({identifier.removeprefix("pmid:") for value in selected.assay_study_ids
                        for identifier in str(value).split("|") if identifier.startswith("pmid:")})
        reviewed_pmids = [pmid for pmid in pmids if pmid in PAPER_DECISIONS]
        if len(reviewed_pmids) != 1:
            raise ValueError(f"Candidate has no unique reviewed evidence owner: {molecule.sample_id}")
        pmid = reviewed_pmids[0]
        evidence, pending = PAPER_DECISIONS[pmid]
        form_verified = pmid in VERIFIED_FORM_PMIDS
        rows.append({
            "sample_id": molecule.sample_id, "record_ids": molecule.record_ids, "sequence": molecule.seq,
            "candidate_label": int(molecule.amp), "candidate_observations": len(selected),
            "all_assay_study_ids": "|".join(sorted({identifier for value in selected.assay_study_ids
                                                    for identifier in str(value).split("|")})),
            "primary_evidence_pmid": pmid, "primary_source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "sequence_and_mic_review": evidence,
            "molecular_form_review": "primary_free_acid_confirmed" if form_verified else "pending_primary_molecular_form_review",
            "pending_items": pending, "review_component": int(molecule.review_component),
            "decision": "local_fields_confirmed_not_released" if form_verified else "pending_not_released",
            "training_release": False,
        })
    queue = pd.DataFrame(rows)
    confirmed_molecules = int(queue.molecular_form_review.eq("primary_free_acid_confirmed").sum())
    pending_molecules = len(queue) - confirmed_molecules
    if confirmed_molecules != 7 or pending_molecules != 34:
        raise ValueError("Expected seven locally confirmed free-acid molecular identities and 34 pending identities.")
    output.mkdir(parents=True)
    queue.to_csv(output / "molecule_review_queue.csv", index=False)
    summary = queue.groupby("primary_evidence_pmid", as_index=False).agg(
        candidate_molecules=("sample_id", "size"), candidate_observations=("candidate_observations", "sum"),
        molecular_form_review=("molecular_form_review", "first"), pending_items=("pending_items", "first"))
    summary.to_csv(output / "paper_review_queue.csv", index=False)
    report = (
        "# 候选训练释放审查队列\n\n"
        "41 条候选的结构门禁已通过，但结构通过不等于证据释放。"
        "7 条分子的原始序列、MIC 和游离酸端形式已作局部确认；34 条的完整分子身份或补充证据仍待核实。"
        "这不是认定 34 条全部错误，也不是认定 7 条已经构成可训练队列。\n\n"
        "剩余事项逐条列在 `molecule_review_queue.csv`，按论文汇总在 `paper_review_queue.csv`："
        "商业合成和质谱验证的概述不能替代末端形式证明；未核对的二硫键或氧化状态不能填为无修饰；"
        "原始图中的 `80` 编码不转换成删失 MIC；图片转录须完成复核；引用的测定方法须追溯。"
        "完成证据筛选后必须再次执行全员比较和固定五折，不能沿用未释放候选的通过结果。\n\n"
        "当前总状态 `blocked`，训练释放 0。新训练协议须绑定最终证据和分折文件，冻结后才可调用训练入口。\n"
    )
    (output / "report.md").write_text(report, encoding="utf-8")
    paths = (STRUCTURE / "manifest.json", STRUCTURE / "candidate_molecules.csv",
             STRUCTURE / "candidate_observations.csv", ROOT / "02_code/audit_mic_reviewed_subset_ludwig.py",
             *ORIGINAL_METHODS.values())
    manifest = {
        "status": "blocked_primary_evidence_release", "generated_at": utc_now(),
        "candidate_molecules": len(queue), "candidate_observations": len(observations),
        "locally_confirmed_free_acid_molecules": confirmed_molecules,
        "pending_primary_molecular_form_molecules": pending_molecules,
        "candidate_structure_gate_passed": True,
        "records_released_for_training": 0, "training_started": False,
        "blockers": ["Full primary-paper molecular-identity and observation review remains incomplete.",
                     "Final admitted cohort must be re-audited and bound to a new immutable training protocol."],
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
        "outputs": {name: sha256(output / name) for name in
                    ("molecule_review_queue.csv", "paper_review_queue.csv", "report.md")},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output), ensure_ascii=True, indent=2))
