"""Fetch version-bound PMC assets from the current official public distribution."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.parse
import xml.etree.ElementTree as ET

from acquire_half_lysis_primary_copies import acquire
from research_utils import sha256, utc_now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-acquisition", type=Path, required=True)
    parser.add_argument("--metadata-file", required=True)
    parser.add_argument("--expected-pmcid", required=True)
    parser.add_argument("--expected-doi", required=True)
    parser.add_argument("--version", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if Path(args.metadata_file).name != args.metadata_file:
        raise ValueError("Metadata must be an acquired basename")
    manifest_path = args.metadata_acquisition / "acquisition_manifest.json"
    acquisition = json.loads(manifest_path.read_text(encoding="utf-8"))
    metadata_path = args.metadata_acquisition / args.metadata_file
    binding = next(row for row in acquisition["records"] if row["filename"] == args.metadata_file)
    if sha256(metadata_path) != binding["sha256"]:
        raise ValueError("Cloud metadata acquisition changed")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if (metadata["pmcid"] != args.expected_pmcid or metadata["version"] != args.version
            or str(metadata.get("doi", "")).lower() != args.expected_doi.lower()
            or metadata.get("is_retracted") is not False or metadata.get("is_manuscript") is not False):
        raise ValueError("Cloud article version identity mismatch or not confirmed published/non-retracted")
    prefix = args.expected_pmcid + "." + str(args.version)
    requests = []
    for kind in ("xml", "pdf"):
        value = metadata.get(kind + "_url")
        if not value:
            continue
        parsed = urllib.parse.urlsplit(value)
        expected_path = "/" + prefix + "/" + prefix + "." + kind
        if parsed.scheme != "s3" or parsed.netloc != "pmc-oa-opendata" or parsed.path != expected_path:
            raise ValueError("Asset is not the exact official version object")
        digests = urllib.parse.parse_qs(parsed.query).get("md5", [])
        if len(digests) != 1 or len(digests[0]) != 32:
            raise ValueError("Official metadata lacks a unique MD5 asset binding")
        requests.append({"url": "https://pmc-oa-opendata.s3.amazonaws.com" + parsed.path,
                         "filename": prefix + "." + kind, "expected_md5": digests[0],
                         "role": "official_version_bound_original_asset",
                         "license_note": "Individual publication license must be reviewed; acquisition is not assay approval."})
    args.output.mkdir(parents=True, exist_ok=False)
    records = []
    for request in requests:
        result = acquire(request, args.output)
        if result["status"] == "acquired_not_reviewed":
            path = args.output / result["filename"]
            digest = hashlib.md5(path.read_bytes()).hexdigest()
            result["observed_md5"] = digest
            result["official_md5_matches"] = digest == request["expected_md5"]
            if not result["official_md5_matches"]:
                result["status"] = "checksum_failed_no_release"
            elif path.suffix == ".xml":
                tree = ET.parse(path)
                ids = {n.get("pub-id-type"): "".join(n.itertext()).strip() for n in tree.findall(".//front/article-meta/article-id")}
                result["original_doi_matches"] = ids.get("doi", "").lower() == args.expected_doi.lower()
                result["fulltext_body_present"] = tree.find(".//body") is not None
                result["licenses"] = [" ".join(n.itertext()) for n in tree.findall(".//license")]
                if not result["original_doi_matches"]:
                    result["status"] = "original_identity_failed_no_release"
        records.append(result)
    manifest = {"generated_at": utc_now(), "scope": "Official version-bound acquisition, not molecule/assay release",
                "pmcid": metadata["pmcid"], "doi": metadata["doi"], "version": metadata["version"], "pmid": metadata.get("pmid"),
                "metadata_license_code": metadata.get("license_code"), "is_pmc_openaccess": metadata.get("is_pmc_openaccess"),
                "inputs": {str(manifest_path.resolve()): sha256(manifest_path), str(metadata_path.resolve()): sha256(metadata_path)},
                "producer_sha256": sha256(Path(__file__)),
                "helper_sha256": sha256(Path(__file__).with_name("acquire_half_lysis_primary_copies.py")),
                "records": records, "labels_released": 0, "model_fit_calls": 0}
    with (args.output / "acquisition_manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    print(json.dumps([{k: row.get(k) for k in ("filename", "status", "official_md5_matches", "fulltext_body_present")} for row in records]))


if __name__ == "__main__":
    main()
