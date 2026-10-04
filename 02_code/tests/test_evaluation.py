import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluation import binary_metrics,select_threshold,paired_cluster_comparison,validate_predictions,holm

def test_missing_labels_and_undefined_auc():
    m=binary_metrics([1,np.nan],[.8,.9])
    assert m['n']==1 and m['AUROC'] is None and m['status']=='single_class'

def test_threshold_respects_validation_specificity():
    y=np.array([0]*20+[1]*5);p=np.linspace(0,1,25)
    t=select_threshold(y,p)
    assert binary_metrics(y,p,t)['specificity']>=.95

def test_paired_cluster_identical_predictions():
    y=np.array([0,1]*10);p=np.linspace(.1,.9,20);g=np.repeat(np.arange(10),2)
    r=paired_cluster_comparison(y,p,p,g,resamples=40)
    assert r['difference']==0 and r['ci95_low']==0 and r['paired_cluster_permutation_p']==1

def test_holm_and_invalid_probability():
    assert holm([.01,.04,.2])==pytest.approx([.03,.08,.2])
    with pytest.raises(ValueError):binary_metrics([0,1],[float('nan'),.2])

def test_missing_duplicate_prediction_metadata():
    row=dict(sample_id='a',cluster_id=1,split='test',model='full',seed=11,task='hemo',y_true=0,probability=.2,threshold=.5)
    with pytest.raises(ValueError,match='Duplicate'):validate_predictions(pd.DataFrame([row,row]))
