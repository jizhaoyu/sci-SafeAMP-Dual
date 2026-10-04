"""Audit all-member homology and study groups of paper-reviewed MIC candidates.

This is a feasibility calculation, not a training release or model run.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from research_utils import ROOT, sha256, utc_now, write_json


PAPER_AUDITS = {
    "42206144": "mic_primary_review_20261001_v3",
    "33281785": "mic_primary_review_pmid33281785_20261002_v2",
    "36551368": "mic_primary_review_pmid36551368_20261002_v2",
    "29259134": "mic_primary_review_pmid29259134_20261002_v2",
    "33790103": "mic_primary_review_pmid33790103_20261002_v2",
}
GUAN_AUDIT = "mic_primary_review_pmid40645962_20261002_v2"
EXCLUDED_RECORDS = {"DBAASP:25512"}
FOLDS = 5
CUTOFF = 0.40


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


def reviewed_table(relative_dir: str, pmid: str, status: str, inputs: list[Path]) -> pd.DataFrame:
    directory = ROOT / "03_experiments/audits" / relative_dir
    manifest_path, review_path = directory / "manifest.json", directory / "record_review.csv"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    released = (manifest.get("review", {}).get("records_released_for_training")
                if "review" in manifest else
                manifest.get("paper_review", {}).get("records_fully_released_for_training"))
    if (manifest["paper"]["pmid"] != pmid or manifest["status"] != status
            or released != 0
            or manifest["outputs"]["record_review.csv"] != sha256(review_path)):
        raise ValueError(f"Paper review changed or has an unexpected status: {pmid}")
    inputs.extend((manifest_path, review_path))
    return pd.read_csv(review_path)


def run(output: Path, assays_path: Path, molecules_path: Path, pairs_path: Path,
        dramp_path: Path) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite reviewed subset audit: {output}")
    inputs = [Path(path).resolve() for path in
              (assays_path, molecules_path, pairs_path, dramp_path)]
    assays = pd.read_csv(inputs[0])
    selected = []
    for pmid, directory in PAPER_AUDITS.items():
        review = reviewed_table(directory, pmid, "blocked_primary_review_in_progress", inputs)
        ids = set(review.record_id) - EXCLUDED_RECORDS
        frame = assays[
            assays.record_id.isin(ids) & assays.eligible.eq(True)
            & assays.derived_label.notna()
            & assays.assay_study_ids.astype(str).str.contains(f"pmid:{pmid}", regex=False)
        ]
        if not ids or set(frame.record_id) != ids:
            raise ValueError(f"Paper-reviewed records missing from frozen assays: {pmid}")
        selected.append(frame)
    guan = reviewed_table(GUAN_AUDIT, "40645962", "blocked_source_80_code_unresolved", inputs)
    exact = guan[guan.exact_mic_match.eq(True)]
    if len(exact) != 4 or exact.database_mic.astype(str).str.startswith(">").any():
        raise ValueError("Expected four exact Guan source-data observations.")
    guan_pairs = set(zip(exact.record_id, exact.target))
    frame = assays[
        assays.apply(lambda row: (row.record_id, row.target) in guan_pairs, axis=1)
        & assays.assay_study_ids.astype(str).str.contains("pmid:40645962", regex=False)
        & assays.eligible.eq(True) & assays.derived_label.notna()
    ]
    if len(frame) != len(exact):
        raise ValueError("Exact Guan source-data rows do not map to four frozen observations.")
    selected.append(frame)
    dramp = pd.read_csv(inputs[3])
    if len(dramp) != 4 or not dramp.amp.eq(1).all():
        raise ValueError("Verified DRAMP candidate inventory changed.")
    frame = assays[assays.record_id.isin(set(dramp.record_id)) & assays.eligible.eq(True)
                   & assays.derived_label.eq(1)]
    if set(frame.record_id) != set(dramp.record_id):
        raise ValueError("DRAMP candidates do not map to frozen observations.")
    selected.append(frame)
    observations = pd.concat(selected, ignore_index=True).drop_duplicates("sample_id")
    # Multiple target rows must not silently change a molecule's binary class.
    all_selected = pd.concat(selected, ignore_index=True)
    if all_selected.groupby("sample_id").derived_label.nunique().max() != 1:
        raise ValueError("Reviewed source observations conflict on a molecular label.")
    molecules = pd.read_csv(inputs[1])
    sample_ids = set(observations.sample_id)
    subset = molecules[molecules.sample_id.isin(sample_ids)].copy()
    if set(subset.sample_id) != sample_ids or len(subset) != len(sample_ids):
        raise ValueError("Candidate molecule absent from frozen all-member cohort.")
    label_by_sample = all_selected.groupby("sample_id").derived_label.first().astype(int)
    if any(int(row.amp) != label_by_sample[row.sample_id] for row in subset.itertuples(index=False)):
        raise ValueError("Candidate source label conflicts with molecule-level frozen label.")
    pairs = pd.read_csv(inputs[2])
    candidate_pairs = pairs[pairs.sample_id_a.isin(sample_ids) & pairs.sample_id_b.isin(sample_ids)].copy()
    if len(candidate_pairs) != len(subset) * (len(subset) - 1) // 2:
        raise ValueError("Frozen all-member similarity table is incomplete for candidate subset.")
    union = DisjointSet(subset.sample_id.tolist())
    homology_edges = candidate_pairs[candidate_pairs.identity.ge(CUTOFF)]
    for row in homology_edges.itertuples(index=False):
        union.union(row.sample_id_a, row.sample_id_b)
    first_by_study = {}
    study_members = defaultdict(set)
    for row in all_selected.itertuples(index=False):
        for identifier in str(row.assay_study_ids).split("|"):
            if not identifier:
                continue
            study_members[identifier].add(row.sample_id)
            if identifier in first_by_study:
                union.union(row.sample_id, first_by_study[identifier])
            else:
                first_by_study[identifier] = row.sample_id
    root_by_sample = {sample_id: union.find(sample_id) for sample_id in sample_ids}
    component_ids = {root: index for index, root in enumerate(sorted(set(root_by_sample.values())))}
    subset["review_component"] = subset.sample_id.map(
        lambda sample_id: component_ids[root_by_sample[sample_id]])
    summary = subset.groupby("review_component").agg(
        molecules=("sample_id", "size"), positives=("amp", "sum"))
    summary["negatives"] = summary.molecules - summary.positives
    summary = summary.reset_index().sort_values("molecules", ascending=False)
    negative_groups = int(summary.negatives.gt(0).sum())
    positive_groups = int(summary.positives.gt(0).sum())
    blockers = []
    if negative_groups < FOLDS or positive_groups < FOLDS:
        blockers.append(f"Only {negative_groups} negative-bearing and {positive_groups} positive-bearing disjoint components for {FOLDS} folds.")
    folds = []
    if len(summary) >= FOLDS:
        splitter = StratifiedGroupKFold(n_splits=FOLDS, shuffle=True, random_state=42)
        for fold, (train_idx, valid_idx) in enumerate(splitter.split(
                subset.seq, subset.amp, subset.review_component)):
            train, valid = subset.iloc[train_idx], subset.iloc[valid_idx]
            ok = set(train.amp) == {0, 1} and set(valid.amp) == {0, 1}
            folds.append({"fold": fold, "train_n": len(train), "validation_n": len(valid),
                          "validation_positive": int(valid.amp.sum()),
                          "validation_negative": int(len(valid) - valid.amp.sum()),
                          "both_classes": ok})
            if not ok:
                blockers.append(f"Fold {fold} lacks both classes in training or validation.")
    else:
        blockers.append(f"Only {len(summary)} components for {FOLDS} folds.")
    output.mkdir(parents=True)
    all_selected.to_csv(output / "candidate_observations.csv", index=False)
    subset.to_csv(output / "candidate_molecules.csv", index=False)
    summary.to_csv(output / "component_summary.csv", index=False)
    report = (
        "# 原文核查候选集的全员隔离可行性\n\n"
        f"从 {len(all_selected)} 条逐测定候选、{len(subset)} 条唯一序列开始，"
        f"读取冻结的全部 {len(candidate_pairs)} 个候选序列配对；"
        f"以固定 {CUTOFF:.2f} 阈值和共同原始论文连接后为 {len(summary)} 个不可拆分组件，"
        f"其中含阴性 {negative_groups} 组、含阳性 {positive_groups} 组。"
        f"固定 seed 42 的 {FOLDS} 折中，满足两类条件的折数为 "
        f"{sum(item['both_classes'] for item in folds)}/{len(folds)}。\n\n"
        "此计算仅是结构可行性：候选有单人图片转录、来源化学形式与测定对象尚待全队列复核；"
        "Guan 原始绘图文件的 `80` 编码测定已排除。训练释放数为 0。\n\n"
        + ("阻断项：\n" + "".join(f"- {item}\n" for item in blockers) if blockers else
           "分折结构必要条件通过；证据释放及新协议冻结仍未完成。\n")
    )
    (output / "report.md").write_text(report, encoding="utf-8")
    manifest = {
        "status": "blocked", "generated_at": utc_now(), "folds_required": FOLDS,
        "cutoff": CUTOFF, "candidate_observations": len(all_selected),
        "candidate_molecules": len(subset), "all_member_pairs": len(candidate_pairs),
        "homology_edges": len(homology_edges), "combined_components": len(summary),
        "negative_bearing_components": negative_groups,
        "positive_bearing_components": positive_groups,
        "fold_structure_gate_passed": not blockers,
        "folds": folds, "blockers": blockers, "records_released_for_training": 0,
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in inputs},
        "script_sha256": sha256(Path(__file__)),
        "outputs": {name: sha256(output / name) for name in (
            "candidate_observations.csv", "candidate_molecules.csv", "component_summary.csv", "report.md")},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assays", type=Path, default=ROOT / "03_experiments/audits/mic_study_disjoint_20261001_v5/assay_observations.csv")
    parser.add_argument("--molecules", type=Path, default=ROOT / "03_experiments/audits/mic_only_cohort_20261001_v9/molecule_components.csv")
    parser.add_argument("--pairs", type=Path, default=ROOT / "03_experiments/audits/mic_only_cohort_20261001_v9/all_member_similarity.csv")
    parser.add_argument("--dramp", type=Path, default=ROOT / "03_experiments/audits/dramp_verified_ecoli_mic_20261001_v8/records.csv")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.assays, args.molecules, args.pairs, args.dramp),
                     ensure_ascii=False, indent=2))
