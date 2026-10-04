"""Regression boundaries for the newly acquired original figure; never fit models."""
import json
from pathlib import Path

import pandas as pd
import pytest

import mic_followup_release as release
import train_mic_followup_baseline as training
from research_utils import ROOT, sha256

DIR=ROOT/'03_experiments/audits/mic_followup_release_20261004_v1'


def materials():
    return (pd.read_csv(DIR/'cohort/candidate_molecules.csv',keep_default_na=False),
            pd.read_csv(DIR/'cohort/candidate_observations.csv',keep_default_na=False),
            pd.read_csv(DIR/'evidence/source_review.csv',keep_default_na=False),
            pd.read_csv(DIR/'cohort/fold_roles.csv',keep_default_na=False),
            pd.read_csv(DIR/'cohort/all_member_similarity.csv',keep_default_na=False))


def test_only_original_numeric_isolate_observation_is_admitted():
    mol,obs,_,_,_=materials()
    bmap=obs[obs.sample_id.eq(release.BMAP_ID)]
    assert len(mol)==16 and len(obs)==23 and len(bmap)==1
    row=bmap.iloc[0]
    assert row.record_id=='bmap2025:Figure1:CREC6'
    assert row.target=='Escherichia coli CREC6' and row.raw_mic=='3.125'
    assert release.label_of(row.to_dict(),row.sequence)==int(row.derived_label)
    assert sha256(ROOT/row.primary_file)==release.FIGURE_SHA
    assert release.PISCIDIN_ID not in set(mol.sample_id)
    assert 'bmap2025:BMAP-27B' not in set(obs.record_id)


def test_source_figure_tampering_prevents_any_preparation(tmp_path,monkeypatch):
    image=tmp_path/'figure.jpeg';image.write_bytes(b'not the reviewed original')
    monkeypatch.setattr(release,'FIGURE',image)
    output=ROOT/'03_experiments/audits/test_no_output_from_tampered_figure'
    assert not output.exists()
    with pytest.raises(ValueError,match='figure/XML differs'):
        release.prepare(output)
    assert not output.exists()


def test_opposite_measurements_block_a_molecule():
    mol,obs,_,_,_=materials()
    row=obs[obs.sample_id.eq(release.BMAP_ID)].iloc[0].to_dict()
    other={**row,'record_id':'conflicting_measurement','raw_mic':'128','raw_unit':'µg/ml'}
    with pytest.raises(ValueError,match='Opposite measured labels'):
        release.ensure_consistent(pd.DataFrame([row,other]),mol.set_index('sample_id').seq.to_dict())


def test_duplicate_partition_roles_remain_blocked():
    mol,obs,src,roles,pairs=materials()
    duplicate=pd.concat([roles,roles[roles.role.eq('validation')].iloc[[0]]],ignore_index=True)
    result=release.audit_partition(mol,obs,src,duplicate,pairs)
    assert result['status']=='blocked'
    assert any('exactly one' in blocker or 'duplicates' in blocker for blocker in result['blockers'])


def test_changed_primary_study_relationship_is_rejected():
    mol,obs,src,roles,pairs=materials()
    bmap=obs.index[obs.sample_id.eq(release.BMAP_ID)][0]
    other=obs.index[~obs.sample_id.eq(release.BMAP_ID)][0]
    obs.loc[bmap,'assay_study_ids']=obs.loc[other,'assay_study_ids']
    with pytest.raises(ValueError,match='connected components differ'):
        release.audit_partition(mol,obs,src,roles,pairs)


def test_pair_coverage_cannot_be_representative_only():
    mol,obs,src,roles,pairs=materials()
    with pytest.raises(ValueError,match='pair audit differs'):
        release.audit_partition(mol,obs,src,roles,pairs.iloc[:-1])


def test_missing_freeze_refuses_training_before_fit(tmp_path):
    with pytest.raises(ValueError,match='Mandatory frozen protocol'):
        training.load(tmp_path/'missing-protocol.json',tmp_path/'missing-freeze.json')
