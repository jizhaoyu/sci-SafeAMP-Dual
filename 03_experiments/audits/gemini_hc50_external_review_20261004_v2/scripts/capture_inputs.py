"""One-time local snapshot; never replaces an existing snapshot or manifest."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
BUNDLE = Path(__file__).resolve().parents[1]
LEGACY = ROOT / '03_experiments/audits/gemini_hc50_external_review_20261004_v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture():
    target = BUNDLE / 'input_manifest.json'
    if target.exists() or (BUNDLE / 'inputs').exists() or (BUNDLE / 'raw').exists():
        raise FileExistsError('Input snapshot already exists')
    protected = {p.relative_to(ROOT).as_posix(): sha(p) for p in LEGACY.rglob('*') if p.is_file()}
    roles = {}
    for name, role in [('molecule_review.csv', 'legacy_molecules'), ('assay_observations.csv', 'legacy_assays'), ('source_manifest.csv', 'legacy_sources'), ('search_log.csv', 'legacy_search')]:
        dest = BUNDLE / 'inputs' / name
        dest.parent.mkdir(exist_ok=True)
        with dest.open('xb') as handle:
            handle.write((LEGACY / name).read_bytes())
        roles[role] = dest.relative_to(ROOT).as_posix()
    for source in (LEGACY / 'raw').glob('*.xml'):
        dest = BUNDLE / 'raw' / source.name
        dest.parent.mkdir(exist_ok=True)
        with dest.open('xb') as handle:
            handle.write(source.read_bytes())
    roles.update(development_records='03_experiments/prepared/amd02_evidence_clean_20261001/records.csv',
                 mic_cohort='03_experiments/audits/mic_goat_followup_release_20261004_v1/cohort/candidate_molecules.csv')
    required = list(roles.values()) + [p.relative_to(ROOT).as_posix() for p in (BUNDLE / 'raw').glob('*.xml')]
    required += ['02_code/research_data.py', '02_code/public_data.py', '02_code/research_protocol_config.py',
                 'docs/amendments/PROTOCOL_AMENDMENT_02_ALL_MEMBER.md',
                 '03_experiments/prepared/amd02_evidence_clean_20261001/manifest.json',
                 '04_paper/research_status.json', '03_experiments/audits/mic_training_readiness_20261004_v26.json',
                 '03_experiments/audits/protocol_mic_13_freeze_20261004_v1.json']
    freeze = json.loads((ROOT / required[-1]).read_text(encoding='utf-8'))
    required += list(freeze['dependency_sha256'])
    required = sorted(set(required))
    data = {'schema_version': 1, 'roles': roles, 'required_files': required,
            'files': {p: sha(ROOT / p) for p in required}, 'protected_v1': protected,
            'capture_method': 'local byte-for-byte snapshot; not a new literature acquisition'}
    with target.open('x', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    print(json.dumps({'input_manifest': target.relative_to(ROOT).as_posix(), 'sha256': sha(target), 'protected_v1_files': len(protected), 'input_files': len(required)}, ensure_ascii=True))


if __name__ == '__main__':
    capture()
