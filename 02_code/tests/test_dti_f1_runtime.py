"""F1 web registration, exact features and inference alignment; never train."""
import csv
import json
from pathlib import Path

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
BUNDLE=ROOT/'03_experiments/deployments/dti_f1_ridge_20261010_v1'


def test_feature_extractors_match_all_frozen_f1_vectors():
    from extract_dti_davis_enhanced_features import extract_enhanced_drug_features,extract_enhanced_kinase_features
    from dti_f1_model import F1RidgePredictor
    predictor=F1RidgePredictor(BUNDLE).load()
    for identity,smiles in predictor.drug_smiles.items():
        np.testing.assert_array_equal(extract_enhanced_drug_features(smiles),predictor.drug_features[identity])
    for identity,sequence in predictor.target_sequences.items():
        np.testing.assert_array_equal(extract_enhanced_kinase_features(sequence),predictor.target_features[identity])


def test_fixed_pairs_replay_exactly_without_clamping():
    from dti_f1_model import F1RidgePredictor
    predictor=F1RidgePredictor(BUNDLE).load()
    with (BUNDLE/'reference_predictions.csv').open(encoding='utf-8',newline='') as stream:rows=list(csv.DictReader(stream))
    pairs=[(predictor.drug_smiles[r['drug_id']],predictor.target_sequences[r['target_id']]) for r in rows]
    predictions=predictor.predict_many(pairs)
    np.testing.assert_allclose(predictions,[float(r['predicted_pkd']) for r in rows],rtol=0,atol=2e-5)
    assert len(rows)==975


def test_new_inputs_use_bound_f1_pipeline_and_are_finite():
    from dti_f1_model import F1RidgePredictor
    predictor=F1RidgePredictor(BUNDLE).load()
    value=predictor.predict('CCO','ACDEFGHIKLMNPQRSTVWY'*5)
    assert np.isfinite(value)
    assert predictor.pair_features('CCO','ACDEFGHIKLMNPQRSTVWY'*5).shape==(2156,)


def test_artifact_change_is_rejected_before_model_load(tmp_path):
    import shutil
    from dti_f1_model import F1RidgePredictor
    target=tmp_path/'bundle';shutil.copytree(BUNDLE,target)
    with (target/'model.joblib').open('ab') as stream:stream.write(b'changed')
    with pytest.raises(ValueError,match='identity'):
        F1RidgePredictor(target).load()


def test_runtime_registers_f1_as_default_and_preserves_explicit_old_model():
    from dti_inference_runtime import DTIInferenceRuntime
    runtime=DTIInferenceRuntime();runtime.load()
    assert runtime.get_status()['default_model']=='f1_ridge'
    assert 'stacked_ensemble' in runtime.models
    predictor=runtime.f1_predictor
    row=next(csv.DictReader((BUNDLE/'reference_predictions.csv').open(encoding='utf-8',newline='')))
    result=runtime.predict(predictor.drug_smiles[row['drug_id']],predictor.target_sequences[row['target_id']])
    assert result['model_used']=='f1_ridge' and result['features_dim']==2156
    assert abs(result['predicted_pkd']-float(row['predicted_pkd']))<=.000051
    assert result['provenance']['model_sha256']==predictor.manifest['files']['model.joblib']
    assert runtime._resolve_model_name('stacked_ensemble')=='stacked_ensemble'
    assert result['domain']=='strict_dual_cold_test'
    assert result['domain_diagnosis_scope']=='benchmark_identity'


def test_model_catalog_has_one_recommendation_with_matching_metrics():
    import importlib.util
    spec=importlib.util.spec_from_file_location('f1_endpoint_tests',ROOT/'05_web_server/dti_endpoints.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    models=module.list_dti_models()
    recommended=[m for m in models if m['is_recommended']]
    assert len(recommended)==1 and recommended[0]['id']=='f1_ridge'
    model=recommended[0]
    assert model['feature_dimension']==2156 and model['seed']==123
    assert abs(model['dual_cold_ci']-.7244740915922354)<1e-10
    assert model['cold_drug_ci'] is None and model['cold_target_ci'] is None


def test_invalid_default_bundle_is_visible_and_not_silently_replaced(tmp_path):
    import shutil
    from dti_inference_runtime import DTIInferenceRuntime
    bundle=tmp_path/'invalid';shutil.copytree(BUNDLE,bundle)
    with (bundle/'model.joblib').open('ab') as stream:stream.write(b'changed')
    runtime=DTIInferenceRuntime();runtime.f1_bundle_dir=bundle;runtime.load()
    assert runtime.get_status()['status']=='degraded'
    with pytest.raises(ValueError,match='Default F1 model unavailable'):
        runtime._resolve_model_name(None)
    assert runtime._resolve_model_name('stacked_ensemble')=='stacked_ensemble'


def test_new_inputs_do_not_borrow_benchmark_metrics():
    from dti_inference_runtime import DTIInferenceRuntime
    runtime=DTIInferenceRuntime()
    result=runtime.predict('CCO','ACDEFGHIKLMNPQRSTVWY'*5)
    assert result['model_used']=='f1_ridge'
    assert result['domain_diagnosis_scope']=='similarity_heuristic'
    assert result['domain_benchmark_metrics']=={}


def test_api_batch_and_panel_keep_f1_default():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import importlib.util
    spec=importlib.util.spec_from_file_location('f1_batch_endpoint_tests',ROOT/'05_web_server/dti_endpoints.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    app=FastAPI();app.include_router(module.router);client=TestClient(app)
    module.dti_runtime.load();predictor=module.dti_runtime.f1_predictor
    drug=next(iter(predictor.drug_smiles.values()));sequence=next(iter(predictor.target_sequences.values()))
    response=client.post('/api/dti/predict_batch',json={'pairs':[
        {'drug_smiles':drug,'target_sequence':sequence},
        {'drug_smiles':'CCO','target_sequence':'ACDEFGHIKLMNPQRSTVWY'*5}]})
    assert response.status_code==200
    result=response.json()
    assert len(result)==2 and all(r['model_used']=='f1_ridge' for r in result)
    panel=client.post('/api/dti/profile_panel',json={'drug_smiles':drug})
    assert panel.status_code==200 and len(panel.json())>0
