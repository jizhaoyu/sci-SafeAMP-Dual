"""Retain chemical identities from Table S8 and reject current MIC-domain mismatch."""
import csv
import json
import pathlib
import re

root = pathlib.Path(__file__).resolve().parent
pages = json.loads((root / 'foundation_pages.json').read_text(encoding='utf-8'))
text = next(page['text'] for page in pages if page['page'] == 11)
pattern = r'^([A-Z]+\d+)\s+([A-Z]+-NH2)\s+(\d+\.\d+)\s+(\d+\.\d+)\s*$'
rows = []
for name, sequence, expected, measured in re.findall(pattern, text, re.MULTILINE):
    rows.append({'name': name, 'sequence_with_form_verbatim': sequence,
                 'expected_ms_verbatim': expected, 'measured_ms_verbatim': measured,
                 'terminal_form': 'C-terminal amide', 'source': '10.1126/sciadv.ads8932',
                 'location': 'Supplementary PDF page 11, Table S8',
                 'mic_cohort_decision': 'excluded_current_domain',
                 'reason': 'Current MIC protocol requires unmodified linear molecules; S8 explicitly reports -NH2',
                 'formal_dual_task_decision': 'pending_separate_protocol_and_isolation_review',
                 'label': '', 'review_mode': 'agent_primary_source_review'})
assert len(rows) == 23
with (root / 'foundation_molecule_review.csv').open('x', encoding='utf-8', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
with (root / 'foundation_endpoint_review.json').open('x', encoding='utf-8') as handle:
    json.dump({'source': '10.1126/sciadv.ads8932', 'location': 'Supplementary PDF page 5, Figure S4',
               'visual_review_completed': True, 'molecules': ['KW13', 'AI18'],
               'highest_displayed_peptide_concentration': 1000, 'unit': 'ug/ml',
               'reported_hc50_relation': '>', 'reported_hc50_bound': 1000,
               'exact_hc50': None, 'raw_numeric_hemolysis_replicates_available_in_pdf': False,
               'handling': 'Preserve censored range; do not set exact HC50 to 1000 or digitize bars as raw replicates',
               'remaining_condition_issue': 'Main methods describe 100 ug/ml procedure; figure shows a dilution series to 1000 ug/ml',
               'labels_released': 0}, handle, indent=2)
print('23 identities reviewed: all C-terminal amides, excluded from current MIC domain. No labels released.')
