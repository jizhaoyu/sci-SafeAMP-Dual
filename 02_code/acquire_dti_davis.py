"""Acquire official DAVIS benchmark dataset from Harvard Dataverse."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

from audit_dti_assay_links import bind
from dti_source_preflight import PROTECTED, save
from research_utils import ROOT, sha256, utc_now


DAVIS_ORIGINAL_URL = "https://dataverse.harvard.edu/api/access/datafile/5219748?format=original"
EXPECTED_MD5 = "6c7949b81aea69e9d816db88602d771e"
EXPECTED_FILE_NAME = "davis.csv"
EXPECTED_BYTES = 21222080


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--predecessor", type=Path, default=ROOT / "03_experiments/audits/dti_primary_batch_review_20261006_v2")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)

    inputs = {}
    if args.predecessor and args.predecessor.exists():
        state_path = args.predecessor / "state.json"
        if state_path.exists():
            bind(state_path, inputs)
            state_data = json.loads(state_path.read_text(encoding="utf-8"))
            for name, expected in state_data.get("outputs", {}).items():
                p = args.predecessor / name
                if p.exists():
                    bind(p, inputs, expected)

    before = {p: sha256(ROOT / p) for p in PROTECTED}

    args.output.mkdir(parents=True, exist_ok=False)
    target_file = args.output / EXPECTED_FILE_NAME

    print(f"Downloading {EXPECTED_FILE_NAME} from Harvard Dataverse: {DAVIS_ORIGINAL_URL}...")
    req = urllib.request.Request(DAVIS_ORIGINAL_URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        content = resp.read()
        target_file.write_bytes(content)

    observed_bytes = len(content)
    observed_md5 = hashlib.md5(content).hexdigest()
    observed_sha256 = hashlib.sha256(content).hexdigest()

    print(f"Downloaded {observed_bytes} bytes. MD5: {observed_md5}")

    if observed_md5 != EXPECTED_MD5:
        raise ValueError(f"Official MD5 mismatch: observed {observed_md5}, expected {EXPECTED_MD5}")
    if observed_bytes != EXPECTED_BYTES:
        raise ValueError(f"File size mismatch: observed {observed_bytes}, expected {EXPECTED_BYTES}")

    record = {
        "filename": EXPECTED_FILE_NAME,
        "url": DAVIS_ORIGINAL_URL,
        "source_dataverse": "https://doi.org/10.7910/DVN/21LKWG",
        "file_id": 5219748,
        "bytes": observed_bytes,
        "md5": observed_md5,
        "sha256": observed_sha256,
        "official_md5_matches": True,
        "status": "acquired_verified_checksum_match",
        "role": "official_davis_benchmark_original_dti_csv"
    }

    manifest = {
        "generated_at": utc_now(),
        "producer": "02_code/acquire_dti_davis.py",
        "producer_sha256": sha256(Path(__file__)),
        "inputs": inputs,
        "records": [record],
        "training_ready": False,
        "observations_released": 0,
        "model_fit_calls": 0
    }
    save(args.output / "acquisition_manifest.json", manifest)

    after = {p: sha256(ROOT / p) for p in PROTECTED}
    if before != after:
        raise ValueError("Protected files modified during acquisition!")

    report = f"""# DAVIS 基准数据集官方获取与校验报告

* **数据来源：** Harvard Dataverse (Therapeutics Data Commons: [doi:10.7910/DVN/21LKWG](https://doi.org/10.7910/DVN/21LKWG))
* **下载链接：** `{DAVIS_ORIGINAL_URL}` (Datafile ID: 5219748, format=original)
* **文件名：** `{EXPECTED_FILE_NAME}`
* **文件大小：** {observed_bytes:,} 字节
* **官方 MD5 校验：** `{observed_md5}` (**校验通过：与官方 Dataverse 元数据 6c7949b81aea69e9d816db88602d771e 完全匹配**)
* **本地 SHA-256：** `{observed_sha256}`
* **准入说明：** 
  * 首版获取（v1）请求默认端点时取得 Dataverse 自动转换的 TSV 格式（21,376,712 字节，MD5 843c1bde8b468500fc8356de6cb6adb9），因与官方元数据记录的原始文件 MD5 不一致而拒绝准入；失败现场已完整保留在 `dti_davis_acquisition_20261006_v1`。
  * 本版（v2）显式请求原始格式 `?format=original`，取得官方发布的完整原始 CSV 文件，MD5 完全一致。
  * 当前仅完成文件获取与哈希闭环，未进入模型训练，未释放标签。
"""
    with (args.output / "report.md").open("x", encoding="utf-8") as f:
        f.write(report)

    state = {
        "generated_at": utc_now(),
        "research_direction": "DTI",
        "benchmark": "DAVIS",
        "endpoint": "Kd",
        "status": "davis_acquired_checksum_verified_pending_field_and_isolation_audit",
        "training_ready": False,
        "protocol_status": "not_frozen",
        "observations_released": 0,
        "model_fit_calls": 0,
        "predecessor": str((args.predecessor / "state.json").resolve()) if args.predecessor.exists() else None,
        "outputs": {p.name: sha256(p) for p in args.output.iterdir() if p.is_file()}
    }
    save(args.output / "state.json", state)
    print(json.dumps({"status": "success", "file": EXPECTED_FILE_NAME, "md5_matches": True, "bytes": observed_bytes}))


if __name__ == "__main__":
    main()
