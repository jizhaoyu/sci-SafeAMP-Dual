"""Validate coverage and protected inputs, then write an immutable artifact manifest."""
import csv
import datetime
import hashlib
import json
import pathlib

root = pathlib.Path(__file__).resolve().parent
workspace = root.parents[2]
target = root / 'manifest.json'
if target.exists():
    raise FileExistsError(target)
protected = {
    '03_experiments/audits/mic_training_readiness_20261004_v22.json':
        '67fcb7ce81a3957ba468084b6b7e24732fe4e761476e0dbfd6b22655fb42aab1',
    '03_experiments/prepared/amd02_evidence_clean_20261001/records.csv':
        'ccec346bf88c6d3b2da57f058019fb10305019de5dca4ef3402949931ac71f37',
}
for relative, expected in protected.items():
    actual = hashlib.sha256((workspace / relative).read_bytes()).hexdigest()
    assert actual == expected, (relative, actual)
with (root / 'molecule_identity_review.csv').open(encoding='utf-8', newline='') as handle:
    coa_rows = list(csv.DictReader(handle))
with (root / 'foundation_molecule_review.csv').open(encoding='utf-8', newline='') as handle:
    foundation_rows = list(csv.DictReader(handle))
assert len(coa_rows) == 80 and all(row['decision'] == 'pending' and not row['label'] for row in coa_rows)
assert len(foundation_rows) == 23 and all(row['terminal_form'] == 'C-terminal amide' and not row['label'] for row in foundation_rows)
files = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
         for path in sorted(root.rglob('*')) if path.is_file() and path != target}
manifest = {'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'artifact_version': root.name, 'review_mode': 'agent_primary_source_review',
            'new_molecules_admitted': 0, 'new_labels_released': 0,
            'coa_pending': 80, 'foundation_excluded_current_mic_domain': 23,
            'formal_dual_task_status': 'blocked', 'new_training_executed': False,
            'homology_audit': 'not_run_pending_molecule_identity_and_assay_mapping',
            'protected_inputs': protected, 'protected_input_hashes_verified': True,
            'current_state_source': '03_experiments/audits/mic_training_readiness_20261004_v22.json',
            'current_mic_training_blocked': False, 'files': files}
with target.open('x', encoding='utf-8') as handle:
    json.dump(manifest, handle, indent=2)
print(json.dumps({key: value for key, value in manifest.items() if key not in ['files', 'protected_inputs']}, indent=2))
print(f'Hashed {len(files)} artifacts. Coverage and protected input checks passed.')
