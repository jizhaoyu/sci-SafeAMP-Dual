"""Retrieve public original-source assets into an immutable evidence directory.

This entrypoint never releases records or labels. URL derivation is recorded;
file extensions alone never certify that a response is a research document.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"%PDF-"):
        return "pdf"
    if zipfile.is_zipfile(io.BytesIO(data)):
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            if "word/document.xml" in package.namelist():
                return "docx"
        return "zip"
    if b"<html" in data[:2048].lower() or b"<!doctype html" in data[:2048].lower():
        return "html"
    return "unverified"


def fetch(case: dict, output: Path) -> dict:
    record = {**case, "attempted_at": utc_now(), "verified_original_document": False}
    try:
        request = urllib.request.Request(case["url"], headers={"User-Agent": "MIC-evidence-source-review/1.0"})
        with urllib.request.urlopen(request, timeout=25) as response:
            data = response.read(32 * 1024 * 1024 + 1)
            record.update(http_status=response.status, final_url=response.url,
                          content_type=response.headers.get("Content-Type", ""))
        if len(data) > 32 * 1024 * 1024:
            raise ValueError("Response exceeds the 32 MiB acquisition limit")
        kind = classify(data)
        filename = case["id"] + "." + (kind if kind != "unverified" else "bin")
        (output / filename).write_bytes(data)
        record.update(file=filename, bytes=len(data), sha256=digest(data), detected_type=kind,
                      verified_original_document=kind == case["expected_type"], status="retrieved")
    except urllib.error.HTTPError as exc:
        record.update(status="http_error", http_status=exc.code)
    except Exception as exc:
        record.update(status="retrieval_failed", error_type=type(exc).__name__)
    return record


def acquire(output: Path) -> dict:
    root = Path(__file__).resolve().parents[1]
    xml = root / "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/bmap2025.xml"
    xml_text = xml.read_text(encoding="utf-8")
    figure_path = "blobs/fcf5/12207908/1f6489e74c5d/MLF2-4-275-g003.jpg"
    if figure_path not in xml_text or 'MLF2-4-275-s003.docx' not in xml_text:
        raise ValueError("Expected original XML asset references are missing")
    cases = [
        {"id": "bmap_figure_1", "url": "https://cdn.ncbi.nlm.nih.gov/pmc/" + figure_path,
         "expected_type": "jpeg", "url_basis": "cloudpmc-path processing instruction in original XML"},
        {"id": "bmap_supplement_instance", "url": "https://pmc.ncbi.nlm.nih.gov/articles/instance/12207908/bin/MLF2-4-275-s003.docx",
         "expected_type": "docx", "url_basis": "PMCID and exact supplementary filename in original XML; instance route derived"},
        {"id": "bmap_supplement_europepmc", "url": "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12207908/supplementaryFiles",
         "expected_type": "zip", "url_basis": "Europe PMC public supplementaryFiles endpoint and source PMCID"},
    ]
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda case: fetch(case, output), cases))
    manifest = {"generated_at": utc_now(), "status": "source_retrieval_only_no_release",
                "primary_doi": "10.1002/mlf2.70020", "source_xml": xml.relative_to(root).as_posix(),
                "source_xml_sha256": digest(xml.read_bytes()), "script_sha256": digest(Path(__file__).read_bytes()),
                "attempts": results, "new_labels_released": 0, "training_started": False}
    (output / "acquisition.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = acquire(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
