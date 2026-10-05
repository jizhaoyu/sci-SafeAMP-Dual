"""Version scopes cannot turn legacy incompatibility into a full-project pass."""
import json
import os
import subprocess
import sys

import pytest
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import check_mic_project as checker
from research_utils import ROOT, read_json


@pytest.fixture(scope='module')
def current_report():
    return checker.check_project(scope='current')


def test_actual_current_gates_pass_with_visible_legacy_incompatibility(current_report):
    assert current_report['status'] == 'passed'
    current = current_report['current_delivery']
    assert current['documents_verified'] == 5
    assert current['offline_validation']['models_reloaded'] == 9
    assert current['offline_validation']['oof_rows_independently_recomputed'] == 51
    assert current['offline_validation']['fit_calls_during_validation'] == 0
    assert current_report['legacy_documents']['status'] == 'incompatible'
    assert current_report['legacy_documents']['current_inventory'] == [17, 42]
    assert current_report['scientific_status']['mic_training_blocked'] is False
    assert current_report['scientific_status']['formal_dual_task_status'] == 'blocked'
    assert current_report['scientific_status']['publication_ready'] is False
    assert current_report['full_pytest_suite_executed'] is False


def test_default_all_scope_fails_without_changing_legacy_test():
    report = checker.check_project()
    assert report['scope'] == 'all' and report['status'] == 'failed'
    assert report['current_delivery']['status'] == 'passed'
    assert report['legacy_documents']['introduced_by_current_state_upgrade'] is True


def test_cli_has_one_json_and_correct_exit_codes(current_report, monkeypatch, capsys):
    monkeypatch.setattr(checker, 'check_project', lambda *args: current_report)
    assert checker.main(['--scope', 'current']) == 0
    assert json.loads(capsys.readouterr().out) == current_report
    failed = {**current_report, 'status': 'failed', 'scope': 'all'}
    monkeypatch.setattr(checker, 'check_project', lambda *args: failed)
    assert checker.main([]) == 1
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'


def test_bad_anchor_fails_in_current_scope():
    report = checker.check_project(manifest_sha256='0' * 64, scope='current')
    assert report['status'] == 'failed'
    assert report['legacy_documents']['status'] == 'not_checked'


def test_gate_failure_is_not_promoted(monkeypatch):
    def fail(*args):
        raise ValueError('Frozen binding changed')
    monkeypatch.setattr(checker, 'accept_delivery', fail)
    report = checker.check_project(scope='current')
    assert report['status'] == 'failed'
    assert report['current_delivery']['reason'] == 'Frozen binding changed'


def test_verification_never_fits(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError('Project check must never fit')
    for cls in (DummyClassifier, RandomForestClassifier, LogisticRegression, Pipeline, StandardScaler):
        monkeypatch.setattr(cls, 'fit', fail)
    assert checker.check_project(scope='current')['status'] == 'passed'


def test_output_is_exclusive_and_outside_frozen_inputs(current_report, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(checker, 'check_project', lambda *args: current_report)
    output = tmp_path / 'report.json'
    assert checker.main(['--scope', 'current', '--output', str(output)]) == 0
    capsys.readouterr()
    original = output.read_bytes()
    assert read_json(output) == current_report
    assert checker.main(['--scope', 'current', '--output', str(output)]) == 1
    assert output.read_bytes() == original
    assert json.loads(capsys.readouterr().out)['error_type'] == 'FileExistsError'
    for forbidden in (checker.DEFAULT_BUNDLE / 'new-report.json',
                      ROOT / '03_experiments/protocols/new-project-report.json'):
        assert checker.main(['--output', str(forbidden)]) == 1
        assert json.loads(capsys.readouterr().out)['status'] == 'failed'
        assert not forbidden.exists()


def test_failure_report_is_saved_as_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(checker, 'check_project', lambda *args: {'status': 'failed', 'reason': 'gate blocked'})
    output = tmp_path / 'blocked.json'
    assert checker.main(['--output', str(output)]) == 1
    assert read_json(output)['status'] == json.loads(capsys.readouterr().out)['status'] == 'failed'


def test_unknown_scope_is_rejected():
    with pytest.raises(ValueError, match='Scope must'):
        checker.check_project(scope='unsupported')


@pytest.mark.parametrize('entry', ['check', 'accept'])
def test_cli_utf8_consumer_works_under_gbk_console(entry, tmp_path):
    if entry == 'check':
        command = [sys.executable, str(ROOT / '02_code/check_mic_project.py'), '--scope', 'current']
    else:
        command = [sys.executable, str(ROOT / '02_code/accept_mic_delivery.py'),
                   '--bundle', str(checker.DEFAULT_BUNDLE), '--manifest-sha256', checker.DEFAULT_ANCHOR,
                   '--output', str(tmp_path / 'gbk-acceptance.json')]
    environment = {**os.environ, 'PYTHONIOENCODING': 'gbk'}
    completed = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, timeout=60)
    assert completed.returncode == 0, completed.stderr.decode('gbk', errors='replace')
    report = json.loads(completed.stdout.decode('utf-8'))
    assert report['status'] == 'passed'
    if entry == 'accept':
        assert report == read_json(tmp_path / 'gbk-acceptance.json')
