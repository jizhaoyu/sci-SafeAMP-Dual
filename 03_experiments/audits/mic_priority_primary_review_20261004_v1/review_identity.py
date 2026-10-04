"""Build per-certificate pending decisions; do not infer terminal or assay IDs."""
import csv
import datetime
import hashlib
import json
import pathlib
import re
import zipfile

root = pathlib.Path(__file__).resolve().parent
output = root / 'molecule_identity_review.csv'
if output.exists():
    raise FileExistsError(output)
records = json.loads((root / 'coa_text.json').read_text(encoding='utf-8'))['records']
rows = []
for record in records:
    text = record['pages'][0]
    name = re.search(r'Peptide Name:\s*([^\n]+)', text)
    sequence = re.search(r'Peptide Sequence:\s*([^\n]+)', text)
    mass = re.search(r'Molecular Weight \(Theoretical\):\s*([\d.]+)', text)
    rows.append({'certificate_member': record['archive_member'], 'certificate_sha256': record['sha256'],
                 'certificate_page': 1, 'peptide_name': name.group(1).strip() if name else '',
                 'sequence_verbatim': sequence.group(1).strip() if sequence else '',
                 'theoretical_molecular_weight_verbatim': mass.group(1) if mass else '',
                 'measurement_id': '', 'terminal_form': '', 'label': '',
                 'decision': 'pending',
                 'reason': 'No explicit Archaeasin assay-ID mapping or terminal specification in certificate',
                 'review_mode': 'agent_primary_source_review'})
with output.open('x', encoding='utf-8', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
assert len(rows) == 80
assert all(row['sequence_verbatim'] for row in rows)
assert len({row['peptide_name'] for row in rows}) == 80
with zipfile.ZipFile(root / 'raw/COA_archaeasins.zip') as archive:
    member = records[0]['archive_member']
    with (root / 'raw/example_certificate.pdf').open('xb') as handle:
        handle.write(archive.read(member))
summary = {'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'certificates': 80, 'unique_certificate_names': 80, 'sequences_extracted': 80,
           'explicit_assay_id_mapping_in_certificates': 0,
           'admitted_molecules': 0, 'homology_audit_status': 'not_run_pending_identity_and_mapping',
           'decisions_sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
with (root / 'identity_review_summary.json').open('x', encoding='utf-8') as handle:
    json.dump(summary, handle, indent=2)
print(json.dumps(summary, indent=2))
