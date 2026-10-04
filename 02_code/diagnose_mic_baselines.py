"""Describe the fixed MIC cohort, assay evidence, homology graph, and OOF errors.

This is a descriptive audit. It does not refit models or alter frozen folds.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
import re
from types import SimpleNamespace

import numpy as np
import pandas as pd

from assay_records import SingleAssayObservation, evaluate_assay_for_amp
from research_data import source_study_ids
from research_utils import ROOT, utc_now

AUDIT = ROOT / "03_experiments/audits/mic_only_cohort_20261001_v3"
RUN = ROOT / "03_experiments/runs/mic_only_baselines_20261001_v3"
SOURCES = [
    ROOT / "03_experiments/prepared/amd02_evidence_clean_20261001/records.csv",
    ROOT / "03_experiments/audits/dramp_verified_ecoli_mic_20261001_v6/records.csv",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ids_from_reference(reference: object) -> set[str]:
    identifiers = source_study_ids(SimpleNamespace(evidence_reference=json.dumps(reference, ensure_ascii=False)))
    if isinstance(reference, dict) and reference.get("id") and reference.get("title"):
        identifiers.add(f"dbaasp_article:{reference['id']}")
    return identifiers


def resolve_assay_studies(obs: dict, references: list, raw_entry: dict | None = None) -> tuple[set[str], str]:
    if raw_entry:
        primary = set()
        if raw_entry.get("pmid"):
            primary.add(f"pmid:{raw_entry['pmid']}")
        if raw_entry.get("doi"):
            primary.add(f"doi:{str(raw_entry['doi']).lower()}")
        declared = set().union(*(ids_from_reference(reference) for reference in references))
        if primary and primary <= declared:
            return primary, "raw_primary_reference"
    marker = str(obs.get("reference", "")).strip()
    if marker and re.fullmatch(r"\d+(?:\s*[,;]\s*\d+)*", marker):
        indices = [int(value) - 1 for value in re.split(r"\s*[,;]\s*", marker)]
        if all(0 <= index < len(references) for index in indices):
            identifiers = set().union(*(ids_from_reference(references[index]) for index in indices))
            if identifiers:
                return identifiers, "indexed_assay_reference"
    if len(references) == 1:
        identifiers = ids_from_reference(references[0])
        if identifiers:
            return identifiers, "single_reference_inferred"
    return set(), "unresolved_assay_reference"


def assay_rows(records: pd.DataFrame, sample_by_record: dict[str, str]) -> list[dict]:
    rows, raw_cache = [], {}
    for row in records.itertuples(index=False):
        if row.record_id not in sample_by_record:
            continue
        conditions = json.loads(row.assay_conditions)
        references = json.loads(row.evidence_reference)
        if not isinstance(references, list):
            references = [references]
        raw_entry = None
        if row.source_dataset == "DRAMP":
            raw_path = ROOT / row.raw_path
            if raw_path not in raw_cache:
                raw_cache[raw_path] = json.loads(raw_path.read_text(encoding="utf-8"))
            matches = [entry for entry in raw_cache[raw_path]["records"] if entry.get("record_id") == row.record_id]
            if len(matches) != 1:
                raise ValueError(f"Cannot resolve exact DRAMP raw evidence for {row.record_id}.")
            raw_entry = matches[0]
        for index, item in enumerate(conditions.get("amp", [])):
            is_dbaasp = "targetSpecies" in item
            target = str(item.get("targetSpecies", {}).get("name", "")) if is_dbaasp else str(item.get("target", ""))
            raw_value = str(item.get("concentration", "")) if is_dbaasp else str(item.get("raw_value", ""))
            unit = str(item.get("unit", {}).get("name", "")) if is_dbaasp else str(item.get("raw_unit", ""))
            endpoint = str(item.get("activityMeasureValue", "")) if is_dbaasp else "MIC"
            medium = item.get("medium", "")
            if isinstance(medium, dict):
                medium = medium.get("name", "")
            assay = SingleAssayObservation(endpoint="amp", target_organism_or_cell=target,
                                           metric_name=endpoint, raw_value=raw_value, raw_unit=unit)
            evaluate_assay_for_amp(assay, row.seq)
            study_ids, resolution = resolve_assay_studies(item, references, raw_entry)
            rows.append({
                "sample_id": sample_by_record[row.record_id], "record_id": row.record_id,
                "source_dataset": row.source_dataset, "assay_index": index,
                "target": target, "medium": str(medium), "method": str(item.get("method", "")),
                "raw_mic": raw_value, "raw_unit": unit,
                "normalized_low_ug_ml": assay.normalized_low_ug_ml,
                "normalized_high_ug_ml": assay.normalized_high_ug_ml,
                "eligible": assay.eligible, "derived_label": assay.derived_label,
                "reference_resolution": resolution,
                "assay_study_ids": "|".join(sorted(study_ids)),
            })
    return rows


def reported_names(records: pd.DataFrame, sample_by_record: dict[str, str]) -> pd.DataFrame:
    rows, checked = [], {}
    for row in records.itertuples(index=False):
        if row.record_id not in sample_by_record:
            continue
        raw_path = Path(row.raw_path)
        if not raw_path.is_absolute():
            raw_path = ROOT / raw_path
        if raw_path not in checked:
            checked[raw_path] = digest(raw_path)
        if checked[raw_path] != row.raw_sha256:
            raise ValueError(f"Raw name source checksum changed for {row.record_id}.")
        name = ""
        if row.source_dataset == "DBAASP":
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            name = str(raw.get("majorName") or raw.get("name") or "").strip()
        rows.append({"sample_id": sample_by_record[row.record_id], "record_id": row.record_id,
                     "source_dataset": row.source_dataset, "reported_peptide_name": name,
                     "raw_path": row.raw_path, "raw_sha256": row.raw_sha256})
    return pd.DataFrame(rows)


def study_reference_inventory(records: pd.DataFrame, sample_by_record: dict[str, str]) -> pd.DataFrame:
    by_identifier = defaultdict(lambda: {"titles": set(), "years": set(), "record_ids": set(), "source_datasets": set()})
    for row in records.itertuples(index=False):
        if row.record_id not in sample_by_record:
            continue
        references = json.loads(row.evidence_reference)
        if not isinstance(references, list):
            references = [references]
        for reference in references:
            if not isinstance(reference, dict):
                continue
            for identifier in ids_from_reference(reference):
                entry = by_identifier[identifier]
                if reference.get("title"):
                    entry["titles"].add(str(reference["title"]))
                if reference.get("year"):
                    entry["years"].add(str(reference["year"]))
                entry["record_ids"].add(row.record_id)
                entry["source_datasets"].add(row.source_dataset)
    return pd.DataFrame([
        {"study_id": identifier, "titles": " | ".join(sorted(values["titles"])),
         "years": "|".join(sorted(values["years"])),
         "source_datasets": "|".join(sorted(values["source_datasets"])),
         "record_count": len(values["record_ids"]),
         "record_ids": "|".join(sorted(values["record_ids"]))}
        for identifier, values in sorted(by_identifier.items())
    ])


def graph_diagnostics(molecules: pd.DataFrame, pairs: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    component = molecules.set_index("sample_id").homology_component.to_dict()
    edges = pairs[pairs.identity >= 0.4]
    edge_counts = Counter(component[a] for a in edges.sample_id_a)
    rows = []
    for cid, group in molecules.groupby("homology_component", sort=True):
        n = len(group)
        label_count = group.amp.value_counts().to_dict()
        studies = set().union(*(set(str(value).split("|")) - {""} for value in group.study_ids))
        rows.append({"homology_component": int(cid), "n": n, "positive": int(label_count.get(1, 0)),
                     "negative": int(label_count.get(0, 0)), "distinct_declared_study_ids": len(studies),
                     "source_counts": json.dumps(group.source_datasets.value_counts().to_dict(), ensure_ascii=False),
                     "length_min": int(group.seq.str.len().min()), "length_median": float(group.seq.str.len().median()),
                     "length_max": int(group.seq.str.len().max()), "direct_edges_above_0_40": int(edge_counts[cid]),
                     "direct_edge_density": float(edge_counts[cid] / (n * (n - 1) / 2)) if n > 1 else None})
    result = pd.DataFrame(rows).sort_values(["n", "homology_component"], ascending=[False, True])
    giant = result.iloc[0]
    giant_ids = set(molecules.loc[molecules.homology_component == giant.homology_component, "sample_id"])
    adjacency = {sample_id: set() for sample_id in giant_ids}
    for a, b in edges.loc[edges.sample_id_a.isin(giant_ids), ["sample_id_a", "sample_id_b"]].itertuples(index=False, name=None):
        adjacency[a].add(b)
        adjacency[b].add(a)
    # The connected component may contain distant members joined by transitive bridges.
    distances, direct_degrees = [], [len(adjacency[node]) for node in adjacency]
    for start in adjacency:
        found = {start: 0}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for neighbor in adjacency[node]:
                if neighbor not in found:
                    found[neighbor] = found[node] + 1
                    queue.append(neighbor)
        if len(found) != len(giant_ids):
            raise ValueError("Audited giant component is disconnected under the frozen 0.40 edge rule.")
        distances.extend(value for other, value in found.items() if other > start)
    giant_pairs = pairs[pairs.sample_id_a.isin(giant_ids) & pairs.sample_id_b.isin(giant_ids)]
    graph = {"component_id": int(giant.homology_component), "n": len(giant_ids),
             "direct_edges": int(giant.direct_edges_above_0_40), "possible_pairs": int(len(giant_pairs)),
             "direct_edge_fraction": float(giant.direct_edges_above_0_40 / len(giant_pairs)),
             "median_pair_identity": float(giant_pairs.identity.median()),
             "pairs_below_0_40": int((giant_pairs.identity < 0.4).sum()),
             "median_shortest_path_edges": float(np.median(distances)),
             "maximum_shortest_path_edges": int(max(distances)),
             "median_direct_degree": float(np.median(direct_degrees)),
             "isolated_within_component": int(sum(degree == 0 for degree in direct_degrees))}
    return result, graph


def study_overlap(molecules: pd.DataFrame, assays: pd.DataFrame) -> pd.DataFrame:
    assay_ids = defaultdict(set)
    for row in assays.itertuples(index=False):
        assay_ids[row.sample_id].update(set(str(row.assay_study_ids).split("|")) - {""})
    rows = []
    for scope in ("declared_references", "assay_linked_references"):
        by_id = defaultdict(set)
        for row in molecules.itertuples(index=False):
            identifiers = set(str(row.study_ids).split("|")) - {""} if scope == "declared_references" else assay_ids[row.sample_id]
            for identifier in identifiers:
                by_id[identifier].add((row.sample_id, int(row.fold)))
        for identifier, members in by_id.items():
            folds = sorted({fold for _, fold in members})
            if len(folds) > 1:
                rows.append({"reference_scope": scope, "study_id": identifier,
                             "molecules": len({sample_id for sample_id, _ in members}),
                             "folds": "|".join(map(str, folds)), "fold_count": len(folds)})
    return pd.DataFrame(rows, columns=["reference_scope", "study_id", "molecules", "folds", "fold_count"]).sort_values(
        ["reference_scope", "molecules", "study_id"], ascending=[True, False, True])


def run(output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing audit: {output}")
    audit = json.loads((AUDIT / "manifest.json").read_text(encoding="utf-8"))
    baseline = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    if audit["status"] != "feasible_for_training_review" or baseline["status"] != "exploratory_baselines_completed":
        raise ValueError("The source audit or exploratory baseline is not complete.")
    if baseline["audit_manifest_sha256"] != digest(AUDIT / "manifest.json") or baseline["fold_assignments_sha256"] != digest(AUDIT / "fold_assignments.csv"):
        raise ValueError("Baseline run is not tied to the selected immutable audit and folds.")
    if digest(SOURCES[0]) != audit["existing_records_sha256"] or digest(SOURCES[1]) != audit["supplement_records_sha256"]:
        raise ValueError("Source records have changed since the evidence audit.")
    molecules = pd.read_csv(AUDIT / "molecule_components.csv")
    fold_rows = pd.read_csv(AUDIT / "fold_assignments.csv")
    validation = fold_rows[fold_rows.role == "validation"][["sample_id", "fold"]]
    if validation.sample_id.duplicated().any() or len(validation) != len(molecules):
        raise ValueError("Each molecule must have exactly one fixed validation fold.")
    molecules = molecules.merge(validation, on="sample_id", validate="one_to_one")
    predictions = pd.read_csv(RUN / "oof_predictions.csv")
    if len(predictions) != len(molecules) * 3 or predictions.duplicated(["model", "sample_id"]).any():
        raise ValueError("Incomplete or duplicated baseline OOF predictions.")
    predictions = predictions.merge(molecules[["sample_id", "amp", "homology_component", "fold"]], on="sample_id", suffixes=("", "_audit"), validate="many_to_one")
    if (predictions.y_true != predictions.amp).any() or (predictions.fold != predictions.fold_audit).any():
        raise ValueError("Prediction labels/folds disagree with audited cohort.")
    sources = pd.concat([pd.read_csv(path) for path in SOURCES], ignore_index=True)
    sample_by_record = {record_id: row.sample_id for row in molecules.itertuples(index=False) for record_id in json.loads(row.record_ids)}
    names = reported_names(sources, sample_by_record)
    references = study_reference_inventory(sources, sample_by_record)
    assay = pd.DataFrame(assay_rows(sources, sample_by_record))
    if assay.empty or set(assay.sample_id) != set(molecules.sample_id):
        raise ValueError("Selected molecules lack parsed assay observations.")
    pairs = pd.read_csv(AUDIT / "all_member_similarity.csv")
    if len(pairs) != len(molecules) * (len(molecules) - 1) // 2:
        raise ValueError("All-member similarity audit is incomplete.")
    components, graph = graph_diagnostics(molecules, pairs)
    giant_id = graph["component_id"]
    name_by_sample = names.groupby("sample_id").reported_peptide_name.agg(lambda values: "|".join(sorted(set(str(value) for value in values if str(value).strip()))))
    molecules["reported_peptide_names"] = molecules.sample_id.map(name_by_sample).fillna("")
    molecules["in_largest_component"] = molecules.homology_component.eq(giant_id)
    studies = study_overlap(molecules, assay)
    studies = studies.merge(references[["study_id", "titles", "years", "source_datasets"]], on="study_id", how="left", validate="many_to_one")
    fold_composition = []
    for fold, group in molecules.groupby("fold"):
        study_ids = set().union(*(set(str(value).split("|")) - {""} for value in group.study_ids))
        fold_composition.append({"fold": int(fold), "n": len(group), "positive": int(group.amp.sum()),
                                 "negative": int(len(group) - group.amp.sum()),
                                 "largest_component_molecules": int(group.in_largest_component.sum()),
                                 "DBAASP_molecules": int(group.source_datasets.str.contains("DBAASP").sum()),
                                 "DRAMP_molecules": int(group.source_datasets.str.contains("DRAMP").sum()),
                                 "length_median": float(group.seq.str.len().median()),
                                 "declared_study_ids": len(study_ids)})
    fold_frame = pd.DataFrame(fold_composition)
    predictions["wrong_at_0_5"] = (predictions.probability >= 0.5).astype(int) != predictions.y_true
    predictions["absolute_probability_error"] = (predictions.probability - predictions.y_true).abs()
    predictions = predictions.merge(molecules[["sample_id", "record_ids", "source_datasets", "study_ids", "in_largest_component"]], on="sample_id", validate="many_to_one")
    errors = predictions.groupby(["model", "fold", "in_largest_component", "y_true"], dropna=False).agg(
        n=("sample_id", "size"), wrong=("wrong_at_0_5", "sum"),
        mean_probability=("probability", "mean")).reset_index()
    errors["error_rate_at_0_5"] = errors.wrong / errors.n
    predictions["predicted_positive_at_0_5"] = predictions.probability.ge(0.5)
    fold_predictions = predictions.groupby(["model", "fold"]).agg(
        n=("sample_id", "size"), measured_positive_fraction=("y_true", "mean"),
        predicted_positive_fraction=("predicted_positive_at_0_5", "mean"),
        mean_probability=("probability", "mean")).reset_index()
    shared_errors = predictions.groupby("sample_id").agg(models_wrong=("wrong_at_0_5", "sum")).reset_index()
    shared_errors = shared_errors.merge(molecules[["sample_id", "fold", "amp", "in_largest_component", "record_ids", "study_ids"]], on="sample_id", validate="one_to_one")
    source_errors = predictions.groupby(["model", "source_datasets"]).agg(
        n=("sample_id", "size"), wrong=("wrong_at_0_5", "sum")).reset_index()
    source_errors["error_rate_at_0_5"] = source_errors.wrong / source_errors.n
    assay_studies = assay[["sample_id", "assay_study_ids"]].copy()
    assay_studies["study_id"] = assay_studies.assay_study_ids.str.split("|")
    assay_studies = assay_studies.explode("study_id")[["sample_id", "study_id"]].dropna().drop_duplicates()
    study_errors = predictions.merge(assay_studies, on="sample_id", validate="many_to_many").groupby(
        ["model", "study_id"]).agg(n=("sample_id", "nunique"), wrong=("wrong_at_0_5", "sum")).reset_index()
    study_errors["error_rate_at_0_5"] = study_errors.wrong / study_errors.n
    study_errors = study_errors.merge(references[["study_id", "titles", "years"]], on="study_id", how="left", validate="many_to_one")
    output.mkdir(parents=True)
    molecules.to_csv(output / "molecule_diagnostics.csv", index=False)
    names.to_csv(output / "reported_name_inventory.csv", index=False)
    references.to_csv(output / "study_reference_inventory.csv", index=False)
    assay.to_csv(output / "assay_observations.csv", index=False)
    components.to_csv(output / "component_summary.csv", index=False)
    fold_frame.to_csv(output / "fold_composition.csv", index=False)
    studies.to_csv(output / "cross_fold_study_overlap.csv", index=False)
    predictions.to_csv(output / "prediction_errors.csv", index=False)
    errors.to_csv(output / "error_summary.csv", index=False)
    fold_predictions.to_csv(output / "fold_prediction_distribution.csv", index=False)
    shared_errors.to_csv(output / "shared_errors.csv", index=False)
    source_errors.to_csv(output / "source_error_summary.csv", index=False)
    study_errors.to_csv(output / "study_error_summary.csv", index=False)
    exact = assay[assay.eligible & assay.normalized_low_ug_ml.notna() & assay.normalized_low_ug_ml.eq(assay.normalized_high_ug_ml)]
    giant_molecules = molecules[molecules.in_largest_component]
    outside_molecules = molecules[~molecules.in_largest_component]
    unresolved = int(assay.assay_study_ids.eq("").sum())
    crossfold_counts = studies.groupby("reference_scope").size().to_dict()
    error_group = predictions.groupby(["model", "in_largest_component"]).wrong_at_0_5.agg(["sum", "count"])
    all_three_wrong = shared_errors[shared_errors.models_wrong == 3]
    fold0_train_positive = int(outside_molecules.amp.sum())
    fold0_val_positive = int(giant_molecules.amp.sum())
    named_giant = giant_molecules.reported_peptide_names[giant_molecules.reported_peptide_names.ne("")]
    name_examples = []
    for fragment in ("Magainin", "Apidaecin", "Temporin", "Bactenecin", "Pyrrhocoricin"):
        matches = sorted(value for value in named_giant if fragment.lower() in value.lower())
        if matches:
            name_examples.append(matches[0])
    lines = ["# MIC-only 基线失败原因诊断", "", f"生成时间：{utc_now()}",
             f"数据：`{AUDIT.relative_to(ROOT)}`；协议 `{audit['protocol_id']}`；基线协议 `{baseline['protocol_id']}`。", "",
             "## 核心发现", "",
             f"- 最大同源组件为 {giant_id}，包含 {len(giant_molecules)}/{len(molecules)} 条序列（{len(giant_molecules)/len(molecules):.1%}），阳性 {int(giant_molecules.amp.sum())}、阴性 {int((1-giant_molecules.amp).sum())}。其余 {len(outside_molecules)} 条中阳性 {int(outside_molecules.amp.sum())}、阴性 {int((1-outside_molecules.amp).sum())}。",
             f"- 大组件内直接达到 0.40 一致性的序列对为 {graph['direct_edges']}/{graph['possible_pairs']}（{graph['direct_edge_fraction']:.1%}）；其余 {graph['pairs_below_0_40']} 对依靠传递路径处于同一组件。组件内两两一致性中位数 {graph['median_pair_identity']:.3f}，最短路径中位数 {graph['median_shortest_path_edges']:.1f} 条边、最长 {graph['maximum_shortest_path_edges']} 条边。这是协议定义的连通组件，不等于已鉴定的单一生物学家族。",
             f"- 大组件 {len(named_giant)}/{len(giant_molecules)} 条有原数据库报告的肽名称，示例：{'；'.join(name_examples)}。名称显示成分多样，但数据库名称不是经审定的家族分类；完整名称及原始文件哈希见 `reported_name_inventory.csv`。",
             f"- 折 0 的训练集只有 {len(outside_molecules)} 条，阳性 {fold0_train_positive}/{len(outside_molecules)}（{fold0_train_positive/len(outside_molecules):.1%}）；验证集是整个大组件，阳性 {fold0_val_positive}/{len(giant_molecules)}（{fold0_val_positive/len(giant_molecules):.1%}）。训练规模与类别比例同时变化，因此不能将折 0 的错误单独归因于序列家族。",
             f"- 声明参考文献中 {crossfold_counts.get('declared_references', 0)} 个标识出现在多个折；可关联测定的参考文献中 {crossfold_counts.get('assay_linked_references', 0)} 个标识出现在多个折。标识包括 DOI、PMID 和 DBAASP 内部论文 ID，同篇论文可有多个别名，因此数量不等于独立论文数。关联依据为 DBAASP 测定引用编号或 DRAMP 原始记录的主论文标识。标识、论文题名和涉及折位于 `cross_fold_study_overlap.csv`，完整来源位于 `study_reference_inventory.csv`。跨折同论文提示来源相关性，不能单凭它断言标签泄漏。",
             f"- {len(assay)} 条 MIC 测定观察均可推导二值标签，其中 {unresolved} 条未能关联到来源记录中的主论文标识；缺少 DOI/PMID 的 DBAASP 引用使用其源数据库论文 ID。{len(exact)} 条可规范化为精确数值，其余 {len(assay)-len(exact)} 条为有界/删失数值。中位数仅对精确、合格测定计算。",
             f"- {len(all_three_wrong)} 条序列被三个模型同时错分，其中 {int(all_three_wrong.in_largest_component.sum())} 条在大组件；这只是固定 0.5 阈值的描述，不证明测定标签有误。", "",
             "- 按测定主论文关联，PMID 42206144 / DOI 10.1038/s42256-026-01237-5 的 10 条记录分散在 4 折，其中 7 条为阴性；固定阈值下逻辑回归错分 9 条，RBF-SVM 与随机森林各错分 8 条。该论文在表中会以 PMID 与 DOI 两个标识出现，应按同一来源解读；样本量太小，不能据此推断整篇论文的数据有误。", "",
             "## 五折构成", "", "| 折 | n | 阳性 | 阴性 | 大组件 | DBAASP | DRAMP | 序列长度中位数 |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in fold_frame.itertuples(index=False):
        lines.append(f"| {row.fold} | {row.n} | {row.positive} | {row.negative} | {row.largest_component_molecules} | {row.DBAASP_molecules} | {row.DRAMP_molecules} | {row.length_median:.1f} |")
    lines += ["", "## 原始 MIC 测定分布", "", "| 组别 | 合格精确 MIC 观察数 | 精确 MIC 中位数（µg/mL） |", "|---|---:|---:|"]
    for name, ids in (("大组件", set(giant_molecules.sample_id)), ("其余组件", set(outside_molecules.sample_id))):
        selected = exact[exact.sample_id.isin(ids)]
        median = f"{selected.normalized_low_ug_ml.median():.2f}" if not selected.empty else "不可计算"
        lines.append(f"| {name} | {len(selected)} | {median} |")
    lines += ["", "## 固定阈值下的错误（描述性）", "", "| 模型 | 大组件错误数/样本数 | 其余组件错误数/样本数 |", "|---|---:|---:|"]
    for model in sorted(predictions.model.unique()):
        large = error_group.loc[(model, True)]
        small = error_group.loc[(model, False)]
        lines.append(f"| {model} | {int(large['sum'])}/{int(large['count'])} | {int(small['sum'])}/{int(small['count'])} |")
    lines += ["", "## 各折预测阳性比例", "", "| 模型 | 折 | 实测阳性比例 | 预测阳性比例@0.5 | 平均预测概率 |", "|---|---:|---:|---:|---:|"]
    for row in fold_predictions.itertuples(index=False):
        lines.append(f"| {row.model} | {row.fold} | {row.measured_positive_fraction:.3f} | {row.predicted_positive_fraction:.3f} | {row.mean_probability:.3f} |")
    lines += ["", "## 解读与下一步", "", "以上均为事后描述性诊断，没有重新分折、重训或显著性检验。`source_error_summary.csv` 和 `study_error_summary.csv` 提供来源分层错分计数；单个 DRAMP 来源只有 4 条，不能据此比较数据库性能。论文标识与实验条件的异质性需要逐条审阅，不能由这些表格自动判定为错误标签。重点检查 `assay_observations.csv` 中的测定值、菌株、培养基及文献关联，以及 `shared_errors.csv` 中多个模型同时错分的序列。折 0 的预测阳性比例低于实测比例，可能与训练集较小、类别比例变化、特征域变化或概率估计有关；本审计不能区分这些原因。若要评估新的 ESM 基线，应另行冻结方案并保持同一审计折。", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    manifest = {"status": "descriptive_diagnostics_completed", "generated_at": utc_now(),
                "audit_protocol_id": audit["protocol_id"], "baseline_protocol_id": baseline["protocol_id"],
                "inputs_sha256": {str(path.relative_to(ROOT)): digest(path) for path in [*SOURCES, AUDIT / "manifest.json", AUDIT / "molecule_components.csv", AUDIT / "fold_assignments.csv", AUDIT / "all_member_similarity.csv", RUN / "manifest.json", RUN / "oof_predictions.csv"]},
                "n_molecules": len(molecules), "n_assay_observations": len(assay), "largest_component_graph": graph,
                "outputs": ["report.md", "molecule_diagnostics.csv", "reported_name_inventory.csv", "study_reference_inventory.csv", "assay_observations.csv", "component_summary.csv", "fold_composition.csv", "cross_fold_study_overlap.csv", "prediction_errors.csv", "error_summary.csv", "fold_prediction_distribution.csv", "shared_errors.csv", "source_error_summary.csv", "study_error_summary.csv"],
                "training_performed": False, "formal_study_status": "blocked_unmodified"}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    result = run(output)
    print(json.dumps({key: result[key] for key in ("status", "n_molecules", "n_assay_observations", "largest_component_graph")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
