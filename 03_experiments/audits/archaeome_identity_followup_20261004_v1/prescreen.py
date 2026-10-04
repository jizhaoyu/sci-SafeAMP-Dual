"""All-member sequence prescreen; does not map assay IDs, release labels, or train."""
import csv
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
sys.path.insert(0, str(PROJECT / '02_code'))
from research_data import sequence_identity

def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

outputs = ['sequence_pair_prescreen.csv', 'sequence_prescreen_summary.csv', 'prescreen.json']
if any((ROOT / name).exists() for name in outputs):
    raise FileExistsError('Prescreen outputs already exist')
certificate_path = PROJECT / '03_experiments/audits/mic_priority_primary_review_20261004_v1/molecule_identity_review.csv'
development_path = PROJECT / '03_experiments/prepared/amd02_evidence_clean_20261001/records.csv'
mic_path = PROJECT / '03_experiments/audits/mic_followup_release_20261004_v1/cohort/candidate_molecules.csv'
certificates = read_csv(certificate_path)
development = read_csv(development_path)
mic = read_csv(mic_path)
assert len(certificates) == 80 and len(development) == 417 and len(mic) == 16
canonical = set('ACDEFGHIKLMNPQRSTVWY')
assert all(row['sequence_verbatim'] and set(row['sequence_verbatim']) <= canonical for row in certificates)
references = [('formal_development_417', row['record_id'], row['seq']) for row in development]
references += [('mic_development_16', row['sample_id'], row['seq']) for row in mic]
fields = ['certificate_name', 'reference_cohort', 'reference_id', 'identity_alignment', 'violates_cutoff']
summaries = []
pair_count = 0
with (ROOT / outputs[0]).open('x', encoding='utf-8', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for index, certificate in enumerate(certificates, 1):
        stats = {name: {'max_identity': -1, 'closest_reference_id': '', 'violating_pairs': 0}
                 for name in ['formal_development_417', 'mic_development_16']}
        for cohort, reference_id, seq in references:
            identity = sequence_identity(certificate['sequence_verbatim'], seq, identity_mode='alignment')
            violates = identity >= 0.40
            writer.writerow(dict(zip(fields, [certificate['peptide_name'], cohort, reference_id, identity, violates])))
            pair_count += 1
            stat = stats[cohort]
            stat['violating_pairs'] += int(violates)
            if identity > stat['max_identity']:
                stat.update(max_identity=identity, closest_reference_id=reference_id)
        for cohort, stat in stats.items():
            summaries.append({'certificate_name': certificate['peptide_name'], 'reference_cohort': cohort,
                              **stat, 'measurement_id': '', 'admitted': False,
                              'evidence_status': 'pending_assay_id_mapping_and_terminal_form'})
        if index % 20 == 0:
            print(f'Compared {index}/80 certificate sequences against all 433 reference rows.', flush=True)
assert pair_count == 80 * (417 + 16)
with (ROOT / outputs[1]).open('x', encoding='utf-8', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
    writer.writeheader()
    writer.writerows(summaries)
counts = {}
for cohort in ['formal_development_417', 'mic_development_16']:
    rows = [row for row in summaries if row['reference_cohort'] == cohort]
    counts[cohort] = {'sequences_with_conflict': sum(row['violating_pairs'] > 0 for row in rows),
                      'sequences_without_conflict': sum(row['violating_pairs'] == 0 for row in rows),
                      'violating_pairs': sum(row['violating_pairs'] for row in rows)}
result = {'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'status': 'sequence_prescreen_only', 'candidate_sequences': 80,
          'pairs': pair_count, 'identity_mode': 'alignment', 'cutoff': 0.40,
          'alignment': {'algorithm': 'global Needleman-Wunsch', 'match': 2, 'mismatch': -1,
                        'gap': -2, 'tie_order': ['diagonal', 'up', 'left'],
                        'orientation': 'canonical lexicographic', 'denominator': 'alignment columns'},
          'counts': counts, 'new_molecules_admitted': 0, 'training_executed': False,
          'limitations': ['No assay-to-certificate mapping or terminal identity approval',
                         'This is not a complete source-alias or candidate-internal isolation audit'],
          'inputs': {str(path.relative_to(PROJECT)): digest(path)
                     for path in [certificate_path, development_path, mic_path, PROJECT / '02_code/research_data.py']},
          'outputs': {name: digest(ROOT / name) for name in outputs[:2]}}
with (ROOT / outputs[2]).open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result['counts'], indent=2), flush=True)
