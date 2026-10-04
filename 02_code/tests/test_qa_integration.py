"""
test_qa_integration.py
Comprehensive QA & Integration Test Suite for SafeAMP-Dual Platform.
Covers API contracts, endpoint lifecycle, fuzzing, boundary cases, and concurrency.
"""

import concurrent.futures
import json
import os
from pathlib import Path
import sys
import time
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / '02_code') not in sys.path:
    sys.path.insert(0, str(ROOT / '02_code'))
if str(ROOT / '05_web_server') not in sys.path:
    sys.path.insert(0, str(ROOT / '05_web_server'))

import research_api
import app
import audit_logger
from inference_runtime import ResearchRuntime, ModelUnavailable
from ai_optimizer import AIPeptideOptimizer
from feature_extractor import clean_sequence, KYTE_DOOLITTLE, CHARGE_ESTIMATE


# Standard Benchmark Sequences
MELITTIN = "GIGAVLKVLTTGLPALISWIKRKRQQ"      # Length 26, highly amphipathic, net charge +5
MAGAININ2 = "GIGKFLHSAKKFGKAFVGEIMNS"       # Length 23, canonical antimicrobial peptide
SHORT_VALID_WHEEL = "ADAD"                   # Length 4, valid for helical wheel (3-50), invalid for model (10-50)


def create_mock_optimizer():
    """Create a fully compliant mock optimizer for validated runtime scenarios."""
    instance = object.__new__(AIPeptideOptimizer)
    instance.evaluate_sequence = lambda s: (0.8850, 0.1150, 0.7832)
    instance.compute_residue_attributions = lambda s: AIPeptideOptimizer.compute_residue_attributions(instance, s)
    instance.optimize_mutations = lambda s, top_k=3: [
        {
            "variant": s[:5] + "K" + s[6:],
            "mutation": f"{s[5]}6K",
            "amp_prob": 0.9200,
            "hemo_prob": 0.0800,
            "tsi": 0.8464,
            "tsi_gain": 0.0632,
            "hemo_probability_change": -0.0350,
            "rationale": "探索性突变候选，改善模型预测得分。",
            "validation_status": "exploratory_same_model_scoring"
        }
    ]
    instance.generate_scientific_report = lambda s: AIPeptideOptimizer.generate_scientific_report(instance, s)
    return instance


# ============================================================================
# 1. System Status Endpoint Tests
# ============================================================================

class TestSystemStatusEndpoint:
    """Contract tests for GET /api/system_status."""

    def test_system_status_unvalidated(self, monkeypatch):
        """Verify unvalidated system status response contract."""
        monkeypatch.setattr(research_api, 'runtime', ResearchRuntime())
        client = TestClient(research_api.app)
        res = client.get('/api/system_status')
        assert res.status_code == 200
        data = res.json()
        assert data['status'] == 'unavailable'
        assert data['dual_task_model']['weights_loaded'] is False
        assert data['dual_task_model']['status'] == 'Not validated'
        assert data['esm_model']['name'] == 'ESM-2 8M'
        assert data['mutation_engine']['status'] == 'Disabled'
        assert isinstance(data['provenance'], dict)

    def test_system_status_validated(self, monkeypatch):
        """Verify validated system status response contract when runtime is loaded."""
        mock_runtime = ResearchRuntime()
        mock_runtime.members = [("mock_model", {"seed": 11})]
        mock_runtime.metadata = {
            'run_id': 'validated_run_01',
            'backend': 'esm2_t6_8M',
            'feature_version': 'v1',
            'seeds': [11, 23, 42]
        }
        monkeypatch.setattr(research_api, 'runtime', mock_runtime)
        client = TestClient(research_api.app)
        res = client.get('/api/system_status')
        assert res.status_code == 200
        data = res.json()
        assert data['status'] == 'healthy'
        assert data['dual_task_model']['weights_loaded'] is True
        assert data['dual_task_model']['status'] == 'Validated'
        assert data['mutation_engine']['status'] == 'Ready'
        assert data['provenance']['run_id'] == 'validated_run_01'


# ============================================================================
# 2. Helical Wheel Endpoint Tests
# ============================================================================

class TestHelicalWheelEndpoint:
    """Contract and projection tests for POST /api/helical_wheel."""

    def test_melittin_wheel_projection(self):
        """Test valid Melittin sequence projection against physical chemistry rules."""
        client = TestClient(research_api.app)
        res = client.post('/api/helical_wheel', json={'sequence': MELITTIN})
        assert res.status_code == 200
        data = res.json()

        assert data['sequence'] == MELITTIN
        assert data['length'] == 26
        assert len(data['residues']) == 26
        assert data['hydrophobic_moment'] > 0.1
        assert 0.0 <= data['moment_angle_deg'] < 360.0
        assert data['net_charge'] == pytest.approx(5.0, abs=0.1)
        assert 'mean_hydrophobicity' in data
        assert 'hydrophobic_angle_span' in data

        # Check residue schema
        first = data['residues'][0]
        assert first['pos'] == 1
        assert first['aa'] == 'G'
        assert first['angle_deg'] == 0.0
        assert 'x' in first and 'y' in first
        assert 'category' in first
        assert 'color' in first

    def test_magainin2_wheel_projection(self):
        """Test valid Magainin-2 sequence projection."""
        client = TestClient(research_api.app)
        res = client.post('/api/helical_wheel', json={'sequence': MAGAININ2})
        assert res.status_code == 200
        data = res.json()

        assert data['sequence'] == MAGAININ2
        assert data['length'] == 23
        # Magainin-2 has K4, K10, K11, K14 (+4), E19 (-1), and H7 (+0.1) -> net charge +3.1
        assert data['net_charge'] == pytest.approx(3.1, abs=0.05)
        assert data['hydrophobic_moment'] > 0.0

    def test_helical_wheel_valid_boundary_lengths(self):
        """Helical wheel accepts sequences between 3 and 50 residues."""
        client = TestClient(research_api.app)
        # Min length 3
        res3 = client.post('/api/helical_wheel', json={'sequence': 'AAA'})
        assert res3.status_code == 200
        assert res3.json()['length'] == 3

        # Short peptide length 4
        res4 = client.post('/api/helical_wheel', json={'sequence': SHORT_VALID_WHEEL})
        assert res4.status_code == 200
        assert res4.json()['length'] == 4

        # Max length 50
        res50 = client.post('/api/helical_wheel', json={'sequence': 'A' * 50})
        assert res50.status_code == 200
        assert res50.json()['length'] == 50

    def test_helical_wheel_invalid_lengths(self):
        """Helical wheel rejects < 3 or > 50 residues with 422."""
        client = TestClient(research_api.app)
        # Length 1
        assert client.post('/api/helical_wheel', json={'sequence': 'A'}).status_code == 422
        # Length 2
        assert client.post('/api/helical_wheel', json={'sequence': 'AK'}).status_code == 422
        # Length 51
        res51 = client.post('/api/helical_wheel', json={'sequence': 'A' * 51})
        assert res51.status_code == 422
        assert 'supports 3–50' in res51.json()['detail']
        # Length 100
        assert client.post('/api/helical_wheel', json={'sequence': 'A' * 100}).status_code == 422
        # Length 1000
        assert client.post('/api/helical_wheel', json={'sequence': 'A' * 1000}).status_code == 422

    def test_helical_wheel_invalid_characters(self):
        """Helical wheel rejects non-canonical amino acids with 422."""
        client = TestClient(research_api.app)
        for char in ['B', 'Z', 'X', 'U', '1', '!', '@', '#', '$']:
            bad_seq = f"GIGAVLKV{char}TTGLPALISWIKRKRQQ"
            res = client.post('/api/helical_wheel', json={'sequence': bad_seq})
            assert res.status_code == 422
            assert 'Noncanonical' in res.json()['detail']


# ============================================================================
# 3. Predict Batch Endpoint Tests
# ============================================================================

class TestPredictBatchEndpoint:
    """Contract tests for POST /api/predict_batch."""

    def test_predict_batch_unvalidated_503(self, monkeypatch):
        """Unvalidated runtime must fail-closed with HTTP 503."""
        monkeypatch.setattr(research_api, 'runtime', ResearchRuntime())
        client = TestClient(research_api.app)
        res = client.post('/api/predict_batch', json={'sequences': [MELITTIN, MAGAININ2]})
        assert res.status_code == 503
        data = res.json()
        assert data['detail']['code'] == 'MODEL_NOT_VALIDATED'

    def test_predict_batch_empty_list_422(self):
        """Empty sequence list must be rejected with 422."""
        client = TestClient(research_api.app)
        res = client.post('/api/predict_batch', json={'sequences': []})
        assert res.status_code == 422

    def test_predict_batch_invalid_residue_with_index(self):
        """Sequence with invalid residue returns 422 with index in error message."""
        client = TestClient(research_api.app)
        res = client.post('/api/predict_batch', json={'sequences': [MELITTIN, "ACDEFGHIBKLMNPQ"]})
        assert res.status_code == 422
        detail = res.json()['detail']
        assert 'Sequence at index 1' in detail
        assert 'Noncanonical' in detail

    def test_predict_batch_domain_limits_10_to_50(self):
        """Model domain strictly enforces 10–50 residues."""
        client = TestClient(research_api.app)
        # Length 4 (< 10)
        res_short = client.post('/api/predict_batch', json={'sequences': [SHORT_VALID_WHEEL]})
        assert res_short.status_code == 422
        assert 'Sequence at index 0' in res_short.json()['detail']
        assert 'Research model domain is 10–50' in res_short.json()['detail']

        # Length 9 (< 10)
        res_9 = client.post('/api/predict_batch', json={'sequences': ['A' * 9]})
        assert res_9.status_code == 422
        assert 'Research model domain is 10–50' in res_9.json()['detail']

        # Length 51 (> 50)
        res_51 = client.post('/api/predict_batch', json={'sequences': ['A' * 51]})
        assert res_51.status_code == 422
        assert 'Research model domain is 10–50' in res_51.json()['detail']

    def test_predict_batch_validated_200(self, monkeypatch):
        """Validated model produces full contract outputs."""
        optimizer = create_mock_optimizer()
        monkeypatch.setattr(research_api, 'engine', lambda: optimizer)
        client = TestClient(research_api.app)

        res = client.post('/api/predict_batch', json={'sequences': [MELITTIN, MAGAININ2]})
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 2

        item = items[0]
        assert item['sequence'] == MELITTIN
        assert item['length'] == 26
        assert 0.0 <= item['amp_probability'] <= 1.0
        assert 0.0 <= item['hemo_probability'] <= 1.0
        assert 'ranking_score' in item
        assert 'therapeutic_safety_index' in item
        assert item['is_safe'] is None
        assert item['attribution_type'] == 'physicochemical_heuristic'
        assert isinstance(item['residues'], list)
        assert len(item['residues']) == 26
        assert 'warning' in item
        assert 'Research prediction; no clinical safety' in item['warning']


# ============================================================================
# 4. Async Batch Jobs Endpoint Tests
# ============================================================================

class TestBatchJobsEndpoints:
    """Contract tests for POST/GET/DELETE /api/batch_jobs."""

    def test_batch_jobs_unvalidated_503(self, monkeypatch):
        """Unvalidated runtime fails-closed on job submission."""
        monkeypatch.setattr(research_api, 'runtime', ResearchRuntime())
        client = TestClient(research_api.app)
        res = client.post('/api/batch_jobs', json={'sequences': [MELITTIN]})
        assert res.status_code == 503
        assert res.json()['detail']['code'] == 'MODEL_NOT_VALIDATED'

    def test_batch_jobs_invalid_inputs_422(self):
        """Invalid inputs rejected during submission."""
        client = TestClient(research_api.app)
        assert client.post('/api/batch_jobs', json={'sequences': []}).status_code == 422
        assert client.post('/api/batch_jobs', json={'sequences': ['AK']}).status_code == 422
        assert client.post('/api/batch_jobs', json={'sequences': [MELITTIN, 'INVALID!RESIDUE']}).status_code == 422

    def test_batch_jobs_lifecycle_and_cancellation(self, monkeypatch):
        """Test full async lifecycle: submission -> polling progress -> cancel."""
        optimizer = create_mock_optimizer()
        monkeypatch.setattr(research_api, 'engine', lambda: optimizer)
        client = TestClient(research_api.app)

        # 1. Submit async job
        post_res = client.post('/api/batch_jobs', json={'sequences': [MELITTIN, MAGAININ2]})
        assert post_res.status_code == 200
        data = post_res.json()
        assert 'job_id' in data
        assert data['status'] == 'queued'
        assert data['total'] == 2
        job_id = data['job_id']

        # 2. Poll job status
        deadline = time.time() + 5.0
        final_status = None
        while time.time() < deadline:
            get_res = client.get(f'/api/batch_jobs/{job_id}')
            assert get_res.status_code == 200
            status_info = get_res.json()
            if status_info['status'] == 'completed':
                final_status = status_info
                break
            time.sleep(0.02)

        assert final_status is not None
        assert final_status['status'] == 'completed'
        assert final_status['completed'] == 2
        assert final_status['failed_count'] == 0
        assert len(final_status['results']) == 2
        assert final_status['results'][0]['sequence'] == MELITTIN

        # 3. Cancel job endpoint
        del_res = client.delete(f'/api/batch_jobs/{job_id}')
        assert del_res.status_code == 200
        assert del_res.json() == {'job_id': job_id, 'status': 'cancelled'}

    def test_batch_jobs_not_found_404(self):
        """Non-existent job ID returns 404."""
        client = TestClient(research_api.app)
        assert client.get('/api/batch_jobs/job-unknown-9999').status_code == 404
        assert client.delete('/api/batch_jobs/job-unknown-9999').status_code == 404


# ============================================================================
# 5. AI Optimize Endpoint Tests
# ============================================================================

class TestAiOptimizeEndpoint:
    """Contract tests for POST /api/ai_optimize."""

    def test_ai_optimize_unvalidated_503(self, monkeypatch):
        """Fails closed when unvalidated."""
        monkeypatch.setattr(research_api, 'runtime', ResearchRuntime())
        client = TestClient(research_api.app)
        assert client.post('/api/ai_optimize', json={'sequence': MELITTIN}).status_code == 503

    def test_ai_optimize_invalid_inputs_422(self):
        """Input boundary and character validation."""
        client = TestClient(research_api.app)
        assert client.post('/api/ai_optimize', json={'sequence': SHORT_VALID_WHEEL}).status_code == 422
        assert client.post('/api/ai_optimize', json={'sequence': 'A' * 51}).status_code == 422
        assert client.post('/api/ai_optimize', json={'sequence': 'AKX123LMNOP'}).status_code == 422

    def test_ai_optimize_validated_200(self, monkeypatch):
        """Verified mutation suggestions contract."""
        optimizer = create_mock_optimizer()
        monkeypatch.setattr(research_api, 'engine', lambda: optimizer)
        client = TestClient(research_api.app)

        res = client.post('/api/ai_optimize', json={'sequence': MELITTIN})
        assert res.status_code == 200
        data = res.json()
        assert data['status'] == 'exploratory'
        assert data['original_sequence'] == MELITTIN
        assert isinstance(data['solutions'], list)
        assert len(data['solutions']) >= 1
        sol = data['solutions'][0]
        assert 'variant' in sol
        assert 'mutation' in sol
        assert 'amp_prob' in sol
        assert 'hemo_prob' in sol
        assert 'tsi' in sol
        assert 'warning' in data
        assert 'Same-model ranking is not independent' in data['warning']


# ============================================================================
# 6. AI Report Endpoint Tests
# ============================================================================

class TestAiReportEndpoint:
    """Contract tests for POST /api/ai_report."""

    def test_ai_report_unvalidated_503(self, monkeypatch):
        """Fails closed when unvalidated."""
        monkeypatch.setattr(research_api, 'runtime', ResearchRuntime())
        client = TestClient(research_api.app)
        assert client.post('/api/ai_report', json={'sequence': MELITTIN}).status_code == 503

    def test_ai_report_invalid_inputs_422(self):
        """Input boundary validation."""
        client = TestClient(research_api.app)
        assert client.post('/api/ai_report', json={'sequence': SHORT_VALID_WHEEL}).status_code == 422
        assert client.post('/api/ai_report', json={'sequence': 'A' * 51}).status_code == 422

    def test_ai_report_validated_contract(self, monkeypatch):
        """Verifies report structure conforms to scientific publication standards."""
        optimizer = create_mock_optimizer()
        monkeypatch.setattr(research_api, 'engine', lambda: optimizer)
        client = TestClient(research_api.app)

        res = client.post('/api/ai_report', json={'sequence': MELITTIN})
        assert res.status_code == 200
        data = res.json()

        assert 'report_id' in data
        assert data['sequence'] == MELITTIN
        assert data['tier_code'] == 'Research-only'
        assert data['clinical_tier'] == 'Not clinically validated'
        assert data['disposition_badge'] == 'warning'
        assert data['attribution_type'] == 'physicochemical_heuristic'
        assert 'metrics' in data
        assert 'standard_markdown_report' in data
        assert 'Computational research report' in data['standard_markdown_report']

    def test_ai_report_external_privacy_guarantee(self, monkeypatch):
        """Passing an external API key must NOT trigger remote sequence leak."""
        optimizer = create_mock_optimizer()
        monkeypatch.setattr(research_api, 'engine', lambda: optimizer)
        client = TestClient(research_api.app)

        res = client.post('/api/ai_report', json={
            'sequence': MELITTIN,
            'api_key': 'sk-test-secret-key-12345',
            'model_name': 'gpt-4o'
        })
        assert res.status_code == 200
        data = res.json()
        assert 'custom_llm_error' in data
        assert 'no sequence was sent externally' in data['custom_llm_error']


# ============================================================================
# 7. Static File Serving Tests
# ============================================================================

class TestStaticFileServing:
    """Verifies static asset and SPA index file serving from app.py."""

    def test_frontend_routes(self):
        """Test GET /, /wheel, /evolution, /report serving index.html."""
        client = TestClient(app.app)
        for route in ['/', '/wheel', '/evolution', '/report']:
            res = client.get(route)
            assert res.status_code == 200
            assert 'text/html' in res.headers.get('content-type', '')
            assert '<!doctype html>' in res.text.lower() or '<div id="root">' in res.text.lower()

    def test_favicon_route(self):
        """Test GET /favicon.ico returns 204 No Content."""
        client = TestClient(app.app)
        res = client.get('/favicon.ico')
        assert res.status_code == 204

    def test_static_nonexistent_route_404(self):
        """Non-existent API route returns 404."""
        client = TestClient(app.app)
        assert client.get('/api/completely_invalid_route').status_code == 404


# ============================================================================
# 8. Boundary & Fuzzing Edge Cases
# ============================================================================

class TestBoundaryAndFuzzing:
    """Systematic boundary checking and fuzzing for sequence validation."""

    def test_extremely_short_sequences(self):
        """1-2 residues and whitespace-only must be rejected."""
        client = TestClient(research_api.app)
        short_inputs = ["", "A", "AK", " \t\n ", "   A   ", "  AK \t "]
        for inp in short_inputs:
            # Helical wheel rejected
            res_wheel = client.post('/api/helical_wheel', json={'sequence': inp})
            assert res_wheel.status_code == 422, f"Failed for input: {repr(inp)}"
            # Batch predict rejected
            res_batch = client.post('/api/predict_batch', json={'sequences': [inp]})
            assert res_batch.status_code == 422, f"Failed for input: {repr(inp)}"

    def test_domain_differential_acceptance(self, monkeypatch):
        """
        Verify domain differences:
        - 3–9 residues: accepted by Helical Wheel (3-50), rejected by Model (10-50).
        - 10–50 residues: accepted by both.
        - > 50 residues: rejected by both.
        """
        optimizer = create_mock_optimizer()
        monkeypatch.setattr(research_api, 'engine', lambda: optimizer)
        client = TestClient(research_api.app)

        # 1. Length 3-9 (e.g. Length 3, 4, 9)
        for length in [3, 4, 9]:
            seq = "A" * length
            # Wheel accepts
            res_w = client.post('/api/helical_wheel', json={'sequence': seq})
            assert res_w.status_code == 200, f"Wheel failed for len {length}"
            # Model rejects
            res_m = client.post('/api/predict_batch', json={'sequences': [seq]})
            assert res_m.status_code == 422, f"Model failed to reject len {length}"
            assert 'Research model domain is 10–50' in res_m.json()['detail']

        # 2. Length 10-50 (e.g. Length 10, 26, 50)
        for length in [10, 26, 50]:
            seq = "A" * length
            assert client.post('/api/helical_wheel', json={'sequence': seq}).status_code == 200
            assert client.post('/api/predict_batch', json={'sequences': [seq]}).status_code == 200

        # 3. Length > 50 (e.g. Length 51, 100, 1000)
        for length in [51, 100, 1000]:
            seq = "A" * length
            assert client.post('/api/helical_wheel', json={'sequence': seq}).status_code == 422
            assert client.post('/api/predict_batch', json={'sequences': [seq]}).status_code == 422

    def test_noncanonical_character_fuzzing(self):
        """Fuzz testing with 34 non-canonical characters injected at various positions."""
        client = TestClient(research_api.app)
        fuzz_chars = [
            'B', 'Z', 'X', 'U', 'O', 'J',  # Non-standard amino acids
            '0', '1', '2', '8', '9',        # Numeric digits
            '!', '@', '#', '$', '%', '^',   # Symbols
            '&', '*', '(', ')', '_', '+',
            '=', '-', '?', '/', '<', '>',
            '~', '`', ';', ':', '"', "'"
        ]
        base = "GIGAVLKVLTTGLPALISWIKRKRQQ"
        for fc in fuzz_chars:
            # Prefix injection
            bad_seq_pre = fc + base[1:]
            assert client.post('/api/helical_wheel', json={'sequence': bad_seq_pre}).status_code == 422
            # Middle injection
            bad_seq_mid = base[:10] + fc + base[11:]
            assert client.post('/api/helical_wheel', json={'sequence': bad_seq_mid}).status_code == 422
            # Suffix injection
            bad_seq_suf = base[:-1] + fc
            assert client.post('/api/helical_wheel', json={'sequence': bad_seq_suf}).status_code == 422

    def test_whitespace_and_newline_normalization(self, monkeypatch):
        """Sequences with messy whitespace/tabs/newlines/lowercase must normalize cleanly."""
        optimizer = create_mock_optimizer()
        monkeypatch.setattr(research_api, 'engine', lambda: optimizer)
        client = TestClient(research_api.app)

        messy_seq = "  \n\t gigavl \n\r kvltt \t\t glpaliswikrkrqq \r\n "
        # Helical wheel
        res_w = client.post('/api/helical_wheel', json={'sequence': messy_seq})
        assert res_w.status_code == 200
        assert res_w.json()['sequence'] == MELITTIN

        # Predict batch
        res_m = client.post('/api/predict_batch', json={'sequences': [messy_seq]})
        assert res_m.status_code == 200
        assert res_m.json()[0]['sequence'] == MELITTIN


# ============================================================================
# 9. Concurrency & Thread-Lock Robustness
# ============================================================================

class TestConcurrencyAndThreadLocks:
    """Stress testing thread safety across audit logging, batch manager, and API."""

    def test_concurrent_api_requests_and_audit_logging(self, tmp_path, monkeypatch):
        """50 concurrent requests hitting multiple endpoints simultaneously."""
        test_audit_file = tmp_path / "test_api_audit.jsonl"
        monkeypatch.setattr(audit_logger, 'AUDIT_LOG_FILE', test_audit_file)

        optimizer = create_mock_optimizer()
        monkeypatch.setattr(research_api, 'engine', lambda: optimizer)
        client = TestClient(research_api.app)

        def worker(req_idx: int):
            client_req_id = f"custom-trace-{req_idx:04d}"
            # Rotate across endpoints
            endpoint_choice = req_idx % 4
            if endpoint_choice == 0:
                res = client.get('/api/system_status', headers={'X-Request-ID': client_req_id})
            elif endpoint_choice == 1:
                res = client.post('/api/helical_wheel', json={'sequence': MELITTIN}, headers={'X-Request-ID': client_req_id})
            elif endpoint_choice == 2:
                res = client.post('/api/predict_batch', json={'sequences': [MELITTIN, MAGAININ2]}, headers={'X-Request-ID': client_req_id})
            else:
                res = client.post('/api/batch_jobs', json={'sequences': [MELITTIN]}, headers={'X-Request-ID': client_req_id})

            assert res.status_code == 200
            assert res.headers.get('X-Request-ID') == client_req_id
            return res.status_code

        # Run 50 concurrent requests across 10 threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 50
        assert all(code == 200 for code in results)

        # Verify audit log integrity
        assert test_audit_file.is_file()
        audit_entries = audit_logger.read_audit_logs(test_audit_file)
        assert len(audit_entries) == 50
        # Check all custom request IDs are captured
        captured_ids = {e['request_id'] for e in audit_entries}
        expected_ids = {f"custom-trace-{i:04d}" for i in range(50)}
        assert captured_ids == expected_ids


if __name__ == '__main__':
    pytest.main([__file__, "-v", "-p", "no:cacheprovider"])
