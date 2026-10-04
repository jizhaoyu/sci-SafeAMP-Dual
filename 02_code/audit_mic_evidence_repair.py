"""Correct original-source identifiers; record missing evidence without releasing labels."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd

from research_evidence_gate import require_primary_release, verify_manifest, workspace_path
from research_utils import ROOT, read_json, sha256, utc_now, write_json

COHORT = ROOT / "03_experiments/audits/mic_source_expansion_result_20261002_v2"
ARCHIVE = ROOT / "03_experiments/audits/gemini_repair_20261003_v1/archive_manifest.json"
DEFAULT_OUTPUT = ROOT / "03_experiments/audits/mic_evidence_repair_20261003_v1"


def original_identifiers(path: Path) -> dict:
    if path.suffix.lower() != ".xml" or not path.is_file():
        return {}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return {}
    return {node.get("pub-id-type"): "".join(node.itertext()).strip()
            for node in root.findall("./front/article-meta/article-id")
            if node.get("pub-id-type") in {"doi", "pmid", "pmcid"}}


def verify_original_materials() -> dict:
    archive = read_json(ARCHIVE)
    for item in archive["archives"].values():
        if sha256(workspace_path(item["archive_path"])) != item["sha256"]:
            raise ValueError("Repair source archive changed")
    for name, expected in archive["protected_files"].items():
        if sha256(workspace_path(name)) != expected:
            raise ValueError(f"Protected historical material changed: {name}")
    return archive


def audit(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite evidence review: {output}")
    verify_original_materials()
    frozen = verify_manifest(COHORT)
    old_protocol_path = ROOT / "03_experiments/protocols/protocol-mic-07.json"
    old_protocol = read_json(old_protocol_path)
    old_release = require_primary_release(
        old_protocol, ROOT / "03_experiments/audits/protocol_mic_07_freeze_20261002_v2.json",
        ROOT / "02_code/train_mic_three_fold_v2.py")
    release_dir = workspace_path(old_protocol["evidence_release_manifest"]).parent
    old_ids = set(pd.read_csv(release_dir / "molecule_evidence_review.csv", keep_default_na=False).sample_id)
    sources = pd.read_csv(COHORT / "source_inventory.csv", keep_default_na=False)
    corrections, inputs = [], {str(ARCHIVE.relative_to(ROOT)): sha256(ARCHIVE)}
    for row in sources.to_dict("records"):
        file = workspace_path(row["primary_file"]) if row["primary_file"] else None
        ids = original_identifiers(file) if file else {}
        record = dict(row)
        for key in ("doi", "pmid", "pmcid"):
            record[f"original_{key}"] = row[key]
            if ids:
                record[key] = ids.get(key, "")
        if ids:
            record["identifier_review"] = "verified_against_primary_xml"
            record["study_aliases"] = "|".join(f"{key}:{ids[key]}" for key in ("doi", "pmid", "pmcid") if ids.get(key))
            record["primary_url"] = f"https://doi.org/{ids['doi']}" if ids.get("doi") else ""
        else:
            record["identifier_review"] = "not_independently_verified_in_this_repair"
        if file and file.is_file():
            if sha256(file) != row["primary_file_sha256"]:
                raise ValueError(f"Frozen original article changed: {file}")
            inputs[str(file.relative_to(ROOT))] = sha256(file)
        corrections.append(record)
    corrected = pd.DataFrame(corrections)
    by_source = {r["source_id"]: r for r in corrections}
    decisions = pd.read_csv(COHORT / "record_decisions.csv", keep_default_na=False)
    decisions["historical_decision"] = decisions.decision
    decisions["historical_basis"] = decisions.basis
    for index, row in decisions.iterrows():
        source = by_source[row.source_id]
        decisions.at[index, "doi"] = source["doi"]
        if source["identifier_review"] == "verified_against_primary_xml":
            decisions.at[index, "pmid_or_pmcid"] = source["study_aliases"]
        if row.record_id == "bmap2025:BMAP-27B":
            decisions.at[index, "decision"] = "withheld_aggregate_target_endpoint"
            decisions.at[index, "basis"] = "Range pools isolates/species; exact isolate MIC observations remain unverified. No binary training label is approved."
        elif row.decision == "local_fields_confirmed_not_training_released":
            decisions.at[index, "decision"] = "withheld_complete_release_review"
        decisions.at[index, "training_release"] = False
    molecules = pd.read_csv(COHORT / "candidate_molecules.csv", keep_default_na=False)
    observations = pd.read_csv(COHORT / "assay_observations.csv", keep_default_na=False)
    molecule_reviews = []
    for row in molecules.to_dict("records"):
        approved = row["sample_id"] in old_ids
        molecule_reviews.append({"sample_id": row["sample_id"],
                                 "decision": "existing_15_evidence_passed" if approved else "withheld_complete_release_review",
                                 "approved_label": int(row["amp"]) if approved else None,
                                 "evidence_basis": old_protocol["evidence_release_manifest"] if approved else "No complete new release manifest",
                                 "expanded_cohort_training_release": False})
    observation_reviews = []
    for row in observations.to_dict("records"):
        approved = row["sample_id"] in old_ids
        source = by_source.get(row["record_id"].split(":", 1)[0])
        observation_reviews.append({"sample_id": row["sample_id"], "record_id": row["record_id"],
                                    "assay_index": row["assay_index"], "reported_target": row["target"],
                                    "reported_mic": row["raw_mic"], "reported_unit": row["raw_unit"],
                                    "corrected_study_ids": source["study_aliases"] if source else row["assay_study_ids"],
                                    "decision": ("existing_15_evidence_passed" if approved else
                                                 "withheld_aggregate_target_endpoint" if row["record_id"] == "bmap2025:BMAP-27B" else
                                                 "withheld_complete_release_review"),
                                    "approved_label": int(row["derived_label"]) if approved else None,
                                    "expanded_cohort_training_release": False})
    changed = corrected[corrected.apply(lambda r: any(str(r[k]) != str(r[f"original_{k}"]) for k in ("doi", "pmid", "pmcid")), axis=1)]
    output.mkdir(parents=True, exist_ok=False)
    corrected.to_csv(output / "source_identifier_review.csv", index=False, encoding="utf-8-sig")
    decisions.to_csv(output / "record_decisions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(molecule_reviews).to_csv(output / "molecule_evidence_review.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(observation_reviews).to_csv(output / "assay_evidence_review.csv", index=False, encoding="utf-8-sig")
    inputs.update({str(p.relative_to(ROOT)): sha256(p) for p in
                   (COHORT / "manifest.json", COHORT / "source_inventory.csv", COHORT / "record_decisions.csv",
                    COHORT / "candidate_molecules.csv", COHORT / "assay_observations.csv", old_protocol_path,
                    workspace_path(old_protocol["evidence_release_manifest"]), Path(__file__))})
    result = {"status": "complete_evidence_release_blocked", "generated_at": utc_now(),
              "audit_protocol_id": "protocol-mic-08", "data_version": output.name,
              "historical_cohort_version": frozen["candidate_cohort_version"],
              "candidate_molecules": len(molecules), "candidate_observations": len(observations),
              "original_xml_identifier_reviews": int(corrected.identifier_review.eq("verified_against_primary_xml").sum()),
              "sources_with_identifiers_corrected": changed.source_id.tolist(),
              "existing_15_molecules_evidence_approved": old_release["molecules_evidence_approved"],
              "new_molecules_evidence_approved": 0, "full_release_review_complete": False,
              "records_released_for_training": 0, "training_started": False,
              "blockers": ["Expanded cohort has no complete release manifest bound by a prospective training protocol.",
                           "BMAP-27B range is aggregate; identified isolate MIC observations remain unverified.",
                           "Piscidin 1 has not completed the separate new evidence release review.",
                           "Wrong historical study aliases require re-auditing before a scientific isolation claim."],
              "inputs": inputs, "outputs": {}, "script_sha256": sha256(Path(__file__))}
    (output / "report.md").write_text(
        "# MIC 完整证据整改审查\n\n"
        f"生成时间：{result['generated_at']}；协议：protocol-mic-08；数据版本：{output.name}。\n\n"
        f"从 {result['original_xml_identifier_reviews']} 份原文 XML 核对标识；更正来源：{', '.join(result['sources_with_identifiers_corrected'])}。\n\n"
        "17 条历史候选、24 条观察只作审查线索；原 15 条完整证据仍有既有释放记录。两条新增候选未完成整队列释放，新增训练释放为 0。"
        "BMAP-27B 多菌株范围保留为原报告值并暂缓，未改写为单株测定或批准标签。\n\n"
        "旧目录、协议、模型及状态保留。本目录不是训练数据集或释放证书。\n", encoding="utf-8")
    result["outputs"] = {p.name: sha256(p) for p in output.iterdir() if p.is_file()}
    write_json(output / "manifest.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    result = audit(parser.parse_args().output)
    print({k: result[k] for k in ("status", "data_version", "records_released_for_training")})
