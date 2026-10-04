"""Merge locally reviewed MIC candidates, audit every pair and publish blocked readiness."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from audit_mic_independent_sources import molecular_weight
from audit_mic_reviewed_subset_hirsch import DisjointSet
from audit_mic_reviewed_subset_ludwig import verify
from public_data import bounds, measurement_label
from research_data import sequence_identity
from research_utils import ROOT, sha256, utc_now, write_json

BASE = ROOT / "03_experiments/audits/mic_confirmed_acid_subset_20261002_v1"
SOURCES = ROOT / "03_experiments/audits/mic_independent_sources_review_20261002_v1"
PREVIOUS = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v8.json"
PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-01.json"
FORMAL = ROOT / "04_paper/research_status.json"


def run(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite cohort: {output}")
    base, source = verify(BASE), verify(SOURCES)
    for manifest, generator in ((base, "audit_mic_confirmed_acid_subset.py"),
                                (source, "audit_mic_independent_sources.py")):
        if manifest["script_sha256"] != sha256(ROOT / "02_code" / generator):
            raise ValueError(f"Frozen generator changed: {generator}")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    expected_similarity = {"match_score": 2, "mismatch_score": -1, "gap_score": -2, "cutoff": 0.40,
                           "traceback_tie_break": "diagonal_then_up_then_left", "comparison_scope": "all unique molecule pairs"}
    if (any(protocol["similarity"].get(key) != value for key, value in expected_similarity.items())
            or protocol["validation"]["folds"] != 5 or protocol["validation"]["seed"] != 42
            or protocol["label_rule"]["positive_if_upper_bound_ug_ml_lte"] != 32
            or protocol["label_rule"]["negative_if_lower_bound_ug_ml_gte"] != 128
            or protocol["molecule_domain"]["min_length_aa"] != 10
            or protocol["molecule_domain"]["max_length_aa"] != 50
            or protocol["molecule_domain"]["backbone"] != "linear"
            or base["records_released_for_training"] != 0 or source["records_released_for_training"] != 0):
        raise ValueError("Frozen audit rules or release status changed.")
    molecules = pd.read_csv(BASE / "candidate_molecules.csv", keep_default_na=False).drop(columns="review_component")
    observations = pd.read_csv(BASE / "candidate_observations.csv", keep_default_na=False)
    additions = pd.read_csv(SOURCES / "candidate_assays.csv", keep_default_na=False)
    for sample, assays in additions.groupby("sample_id", sort=True):
        sequence = assays.sequence.iloc[0]
        if (sample != hashlib.sha256(sequence.encode("ascii")).hexdigest()[:24]
                or assays.sequence.nunique() != 1
                or set(assays.decision) != {"local_fields_confirmed_not_training_released"}
                or not assays.training_release.eq(False).all()
                or set(assays.endpoint) != {"MIC"}):
            raise ValueError("Addition is not a reviewed, uniquely identified MIC molecule.")
        labels = {measurement_label({"concentration": row.raw_mic, "unit": {"name": row.raw_unit}}, sequence, 32, 128)
                  for row in assays.itertuples(index=False)}
        if len(labels) != 1 or None in labels:
            raise ValueError("An exact new molecule has an opposite label or threshold-gap observation.")
        label = labels.pop()
        studies = set(identifier for ids in assays.assay_study_ids for identifier in ids.split("|"))
        records = set(assays.record_id)
        if sample in set(molecules.sample_id):
            index = molecules.index[molecules.sample_id.eq(sample)][0]
            if molecules.loc[index, "seq"] != sequence or int(molecules.loc[index, "amp"]) != label:
                raise ValueError("Existing exact molecule has conflicting sequence/label.")
            records.update(json.loads(molecules.loc[index, "record_ids"]))
            studies.update(molecules.loc[index, "study_ids"].split("|"))
            molecules.loc[index, "record_ids"] = json.dumps(sorted(records))
            molecules.loc[index, "study_ids"] = "|".join(sorted(studies))
        else:
            row = {column: "" for column in molecules.columns}
            row.update(sample_id=sample, seq=sequence, amp=label, record_ids=json.dumps(sorted(records)),
                       source_datasets="original_primary_source", study_ids="|".join(sorted(studies)))
            molecules = pd.concat([molecules, pd.DataFrame([row])], ignore_index=True)
        for index, assay in enumerate(assays.itertuples(index=False)):
            low, high = bounds(assay.raw_mic)
            factor = molecular_weight(sequence) / 1000 if assay.raw_unit == "µM" else 1
            row = {column: "" for column in observations.columns}
            row.update(sample_id=sample, record_id=assay.record_id, source_dataset="original_primary_source",
                       assay_index=index, target=assay.target, medium=assay.medium, method=assay.method,
                       raw_mic=assay.raw_mic, raw_unit=assay.raw_unit, normalized_low_ug_ml=low * factor,
                       normalized_high_ug_ml=high * factor, eligible=True, derived_label=label,
                       reference_resolution=assay.primary_location, assay_study_ids=assay.assay_study_ids)
            observations = pd.concat([observations, pd.DataFrame([row])], ignore_index=True)
    molecules.amp = molecules.amp.astype(int)
    alphabet = set("ACDEFGHIKLMNPQRSTVWY")
    if (not molecules.sample_id.is_unique or not molecules.seq.is_unique
            or any(not 10 <= len(seq) <= 50 or set(seq) - alphabet for seq in molecules.seq)):
        raise ValueError("Exact duplicate or out-of-domain molecule remains.")
    sequences = molecules.set_index("sample_id").seq.to_dict()
    labels = molecules.set_index("sample_id").amp.to_dict()
    for row in observations.itertuples(index=False):
        label = measurement_label({"concentration": row.raw_mic, "unit": {"name": row.raw_unit}}, sequences[row.sample_id], 32, 128)
        if label is None or label != int(row.derived_label) or label != labels[row.sample_id]:
            raise ValueError(f"Raw MIC label cannot be reproduced: {row.record_id}")
    graph, pairs = DisjointSet(molecules.sample_id.tolist()), []
    for a, b in itertools.combinations(molecules.itertuples(index=False), 2):
        identity = sequence_identity(a.seq, b.seq, identity_mode="alignment")
        pairs.append({"sample_id_a": a.sample_id, "sample_id_b": b.sample_id,
                      "identity": identity, "homology_edge": identity >= 0.40})
        if identity >= 0.40:
            graph.union(a.sample_id, b.sample_id)
    studies: dict[str, set[str]] = {}
    for sample, identifiers in [*zip(molecules.sample_id, molecules.study_ids),
                                *zip(observations.sample_id, observations.assay_study_ids)]:
        for identifier in identifiers.split("|"):
            if not identifier:
                raise ValueError("Missing primary-study identity.")
            members = studies.setdefault(identifier, set())
            if members:
                graph.union(sample, min(members))
            members.add(sample)
    roots = sorted({graph.find(sample) for sample in molecules.sample_id})
    molecules["review_component"] = molecules.sample_id.map(lambda sample: roots.index(graph.find(sample)))
    components = molecules.groupby("review_component").agg(molecules=("sample_id", "size"), positives=("amp", "sum"))
    components["negatives"] = components.molecules - components.positives
    positive_groups, negative_groups = int(components.positives.gt(0).sum()), int(components.negatives.gt(0).sum())
    blockers = [f"{name}: {count} < 5; five validation folds containing both classes are impossible."
                for count, name in ((len(components), "total components"), (positive_groups, "positive-bearing components"),
                                    (negative_groups, "negative-bearing components")) if count < 5]
    assignments, folds = [], []
    if not blockers:
        splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
        for fold, (train_ids, valid_ids) in enumerate(splitter.split(molecules.seq, molecules.amp, molecules.review_component)):
            train, valid = molecules.iloc[train_ids], molecules.iloc[valid_ids]
            both = set(train.amp) == {0, 1} and set(valid.amp) == {0, 1}
            folds.append({"fold": fold, "train_n": len(train), "validation_n": len(valid), "both_classes": both})
            assignments.extend({"sample_id": sample, "fold": fold} for sample in valid.sample_id)
            if not both:
                blockers.append(f"Fixed seed 42 fold {fold} lacks both classes.")
    fold_map = {row["sample_id"]: row["fold"] for row in assignments}
    cross_homology = (sum(row["homology_edge"] and fold_map[row["sample_id_a"]] != fold_map[row["sample_id_b"]]
                          for row in pairs) if assignments else None)
    cross_studies = (sum(len({fold_map[sample] for sample in members}) > 1 for members in studies.values())
                     if assignments else None)
    if cross_homology or cross_studies:
        blockers.append("Cross-fold member homology or primary-study leakage detected.")
    structure_passed = not blockers
    blockers.append("Full evidence release and a new immutable training protocol remain incomplete.")
    output.mkdir(parents=True)
    for name, frame in (("candidate_molecules.csv", molecules), ("candidate_observations.csv", observations),
                        ("all_member_similarity.csv", pd.DataFrame(pairs)), ("component_summary.csv", components.reset_index()),
                        ("fold_assignments.csv", pd.DataFrame(assignments, columns=["sample_id", "fold"]))):
        frame.to_csv(output / name, index=False)
    report = (
        "# 新原始来源合并后的全员分组审计\n\n"
        f"在原 {base['candidate_molecules']} 条局部确认分子、{base['candidate_observations']} 条测定基础上，"
        f"加入 {source['candidate_molecules']} 条分子、{source['candidate_observations']} 条 MIC。"
        "Zhang 2021 两条游离酸阴性对照共用一个原始研究；Sharma 2013 的 Tritrpticin 与 12PhD1 共用一个研究，"
        "两株细菌的测定不计成独立来源。全部逐来源决定见 ../mic_independent_sources_review_20261002_v1/report.md。\n\n"
        f"当前 {len(molecules)} 条分子（阳性 {int(molecules.amp.sum())}、阴性 {int(len(molecules)-molecules.amp.sum())}），"
        f"{len(observations)} 条测定、{len(pairs)} 对全员比较、{sum(r['homology_edge'] for r in pairs)} 条同源边。"
        f"同源与研究整体连接为 {len(components)} 个组件：含阳性 {positive_groups} 个、含阴性 {negative_groups} 个。\n\n"
        f"五折每折两类至少需要 5 个含阳性与 5 个含阴性组件；含阳性仍至少缺 {max(0,5-positive_groups)} 个。"
        "这是必要条件下界，补足后仍须检查固定 seed 42 的实际分折。当前分折未生成，跨折审计为 null。"
        "所有候选仅局部证据确认，完整释放待完成；训练释放为 0，训练未启动，状态 blocked。\n\n"
        + "".join(f"- {reason}\n" for reason in blockers)
        + "\n## 复跑\n\n`python 02_code/audit_mic_extended_acid_cohort.py --output 03_experiments/audits/mic_extended_my_run`\n"
        "须使用不存在的新目录。0.40、5 折、seed 42、32/128 标签边界与分子域保持冻结。\n")
    (output / "report.md").write_text(report, encoding="utf-8")
    inputs = [BASE / "manifest.json", SOURCES / "manifest.json", PROTOCOL, ROOT / "02_code/public_data.py",
              ROOT / "02_code/research_data.py", ROOT / "02_code/audit_mic_reviewed_subset_hirsch.py",
              ROOT / "02_code/audit_mic_independent_sources.py"]
    manifest = {"status": "blocked", "generated_at": utc_now(), "audit_protocol_id": "protocol-mic-01",
                "candidate_molecules": len(molecules), "candidate_observations": len(observations),
                "positive_molecules": int(molecules.amp.sum()), "negative_molecules": int(len(molecules)-molecules.amp.sum()),
                "all_member_pairs": len(pairs), "homology_edges": sum(r["homology_edge"] for r in pairs),
                "combined_components": len(components), "positive_bearing_components": positive_groups,
                "negative_bearing_components": negative_groups, "fold_structure_gate_passed": structure_passed,
                "folds_generated": bool(assignments), "folds": folds, "folds_required": 5, "seed": 42, "cutoff": 0.40,
                "cross_fold_homology_edges": cross_homology, "cross_fold_primary_studies": cross_studies,
                "blockers": blockers, "records_released_for_training": 0, "training_started": False,
                "script_sha256": sha256(Path(__file__)), "inputs": {str(p.relative_to(ROOT)): sha256(p) for p in inputs},
                "outputs": {p.name: sha256(p) for p in output.iterdir() if p.is_file()}}
    write_json(output / "manifest.json", manifest)
    return manifest


def publish(cohort: Path, output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite readiness: {output}")
    manifest, sources = verify(cohort), verify(SOURCES)
    if manifest["script_sha256"] != sha256(Path(__file__)):
        raise ValueError("Frozen cohort generator changed.")
    previous = json.loads(PREVIOUS.read_text(encoding="utf-8"))
    for name, digest in previous["inputs"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"Prior readiness evidence changed: {name}")
    formal = json.loads(FORMAL.read_text(encoding="utf-8"))
    if (sha256(FORMAL) != previous["formal_status_sha256"] or formal["run_status"] != "none"
            or formal["formal_results_available"] or formal["publication_ready"]):
        raise ValueError("Formal dual-task state changed; inspect before publishing.")
    result = {key: previous[key] for key in ("withdrawn_historical_training", "historical_unreleased_candidate_structure",
                                             "historical_evidence_conflicts", "paper_audits")}
    total, pos, neg = (manifest[key] for key in ("combined_components", "positive_bearing_components", "negative_bearing_components"))
    result.update(schema_version=2, status="blocked", generated_at=utc_now(), supersedes=str(PREVIOUS.relative_to(ROOT)),
                  scope="MIC-only exploratory candidates; full evidence release incomplete", audit_protocol_id="protocol-mic-01",
                  audit_protocol_path=str(PROTOCOL.relative_to(ROOT)), audit_protocol_sha256=sha256(PROTOCOL),
                  training_protocol_id=None, training_protocol_status="pending_new_immutable_protocol",
                  candidate_cohort_version=cohort.name, candidate_cohort_manifest=str((cohort / "manifest.json").relative_to(ROOT)),
                  candidate_cohort_manifest_sha256=sha256(cohort / "manifest.json"), candidate_molecules=manifest["candidate_molecules"],
                  candidate_observations=manifest["candidate_observations"],
                  candidate_class_counts={"0": manifest["negative_molecules"], "1": manifest["positive_molecules"]},
                  candidate_all_member_pairs=manifest["all_member_pairs"], candidate_homology_edges=manifest["homology_edges"],
                  candidate_combined_components=total, candidate_positive_bearing_components=pos, candidate_negative_bearing_components=neg,
                  gates={"candidate_structure": {
                      "status": "passed" if manifest["fold_structure_gate_passed"] else "blocked",
                      "folds_required": 5, "seed": 42, "cutoff": 0.40, "folds_generated": manifest["folds_generated"],
                      "folds": manifest["folds"], "cross_fold_homology_edges": manifest["cross_fold_homology_edges"],
                      "cross_fold_primary_studies": manifest["cross_fold_primary_studies"],
                      "necessary_additional_components_lower_bound": {"total": max(0,5-total), "positive_bearing": max(0,5-pos),
                                                                      "negative_bearing": max(0,5-neg), "sufficient_for_fixed_folds": False}},
                      "primary_evidence_release": {"status": "blocked", "full_release_review_complete": False,
                                                   "locally_confirmed_free_acid_molecules": manifest["candidate_molecules"],
                                                   "new_source_review": str((SOURCES / "manifest.json").relative_to(ROOT)),
                                                   "new_source_review_sha256": sha256(SOURCES / "manifest.json")},
                      "final_admitted_cohort": {"status": "pending_full_release_review_and_new_data"},
                      "training_protocol": {"status": "pending_new_immutable_protocol"}},
                  additional_source_reviews={"primary_articles": sources["primary_articles"], "reviewed_records": sources["reviewed_records"],
                                             "new_candidate_molecules": sources["candidate_molecules"],
                                             "new_candidate_observations": sources["candidate_observations"],
                                             "manifest": str((SOURCES / "manifest.json").relative_to(ROOT))},
                  blockers=manifest["blockers"], records_released_for_training=0, training_started=False, training_command=None,
                  formal_dual_task_status=formal["status"], formal_status_generated_at=formal["generated_at"], formal_status_sha256=sha256(FORMAL),
                  formal_results_available=False, publication_ready=False, script_sha256=sha256(Path(__file__)),
                  inputs={str(p.relative_to(ROOT)): sha256(p) for p in (PREVIOUS, cohort / "manifest.json", SOURCES / "manifest.json", PROTOCOL, FORMAL)})
    write_json(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--output", type=Path, required=True)
    state = sub.add_parser("state")
    state.add_argument("--cohort", type=Path, required=True)
    state.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output) if args.command == "audit" else publish(args.cohort.resolve(), args.output)
    print(json.dumps({key: result[key] for key in ("status", "generated_at", "candidate_molecules", "candidate_observations", "blockers")}, indent=2))
