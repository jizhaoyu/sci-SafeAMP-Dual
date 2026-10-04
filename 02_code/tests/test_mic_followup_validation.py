"""Refuse post-training corruption without fitting an estimator."""
import json
import shutil

import joblib
import numpy as np
import pytest

from research_utils import ROOT,sha256
from validate_mic_followup_run import declared_metrics,validate

RUN=ROOT/'03_experiments/runs/mic_followup_baseline_20261004_v1'
PROTOCOL=ROOT/'03_experiments/protocols/protocol-mic-11.json'
FREEZE=ROOT/'03_experiments/audits/protocol_mic_11_freeze_20261004_v1.json'


def test_declared_metric_schema_retains_all_frozen_columns():
    result=declared_metrics(np.asarray([0,1,0,1]),np.asarray([.1,.8,.2,.9]))
    assert result['AUROC']==result['AUPRC']==result['balanced_accuracy_at_0_5']==1
    assert set(result)=={'n','positive','negative','AUPRC','AUROC','MCC_at_0_5','balanced_accuracy_at_0_5','accuracy_at_0_5'}


def test_prediction_digest_corruption_is_rejected(tmp_path,monkeypatch):
    monkeypatch.chdir(ROOT)
    run=tmp_path/'run';shutil.copytree(RUN,run)
    with (run/'oof_predictions.csv').open('a',encoding='utf-8') as stream:stream.write('changed\n')
    with pytest.raises(ValueError,match='Run artifact changed'):
        validate(run,tmp_path/'verification.json',PROTOCOL,FREEZE)


def test_scaler_leakage_is_rejected_even_with_updated_artifact_hash(tmp_path,monkeypatch):
    monkeypatch.chdir(ROOT)
    run=tmp_path/'run';shutil.copytree(RUN,run)
    path=run/'fold_models/logistic_regression_fold0.joblib'
    pipeline=joblib.load(path)
    pipeline.steps[0][1].mean_[0]+=1
    joblib.dump(pipeline,path)
    manifest_path=run/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['outputs']['fold_models/logistic_regression_fold0.joblib']=sha256(path)
    manifest_path.write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(AssertionError,match='Not equal'):
        validate(run,tmp_path/'verification.json',PROTOCOL,FREEZE)


def test_new_protocol_is_bound_to_admitted_pretraining_state():
    protocol=json.loads(PROTOCOL.read_text(encoding='utf-8'))
    state_path=ROOT/protocol['readiness_state']
    state=json.loads(state_path.read_text(encoding='utf-8'))
    assert sha256(state_path)==protocol['readiness_state_sha256']
    assert state['status']=='ready_for_local_exploratory_training'
    assert not state['training_started'] and not state['training_blocked']
    assert state['evidence_molecules']==16 and state['evidence_observations']==23
