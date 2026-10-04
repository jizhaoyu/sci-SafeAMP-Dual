"""Audit MIC-only evidence coverage and homology-grouped five-fold feasibility.

This script does not train models and never overwrites an existing output.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from research_data import REQUIRED, ResearchDataError, sequence_identity, source_study_ids, validate_records
from research_utils import ROOT, sha256, utc_now


def canonical_digest(value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_protocol(path: Path) -> tuple[dict, str]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    digest = canonical_digest(protocol)
    if protocol.get("protocol_id") != "protocol-mic-01" or protocol.get("protocol_version") != 1:
        raise ValueError("Expected immutable protocol-mic-01 version 1.")
    if protocol.get("status") != "frozen_for_feasibility_audit_only":
        raise ValueError("Protocol is not marked as frozen for feasibility audit only.")
    return protocol, digest


def consolidate_mic(records: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    rows, exclusions = [], []
    for sequence, group in records.groupby("seq", sort=True):
        labels = sorted(set(group.amp.dropna().astype(int)))
        record_ids = group.record_id.astype(str).tolist()
        if len(labels) > 1:
            exclusions.append({"sequence": sequence, "record_ids": record_ids, "reason": "conflicting_rederived_mic_labels"})
            continue
        if not labels:
            exclusions.append({"sequence": sequence, "record_ids": record_ids, "reason": "mic_label_unknown_or_intermediate"})
            continue
        studies = set().union(*(source_study_ids(row) for row in group.itertuples()))
        rows.append({
            "sample_id": hashlib.sha256(sequence.encode("ascii")).hexdigest()[:24],
            "seq": sequence,
            "amp": labels[0],
            "record_ids": json.dumps(record_ids, ensure_ascii=False),
            "source_datasets": "|".join(sorted(set(group.source_dataset.astype(str)))),
            "study_ids": "|".join(sorted(studies)),
        })
    return pd.DataFrame(rows), exclusions


def audit_target_identifiers(records: pd.DataFrame) -> list[dict]:
    """Flag MIC observations lacking an identified E. coli strain or isolate."""
    unresolved_suffixes = {"", "(strain not stated)", "esbl", "ndm", "o157", "o157:h7", "o111", "k88", "k99"}
    rows = []
    for record in records.itertuples(index=False):
        conditions = json.loads(record.assay_conditions)
        for index, observation in enumerate(conditions.get("amp", [])):
            target = observation.get("targetSpecies", {}).get("name", "") if "targetSpecies" in observation else observation.get("target", "")
            target = str(target).strip()
            suffix = re.sub(r"^(?:Escherichia coli|E\. coli)\s*", "", target, flags=re.IGNORECASE).strip().lower()
            note = str(observation.get("note", "")).strip()
            single_isolate_in_note = bool(re.search(r"\bclinical isolate\s+[A-Za-z0-9]+\b", note, flags=re.IGNORECASE))
            if re.search(r"\b(?:isolates|\band\b|\d+\s+(?:MDR\s+)?clinical isolates)\b|,", note, flags=re.IGNORECASE):
                single_isolate_in_note = False
            status = "unresolved_strain_or_isolate" if suffix in unresolved_suffixes and not single_isolate_in_note else "identified_provisionally"
            rows.append({"record_id": record.record_id, "source_dataset": record.source_dataset,
                         "assay_index": index, "target": target, "source_note": note,
                         "strain_identifier_status": status})
    return rows


def run_audit(records_path: Path, supplement_path: Path, protocol_path: Path, output_dir: Path) -> dict:
    records_path, supplement_path, protocol_path, output_dir = map(Path, (records_path, supplement_path, protocol_path, output_dir))
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing audit directory: {output_dir}")
    if not records_path.is_file() or not supplement_path.is_file() or not protocol_path.is_file():
        raise FileNotFoundError("Records, supplement, and protocol JSON must all exist.")
    output_dir.mkdir(parents=True)

    protocol, protocol_sha = load_protocol(protocol_path)
    original = pd.read_csv(records_path)
    supplement = pd.read_csv(supplement_path)
    if set(REQUIRED) - set(original.columns) or set(REQUIRED) - set(supplement.columns):
        raise ResearchDataError("Both input tables must contain the research provenance schema.")
    original["input_cohort"] = "development_source"
    supplement["input_cohort"] = "dramp_candidate_supplement"
    combined = pd.concat([original, supplement], ignore_index=True)

    blockers, warnings = [], []
    try:
        validated = validate_records(combined, verify_raw=True)
        evidence_status = "passed"
        evidence_detail = f"{len(validated)} provenance records passed raw-assay validation and label re-derivation."
    except Exception as exc:
        validated = combined.copy()
        evidence_status = "failed"
        evidence_detail = str(exc)
        blockers.append(f"Raw evidence validation failed: {exc}")

    evidence_rows = []
    for row in validated.itertuples():
        evidence_rows.append({
            "record_id": row.record_id,
            "input_cohort": row.input_cohort,
            "source_dataset": row.source_dataset,
            "sequence": row.seq,
            "length_aa": len(row.seq),
            "declared_amp_label": None if pd.isna(row.amp) else int(row.amp),
            "has_raw_assay_file": bool(Path(row.raw_path).is_absolute() and Path(row.raw_path).is_file()) or (ROOT / str(row.raw_path)).is_file(),
            "primary_reference": str(row.evidence_reference),
            "raw_path": str(row.raw_path),
            "raw_sha256": str(row.raw_sha256),
        })
    pd.DataFrame(evidence_rows).to_csv(output_dir / "evidence_inventory.csv", index=False, encoding="utf-8-sig")

    eligible = validated[
        validated.seq.str.len().between(protocol["molecule_domain"]["min_length_aa"], protocol["molecule_domain"]["max_length_aa"])
        & validated.modifications.astype(str).str.lower().eq("none")
        & validated.evidence_type.eq("experimental")
        & validated.amp.notna()
    ].copy()
    target_rows = audit_target_identifiers(eligible)
    target_audit_path = output_dir / "target_identifier_audit.csv"
    pd.DataFrame(target_rows, columns=["record_id", "source_dataset", "assay_index", "target", "source_note", "strain_identifier_status"]).to_csv(
        target_audit_path, index=False, encoding="utf-8-sig")
    unresolved_targets = [row for row in target_rows if row["strain_identifier_status"] == "unresolved_strain_or_isolate"]
    if unresolved_targets:
        blockers.append(
            f"{len(unresolved_targets)} MIC observations across {len({row['record_id'] for row in unresolved_targets})} records "
            "lack an identified E. coli strain or isolate under protocol-mic-01; review primary papers before release."
        )
    molecules, exclusions = consolidate_mic(eligible)
    pd.DataFrame(exclusions, columns=["sequence", "record_ids", "reason"]).to_csv(output_dir / "exclusions.csv", index=False, encoding="utf-8-sig")
    unresolved_conflicts = [item for item in exclusions if item["reason"] == "conflicting_rederived_mic_labels"]
    if unresolved_conflicts:
        blockers.append(f"{len(unresolved_conflicts)} exact-sequence groups have conflicting re-derived MIC labels.")
    if molecules.empty:
        blockers.append("No labeled eligible molecules remain after exact-sequence consolidation.")

    label_counts = {str(k): int(v) for k, v in molecules.amp.value_counts().sort_index().items()} if not molecules.empty else {}
    group_components = np.array([], dtype=int)
    homology_summary = {"possible_pairs": 0, "above_cutoff_pairs": 0, "component_count": 0, "largest_component": 0}
    pair_rows = []
    if not molecules.empty:
        seqs = molecules.seq.tolist()
        parent = list(range(len(seqs)))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        cutoff = float(protocol["similarity"]["cutoff"])
        for i in range(len(seqs)):
            for j in range(i):
                identity = sequence_identity(seqs[i], seqs[j], identity_mode="alignment")
                is_edge = identity >= cutoff
                pair_rows.append({
                    "sample_id_a": molecules.iloc[j].sample_id,
                    "sample_id_b": molecules.iloc[i].sample_id,
                    "record_ids_a": molecules.iloc[j].record_ids,
                    "record_ids_b": molecules.iloc[i].record_ids,
                    "identity": identity,
                    "same_homology_component": is_edge,
                })
                if is_edge:
                    parent[find(i)] = find(j)
        roots = [find(i) for i in range(len(seqs))]
        root_to_id = {root: component_id for component_id, root in enumerate(sorted(set(roots)))}
        group_components = np.array([root_to_id[root] for root in roots], dtype=int)
        molecules["homology_component"] = group_components
        sizes = molecules.groupby("homology_component").size()
        homology_summary = {
            "possible_pairs": len(pair_rows),
            "above_cutoff_pairs": int(sum(r["same_homology_component"] for r in pair_rows)),
            "component_count": int(len(sizes)),
            "largest_component": int(sizes.max()),
            "largest_component_fraction": float(sizes.max() / len(molecules)),
        }
        pd.DataFrame(pair_rows).to_csv(output_dir / "all_member_similarity.csv", index=False, encoding="utf-8-sig")
        molecules.to_csv(output_dir / "molecule_components.csv", index=False, encoding="utf-8-sig")

    if set(label_counts) != {"0", "1"}:
        blockers.append(f"Both MIC classes are required; observed class counts are {label_counts}.")
    if homology_summary["component_count"] < int(protocol["validation"]["folds"]):
        blockers.append(f"Only {homology_summary['component_count']} independent homology components remain for {protocol['validation']['folds']} folds.")

    fold_rows, fold_summary = [], []
    fold_count = int(protocol["validation"]["folds"])
    if not molecules.empty and homology_summary["component_count"] >= fold_count and set(label_counts) == {"0", "1"}:
        splitter = StratifiedGroupKFold(n_splits=fold_count, shuffle=True, random_state=int(protocol["validation"]["seed"]))
        y = molecules.amp.astype(int).to_numpy()
        for fold, (train_idx, validation_idx) in enumerate(splitter.split(molecules.seq, y, group_components)):
            train_classes = set(y[train_idx].tolist())
            validation_classes = set(y[validation_idx].tolist())
            group_overlap = set(group_components[train_idx]) & set(group_components[validation_idx])
            fold_ok = train_classes == {0, 1} and validation_classes == {0, 1} and not group_overlap
            if not fold_ok:
                blockers.append(f"Fold {fold} fails class-coverage or component-isolation gate: train={sorted(train_classes)}, validation={sorted(validation_classes)}, shared_groups={len(group_overlap)}.")
            fold_summary.append({
                "fold": fold,
                "train_molecules": len(train_idx),
                "validation_molecules": len(validation_idx),
                "train_positive": int((y[train_idx] == 1).sum()),
                "train_negative": int((y[train_idx] == 0).sum()),
                "validation_positive": int((y[validation_idx] == 1).sum()),
                "validation_negative": int((y[validation_idx] == 0).sum()),
                "train_components": int(len(set(group_components[train_idx]))),
                "validation_components": int(len(set(group_components[validation_idx]))),
                "shared_components": len(group_overlap),
                "gate_passed": fold_ok,
            })
            for role, indices in (("train", train_idx), ("validation", validation_idx)):
                for idx in indices:
                    molecule = molecules.iloc[int(idx)]
                    fold_rows.append({"sample_id": molecule.sample_id, "seq": molecule.seq, "amp": int(molecule.amp), "homology_component": int(group_components[idx]), "fold": fold, "role": role, "record_ids": molecule.record_ids})
        pd.DataFrame(fold_rows).to_csv(output_dir / "fold_assignments.csv", index=False, encoding="utf-8-sig")
    elif molecules.empty:
        pd.DataFrame(columns=["sample_id", "seq", "amp", "homology_component", "fold", "role", "record_ids"]).to_csv(output_dir / "fold_assignments.csv", index=False, encoding="utf-8-sig")
    else:
        warnings.append("Fold assignment skipped because both classes or five independent components are not present.")

    if fold_summary:
        validation_sizes = [row["validation_molecules"] for row in fold_summary]
        if homology_summary["largest_component_fraction"] >= 0.5 or max(validation_sizes) >= 2 * min(validation_sizes):
            warnings.append(
                "Severe fold-size imbalance from an indivisible homology component: "
                f"largest component={homology_summary['largest_component']} of {len(molecules)} molecules "
                f"({homology_summary['largest_component_fraction']:.1%}); validation fold sizes="
                f"{validation_sizes}. Preserve all-member isolation and review the estimand before model training."
            )

    n_development = int((validated.input_cohort == "development_source").sum())
    n_supplement = int((validated.input_cohort == "dramp_candidate_supplement").sum())
    study_ids = set().union(*(source_study_ids(row) for row in eligible.itertuples())) if not eligible.empty else set()
    status = "feasible_for_training_review" if not blockers else "blocked"
    summary = {
        "status": status,
        "generated_at": utc_now(),
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": protocol_sha,
        "protocol_path": str(protocol_path),
        "existing_records_path": str(records_path),
        "existing_records_sha256": sha256(records_path),
        "existing_record_count": n_development,
        "supplement_records_path": str(supplement_path),
        "supplement_records_sha256": sha256(supplement_path),
        "supplement_record_count": n_supplement,
        "combined_evidence_gate": {"status": evidence_status, "detail": evidence_detail},
        "target_identifier_gate": {"status": "failed" if unresolved_targets else "passed",
                                   "unresolved_observations": len(unresolved_targets),
                                   "affected_records": len({row["record_id"] for row in unresolved_targets})},
        "eligible_record_count_before_exact_sequence_merge": int(len(eligible)),
        "unique_labeled_molecule_count": int(len(molecules)),
        "amp_label_counts": label_counts,
        "primary_study_identifier_count": len(study_ids),
        "source_dataset_record_counts": {str(k): int(v) for k, v in eligible.source_dataset.value_counts().sort_index().items()},
        "homology": homology_summary,
        "folds": fold_summary,
        "blockers": blockers,
        "warnings": warnings,
        "training_started": False,
        "model_results_generated": False,
        "outputs": {
            "evidence_inventory": str(output_dir / "evidence_inventory.csv"),
            "target_identifier_audit": str(target_audit_path),
            "exclusions": str(output_dir / "exclusions.csv"),
            "molecule_components": str(output_dir / "molecule_components.csv"),
            "all_member_similarity": str(output_dir / "all_member_similarity.csv"),
            "fold_assignments": str(output_dir / "fold_assignments.csv"),
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "report.md").write_text(render_report(summary), encoding="utf-8")
    return summary


def render_report(summary: dict) -> str:
    folds = summary["folds"]
    fold_table = "\n".join(
        f"| {x['fold']} | {x['train_molecules']} | {x['train_positive']} | {x['train_negative']} | {x['validation_molecules']} | {x['validation_positive']} | {x['validation_negative']} | {x['shared_components']} | {x['gate_passed']} |"
        for x in folds
    ) or "| — | — | — | — | — | — | — | — | 未分配 |"
    blockers = "\n".join(f"- {x}" for x in summary["blockers"]) or "- 无"
    return f"""# MIC-only 五折可行性审计

**状态：** `{summary['status']}`  
**生成时间：** {summary['generated_at']}  
**协议：** `{summary['protocol_id']}`，SHA-256 `{summary['protocol_sha256']}`  
**现有记录：** {summary['existing_record_count']}；**DRAMP 补充记录：** {summary['supplement_record_count']}  
**模型训练：** 未开始；**模型结果：** 未生成

## 证据与队列

- 合并证据门禁：{summary['combined_evidence_gate']['status']} — {summary['combined_evidence_gate']['detail']}
- 菌株／分离株标识门禁：{summary['target_identifier_gate']['status']}；{summary['target_identifier_gate']['unresolved_observations']} 条测定、{summary['target_identifier_gate']['affected_records']} 条记录待原文核对。逐条见 `target_identifier_audit.csv`。
- 可判标签记录（合并精确序列前）：{summary['eligible_record_count_before_exact_sequence_merge']}
- 唯一有标签序列：{summary['unique_labeled_molecule_count']}
- MIC 标签计数（0=阴性、1=阳性）：`{summary['amp_label_counts']}`
- 原始研究标识数：{summary['primary_study_identifier_count']}
- 同源组件：{summary['homology']['component_count']}；最大组件：{summary['homology']['largest_component']}；`>=0.40` 成员对：{summary['homology']['above_cutoff_pairs']}

## 五折类别及隔离

| 折 | 训练分子 | 训练阳性 | 训练阴性 | 验证分子 | 验证阳性 | 验证阴性 | 跨折共享组件 | 通过 |
|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
{fold_table}

## 阻断项

{blockers}

## 警示

{chr(10).join(f"- {x}" for x in summary['warnings']) or '- 无'}

完整记录见同目录 `evidence_inventory.csv`、`exclusions.csv`、`molecule_components.csv`、`all_member_similarity.csv`、`fold_assignments.csv` 和 `manifest.json`。
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--supplement", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_audit(args.records, args.supplement, args.protocol, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
