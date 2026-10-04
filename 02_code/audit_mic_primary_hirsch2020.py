"""Review the original EtCec3 free-acid MICs and all-member similarity.

This is evidence and structural screening, not a training release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd

from research_data import sequence_identity
from research_utils import ROOT, sha256, utc_now, write_json


PMID = "32344933"
DOI = "10.3390/microorganisms8050626"
PMCID = "PMC7284870"
SEQUENCE = "GFLKKVGKKLEGASDLTRDATIQTIAVAQAAANVAATAKQG"
SOURCE_URL = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{PMCID}/fullTextXML"
CUTOFF = 0.40


def cells(row: ElementTree.Element) -> list[str]:
    return [re.sub(r"\s+", " ", "".join(cell.itertext())).strip()
            for cell in row if cell.tag in {"td", "th"}]


def table(article: ElementTree.Element, label: str) -> ElementTree.Element:
    found = [item for item in article.findall(".//table-wrap")
             if item.findtext("label") == label]
    if len(found) != 1:
        raise ValueError(f"Expected exactly one {label} in original article.")
    return found[0]


def run(source: Path, reviewed: Path, historical: Path, output: Path) -> dict:
    source, reviewed, historical, output = [Path(path).resolve()
                                            for path in (source, reviewed, historical, output)]
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite paper review: {output}")
    for path in (source, reviewed, historical):
        if not path.is_file():
            raise FileNotFoundError(path)
    article = ElementTree.parse(source).getroot()
    ids = {item.attrib.get("pub-id-type"): item.text
           for item in article.findall(".//article-id")}
    if any(ids.get(kind) != value for kind, value in
           (("pmid", PMID), ("pmcid", PMCID), ("doi", DOI))):
        raise ValueError("Original article identifiers differ from the expected paper.")
    license_text = " ".join(article.find(".//license").itertext())
    if "creativecommons.org/licenses/by/4.0/" not in license_text:
        raise ValueError("Original article reuse license differs from CC BY 4.0.")
    table1 = table(article, "Table 1")
    sequence_rows = [cells(row) for row in table1.findall(".//tbody/tr")]
    free_acid = [row for row in sequence_rows if row[0] == "EtCec3"]
    amidated = [row for row in sequence_rows if row[0].replace(" ", "") == "EtCec3-NH2"]
    if (len(free_acid) != 1 or free_acid[0][1:4] != [SEQUENCE, "41", "4113.67"]
            or len(amidated) != 1 or not amidated[0][1].endswith("-NH2")):
        raise ValueError("Original Table 1 does not distinguish EtCec3 free acid and amide.")
    table2 = table(article, "Table 2")
    assay_rows = [cells(row) for row in table2.findall(".//tbody/tr")]
    observations = []
    for strain in ("D31", "ATCC 25922"):
        matches = [row for row in assay_rows if "coli" in row[0] and strain in row[0]]
        if len(matches) != 1 or len(matches[0]) != 10 or matches[0][5] != ">1024":
            raise ValueError(f"Original Table 2 EtCec3-OH MIC changed for {strain}.")
        observations.append({
            "record_id": "PMID32344933:EtCec3-OH",
            "sample_id": hashlib.sha256(SEQUENCE.encode("ascii")).hexdigest()[:24],
            "sequence": SEQUENCE, "molecular_form": "C-terminal free acid",
            "assay_study_id": f"pmid:{PMID}", "target": f"Escherichia coli {strain}",
            "endpoint": "MIC", "paper_value": ">1024", "unit": "µg/mL",
            "medium": "cation-adjusted Mueller-Hinton broth",
            "paper_location": "Table 1 sequence and molecular form; Table 2 MIC; Methods 2.4",
            "derived_binary_label": 0,
            "label_rule": "MIC >1024 µg/mL implies MIC >=128 µg/mL",
            "training_release": False,
        })
    assay_notes = " ".join(table2.itertext())
    if (not re.search(r"n\s*=\s*4", assay_notes)
            or "C-terminally carboxylated" not in assay_notes
            or "cation-adjusted Mueller-Hinton broth" not in assay_notes):
        raise ValueError("Original Table 2 replication, form, or medium note changed.")
    methods = " ".join(article.itertext())
    start = methods.find("2.4. Inhibition of Microbial Growth")
    end = methods.find("2.5. Checkerboard Assay", start)
    if start < 0 or end < 0 or not all(token in methods[start:end]
                                        for token in ("1024", "0.03125", "MIC was defined")):
        raise ValueError("Original primary MIC method or concentration range changed.")
    reviewed_molecules = pd.read_csv(reviewed)
    historical_molecules = pd.read_csv(historical)
    if len(reviewed_molecules) != 37 or len(historical_molecules) != 324:
        raise ValueError("Frozen comparison cohorts changed; review before rerunning.")
    pair_tables = {}
    for name, frame in (("reviewed", reviewed_molecules),
                        ("historical", historical_molecules)):
        rows = []
        for item in frame.itertuples(index=False):
            identity = sequence_identity(SEQUENCE, item.seq, identity_mode="alignment")
            rows.append({"candidate_sample_id": observations[0]["sample_id"],
                         "other_sample_id": item.sample_id, "other_sequence": item.seq,
                         "other_label": int(item.amp), "other_study_ids": item.study_ids,
                         "identity": identity, "edge_at_0_40": identity >= CUTOFF})
        pair_tables[name] = pd.DataFrame(rows).sort_values(
            ["identity", "other_sample_id"], ascending=[False, True])
    if pair_tables["reviewed"].edge_at_0_40.any():
        raise ValueError("EtCec3 connects to a reviewed-subset component; reassess selection.")
    output.mkdir(parents=True)
    pd.DataFrame(observations).to_csv(output / "primary_assays.csv", index=False)
    for name, frame in pair_tables.items():
        frame.to_csv(output / f"similarity_{name}.csv", index=False)
    report = (
        "# Hirsch 等 2020：EtCec3 游离羧酸端阴性候选\n\n"
        f"[原论文]({SOURCE_URL})，PMID {PMID}，DOI {DOI}，CC BY 4.0。"
        "Table 1 明确 EtCec3-OH 的 41 aa 序列及其与酰胺化形式的区别；"
        "Table 2 对 *E. coli* D31、ATCC 25922 均记 `>1024 µg/mL`（n=4，CAMB）。"
        "Methods 2.4 的最高终浓度为 1024 µg/mL；两条测定均能按既有阴性界限推导为阴性。\n\n"
        f"与已核查的 37 条候选全员比较，最高一致性 "
        f"{pair_tables['reviewed'].identity.max():.6f}，达到 0.40 的边 "
        f"{int(pair_tables['reviewed'].edge_at_0_40.sum())} 条；"
        f"与旧 324 条未完成原文核对的队列比较，最高一致性 "
        f"{pair_tables['historical'].identity.max():.6f}，达到 0.40 的边 "
        f"{int(pair_tables['historical'].edge_at_0_40.sum())} 条。"
        "后者是若恢复旧成员时必须合并的同源关系。\n\n"
        "本项仅建立有原始测定依据的候选。尚未完成全候选证据复核、"
        "新队列冻结和固定五折验证；训练释放数为 0。\n"
    )
    (output / "report.md").write_text(report, encoding="utf-8")
    output_names = ("primary_assays.csv", "similarity_reviewed.csv",
                    "similarity_historical.csv", "report.md")
    manifest = {
        "status": "candidate_primary_evidence_verified_not_released",
        "generated_at": utc_now(), "paper": {"pmid": PMID, "pmcid": PMCID,
        "doi": DOI, "source_url": SOURCE_URL, "license": "CC BY 4.0"},
        "candidate_sample_id": observations[0]["sample_id"],
        "primary_assay_observations": len(observations),
        "reviewed_cohort_count": len(reviewed_molecules),
        "reviewed_similarity_edges_at_0_40": int(pair_tables["reviewed"].edge_at_0_40.sum()),
        "historical_cohort_count": len(historical_molecules),
        "historical_similarity_edges_at_0_40": int(pair_tables["historical"].edge_at_0_40.sum()),
        "records_released_for_training": 0,
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str(path.relative_to(ROOT)): sha256(path)
                   for path in (source, reviewed, historical)},
        "outputs": {name: sha256(output / name) for name in output_names},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "03_experiments/audits/mic_primary_review_pmid32344933_20261002_v1/raw/PMC7284870_fullTextXML.xml")
    parser.add_argument("--reviewed", type=Path, default=ROOT / "03_experiments/audits/mic_reviewed_subset_groups_20261002_v1/candidate_molecules.csv")
    parser.add_argument("--historical", type=Path, default=ROOT / "03_experiments/audits/mic_only_cohort_20261001_v9/molecule_components.csv")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.reviewed, args.historical, args.output),
                     ensure_ascii=True, indent=2))
