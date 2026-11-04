"""Fetch exact public supplementary objects bound by official PMC metadata."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.parse
import zipfile

from acquire_half_lysis_primary_copies import acquire
from research_utils import sha256, utc_now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-acquisition", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    manifest_file = args.metadata_acquisition / "acquisition_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    inputs = {str(manifest_file.resolve()): sha256(manifest_file)}
    requests = []
    specs = [("bet_cloud_metadata.json", "PMC5117811", 27775715, "10.1038/nchembio.2209", True,
              {"NIHMS807910-supplement-1.docx", "NIHMS807910-supplement-2.pdf", "PMC5117811.1.pdf"}),
             ("nos_cloud_metadata.json", "PMC4139154", 25089924, "10.1021/bi500561h", False,
              {"bi500561h_si_001.pdf", "PMC4139154.1.pdf"})]
    for name, pmcid, pmid, doi, manuscript, selected in specs:
        row = next(r for r in manifest["records"] if r["filename"] == name)
        path = args.metadata_acquisition / name
        if row["status"] != "acquired_not_reviewed" or sha256(path) != row["sha256"]:
            raise ValueError("Cloud metadata acquisition/checksum failed")
        inputs[str(path.resolve())] = row["sha256"]
        metadata = json.loads(path.read_text(encoding="utf-8"))
        if (metadata["pmcid"] != pmcid or metadata["pmid"] != pmid or metadata["version"] != 1
                or metadata["doi"].lower() != doi or metadata["is_manuscript"] != manuscript
                or metadata["is_retracted"] is not False):
            raise ValueError("Exact cloud article identity/version/type differs")
        urls = metadata["media_urls"] + [metadata["pdf_url"]]
        found = set()
        for value in urls:
            parsed = urllib.parse.urlsplit(value)
            basename = Path(parsed.path).name
            if basename not in selected:
                continue
            expected_md5 = urllib.parse.parse_qs(parsed.query).get("md5", [])
            if (parsed.scheme != "s3" or parsed.netloc != "pmc-oa-opendata"
                    or not parsed.path.startswith("/" + pmcid + ".1/")
                    or len(expected_md5) != 1 or len(expected_md5[0]) != 32):
                raise ValueError("Supplement is not an exact MD5-bound public version object")
            found.add(basename)
            requests.append({"filename": pmcid + "_" + basename,
                "url": "https://pmc-oa-opendata.s3.amazonaws.com" + parsed.path,
                "expected_md5": expected_md5[0], "pmid": str(pmid), "doi": doi,
                "source_version": 1, "is_manuscript": manuscript, "license_code": metadata.get("license_code"),
                "role": "official_exact_version_original_or_supplement_asset",
                "license_note": "Private academic source review only; retain individual terms and no blanket redistribution approval"})
        if found != selected:
            raise ValueError("Official metadata does not list every requested asset")
    args.output.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(lambda r: acquire(r, args.output), requests))
    for row in records:
        if row["status"] != "acquired_not_reviewed":
            continue
        path = args.output / row["filename"]
        row["observed_md5"] = hashlib.md5(path.read_bytes()).hexdigest()
        row["official_md5_matches"] = row["observed_md5"] == row["expected_md5"]
        if not row["official_md5_matches"]:
            row["status"] = "checksum_failed_no_release"
        elif path.suffix == ".docx":
            try:
                with zipfile.ZipFile(path) as archive:
                    if archive.getinfo("word/document.xml").file_size == 0:
                        raise ValueError("Empty DOCX document")
                row["docx_container_verified"] = True
            except (zipfile.BadZipFile, KeyError, ValueError) as exc:
                row.update(status="invalid_docx_no_release", error=str(exc))
    result = {"generated_at": utc_now(), "inputs": inputs, "records": records,
              "producer_sha256": sha256(Path(__file__)),
              "helper_sha256": sha256(Path(__file__).with_name("acquire_half_lysis_primary_copies.py")),
              "scope": "Exact-version assets acquired and container/hash checked; assay review remains separate",
              "observations_released": 0, "model_fit_calls": 0}
    with (args.output / "acquisition_manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps([{k:r.get(k) for k in ["filename", "status", "official_md5_matches"]} for r in records]))


if __name__ == "__main__":
    main()
