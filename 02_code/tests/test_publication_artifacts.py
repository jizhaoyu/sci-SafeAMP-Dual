import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from evaluation import ensemble_predictions,cluster_intervals,validate_coverage
from publication_artifacts import export,plot_primary


def predictions():
    # These are software fixtures, never an experimental dataset or result.
    rows=[]
    for split in ['oof_selection','test','external']:
        for i in range(12):
            for model in ['dual_gated','rf']:
                for seed in [11,23,42]:
                    for task in ['amp','hemo']:
                        rows.append(dict(sample_id=split+str(i),cluster_id=split+str(i//2),split=split,model=model,seed=seed,task=task,y_true=i%2,probability=.8 if i%2 else .2,threshold=.5))
    return pd.DataFrame(rows)


def test_ensemble_uses_development_threshold_and_cluster_intervals(tmp_path):
    frame=predictions();ensemble=ensemble_predictions(frame)
    assert len(ensemble)*3==len(frame)
    assert ensemble.seed.eq(-1).all()
    # Three-way floating-point averaging differs from 0.8 by one ULP.
    np.testing.assert_allclose(ensemble.threshold,.8,rtol=0,atol=1e-15)
    intervals=cluster_intervals(ensemble,resamples=40)
    assert len(intervals)==2*2*2*6
    assert all(r['clusters']==6 and r['valid_draws']==40 for r in intervals)
    plot_primary(intervals,tmp_path/'software_fixture')
    assert (tmp_path/'software_fixture.png').stat().st_size>1000


def test_missing_model_seed_or_sample_blocks_outputs():
    frame=predictions()
    with pytest.raises(ValueError):validate_coverage(frame[frame.seed.ne(42)],['dual_gated','rf'],[11,23,42])
    with pytest.raises(ValueError):ensemble_predictions(frame.iloc[1:])


def test_invalid_run_cannot_emit_publication_tables(tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps({'status':'blocked'}))
    destination=tmp_path/'paper'
    with pytest.raises(ValueError,match='completed'):export(tmp_path,destination)
    assert not destination.exists()


def test_publication_not_ready_blocks_export(tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps({
        'status': 'completed',
        'dataset_manifest': {'status': 'validated'},
        'publication_ready': False,
        'formal_results_available': True,
        'reference_audit': {'all_claims_verified': True}
    }))
    with pytest.raises(ValueError, match='publication_ready must be true'):
        export(tmp_path, tmp_path/'paper')


def test_formal_results_not_available_blocks_export(tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps({
        'status': 'completed',
        'dataset_manifest': {'status': 'validated'},
        'publication_ready': True,
        'formal_results_available': False,
        'reference_audit': {'all_claims_verified': True}
    }))
    with pytest.raises(ValueError, match='formal_results_available must be true'):
        export(tmp_path, tmp_path/'paper')


def test_unverified_reference_audit_blocks_export(tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps({
        'status': 'completed',
        'dataset_manifest': {'status': 'validated'},
        'publication_ready': True,
        'formal_results_available': True,
        'reference_audit': {'all_claims_verified': False}
    }))
    with pytest.raises(ValueError, match='reference_audit.all_claims_verified must be true'):
        export(tmp_path, tmp_path/'paper')

