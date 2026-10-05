"""Archive public PMC sources without treating challenge pages as originals."""
import csv
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
PREVIOUS = ROOT / "03_experiments/audits/hc50_primary_followup_20261004_v1/review_v2"
PREVIOUS_SHA = "a9532b01b58682421330abb4b4e7e41c9aae4b5cc1d2726bcbcc0e4e720968e1"
SOURCES = {
    "pmc_article.html": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5786472/",
    "main_manuscript.pdf": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5786472/pdf/nihms926512.pdf",
    "supplement_6_table_s2.pdf": "https://pmc.ncbi.nlm.nih.gov/articles/instance/5786472/bin/NIHMS926512-supplement-6.pdf",
    "supplement_7_table_s3.pdf": "https://pmc.ncbi.nlm.nih.gov/articles/instance/5786472/bin/NIHMS926512-supplement-7.pdf",
    "bioc_article.xml": "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/PMC5786472/unicode",
    "pmc_oa_response.xml": "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC5786472",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(item, out):
    name, url = item
    row = {"requested_file": name, "url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
           "license": "not_verified; local original-source review only", "pmid": "29307492",
           "pmcid": "PMC5786472", "doi": "10.1016/j.cell.2017.12.009"}
    try:
        request = Request(url, headers={"User-Agent": "ResearchEvidenceAudit/1.0"})
        with urlopen(request, timeout=25) as response:
            data = response.read()
            row.update(final_url=response.url, http_status=response.status,
                       content_type=response.headers.get("Content-Type", ""))
        text = data.decode("utf-8", errors="replace").lower()
        is_pdf = data.startswith(b"%PDF-")
        if "recaptcha" in text or "checking your browser" in text:
            status = "challenge_page_not_original"
        elif name.endswith(".pdf") and not is_pdf:
            status = "non_pdf_response_not_original"
        elif name == "pmc_article.html" and "IHRDQQHESFLDARPEPGLTE".lower() in text and "Analysis of Hemolytic Activity".lower() in text:
            status = "primary_html_acquired"
        elif is_pdf:
            status = "pdf_acquired_requires_identity_review"
        elif name == "bioc_article.xml" and "ihrdqqhesfldarpepglte" in text:
            status = "primary_bioc_xml_acquired_requires_review"
        else:
            status = "response_archived_not_validated_original"
        # Do not give HTML errors the .pdf suffix.
        filename = name if (not name.endswith(".pdf") or is_pdf) else name + ".response.html"
        path = out / "raw" / filename
        with path.open("xb") as stream:
            stream.write(data)
        row.update(status=status, file=path.relative_to(out).as_posix(), sha256=sha(path), bytes=len(data))
    except Exception as exc:
        row.update(status="request_failed", error=f"{type(exc).__name__}: {exc}")
    return row


def main():
    out = BASE / "acquisition"
    if out.exists():
        raise FileExistsError(out)
    if sha(PREVIOUS / "manifest.json") != PREVIOUS_SHA:
        raise ValueError("Previous review manifest changed")
    prior = json.loads((PREVIOUS / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in prior["outputs"].items():
        if sha(PREVIOUS / name) != expected:
            raise ValueError(f"Previous review output changed: {name}")
    with (PREVIOUS / "candidate_decisions.csv").open(encoding="utf-8-sig") as stream:
        subset = [row for row in csv.DictReader(stream) if row["pmid"] == "29307492"]
    if len(subset) != 14 or len({r["candidate_id"] for r in subset}) != 14:
        raise ValueError("Fixed SLAY coverage is not fourteen")
    protected = dict(prior["protected"])
    protected["03_experiments/audits/hc50_primary_followup_20261004_v1/review_v2/manifest.json"] = PREVIOUS_SHA
    for path in PREVIOUS.iterdir():
        if path.is_file():
            protected[path.relative_to(ROOT).as_posix()] = sha(path)
    protected["03_experiments/audits/hc50_primary_followup_20261004_v1/verification.json"] = sha(PREVIOUS.parent / "verification.json")
    for name, expected in protected.items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"Protected file changed: {name}")
    (out / "raw").mkdir(parents=True, exist_ok=False)
    with (out / "candidate_subset.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(subset[0]))
        writer.writeheader()
        writer.writerows(subset)
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(lambda item: fetch(item, out), SOURCES.items()))
    with (out / "source_acquisition.json").open("x", encoding="utf-8") as stream:
        json.dump(rows, stream, ensure_ascii=False, indent=2)
    record = {"generated_at": datetime.now(timezone.utc).isoformat(), "fixed_candidate_records": 14,
              "protected": protected, "outputs": {p.relative_to(out).as_posix(): sha(p) for p in out.rglob("*") if p.is_file()},
              "script_sha256": sha(Path(__file__)), "evidence_release_performed": False}
    with (out / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    print(json.dumps([{k: row.get(k) for k in ("requested_file", "status", "bytes", "error")} for row in rows]))


if __name__ == "__main__":
    main()
