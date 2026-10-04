"""Retain completed acquisition artifacts, a stalled-request record, and audit hashes."""
import csv
import datetime
import hashlib
import json
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
target = ROOT / 'manifest.json'
if target.exists():
    raise FileExistsError(target)
protected_path = PROJECT / '03_experiments/audits/mic_training_readiness_20261004_v22.json'
expected = '67fcb7ce81a3957ba468084b6b7e24732fe4e761476e0dbfd6b22655fb42aab1'
assert hashlib.sha256(protected_path.read_bytes()).hexdigest() == expected
base = 'https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41564-025-02061-0/MediaObjects/'
acquisition = []
for filename in ['41564_2025_2061_MOESM1_ESM.pdf', '41564_2025_2061_MOESM17_ESM.xlsx']:
    path = ROOT / 'raw' / filename
    data = path.read_bytes()
    valid = data.startswith(b'%PDF-') if filename.endswith('.pdf') else zipfile.is_zipfile(path)
    acquisition.append({'url': base + filename, 'path': str(path.relative_to(ROOT)),
                        'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                        'file_last_written_at': datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc).isoformat(),
                        'acquisition_verified_at': now,
                        'status': 'valid_document' if valid else 'rejected_html_response'})
acquisition.append({'url': 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12408343/supplementaryFiles',
                    'status': 'client_stopped_stalled_acquisition', 'recorded_at': now,
                    'reason': 'Request still running after more than six minutes; only its identified local process was stopped',
                    'server_failure_claimed': False, 'complete_file_received': False})
with (ROOT / 'acquisition_recovery.json').open('x', encoding='utf-8') as stream:
    json.dump(acquisition, stream, indent=2)
prescreen = json.loads((ROOT / 'prescreen.json').read_text(encoding='utf-8'))
with (ROOT / 'sequence_pair_prescreen.csv').open(encoding='utf-8', newline='') as stream:
    count = sum(1 for _ in csv.DictReader(stream))
assert count == 34640 == prescreen['pairs']
assert prescreen['new_molecules_admitted'] == 0
files = {str(path.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
         for path in sorted(ROOT.rglob('*')) if path.is_file() and path != target}
with target.open('x', encoding='utf-8') as stream:
    json.dump({'generated_at': now, 'artifact_version': ROOT.name,
               'review_mode': 'agent_primary_source_review',
               'new_molecules_admitted': 0, 'training_executed': False,
               'formal_dual_task_status': 'blocked', 'current_mic_training_blocked': False,
               'current_state_source': str(protected_path.relative_to(PROJECT)),
               'current_state_sha256': expected, 'protected_state_hash_verified': True,
               'prescreen_counts': prescreen['counts'], 'all_member_pairs_verified': count,
               'scientific_blockers': ['Assay ID to certificate mapping unresolved',
                                       'Explicit terminal forms unresolved',
                                       'Extended Data Fig. 7 raw dose responses not obtained'],
               'author_request_sent': False, 'files': files}, stream, indent=2)
print(f'Manifest saved: {len(files)} artifacts, {count} verified comparison rows, 0 admissions. Protected state unchanged.')
