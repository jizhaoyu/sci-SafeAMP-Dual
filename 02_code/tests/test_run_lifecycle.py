"""Tests for run lifecycle, dataset loading gates, and full artifact validation."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from experiment_runner import load_dataset, MODELS, SEEDS
from run_artifacts import validate_run_artifacts, validate_artifact_payloads
from research_data import ResearchDataError
from research_utils import sha256, write_json


def test_load_dataset_rejects_csv_file(tmp_path):
    csv_file = tmp_path / "dataset.csv"
    csv_file.write_text("sample_id,seq\n")
    with pytest.raises(ResearchDataError, match="requires a validated prepared directory, not a CSV file"):
        load_dataset(csv_file)


def test_load_dataset_rejects_cohorts_built_status(tmp_path):
    dir_path = tmp_path / "cohorts_built_dir"
    dir_path.mkdir()
    write_json(dir_path / "manifest.json", {"status": "cohorts_built"})
    with pytest.raises(ResearchDataError, match="status is 'cohorts_built', not 'validated'"):
        load_dataset(dir_path)


@pytest.mark.parametrize('protocol_id, expected', [
    ('protocol-amd-01', 'protocol_conflict'),
    ('protocol-amd-02', 'specification or digest mismatch'),
])
def test_load_dataset_rejects_unapproved_or_incomplete_protocol(tmp_path, protocol_id, expected):
    write_json(tmp_path / 'manifest.json', {'status': 'validated', 'protocol_id': protocol_id})
    with pytest.raises(ResearchDataError, match=expected):
        load_dataset(tmp_path)


def test_validate_run_artifacts_rejects_non_completed(tmp_path):
    run_dir = tmp_path / "running_run"
    run_dir.mkdir()
    write_json(run_dir / "manifest.json", {"status": "running", "formal_results_available": False})
    with pytest.raises(ValueError, match="expected 'completed'"):
        validate_run_artifacts(run_dir)


def test_validate_run_artifacts_rejects_missing_formal_results(tmp_path):
    run_dir = tmp_path / "unformal_run"
    run_dir.mkdir()
    write_json(run_dir / "manifest.json", {"status": "completed", "formal_results_available": False})
    with pytest.raises(ValueError, match="formal_results_available must be true"):
        validate_run_artifacts(run_dir)


def make_mock_completed_run(tmp_path):
    run_dir = tmp_path / "mock_completed_run"
    run_dir.mkdir()

    # 1. features.npz
    feat_file = run_dir / "features.npz"
    samples = [
        ('s1', 'oof_selection', 0, 1.0, 0.0),
        ('s2', 'oof_selection', 1, 0.0, 1.0),
        ('s3', 'test', 2, 1.0, 0.0),
        ('s4', 'test', 3, 0.0, 1.0),
        ('s5', 'external', 4, 1.0, 0.0),
        ('s6', 'external', 5, 0.0, 1.0),
        ('s7', 'test', 2, 0.0, 1.0),
        ('s8', 'external', 4, 1.0, 0.0),
    ]
    sample_ids = np.array([s[0] for s in samples])
    np.savez_compressed(feat_file, esm=np.zeros((len(samples), 320), dtype='float32'), phys=np.zeros((len(samples), 44), dtype='float32'), sample_ids=sample_ids)
    feat_sha = sha256(feat_file)

    # 2. predictions.csv
    pred_rows = []
    for s_id, split, c_id, amp_val, hemo_val in samples:
        for m in MODELS:
            for s in SEEDS:
                for t in ['amp', 'hemo']:
                    val = amp_val if t == 'amp' else hemo_val
                    pred_rows.append({
                        'sample_id': s_id,
                        'cluster_id': c_id,
                        'split': split,
                        'fold': 0 if split == 'oof_selection' else -1,
                        'model': m,
                        'seed': s,
                        'task': t,
                        'y_true': val,
                        'probability': 0.8 if val == 1.0 else 0.2,
                        'raw_probability': 0.75 if val == 1.0 else 0.25,
                        'threshold': 0.5
                    })
    pred_df = pd.DataFrame(pred_rows)
    pred_file = run_dir / "predictions.csv"
    pred_df.to_csv(pred_file, index=False)
    pred_sha = sha256(pred_file)

    # 3. Model joblib artifacts
    art_list = []
    for m in MODELS:
        for s in SEEDS:
            f = run_dir / f"{m}_seed_{s}.joblib"
            f.write_text("mock_model")
            art_list.append({"path": f.name, "sha256": sha256(f)})

    # 4. Checkpoints
    cp_list = []
    for s in SEEDS:
        f = run_dir / f"dual_gated_seed_{s}.pt"
        f.write_text("mock_checkpoint")
        cp_list.append({"path": f.name, "sha256": sha256(f), "seed": s})

    # 5. Evaluation files
    eval_shas = {}
    for fname in ['ensemble_predictions.csv', 'ensemble_metrics.json', 'confidence_intervals.json', 'metrics.json', 'comparisons.json']:
        f = run_dir / fname
        f.write_text("{}" if fname.endswith(".json") else "mock_data")
        eval_shas[fname.replace(".", "_") + "_sha256" if fname.endswith(".json") else fname.replace(".csv", "_sha256")] = sha256(f)

    manifest = {
        "status": "completed",
        "formal_results_available": True,
        "publication_ready": False,
        "config": {"models": list(MODELS), "seeds": list(SEEDS)},
        "features_sha256": feat_sha,
        "predictions_sha256": pred_sha,
        "model_artifacts": art_list,
        "checkpoints": cp_list,
        **eval_shas
    }
    write_json(run_dir / "manifest.json", manifest)
    return run_dir


def test_validate_run_artifacts_succeeds_on_valid_fixture(tmp_path):
    run_dir = make_mock_completed_run(tmp_path)
    res = validate_run_artifacts(run_dir)
    assert res['models_verified'] == 7
    assert res['seeds_verified'] == 3
    assert res['joblib_count'] == 21
    assert res['checkpoint_count'] == 3
