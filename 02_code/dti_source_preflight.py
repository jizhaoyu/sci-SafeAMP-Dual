"""Acquire official DTI sources and inventory Kd fields without evidence release."""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import urllib.request
import zipfile

from research_utils import ROOT, sha256, utc_now


SOURCES = [
    ("tdc_dti.html", "https://tdcommons.ai/multi_pred_tasks/dti/", "task_documentation"),
    ("bindingdb_download.html", "https://www.bindingdb.org/rwd/bind/chemsearch/marvin/Download.jsp", "download_index"),
    ("davis_article.html", "https://www.nature.com/articles/nbt.1990", "original_article_locator_not_fulltext_approval"),
    ("BindingDB_BindingDB_Articles_202610_tsv.zip", "https://www.bindingdb.org/rwd/bind/downloads/BindingDB_BindingDB_Articles_202610_tsv.zip", "database_curated_article_subset_not_primary_approval"),
    ("bindingdb_articles.md5", "https://www.bindingdb.org/rwd/bind/downloads/BindingDB_BindingDB_Articles_202610_tsv.md5", "official_archive_md5"),
]
PROTECTED = [
    "04_paper/research_status.json",
    "03_experiments/prepared/amd02_evidence_clean_20261001/records.csv",
    "03_experiments/prepared/amd02_evidence_clean_20261001/cluster_membership.csv",
    "03_experiments/prepared/amd02_evidence_clean_20261001/manifest.json",
    "03_experiments/audits/mic_training_readiness_20261004_v26.json",
    "03_experiments/audits/project_closeout_20261005_v1/review/merged_candidate_decisions.csv",
]


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def acquire(directory, name, url, role):
    record = {"filename": name, "url": url, "role": role, "started_at": utc_now(),
              "evidence_approved": False, "license_review": "pending"}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "DTI-SourceAudit/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read(64 * 1024 * 1024 + 1)
            record.update(final_url=response.url, content_type=response.headers.get("Content-Type"))
        if len(body) > 64 * 1024 * 1024:
            raise ValueError("Resource exceeds 64 MiB bound")
        if name.endswith(".zip") and not zipfile.is_zipfile(io.BytesIO(body)):
            raise ValueError("Expected ZIP archive")
        with (directory / name).open("xb") as stream:
            stream.write(body)
        record.update(status="acquired_not_reviewed", sha256=sha256(directory / name), bytes=len(body))
    except Exception as exc:
        record.update(status="acquisition_failed", error_type=type(exc).__name__, error=str(exc))
    record["finished_at"] = utc_now()
    return record


def kd_kind(value):
    value = value.strip()
    if not value:
        return "missing"
    if value.startswith((">", "<", "~", "≥", "≤")):
        return "non_exact_comparator_unapproved"
    try:
        number = float(value)
    except ValueError:
        return "non_numeric_or_interval"
    return "exact_positive_numeric" if math.isfinite(number) and number > 0 else "invalid_numeric"


def inventory(directory):
    archive = directory / SOURCES[3][0]
    official = (directory / "bindingdb_articles.md5").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[a-fA-F0-9]{32}", official):
        raise ValueError("Official MD5 resource is not a checksum")
    actual_md5 = hashlib.md5(archive.read_bytes()).hexdigest()
    if actual_md5 != official.lower():
        raise ValueError("Official archive MD5 mismatch")
    counts, coverage = Counter(), Counter()
    ligands, sequences, article_ids = set(), set(), set()
    required = ["Kd (nM)", "Ligand SMILES", "BindingDB MonomerID", "Article DOI", "PMID",
                "Number of Protein Chains in Target (>1 implies a multichain complex)",
                "BindingDB Target Chain Sequence"]
    csv.field_size_limit(16 * 1024 * 1024)
    with zipfile.ZipFile(archive) as bundle:
        members = [n for n in bundle.infolist() if not n.is_dir() and n.filename.endswith(".tsv")]
        if len(members) != 1 or members[0].file_size > 512 * 1024 * 1024:
            raise ValueError("Expected one bounded TSV archive member")
        with bundle.open(members[0]) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            columns = reader.fieldnames or []
            save(directory / "columns.json", columns)
            missing = sorted(set(required) - set(columns))
            if missing:
                raise ValueError(f"Required source fields absent: {missing}")
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"Malformed TSV row {reader.line_num}")
                counts["all_measurement_rows"] += 1
                kind = kd_kind(row["Kd (nM)"])
                counts[kind] += 1
                if kind != "exact_positive_numeric":
                    continue
                coverage["smiles_present"] += bool(row["Ligand SMILES"].strip())
                coverage["single_target_chain_declared"] += row[required[5]].strip() == "1"
                sequence = row["BindingDB Target Chain Sequence"].strip()
                coverage["first_target_chain_sequence_present"] += bool(sequence)
                doi, pmid = row["Article DOI"].strip(), row["PMID"].strip()
                coverage["article_doi_present"] += bool(doi)
                coverage["pmid_present"] += bool(pmid)
                coverage["article_doi_or_pmid_present"] += bool(doi or pmid)
                if row["BindingDB MonomerID"].strip():
                    ligands.add(row["BindingDB MonomerID"].strip())
                if sequence:
                    sequences.add(sequence)
                if doi:
                    article_ids.add(doi)
    return {"scope": "Complete database field census; no primary assay or molecular identity approval",
            "official_md5": official.lower(), "actual_md5": actual_md5, "official_md5_matches": True,
            "archive_sha256": sha256(archive), "tsv_member": members[0].filename,
            "counts": dict(counts), "exact_kd_field_coverage": dict(coverage),
            "unique_raw_ligand_ids_with_exact_kd": len(ligands),
            "unique_first_chain_sequences_with_exact_kd": len(sequences),
            "unique_raw_article_doi_strings_with_exact_kd": len(article_ids),
            "structure_standardized": False, "protein_constructs_verified": False,
            "study_aliases_resolved": False, "independence_audited": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    before = {p: sha256(ROOT / p) for p in PROTECTED}
    save(args.output / "protected_inputs.json", before)
    acquisition = [acquire(args.output, *source) for source in SOURCES]
    save(args.output / "acquisition_manifest.json", {"generated_at": utc_now(), "records": acquisition,
         "producer_sha256": sha256(Path(__file__)), "source_spec": SOURCES})
    error = None
    try:
        if any(r["status"] != "acquired_not_reviewed" for r in acquisition[3:]):
            raise ValueError("Article subset or official checksum acquisition failed")
        result = inventory(args.output)
        save(args.output / "inventory.json", result)
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
    after = {p: sha256(ROOT / p) for p in PROTECTED}
    save(args.output / "verification.json", {"generated_at": utc_now(), "protected_files_unchanged": before == after,
         "before": before, "after": after, "inventory_completed": error is None,
         "scope": "Source acquisition, official archive checksum, field census and historical protection only"})
    outputs = {p.name: sha256(p) for p in args.output.iterdir() if p.is_file()}
    state = {"generated_at": utc_now(), "research_direction": "DTI", "endpoint": "Kd",
             "status": "source_inventory_complete_evidence_review_pending" if error is None else "source_preflight_blocked",
             "error": error, "training_ready": False, "observations_released": 0, "model_fit_calls": 0,
             "protocol_status": "not_frozen", "split_audit": "not_computed",
             "protected_files_unchanged": before == after, "outputs": outputs,
             "producer_sha256": sha256(Path(__file__)),
             "next_stage": "Original-source, actual molecule/construct identity and assay review before isolation and protocol freeze"}
    save(args.output / "state.json", state)
    print(json.dumps({k: state[k] for k in ["status", "error", "training_ready", "protected_files_unchanged"]}))
    if error is not None or before != after:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
