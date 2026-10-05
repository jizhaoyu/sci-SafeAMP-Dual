"""Read-only coverage and provenance verification with independent raw DOCX XML parsing."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
from acquire_sources import BASE, ROOT, PRIOR, IDS, sha, write_json

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
OLD = ROOT / '03_experiments/audits/hc50_primary_followup_20261004_v1/acquisition'
DOCS = BASE / 'publisher_static_content_acquisition_20261005/raw'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def raw_docx_table(number):
    with zipfile.ZipFile(DOCS / f'41598_2026_40997_MOESM{number}_ESM.docx') as package:
        doc = ET.fromstring(package.read('word/document.xml'))
    table = doc.find(f'.//{W}tbl')
    data = []
    vertical = {}
    for tr in table.findall(f'{W}tr'):
        row = []
        for tc in tr.findall(f'{W}tc'):
            col = len(row)
            value = ''.join(t.text or '' for t in tc.findall(f'.//{W}t')).strip()
            properties = tc.find(f'{W}tcPr')
            span = properties.find(f'{W}gridSpan') if properties is not None else None
            count = int(span.get(f'{W}val', '1')) if span is not None else 1
            merge = properties.find(f'{W}vMerge') if properties is not None else None
            if merge is not None:
                if merge.get(f'{W}val') == 'restart':
                    vertical[col] = value
                else:
                    value = vertical.get(col, value)
            else:
                vertical.pop(col, None)
            row.extend([value] * count)
        data.append(row)
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Output already exists')
    review = args.review.resolve()
    manifest_file = review / 'manifest.json'
    manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
    for key in ['inputs', 'protected']:
        for name, expected in manifest[key].items():
            require(sha(ROOT / name) == expected, f'Changed {key}: {name}')
    for name, expected in manifest['outputs'].items():
        require(sha(review / name) == expected, f'Changed review output: {name}')
    prior = rows(PRIOR / 'merged_candidate_decisions.csv')
    merged = rows(review / 'merged_candidate_decisions.csv')
    decisions = rows(review / 'candidate_decisions.csv')
    require(len(decisions) == 4 and {r['candidate_id'] for r in decisions} == IDS, 'Fixed four-record coverage')
    require(len(merged) == 78 and len({r['candidate_id'] for r in merged}) == 78, 'Merged coverage')
    require({r['candidate_id'] for r in merged} == {r['candidate_id'] for r in prior}, 'Candidate universe changed')
    prior_map = {r['candidate_id']: r for r in prior}
    require(all(r == prior_map[r['candidate_id']] for r in merged if r['candidate_id'] not in IDS), 'Unrelated decisions changed')
    require(all(r['formal_release'] == r['sequence_and_form_release'] == 'False' for r in decisions), 'Unexpected release')
    require(next(r for r in decisions if r['candidate_id'] == 'DBAASP_19706')['decision'] == 'excluded_by_known_molecular_form', 'CT7 form exclusion missing')
    identity = {r['candidate_id']: r for r in rows(review / 'sequence_identity_review.csv')}
    inventory = {r['candidate_id']: r for r in rows(OLD / 'candidate_inventory.csv')}
    require(set(identity) == IDS and all(identity[cid]['sequence'] == inventory[cid]['sequence'] for cid in IDS), 'Inventory/sequence mismatch')
    t1 = raw_docx_table(1)
    t2 = raw_docx_table(2)
    require(t2[1][2] == 'Red blood cells (human)' and t2[1][3] == 'MRC5-SV2 cells', 'Human RBC and cell IC50 columns mixed')
    require(t2[1][12] == 'E. coli' and 'Inhibitory' in t2[0][12], 'MIC/MBC column mixed')
    source_s1 = {r[0].split(' (')[0].strip(): r for r in t1[1:]}
    names = {'DBAASP_25709': 'NHill_AD_C49215', 'DBAASP_25712': 'Hill_BB_C7985'}
    for cid, name in names.items():
        row = source_s1[name]
        require(identity[cid]['sequence'] == row[1] and len(row[1]) == int(row[2]), 'Supplementary sequence mismatch')
        require(Decimal(identity[cid]['reported_mw_g_per_mol']) == Decimal(row[3]), 'Supplementary MW mismatch')
    observations = rows(review / 'raw_assay_observations.csv')
    require(len(observations) == 14, 'Observation row coverage')
    seen = set()
    s2_cells_checked = 0
    for record in observations:
        require(record['formal_label'] == '' and record['formal_release'] == 'False', 'Unexpected formal label')
        cid = record['candidate_id']
        if cid in names:
            key = cid, record['repeat'], record['normalized_endpoint']
            require(key not in seen, 'Duplicate repeat/endpoint observation')
            seen.add(key)
            row = next(r for r in t2[2:] if r[0].strip() == names[cid] and r[1] == record['repeat'])
            col = 2 if record['target'] == 'human red blood cells' else 12
            require(record['raw_value'] == row[col] and record['unit'] == 'µM', 'Raw supplementary cell mismatch')
            s2_cells_checked += 1
    require(s2_cells_checked == 8 and len(seen) == 8, 'Incomplete supplementary repeats')
    ct = ET.parse(OLD / 'raw/pmid_35323465.xml').getroot()
    ct_table = ct.find(".//table-wrap[@id='marinedrugs-20-00167-t002']")
    expected_ct7 = {}
    for tr in ct_table.findall('.//tbody/tr'):
        cells = [' '.join(' '.join(c.itertext()).split()) for c in tr.findall('td')]
        if len(cells) == 9 and cells[0].startswith('E. coli'):
            expected_ct7[cells[0]] = cells[7]
    actual_ct7 = {r['target']: r['raw_value'] for r in observations if r['candidate_id'] == 'DBAASP_19706'}
    require(actual_ct7 == expected_ct7 and len(actual_ct7) == 6, 'CT7 original cell mismatch')
    require(sum(v == 'n.d.' for v in actual_ct7.values()) == 2, 'Missing values converted to measurements')
    ct_form = ' '.join(ct.find(".//table-wrap[@id='marinedrugs-20-00167-t001']").itertext())
    require('two disulfide bonds' in ct_form, 'CT7 exclusion lacks explicit form evidence')
    conversions = rows(review / 'conditional_threshold_checks.csv')
    require(len(conversions) == 8, 'Conditional calculation coverage')
    for record in conversions:
        cid = record['candidate_id']
        mw = Decimal(source_s1[names[cid]][3])
        value = Decimal(record['reported_value_uM']) * mw / Decimal(1000)
        require(value == Decimal(record['conditional_value_ug_per_ml']), 'Conditional unit conversion mismatch')
        require(record['formal_label'] == '' and record['formal_release'] == 'False', 'Conditional check produced formal label')
        if record['endpoint'].startswith('human_'):
            require(record['operator'] == '>' and Decimal(100) < value < Decimal(250) and record['threshold_interpretation'] == 'unknown', 'HC50 lower bound incorrectly classified')
        if cid == 'DBAASP_25709' and record['endpoint'] == 'MIC':
            require(value == Decimal('127.537312') and value < 128 and record['threshold_interpretation'] == 'unknown', 'Censored MIC incorrectly rounded to negative boundary')
    summary = json.loads((review / 'summary.json').read_text(encoding='utf-8'))
    require(summary['merged_decision_counts'] == dict(Counter(r['decision'] for r in merged)), 'Summary counts inconsistent')
    require(summary['formal_external_released'] == summary['model_fit_calls'] == 0 and summary['formal_scientific_status'] == 'blocked', 'Scientific gate changed')
    render = json.loads((BASE / 'inspection_20261005/render_manifest.json').read_text(encoding='utf-8'))
    require(len(render['pages']) == 3, 'Missing rendered source tables')
    for page in render['pages']:
        folder = BASE / 'inspection_20261005'
        require(sha(folder / page['source_pdf']) == page['source_pdf_sha256'] and sha(folder / page['image']) == page['image_sha256'], 'Rendered source changed')
    result = {'generated_at': datetime.now(timezone.utc).isoformat(), 'status': 'passed',
              'scope': 'read-only coverage, raw DOCX XML cells, censoring, conditional arithmetic and provenance; not independent human review',
              'review_manifest_sha256': sha(manifest_file), 'verifier_sha256': sha(Path(__file__)),
              'protected_files_checked': len(manifest['protected']), 'input_files_checked': len(manifest['inputs']),
              'output_files_checked': len(manifest['outputs']), 'candidate_records_checked': 4, 'merged_records_checked': 78,
              'supplementary_assay_cells_checked': s2_cells_checked, 'ct7_ecoli_cells_checked': 6,
              'ct7_not_determined_cells_preserved': 2, 'conditional_calculations_checked': 8,
              'rendered_source_pages_checked': 3, 'model_fit_calls': 0, 'formal_release': False}
    write_json(args.output, result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
