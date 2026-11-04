"""Join all exact Kd observations to official assay descriptions, no release."""
import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.parse
import zipfile

from dti_source_preflight import PROTECTED, save
from research_utils import ROOT, sha256, utc_now


def bind(path, inputs, expected=None):
    digest = sha256(path)
    if expected is not None and digest != expected:
        raise ValueError(f"Checksum changed: {path}")
    inputs[str(path.resolve())] = digest


def checked_tsv(directory, stem, inputs):
    archive, md5file = directory / (stem + ".zip"), directory / (stem + ".md5")
    bind(archive, inputs)
    bind(md5file, inputs)
    expected = md5file.read_text(encoding="utf-8").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{32}", expected) or hashlib.md5(archive.read_bytes()).hexdigest() != expected:
        raise ValueError(f"Official MD5 mismatch: {stem}")
    with zipfile.ZipFile(archive) as bundle:
        items = [i for i in bundle.infolist() if not i.is_dir() and i.filename.endswith(".tsv")]
        if len(items) != 1 or items[0].file_size > 512 * 1024 * 1024:
            raise ValueError("Unexpected ZIP members or uncompressed size")
        with bundle.open(items[0]) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError("Missing or duplicate TSV header")
            for row in reader:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError(f"Malformed row in {stem}, line {reader.line_num}")
                yield row


def norm_doi(value):
    value = value.strip().lower()
    for prefix in ["https://doi.org/", "http://doi.org/", "doi:"]:
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    inputs = {}
    state_path = args.source_inventory / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    bind(state_path, inputs)
    for path, expected in state["inputs"].items():
        bind(Path(path), inputs, expected)
    for name, expected in state["outputs"].items():
        bind(args.source_inventory / name, inputs, expected)
    bind(Path(__file__).with_name("audit_dti_kd_source_fields.py"), inputs, state["producer_sha256"])
    if state["observations_released"] != 0 or state["model_fit_calls"] != 0:
        raise ValueError("Predecessor unexpectedly approved observations or trained")
    manifest_path = args.acquisition / "acquisition_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bind(manifest_path, inputs)
    bind(Path(__file__).with_name("fetch_dti_assay_sources.py"), inputs, manifest["producer_sha256"])
    bind(Path(__file__).with_name("dti_source_preflight.py"), inputs, manifest["helper_sha256"])
    for path, expected in manifest["inputs"].items():
        bind(Path(path), inputs, expected)
    for record in manifest["records"]:
        if record["status"] != "acquired_not_reviewed":
            raise ValueError(f"Missing assay/metadata source: {record['filename']}")
        bind(args.acquisition / record["filename"], inputs, record["sha256"])
    before = {path: sha256(ROOT / path) for path in PROTECTED}
    prior_verification = json.loads((args.source_inventory / "verification.json").read_text(encoding="utf-8"))
    if not prior_verification["passed"] or before != prior_verification["after"]:
        raise ValueError("Predecessor verification or historical protection differs")
    with (args.source_inventory / "kd_exact_observations.csv").open(encoding="utf-8", newline="") as stream:
        observations = list(csv.DictReader(stream))
    wanted = {r["BindingDB Reactant_set_id"] for r in observations}
    by_line = {r["source_tsv_line"]: r for r in observations}
    if len(by_line) != len(observations):
        raise ValueError("Duplicate source-line identities")
    duplicate_ids = {key: [r["source_tsv_line"] for r in observations if r["BindingDB Reactant_set_id"] == key]
                     for key, count in Counter(r["BindingDB Reactant_set_id"] for r in observations).items() if count > 1}
    mapping = defaultdict(set)
    for row in checked_tsv(args.acquisition, "BindingDB_rsid_eaids_202610_tsv", inputs):
        if row["REACTANT_SET_ID"] in wanted:
            mapping[row["REACTANT_SET_ID"]].add(row["ENTRYID_ASSAYID"])
    wanted_assays = set().union(*mapping.values()) if mapping else set()
    assay_map = defaultdict(set)
    for row in checked_tsv(args.acquisition, "BindingDB_Assays_202610_tsv", inputs):
        key = row["ENTRYID"] + "_" + row["ASSAYID"]
        if key in wanted_assays:
            assay_map[key].add((row["ASSAY_NAME"], row["DESCRIPTION"]))
    metadata = json.loads((args.acquisition / "measurement_sources_metadata.json").read_text(encoding="utf-8"))
    records = metadata["resultList"]["result"]
    if metadata["hitCount"] != len(records):
        raise ValueError("Metadata response is paginated or incomplete")
    by_pmid = {r["id"]: r for r in records if r.get("source") == "MED"}
    if set(by_pmid) != set(manifest["requested_pmids"]):
        raise ValueError("Metadata does not cover the exact requested PMID set")
    stats, pairs, joined = Counter(), defaultdict(list), []
    for observation in observations:
        item = dict(observation)
        rid = item["BindingDB Reactant_set_id"]
        refs = sorted(mapping.get(rid, set()))
        details = [{"entry_assay_id": ref, "assay_name": name, "description": text}
                   for ref in refs for name, text in sorted(assay_map.get(ref, set()))]
        link_ok = bool(refs) and all(any(text.strip() for _, text in assay_map.get(ref, set())) for ref in refs)
        pmid = item["PMID"].strip()
        met = by_pmid.get(pmid, {})
        doi = norm_doi(item["Article DOI"])
        identified_doi = norm_doi(met.get("doi", ""))
        source_status = ("metadata_doi_matches" if doi and doi == identified_doi else
                         "doi_disagrees_with_metadata" if doi and identified_doi else
                         "pmid_metadata_available_raw_doi_missing" if met and not doi else
                         "doi_or_metadata_incomplete")
        item.update(entry_assay_ids=refs, assay_descriptions=details,
                    observation_id="bindingdb_202610_articles_line_" + item["source_tsv_line"],
                    assay_link_complete=link_ok, source_identity_status=source_status,
                    metadata_doi=met.get("doi", ""), pmcid=met.get("pmcid", ""),
                    original_review_status="pending_original_measurement_and_molecular_identity",
                    formal_release=False)
        stats["total_observations"] += 1
        stats["assay_link_complete"] += link_ok
        stats["mapping_missing"] += not refs
        stats["multiple_assay_keys"] += len(refs) > 1
        stats["description_missing_or_blank"] += bool(refs) and not link_ok
        stats[source_status] += 1
        key = (item["BindingDB MonomerID"], item["BindingDB Target Chain Sequence 1"])
        pairs[key].append({"reaction_id": rid, "source_tsv_line": item["source_tsv_line"], "kd_nM": item["Kd (nM)"], "pmid": pmid,
                           "article_doi": item["Article DOI"], "assay_keys": refs})
        joined.append(item)
    differing = [{"raw_ligand_id": key[0], "raw_sequence_sha256": hashlib.sha256(key[1].encode()).hexdigest(),
                  "observations": values, "decision": "measurement_difference_requires_context_not_automatic_conflict"}
                 for key, values in pairs.items() if len({Decimal(v["kd_nM"]) for v in values}) > 1]
    stats["raw_pairs_with_multiple_exact_values"] = len(differing)
    stats["duplicate_reaction_id_groups_preserved"] = len(duplicate_ids)
    # Re-read complete raw records to retain target names/construct annotations, not just sequences.
    raw_archive = next(Path(p) for p in state["inputs"] if p.endswith("BindingDB_BindingDB_Articles_202610_tsv.zip"))
    contexts = {}
    csv.field_size_limit(16 * 1024 * 1024)
    with zipfile.ZipFile(raw_archive) as bundle:
        member = next(i for i in bundle.infolist() if i.filename.endswith(".tsv"))
        with bundle.open(member) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            for row in reader:
                line = str(reader.line_num)
                if line in by_line:
                    if any(row[key] != by_line[line][key] for key in observations[0]
                           if key not in ["source_tsv_line", "metadata_complete_single_chain", "evidence_status"]):
                        raise ValueError(f"Observation differs from actual source line {line}")
                    contexts[line] = {key: value for key, value in row.items()
                        if key is not None and (key in ["Target Name", "Target Name Assigned by Curator or DataSource",
                            "Target Source Organism According to Curator or DataSource", "Ligand InChI", "Ligand InChI Key",
                            "pH", "Temp (C)", "Curation/DataSource", "BindingDB Entry DOI"]
                            or ("Target Chain 1" in key and "UniProt" in key))}
    if set(contexts) != set(by_line):
        raise ValueError("Raw source identity context coverage differs")
    for item in joined:
        item["raw_identity_context"] = contexts[item["source_tsv_line"]]
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / "assay_evidence_pending.json", joined)
    save(args.output / "repeated_pair_measurements.json", differing)
    save(args.output / "duplicate_reaction_ids.json", duplicate_ids)
    source_rows = []
    for pmid in manifest["requested_pmids"]:
        record = by_pmid[pmid]
        rows = [r for r in joined if r["PMID"].strip() == pmid]
        source_rows.append({"pmid": pmid, "doi": record.get("doi", ""), "pmcid": record.get("pmcid", ""),
                            "title": record.get("title", ""), "isOpenAccess": record.get("isOpenAccess", ""),
                            "measurement_rows": len(rows), "raw_article_dois": sorted({r["Article DOI"] for r in rows}),
                            "review_status": "metadata_identity_only_original_pending"})
    save(args.output / "source_review_pending.json", source_rows)
    requests = [{"filename": row["pmid"] + ".xml", "url":
                 "https://www.ebi.ac.uk/europepmc/webservices/rest/" + urllib.parse.quote(row["pmcid"]) + "/fullTextXML",
                 "role": "official_original_fulltext_candidate", "pmid": row["pmid"], "doi": row["doi"],
                 "license_note": "Metadata OA only; inspect actual article identity/license and assay attribution before approval"}
                for row in source_rows if row["isOpenAccess"] == "Y" and row["pmcid"]]
    save(args.output / "open_original_requests.json", requests)
    after = {path: sha256(ROOT / path) for path in PROTECTED}
    checks = {"old_files_unchanged": before == after, "all_exact_observations_covered": len(joined) == len(by_line) == len(observations),
              "raw_identity_context_covered": set(contexts) == set(by_line), "pmid_metadata_complete": set(by_pmid) == set(manifest["requested_pmids"])}
    summary = {"generated_at": utc_now(), "scope": "Database assay joins and metadata checks; no primary evidence release",
               "counts": dict(stats), "pmid_sources": len(source_rows), "open_original_requests": len(requests),
               "observations_released": 0, "model_fit_calls": 0, "inputs": inputs,
               "producer_sha256": sha256(Path(__file__)), "checks": checks}
    save(args.output / "summary.json", summary)
    report = f"""# DTI Kd 测定关联审计

本轮关联全部 {stats['total_observations']} 条精确 Kd 观察，官方两个 ZIP 的 MD5 校验通过。

- 有完整关联及非空测定描述：{stats['assay_link_complete']}。
- 缺少 reaction→assay 关联：{stats['mapping_missing']}；描述缺失：{stats['description_missing_or_blank']}；一对多关联：{stats['multiple_assay_keys']}。
- 数据库原始 Article DOI 与 PMID 元数据 DOI 一致：{stats['metadata_doi_matches']} 条；不一致：{stats['doi_disagrees_with_metadata']} 条；缺少原始 DOI 但 PMID 元数据存在：{stats['pmid_metadata_available_raw_doi_missing']} 条。
- 同一原始配体 ID/首链序列对有多个精确值的组：{len(differing)}。未按最强值、平均值或模型表现合并；差异需结合实验条件判断，不自动断定冲突。
- 原始文件有 {len(duplicate_ids)} 个重复 Reaction Set ID 组；首次唯一 ID 假设检查拒绝继续。现按原始 TSV 行号保留全部观察，不丢弃重复，也不将其声称为独立重复实验。
- 已取得全部 {len(source_rows)} 个 PMID 的元数据，生成 {len(requests)} 篇开放原文请求。元数据和 assay 描述不代替原始测量论文。

保存目标原始名称、物种、UniProt 映射及 InChI 上下文，尚未批准实际构建体、分子结构或测量端点。新准入观察 0、新训练 0、隔离未计算。下一步取得原文并逐项复核；非开放来源仍待合法公开副本或人工资料。
"""
    with (args.output / "report.md").open("x", encoding="utf-8") as stream:
        stream.write(report)
    save(args.output / "state.json", {"generated_at": utc_now(), "research_direction": "DTI", "endpoint": "Kd",
          "status": "assay_links_audited_primary_review_pending", "training_ready": False,
          "observations_released": 0, "model_fit_calls": 0, "split_audit": "not_computed",
          "protocol_status": "not_frozen", "predecessor": str(state_path.resolve()),
          "summary_sha256": sha256(args.output / "summary.json"),
          "outputs": {p.name: sha256(p) for p in args.output.iterdir() if p.is_file()}})
    if not all(checks.values()):
        raise ValueError("Artifact coverage/protection check failed")
    print(json.dumps({"counts": dict(stats), "sources": len(source_rows), "open_originals": len(requests), "checks": checks}))


if __name__ == "__main__":
    main()
