"""Validation of completed experiment run artifacts and immutable payloads.

Enforces strict integrity of:
- 21 model joblib artifacts (7 models x 3 seeds)
- 3 PyTorch dual_gated checkpoints
- Extracted features (features.npz)
- Exhaustive per-sample predictions (N x 7 x 3 x 2)
- Aggregated ensemble predictions, metrics, confidence intervals, and comparisons
"""
from pathlib import Path
import numpy as np
import pandas as pd

from evaluation import validate_coverage
from research_utils import read_json, sha256


EXPECTED_MODELS = ('svm', 'rf', 'dual_gated', 'dual_concat', 'phys_only', 'esm_only', 'single_task')
EXPECTED_SEEDS = (11, 23, 42)


def validate_artifact_payloads(run_dir: Path, manifest: dict) -> dict:
    """Validate existence, hashes, and internal structure of all physical run outputs.
    
    Called internally by experiment_runner before writing status='completed',
    and reused by validate_run_artifacts.
    """
    run_dir = Path(run_dir)
    config = manifest.get('config', {})
    models = config.get('models', list(EXPECTED_MODELS))
    seeds = config.get('seeds', list(EXPECTED_SEEDS))

    # 1. Validate features.npz
    feat_path = run_dir / 'features.npz'
    if not feat_path.is_file():
        raise FileNotFoundError(f"Missing feature cache: {feat_path}")
    if sha256(feat_path) != manifest.get('features_sha256'):
        raise ValueError("features.npz checksum mismatch with manifest.")
    feat_data = np.load(feat_path)
    for arr in ['esm', 'phys', 'sample_ids']:
        if arr not in feat_data:
            raise ValueError(f"features.npz missing required array: {arr}")

    # 2. Validate predictions.csv
    pred_path = run_dir / 'predictions.csv'
    if not pred_path.is_file():
        raise FileNotFoundError(f"Missing predictions file: {pred_path}")
    if sha256(pred_path) != manifest.get('predictions_sha256'):
        raise ValueError("predictions.csv checksum mismatch with manifest.")
    preds = pd.read_csv(pred_path)
    validate_coverage(preds, models, seeds)

    # Validate probability bounds
    if not np.isfinite(preds['probability']).all():
        raise ValueError("predictions.csv contains non-finite probabilities.")
    if (preds['probability'] < 0.0).any() or (preds['probability'] > 1.0).any():
        raise ValueError("predictions.csv contains probabilities outside [0, 1].")

    # 3. Validate joblib model artifacts (7 x 3 = 21 artifacts)
    art_map = {a['path']: a['sha256'] for a in manifest.get('model_artifacts', [])}
    for m in models:
        for s in seeds:
            fname = f"{m}_seed_{s}.joblib"
            p = run_dir / fname
            if not p.is_file():
                raise FileNotFoundError(f"Missing model artifact: {fname}")
            if fname not in art_map:
                raise ValueError(f"Model artifact {fname} not declared in manifest model_artifacts.")
            if sha256(p) != art_map[fname]:
                raise ValueError(f"Checksum mismatch for model artifact: {fname}")

    # 4. Validate PyTorch dual_gated checkpoints (3 seeds)
    cp_map = {c['path']: c['sha256'] for c in manifest.get('checkpoints', [])}
    for s in seeds:
        fname = f"dual_gated_seed_{s}.pt"
        p = run_dir / fname
        if not p.is_file():
            raise FileNotFoundError(f"Missing dual_gated checkpoint: {fname}")
        if fname not in cp_map:
            raise ValueError(f"Checkpoint {fname} not declared in manifest checkpoints.")
        if sha256(p) != cp_map[fname]:
            raise ValueError(f"Checksum mismatch for checkpoint: {fname}")

    # 5. Validate evaluation outputs and metrics
    eval_files = [
        ('ensemble_predictions.csv', 'ensemble_predictions_sha256'),
        ('ensemble_metrics.json', 'ensemble_metrics_sha256'),
        ('confidence_intervals.json', 'confidence_intervals_sha256'),
        ('metrics.json', 'metrics_sha256'),
        ('comparisons.json', 'comparisons_sha256'),
    ]
    for fname, sha_key in eval_files:
        p = run_dir / fname
        if not p.is_file():
            raise FileNotFoundError(f"Missing evaluation artifact: {fname}")
        if sha_key in manifest and sha256(p) != manifest[sha_key]:
            raise ValueError(f"Checksum mismatch for {fname}.")

    return {
        'run_dir': str(run_dir.resolve()),
        'models_verified': len(models),
        'seeds_verified': len(seeds),
        'total_predictions': len(preds),
        'joblib_count': len(models) * len(seeds),
        'checkpoint_count': len(seeds),
    }


def validate_run_artifacts(run_dir: Path) -> dict:
    """Public gate: validate completed research run outputs."""
    run_dir = Path(run_dir)
    manifest_file = run_dir / 'manifest.json'
    if not manifest_file.is_file():
        raise FileNotFoundError(f"Missing run manifest: {manifest_file}")

    manifest = read_json(manifest_file)
    if manifest.get('status') != 'completed':
        raise ValueError(f"Run status is '{manifest.get('status')}', expected 'completed'.")
    if not manifest.get('formal_results_available', False):
        raise ValueError("Run formal_results_available must be true for completed runs.")

    return validate_artifact_payloads(run_dir, manifest)
