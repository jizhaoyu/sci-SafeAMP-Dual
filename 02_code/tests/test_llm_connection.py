"""Connection checks never send research inputs or release research readiness."""
import io
import json
from pathlib import Path
import sys
import urllib.error

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '02_code'))
sys.path.insert(0, str(ROOT / '05_web_server'))
import llm_connection as connection
import research_api

KEY = 'sk-fixture-secret-do-not-log'
CONFIG = {'provider': 'deepseek', 'api_key': KEY, 'base_url': 'https://api.deepseek.com/v1', 'model_name': 'deepseek-chat'}


def response_body():
    return {'id': 'fixture-id', 'object': 'chat.completion', 'model': 'fixture-returned-model',
            'choices': [{'message': {'role': 'assistant', 'content': 'API_CONNECTION_OK'}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}


def install_response(monkeypatch, body=None):
    class Response(io.BytesIO):
        status = 200

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == 'https://api.deepseek.com/v1/chat/completions'
            assert timeout == 45
            payload = json.loads(request.data)
            assert set(payload) == {'model', 'temperature', 'stream', 'max_tokens', 'messages'}
            assert payload['messages'] == [{'role': 'user', 'content': 'Return exactly API_CONNECTION_OK. No other text.'}]
            assert payload['max_tokens'] == 32 and payload['temperature'] == 0 and payload['stream'] is False
            return Response(json.dumps(body if body is not None else response_body()).encode())

    monkeypatch.setattr(connection.urllib.request, 'build_opener', lambda *args: Opener())


@pytest.mark.parametrize('base', ['http://api.deepseek.com/v1', 'https://api.deepseek.com.evil/v1',
                                  'https://user:pass@api.deepseek.com/v1', 'https://127.0.0.1/v1',
                                  'https://api.deepseek.com:443/v1', 'https://api.deepseek.com/v1?key=secret'])
def test_nonofficial_endpoints_rejected_before_network(base):
    with pytest.raises(connection.ConnectionCheckError) as error:
        connection.check_connection({**CONFIG, 'base_url': base})
    assert error.value.code == 'INVALID_ENDPOINT'


@pytest.mark.parametrize('field,value,code', [('provider', 'anthropic', 'UNSUPPORTED_PROVIDER'),
                                            ('api_key', '', 'INVALID_KEY'),
                                            ('api_key', 'secret\r\nheader', 'INVALID_KEY'),
                                            ('model_name', '', 'INVALID_MODEL')])
def test_invalid_config(field, value, code):
    with pytest.raises(connection.ConnectionCheckError) as error:
        connection.check_connection({**CONFIG, field: value})
    assert error.value.code == code
    assert KEY not in str(error.value)


def test_success_returns_metadata_not_key(monkeypatch):
    install_response(monkeypatch)
    result = connection.check_connection(CONFIG)
    assert result['returned_model'] == 'fixture-returned-model'
    assert result['requested_model'] == 'deepseek-chat'
    assert result['scope'] == 'neutral_connectivity_only'
    assert result['duration_seconds_full_response'] >= 0
    assert KEY not in json.dumps(result)


@pytest.mark.parametrize('change', ['marker', 'finish', 'usage', 'empty', 'huge'])
def test_invalid_response_is_not_success(monkeypatch, change):
    body = response_body()
    if change == 'marker': body['choices'][0]['message']['content'] = 'some other output'
    if change == 'finish': body['choices'][0]['finish_reason'] = 'length'
    if change == 'usage': body['usage']['total_tokens'] = 999
    if change == 'empty': body = {}
    if change == 'huge': body['extra'] = 'x' * 70000
    install_response(monkeypatch, body)
    with pytest.raises(connection.ConnectionCheckError) as error:
        connection.check_connection(CONFIG)
    assert error.value.code == 'INVALID_PROVIDER_RESPONSE'


@pytest.mark.parametrize('status,code', [(401, 'AUTH_FAILED'), (402, 'INSUFFICIENT_BALANCE'),
                                      (403, 'ACCESS_DENIED'), (404, 'MODEL_NOT_FOUND'),
                                      (429, 'PROVIDER_RATE_LIMITED'), (302, 'PROVIDER_ERROR')])
def test_provider_error_does_not_echo_body(monkeypatch, status, code):
    class Opener:
        def open(self, *args, **kwargs):
            raise urllib.error.HTTPError('https://api.deepseek.com', status, KEY, {}, io.BytesIO(KEY.encode()))
    monkeypatch.setattr(connection.urllib.request, 'build_opener', lambda *args: Opener())
    with pytest.raises(connection.ConnectionCheckError) as error:
        connection.check_connection(CONFIG)
    assert error.value.code == code and KEY not in str(error.value)


def test_timeout_and_global_concurrency_limit(monkeypatch):
    class Opener:
        def open(self, *args, **kwargs): raise TimeoutError(KEY)
    monkeypatch.setattr(connection.urllib.request, 'build_opener', lambda *args: Opener())
    with pytest.raises(connection.ConnectionCheckError) as error:
        connection.check_connection(CONFIG)
    assert error.value.code == 'PROVIDER_TIMEOUT'
    assert connection._slots.acquire(False) and connection._slots.acquire(False)
    try:
        with pytest.raises(connection.ConnectionCheckError) as error:
            connection.check_connection(CONFIG)
        assert error.value.code == 'TEST_BUSY'
    finally:
        connection._slots.release(); connection._slots.release()


def test_api_does_not_release_gate_and_logs_no_key(monkeypatch, tmp_path):
    import audit_logger
    monkeypatch.setattr(audit_logger, 'AUDIT_LOG_FILE', tmp_path / 'api.jsonl')
    monkeypatch.setattr(research_api, 'runtime', research_api.DTISystemStatus())
    install_response(monkeypatch)
    client = TestClient(research_api.app)
    result = client.post('/api/llm/test_connection', json=CONFIG)
    assert result.status_code == 200 and result.headers['cache-control'] == 'no-store'
    assert client.get('/api/ready').status_code == 503
    assert KEY not in (tmp_path / 'api.jsonl').read_text()
    for body in [[], {**CONFIG, 'model_name': {'api_key': KEY}}, {**CONFIG, 'sequence': 'RESEARCH'}]:
        result = client.post('/api/llm/test_connection', json=body)
        assert result.status_code == 422 and KEY not in result.text
    result = client.post('/api/llm/test_connection', content=KEY)
    assert result.status_code == 422 and KEY not in result.text
    result = client.post('/api/llm/test_connection', content='x' * 8193)
    assert result.status_code == 413


def test_official_openai_endpoint_and_rate_limit():
    key, endpoint, model = connection.validate_config({**CONFIG, 'provider': 'openai', 'base_url': 'https://api.openai.com/v1', 'model_name': 'gpt-4o'})
    assert endpoint == 'https://api.openai.com/v1/chat/completions' and key == KEY and model == 'gpt-4o'
    limiter = research_api.SlidingWindowRateLimiter()
    for _ in range(6): assert limiter.check_rate_limit('fixture-ip', '/api/llm/test_connection')[0]
    assert not limiter.check_rate_limit('fixture-ip', '/api/llm/test_connection')[0]


def test_custom_and_local_provider_validation():
    # Custom provider endpoint normalization
    k1, ep1, m1 = connection.validate_config({
        'provider': 'custom',
        'api_key': KEY,
        'base_url': 'https://vip.auto-code.net/v1',
        'model_name': 'grok-4.6'
    })
    assert ep1 == 'https://vip.auto-code.net/v1/chat/completions'
    assert m1 == 'grok-4.6' and k1 == KEY

    # Ollama endpoint normalization (HTTP + port)
    k2, ep2, m2 = connection.validate_config({
        'provider': 'ollama',
        'api_key': 'dummy_key',
        'base_url': 'http://localhost:11434/v1',
        'model_name': 'llama3:latest'
    })
    assert ep2 == 'http://localhost:11434/v1/chat/completions'
    assert m2 == 'llama3:latest'


def test_custom_provider_connection_success(monkeypatch):
    class Response(io.BytesIO):
        status = 200

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == 'https://vip.auto-code.net/v1/chat/completions'
            # Custom provider response may omit full usage or have diverse assistant text
            body = {
                'id': 'chatcmpl-test',
                'object': 'chat.completion',
                'model': 'grok-4.6',
                'choices': [{'message': {'role': 'assistant', 'content': 'API_CONNECTION_OK.'}, 'finish_reason': 'stop'}],
                'usage': {'total_tokens': 12}
            }
            return Response(json.dumps(body).encode())

    monkeypatch.setattr(connection.urllib.request, 'build_opener', lambda *args: Opener())
    res = connection.check_connection({
        'provider': 'custom',
        'api_key': KEY,
        'base_url': 'https://vip.auto-code.net/v1',
        'model_name': 'grok-4.6'
    })
    assert res['status'] == 'connected'
    assert res['requested_model'] == 'grok-4.6'
    assert res['returned_model'] == 'grok-4.6'
    assert res['provider'] == 'custom'
    assert res['usage']['total_tokens'] == 12


def test_custom_provider_error_detail_surfaced(monkeypatch):
    err_json = json.dumps({'error': {'message': 'No compatible upstream account is currently available.'}})
    class Opener:
        def open(self, *args, **kwargs):
            raise urllib.error.HTTPError('https://vip.auto-code.net/v1', 503, 'Unavailable', {}, io.BytesIO(err_json.encode()))

    monkeypatch.setattr(connection.urllib.request, 'build_opener', lambda *args: Opener())
    with pytest.raises(connection.ConnectionCheckError) as exc:
        connection.check_connection({
            'provider': 'custom',
            'api_key': KEY,
            'base_url': 'https://vip.auto-code.net/v1',
            'model_name': 'grok-4.6'
        })
    assert exc.value.status == 502
    assert 'No compatible upstream account' in exc.value.message

