"""Read-only provenance and endpoint audit; never imports training code."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from acquire_public_sources import BASE, ROOT, PREVIOUS, sha


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "Output exists; refusing overwrite")
    review = args.review.resolve()
    manifest_path = review / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key in ["inputs", "protected"]:
        for name, expected in manifest[key].items():
            require(sha(ROOT / name) == expected, f"Changed {key}: {name}")
    for name, expected in manifest["outputs"].items():
        require(sha(review / name) == expected, f"Changed review output: {name}")
    # Bind the acquisition entrypoints too, including the append-only manifest repair.
    for folder, filename, script in [
            ("acquisition", "manifest.json", "acquire_public_sources.py"),
            ("alternate_acquisition", "manifest.json", "acquire_alternate_sources.py"),
            ("figure_acquisition", "manifest_v2.json", "acquire_figure.py")]:
        acquired = json.loads((BASE / folder / filename).read_text(encoding="utf-8"))
        require(sha(BASE / "scripts" / script) == acquired["script_sha256"], f"Changed acquisition script: {script}")
        if "repair_script_sha256" in acquired:
            require(sha(BASE / "scripts/repair_figure_manifest.py") == acquired["repair_script_sha256"], "Changed manifest repair")
    prior = rows(PREVIOUS / "candidate_decisions.csv")
    subset = {row["candidate_id"] for row in prior if row["pmid"] == "29307492"}
    decisions = rows(review / "candidate_decisions.csv")
    require(len(decisions) == 14 and {row["candidate_id"] for row in decisions} == subset, "Incorrect fourteen-record coverage")
    merged = rows(review / "merged_candidate_decisions.csv")
    require(len(merged) == 78 and len({row["candidate_id"] for row in merged}) == 78, "Incorrect merged coverage")
    require({r["candidate_id"] for r in merged} == {r["candidate_id"] for r in prior}, "Changed candidate universe")
    original_by_id = {row["candidate_id"]: row for row in prior}
    require(all(row == original_by_id[row["candidate_id"]] for row in merged if row["candidate_id"] not in subset), "Unrelated decisions changed")
    require(all(row["formal_release"] == "False" and row["sequence_and_form_release"] == "False" for row in decisions), "Unexpected release")
    bioc = ET.parse(BASE / "acquisition/raw/bioc_article.xml").getroot()
    passage = next(p for p in bioc.iter("passage") if p.findtext("infon[@key='id']") == "T2" and p.findtext("infon[@key='type']") == "table")
    table = ET.fromstring(passage.findtext("infon[@key='xml']"))
    original_rows = {}
    for tr in table.findall("./tbody/tr"):
        cells = ["".join(td.itertext()).strip() for td in tr.findall("td")]
        original_rows[cells[0]] = cells
    identities = rows(review / "sequence_identity_review.csv")
    inventory = {r["candidate_id"]: r for r in rows(PREVIOUS.parent / "acquisition/candidate_inventory.csv")}
    require(len(identities) == 14 and {r["candidate_id"] for r in identities} == subset, "Identity coverage")
    for row in identities:
        require(row["sequence"] == original_rows[row["peptide"]][1] == inventory[row["candidate_id"]]["sequence"], "Sequence mismatch")
        require(row["full_molecular_identity_released"] == "False", "Incomplete form released")
    mbc = rows(review / "mbc_observations.csv")
    require(len(mbc) == 28 and Counter(row["candidate_id"] for row in mbc) == Counter({cid: 2 for cid in subset}), "MBC coverage")
    unique_targets = set()
    for row in mbc:
        index = 7 if row["target"] == "E. coli W3110" else 10
        key = (row["candidate_id"], row["target"])
        require(key not in unique_targets, "Duplicate molecular/strain observation")
        unique_targets.add(key)
        require(row["endpoint"] == "MBC" and row["unit"] == "µM", "Endpoint or unit changed")
        require(row["raw_value"] == original_rows[row["peptide"]][index], "MBC cell mismatch")
        require(row["formal_mic_label"] == row["formal_hc50_label"] == "", "MBC converted to labels")
        require(row["formal_release"] == "False", "MBC released")
    for filename, forbidden in [("mic_endpoint_gaps.csv", ["raw_value", "formal_mic_label"]),
                                 ("single_point_hemolysis_review.csv", ["percent_value", "hc50_value", "formal_hc50_label"])]:
        data = rows(review / filename)
        require(len(data) == 14 and {r["candidate_id"] for r in data} == subset, f"Coverage: {filename}")
        require(all(all(row[field] == "" for field in forbidden) and row["formal_release"] == "False" for row in data), "Unsupported numeric label")
    summary = json.loads((review / "summary.json").read_text(encoding="utf-8"))
    require(summary["merged_decision_counts"] == dict(Counter(row["decision"] for row in merged)), "Summary counts disagree")
    require(summary["remaining_original_access_gaps"] == sum(row["screen_status"] == "original_not_acquired" for row in merged), "Access count mismatch")
    require(summary["formal_external_released"] == summary["model_fit_calls"] == 0 and summary["formal_scientific_status"] == "blocked", "Scientific gate changed")
    result = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "passed",
              "scope": "provenance, fixed candidate coverage, source cells and endpoint guards; not independent human review",
              "review_manifest_sha256": sha(manifest_path), "verifier_sha256": sha(Path(__file__)),
              "protected_files_checked": len(manifest["protected"]), "input_files_checked": len(manifest["inputs"]),
              "review_outputs_checked": len(manifest["outputs"]), "candidates_checked": 14,
              "merged_candidates_checked": 78, "sequence_cells_checked": 14, "mbc_cells_checked": 28,
              "model_fit_calls": 0, "formal_release": False}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
