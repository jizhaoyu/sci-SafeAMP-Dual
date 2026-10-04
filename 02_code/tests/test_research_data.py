import sys
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from public_data import bounds, measurement_label, extract_record
from research_data import ResearchDataError, validate_records, consolidate_records, homology_components, assert_cross_isolation, sequence_identity

def record(**kw):
    row=dict(record_id='source:1',seq='ACDEFGHIKLMN',amp=1,hemo=np.nan,source_dataset='study',source_accession='1',
             source_url='https://example.org/source',evidence_reference='PMID:1',label_basis='measured',assay_conditions='reported',
             modifications='none',evidence_type='experimental',is_synthetic=False,source_role='development',raw_path='source.json',raw_sha256='test')
    return {**row,**kw}

def test_missing_labels_remain_missing():
    df=validate_records(pd.DataFrame([record()]),verify_raw=False)
    assert pd.isna(df.hemo.iloc[0])
    assert df.amp_observed.iloc[0] and not df.hemo_observed.iloc[0]


def test_observed_flags_cannot_hide_known_labels():
    with pytest.raises(ResearchDataError,match='flag'):
        validate_records(pd.DataFrame([record(amp_observed=False)]),verify_raw=False)


def test_identity_is_symmetric_for_traceback_ties():
    rng=np.random.default_rng(42)
    for _ in range(30):
        a=''.join(rng.choice(list('ACDE'),12));b=''.join(rng.choice(list('ACDE'),18))
        assert sequence_identity(a,b)==sequence_identity(b,a)

@pytest.mark.parametrize('change',[{'is_synthetic':True},{'evidence_type':'unannotated'},{'modifications':'amidated'},{'amp':2},{'source_accession':''}])
def test_unsupported_evidence_is_rejected(change):
    with pytest.raises(ValueError):validate_records(pd.DataFrame([record(**change)]),verify_raw=False)

def test_conflicts_are_not_silently_voted():
    df=validate_records(pd.DataFrame([record(hemo=0),record(record_id='source:2',amp=0,hemo=0)]),verify_raw=False)
    merged,_=consolidate_records(df)
    assert pd.isna(merged.amp.iloc[0]) and merged.hemo.iloc[0]==0

def test_external_exact_overlap_is_excluded():
    df=pd.DataFrame([record(),record(record_id='b',source_role='external')])
    merged,excluded=consolidate_records(df)
    assert merged.empty and len(excluded)==1

def test_connected_components_capture_nonrepresentative_link():
    seqs=['A'*10,'A'*6+'C'*4,'C'*10]
    groups,_=homology_components(seqs,.4)
    assert len(set(groups))==1
    assert sequence_identity(seqs[0],seqs[2])==0

def test_cross_set_violation_blocks():
    a=pd.DataFrame([dict(sample_id='a',seq='A'*10)])
    b=pd.DataFrame([dict(sample_id='b',seq='A'*6+'C'*4)])
    with pytest.raises(ResearchDataError):assert_cross_isolation(a,b)

@pytest.mark.parametrize('value,expected',[('32',(32.,32.)),('>128',(128.,float('inf'))),('<4',(0.,4.)),('4-8',(4.,8.)),('unknown',None),('2±1',None)])
def test_censoring_and_ranges(value,expected):assert bounds(value)==expected

def test_interval_label_and_unit_conversion():
    assay={'unit':{'name':'µg/ml'},'concentration':'16-64'}
    assert measurement_label(assay,'ACDEFGHIKLMN',32,128) is None
    assay['concentration']='>128'
    assert measurement_label(assay,'ACDEFGHIKLMN',32,128)==0
    assay['unit']['name']='unsupported'
    assert measurement_label(assay,'ACDEFGHIKLMN',32,128) is None
