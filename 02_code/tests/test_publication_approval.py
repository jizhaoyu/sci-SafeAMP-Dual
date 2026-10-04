"""Tests for publication approval receipt validation, research draft mode, and hash bindings."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from publication_artifacts import export, load_research_predictions, load_predictions
from research_utils import sha256, write_json, read_json
from test_run_lifecycle import make_mock_completed_run


def make_export_fixtures(tmp_path):
    dataset_dir = tmp_path / "valid_dataset"
    dataset_dir.mkdir(parents=True)
    
    samples = []
    for split_idx, split_name in enumerate(["development", "test", "external"]):
        for i in range(12):
            s_id = f"{split_name}_{i}"
            c_id = f"c_{split_idx}_{i // 2}"
            amp_val = float(i % 2)
            hemo_val = float((i + 1) % 2)
            samples.append((s_id, split_name, c_id, amp_val, hemo_val, 0 if split_name == "development" else -1))

    records = pd.DataFrame([
        {
            "record_id": f"REC_{i}", "seq": "GIGAVLKVLTTGLPALISWIKRKRQQ",
            "amp": s[3], "hemo": s[4],
            "source_dataset": "DBAASP", "source_accession": f"A{i}", "source_url": "http://example.com",
            "evidence_reference": "ref", "label_basis": "measured", "assay_conditions": "std",
            "modifications": "none", "evidence_type": "experimental", "is_synthetic": False,
            "source_role": "external" if s[1] == "external" else "development", "raw_path": "fake", "raw_sha256": "fake"
        }
        for i, s in enumerate(samples)
    ])
    records.to_csv(dataset_dir / "records.csv", index=False)
    
    dataset = pd.DataFrame([
        {"sample_id": s[0], "seq": "GIGAVLKVLTTGLPALISWIKRKRQQ",
         "amp": s[3], "hemo": s[4],
         "split": s[1], "fold": s[5], "cluster_id": s[2],
         "source_role": "external" if s[1] == "external" else "development"}
        for s in samples
    ])
    dataset.to_csv(dataset_dir / "dataset.csv", index=False)

    manifest = {
        "status": "validated",
        "cutoff": 0.40,
        "protocol_id": "legacy-v1",
        "dataset_sha256": sha256(dataset_dir / "dataset.csv"),
        "provenance_sha256": sha256(dataset_dir / "records.csv"),
    }
    write_json(dataset_dir / "manifest.json", manifest)

    # Now make run_dir
    run_dir = tmp_path / "mock_completed_run"
    run_dir.mkdir(parents=True)
    from experiment_runner import MODELS, SEEDS
    feat_file = run_dir / "features.npz"
    sample_ids = np.array([s[0] for s in samples])
    np.savez_compressed(feat_file, esm=np.zeros((len(samples), 320), dtype='float32'), phys=np.zeros((len(samples), 44), dtype='float32'), sample_ids=sample_ids)
    
    pred_rows = []
    for s_id, split_name, c_id, amp_val, hemo_val, _ in samples:
        split_eval = "oof_selection" if split_name == "development" else split_name
        for m in MODELS:
            for s in SEEDS:
                for t in ['amp', 'hemo']:
                    val = amp_val if t == 'amp' else hemo_val
                    pred_rows.append({
                        'sample_id': s_id,
                        'cluster_id': c_id,
                        'split': split_eval,
                        'fold': 0 if split_eval == 'oof_selection' else -1,
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

    art_list = []
    for m in MODELS:
        for s in SEEDS:
            f = run_dir / f"{m}_seed_{s}.joblib"
            f.write_text("mock_model")
            art_list.append({"path": f.name, "sha256": sha256(f)})

    cp_list = []
    for s in SEEDS:
        f = run_dir / f"dual_gated_seed_{s}.pt"
        f.write_text("mock_checkpoint")
        cp_list.append({"path": f.name, "sha256": sha256(f), "seed": s})

    eval_shas = {}
    for fname in ['ensemble_predictions.csv', 'ensemble_metrics.json', 'confidence_intervals.json', 'metrics.json', 'comparisons.json']:
        f = run_dir / fname
        f.write_text("{}" if fname.endswith(".json") else "mock_data")
        eval_shas[fname.replace(".", "_") + "_sha256" if fname.endswith(".json") else fname.replace(".csv", "_sha256")] = sha256(f)

    run_manifest = {
        "status": "completed",
        "formal_results_available": True,
        "publication_ready": False,
        "config": {"models": list(MODELS), "seeds": list(SEEDS)},
        "features_sha256": sha256(feat_file),
        "predictions_sha256": sha256(pred_file),
        "model_artifacts": art_list,
        "checkpoints": cp_list,
        "dataset_dir": str(dataset_dir.resolve()),
        "dataset_manifest": manifest,
        "features": {"backend": "fair-esm"},
        **eval_shas
    }
    write_json(run_dir / "manifest.json", run_manifest)
    return dataset_dir, run_dir


def test_research_mode_succeeds_without_approval(tmp_path, monkeypatch):
    ds_dir, run_dir = make_export_fixtures(tmp_path)
    
    m = read_json(run_dir / "manifest.json")
    from experiment_runner import MODELS, SEEDS
    dataset_df = pd.read_csv(ds_dir / "dataset.csv")
    monkeypatch.setattr("experiment_runner.load_dataset", lambda f: (dataset_df, m["dataset_manifest"]))
    monkeypatch.setattr("publication_artifacts.plot_primary", lambda intervals, p: None)

    out_research = tmp_path / "research_export"
    res = export(run_dir, out_research, mode="research", resamples=40)
    assert res["status"] == "generated"
    assert res["publication_ready"] is False
    assert res["artifact_scope"] == "research_draft"
    assert res["review_status"] == "pending"


def test_publication_mode_blocks_without_approval(tmp_path, monkeypatch):
    ds_dir, run_dir = make_export_fixtures(tmp_path)
    m = read_json(run_dir / "manifest.json")

    dataset_df = pd.read_csv(ds_dir / "dataset.csv")
    monkeypatch.setattr("experiment_runner.load_dataset", lambda f: (dataset_df, m["dataset_manifest"]))

    out_pub = tmp_path / "pub_export"
    with pytest.raises(ValueError, match="explicit human approval receipt"):
        export(run_dir, out_pub, mode="publication", approval_path=None, resamples=40)


def test_publication_mode_succeeds_with_valid_approval_and_fails_on_tamper(tmp_path, monkeypatch):
    ds_dir, run_dir = make_export_fixtures(tmp_path)
    m = read_json(run_dir / "manifest.json")

    dataset_df = pd.read_csv(ds_dir / "dataset.csv")
    monkeypatch.setattr("experiment_runner.load_dataset", lambda f: (dataset_df, m["dataset_manifest"]))
    monkeypatch.setattr("publication_artifacts.plot_primary", lambda intervals, p: None)

    # Create dummy manuscript and approval receipt
    ms_file = tmp_path / "manuscript.tex"
    ms_file.write_text("dummy latex")
    
    app_file = tmp_path / "approval.json"
    app_data = {
        "status": "approved",
        "reviewed_at": "2026-09-30T00:00:00Z",
        "reviewed_by": "Lead Researcher",
        "run_manifest_sha256": sha256(run_dir / "manifest.json"),
        "manuscript_path": str(ms_file),
        "manuscript_sha256": sha256(ms_file),
    }
    write_json(app_file, app_data)

    out_pub = tmp_path / "pub_export_ok"
    res = export(run_dir, out_pub, mode="publication", approval_path=app_file, resamples=40)
    assert res["status"] == "generated"
    assert res["publication_ready"] is True
    assert res["artifact_scope"] == "publication_submission"

    # Now tamper with manuscript file: publication export must be rejected!
    ms_file.write_text("tampered content")
    out_pub_tampered = tmp_path / "pub_export_tampered"
    with pytest.raises(ValueError, match="Approval receipt hash mismatch"):
        export(run_dir, out_pub_tampered, mode="publication", approval_path=app_file, resamples=40)
