import sys
from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'02_code'));sys.path.insert(0,str(ROOT/'05_web_server'))
from inference_runtime import ResearchRuntime,ModelUnavailable
import research_api

def test_missing_configuration_never_looks_healthy():
    r=ResearchRuntime()
    assert r.status()['status']=='unavailable'
    assert not r.status()['dual_task_model']['weights_loaded']
    with pytest.raises(ModelUnavailable):r.load()

def test_unvalidated_run_rejected_before_model_loading(tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps({'status':'completed','dataset_manifest':{'status':'blocked'}}))
    with pytest.raises(ModelUnavailable,match='validation'):ResearchRuntime(tmp_path).load()

def test_checkpoint_integrity_rejected(tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps({'status':'completed','dataset_manifest':{'status':'validated'},'predictions_sha256':'bad'}))
    (tmp_path/'predictions.csv').write_text('not a validated prediction file')
    with pytest.raises(ModelUnavailable,match='checksum'):ResearchRuntime(tmp_path).load()

def test_api_failure_and_validation_are_explicit(monkeypatch):
    monkeypatch.setattr(research_api,'runtime',ResearchRuntime())
    client=TestClient(research_api.app)
    assert client.get('/api/system_status').json()['status']=='unavailable'
    seq='ACDEFGHIKLMNPQ'
    for route,body in [('/api/predict_batch',{'sequences':[seq]}),('/api/ai_optimize',{'sequence':seq}),('/api/ai_report',{'sequence':seq})]:
        response=client.post(route,json=body)
        assert response.status_code==503 and response.json()['detail']['code']=='MODEL_NOT_VALIDATED'
    assert client.post('/api/predict_batch',json={'sequences':[seq,'AKX123L']}).status_code==422
    assert client.post('/api/predict_batch',json={'sequences':[]}).status_code==422
    assert client.post('/api/helical_wheel',json={'sequence':seq}).status_code==200

def test_report_has_no_clinical_approval(monkeypatch):
    from ai_optimizer import AIPeptideOptimizer
    instance=object.__new__(AIPeptideOptimizer)
    monkeypatch.setattr(instance,'evaluate_sequence',lambda seq:(.8,.2,.64))
    result=instance.generate_scientific_report('ACDEFGHIKLMNPQ')
    assert result['tier_code']=='Research-only'
    assert result['attribution_type']=='physicochemical_heuristic'
    assert result['ai_mutation_solutions']==[]


def test_ui_and_invalid_routes_do_not_bypass_model_gate(monkeypatch):
    import app
    monkeypatch.setattr(research_api,'runtime',ResearchRuntime())
    client=TestClient(app.app)
    assert client.get('/').status_code==200
    assert client.get('/api/unknown').status_code==404
    assert client.post('/api/predict_batch',json={'sequences':['ADAD']}).status_code==422
    assert client.post('/api/predict_batch',json={'sequences':['A'*51]}).status_code==422
    assert client.post('/api/helical_wheel',json={'sequence':'A'*51}).status_code==422


def test_batch_jobs_api_routes(monkeypatch):
    import time
    from ai_optimizer import AIPeptideOptimizer

    monkeypatch.setattr(research_api, 'runtime', ResearchRuntime())
    client = TestClient(research_api.app)

    seq = 'ACDEFGHIKLMNPQ'
    # 503 when model is unavailable
    res = client.post('/api/batch_jobs', json={'sequences': [seq]})
    assert res.status_code == 503
    assert res.json()['detail']['code'] == 'MODEL_NOT_VALIDATED'

    # 422 for invalid sequences
    assert client.post('/api/batch_jobs', json={'sequences': [seq, 'AKX123L']}).status_code == 422
    assert client.post('/api/batch_jobs', json={'sequences': []}).status_code == 422

    # 404 for unknown jobs
    assert client.get('/api/batch_jobs/job-nonexistent').status_code == 404
    assert client.delete('/api/batch_jobs/job-nonexistent').status_code == 404

    # Now mock engine to simulate valid model
    instance = object.__new__(AIPeptideOptimizer)
    monkeypatch.setattr(instance, 'evaluate_sequence', lambda s: (0.85, 0.15, 0.70))
    monkeypatch.setattr(instance, 'compute_residue_attributions', lambda s: [])
    monkeypatch.setattr(research_api, 'engine', lambda: instance)

    post_res = client.post('/api/batch_jobs', json={'sequences': [seq, seq]})
    assert post_res.status_code == 200
    data = post_res.json()
    assert 'job_id' in data
    assert data['status'] == 'queued'
    assert data['total'] == 2
    job_id = data['job_id']

    # Wait for completion
    deadline = time.time() + 5.0
    status_data = None
    while time.time() < deadline:
        get_res = client.get(f'/api/batch_jobs/{job_id}')
        assert get_res.status_code == 200
        status_data = get_res.json()
        if status_data['status'] == 'completed':
            break
        time.sleep(0.02)

    assert status_data is not None
    assert status_data['status'] == 'completed'
    assert status_data['completed'] == 2
    assert status_data['failed_count'] == 0
    assert len(status_data['results']) == 2
    assert status_data['results'][0]['sequence'] == seq
    assert status_data['results'][0]['ranking_score'] == 0.70

    # Test cancel endpoint
    del_res = client.delete(f'/api/batch_jobs/{job_id}')
    assert del_res.status_code == 200
    assert del_res.json() == {'job_id': job_id, 'status': 'cancelled'}

