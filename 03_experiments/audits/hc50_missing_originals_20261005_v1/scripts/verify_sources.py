"""Read-only provenance, coverage, and source-cell verification. Never fits a model."""
import argparse
import ast
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import fitz
from acquire_sources import BASE, ROOT, PRIOR, PRIOR_SHA, sha, save


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    review, output = args.review.resolve(), args.output.resolve()
    require(review.is_relative_to(BASE) and output.is_relative_to(BASE) and not output.exists(), 'Use existing review and new verification path inside this batch')
    manifest_path = review / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    require(manifest['prior_review_manifest_sha256'] == PRIOR_SHA == sha(PRIOR / 'manifest.json'), 'Previous review binding changed')
    for key in ['protected', 'inputs']:
        for name, expected in manifest[key].items():
            require(sha(ROOT / name) == expected, f'Changed {key}: {name}')
    for name, expected in manifest['outputs'].items():
        require(sha(review / name) == expected, f'Changed review output: {name}')
    decisions = rows(review / 'candidate_decisions.csv')
    merged = rows(review / 'merged_candidate_decisions.csv')
    subset = rows(BASE / 'acquisition/candidate_subset.csv')
    prior = rows(PRIOR / 'merged_candidate_decisions.csv')
    ids = {r['candidate_id'] for r in subset}
    require(len(decisions) == len(ids) == 44 and {r['candidate_id'] for r in decisions} == ids, '44-record coverage changed')
    require(len(merged) == 78 and len({r['candidate_id'] for r in merged}) == 78, '78-record coverage changed')
    old = {r['candidate_id']: r for r in prior}
    current = {r['candidate_id']: r for r in decisions}
    require(set(old) == {r['candidate_id'] for r in merged}, 'Candidate universe changed')
    require(all(r == old[r['candidate_id']] for r in merged if r['candidate_id'] not in ids), 'Unrelated previous decisions changed')
    require(all(r == current[r['candidate_id']] for r in merged if r['candidate_id'] in ids), 'Batch/cumulative decisions differ')
    require(all(r['formal_release'] == r['sequence_and_form_release'] == 'False' for r in merged), 'Unexpected formal release')
    studies = rows(review / 'source_review.csv')
    require(len(studies) == 28 and len({(r['pmid'],r['doi']) for r in studies}) == 28, '28-study coverage changed')
    covered = [cid for r in studies for cid in r['candidate_ids'].split(';')]
    require(len(covered) == 44 and set(covered) == ids, 'Study-to-candidate coverage changed')
    require({r['pmid'] for r in studies if r['original_identity_reviewed'] == 'True'} == {'27818338', '34302796', '16940535'}, 'Original source count changed')
    require(sum(int(r['capture_attempts']) for r in studies) == 40, 'Capture coverage changed')
    response_review = json.loads((review / 'response_review.json').read_text(encoding='utf-8'))
    originals = [r for r in response_review if r['reviewed_response_role'] in ['author_manuscript_identity_reviewed', 'primary_html_identity_reviewed']]
    require(len(originals) == 3, 'Non-original counted as original')
    require(all(r['reviewed_response_role'].endswith('not_original') or r['reviewed_response_role'] == 'supporting_bioc_identity_reviewed' or r in originals for r in response_review), 'Ambiguous response counted')
    require(sum(len(r.get('file','')) > 0 for r in response_review) == sum('sha256' in r for r in response_review), 'Archived responses lack hashes')

    inventory_path = ROOT / '03_experiments/audits/hc50_primary_followup_20261004_v1/acquisition/candidate_inventory.csv'
    inventory = {r['candidate_id']: r for r in rows(inventory_path)}
    identity = {r['candidate_id']: r for r in rows(review / 'sequence_identity_review.csv')}
    require(len(identity) == 7 and set(identity).issubset(ids), 'Identity coverage changed')
    for cid, row in identity.items():
        require(row['inventory_sequence'] == inventory[cid]['sequence'], 'Inventory sequence rewritten')
        require(int(row['inventory_length']) == len(row['inventory_sequence']) and int(row['source_length']) == len(row['source_sequence']), 'Sequence length mismatch')
        require((row['sequence_match'] == 'True') == (row['source_sequence'] == row['inventory_sequence']), 'Sequence-match flag incorrect')
    conflicts = [cid for cid,r in identity.items() if r['sequence_match'] == 'False']
    require(conflicts == ['HIST_DRAMP20862'], 'Unexpected sequence conflict set')
    require(identity['HIST_DRAMP20862']['source_sequence'] == 'RRGKDSGGPKMGRKNSKGGWRGRPGSGSRPGFGSGI', 'Manual figure transcription changed')
    require(identity['HIST_DRAMP20862']['source_length'] == '36' and identity['HIST_DRAMP20862']['inventory_length'] == '35', 'rtCATH2 mismatch lost')

    observations = rows(review / 'raw_assay_observations.csv')
    require(len(observations) == 17 and len({(r['candidate_id'],r['endpoint']) for r in observations}) == 17, 'Observation coverage/uniqueness changed')
    require(all(r['formal_label'] == '' and r['formal_release'] == 'False' for r in observations), 'Unexpected label assignment')
    require({r['candidate_id'] for r in observations} == set(identity) - {'DBAASP_497'}, 'Wrong molecule receives assay observations')
    with fitz.open(BASE / 'acquisition/raw/pmid_27818338_author_accepted.pdf') as document:
        page = document[30]
        words = page.get_text('words')
        anchor = next(w for w in words if w[4] == '25922')
        # Independent spatial read of the rotated PDF row, not the review regex.
        row_words = [w for w in words if abs(w[0]-anchor[0]) < 2 and w[4].isdigit() and w[4] != '25922']
        row_words.sort(key=lambda w: (fitz.Point(w[0],w[1])*page.rotation_matrix).x)
        raw_cells = [w[4] for w in row_words]
        require(raw_cells == ['32','4','2','16','4','16'], 'PDF Table 2 spatial read changed')
        expected = {'HIST_DRAMP20859':raw_cells[0], 'HIST_DRAMP20860':raw_cells[1], 'HIST_DRAMP20862':raw_cells[3], 'HIST_DRAMP20863':raw_cells[4], 'HIST_DRAMP20864':raw_cells[5]}
        for cid, value in expected.items():
            obs = [r for r in observations if r['candidate_id'] == cid]
            mic = next(r for r in obs if r['endpoint'] == 'MIC')
            human = next(r for r in obs if r['endpoint'] == 'human_hemolysis_qualitative_test_ceiling')
            panel = next(r for r in obs if r['endpoint'] == 'MIC_bacterial_panel_statement')
            require(mic['raw_value'] == value and mic['target'] == 'E. coli ATCC 25922', 'Salmon MIC mapping changed')
            require(human['raw_value'] == 'no hemolytic effects reported up to 100' and 'not a reported HC50' in human['unit'], 'Qualitative ceiling promoted to HC50')
            require(panel['raw_value'] == '>64' and 'no individual row' in panel['target'], 'Panel statement promoted to individual measurement')
            require(not any(r['conditional_lower_ug_ml'] or r['conditional_upper_ug_ml'] for r in obs), 'Unapproved salmon conversion')
        human_text = document[18].get_text()
        require('human red blood cells' in human_text and 'up to 100 µM' in human_text and 'Figure S1' in human_text, 'Human narrative not reproduced')
        require('MIC >64 µM' in document[15].get_text() and 'data not shown' in document[15].get_text(), 'Panel/medium statement not reproduced')
        pdf_cells_checked = len(raw_cells)

    soup = BeautifulSoup((BASE / 'acquisition/raw/pmid_34302796_primary.html').read_bytes(), 'html.parser')
    # Direct indexed cells and source headers, separate from the review row-name selection.
    t1 = soup.select('#T1 tbody tr')[1].find_all('td',recursive=False)
    t2 = soup.select('#T2 tbody tr')[0].find_all('td',recursive=False)
    t3 = soup.select('#T3 tbody tr')[1].find_all('td',recursive=False)
    value = lambda cell: cell.get_text(' ',strip=True)
    require(value(t1[1]) == 'M-PONTX–Nc1a' and value(t1[2]) == identity['DBAASP_19356']['source_sequence'], 'Nc1a source identity mismatch')
    require('Hemolysis' in soup.select('#T3 thead tr')[0].get_text() and '50% of human red blood cells' in soup.select_one('#T3').get_text(' ',strip=True), 'HC50 target/header mismatch')
    require(value(t3[0]) == 'Nc1a' and value(t3[6]) == '12.6–13.5' and value(t3[7]) == '28.6–48.2', 'CC50/HC50 cells confused')
    require(value(t2[2]) == '25.8–51.6' and 'E.coli' in value(t2[0]), 'Species-specific MIC missing')
    require('259922' == soup.select('#T2 tbody tr')[1].get_text(' ',strip=True), 'Source strain typography changed')
    mass = Decimal(value(t1[4]))
    ant_observations = [r for r in observations if r['candidate_id'] == 'DBAASP_19356']
    for record in ant_observations:
        raw = value(t3[7]) if record['endpoint'] == 'HC50' else value(t2[2])
        low,high = [Decimal(x) for x in raw.split('–')]
        require(record['raw_value'] == raw and record['unit'] == 'µM', 'Nc1a original assay value mismatch')
        require(Decimal(record['conversion_mass_da']) == mass, 'Nc1a mass mismatch')
        require(Decimal(record['conditional_lower_ug_ml']) == low*mass/1000 and Decimal(record['conditional_upper_ug_ml']) == high*mass/1000, 'Conditional Decimal conversion mismatch')
    human = next(r for r in ant_observations if r['endpoint'] == 'HC50')
    mic = next(r for r in ant_observations if r['endpoint'] == 'MIC')
    require(Decimal(human['conditional_lower_ug_ml']) < 100 < Decimal(human['conditional_upper_ug_ml']), 'HC50 threshold crossing lost')
    require(32 < Decimal(mic['conditional_lower_ug_ml']) < Decimal(mic['conditional_upper_ug_ml']) < 128, 'MIC threshold gap lost')
    bioc = ET.parse(BASE / 'acquisition/raw/pmid_34302796_bioc.xml').getroot()
    require(bioc.tag == 'collection' and 'FWGAAAKMLGKALPGLISMFQKN' in ''.join(bioc.itertext()), 'Supporting BioC is not original text')
    dhvar = BeautifulSoup((BASE / 'acquisition/raw/pmid_16940535_primary.html').read_bytes(),'html.parser')
    require('Dhvar3, KRLFKKLKFSLRKY;' in dhvar.select_one('#sec2').get_text(' ',strip=True), 'Dhvar3 identity not reproduced')
    require(not any(r['candidate_id'] == 'DBAASP_497' for r in observations), 'Wrong-endpoint Dhvar3 assay fabricated')
    visual = json.loads((review / 'visual_review.json').read_text(encoding='utf-8'))
    require(visual['pdf_pages_inspected'] == [11,19,30,31,32] and len(visual['images']) == 8, 'Visual review acknowledgement incomplete')
    require(all((BASE/name).is_file() for name in visual['images']), 'Visual evidence missing')
    for path in (BASE / 'scripts').glob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        require(not any(isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in ['fit','fit_transform','partial_fit'] for node in ast.walk(tree)), f'Model fitting added to audit: {path.name}')
    summary = json.loads((review / 'summary.json').read_text(encoding='utf-8'))
    require(summary['remaining_original_access_gaps'] == sum(r['screen_status'] == 'original_not_acquired' for r in merged) == 37, 'Access-gap count mismatch')
    require(summary['merged_candidates_endpoint_screened'] == 41 and summary['merged_decision_counts'] == dict(Counter(r['decision'] for r in merged)), 'Summary/ledger mismatch')
    require(summary['formal_scientific_status'] == 'blocked' and summary['formal_external_released'] == summary['model_fit_calls'] == 0 and not summary['training_state_changed'], 'Formal state changed')
    formal = json.loads((ROOT / '04_paper/research_status.json').read_text(encoding='utf-8'))
    # The formal state and current MIC status are included in protected SHA checks above.
    require(sha(ROOT / '04_paper/research_status.json') == '846c1fc2452646f3df9c2055b0a4a1b5140132acc2433bb2c304b133b6e8012c', 'Formal state hash changed')
    require(sha(ROOT / '03_experiments/audits/mic_training_readiness_20261004_v26.json') == '404e9d90166564ec9c7543022853ae694dabc9022d913fa5d8e10f3b842a2da1', 'Current MIC state hash changed')
    result = {'generated_at':datetime.now(timezone.utc).isoformat(), 'status':'passed',
              'review_manifest_sha256':sha(manifest_path), 'verification_script_sha256':sha(Path(__file__)),
              'protected_files_checked':len(manifest['protected']), 'inputs_checked':len(manifest['inputs']), 'outputs_checked':len(manifest['outputs']),
              'batch_candidates_checked':44, 'research_sources_checked':28, 'merged_candidates_checked':78,
              'unchanged_outside_batch_candidates':34, 'pdf_table_cells_spatially_checked':pdf_cells_checked,
              'html_sequence_mass_and_assay_cells_checked':5, 'conditional_conversions_checked':4,
              'declared_visual_pages':5, 'visual_artifacts_hash_checked':8, 'sequence_transcriptions_independently_human_verified':False,
              'formal_external_released':0, 'model_fit_calls':0, 'formal_scientific_status':'blocked',
              'limitation':'Coverage/source-cell/hash verification; not independent human review or scientific gate clearance'}
    save(output,result)
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    main()
