"""Acquire explicit public source requests into an immutable directory."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from acquire_half_lysis_primary_copies import acquire
from research_utils import sha256, utc_now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    requests = json.loads(args.requests.read_text(encoding="utf-8"))
    names = [row["filename"] for row in requests]
    if len(set(names)) != len(names) or any(Path(name).name != name or "/" in name or "\\" in name for name in names):
        raise ValueError("Source filenames must be distinct basenames")
    args.output.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(lambda item: acquire(item, args.output), requests))
    manifest = {"generated_at": utc_now(), "scope": "Explicit public-source acquisition; identity, assay and license review pending",
                "inputs": {str(args.requests.resolve()): sha256(args.requests)},
                "producer_sha256": sha256(Path(__file__)),
                "helper_sha256": sha256(Path(__file__).with_name("acquire_half_lysis_primary_copies.py")),
                "records": records, "labels_released": 0, "model_fit_calls": 0}
    with (args.output / "acquisition_manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps([{key: row.get(key) for key in ("filename", "status", "error")} for row in records]))


if __name__ == "__main__":
    main()
