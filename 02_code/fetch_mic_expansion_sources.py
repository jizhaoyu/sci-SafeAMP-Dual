"""Fetch the fixed MIC evidence-expansion batch; retain responses and access failures."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

from research_utils import ROOT, read_json, sha256, utc_now, write_json

PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-08.json"
FREEZE = ROOT / "03_experiments/audits/protocol_mic_08_freeze_20261002_v1.json"
CATALOG = ROOT / "03_experiments/audits/mic_source_expansion_20261002_v1/discovery_catalog.json"


def fetch(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite source acquisition: {output}")
    protocol, freeze, catalog = read_json(PROTOCOL), read_json(FREEZE), read_json(CATALOG)
    if sha256(PROTOCOL) != freeze["protocol_sha256"] or len(catalog["selected_studies"]) != protocol["search"]["batch_limit_primary_studies"]:
        raise ValueError("Frozen protocol or fixed study inventory changed")
    for name, digest in freeze["inputs"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"Protected input changed: {name}")
    output.mkdir(parents=True)
    raw = output / "raw"
    raw.mkdir()
    session = requests.Session()
    session.headers["User-Agent"] = "MIC-evidence-audit/1.0 (public literature retrieval)"
    acquisition, sources, searches = [], [], []

    def get(url: str, file: Path, params: dict | None = None) -> requests.Response | None:
        started = utc_now()
        row = {"requested_url": url, "parameters": params, "retrieval_started_at": started,
               "file": file.relative_to(output).as_posix()}
        try:
            response = session.get(url, params=params, timeout=45)
            file.write_bytes(response.content)
            row.update({"http_status": response.status_code, "resolved_url": response.url,
                        "content_type": response.headers.get("Content-Type", ""), "sha256": sha256(file),
                        "retrieval_completed_at": utc_now()})
            acquisition.append(row)
            return response
        except requests.RequestException as exc:
            row.update({"http_status": None, "exception": str(exc), "retrieval_completed_at": utc_now()})
            acquisition.append(row)
            return None

    for index, theme in enumerate(protocol["search"]["themes"]):
        for channel, url, params in (
            ("europepmc", "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
             {"query": theme, "format": "json", "pageSize": 20, "resultType": "core"}),
            ("openalex", "https://api.openalex.org/works", {"search": theme, "per-page": 20}),
        ):
            response = get(url, raw / f"search_{channel}_{index}.json", params)
            count = None
            if response is not None and response.ok:
                try:
                    data = response.json()
                    count = data.get("hitCount") if channel == "europepmc" else data.get("meta", {}).get("count")
                except ValueError:
                    pass
            searches.append({"channel": channel, "theme": theme, "reported_hits": count,
                             "discovery_response_saved": response is not None})
            print(json.dumps(searches[-1]), flush=True)
    for ordinal, lead in enumerate(catalog["selected_studies"], 1):
        source = {**lead, "review_order": ordinal, "files": [], "metadata": [], "full_text_available": False}
        if lead.get("pmcid"):
            query = "EXT_ID:" + lead["pmcid"]
        elif lead.get("pmid"):
            query = "EXT_ID:" + lead["pmid"] + " AND SRC:MED"
        elif lead.get("doi"):
            query = 'DOI:"' + lead["doi"] + '"'
        else:
            query = None
        if query is not None:
            file = raw / f"{lead['source_id']}_metadata.json"
            response = get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", file,
                           {"query": query, "format": "json", "resultType": "core", "pageSize": 10})
            if response is not None:
                source["files"].append(file.relative_to(output).as_posix())
            if response is not None and response.ok:
                try:
                    source["metadata"] = response.json().get("resultList", {}).get("result", [])
                except ValueError:
                    pass
            pmcids = [item["pmcid"] for item in source["metadata"] if item.get("pmcid")]
            pmcid = lead.get("pmcid") or (pmcids[0] if pmcids else None)
            if pmcid:
                file = raw / f"{lead['source_id']}.xml"
                response = get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML", file)
                if response is not None:
                    source["files"].append(file.relative_to(output).as_posix())
                if response is not None and response.ok:
                    try:
                        root = ET.fromstring(response.content)
                        article = root if root.tag == "article" else root.find(".//article")
                        source["full_text_available"] = article is not None and article.find("body") is not None
                    except ET.ParseError:
                        pass
        if lead.get("pdf_url"):
            file = raw / f"{lead['source_id']}.pdf"
            response = get(lead["pdf_url"], file)
            if response is not None:
                source["files"].append(file.relative_to(output).as_posix())
            if response is not None and response.ok and response.content.startswith(b"%PDF"):
                source["full_text_available"] = True
        sources.append(source)
        write_json(output / "acquisition_progress.json", {"sources": sources, "requests": acquisition})
        print(json.dumps({"source": lead["source_id"], "full_text_available": source["full_text_available"]}), flush=True)
    result = {"status": "primary_source_acquisition_completed", "generated_at": utc_now(),
              "protocol_id": protocol["protocol_id"], "protocol_sha256": sha256(PROTOCOL),
              "protocol_frozen_at": freeze["frozen_at"], "searches": searches,
              "sources": sources, "requests": acquisition, "new_records_released_for_training": 0,
              "script_sha256": sha256(Path(__file__)),
              "inputs": {p.relative_to(ROOT).as_posix(): sha256(p) for p in (PROTOCOL, FREEZE, CATALOG)},
              "outputs": {p.relative_to(output).as_posix(): sha256(p) for p in sorted(raw.iterdir())}}
    write_json(output / "manifest.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = fetch(args.output)
    print(json.dumps({"status": result["status"], "sources": len(result["sources"]),
                      "full_texts": sum(s["full_text_available"] for s in result["sources"])}, indent=2))
