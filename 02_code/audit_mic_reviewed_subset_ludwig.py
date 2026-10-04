"""Extend the frozen reviewed candidate subset with the complete Ludwig paper decisions."""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from audit_mic_reviewed_subset_hirsch import DisjointSet
from research_data import sequence_identity
from research_utils import ROOT, sha256, utc_now, write_json


BASE = ROOT / "03_experiments/audits/mic_reviewed_subset_groups_20261002_v2"
PAPER = ROOT / "03_experiments/audits/mic_primary_review_pmid35735615_20261002_v1"
CUTOFF = 0.40
FOLDS = 5


def verify(directory: Path) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["outputs"].items():
        if sha256(directory / name) != digest:
            raise ValueError(f"Frozen output changed: {directory / name}")
    for name, digest in manifest["inputs"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"Frozen evidence changed: {name}")
    return manifest


def run(output: Path) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite candidate structure audit: {output}")
    base, paper = verify(BASE), verify(PAPER)
    if (base["candidate_molecules"] != 38 or base["candidate_observations"] != 50
            or base["records_released_for_training"] != 0
            or paper["paper"]["pmid"] != "35735615"
            or paper["candidate_molecules"] != 3 or paper["candidate_observations"] != 4
            or paper["records_released_for_training"] != 0):
        raise ValueError("Expected frozen base and complete paper candidate decisions.")
    molecules = pd.read_csv(BASE / "candidate_molecules.csv")
    observations = pd.read_csv(BASE / "candidate_observations.csv")
    original_pairs = pd.read_csv(BASE / "all_member_similarity.csv")
    reviewed_records = pd.read_csv(PAPER / "record_review.csv")
    records = reviewed_records[reviewed_records.decision.eq("candidate")].copy()
    assays = pd.read_csv(PAPER / "primary_assays.csv")
    assays = assays[assays.candidate_eligible.eq(True)].copy()
    if (len(records) != 3 or len(assays) != 4
            or set(records.sample_id) != set(assays.sample_id)
            or not set(records.derived_binary_label.astype(int)) == {0, 1}
            or set(records.molecular_form) != {"C-terminal free acid"}
            or set(molecules.sample_id) & set(records.sample_id)
            or set(molecules.seq) & set(records.sequence)):
        raise ValueError("Unexpected paper candidate inventory or molecular identity.")
    for record in records.itertuples(index=False):
        row = {column: "" for column in molecules.columns}
        row.update({
            "sample_id": record.sample_id, "seq": record.sequence,
            "amp": int(record.derived_binary_label),
            "record_ids": json.dumps([record.record_id]), "source_datasets": "original_primary_article",
            "study_ids": "doi:10.3390/cimb44060174|pmid:35735615",
            "homology_component": "new_candidate",
        })
        molecules = pd.concat([molecules, pd.DataFrame([row])], ignore_index=True)
    new_observations = [{
        "sample_id": row.sample_id, "record_id": row.record_id,
        "source_dataset": "original_primary_article", "assay_index": row.assay_index,
        "target": row.target, "medium": row.medium, "method": "broth MIC, Methods 2.3",
        "raw_mic": row.paper_value, "raw_unit": row.unit,
        "normalized_low_ug_ml": row.normalized_low_ug_ml,
        "normalized_high_ug_ml": row.normalized_high_ug_ml,
        "eligible": True, "derived_label": int(row.derived_binary_label),
        "reference_resolution": "original_article_table_1_methods_2_2_2_3",
        "assay_study_ids": row.assay_study_ids,
    } for row in assays.itertuples(index=False)]
    observations = pd.concat([observations, pd.DataFrame(new_observations)], ignore_index=True)
    labels = observations.groupby("sample_id").derived_label
    if (labels.nunique().max() != 1 or set(labels.groups) != set(molecules.sample_id)
            or any(int(row.amp) != int(labels.first().loc[row.sample_id]) for row in molecules.itertuples(index=False))):
        raise ValueError("Observation labels conflict with candidate molecular labels.")
    old_ids = set(pd.read_csv(BASE / "candidate_molecules.csv").sample_id)
    lookup = molecules.set_index("sample_id")
    pair_rows = original_pairs.to_dict("records")
    # Preserve the frozen old-pair order; compare every newly admitted member to every old member.
    for record in records.itertuples(index=False):
        for sample_id in molecules.sample_id:
            if sample_id not in old_ids:
                continue
            pair_rows.append({"sample_id_a": record.sample_id, "sample_id_b": sample_id,
                              "record_ids_a": lookup.loc[record.sample_id, "record_ids"],
                              "record_ids_b": lookup.loc[sample_id, "record_ids"],
                              "identity": sequence_identity(record.sequence, lookup.loc[sample_id, "seq"], identity_mode="alignment")})
    for a, b in itertools.combinations(records.itertuples(index=False), 2):
        pair_rows.append({"sample_id_a": a.sample_id, "sample_id_b": b.sample_id,
                          "record_ids_a": lookup.loc[a.sample_id, "record_ids"],
                          "record_ids_b": lookup.loc[b.sample_id, "record_ids"],
                          "identity": sequence_identity(a.sequence, b.sequence, identity_mode="alignment")})
    pairs = pd.DataFrame(pair_rows).drop(columns=["same_homology_component"], errors="ignore")
    expected_pairs = set(itertools.combinations(sorted(molecules.sample_id), 2))
    actual_pairs = [tuple(sorted((row.sample_id_a, row.sample_id_b))) for row in pairs.itertuples(index=False)]
    if set(actual_pairs) != expected_pairs or len(actual_pairs) != len(expected_pairs):
        raise ValueError("Full all-member pair coverage is incomplete or duplicated.")
    groups = DisjointSet(molecules.sample_id.tolist())
    homology_edges = pairs[pairs.identity.ge(CUTOFF)]
    for row in homology_edges.itertuples(index=False):
        groups.union(row.sample_id_a, row.sample_id_b)
    study_members: dict[str, set[str]] = {}
    first_by_study = {}
    for row in observations.itertuples(index=False):
        identifiers = str(row.assay_study_ids).split("|")
        if not identifiers or any(not identifier or identifier == "nan" for identifier in identifiers):
            raise ValueError("Candidate observation lacks a primary-study identifier.")
        for identifier in identifiers:
            study_members.setdefault(identifier, set()).add(row.sample_id)
            if identifier in first_by_study:
                groups.union(row.sample_id, first_by_study[identifier])
            else:
                first_by_study[identifier] = row.sample_id
    roots = {sample: groups.find(sample) for sample in molecules.sample_id}
    component_ids = {root: index for index, root in enumerate(sorted(set(roots.values())))}
    molecules["review_component"] = molecules.sample_id.map(lambda sample: component_ids[roots[sample]])
    components = molecules.groupby("review_component").agg(molecules=("sample_id", "size"), positives=("amp", "sum"))
    components["negatives"] = components.molecules - components.positives
    components = components.reset_index().sort_values("molecules", ascending=False)
    fold_rows, assignments = [], []
    splitter = StratifiedGroupKFold(n_splits=FOLDS, shuffle=True, random_state=42)
    for fold, (train_ids, valid_ids) in enumerate(splitter.split(molecules.seq, molecules.amp, molecules.review_component)):
        train, valid = molecules.iloc[train_ids], molecules.iloc[valid_ids]
        both = set(train.amp) == {0, 1} and set(valid.amp) == {0, 1}
        fold_rows.append({"fold": fold, "train_n": len(train), "validation_n": len(valid),
                          "validation_positive": int(valid.amp.sum()),
                          "validation_negative": int(len(valid) - valid.amp.sum()), "both_classes": both})
        assignments.extend({"sample_id": sample, "fold": fold} for sample in valid.sample_id)
    fold_by_sample = {row["sample_id"]: row["fold"] for row in assignments}
    pairs["fold_a"] = pairs.sample_id_a.map(fold_by_sample)
    pairs["fold_b"] = pairs.sample_id_b.map(fold_by_sample)
    pairs["cross_fold"] = pairs.fold_a.ne(pairs.fold_b)
    pairs["cross_fold_homology_violation"] = pairs.cross_fold & pairs.identity.ge(CUTOFF)
    study_rows = [{"study_id": identifier, "members": len(members),
                   "validation_folds": json.dumps(sorted({fold_by_sample[s] for s in members})),
                   "cross_fold_violation": len({fold_by_sample[s] for s in members}) > 1}
                  for identifier, members in sorted(study_members.items())]
    negative_groups, positive_groups = int(components.negatives.gt(0).sum()), int(components.positives.gt(0).sum())
    blockers = [f"Fixed seed 42 fold {row['fold']} lacks both classes." for row in fold_rows if not row["both_classes"]]
    cross_edges = int(pairs.cross_fold_homology_violation.sum())
    cross_studies = sum(row["cross_fold_violation"] for row in study_rows)
    if cross_edges or cross_studies:
        blockers.append(f"Cross-fold violations: {cross_edges} homology edges, {cross_studies} primary-study identifiers.")
    structure_passed = not blockers
    blockers.append("The full selected cohort still needs complete primary-paper review and a new immutable training protocol.")
    output.mkdir(parents=True)
    for name, frame in (("candidate_molecules.csv", molecules), ("candidate_observations.csv", observations),
                        ("all_member_similarity.csv", pairs), ("component_summary.csv", components),
                        ("fold_assignments.csv", pd.DataFrame(assignments)), ("cross_fold_study_audit.csv", pd.DataFrame(study_rows))):
        frame.to_csv(output / name, index=False)
    (output / "report.md").write_text(
        "# 加入 Ludwig 原论文候选后的全员与五折审计\n\n"
        f"现有 {len(molecules)} 条分子、{len(observations)} 条测定，完整比较 {len(pairs)} 对；"
        f"达到 0.40 的 {len(homology_edges)} 对和共享论文连接后，保留 {len(components)} 个不可拆分组件。"
        f"含阴性 {negative_groups} 组、含阳性 {positive_groups} 组。Api810 连到现有 Okimura 肽，并将同论文的 Api801/Api805 一起连接，未新增独立阴性组件。\n\n"
        f"固定 StratifiedGroupKFold、seed 42、5 折中 {sum(row['both_classes'] for row in fold_rows)}/5 折具备训练和验证两类；"
        f"跨折超阈值同源边 {cross_edges}，跨折论文标识 {cross_studies}。"
        "本次未调整阈值、seed 或折数。候选证据尚未全量释放，正式训练数仍为 0，状态为 `blocked`。\n\n"
        + "阻断项：\n" + "".join(f"- {reason}\n" for reason in blockers), encoding="utf-8")
    inputs = (BASE / "manifest.json", PAPER / "manifest.json", ROOT / "02_code/audit_mic_reviewed_subset_hirsch.py",
              ROOT / "02_code/research_data.py", ROOT / "02_code/research_protocol_config.py")
    output_names = ("candidate_molecules.csv", "candidate_observations.csv", "all_member_similarity.csv", "component_summary.csv",
                    "fold_assignments.csv", "cross_fold_study_audit.csv", "report.md")
    manifest = {
        "status": "blocked", "generated_at": utc_now(), "cutoff": CUTOFF, "folds_required": FOLDS,
        "candidate_observations": len(observations), "candidate_molecules": len(molecules),
        "all_member_pairs": len(pairs), "homology_edges": len(homology_edges), "combined_components": len(components),
        "negative_bearing_components": negative_groups, "positive_bearing_components": positive_groups,
        "fold_structure_gate_passed": structure_passed, "cross_fold_homology_edges": cross_edges,
        "cross_fold_primary_studies": cross_studies, "folds": fold_rows, "blockers": blockers,
        "records_released_for_training": 0, "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in inputs},
        "outputs": {name: sha256(output / name) for name in output_names},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output), ensure_ascii=True, indent=2))
