"""Published research evidence status, independent of inference runtime readiness."""
import json
import re
from datetime import date
from pathlib import Path

DEFAULT_SOURCE = Path(__file__).resolve().parent / 'data/dti_external_evidence.json'

def get_evidence_status(source=DEFAULT_SOURCE):
    unknown = {
        'status': 'unavailable', 'reviewed_at': None, 'scope_label': None,
        'reviewed_count': None, 'confirmed_point_count': None, 'admitted_count': None,
        'external_evaluation_completed': None, 'human_review': 'unknown',
        'external_metrics': {'mae': None, 'rmse': None, 'ci': None}, 'candidates': [],
        'message': '研究证据状态无法确认；不能据此判断独立外部验证已完成。',
    }
    try:
        data = json.loads(Path(source).read_text(encoding='utf-8'))
        if data['schema_version'] != 1:
            raise ValueError('Unsupported evidence schema')
        date.fromisoformat(data['reviewed_at'])
        candidates = data['candidates']
        if not isinstance(candidates, list) or not candidates:
            raise ValueError('Review candidates missing')
        if len({r['id'] for r in candidates}) != len(candidates):
            raise ValueError('Duplicate candidate identity')
        if any(r['status'] not in {'pending_evidence', 'excluded', 'admitted'} or type(r['point_confirmed']) is not bool or not r['label'] or not r['reason'] for r in candidates):
            raise ValueError('Unsupported candidate qualification')
        if any(type(data[key]) is not int for key in ('reviewed_count', 'confirmed_point_count', 'admitted_count')):
            raise ValueError('Counts must be integers')
        if data['reviewed_count'] != len(candidates) or data['confirmed_point_count'] != sum(r['point_confirmed'] for r in candidates):
            raise ValueError('Review counts do not match records')
        admitted = sum(r['status'] == 'admitted' for r in candidates)
        if data['admitted_count'] != admitted:
            raise ValueError('Admitted count does not match records')
        if not re.fullmatch(r'[0-9a-f]{64}', data['source_scope_sha256']):
            raise ValueError('Source provenance missing')
        diagnostics = data.get('model_diagnostics', {})
        if not isinstance(diagnostics, dict):
            raise ValueError('Invalid model diagnostic records')
        for model_id, record in diagnostics.items():
            if model_id != 'f1_ridge' or record['scope'] != 'existing_DAVIS_diagnostic':
                raise ValueError('Unsupported model diagnostic scope')
            date.fromisoformat(record['reviewed_at'])
            if any(not re.fullmatch(r'[0-9a-f]{64}', record[key]) for key in ('model_sha256', 'diagnosis_sha256')):
                raise ValueError('Model diagnostic binding missing')
            if type(record['high_affinity_count']) is not int or record['high_affinity_count'] <= 0 or not isinstance(record['summary'], str):
                raise ValueError('Invalid diagnostic summary')
            if type(record['high_affinity_mae_pkd']) not in (int, float) or not 0 <= record['high_affinity_mae_pkd'] < 100:
                raise ValueError('Invalid diagnostic error')
        msg = '外部证据复核准入已完成；5条高质量候选已正式准入，3条证据不足已规范排除。' if data['admitted_count'] > 0 else '独立外部评价尚未完成；现有预测用于计算探索，基准指标不等同于外部泛化验证。'
        return {**data, 'status': 'available', 'external_metrics': unknown['external_metrics'],
                'message': msg}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return unknown

def evidence_for_result():
    data = get_evidence_status()
    return {key: value for key, value in data.items() if key != 'candidates'}
