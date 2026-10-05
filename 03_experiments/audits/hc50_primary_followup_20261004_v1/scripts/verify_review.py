"""Read-only integrity and coverage verification, no network or model imports."""
import argparse
import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(base, entries):
    for name, expected in entries.items():
        path = (base / name).resolve()
        if not path.is_relative_to(base.resolve()) or digest(path) != expected:
            raise ValueError(f"Binding changed: {name}")
    return len(entries)


def read_csv(path):
    with path.open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def cells(row):
    return [" ".join("".join(c.itertext()).split()) for c in row]


def verify(review, expected, output):
    if output.exists():
        raise FileExistsError(output)
    if digest(review / "manifest.json") != expected:
        raise ValueError("Review manifest anchor mismatch")
    manifest = json.loads((review / "manifest.json").read_text(encoding="utf-8"))
    checked = check(BASE, manifest["inputs"]) + check(review, manifest["outputs"])
    protected = check(ROOT, manifest["protected"])
    acquisition = BASE / "acquisition"
    intake = json.loads((acquisition / "manifest.json").read_text(encoding="utf-8"))
    checked += check(acquisition, intake["outputs"]) + check(ROOT, intake["scripts"])
    extra = BASE / "additional_metadata"
    more = json.loads((extra / "manifest.json").read_text(encoding="utf-8"))
    checked += check(extra, {r["file"]: r["sha256"] for r in more["requests"] if r.get("file")})
    old_path = ROOT / "03_experiments/audits/gemini_hc50_external_review_20261004_v2/input_manifest.json"
    if digest(old_path) != "e08370d9a391a849aa690470dc7574b13b07130727727daa76d60330b57d0e85":
        raise ValueError("Historical input manifest changed")
    old = json.loads(old_path.read_text(encoding="utf-8"))
    old_inputs = check(ROOT, old["files"])
    old_v1 = check(ROOT, old["protected_v1"])
    inventory = read_csv(acquisition / "candidate_inventory.csv")
    decisions = read_csv(review / "candidate_decisions.csv")
    originals = read_csv(review / "original_human_hc50_observations.csv")
    gaps = read_csv(review / "source_access_gaps.csv")
    summary = json.loads((review / "summary.json").read_text(encoding="utf-8"))
    if len(decisions) != 78 or {r["candidate_id"] for r in decisions} != {r["candidate_id"] for r in inventory}:
        raise ValueError("Candidate coverage is incomplete")
    if len(originals) != 8 or len({r["candidate_id"] for r in originals}) != 8:
        raise ValueError("HC50 observation coverage changed")
    if len(gaps) != summary["candidate_access_gaps"] or len(gaps) != 58:
        raise ValueError("Access gap count changed")
    if dict(Counter(r["decision"] for r in decisions)) != summary["decision_counts"]:
        raise ValueError("Summary decision counts disagree")
    if any(r["formal_release"] != "False" for r in decisions):
        raise ValueError("Unexpected formal evidence release")
    for r in originals:
        if r["rbc_species"] != "human" or r["formal_label"] != "not_released" or digest(BASE / r["source_file"]) != r["source_sha256"]:
            raise ValueError("Unexpected observation binding or release")
    # Independently re-read exact table cells for six numeric observations.
    cyclic = ET.parse(acquisition / "raw/pmid_36442155.xml").getroot()
    rows = {cells(r)[0]: cells(r) for r in cyclic.findall(".//table-wrap[@id='tbl1']//tbody/tr")}
    for r in originals:
        if r["pmid"] == "36442155":
            code = r["measured_molecule"].split()[0]
            if rows[code][6] != r["value_original"]:
                raise ValueError("Cyclic HC50 differs from original table")
    ar = ET.parse(acquisition / "raw/pmid_31234579.xml").getroot()
    ar_row = next(cells(r) for r in ar.findall(".//table-wrap[@id='marinedrugs-17-00376-t003']//tbody/tr") if cells(r)[0].startswith("HC50"))
    kr = ET.parse(acquisition / "raw/pmid_32153522.xml").getroot()
    kr_row = next(cells(r) for r in kr.findall(".//table-wrap[@id='T2']//tbody/tr") if cells(r)[0] == "cd4(Q5K,D9K)")
    values = {r["candidate_id"]: r["value_original"] for r in originals}
    if ar_row[8] != values["DBAASP_13515"] or kr_row[5] != values["DBAASP_15043"]:
        raise ValueError("AR-F or KR12 original table mismatch")
    report = (review / "report.md").read_text(encoding="utf-8")
    if summary["generated_at"] not in report or summary["data_version"] not in report or "protocol-amd-02" not in report:
        raise ValueError("Report metadata differs from machine summary")
    for r in originals:
        if f"| {r['candidate_id']} | {r['measured_molecule']} | {r['value_original']} {r['unit_original']} |" not in report:
            raise ValueError("Report observation differs from audit table")
    if summary["formal_external_released"] != 0 or summary["new_models_trained"] != 0 or summary["formal_scientific_status"] != "blocked":
        raise ValueError("Unexpected scientific gate change")
    result = {"status": "passed", "verified_at": datetime.now(timezone.utc).isoformat(),
              "review_manifest_sha256": expected, "candidate_records_checked": 78,
              "human_hc50_records_checked": 8, "numeric_table_cells_independently_rechecked": 6,
              "pdf_review": "agent visual review with pinned page images; not independent human review",
              "bound_new_file_hashes_checked": checked, "protected_v2_and_states_checked": protected,
              "historical_input_files_checked": old_inputs, "historical_v1_files_checked": old_v1,
              "formal_evidence_release": False, "formal_scientific_status": "blocked",
              "verifier_sha256": digest(Path(__file__))}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify(args.review.resolve(), args.manifest_sha256, args.output.resolve())
