"""Evidence-clean source and external curation must remain fail closed."""
import json

import numpy as np
import pandas as pd
import pytest

from curate_evidence_clean_source import curate_evidence_clean_source
from audit_external_candidates import audit_external_candidates
from external_curator import build_external_cohort
from research_data import ResearchDataError, prepare
from research_utils import read_json, sha256, write_json
from test_external_evidence import make_record


def test_unsupported_external_label_is_excluded_and_preparation_stays_blocked(tmp_path):
    raw_entries = [
        {'id': 'DEV_1', 'seq': 'A' * 10, 'doi': '10.1000/dev', 'assays': [
            {'endpoint': 'amp', 'target_organism_or_cell': 'Escherichia coli',
             'metric_name': 'MIC', 'raw_value': '8', 'raw_unit': 'ug/ml', 'reference': '10.1000/dev'}]},
        {'id': 'EXT_1', 'seq': 'C' * 10, 'amp': 0, 'hemo': 0},
    ]
    dev = make_record(
        tmp_path, raw_data=raw_entries, record_id='DEV_1', seq='A' * 10,
        amp=1.0, hemo=np.nan, source_role='development', source_dataset='DevDB',
        evidence_reference=json.dumps([{'doi': '10.1000/dev'}]),
    )
    ext = dev.copy()
    ext.loc[0, ['record_id', 'seq', 'amp', 'hemo', 'source_role', 'source_dataset']] = [
        'EXT_1', 'C' * 10, 0.0, 0.0, 'external', 'ExternalDB'
    ]
    source_file = tmp_path / 'source.csv'
    pd.concat([dev, ext], ignore_index=True).to_csv(source_file, index=False)

    cleaned_dir = tmp_path / 'cleaned'
    source_manifest = curate_evidence_clean_source(source_file, cleaned_dir)
    assert source_manifest['development_records'] == 1
    assert source_manifest['external_records'] == 0
    assert source_manifest['excluded_unsupported_external_records'] == 1
    assert read_json(cleaned_dir / 'exclusions.json')[0]['record_id'] == 'EXT_1'

    prepared_dir = tmp_path / 'prepared'
    with pytest.raises(ResearchDataError, match='external cohort is required'):
        prepare(cleaned_dir / 'records.csv', prepared_dir, protocol_id='protocol-amd-02')
    prepared = read_json(prepared_dir / 'manifest.json')
    assert prepared['status'] == 'blocked'
    assert prepared['protocol_id'] == 'protocol-amd-02'
    assert prepared['cluster_count'] == 1
    assert prepared['cross_cohort_similarity_sha256'] == sha256(prepared_dir / 'cross_cohort_similarity.csv')
    assert read_json(prepared_dir / 'homology_audit.json')['cross_pairs_evaluated'] == 0


def test_external_curator_uses_assays_and_all_development_members(tmp_path):
    dev_file = tmp_path / 'development.csv'
    pd.DataFrame([
        {'seq': 'A' * 10, 'evidence_reference': json.dumps([{'doi': '10.1000/dev'}])},
        {'seq': 'C' * 10, 'evidence_reference': json.dumps([{'doi': '10.1000/dev2'}])},
    ]).to_csv(dev_file, index=False)
    raw_file = tmp_path / 'external.json'
    write_json(raw_file, [
        {'id': 'HANDWRITTEN', 'seq': 'M' * 10, 'doi': '10.1000/invalid', 'amp': 1, 'hemo': 0},
        {'id': 'OVERLAP', 'seq': 'M' * 10, 'doi': '10.1000/dev', 'assays': [
            {'endpoint': 'amp', 'target_organism_or_cell': 'Escherichia coli',
             'metric_name': 'MIC', 'raw_value': '8', 'raw_unit': 'ug/ml'}]},
        {'id': 'MEASURED', 'seq': 'M' * 10, 'doi': '10.1000/independent', 'amp': 0, 'hemo': 1,
         'assays': [
             {'endpoint': 'amp', 'target_organism_or_cell': 'Escherichia coli',
              'metric_name': 'MIC', 'raw_value': '8', 'raw_unit': 'ug/ml'},
             {'endpoint': 'hemo', 'target_organism_or_cell': 'Human erythrocytes',
              'metric_name': 'HC50', 'raw_value': '300', 'raw_unit': 'ug/ml'},
         ]},
    ])

    output = tmp_path / 'external_candidate'
    curated = build_external_cohort(dev_file, output, raw_entries_path=raw_file)
    assert len(curated) == 1
    assert curated.iloc[0]['amp'] == 1.0
    assert curated.iloc[0]['hemo'] == 0.0
    exclusions = read_json(output / 'exclusions.json')
    assert {item['id'] for item in exclusions} == {'HANDWRITTEN', 'OVERLAP'}
    with pytest.raises(ValueError, match='Output exists'):
        build_external_cohort(dev_file, output, raw_entries_path=raw_file)


def test_candidate_screen_retains_every_pair_and_cutoff_boundary(tmp_path):
    candidates = tmp_path / 'candidates.csv'
    development = tmp_path / 'development.csv'
    pd.DataFrame([{'sequence': 'A' * 10}]).to_csv(candidates, index=False)
    pd.DataFrame([
        {'record_id': 'same', 'seq': 'A' * 10},
        {'record_id': 'different', 'seq': 'C' * 10},
        {'record_id': 'boundary', 'seq': 'A' * 4 + 'C' * 6},
    ]).to_csv(development, index=False)
    out = tmp_path / 'screen'
    manifest = audit_external_candidates(candidates, development, out)
    pairs = pd.read_csv(out / 'all_pairs.csv')
    assert manifest['all_pairs_evaluated'] == 3
    assert manifest['candidates_violating_cutoff'] == 1
    assert pairs.set_index('development_record_id').loc['boundary', 'identity'] == pytest.approx(0.4)
    assert bool(pairs.set_index('development_record_id').loc['boundary', 'violates_cutoff'])
