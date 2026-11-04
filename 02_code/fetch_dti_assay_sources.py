"""Acquire version-bound BindingDB assay maps and source metadata, no release."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path
import urllib.parse

from dti_source_preflight import acquire, save
from research_utils import sha256, utc_now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    state_path = args.source_inventory / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state["status"] != "source_inventory_complete_evidence_review_pending" or state["observations_released"] != 0:
        raise ValueError("Unexpected source inventory status")
    inputs = {str(state_path.resolve()): sha256(state_path)}
    for name, expected in state["outputs"].items():
        path = args.source_inventory / name
        if sha256(path) != expected:
            raise ValueError(f"Source inventory output changed: {path}")
        inputs[str(path.resolve())] = expected
    with (args.source_inventory / "kd_exact_observations.csv").open(encoding="utf-8", newline="") as stream:
        pmids = sorted({r["PMID"].strip() for r in csv.DictReader(stream) if r["PMID"].strip()})
    if not all(pmid.isdigit() for pmid in pmids):
        raise ValueError("PMID field contains unresolved multi-reference identifiers")
    sources = []
    base = "https://www.bindingdb.org/rwd/bind/downloads/"
    for stem in ["BindingDB_Assays_202610_tsv", "BindingDB_rsid_eaids_202610_tsv"]:
        for extension in ["zip", "md5"]:
            sources.append((stem + "." + extension, base + stem + "." + extension,
                            "official_assay_description" if "Assays" in stem else "official_reaction_assay_map"))
    query = "SRC:MED AND (" + " OR ".join("EXT_ID:" + p for p in pmids) + ")"
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
        {"query": query, "format": "json", "resultType": "core", "pageSize": 1000})
    sources.append(("measurement_sources_metadata.json", url, "publication_identity_fulltext_locator_only"))
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / "source_requests.json", sources)
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(lambda item: acquire(args.output, *item), sources))
    manifest = {"generated_at": utc_now(), "scope": "Assay map acquisition and literature metadata, not evidence approval",
                "inputs": inputs, "requested_pmids": pmids, "records": records,
                "producer_sha256": sha256(Path(__file__)),
                "helper_sha256": sha256(Path(__file__).with_name("dti_source_preflight.py")),
                "source_requests_sha256": sha256(args.output / "source_requests.json"),
                "observations_released": 0, "model_fit_calls": 0}
    save(args.output / "acquisition_manifest.json", manifest)
    print(json.dumps([{"filename": r["filename"], "status": r["status"], "error": r.get("error")} for r in records]))


if __name__ == "__main__":
    main()
