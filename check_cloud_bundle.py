"""Verify frozen inputs by hash, and evolving training artifacts structurally."""
from pathlib import Path
import hashlib
import json

import joblib
import numpy as np


def sha256(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def check_bundle(root):
    manifest = json.loads((root / 'cloud_manifest.json').read_text(encoding='utf-8'))
    run_relative = 'output/dta-paper-run-v5-20261009/'
    generated = tuple(run_relative + folder for folder in
                      ('models/', 'checkpoints/', 'predictions/'))
    checked = 0
    for relative, expected in manifest['sha256'].items():
        if relative.startswith(generated):
            continue
        if sha256(root / relative) != expected:
            raise RuntimeError(f'File checksum mismatch: {relative}')
        checked += 1

    run = root / run_relative
    settings = 0
    for metadata_path in sorted((run / 'checkpoints').glob('*.json')):
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        with np.load(metadata_path.with_suffix('.npz'), allow_pickle=False) as arrays:
            for exp_id, metrics in metadata['metrics'].items():
                oof = arrays[f'oof_{exp_id}']
                evaluation = arrays[f'eval_{exp_id}']
                if oof.shape != (16720,) or not np.isfinite(oof).all():
                    raise RuntimeError(f'Invalid OOF checkpoint: {exp_id}')
                if evaluation.shape != (metrics['eval_overall']['n'],) or not np.isfinite(evaluation).all():
                    raise RuntimeError(f'Invalid evaluation checkpoint: {exp_id}')
                if metrics['model_id'] == 'stacked_ensemble':
                    weights = json.loads((run / 'models' / f'{exp_id}_weights.json').read_text(encoding='utf-8'))
                    values = [weights['weights'][key] for key in
                              ('ridge', 'hist_gradient_boosting', 'random_forest')]
                    if not np.isfinite(values).all() or np.any(np.asarray(values) < 0):
                        raise RuntimeError(f'Invalid stacking weights: {exp_id}')
                elif not (run / 'models' / f'{exp_id}.joblib').is_file():
                    raise RuntimeError(f'Missing model: {exp_id}')
        settings += 1
    for setting in manifest['completed_settings']:
        if not (run / 'checkpoints' / f'{setting}.json').is_file():
            raise RuntimeError(f'Missing original completed setting: {setting}')

    model_count = 0
    for model_path in sorted((run / 'models').glob('*.joblib')):
        model = joblib.load(model_path)
        if not callable(getattr(model, 'predict', None)) or not hasattr(model, 'n_features_in_'):
            raise RuntimeError(f'Invalid fitted model: {model_path.name}')
        model_count += 1
        del model

    partial_count = 0
    for path in sorted((run / 'checkpoints/fold_progress').glob('*.npz')):
        with np.load(path, allow_pickle=False) as data:
            oof = data['oof']
            completed = data['completed_folds'].item()
            elapsed = data['elapsed_seconds'].item()
            if not isinstance(completed, int) or not 0 <= completed <= 25:
                raise RuntimeError(f'Invalid completed fold count: {path.name}')
            if oof.shape != (16720,) or oof.dtype != np.float32 or not np.isfinite(oof).all():
                raise RuntimeError(f'Invalid fold predictions: {path.name}')
            if hashlib.sha256(memoryview(oof).cast('B')).hexdigest() != data['prediction_sha256'].item():
                raise RuntimeError(f'Fold prediction checksum mismatch: {path.name}')
            if not np.isfinite(elapsed) or elapsed < 0 or not data['fingerprint'].item():
                raise RuntimeError(f'Invalid fold metadata: {path.name}')
            print(f'[FOLD CHECK] {path.stem}: {completed} folds saved')
        partial_count += 1
    print(f'PASS: {checked} frozen files verified; {settings} complete settings; '
          f'{model_count} models readable; {partial_count} fold checkpoints verified.')
    print('Exact fold compatibility will be checked by the runner before resuming.')


if __name__ == '__main__':
    check_bundle(Path(__file__).resolve().parent)
