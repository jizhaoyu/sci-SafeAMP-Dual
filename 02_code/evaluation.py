"""Metrics and paired, cluster-level uncertainty from persisted predictions."""
import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, roc_auc_score, brier_score_loss,
                             confusion_matrix, matthews_corrcoef, roc_curve)

def binary_metrics(y, probability, threshold=.5):
    y,p=np.asarray(y,dtype=float),np.asarray(probability,dtype=float)
    mask=~np.isnan(y); y,p=y[mask],p[mask]
    if not np.isfinite(p).all() or ((p<0)|(p>1)).any():
        raise ValueError('Predictions must be finite probabilities in [0,1].')
    if not np.isin(y,[0,1]).all():raise ValueError('Labels must be binary or missing.')
    if not len(y):return {'n':0,'status':'not_measured'}
    pred=p>=threshold
    tn,fp,fn,tp=map(int,confusion_matrix(y,pred,labels=[0,1]).ravel())
    both=len(set(y))==2
    calibration=[]
    for lo,hi in zip(np.linspace(0,1,11)[:-1],np.linspace(0,1,11)[1:]):
        m=(p>=lo)&((p<hi) if hi<1 else (p<=hi))
        if m.any():calibration.append({'lower':float(lo),'upper':float(hi),'n':int(m.sum()),
                                      'predicted':float(p[m].mean()),'observed':float(y[m].mean())})
    return {'n':len(y),'status':'ok' if both else 'single_class','threshold':float(threshold),
            'AUROC':float(roc_auc_score(y,p)) if both else None,
            'AUPRC':float(average_precision_score(y,p)) if both else None,
            'MCC':float(matthews_corrcoef(y,pred)) if both else None,
            'accuracy':float((pred==y).mean()),'sensitivity':tp/(tp+fn) if tp+fn else None,
            'specificity':tn/(tn+fp) if tn+fp else None,'Brier':float(brier_score_loss(y,p)),
            'tn':tn,'fp':fp,'fn':fn,'tp':tp,'calibration_bins':calibration}

def select_threshold(y,p,specificity=.95):
    y,p=np.asarray(y,float),np.asarray(p,float)
    mask=~np.isnan(y);y,p=y[mask],p[mask]
    if set(y)!={0,1}:raise ValueError('Threshold selection requires both measured classes.')
    fpr,tpr,threshold=roc_curve(y,p,drop_intermediate=False)
    eligible=np.flatnonzero(fpr<=1-specificity+1e-12)
    best=max(eligible,key=lambda i:(tpr[i],-fpr[i],threshold[i]))
    # Finite threshold >1 represents predicting no positives, if necessary.
    return float(threshold[best]) if np.isfinite(threshold[best]) else float(np.nextafter(1.,2.))

def validate_predictions(frame):
    required={'sample_id','cluster_id','split','model','seed','task','y_true','probability','threshold'}
    if not required.issubset(frame):raise ValueError('Prediction artifact lacks required fields.')
    if frame.empty:raise ValueError('Prediction artifact is empty.')
    key=['sample_id','split','model','seed','task']
    if frame.duplicated(key).any():raise ValueError('Duplicate prediction keys.')
    if frame[['sample_id','cluster_id','split','model','seed','task','probability','threshold']].isna().any().any():
        raise ValueError('Missing prediction metadata.')
    if not np.isfinite(frame.probability).all() or not frame.probability.between(0,1).all():
        raise ValueError('Invalid probability.')
    if 'raw_probability' in frame and (not np.isfinite(frame.raw_probability).all() or not frame.raw_probability.between(0,1).all()):
        raise ValueError('Invalid raw probability.')
    if not np.isfinite(frame.threshold).all():raise ValueError('Invalid threshold.')
    if not frame.y_true.dropna().isin([0,1]).all():raise ValueError('Invalid observed label.')
    for _,group in frame.groupby(['sample_id','task']):
        if group.y_true.nunique(dropna=False)>1 or group.cluster_id.nunique()>1 or group.split.nunique()>1:
            raise ValueError('Inconsistent label/cluster across paired predictions.')
    return frame


def validate_coverage(frame, models, seeds):
    validate_predictions(frame)
    if set(frame.model)!=set(models) or set(frame.seed)!=set(seeds):
        raise ValueError('Missing planned model or seed.')
    if set(frame.task)!={'amp','hemo'} or set(frame.split)!={'oof_selection','test','external'}:
        raise ValueError('Missing planned task or split.')
    reference=None
    for _,g in frame.groupby(['model','seed','task']):
        keys=set(zip(g.sample_id,g.split))
        if reference is None:reference=keys
        elif reference!=keys:raise ValueError('Incomplete paired sample coverage.')
    expected=len(models)*len(seeds)*2
    if frame.groupby('sample_id').size().ne(expected).any():
        raise ValueError('Incomplete sample/model/seed/task product.')


def ensemble_predictions(frame, specificity=.95, seeds=(11,23,42)):
    validate_coverage(frame, sorted(frame.model.unique()), seeds)
    avg=frame.groupby(['sample_id','cluster_id','split','model','task'],as_index=False).agg(
        y_true=('y_true','first'),probability=('probability','mean'))
    avg['seed']=-1  # A declared ensemble, never an independent random-seed replicate.
    avg['threshold']=np.nan
    for (model,task),group in avg.groupby(['model','task']):
        selection=group[group.split.eq('oof_selection')]
        threshold=select_threshold(selection.y_true,selection.probability,specificity)
        avg.loc[group.index,'threshold']=threshold
    return avg


def cluster_intervals(frame,resamples=2000,seed=42):
    """Conditional held-out uncertainty; this does not resample model fitting."""
    validate_predictions(frame);rows=[]
    names=('AUROC','AUPRC','MCC','Brier','sensitivity','specificity')
    for (split,model,task),g in frame[frame.split.isin(['test','external'])].groupby(['split','model','task']):
        g=g[g.y_true.notna()].reset_index(drop=True)
        if g.sample_id.duplicated().any():raise ValueError('Use one ensemble prediction per sample for uncertainty.')
        groups=[x.index.to_numpy() for _,x in g.groupby('cluster_id')]
        if len(groups)<2:raise ValueError('At least two held-out clusters required for uncertainty.')
        y,p=g.y_true.to_numpy(),g.probability.to_numpy();threshold=float(g.threshold.iloc[0])
        rng=np.random.default_rng(seed);draws={k:[] for k in names};invalid=0
        for _ in range(resamples):
            ix=np.concatenate([groups[i] for i in rng.integers(0,len(groups),len(groups))])
            if len(set(y[ix]))!=2:invalid+=1;continue
            pred=p[ix]>=threshold
            tn,fp,fn,tp=confusion_matrix(y[ix],pred,labels=[0,1]).ravel()
            values=(roc_auc_score(y[ix],p[ix]),average_precision_score(y[ix],p[ix]),matthews_corrcoef(y[ix],pred),
                    brier_score_loss(y[ix],p[ix]),tp/(tp+fn),tn/(tn+fp))
            for k,v in zip(names,values):draws[k].append(float(v))
        if len(draws['AUPRC'])<max(20,resamples//2):raise ValueError('Too few valid cluster bootstrap draws.')
        point=binary_metrics(y,p,threshold)
        for name,values in draws.items():
            lo,hi=np.quantile(values,[.025,.975])
            rows.append({'split':split,'model':model,'task':task,'metric':name,'estimate':point[name],
                         'ci95_low':float(lo),'ci95_high':float(hi),'clusters':len(groups),'n':len(y),
                         'invalid_draws':invalid,'valid_draws':len(values),'resamples':resamples,'seed':seed,
                         'interpretation':'cluster percentile CI conditional on fitted models'})
    return rows

def aggregate_metrics(frame):
    validate_predictions(frame)
    rows=[]
    for (split,model,seed,task),g in frame.groupby(['split','model','seed','task'],sort=True):
        if g.threshold.nunique()!=1:raise ValueError('Threshold changed within evaluation cohort.')
        rows.append({'split':split,'model':model,'seed':int(seed),'task':task,
                     **binary_metrics(g.y_true,g.probability,float(g.threshold.iloc[0]))})
    return rows

def holm(pvalues):
    order=np.argsort(pvalues); adjusted=np.empty(len(order));last=0.
    for rank,index in enumerate(order):
        last=max(last,min(1.,float(pvalues[index])*(len(order)-rank)))
        adjusted[index]=last
    return adjusted.tolist()

def paired_cluster_comparison(y,ours,base,groups,resamples=2000,seed=42):
    y,ours,base,groups=map(np.asarray,(y,ours,base,groups))
    if not (len(y)==len(ours)==len(base)==len(groups)) or set(y)!={0,1}:
        raise ValueError('Paired arrays and two observed classes are required.')
    unique=np.unique(groups)
    if len(unique)<2:raise ValueError('At least two independent clusters are required.')
    rng=np.random.default_rng(seed)
    indices=[np.flatnonzero(groups==g) for g in unique]
    effect=float(average_precision_score(y,ours)-average_precision_score(y,base))
    bootstrap=[];extreme=0
    for _ in range(resamples):
        selected=rng.integers(0,len(unique),len(unique))
        ix=np.concatenate([indices[i] for i in selected])
        if len(set(y[ix]))==2:
            bootstrap.append(float(average_precision_score(y[ix],ours[ix])-average_precision_score(y[ix],base[ix])))
        swap=np.zeros(len(y),dtype=bool)
        for i,bit in enumerate(rng.integers(0,2,len(unique))):
            if bit:swap[indices[i]]=True
        a,b=np.where(swap,base,ours),np.where(swap,ours,base)
        null=float(average_precision_score(y,a)-average_precision_score(y,b))
        extreme+=abs(null)>=abs(effect)-1e-12
    if len(bootstrap)<max(20,resamples//2):raise ValueError('Too few valid cluster bootstrap draws.')
    lo,hi=np.quantile(bootstrap,[.025,.975])
    return {'metric':'AUPRC','difference':effect,'ci95_low':float(lo),'ci95_high':float(hi),
            'paired_cluster_permutation_p':(extreme+1)/(resamples+1),'clusters':len(unique),
            'valid_bootstrap_draws':len(bootstrap),'invalid_bootstrap_draws':resamples-len(bootstrap),
            'resamples':resamples,'seed':seed}

def compare_models(frame,resamples=2000):
    validate_predictions(frame)
    rows=[]
    # Only prespecified primary endpoint comparisons; seeds are averaged, not replicated samples.
    for split in ['test','external']:
        f=frame[(frame.split==split)&(frame.task=='hemo')&frame.y_true.notna()]
        if f.empty:continue
        expected_seeds=set(f.seed)
        for _,g in f.groupby(['model','sample_id']):
            if set(g.seed)!=expected_seeds:raise ValueError('Incomplete paired seed coverage.')
        avg=f.groupby(['model','sample_id','cluster_id','y_true'],as_index=False).probability.mean()
        ours=avg[avg.model.eq('dual_gated')].set_index('sample_id').sort_index()
        if ours.empty:raise ValueError('Full model predictions missing.')
        for model,g in avg.groupby('model'):
            if model=='dual_gated':continue
            base=g.set_index('sample_id').sort_index()
            if not ours.index.equals(base.index):raise ValueError('Unpaired model samples.')
            rows.append({'split':split,'comparison':'dual_gated vs '+model,
                         **paired_cluster_comparison(ours.y_true.to_numpy(),ours.probability.to_numpy(),
                                                     base.probability.to_numpy(),ours.cluster_id.to_numpy(),resamples)})
    adjusted=holm([r['paired_cluster_permutation_p'] for r in rows])
    for row,p in zip(rows,adjusted):row['holm_adjusted_p']=p
    return rows
