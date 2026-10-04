"""Create a MIC-only source subset by enforcing the frozen target-ID evidence gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from research_utils import ROOT, sha256, utc_now, write_json


def curate(records_path: Path, audit_path: Path, output: Path) -> dict:
    records_path, audit_path, output = map(Path, (records_path, audit_path, output))
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing source directory: {output}")
    records = pd.read_csv(records_path)
    targets = pd.read_csv(audit_path)
    if records.record_id.isna().any() or records.record_id.duplicated().any():
        raise ValueError("Source record IDs must be present and unique.")
    if not {"record_id", "strain_identifier_status"}.issubset(targets.columns):
        raise ValueError("Target audit lacks required columns.")
    labeled = records[records.amp.notna()].copy()
    if not labeled.amp.isin([0, 1]).all():
        raise ValueError("MIC labels must be binary or blank in the source.")
    target_ids = set(targets.record_id.astype(str))
    labeled_ids = set(labeled.record_id.astype(str))
    extra_ids = target_ids - labeled_ids
    extra_rows = targets[targets.record_id.isin(extra_ids)]
    if labeled_ids - target_ids or not extra_rows.source_dataset.eq("DRAMP").all():
        raise ValueError(f"Target audit/source mismatch: missing={len(labeled_ids - target_ids)}, unexpected extra={len(extra_rows[~extra_rows.source_dataset.eq('DRAMP')])}")
    unexpected = set(targets.strain_identifier_status) - {"identified_provisionally", "unresolved_strain_or_isolate"}
    if unexpected:
        raise ValueError(f"Unexpected target audit decisions: {sorted(unexpected)}")
    unresolved = set(targets.loc[targets.strain_identifier_status.eq("unresolved_strain_or_isolate") & targets.record_id.isin(labeled_ids), "record_id"])
    retained = labeled[~labeled.record_id.isin(unresolved)].copy()
    if retained.empty or set(retained.amp.astype(int)) != {0, 1}:
        raise ValueError("Evidence-qualified records must retain both MIC classes.")
    exclusions = records.loc[~records.record_id.isin(retained.record_id), ["record_id", "seq", "amp"]].copy()
    exclusions["reason"] = exclusions.record_id.map(
        lambda record_id: "unresolved_target_identifier" if record_id in unresolved else "no_binary_mic_label"
    )
    if set(retained.record_id) & set(exclusions.record_id) or len(retained) + len(exclusions) != len(records):
        raise ValueError("Curated records and exclusions do not partition the source.")
    output.mkdir(parents=True)
    retained.to_csv(output / "records.csv", index=False, encoding="utf-8-sig")
    exclusions.to_csv(output / "exclusions.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "status": "evidence_screened_subset_pending_full_cohort_audit",
        "generated_at": utc_now(),
        "protocol_id": "protocol-mic-01",
        "source_records": str(records_path.resolve().relative_to(ROOT)),
        "source_sha256": sha256(records_path),
        "target_audit": str(audit_path.resolve().relative_to(ROOT)),
        "target_audit_sha256": sha256(audit_path),
        "script_sha256": sha256(Path(__file__)),
        "source_count": len(records),
        "retained_count": len(retained),
        "excluded_unresolved_target_count": len(unresolved),
        "excluded_no_binary_mic_count": int(records.amp.isna().sum()),
        "label_counts": {str(int(label)): int(count) for label, count in retained.amp.value_counts().sort_index().items()},
        "retained_records_sha256": sha256(output / "records.csv"),
        "exclusions_sha256": sha256(output / "exclusions.csv"),
        "training_started": False,
        "outputs": {"records": str((output / "records.csv").resolve().relative_to(ROOT)),
                    "exclusions": str((output / "exclusions.csv").resolve().relative_to(ROOT))},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--target-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(curate(args.records, args.target_audit, args.output), ensure_ascii=False, indent=2))
