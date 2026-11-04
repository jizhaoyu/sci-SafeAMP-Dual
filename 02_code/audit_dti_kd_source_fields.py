"""Review the acquired BindingDB schema; preserve failed preflight artifacts."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from dti_source_preflight import PROTECTED, kd_kind, save
from research_utils import ROOT, sha256, utc_now


FIELDS = ["BindingDB Reactant_set_id", "Ligand SMILES", "BindingDB MonomerID", "Kd (nM)",
          "Article DOI", "PMID", "BindingDB Target Chain Sequence 1",
          "Number of Protein Chains in Target (>1 implies a multichain complex)"]


def run(acquisition, output):
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads((acquisition / "acquisition_manifest.json").read_text(encoding="utf-8"))
    original_producer = Path(__file__).with_name("dti_source_preflight.py")
    if sha256(original_producer) != manifest["producer_sha256"]:
        raise ValueError("Acquisition producer changed")
    inputs = {str(original_producer.resolve()): sha256(original_producer),
              str((acquisition / "acquisition_manifest.json").resolve()): sha256(acquisition / "acquisition_manifest.json")}
    for record in manifest["records"]:
        if "sha256" in record:
            path = acquisition / record["filename"]
            if sha256(path) != record["sha256"]:
                raise ValueError(f"Acquired file changed: {path}")
            inputs[str(path.resolve())] = record["sha256"]
    before = {p: sha256(ROOT / p) for p in PROTECTED}
    predecessor = json.loads((acquisition / "protected_inputs.json").read_text(encoding="utf-8"))
    if before != predecessor:
        raise ValueError("Historical files differ from acquisition snapshot")
    for name in ["state.json", "verification.json", "protected_inputs.json"]:
        inputs[str((acquisition / name).resolve())] = sha256(acquisition / name)
    archive = acquisition / "BindingDB_BindingDB_Articles_202610_tsv.zip"
    expected = (acquisition / "bindingdb_articles.md5").read_text(encoding="utf-8").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{32}", expected) or hashlib.md5(archive.read_bytes()).hexdigest() != expected:
        raise ValueError("Official ZIP MD5 failed")
    counts = Counter({k: 0 for k in ["all_measurement_rows", "missing", "exact_positive_numeric",
                     "non_exact_comparator_unapproved", "non_numeric_or_interval", "invalid_numeric"]})
    coverage, ligands, sequences, doi_strings = Counter(), set(), set(), set()
    studies = defaultdict(lambda: {"rows": 0, "single_chain_complete_fields": 0, "pmids": set()})
    output.mkdir(parents=True, exist_ok=False)
    csv.field_size_limit(16 * 1024 * 1024)
    with zipfile.ZipFile(archive) as bundle:
        members = [n for n in bundle.infolist() if not n.is_dir() and n.filename.endswith(".tsv")]
        if len(members) != 1 or members[0].file_size > 512 * 1024 * 1024:
            raise ValueError("Expected one bounded source TSV")
        with bundle.open(members[0]) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream, \
                (output / "kd_exact_observations.csv").open("x", encoding="utf-8", newline="") as destination:
            reader = csv.DictReader(stream, delimiter="\t")
            columns = reader.fieldnames or []
            if len(set(columns)) != len(columns) or set(FIELDS) - set(columns):
                raise ValueError("Unexpected or ambiguous source header")
            save(output / "columns.json", columns)
            writer = csv.DictWriter(destination, fieldnames=FIELDS + ["source_tsv_line", "metadata_complete_single_chain", "evidence_status"])
            writer.writeheader()
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"Malformed source row {reader.line_num}")
                counts["all_measurement_rows"] += 1
                kind = kd_kind(row["Kd (nM)"])
                counts[kind] += 1
                if kind != "exact_positive_numeric":
                    continue
                ligand, smiles = row["BindingDB MonomerID"].strip(), row["Ligand SMILES"].strip()
                sequence = row["BindingDB Target Chain Sequence 1"].strip()
                doi, pmid = row["Article DOI"].strip(), row["PMID"].strip()
                one_chain = row[FIELDS[7]].strip() == "1"
                complete = bool(ligand and smiles and sequence and (doi or pmid) and one_chain)
                for key, value in [("ligand_id_present", ligand), ("smiles_present", smiles),
                                   ("first_chain_sequence_present", sequence), ("article_doi_present", doi),
                                   ("pmid_present", pmid), ("article_doi_or_pmid_present", doi or pmid),
                                   ("single_chain_declared", one_chain), ("complete_metadata_single_chain", complete)]:
                    coverage[key] += bool(value)
                if ligand:
                    ligands.add(ligand)
                if sequence:
                    sequences.add(sequence)
                if doi:
                    doi_strings.add(doi)
                source_key = "doi:" + doi if doi else ("pmid:" + pmid if pmid else "missing_source")
                studies[source_key]["rows"] += 1
                studies[source_key]["single_chain_complete_fields"] += complete
                if pmid:
                    studies[source_key]["pmids"].add(pmid)
                writer.writerow({**{k: row[k] for k in FIELDS}, "source_tsv_line": reader.line_num,
                                 "metadata_complete_single_chain": complete,
                                 "evidence_status": "database_fields_only_not_released"})
    save(output / "study_inventory.json", {key: {**value, "pmids": sorted(value["pmids"])}
                                           for key, value in sorted(studies.items())})
    result = {"generated_at": utc_now(), "scope": "All source TSV rows; database fields only, not primary-approved cohort",
              "official_archive_md5_matches": True, "archive_sha256": sha256(archive),
              "source_member": members[0].filename, "source_column_count": len(columns),
              "sequence_field": "BindingDB Target Chain Sequence 1", "counts": dict(counts),
              "exact_kd_field_coverage": dict(coverage), "unique_raw_ligand_ids": len(ligands),
              "unique_first_chain_sequences": len(sequences), "unique_raw_article_doi_strings": len(doi_strings),
              "structure_standardized": False, "protein_constructs_verified": False,
              "study_aliases_resolved": False, "independence_audited": False, "observations_released": 0}
    save(output / "inventory.json", result)
    after = {p: sha256(ROOT / p) for p in PROTECTED}
    checks = {"official_archive_md5_matches": True, "measurement_count_conserved":
              counts["all_measurement_rows"] == sum(v for k, v in counts.items() if k != "all_measurement_rows"),
              "exact_count_matches_source_groups": counts["exact_positive_numeric"] == sum(s["rows"] for s in studies.values()),
              "historical_files_unchanged": before == after}
    save(output / "verification.json", {"generated_at": utc_now(), "passed": all(checks.values()),
         "checks": checks, "scope": "File binding, counts and historical protection; not evidence release or model validation",
         "before": before, "after": after})
    report = f"""# DTI Kd 首轮字段审计

本轮遍历 BindingDB 官方 202610 文章子集的全部 {counts['all_measurement_rows']:,} 行测量。ZIP 官方 MD5 和本地 SHA256 均检查。取得文件包含 {len(columns)} 列，实际首链字段为 `BindingDB Target Chain Sequence 1`。

| 分类 | 测量行数 |
|---|---:|
| 正数精确 Kd 字段 | {counts['exact_positive_numeric']:,} |
| 有非精确比较符 | {counts['non_exact_comparator_unapproved']:,} |
| 非数值/区间 | {counts['non_numeric_or_interval']:,} |
| 非法数值 | {counts['invalid_numeric']:,} |
| 无 Kd 字段 | {counts['missing']:,} |

精确 Kd 中，单链声明且配体 ID、SMILES、首链序列和论文标识均存在的行数为 {coverage['complete_metadata_single_chain']:,}。全部精确 Kd 包含 {len(ligands):,} 个原始配体 ID、{len(sequences):,} 条不同首链序列、{len(doi_strings):,} 个不同原始 Article DOI 字符串。这些不是标准化后的独立分子、已核实构建体或已合并测量研究数量。

## 实际限制

- 第一版预审因预期列名缺少后缀 `1` 而失败，失败状态及原生产脚本保留；本版只读取已取得的文件，未重新下载或覆盖前版。
- 本地 DAVIS 落地页为 JavaScript/访问挑战页，不是实验全文；尚未取得原始补充表。官方原论文目录说明空白可能是弱结合或初筛未检出，不能填成精确 Kd。
- BindingDB 长期归档浏览器访问被拒绝；当前月版只作为可行性输入，不声称取得推荐的长期归档版本。
- 单链字段完整只提供原文审查入口。实际配体结构、立体化学、蛋白突变/构建体、端点和测量条件均未逐记录批准。
- 研究别名、同源、药物结构相似性及跨队列来源隔离均未计算。不能宣称数据独立或可训练。

## 下一步

取得官方 assay 描述关联表，按实际 Article DOI/PMID 核对原测定和分子身份，再预审隔离组件及新协议。新增准入观察 0、新训练 0。旧六份关键文件前后摘要检查结果：{before == after}。
"""
    with (output / "report.md").open("x", encoding="utf-8") as stream:
        stream.write(report)
    state = {"generated_at": utc_now(), "research_direction": "DTI", "endpoint": "Kd",
             "status": "source_inventory_complete_evidence_review_pending", "training_ready": False,
             "protocol_status": "not_frozen", "observations_released": 0, "model_fit_calls": 0,
             "split_audit": "not_computed", "predecessor": str((acquisition / "state.json").resolve()),
             "inputs": inputs, "producer_sha256": sha256(Path(__file__)),
             "outputs": {p.name: sha256(p) for p in output.iterdir() if p.is_file()}}
    save(output / "state.json", state)
    if not all(checks.values()):
        raise ValueError("Audit verification failed; this output does not authorize progression")
    return {"status": state["status"], "counts": dict(counts), "metadata_complete_single_chain":
            coverage["complete_metadata_single_chain"], "checks_passed": all(checks.values()), "training_ready": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.acquisition, args.output)))


if __name__ == "__main__":
    main()
