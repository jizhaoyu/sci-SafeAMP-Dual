import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiment_runner import fit_predict,CONFIG,MODELS,load_dataset
from research_data import ResearchDataError

@pytest.mark.parametrize('kind',MODELS)
def test_each_model_trains_with_partial_labels_and_is_reproducible(kind):
    rng=np.random.default_rng(22)
    e=rng.normal(size=(16,320)).astype('float32');p=rng.normal(size=(16,44)).astype('float32')
    y=np.column_stack([np.arange(16)%2,np.arange(16)%2]).astype('float32')
    y[0,0]=np.nan;y[1,1]=np.nan
    config={**CONFIG,'epochs':1,'rf_trees':8}
    first,state=fit_predict(kind,e,p,y,[(e[:3],p[:3])],11,config)
    second,_=fit_predict(kind,e,p,y,[(e[:3],p[:3])],11,config)
    assert first[0].shape==(3,2) and np.isfinite(first[0]).all()
    np.testing.assert_allclose(first[0],second[0],atol=1e-7)
    np.testing.assert_allclose(state['phys_scaler'].mean_,p.mean(axis=0),atol=1e-6)

def test_unvalidated_dataset_blocks_training(tmp_path):
    (tmp_path/'manifest.json').write_text('{"status":"blocked"}')
    with pytest.raises(ResearchDataError):load_dataset(tmp_path)
