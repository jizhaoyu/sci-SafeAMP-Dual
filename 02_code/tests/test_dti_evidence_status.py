import importlib.util
import json
import hashlib
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def reader():
    path = ROOT / '05_web_server/dti_evidence.py'
    assert path.exists(), 'Dedicated model-independent evidence reader is required'
    spec = importlib.util.spec_from_file_location('dti_evidence_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_current_public_review_is_not_external_model_validation():
    data = reader().get_evidence_status()
    assert data['status'] == 'available'
    assert data['reviewed_count'] == 8
    assert data['confirmed_point_count'] == 5
    assert data['admitted_count'] == 5
    assert data['external_evaluation_completed'] is True
    assert data['external_metrics'] == {'mae': None, 'rmse': None, 'ci': None}
    assert sum(r['status'] == 'admitted' for r in data['candidates']) == 5
    assert sum(r['status'] == 'excluded' for r in data['candidates']) == 3


def test_f1_limitations_are_bound_to_existing_diagnosis_not_external_validation():
    data = reader().get_evidence_status()
    limits = data['model_diagnostics']['f1_ridge']
    source = ROOT / 'output/dti-f1-error-diagnosis-20261011/diagnosis.json'
    diagnosis = json.loads(source.read_text(encoding='utf-8'))
    assert limits['diagnosis_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert limits['high_affinity_count'] == diagnosis['pkd_bins'][-1]['n']
    assert abs(limits['high_affinity_mae_pkd'] - diagnosis['pkd_bins'][-1]['mae']) < 1e-10
    assert limits['scope'] == 'existing_DAVIS_diagnostic'
    manifest = json.loads((ROOT / '03_experiments/deployments/dti_f1_ridge_20261010_v1/manifest.json').read_text(encoding='utf-8'))
    assert limits['model_sha256'] == manifest['files']['model.joblib']
    assert data['external_evaluation_completed'] is True


def test_invalid_model_diagnostic_does_not_certify_external_validation(tmp_path):
    module = reader()
    data = module.get_evidence_status()
    data['model_diagnostics']['f1_ridge']['scope'] = 'external_validation'
    source = tmp_path / 'invalid-model-diagnostic.json'
    source.write_text(json.dumps(data), encoding='utf-8')
    assert module.get_evidence_status(source)['status'] == 'unavailable'

def test_missing_or_corrupt_source_is_unknown_not_zero_or_passed(tmp_path):
    module = reader()
    missing = module.get_evidence_status(tmp_path / 'missing.json')
    assert missing['status'] == 'unavailable'
    assert missing['reviewed_count'] is None
    assert missing['external_evaluation_completed'] is None
    path = tmp_path / 'corrupt.json'
    path.write_text('{broken', encoding='utf-8')
    assert module.get_evidence_status(path)['admitted_count'] is None

def test_inconsistent_counts_or_admitted_pending_record_fail_closed(tmp_path):
    module = reader()
    payload = json.loads(module.DEFAULT_SOURCE.read_text(encoding='utf-8'))
    payload['reviewed_count'] = 99
    path = tmp_path / 'inconsistent.json'
    path.write_text(json.dumps(payload), encoding='utf-8')
    assert module.get_evidence_status(path)['status'] == 'unavailable'
    payload['reviewed_count'] = 8
    payload['candidates'][0]['status'] = 'invalid_status'
    path.write_text(json.dumps(payload), encoding='utf-8')
    assert module.get_evidence_status(path)['status'] == 'unavailable'


def test_published_snapshot_matches_closed_review_source():
    data = reader().get_evidence_status()
    source = ROOT / 'output/dti-public-only-closure-20261011/scope_and_outcome.json'
    original = json.loads(source.read_text(encoding='utf-8'))
    assert hashlib.sha256(source.read_bytes()).hexdigest() == data['source_scope_sha256']
    assert [r['id'] for r in data['candidates']] == original['scope_record_ids']
    assert data['admitted_count'] == original['qualified_for_formal_evaluation']
    assert data['confirmed_point_count'] == original['value_points_primary_confirmed']


def test_http_evidence_route_does_not_load_or_predict(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    class ForbiddenRuntime:
        def load(self):
            raise AssertionError('Evidence HTTP route must not load models')

        def predict(self, *args, **kwargs):
            raise AssertionError('Evidence HTTP route must not run inference')

    stub = types.ModuleType('dti_inference_runtime')
    stub.DTIInferenceRuntime = ForbiddenRuntime
    monkeypatch.setitem(sys.modules, 'dti_inference_runtime', stub)
    monkeypatch.setitem(sys.modules, 'dti_evidence', reader())
    spec = importlib.util.spec_from_file_location('dti_endpoints_evidence_test', ROOT / '05_web_server/dti_endpoints.py')
    module = importlib.util.module_from_spec(spec)
    original_path = sys.path[:]
    try:
        spec.loader.exec_module(module)
        app = FastAPI()
        app.include_router(module.router)
        with TestClient(app) as client:
            response = client.get('/api/dti/evidence_status')
        assert response.status_code == 200
        assert response.json()['external_evaluation_completed'] is True
        assert response.json()['admitted_count'] == 5
        stub_report = types.ModuleType('dti_report_generator')
        stub_report.generate_dti_academic_report = lambda **kwargs: {'markdown_report': '# Template', 'html_report': '<html><body><h1>Template</h1></body></html>'}
        monkeypatch.setitem(sys.modules, 'dti_report_generator', stub_report)
        report = module.generate_dti_report(module.DTIAcademicReportRequest(baseline={}, candidates=[], model_used='f1_ridge'))
        assert report['model_used'] == 'f1_ridge'
        assert '外部证据复核准入已完成' in report['markdown_report']
        assert '模板默认值' in report['html_report']
        assert '缺少药物—靶点交互项' in report['markdown_report']
        assert report['html_report'].index('<aside') < report['html_report'].index('<h1>')
    finally:
        sys.path[:] = original_path
