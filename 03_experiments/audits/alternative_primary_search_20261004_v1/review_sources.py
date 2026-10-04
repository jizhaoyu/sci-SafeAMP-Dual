"""Extract evidence and overlaps; avoid shadowing the standard library inspect module."""
import csv
import datetime
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
sys.path.insert(0, str(PROJECT / '02_code'))
from research_data import sequence_identity

def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

def text(node):
    return ' '.join(node.itertext()) if node is not None else ''

def write(name, value):
    with (ROOT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True)

if (ROOT / 'source_review.json').exists():
    raise FileExistsError('Review outputs exist')
dev = read_csv(PROJECT / '03_experiments/prepared/amd02_evidence_clean_20261001/records.csv')
mic = read_csv(PROJECT / '03_experiments/audits/mic_followup_release_20261004_v1/cohort/candidate_molecules.csv')
mic_sources = read_csv(PROJECT / '03_experiments/audits/mic_followup_release_20261004_v1/evidence/source_review.csv')
assert len(dev) == 417 and len(mic) == 16
sources = []
evidence = []
for path in sorted((ROOT / 'raw').glob('*.xml')):
    article = ET.parse(path).getroot()
    ids = {node.attrib['pub-id-type']: node.text for node in article.findall('.//article-meta/article-id')}
    tokens = [ids[key].lower() for key in ['doi', 'pmid', 'pmcid'] if ids.get(key)]
    sources.append({'source_id': path.stem, 'identifiers': ids,
                    'title': text(article.find('.//article-title')),
                    'license': [text(node) for node in article.findall('.//license')],
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'formal_exact_identifier_matches': [row['record_id'] for row in dev if any(token in json.dumps(row).lower() for token in tokens)],
                    'mic_exact_identifier_matches': [row for row in mic_sources if any(token in json.dumps(row).lower() for token in tokens)],
                    'source_alias_audit': 'exact_identifier_screen_only', 'admitted': False})
    evidence.append({'source_id': path.stem,
                     'tables': [{'id': node.get('id'), 'text': text(node),
                                 'rows': [[{'text': text(cell), 'rowspan': cell.get('rowspan', '1'),
                                            'colspan': cell.get('colspan', '1')} for cell in row if cell.tag in ['td', 'th']]
                                          for row in node.findall('.//tr')]} for node in article.findall('.//table-wrap')],
                     'sections': [{'id': node.get('id'), 'title': text(node.find('title')), 'text': text(node)}
                                  for node in article.findall('.//sec') if node.find('title') is not None
                                  and any(key in text(node.find('title')).lower() for key in
                                          ['synthesis', 'hemol', 'haemol', 'recombinant', 'antimicrobial', 'bacterial'])]})
write('source_review.json', sources)
write('primary_evidence.json', evidence)

pin = ET.parse(ROOT / 'raw/pandinin2014.xml').getroot()
table = next(node for node in pin.findall('.//table-wrap') if node.get('id') == 'pone-0101742-t001')
candidates = []
for row in table.findall('.//tbody/tr'):
    cells = [text(node).strip() for node in row if node.tag == 'td']
    if len(cells) == 9:
        name = ' '.join(cells[0].split())
        seq = ''.join(cells[1].split())
        if set(seq) <= set('ACDEFGHIKLMNPQRSTVWY'):
            candidates.append({'name': name, 'seq': seq, 'source_id': 'pandinin2014',
                               'identity_basis': 'Table 1 sequence and MS; synthesis explicitly states free carboxyl',
                               'label': None})
assert len(candidates) == 5
candidates.append({'name': 'ChMAP-28', 'seq': 'GRFKRFRKKLKRLWHKVGPFVGPILHY',
                   'source_id': 'chmap2018', 'identity_basis': 'Abstract sequence; methods explicitly non-amidated recombinant analog',
                   'label': None})
pair_rows = []
summary = []
for candidate in candidates:
    for cohort, rows, identifier in [('formal_417', dev, 'record_id'), ('mic_16', mic, 'sample_id')]:
        pairs = []
        for row in rows:
            identity = sequence_identity(candidate['seq'], row['seq'], identity_mode='alignment')
            pair = {'candidate_name': candidate['name'], 'reference_cohort': cohort,
                    'reference_id': row[identifier], 'identity_alignment': identity, 'conflict_ge_0_40': identity >= .40}
            pair_rows.append(pair)
            pairs.append(pair)
        best = max(pairs, key=lambda row: row['identity_alignment'])
        summary.append({'candidate_name': candidate['name'], 'reference_cohort': cohort,
                        'max_identity': best['identity_alignment'], 'closest_reference_id': best['reference_id'],
                        'violating_pairs': sum(pair['conflict_ge_0_40'] for pair in pairs), 'admitted': False})
with (ROOT / 'sequence_pairs.csv').open('x', encoding='utf-8', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(pair_rows[0]))
    writer.writeheader()
    writer.writerows(pair_rows)
write('candidate_identity_prescreen.json', {'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'status': 'discovery_prescreen_only', 'candidates': candidates, 'summary': summary,
      'pair_count': len(pair_rows), 'identity_mode': 'alignment', 'cutoff': .40,
      'labels_released': 0, 'new_training': False})
assert len(pair_rows) == 6 * 433
print(json.dumps({'sources': [{key: source[key] for key in ['source_id', 'formal_exact_identifier_matches', 'mic_exact_identifier_matches']} for source in sources], 'sequence_summary': summary}, indent=2))
