"""Audit all five synthetic apidaecins in the original Table 1, without releasing training."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd

from audit_mic_primary_hirsch2020 import cells, table
from research_data import sequence_identity
from research_utils import ROOT, sha256, utc_now, write_json


PMID = "35735615"
PMCID = "PMC9221748"
DOI = "10.3390/cimb44060174"
SOURCE_URL = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{PMCID}/fullTextXML"
EXPECTED = [
    ["Api801", "GNNRPVYIPRPRPPHPRL-OH", "2", "n.d."],
    ["Api802", "MNNRPIYIPRPRPPHPRL-OH", "2–4", "64"],
    ["Api805", "GNNRPIYIPRPRPPHPRPIRV-OH", "4", "n.d."],
    ["Api806", "MNNRPIYIPRPRPPHPRPIRV-OH", "4–8", "128"],
    ["Api810", "MNNRPIYIPRPRPPHPAL-OH", "128", ">128"],
]


def interval(value: str) -> tuple[float, float, int | None]:
    if value == "n.d.":
        return float("nan"), float("nan"), None
    if value.startswith(">"):
        low, high = float(value[1:]), float("inf")
    elif "–" in value:
        low, high = map(float, value.split("–"))
    else:
        low = high = float(value)
    label = 1 if high <= 32 else 0 if low >= 128 else None
    return low, high, label


def run(source: Path, reviewed: Path, historical: Path, output: Path) -> dict:
    source, reviewed, historical, output = [Path(p).resolve()
                                           for p in (source, reviewed, historical, output)]
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite primary review: {output}")
    article = ElementTree.parse(source).getroot()
    identifiers = {item.attrib.get("pub-id-type"): item.text
                   for item in article.findall(".//article-id")}
    if any(identifiers.get(kind) != value for kind, value in
           (("pmid", PMID), ("pmcid", PMCID), ("doi", DOI))):
        raise ValueError("Original article identity changed.")
    license_node = article.find(".//license")
    if license_node is None or "creativecommons.org/licenses/by/4.0/" not in " ".join(license_node.itertext()):
        raise ValueError("Original article license is not the expected CC BY 4.0.")
    original_table = table(article, "Table 1")
    rows = [cells(row) for row in original_table.findall(".//tbody/tr")]
    if rows != EXPECTED:
        raise ValueError("Original Table 1 sequence or MIC differs from the reviewed inventory.")
    caption = " ".join(original_table.find("caption").itertext())
    if not all(token in caption for token in ("E. coli", "Rosetta DE3 pLysS", "25% MHBII", "LB medium")):
        raise ValueError("Original table target or media changed.")
    synthesis = article.find(".//sec[@id='sec2dot2-cimb-44-00174']")
    method = article.find(".//sec[@id='sec2dot3-cimb-44-00174']")
    if synthesis is None or method is None:
        raise ValueError("Original synthesis or MIC methods missing.")
    synthesis_text, method_text = " ".join(synthesis.itertext()), " ".join(method.itertext())
    if not all(token in synthesis_text for token in ("Wang resins", "C-terminal acids", "Monoisotopic masses were confirmed")):
        raise ValueError("Free-acid molecular identity is no longer confirmed by the original synthesis.")
    if not all(token in method_text for token in ("at least twice in triplicates", "25% MHBII or LB", "7.5", "20", "37", "600", "MIC was defined")):
        raise ValueError("Original broth MIC conditions changed.")
    record_rows, assay_rows = [], []
    for name, sequence_with_form, mhb, lb in rows:
        sequence = sequence_with_form.removesuffix("-OH")
        sample_id = hashlib.sha256(sequence.encode("ascii")).hexdigest()[:24]
        measured = [(medium, value, interval(value)) for medium, value in
                    (("25% Mueller-Hinton broth II", mhb), ("LB (Luria/Miller)", lb))
                    if value != "n.d."]
        labels = {bounds[2] for _, _, bounds in measured}
        if labels == {0, 1}:
            decision, reason = "excluded", "conflicting_binary_MIC_labels_across_media"
        elif None in labels:
            decision, reason = "excluded", "at_least_one_measured_MIC_in_32_128_threshold_gap"
        else:
            decision, reason = "candidate", "all_reported_MICs_support_one_binary_class"
        record_rows.append({
            "record_id": f"PMID{PMID}:{name}", "sample_id": sample_id,
            "name": name, "sequence": sequence, "molecular_form": "C-terminal free acid",
            "decision": decision, "reason": reason,
            "derived_binary_label": next(iter(labels)) if decision == "candidate" else None,
            "training_release": False,
        })
        for assay_index, (medium, value, (low, high, label)) in enumerate(measured):
            assay_rows.append({
                "record_id": f"PMID{PMID}:{name}", "sample_id": sample_id,
                "sequence": sequence, "assay_index": assay_index,
                "molecular_form": "C-terminal free acid",
                "assay_study_ids": f"doi:{DOI}|pmid:{PMID}",
                "target": "Escherichia coli Rosetta DE3 pLysS", "endpoint": "MIC",
                "paper_value": value, "unit": "µg/mL", "medium": medium,
                "normalized_low_ug_ml": low, "normalized_high_ug_ml": high,
                "derived_binary_label": label, "candidate_eligible": decision == "candidate",
                "replication": "at least two experiments, each in triplicate",
                "inoculum_cfu_ml": 7.5e6, "temperature_c": 37,
                "incubation_hours": "20 ± 2", "volume_ul": 100,
                "paper_location": "Table 1; Methods 2.2 and 2.3",
                "training_release": False,
            })
    records, assays = pd.DataFrame(record_rows), pd.DataFrame(assay_rows)
    candidates = records[records.decision.eq("candidate")]
    if set(candidates.name) != {"Api801", "Api805", "Api810"}:
        raise ValueError("Unexpected primary-evidence candidate decisions.")
    comparison = {}
    for name, path, expected_count in (("reviewed", reviewed, 38), ("historical", historical, 324)):
        cohort = pd.read_csv(path)
        if len(cohort) != expected_count or cohort.sample_id.duplicated().any():
            raise ValueError("Frozen comparison cohort changed.")
        pairs = []
        for candidate in candidates.itertuples(index=False):
            for member in cohort.itertuples(index=False):
                identity = sequence_identity(candidate.sequence, member.seq, identity_mode="alignment")
                pairs.append({
                    "candidate_sample_id": candidate.sample_id, "candidate_name": candidate.name,
                    "other_sample_id": member.sample_id, "other_sequence": member.seq,
                    "other_study_ids": member.study_ids, "identity": identity,
                    "edge_at_0_40": identity >= 0.40,
                })
        comparison[name] = pd.DataFrame(pairs)
    output.mkdir(parents=True)
    records.to_csv(output / "record_review.csv", index=False)
    assays.to_csv(output / "primary_assays.csv", index=False)
    for name, pairs in comparison.items():
        pairs.to_csv(output / f"similarity_{name}.csv", index=False)
    (output / "report.md").write_text(
        "# Ludwig 等 2022：原始 apidaecin 测定审计\n\n"
        f"[原论文](https://pmc.ncbi.nlm.nih.gov/articles/{PMCID}/)，PMID {PMID}，DOI {DOI}，CC BY 4.0。"
        "结构化 Table 1 与 Methods 2.2/2.3 明确五条人工合成游离酸端肽、Rosetta DE3 pLysS 菌株、培养基和 MIC 端点；"
        "未使用噬菌体表达或联合治疗读数作为肽 MIC。\n\n"
        "Api801、Api805 的所有已报告 MIC 均支持阳性；Api810 在两种培养基均支持阴性。"
        "Api802 有 64 µg/mL 空档测定，保守排除整条分子；Api806 两种培养基分别给出阳性和阴性，排除整条分子。"
        "未测定不补值。最终为 3 条候选分子、4 条候选测定。\n\n"
        f"与现有 38 条逐成员核对共 {len(comparison['reviewed'])} 对，"
        f"达到 0.40 的边为 {int(comparison['reviewed'].edge_at_0_40.sum())}；"
        "同源关系和共享论文均必须连接，不能把 Api810 当作新独立组件。"
        "完整证据复核、队列冻结及五折门禁尚未通过，训练释放数为 0。\n",
        encoding="utf-8")
    inputs = (source, reviewed, historical, ROOT / "02_code/audit_mic_primary_hirsch2020.py",
              ROOT / "02_code/research_data.py", ROOT / "02_code/research_protocol_config.py")
    names = ("record_review.csv", "primary_assays.csv", "similarity_reviewed.csv", "similarity_historical.csv", "report.md")
    manifest = {
        "status": "candidate_primary_evidence_verified_not_released", "generated_at": utc_now(),
        "paper": {"pmid": PMID, "pmcid": PMCID, "doi": DOI, "source_url": SOURCE_URL, "license": "CC BY 4.0"},
        "original_molecules_reviewed": len(records), "original_MIC_observations": len(assays),
        "candidate_molecules": len(candidates), "candidate_observations": int(assays.candidate_eligible.sum()),
        "excluded_molecules": int(records.decision.eq("excluded").sum()),
        "reviewed_similarity_pairs": len(comparison["reviewed"]),
        "reviewed_similarity_edges_at_0_40": int(comparison["reviewed"].edge_at_0_40.sum()),
        "records_released_for_training": 0, "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in inputs},
        "outputs": {name: sha256(output / name) for name in names},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "03_experiments/audits/mic_primary_candidate_sources_20261002_v1/PMC9221748.xml")
    parser.add_argument("--reviewed", type=Path, default=ROOT / "03_experiments/audits/mic_reviewed_subset_groups_20261002_v2/candidate_molecules.csv")
    parser.add_argument("--historical", type=Path, default=ROOT / "03_experiments/audits/mic_only_cohort_20261001_v9/molecule_components.csv")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.reviewed, args.historical, args.output), ensure_ascii=True, indent=2))
