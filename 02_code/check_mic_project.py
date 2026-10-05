"""Check the current MIC delivery and report frozen legacy compatibility explicitly."""
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys
import tempfile

from accept_mic_delivery import accept_delivery, STATE_RELATIVE
import publish_mic_followup_status as legacy
from research_utils import ROOT, read_json, sha256, utc_now

DEFAULT_BUNDLE = ROOT / '03_experiments/deliveries/mic_baseline_20261004_v1'
DEFAULT_ANCHOR = 'f8b8606dc807279cc78c6728260f6d3d7da463f2416bf47e8d3bafbdf1789ed3'


def check_project(bundle=DEFAULT_BUNDLE, manifest_sha256=DEFAULT_ANCHOR, scope='all'):
    if scope not in ('current', 'all'):
        raise ValueError('Scope must be current or all')
    report = {'schema_version': 1, 'generated_at': utc_now(), 'scope': scope,
              'status': 'failed', 'full_pytest_suite_executed': False,
              'scientific_state_updated': False, 'training_executed': False}
    try:
        with tempfile.TemporaryDirectory(prefix='mic-project-check-') as temp:
            with redirect_stdout(sys.stderr):
                current = accept_delivery(bundle, manifest_sha256, Path(temp) / 'acceptance.json')
        state = read_json(ROOT / STATE_RELATIVE)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, AssertionError) as exc:
        report['current_delivery'] = {'status': 'failed', 'error_type': type(exc).__name__,
                                      'reason': str(exc)}
        report['legacy_documents'] = {'status': 'not_checked'}
        return report

    report['current_delivery'] = current
    report['scientific_status'] = {
        'state_path': STATE_RELATIVE, 'state_sha256': current['state_sha256'],
        'mic_training_blocked': state['training_blocked'],
        'formal_dual_task_status': state['formal_dual_task_status'],
        'formal_results_available': state['formal_results_available'],
        'publication_ready': state['publication_ready'],
    }
    try:
        legacy.validate_documents(state)
        compatibility = {'status': 'passed'}
    except ValueError as exc:
        inventory_mismatch = str(exc) == 'Current evidence inventory differs'
        compatibility = {
            'status': 'incompatible' if inventory_mismatch else 'failed',
            'reason': str(exc),
            'publisher': '02_code/publish_mic_followup_status.py',
            'test': '02_code/tests/test_evidence_gate_repair.py::test_all_current_documents_agree',
            'current_inventory': [state['evidence_molecules'], state['evidence_observations']],
            'supported_legacy_inventory': [16, 23],
            'introduced_by_current_state_upgrade': inventory_mismatch,
            'pytest_test_executed': False,
        }
    report['legacy_documents'] = compatibility
    report['status'] = 'passed' if scope == 'current' or compatibility['status'] == 'passed' else 'failed'
    report['code_sha256'] = {
        name: sha256(ROOT / name) for name in (
            '02_code/check_mic_project.py', '02_code/accept_mic_delivery.py',
            '02_code/publish_mic_followup_status.py',
        )
    }
    return report


def _new_report_path(path, bundle):
    path = Path(path).absolute()
    if path.exists() or path.is_symlink():
        raise FileExistsError('Refusing to overwrite project check report')
    path = path.resolve()
    if path.is_relative_to(Path(bundle).resolve()):
        raise ValueError('Report must be outside the immutable delivery bundle')
    if path.is_relative_to(ROOT) and path.parent != (ROOT / '03_experiments/audits').resolve():
        raise ValueError('Workspace reports must be direct files in 03_experiments/audits')
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument('--manifest-sha256', default=DEFAULT_ANCHOR)
    parser.add_argument('--scope', choices=('current', 'all'), default='all',
                        help='current: MIC delivery gates; all: also require frozen legacy document compatibility')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        output = _new_report_path(args.output, args.bundle) if args.output is not None else None
        result = check_project(args.bundle, args.manifest_sha256, args.scope)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('x', encoding='utf-8') as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write('\n')
    except (OSError, ValueError) as exc:
        result = {'status': 'failed', 'error_type': type(exc).__name__, 'reason': str(exc)}
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
