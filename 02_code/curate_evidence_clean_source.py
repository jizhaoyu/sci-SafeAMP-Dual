"""Create an immutable candidate source without unsupported external labels."""
import argparse
from pathlib import Path

import pandas as pd

from evidence_validation import validate_source_evidence
from research_data import ResearchDataError, validate_records
from research_utils import sha256, utc_now, write_json


def curate_evidence_clean_source(records_path: Path, output_dir: Path) -> dict:
    records_path, output_dir = Path(records_path), Path(output_dir)
    if output_dir.exists():
        raise ValueError('Output exists; use a new versioned source directory.')
    records = validate_records(pd.read_csv(records_path), verify_raw=False)
    try:
        validate_source_evidence(records)
        failures = []
    except ResearchDataError as exc:
        if not exc.evidence_audit:
            raise
        failures = exc.evidence_audit['failures']

    failed_ids = {failure['record_id'] for failure in failures}
    if any(record_id.startswith('RAW_FILE:') for record_id in failed_ids):
        raise ResearchDataError('Raw source integrity failure cannot be repaired by excluding records.')
    if any(records.set_index('record_id').loc[record_id, 'source_role'] != 'external' for record_id in failed_ids):
        raise ResearchDataError('Development evidence failure requires source review, not automatic exclusion.')

    accepted = records[~records.record_id.isin(failed_ids)].copy()
    accepted_audit = validate_source_evidence(accepted)
    output_dir.mkdir(parents=True)
    accepted.to_csv(output_dir / 'records.csv', index=False)
    write_json(output_dir / 'exclusions.json', failures)
    write_json(output_dir / 'evidence_audit.json', accepted_audit)
    manifest = {
        'status': 'candidate' if accepted.source_role.eq('external').any() else 'blocked_no_external_cohort',
        'created_at': utc_now(),
        'input_records': str(records_path.resolve()),
        'input_records_sha256': sha256(records_path),
        'records_sha256': sha256(output_dir / 'records.csv'),
        'exclusions_sha256': sha256(output_dir / 'exclusions.json'),
        'evidence_audit_sha256': sha256(output_dir / 'evidence_audit.json'),
        'development_records': int(accepted.source_role.eq('development').sum()),
        'external_records': int(accepted.source_role.eq('external').sum()),
        'excluded_unsupported_external_records': len(failures),
    }
    write_json(output_dir / 'source_manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(curate_evidence_clean_source(args.records, args.output))
