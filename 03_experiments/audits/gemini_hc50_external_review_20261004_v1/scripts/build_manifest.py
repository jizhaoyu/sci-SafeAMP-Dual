"""
Generate manifest.json recording SHA256 digests for all files in the delivery package.
"""
import os
import json
import hashlib
from pathlib import Path
import datetime

REPO_ROOT = Path("D:/桌面文件/sci").resolve()
AUDIT_DIR = REPO_ROOT / "03_experiments/audits/gemini_hc50_external_review_20261004_v1"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

manifest = {
    "audit_version": "gemini_hc50_external_review_20261004_v1",
    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "protocol_id": "protocol-amd-02",
    "audit_protocol_id": "protocol-amd-03",
    "status": "blocked",
    "inputs": {
        "records_csv": {
            "path": "03_experiments/prepared/amd02_evidence_clean_20261001/records.csv",
            "sha256": sha256_file(REPO_ROOT / "03_experiments/prepared/amd02_evidence_clean_20261001/records.csv")
        },
        "candidate_primary_audit_csv": {
            "path": "03_experiments/audits/dramp_dual_task_primary_audit_20261003_v1/candidate_primary_audit.csv",
            "sha256": sha256_file(REPO_ROOT / "03_experiments/audits/dramp_dual_task_primary_audit_20261003_v1/candidate_primary_audit.csv")
        },
        "mic_goat_cohort_csv": {
            "path": "03_experiments/audits/mic_goat_followup_release_20261004_v1/cohort/candidate_molecules.csv",
            "sha256": sha256_file(REPO_ROOT / "03_experiments/audits/mic_goat_followup_release_20261004_v1/cohort/candidate_molecules.csv")
        }
    },
    "scripts": {},
    "raw_files": {},
    "outputs": {}
}

for s_path in (AUDIT_DIR / "scripts").glob("*.py"):
    manifest["scripts"][s_path.name] = {
        "path": str(s_path.relative_to(REPO_ROOT)),
        "sha256": sha256_file(s_path)
    }

for r_path in (AUDIT_DIR / "raw").glob("*.*"):
    manifest["raw_files"][r_path.name] = {
        "path": str(r_path.relative_to(REPO_ROOT)),
        "sha256": sha256_file(r_path)
    }

for o_path in AUDIT_DIR.glob("*.csv"):
    manifest["outputs"][o_path.name] = {
        "path": str(o_path.relative_to(REPO_ROOT)),
        "sha256": sha256_file(o_path)
    }

for o_path in AUDIT_DIR.glob("*.json"):
    if o_path.name != "manifest.json":
        manifest["outputs"][o_path.name] = {
            "path": str(o_path.relative_to(REPO_ROOT)),
            "sha256": sha256_file(o_path)
        }

manifest_file = AUDIT_DIR / "manifest.json"
with open(manifest_file, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print(f"manifest.json written ({len(manifest['outputs'])} outputs, {len(manifest['raw_files'])} raw, {len(manifest['scripts'])} scripts).")
