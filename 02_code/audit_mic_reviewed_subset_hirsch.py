"""Recompute reviewed MIC subset structure after adding original EtCec3 evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from research_utils import ROOT, sha256, utc_now, write_json


BASE = ROOT / "03_experiments/audits/mic_reviewed_subset_groups_20261002_v1"
PAPER = ROOT / "03_experiments/audits/mic_primary_review_pmid32344933_20261002_v2"
OLD_PAIRS = ROOT / "03_experiments/audits/mic_only_cohort_20261001_v9/all_member_similarity.csv"
CUTOFF = 0.40
FOLDS = 5


class DisjointSet:
    def __init__(self, values: list[str]):
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, a: str, b: str) -> None:
        self.parent[self.find(a)] = self.find(b)


def run(output: Path) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite subset audit: {output}")
    base_manifest_path = BASE / "manifest.json"
    paper_manifest_path = PAPER / "manifest.json"
    base = json.loads(base_manifest_path.read_text(encoding="utf-8"))
    paper = json.loads(paper_manifest_path.read_text(encoding="utf-8"))
    if (base["status"] != "blocked" or base["candidate_molecules"] != 37
            or base["all_member_pairs"] != 666 or base["cutoff"] != CUTOFF
            or base["records_released_for_training"] != 0):
        raise ValueError("Base structural audit changed; review it first.")
    if (paper["status"] != "candidate_primary_evidence_verified_not_released"
            or paper["paper"]["pmid"] != "32344933"
            or paper["primary_assay_observations"] != 2
            or paper["reviewed_similarity_edges_at_0_40"] != 0
            or paper["records_released_for_training"] != 0):
        raise ValueError("EtCec3 primary evidence or release state changed.")
    for manifest, directory in ((base, BASE), (paper, PAPER)):
        for name, digest in manifest["outputs"].items():
            if sha256(directory / name) != digest:
                raise ValueError(f"Frozen output changed: {directory / name}")
    paths = [base_manifest_path, BASE / "candidate_molecules.csv",
             BASE / "candidate_observations.csv", paper_manifest_path,
             PAPER / "primary_assays.csv", PAPER / "similarity_reviewed.csv", OLD_PAIRS]
    molecules = pd.read_csv(BASE / "candidate_molecules.csv")
    observations = pd.read_csv(BASE / "candidate_observations.csv")
    assays = pd.read_csv(PAPER / "primary_assays.csv")
    source_pairs = pd.read_csv(PAPER / "similarity_reviewed.csv")
    if (len(assays) != 2 or assays.sample_id.nunique() != 1
            or assays.derived_binary_label.tolist() != [0, 0]
            or set(assays.paper_value) != {">1024"}
            or set(assays.molecular_form) != {"C-terminal free acid"}):
        raise ValueError("EtCec3 assay label or molecular form changed.")
    candidate_id = assays.sample_id.iloc[0]
    candidate_seq = assays.sequence.iloc[0]
    if (candidate_id != hashlib.sha256(candidate_seq.encode("ascii")).hexdigest()[:24]
            or candidate_seq in set(molecules.seq) or candidate_id in set(molecules.sample_id)):
        raise ValueError("EtCec3 sample identity overlaps the frozen subset.")
    if (len(source_pairs) != len(molecules)
            or set(source_pairs.other_sample_id) != set(molecules.sample_id)
            or source_pairs.edge_at_0_40.any()
            or not source_pairs.identity.lt(CUTOFF).all()):
        raise ValueError("EtCec3 all-member comparison differs from primary review.")
    new_molecule = {column: "" for column in molecules.columns}
    new_molecule.update({
        "sample_id": candidate_id, "seq": candidate_seq, "amp": 0,
        "record_ids": json.dumps([assays.record_id.iloc[0]]),
        "source_datasets": "original_primary_article",
        "study_ids": "doi:10.3390/microorganisms8050626|pmid:32344933",
        "homology_component": "new_candidate",
    })
    molecules = pd.concat([molecules, pd.DataFrame([new_molecule])], ignore_index=True)
    new_observations = []
    for index, row in enumerate(assays.itertuples(index=False)):
        new_observations.append({
            "sample_id": candidate_id, "record_id": row.record_id,
            "source_dataset": "original_primary_article", "assay_index": index,
            "target": row.target, "medium": row.medium, "method": "broth MIC, Methods 2.4",
            "raw_mic": row.paper_value, "raw_unit": row.unit,
            "normalized_low_ug_ml": 1024.0, "normalized_high_ug_ml": float("inf"),
            "eligible": True, "derived_label": 0,
            "reference_resolution": "original_article_table_1_2_methods_2_4",
            "assay_study_ids": "doi:10.3390/microorganisms8050626|pmid:32344933",
        })
    observations = pd.concat([observations, pd.DataFrame(new_observations)], ignore_index=True)
    if observations.groupby("sample_id").derived_label.nunique().max() != 1:
        raise ValueError("Conflicting labels for one molecular identity.")
    old = pd.read_csv(OLD_PAIRS)
    prior_ids = set(molecules.sample_id) - {candidate_id}
    prior_pairs = old[old.sample_id_a.isin(prior_ids) & old.sample_id_b.isin(prior_ids)].copy()
    if len(prior_pairs) != 666:
        raise ValueError("Frozen old-old all-member pairs are incomplete.")
    record_ids = dict(zip(molecules.sample_id, molecules.record_ids))
    new_pairs = pd.DataFrame([{
        "sample_id_a": candidate_id, "sample_id_b": row.other_sample_id,
        "record_ids_a": record_ids[candidate_id],
        "record_ids_b": record_ids[row.other_sample_id],
        "identity": row.identity, "same_homology_component": bool(row.edge_at_0_40),
    } for row in source_pairs.itertuples(index=False)])
    pairs = pd.concat([prior_pairs, new_pairs], ignore_index=True)
    if len(pairs) != len(molecules) * (len(molecules) - 1) // 2:
        raise ValueError("Expanded all-member pair table is incomplete.")
    if pairs.duplicated(["sample_id_a", "sample_id_b"]).any():
        raise ValueError("Duplicate all-member pair encountered.")
    groups = DisjointSet(molecules.sample_id.tolist())
    homology_edges = pairs[pairs.identity.ge(CUTOFF)]
    for item in homology_edges.itertuples(index=False):
        groups.union(item.sample_id_a, item.sample_id_b)
    first_by_study = {}
    for item in observations.itertuples(index=False):
        for identifier in str(item.assay_study_ids).split("|"):
            if identifier in first_by_study:
                groups.union(item.sample_id, first_by_study[identifier])
            else:
                first_by_study[identifier] = item.sample_id
    root_by_sample = {sample: groups.find(sample) for sample in molecules.sample_id}
    component_ids = {root: index for index, root in
                     enumerate(sorted(set(root_by_sample.values())))}
    molecules["review_component"] = molecules.sample_id.map(
        lambda sample: component_ids[root_by_sample[sample]])
    components = molecules.groupby("review_component").agg(
        molecules=("sample_id", "size"), positives=("amp", "sum"))
    components["negatives"] = components.molecules - components.positives
    components = components.reset_index().sort_values("molecules", ascending=False)
    negative_groups = int(components.negatives.gt(0).sum())
    positive_groups = int(components.positives.gt(0).sum())
    splitter = StratifiedGroupKFold(n_splits=FOLDS, shuffle=True, random_state=42)
    fold_rows = []
    fold_assignments = []
    for fold, (train_ids, valid_ids) in enumerate(splitter.split(
            molecules.seq, molecules.amp, molecules.review_component)):
        train, valid = molecules.iloc[train_ids], molecules.iloc[valid_ids]
        both = set(train.amp) == {0, 1} and set(valid.amp) == {0, 1}
        fold_rows.append({"fold": fold, "train_n": len(train), "validation_n": len(valid),
                          "validation_positive": int(valid.amp.sum()),
                          "validation_negative": int(len(valid) - valid.amp.sum()),
                          "both_classes": both})
        fold_assignments.extend({"sample_id": sample_id, "fold": fold}
                                for sample_id in valid.sample_id)
    blockers = []
    if negative_groups < FOLDS or positive_groups < FOLDS:
        blockers.append("Fewer than five components bear one or both classes.")
    for row in fold_rows:
        if not row["both_classes"]:
            blockers.append(f"Fixed seed 42 fold {row['fold']} lacks both classes.")
    blockers.append("The full selected cohort lacks independent primary-paper review and an immutable training protocol.")
    output.mkdir(parents=True)
    observations.to_csv(output / "candidate_observations.csv", index=False)
    molecules.to_csv(output / "candidate_molecules.csv", index=False)
    pairs.to_csv(output / "all_member_similarity.csv", index=False)
    components.to_csv(output / "component_summary.csv", index=False)
    pd.DataFrame(fold_assignments).to_csv(output / "fold_assignments.csv", index=False)
    report = (
        "# 加入 EtCec3-OH 后的候选结构复核\n\n"
        f"原论文候选现为 {len(observations)} 条测定、{len(molecules)} 条唯一分子；"
        f"完整全员比对为 {len(pairs)} 对，其中 {len(homology_edges)} 对达到 0.40。"
        f"以原始论文和同源连通后为 {len(components)} 个组件，"
        f"含阴性 {negative_groups} 个，含阳性 {positive_groups} 个。"
        "EtCec3-OH 是当前核查子集中的新增独立阴性组件；"
        "若恢复旧未核实的 324 条队列，它会与其中一条旧序列合并。\n\n"
        f"原有固定 StratifiedGroupKFold、seed 42、五折仅 "
        f"{sum(row['both_classes'] for row in fold_rows)}/5 折具备训练和验证两类。"
        "未改变阈值、折数或 seed 追求放行。候选证据与新冻结训练协议也尚未完成；"
        "训练释放数为 0，状态仍为 `blocked`。\n\n"
        + "阻断项：\n" + "".join(f"- {item}\n" for item in blockers)
    )
    (output / "report.md").write_text(report, encoding="utf-8")
    outputs = ("candidate_observations.csv", "candidate_molecules.csv",
               "all_member_similarity.csv", "component_summary.csv",
               "fold_assignments.csv", "report.md")
    manifest = {
        "status": "blocked", "generated_at": utc_now(),
        "cutoff": CUTOFF, "folds_required": FOLDS,
        "candidate_observations": len(observations),
        "candidate_molecules": len(molecules), "all_member_pairs": len(pairs),
        "homology_edges": len(homology_edges), "combined_components": len(components),
        "negative_bearing_components": negative_groups,
        "positive_bearing_components": positive_groups,
        "fold_group_count_necessary_condition_passed": negative_groups >= FOLDS and positive_groups >= FOLDS,
        "fold_structure_gate_passed": all(row["both_classes"] for row in fold_rows),
        "folds": fold_rows, "blockers": blockers,
        "records_released_for_training": 0,
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
        "script_sha256": sha256(Path(__file__)),
        "outputs": {name: sha256(output / name) for name in outputs},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output), ensure_ascii=True, indent=2))
