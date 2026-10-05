"""Independent matrix replay using explicit 2-D NW traceback; never fits models."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import evidence_audit as audit


def nw_identity(left, right):
    a, b = sorted((left, right))
    n, m = len(a), len(b)
    scores = [[0] * (m + 1) for _ in range(n + 1)]
    directions = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        scores[i][0], directions[i][0] = -2 * i, 1
    for j in range(1, m + 1):
        scores[0][j], directions[0][j] = -2 * j, 2
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            choices = (scores[i-1][j-1] + (2 if a[i-1] == b[j-1] else -1),
                       scores[i-1][j] - 2, scores[i][j-1] - 2)
            value = max(choices)
            scores[i][j], directions[i][j] = value, choices.index(value)
    i, j, matches, columns = n, m, 0, 0
    while i or j:
        direction = directions[i][j]
        if direction == 0:
            matches += a[i-1] == b[j-1]
            i, j = i - 1, j - 1
        elif direction == 1:
            i -= 1
        else:
            j -= 1
        columns += 1
    return matches / columns


def verify(output, anchor):
    if audit.sha(output / 'manifest.json') != anchor:
        raise ValueError('Output manifest anchor mismatch')
    summary = audit.validate_output(output)
    input_manifest = audit.ROOT / summary['input_manifest']
    inputs = audit.load_inputs(input_manifest, summary['input_manifest_sha256'])
    molecules = {r['candidate_id']: r for r in audit.read_csv(output / 'molecule_review.csv')}
    dev = {r['record_id']: r['seq'] for r in audit.read_csv(audit.ROOT / inputs['roles']['development_records'])}
    seen, cache, maxima = set(), {}, {}
    for row in audit.read_csv(output / 'similarity_to_development.csv'):
        cid, did = row['candidate_id'], row['development_record_id']
        key = (cid, did)
        if key in seen:
            raise ValueError('Duplicate matrix pair')
        seen.add(key)
        a, b = molecules[cid]['sequence'], dev[did]
        if a != row['candidate_sequence'] or b != row['development_sequence']:
            raise ValueError('Matrix sequence substitution')
        seq_key = tuple(sorted((a, b)))
        if seq_key not in cache:
            cache[seq_key] = nw_identity(a, b)
        identity = cache[seq_key]
        if abs(identity - float(row['identity'])) > 1e-12 or (identity >= .4) != (row['violates_cutoff'] == 'True'):
            raise ValueError('Independent NW identity mismatch')
        maxima[cid] = max(maxima.get(cid, 0), identity)
    expected = {(cid, did) for cid, c in molecules.items() if c['sequence'] for did in dev}
    if seen != expected:
        raise ValueError('Matrix coverage incomplete')
    for row in audit.read_csv(output / 'external_candidate_decisions.csv'):
        if row['candidate_id'] in maxima and abs(float(row['reported_sequence_max_identity']) - maxima[row['candidate_id']]) > 1e-12:
            raise ValueError('Candidate maximum differs')
    for row in audit.read_csv(output / 'candidate_similarity.csv'):
        a, b = molecules[row['candidate_1_id']]['sequence'], molecules[row['candidate_2_id']]['sequence']
        identity = nw_identity(a, b)
        if abs(identity - float(row['identity'])) > 1e-12 or (identity >= .4) != (row['violates_cutoff'] == 'True'):
            raise ValueError('Internal NW mismatch')
    return dict(status='passed', verified_at=datetime.now(timezone.utc).isoformat(), output_manifest_sha256=anchor,
                independent_development_pairs=len(seen), independent_internal_pairs=summary['counts']['candidate_internal_comparisons'],
                algorithm='2-D scores plus explicit diagonal/up/left traceback; gaps in denominator',
                protected_v1_files=len(inputs['protected_v1']), protected_input_files=len(inputs['files']),
                formal_status='blocked', eligible_external=summary['counts']['eligible_external'],
                meaning='Evidence repair consistency verified; does not approve formal cohort or submission')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise FileExistsError('Verification report already exists')
    result = verify(args.output.resolve(), args.manifest_sha256)
    audit.write_json(args.report, result)
    print(json.dumps(result, ensure_ascii=True))
