"""Fetch a bounded dbAMP record-page sample to assess evidence traceability."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review(observations_csv: Path, output_dir: Path, limit: int = 25) -> dict:
    observations_csv, output_dir = Path(observations_csv), Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing detail-page audit: {output_dir}")
    output_dir.mkdir(parents=True)
    page_dir = output_dir / "record_pages"
    page_dir.mkdir()

    observations = pd.read_csv(observations_csv)
    candidates = observations.drop_duplicates("sequence")
    candidates = candidates[
        (candidates["max_development_identity_protocol_amd_02"] < 0.40)
        & (~candidates["exact_development_sequence_overlap"].astype(bool))
    ]
    candidate_pool_size = int(len(candidates))
    candidates = candidates.sort_values("max_development_identity_protocol_amd_02").drop_duplicates("dbamp_id").head(limit)

    rows = []
    page_hashes = {}
    for candidate in candidates.itertuples(index=False):
        dbamp_id = str(candidate.dbamp_id)
        url = f"https://ycclab.cuhk.edu.cn/dbAMP/information.php?db={dbamp_id}"
        path = page_dir / f"{dbamp_id}.html"
        result = subprocess.run(
            ["curl.exe", "-k", "-L", "--fail", "--silent", "--show-error", "--max-time", "30", "-o", str(path), url],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            rows.append({"dbamp_id": dbamp_id, "page_url": url, "fetch_status": f"curl_error_{result.returncode}", "error": result.stderr.strip()})
            path.unlink(missing_ok=True)
            continue

        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
        fields = {}
        pubmed_ids = set()
        for tr in soup.find_all("tr"):
            cells = tr.find_all("td", recursive=False)
            if len(cells) < 2:
                continue
            key = " ".join(cells[0].get_text(" ", strip=True).split())
            value = " ".join(cells[1].get_text(" ", strip=True).split())
            if key in {"Experimental Evidence", "Target", "Sequence", "Source"}:
                fields[key] = value
            if key == "PubMed":
                for link in cells[1].find_all("a", href=True):
                    pubmed_ids.update(re.findall(r"\d{5,9}", link.get("href", "")))
                pubmed_ids.update(re.findall(r"\b\d{5,9}\b", value))

        expected_sequence = str(candidate.sequence)
        page_sequence = fields.get("Sequence", "")
        rows.append({
            "dbamp_id": dbamp_id,
            "page_url": url,
            "fetch_status": "fetched_tls_certificate_not_verified",
            "page_sha256": sha256(path),
            "sequence_matches_download": page_sequence == expected_sequence,
            "experimental_evidence": fields.get("Experimental Evidence", "missing"),
            "target_raw_from_detail_page": fields.get("Target", ""),
            "pubmed_ids": ";".join(sorted(pubmed_ids)),
            "source_organism": fields.get("Source", ""),
            "sequence": expected_sequence,
            "max_development_identity": float(candidate.max_development_identity_protocol_amd_02),
            "page_file": str(path),
        })
        page_hashes[dbamp_id] = sha256(path)

    audit_path = output_dir / "entry_review.csv"
    pd.DataFrame(rows).to_csv(audit_path, index=False, encoding="utf-8-sig")
    summary = {
        "status": "bounded_record_page_review",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_observations_sha256": sha256(observations_csv),
        "candidate_pool_below_cutoff_nonexact": candidate_pool_size,
        "sampled_unique_entry_count": int(len(candidates)),
        "requested_page_count": int(len(candidates)),
        "fetched_page_count": int(len(page_hashes)),
        "experimental_evidence_yes": sum(row.get("experimental_evidence", "").upper() == "YES" for row in rows),
        "experimental_evidence_no": sum(row.get("experimental_evidence", "").upper() == "NO" for row in rows),
        "sequence_mismatch_count": sum(row.get("sequence_matches_download") is False for row in rows),
        "transport_note": "Pages fetched with curl -k because this endpoint's TLS handshake failed normal certificate validation; fetched content is provisional and requires source-side validation.",
        "record_page_hashes": page_hashes,
        "output": str(audit_path),
    }
    (output_dir / "manifest.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    print(json.dumps(review(args.observations, args.output, args.limit), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
