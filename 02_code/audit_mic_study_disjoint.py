"""Audit five-fold feasibility after joining homology and primary MIC study links."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from diagnose_mic_baselines import assay_rows
from research_data import source_study_ids
from research_utils import ROOT, utc_now

PROTOCOL_PATH = ROOT / "03_experiments/protocols/protocol-mic-study-01.json"
EXPECTED_PARENT_SHA = "d54227ebb5380039cd07f6ddc979561ef6f99efaecdb7644267e6c7d00dffb97"
EXPECTED_PROTOCOL_SHA = {
    "protocol-mic-study-01": "6ddb23d9b616581961a9ba269fa4eb787b846a1e371dacf8190d3c66085273d8",
    "protocol-mic-study-02": "676b9eaafb916572e15161d9fde10212f78d61e8bb53598b794db84529fe3ff8",
    "protocol-mic-study-03": "293acc617fc8ab5d09453eb6645eea76dc6e02d899972bf61b85111484bb3d74",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: dict) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class DisjointSet:
    def __init__(self, values):
        self.parent = {value: value for value in values}

    def find(self, value):
        if value not in self.parent:
            self.parent[value] = value
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left, right):
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def citation_ids(value) -> set[str]:
    identifiers = source_study_ids(SimpleNamespace(evidence_reference=json.dumps(value, ensure_ascii=False)))
    if isinstance(value, dict) and value.get("id") and value.get("title"):
        identifiers.add(f"dbaasp_article:{value['id']}")
    return identifiers


def study_aliases(records: pd.DataFrame, assay: pd.DataFrame) -> tuple[dict[str, str], list[dict]]:
    all_ids = set()
    citations = []
    for row in records.itertuples(index=False):
        refs = json.loads(row.evidence_reference)
        for citation in refs if isinstance(refs, list) else [refs]:
            identifiers = sorted(citation_ids(citation))
            all_ids.update(identifiers)
            if identifiers:
                citations.append(identifiers)
    for value in assay.assay_study_ids.fillna(""):
        all_ids.update(identifier for identifier in str(value).split("|") if identifier)
    aliases = DisjointSet(all_ids)
    for identifiers in citations:
        for identifier in identifiers[1:]:
            aliases.union(identifiers[0], identifier)
    groups = defaultdict(list)
    for identifier in sorted(all_ids):
        groups[aliases.find(identifier)].append(identifier)
    canonical = {identifier: min(group) for group in groups.values() for identifier in group}
    rows = [{"identifier": identifier, "canonical_study_id": canonical[identifier],
             "aliases": "|".join(groups[aliases.find(identifier)])}
            for identifier in sorted(all_ids)]
    return canonical, rows


def run(output: Path, protocol_path: Path = PROTOCOL_PATH) -> dict:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite an existing audit: {output}")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if (protocol.get("protocol_id") not in EXPECTED_PROTOCOL_SHA
            or protocol.get("protocol_version") != 1
            or protocol.get("status") != "frozen_for_study_disjoint_feasibility_audit_only"
            or protocol.get("parent_mic_protocol_sha256") != EXPECTED_PARENT_SHA
            or canonical_sha256(protocol) != EXPECTED_PROTOCOL_SHA[protocol["protocol_id"]]
            or ("diagnostic_manifest" in protocol) != (protocol["protocol_id"] == "protocol-mic-study-01")):
        raise ValueError("Unexpected or incomplete frozen study-disjoint protocol.")
    cohort_path = ROOT / protocol["cohort_manifest"]
    diag_path = ROOT / protocol["diagnostic_manifest"] if "diagnostic_manifest" in protocol else None
    current_path = ROOT / "03_experiments/audits/mic_only_cohort_20261001_v9/manifest.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    if current.get("status") != "feasible_for_training_review" or cohort_path.resolve() != current_path.resolve():
        raise ValueError("Current MIC-only evidence audit is blocked or differs from the study-disjoint protocol cohort.")
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    diag = json.loads(diag_path.read_text(encoding="utf-8")) if diag_path else None
    if cohort["status"] != "feasible_for_training_review" or cohort["protocol_sha256"] != EXPECTED_PARENT_SHA:
        raise ValueError("Parent homology audit did not pass its fixed gate.")
    if diag and (diag["status"] != "descriptive_diagnostics_completed" or diag["audit_protocol_id"] != cohort["protocol_id"]):
        raise ValueError("Assay study diagnostic is not complete for this cohort.")
    cohort_dir = cohort_path.parent
    molecules_path, pairs_path = cohort_dir / "molecule_components.csv", cohort_dir / "all_member_similarity.csv"
    assays_path = diag_path.parent / "assay_observations.csv" if diag_path else None
    if diag:
        expected = diag["inputs_sha256"]
        for path in (molecules_path, pairs_path):
            if sha256(path) != expected[str(path.relative_to(ROOT))]:
                raise ValueError(f"Diagnostic source hash mismatch: {path}")
    molecules = pd.read_csv(molecules_path)
    pairs = pd.read_csv(pairs_path)
    if len(molecules) != cohort["unique_labeled_molecule_count"] or len(pairs) != len(molecules) * (len(molecules) - 1) // 2:
        raise ValueError("Parent all-member cohort or similarity table is incomplete.")
    records_paths = [ROOT / cohort["existing_records_path"], ROOT / cohort["supplement_records_path"]]
    if sha256(records_paths[0]) != cohort["existing_records_sha256"] or sha256(records_paths[1]) != cohort["supplement_records_sha256"]:
        raise ValueError("Original records changed after parent evidence audit.")
    records = pd.concat([pd.read_csv(path) for path in records_paths], ignore_index=True)
    selected_record_ids = {record_id for value in molecules.record_ids for record_id in json.loads(value)}
    records = records[records.record_id.isin(selected_record_ids)].copy()
    raw_paths = set()
    for row in records.itertuples(index=False):
        raw_path = Path(row.raw_path)
        if not raw_path.is_absolute():
            raw_path = ROOT / raw_path
        if sha256(raw_path) != row.raw_sha256:
            raise ValueError(f"Raw assay evidence checksum mismatch for {row.record_id}.")
        raw_paths.add(raw_path)
    if diag:
        assays = pd.read_csv(assays_path)
    else:
        sample_by_record = {record_id: row.sample_id for row in molecules.itertuples(index=False)
                            for record_id in json.loads(row.record_ids)}
        assays = pd.DataFrame(assay_rows(records, sample_by_record))
    if set(assays.sample_id) != set(molecules.sample_id) or assays.assay_study_ids.isna().any() or (assays.assay_study_ids == "").any():
        raise ValueError("Every molecule needs an assay-linked primary study identifier.")
    canonical, alias_rows = study_aliases(records, assays)
    assay_identifier_ids = {identifier for value in assays.assay_study_ids for identifier in str(value).split("|") if identifier}
    primary_study_groups = {canonical[identifier] for identifier in assay_identifier_ids}
    links = defaultdict(set)
    for row in assays.itertuples(index=False):
        links[row.sample_id].update(canonical[identifier] for identifier in str(row.assay_study_ids).split("|") if identifier)
    if any(not links[sample_id] for sample_id in molecules.sample_id):
        raise ValueError("Some molecules have no primary MIC paper after alias normalization.")
    sample_ids = molecules.sample_id.astype(str).tolist()
    union = DisjointSet(sample_ids)
    first_homology, first_study = {}, {}
    for row in molecules.itertuples(index=False):
        if row.homology_component in first_homology:
            union.union(row.sample_id, first_homology[row.homology_component])
        else:
            first_homology[row.homology_component] = row.sample_id
        for study in sorted(links[row.sample_id]):
            if study in first_study:
                union.union(row.sample_id, first_study[study])
            else:
                first_study[study] = row.sample_id
    roots = sorted({union.find(sample_id) for sample_id in sample_ids})
    group_id = {root: index for index, root in enumerate(roots)}
    molecules["combined_component"] = [group_id[union.find(sample_id)] for sample_id in sample_ids]
    molecules["primary_study_ids"] = ["|".join(sorted(links[sample_id])) for sample_id in sample_ids]
    group_rows = []
    for cid, group in molecules.groupby("combined_component"):
        studies = set().union(*(set(value.split("|")) for value in group.primary_study_ids))
        group_rows.append({"combined_component": int(cid), "n": len(group),
                           "positive": int(group.amp.sum()), "negative": int(len(group) - group.amp.sum()),
                           "original_homology_components": int(group.homology_component.nunique()),
                           "primary_studies": len(studies)})
    components = pd.DataFrame(group_rows).sort_values(["n", "combined_component"], ascending=[False, True])
    old_component_by_sample = molecules.set_index("sample_id").homology_component.to_dict()
    old_components_by_study = defaultdict(set)
    samples_by_study = defaultdict(set)
    for sample_id, identifiers in links.items():
        for identifier in identifiers:
            old_components_by_study[identifier].add(old_component_by_sample[sample_id])
            samples_by_study[identifier].add(sample_id)
    bridges = pd.DataFrame([{"primary_study_id": study, "molecules": len(samples_by_study[study]),
                             "original_homology_components": len(old_components_by_study[study]),
                             "original_component_ids": "|".join(map(str, sorted(old_components_by_study[study])))}
                            for study in sorted(samples_by_study)]).sort_values(
        ["original_homology_components", "molecules"], ascending=[False, False])
    blockers, warnings, fold_rows, fold_summary = [], [], [], []
    if len(components) < 5:
        blockers.append(f"Only {len(components)} independent homology-plus-study components remain for five folds.")
    if set(molecules.amp.astype(int)) != {0, 1}:
        blockers.append("The cohort does not contain both MIC classes.")
    if not blockers:
        splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
        y = molecules.amp.astype(int).to_numpy()
        groups = molecules.combined_component.to_numpy()
        for fold, (train_idx, valid_idx) in enumerate(splitter.split(molecules.seq, y, groups)):
            train, valid = molecules.iloc[train_idx], molecules.iloc[valid_idx]
            shared_components = set(train.combined_component) & set(valid.combined_component)
            train_studies = set().union(*(set(value.split("|")) for value in train.primary_study_ids))
            valid_studies = set().union(*(set(value.split("|")) for value in valid.primary_study_ids))
            shared_studies = train_studies & valid_studies
            ok = set(train.amp) == {0, 1} and set(valid.amp) == {0, 1} and not shared_components and not shared_studies
            if not ok:
                blockers.append(f"Fold {fold} lacks both classes or has shared group/study: train={sorted(set(train.amp))}, validation={sorted(set(valid.amp))}, shared_components={len(shared_components)}, shared_studies={len(shared_studies)}.")
            fold_summary.append({"fold": fold, "train_n": len(train), "validation_n": len(valid),
                                 "train_positive": int(train.amp.sum()), "train_negative": int(len(train) - train.amp.sum()),
                                 "validation_positive": int(valid.amp.sum()), "validation_negative": int(len(valid) - valid.amp.sum()),
                                 "shared_components": len(shared_components), "shared_primary_studies": len(shared_studies),
                                 "gate_passed": ok})
            for role, frame in (("train", train), ("validation", valid)):
                fold_rows.extend({"sample_id": row.sample_id, "fold": fold, "role": role,
                                  "amp": int(row.amp), "combined_component": int(row.combined_component)}
                                 for row in frame.itertuples(index=False))
        valid_fold = {row["sample_id"]: row["fold"] for row in fold_rows if row["role"] == "validation"}
        edges = pairs[pairs.identity >= 0.4]
        cross_homology = int(sum(valid_fold[a] != valid_fold[b] for a, b in
                                 edges[["sample_id_a", "sample_id_b"]].itertuples(index=False, name=None)))
        cross_study = sum(len({valid_fold[sample_id] for sample_id in members}) > 1 for members in samples_by_study.values())
        if cross_homology or cross_study:
            blockers.append(f"Explicit cross-fold audit found {cross_homology} homology edges and {cross_study} primary studies spanning folds.")
        sizes = [item["validation_n"] for item in fold_summary]
        if max(sizes) >= 2 * min(sizes) or int(components.iloc[0]["n"]) >= len(molecules) / 2:
            warnings.append(f"Highly imbalanced study-disjoint folds: sizes={sizes}; largest combined component={int(components.iloc[0]['n'])}/{len(molecules)}.")
    else:
        cross_homology, cross_study = None, None
    output.mkdir(parents=True)
    molecules.to_csv(output / "combined_components.csv", index=False)
    components.to_csv(output / "component_summary.csv", index=False)
    pd.DataFrame(alias_rows).to_csv(output / "study_aliases.csv", index=False)
    bridges.to_csv(output / "study_bridges.csv", index=False)
    pd.DataFrame(fold_rows, columns=["sample_id", "fold", "role", "amp", "combined_component"]).to_csv(output / "fold_assignments.csv", index=False)
    if not diag:
        assays.to_csv(output / "assay_observations.csv", index=False)
    input_paths = [protocol_path, cohort_path, molecules_path, pairs_path, *records_paths,
                   Path(__file__).resolve(), *sorted(raw_paths)]
    if diag_path and assays_path:
        input_paths.extend([diag_path, assays_path])
    else:
        input_paths.append(ROOT / "02_code/diagnose_mic_baselines.py")
    result = {"status": "feasible_for_training_review" if not blockers else "blocked",
              "generated_at": utc_now(), "protocol_id": protocol["protocol_id"],
              "protocol_sha256": canonical_sha256(protocol),
              "parent_cohort_protocol_id": cohort["protocol_id"], "cohort_size": len(molecules),
              "original_homology_components": int(molecules.homology_component.nunique()),
              "combined_components": len(components), "largest_combined_component": int(components.iloc[0]["n"]),
              "primary_study_identifier_count": len(assay_identifier_ids),
              "primary_study_count_after_alias_merge": len(primary_study_groups),
              "study_bridges_across_original_homology_components": int((bridges.original_homology_components > 1).sum()),
              "folds": fold_summary, "cross_fold_homology_edges": cross_homology,
              "cross_fold_primary_studies": cross_study, "blockers": blockers, "warnings": warnings,
              "training_performed": False, "formal_study_status": "blocked_unmodified",
              "input_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in input_paths},
              "outputs": ["combined_components.csv", "component_summary.csv", "study_aliases.csv", "study_bridges.csv", "fold_assignments.csv", "report.md"] + (["assay_observations.csv"] if not diag else [])}
    (output / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# MIC-only 同论文隔离五折可行性审计", "", f"生成时间：{result['generated_at']}",
             f"协议：`{result['protocol_id']}`（SHA-256 `{result['protocol_sha256']}`）", "",
             f"**状态：`{result['status']}`。** 原队列 {len(molecules)} 条、{result['original_homology_components']} 个同源组件；按原始 MIC 论文继续合并后为 {len(components)} 个组件。最大组件 {result['largest_combined_component']} 条，由 {int(components.iloc[0]['original_homology_components'])} 个原同源组件连接而成。", "",
             f"{result['primary_study_identifier_count']} 个测定关联的 DOI/PMID/DBAASP 论文 ID 在同一引用对象内合并为 {result['primary_study_count_after_alias_merge']} 个论文标识组；{result['study_bridges_across_original_homology_components']} 个论文标识组连接了多个原同源组件。方法引用不作为主测定论文连接。", "",
             "## 五折结果", "", "| 折 | 训练 n | 训练阳性/阴性 | 验证 n | 验证阳性/阴性 | 组件交叉 | 原始论文交叉 | 门禁 |", "|---:|---:|---:|---:|---:|---:|---:|---|"]
    for row in fold_summary:
        lines.append(f"| {row['fold']} | {row['train_n']} | {row['train_positive']}/{row['train_negative']} | {row['validation_n']} | {row['validation_positive']}/{row['validation_negative']} | {row['shared_components']} | {row['shared_primary_studies']} | {'通过' if row['gate_passed'] else '失败'} |")
    if not fold_summary:
        lines.append("没有生成折分配：独立组件数或类别条件在分折前已失败。")
    lines += ["", "## 阻断与警示", ""]
    lines += [f"- 阻断：{message}" for message in blockers] or ["- 阻断：无。"]
    lines += [f"- 警示：{message}" for message in warnings] or ["- 警示：无。"]
    lines += ["", "此审计只检查固定 0.40 同源组件与原始 MIC 论文共同隔离的可行性。它不训练模型，也不改变原双任务正式研究的阻断状态。详细映射见 `combined_components.csv`、`study_aliases.csv` 与 `study_bridges.csv`。", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=PROTOCOL_PATH)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    protocol_path = args.protocol if args.protocol.is_absolute() else ROOT / args.protocol
    result = run(output, protocol_path)
    print(json.dumps({key: result[key] for key in ("status", "combined_components", "largest_combined_component", "folds", "blockers", "warnings")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
