"""Independent read-only binding, coverage, source-target and mass checks."""
import argparse
import ast
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from bs4 import BeautifulSoup
import fitz

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
PRIOR = ROOT/'03_experiments/audits/hc50_salmon_supplement_20261005_v1/review'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    review, output = args.review.resolve(), args.output.resolve()
    require(review.is_relative_to(BASE) and output.is_relative_to(BASE), 'Paths must remain inside this audit')
    require(not output.exists(), 'Do not overwrite verification')
    manifest = json.loads((review/'manifest.json').read_text(encoding='utf-8'))
    for group in ['protected','inputs','outputs']:
        for name, expected in manifest[group].items():
            base = review if group == 'outputs' else ROOT
            path = (base/name).resolve()
            require(path.is_relative_to(base), 'Manifest path outside scope')
            require(sha(path) == expected, 'Hash mismatch: '+name)
    old = rows(PRIOR/'merged_candidate_decisions.csv')
    new = rows(review/'candidate_decisions.csv')
    merged = rows(review/'merged_candidate_decisions.csv')
    scope = {r['candidate_id'] for r in new}
    require(len(new) == 5 and len(scope) == 5, 'Five unique decisions required')
    require(len(merged) == 78 and len({r['candidate_id'] for r in merged}) == 78, '78 unique cumulative decisions required')
    require([r['candidate_id'] for r in old] == [r['candidate_id'] for r in merged], 'Candidate universe/order changed')
    mapping = {r['candidate_id']:r for r in new}
    for before, after in zip(old, merged):
        require(after == mapping.get(before['candidate_id'],before), 'Outside-scope record modified')
        require(after['decision'] == before['decision'], 'Decision was released without new evidence')
    summary = json.loads((review/'summary.json').read_text(encoding='utf-8'))
    require(summary['merged_decision_counts'] == dict(Counter(r['decision'] for r in merged)), 'Count mismatch')
    require(summary['formal_scientific_status'] == 'blocked' and summary['formal_external_released'] == 0 and summary['human_exact_hc50_values_added'] == 0 and not summary['training_state_changed'], 'Unauthorized state change')
    prior_summary = json.loads((PRIOR/'summary.json').read_text(encoding='utf-8'))
    for key in ['merged_candidate_records','merged_candidates_endpoint_screened','remaining_original_access_gaps']:
        require(summary[key] == prior_summary[key], 'Coverage changed without new candidate screening')
    constants = ast.parse((ROOT/'02_code/feature_extractor.py').read_text(encoding='utf-8-sig'))
    weights = next(ast.literal_eval(n.value) for n in constants.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id == 'MOLECULAR_WEIGHTS' for t in n.targets))
    integer_weights = {a:int(Decimal(str(value))*10000) for a,value in weights.items()}
    figures = json.loads((review/'figure_review.json').read_text(encoding='utf-8'))
    image = BASE/figures['source']
    require(sha(image) == figures['sha256'] and not figures['independent_human_review'], 'Figure binding/review mode mismatch')
    pix = fitz.Pixmap(str(image))
    require((pix.width,pix.height) == (figures['width'],figures['height']), 'Figure dimensions changed')
    previous = {r['candidate_id']:r for r in rows(PRIOR/'sequence_identity_review.csv')}
    diagnostics = rows(review/'mass_and_sequence_diagnostics.csv')
    require(len(diagnostics) == 5 and {r['candidate_id'] for r in diagnostics} == scope, 'Mass/figure coverage mismatch')
    for row in diagnostics:
        seq = row['publisher_figure_sequence']
        require(seq == figures['transcriptions'][row['candidate_id']] == previous[row['candidate_id']]['primary_2016_sequence'], 'Source sequence mismatch')
        expected = Decimal(sum(integer_weights[a] for a in seq)-180152*(len(seq)-1))/10000
        require(expected == Decimal(row['conditional_linear_free_termini_average_mass_da']), 'Mass arithmetic mismatch')
        require(Decimal(row['source_table_mass_da'])-expected == Decimal(row['source_minus_conditional_mass_da']), 'Mass difference mismatch')
        require(row['formal_identity_release'] == 'False' and row['used_for_label_conversion'] == 'False', 'Conditional mass used for release')
    tt = next(r for r in diagnostics if r['candidate_id'] == 'HIST_DRAMP20859')
    require(tt['sequence_length'] == '20' and Decimal(tt['conditional_linear_free_termini_average_mass_da']) == Decimal('2181.4312') and not summary['tt_1_24_conflict_resolved'], 'TT conflict incorrectly resolved')
    primary = rows(review/'primary_endpoint_screen.csv')
    require(len(primary) == 2, 'Two primary-transfer screens required')
    for row in primary:
        source = BASE/row['file']
        soup = BeautifulSoup(source.read_bytes(),'html.parser')
        text = soup.get_text(' ',strip=True)
        require(sha(source) == row['file_sha256'] and row['title_marker'] in soup.select_one('h1').get_text(' ',strip=True), 'Primary identity mismatch')
        require(row['identity_marker'] in text and row['target_marker'] in text and row['human_hc50_released'] == 'False', 'Wrong endpoint accepted')
    coverage = rows(review/'search_coverage.csv')
    hits = rows(review/'search_hit_review.csv')
    require(len(coverage) == summary['search_queries'] == 8, 'Query coverage incomplete')
    for row in coverage:
        result = json.loads((BASE/row['source_file']).read_text(encoding='utf-8'))
        raw = result.get('resultList',{}).get('result',[])
        captured = [h for h in hits if h['query_name'] == row['query_name']]
        require(int(row['hit_count']) == result['hitCount'] == len(raw) == len(captured) and row['truncated'] == 'False', 'Search page/hit coverage mismatch')
        require([(r['id'],r['title']) for r in raw] == [(r['id'],r['title']) for r in captured], 'Search hit identity/order mismatch')
    unrelated = [r for r in hits if r['query_name'] == 'exact_fragments']
    require(len(unrelated) == 5 and all('unrelated' in r['disposition'] and r['formal_release'] == 'False' for r in unrelated), 'False-positive matches not rejected')
    for script in (BASE/'scripts').glob('*.py'):
        tree = ast.parse(script.read_text(encoding='utf-8'))
        require(not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in {'fit','fit_transform','partial_fit'} for n in ast.walk(tree)), 'Model fitting call in audit')
    result = {'generated_at':datetime.now(timezone.utc).isoformat(), 'status':'passed',
              'review_manifest_sha256':sha(review/'manifest.json'), 'verifier_sha256':sha(Path(__file__)),
              'protected_files_checked':len(manifest['protected']), 'input_files_checked':len(manifest['inputs']),
              'output_files_checked':len(manifest['outputs']), 'five_followup_records':5, 'cumulative_records':78,
              'unchanged_outside_scope':73, 'conditional_mass_checks':5,'publisher_figure_bindings':1,
              'primary_wrong_target_transfer_rejections':2,'search_queries_checked':8,
              'unrelated_search_hits_rejected':5,'model_fit_calls':0,'independent_human_review':False,
              'limitations':'Checks bind agent visual review; they do not independently transcribe the image or establish worldwide absence of evidence.'}
    with output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=True))


if __name__ == '__main__':
    main()
