"""Replay every candidate-to-development similarity under protocol-amd-02."""
import argparse
from pathlib import Path

import pandas as pd

from research_data import sequence_identity
from research_protocol_config import get_protocol, protocol_digest
from research_utils import sha256, utc_now, write_json


def audit_external_candidates(candidate_csv: Path, development_csv: Path, output_dir: Path) -> dict:
    candidate_csv, development_csv, output_dir = map(Path, (candidate_csv, development_csv, output_dir))
    if output_dir.exists():
        raise ValueError('Output exists; use a new versioned candidate audit directory.')
    spec = get_protocol('protocol-amd-02')
    candidates = pd.read_csv(candidate_csv)
    development = pd.read_csv(development_csv)
    if 'sequence' not in candidates or not {'record_id', 'seq'} <= set(development.columns):
        raise ValueError('Candidate sequence and development record_id/seq columns are required.')

    pairs = []
    summaries = []
    for index, candidate in candidates.reset_index(drop=True).iterrows():
        scores = []
        for dev in development.itertuples():
            identity = sequence_identity(candidate['sequence'], dev.seq, identity_mode='alignment')
            scores.append(identity)
            pairs.append({
                'candidate_index': index,
                'candidate_sequence': candidate['sequence'],
                'development_record_id': dev.record_id,
                'identity': identity,
                'violates_cutoff': identity >= spec.cutoff,
            })
        maximum = max(scores, default=0.0)
        summaries.append({
            'candidate_index': index,
            'candidate_sequence': candidate['sequence'],
            'max_identity': maximum,
            'violates_cutoff': maximum >= spec.cutoff,
            'assay_and_study_evidence_status': 'not_evaluated_by_sequence_screen',
        })

    output_dir.mkdir(parents=True)
    pd.DataFrame(pairs, columns=[
        'candidate_index', 'candidate_sequence', 'development_record_id', 'identity', 'violates_cutoff'
    ]).to_csv(output_dir / 'all_pairs.csv', index=False)
    pd.DataFrame(summaries, columns=[
        'candidate_index', 'candidate_sequence', 'max_identity', 'violates_cutoff', 'assay_and_study_evidence_status'
    ]).to_csv(output_dir / 'candidate_summary.csv', index=False)
    manifest = {
        'status': 'sequence_screen_only',
        'generated_at': utc_now(),
        'protocol_id': spec.protocol_id,
        'protocol_digest': protocol_digest(spec),
        'candidate_input_sha256': sha256(candidate_csv),
        'development_input_sha256': sha256(development_csv),
        'candidate_count': len(candidates),
        'development_count': len(development),
        'all_pairs_evaluated': len(pairs),
        'candidates_violating_cutoff': sum(row['violates_cutoff'] for row in summaries),
        'all_pairs_sha256': sha256(output_dir / 'all_pairs.csv'),
        'candidate_summary_sha256': sha256(output_dir / 'candidate_summary.csv'),
    }
    write_json(output_dir / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', type=Path, required=True)
    parser.add_argument('--development', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(audit_external_candidates(args.candidates, args.development, args.output))
