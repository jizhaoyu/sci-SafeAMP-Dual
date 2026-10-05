"""Archive public source responses. Metadata and access pages never release assays."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[1]


def main():
    out = BASE / "additional_metadata"
    out.mkdir(exist_ok=False)
    urls = {
        "brevinin_2_ia_crossref.json": "https://api.crossref.org/works/10.1007/s00049-019-00287-z",
        "brevinin_2_ia_publisher.html": "https://link.springer.com/article/10.1007/s00049-019-00287-z",
        "slay_pmc.html": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5786472/",
    }
    rows = []
    for name, url in urls.items():
        row = {"url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
               "purpose": "metadata_or_access_check_only", "license": "not_verified"}
        try:
            with urlopen(Request(url, headers={"User-Agent": "ResearchEvidenceAudit/1.0"}), timeout=25) as response:
                data = response.read()
                row.update(final_url=response.url, http_status=response.status,
                           content_type=response.headers.get("Content-Type", ""))
            with (out / name).open("xb") as stream:
                stream.write(data)
            row.update(file=name, sha256=hashlib.sha256(data).hexdigest(), status="response_archived")
            if name.endswith(".json"):
                message = json.loads(data)["message"]
                assert message["DOI"].lower() == "10.1007/s00049-019-00287-z"
                assert "Indosylvirana aurantiaca" in message["title"][0]
                row["title"] = message["title"][0]
                row["doi_verified_by_metadata"] = message["DOI"]
            else:
                text = data.decode("utf-8", errors="replace").lower()
                row["access_indicator"] = (
                    "challenge_page" if "recaptcha" in text or "checking your browser" in text
                    else "subscription_preview" if "preview of subscription content" in text
                    else "response_requires_manual_review")
        except Exception as exc:
            row.update(status="request_failed", error=f"{type(exc).__name__}: {exc}")
        rows.append(row)
    record = {"generated_at": datetime.now(timezone.utc).isoformat(), "requests": rows,
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "measurement_release_performed": False}
    with (out / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    print(json.dumps([{key: row.get(key) for key in ("url", "status", "access_indicator")} for row in rows]))


if __name__ == "__main__":
    main()
