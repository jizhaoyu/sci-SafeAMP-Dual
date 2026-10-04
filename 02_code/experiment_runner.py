"""Run fixed, grouped, provenance-gated experiments; never use legacy CSVs."""
import argparse
import importlib.metadata
import json
import platform
import random
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from scipy.special import logit, expit
from feature_extractor import ESMFeatureExtractor, extract_handcrafted_features
from model_dual_task import SafeAMPDualNet, DualTaskLoss
from research_data import validate_records, validate_partition, TASKS, ResearchDataError
from research_utils import ROOT, read_json, write_json, sha256, utc_now
from evaluation import select_threshold, aggregate_metrics, compare_models, validate_coverage, ensemble_predictions, cluster_intervals

MODELS=('svm','rf','dual_gated','dual_concat','phys_only','esm_only','single_task')
SEEDS=(11,23,42)
CONFIG={'epochs':15,'batch_size':32,'hidden_dim':128,'dropout':.25,'lr':.001,'weight_decay':.0001,
        'svm_C':1.,'rf_trees':100,'target_specificity':.95,'seeds':list(SEEDS),'models':list(MODELS),
        'hyperparameter_selection':'fixed prespecified settings for all methods; no search',
        'primary_metric':'hemo AUPRC','probability_interpretation':'logistic calibration on development OOF scores; no clinical claim',
        'calibration':{'method':'logistic on clipped logit','C':1.,'clip':1e-6,'selection_split':'oof_selection'}}

def seed_all(seed):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(2)

def fit_network(esm,phys,labels,variant,seed,config,task=None):
    seed_all(seed)
    fusion={'dual_gated':'gated','dual_concat':'concat','phys_only':'phys_only','esm_only':'esm_only','single_task':'gated'}[variant]
    if task is not None:
        eligible=np.isfinite(labels[:,task]);esm,phys,labels=esm[eligible],phys[eligible],labels[eligible].copy()
        labels[:,1-task]=np.nan
    model=SafeAMPDualNet(hidden_dim=config['hidden_dim'],dropout_rate=config['dropout'],fusion=fusion)
    optimizer=torch.optim.AdamW(model.parameters(),lr=config['lr'],weight_decay=config['weight_decay'])
    loss_fn=DualTaskLoss()
    e,p,y=[torch.tensor(x,dtype=torch.float32) for x in (esm,phys,labels)]
    rng=np.random.default_rng(seed)
    for _ in range(config['epochs']):
        model.train()
        for start in range(0,len(y),config['batch_size']):
            # One seeded permutation per epoch, preserving every sample.
            if start==0:order=rng.permutation(len(y))
            ix=order[start:start+config['batch_size']]
            optimizer.zero_grad();a,h,_=model(e[ix],p[ix])
            loss,_,_=loss_fn(a,h,y[ix,0],y[ix,1]);loss.backward();optimizer.step()
    model.eval()
    return model

def fit_predict(kind,esm,phys,y,targets,seed,config):
    se,sp=StandardScaler().fit(esm),StandardScaler().fit(phys)
    e,p=se.transform(esm).astype('float32'),sp.transform(phys).astype('float32')
    transformed=[(se.transform(a).astype('float32'),sp.transform(b).astype('float32')) for a,b in targets]
    models=[]
    if kind in ['svm','rf']:
        x=np.concatenate([e,p],axis=1)
        for task in range(2):
            mask=np.isfinite(y[:,task])
            # SVC internal probability CV is deliberately disabled: its folds are not group-separated.
            cls=SVC(C=config['svm_C'],kernel='rbf',probability=False,random_state=seed) if kind=='svm' else RandomForestClassifier(n_estimators=config['rf_trees'],random_state=seed,n_jobs=1)
            cls.fit(x[mask],y[mask,task]);models.append(cls)
        predictions=[]
        for a,b in transformed:
            x=np.concatenate([a,b],axis=1)
            if kind=='svm':
                from scipy.special import expit
                pred=np.column_stack([expit(m.decision_function(x)) for m in models])
            else:pred=np.column_stack([m.predict_proba(x)[:,list(m.classes_).index(1)] for m in models])
            predictions.append(pred)
    else:
        if kind=='single_task':models=[fit_network(e,p,y,kind,seed,config,task=t) for t in range(2)]
        else:models=[fit_network(e,p,y,kind,seed,config)]
        predictions=[]
        for a,b in transformed:
            a,b=torch.tensor(a),torch.tensor(b)
            with torch.no_grad():
                if kind=='single_task':
                    pred=np.column_stack([torch.sigmoid(m(a,b)[t]).numpy() for t,m in enumerate(models)])
                else:
                    amp,hemo,_=models[0](a,b);pred=np.column_stack([torch.sigmoid(amp).numpy(),torch.sigmoid(hemo).numpy()])
            predictions.append(pred)
    return predictions,{'models':models,'esm_scaler':se,'phys_scaler':sp}

def prediction_rows(df,prob,kind,seed,thresholds,split=None,raw=None):
    rows=[]
    for i,r in enumerate(df.itertuples()):
        for t,task in enumerate(TASKS):
            rows.append({'sample_id':r.sample_id,'cluster_id':int(r.cluster_id),'split':split or r.split,
                         'fold':int(r.fold),'model':kind,'seed':seed,'task':task,'y_true':getattr(r,task),
                         'probability':float(prob[i,t]),'raw_probability':float((prob if raw is None else raw)[i,t]),'threshold':float(thresholds[t])})
    return rows

def load_dataset(folder):
    folder=Path(folder)
    if folder.is_file() or folder.suffix=='.csv':
        raise ResearchDataError(f"load_dataset requires a validated prepared directory, not a CSV file ({folder}). Run research_data.py to prepare.")
    manifest_file = folder/'manifest.json'
    if not manifest_file.is_file():
        raise ResearchDataError(f"Missing manifest.json in prepared directory: {folder}")
    manifest=read_json(manifest_file)
    if manifest.get('status')!='validated':
        if manifest.get('status')=='cohorts_built':
            raise ResearchDataError(f"Directory {folder} status is 'cohorts_built', not 'validated'. A prepared and validated dataset directory is required.")
        raise ResearchDataError(f"Dataset has not passed research validation (status: {manifest.get('status')}).")
    from dataclasses import asdict
    from research_protocol_config import get_protocol, check_protocol_conflicts, protocol_digest
    try:
        spec = get_protocol(manifest.get('protocol_id', 'legacy-v1'))
    except KeyError as exc:
        raise ResearchDataError(str(exc)) from exc
    has_conflict, conflict_reason = check_protocol_conflicts(spec)
    if has_conflict:
        raise ResearchDataError(conflict_reason)
    if spec.protocol_id == 'protocol-amd-02' and (
        manifest.get('protocol_spec') != asdict(spec)
        or manifest.get('protocol_digest') != protocol_digest(spec)
    ):
        raise ResearchDataError('Prepared strict protocol specification or digest mismatch.')
    for name,key in [('dataset.csv','dataset_sha256'),('records.csv','provenance_sha256')]:
        if sha256(folder/name)!=manifest.get(key):raise ResearchDataError('Prepared data checksum mismatch.')
    records=validate_records(pd.read_csv(folder/'records.csv'))
    data=pd.read_csv(folder/'dataset.csv')
    if spec.protocol_id == 'protocol-amd-02':
        from research_data import assert_study_independence, analyze_homology
        assert_study_independence(records)
        expected, _, _, audit = analyze_homology(records, spec)
        if audit['cross_pair_violations']:
            raise ResearchDataError('Prepared strict protocol has cross-cohort homology violations.')
        expected_groups = expected.set_index('sample_id')['cluster_id'].sort_index()
        actual_groups = data.set_index('sample_id')['cluster_id'].sort_index()
        try:
            pd.testing.assert_series_equal(expected_groups, actual_groups, check_dtype=False)
        except AssertionError as exc:
            raise ResearchDataError('Prepared strict protocol cluster membership differs from all-member replay.') from exc
        for name, key in (
            ('cross_cohort_similarity.csv', 'cross_cohort_similarity_sha256'),
            ('homology_audit.json', 'homology_audit_sha256'),
        ):
            if not (folder / name).is_file() or sha256(folder / name) != manifest.get(key):
                raise ResearchDataError(f'Prepared strict protocol audit missing or checksum mismatch: {name}')
    from research_data import consolidate_records
    derived,_=consolidate_records(records)
    left=data.set_index('sample_id')[['seq','amp','hemo','source_role']].sort_index()
    right=derived.set_index('sample_id')[['seq','amp','hemo','source_role']].sort_index()
    try:pd.testing.assert_frame_equal(left,right,check_dtype=False)
    except AssertionError as exc:raise ResearchDataError('Dataset labels do not match source records.') from exc
    validate_partition(data,manifest['cutoff'],protocol=manifest.get('protocol_id'))
    return data,manifest

def run(dataset_dir,output_dir,config=None):
    config=dict(CONFIG if config is None else config)
    if set(config['models'])!=set(MODELS) or set(config['seeds'])!=set(SEEDS):
        raise ValueError('Formal protocol requires all seven models and three prespecified seeds.')
    output=Path(output_dir)
    if output.exists():raise ValueError('Run directory exists; runs are immutable.')
    output.mkdir(parents=True)
    manifest={'status':'running','created_at':utc_now(),'config':config,'dataset_dir':str(Path(dataset_dir).resolve()),
              'python':platform.python_version(),'software':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','scikit-learn','torch','fair-esm']},
              'code_hashes':{p.name:sha256(p) for p in Path(__file__).parent.glob('*.py')},'formal_results_available':False,'publication_ready':False}
    write_json(output/'manifest.json',manifest)
    try:
        data,dm=load_dataset(dataset_dir);manifest['dataset_manifest']=dm
        extractor=ESMFeatureExtractor()
        if not extractor.real_esm_available:raise RuntimeError('Real ESM is mandatory.')
        checkpoint=Path(torch.hub.get_dir())/'checkpoints/esm2_t6_8M_UR50D.pt'
        if extractor.backend!='fair-esm' or not checkpoint.is_file():
            raise RuntimeError('This protocol requires the hashed official fair-esm checkpoint.')
        manifest['features']={'backend':extractor.backend,'version':extractor.feature_version,'esm_sha256':sha256(checkpoint)}
        seed_all(42)
        esms=[];phys=[]
        for seq in data.seq:
            emb,_=extractor.extract_sequence_embedding(seq);esms.append(emb);phys.append(extract_handcrafted_features(seq))
        e,p=np.asarray(esms,dtype='float32'),np.asarray(phys,dtype='float32')
        np.savez_compressed(output/'features.npz',esm=e,phys=p,sample_ids=data.sample_id.to_numpy(dtype=str))
        manifest['features_sha256']=sha256(output/'features.npz')
        dev=np.flatnonzero(data.split.eq('development'));held=np.flatnonzero(data.split.ne('development'))
        y=data[list(TASKS)].to_numpy(dtype='float32');rows=[];checkpoints=[]
        for kind in config['models']:
            for seed in config['seeds']:
                oof=np.full((len(dev),2),np.nan)
                for fold in range(5):
                    mask=data.iloc[dev].fold.to_numpy()==fold;a,b=dev[~mask],dev[mask]
                    pred,_=fit_predict(kind,e[a],p[a],y[a],[(e[b],p[b])],seed,config)
                    oof[mask]=pred[0]
                if not np.isfinite(oof).all():raise ValueError('Incomplete out-of-fold predictions.')
                calibration=[];calibrated=oof.copy()
                for t in range(2):
                    mask=np.isfinite(y[dev,t]);x=logit(np.clip(oof[:,t],1e-6,1-1e-6)).reshape(-1,1)
                    calibrator=LogisticRegression(C=1.,solver='lbfgs',random_state=seed).fit(x[mask],y[dev,t][mask])
                    calibration.append({'coefficient':float(calibrator.coef_[0,0]),'intercept':float(calibrator.intercept_[0])})
                    calibrated[:,t]=calibrator.predict_proba(x)[:,1]
                thresholds=[select_threshold(y[dev,t],calibrated[:,t],config['target_specificity']) for t in range(2)]
                rows.extend(prediction_rows(data.iloc[dev],calibrated,kind,seed,thresholds,'oof_selection',raw=oof))
                pred,fitted=fit_predict(kind,e[dev],p[dev],y[dev],[(e[held],p[held])],seed,config)
                raw_held=pred[0].copy()
                for t,c in enumerate(calibration):
                    pred[0][:,t]=expit(c['coefficient']*logit(np.clip(pred[0][:,t],1e-6,1-1e-6))+c['intercept'])
                rows.extend(prediction_rows(data.iloc[held],pred[0],kind,seed,thresholds,raw=raw_held))
                import joblib
                artifact=output/f'{kind}_seed_{seed}.joblib'
                joblib.dump({'fitted':fitted,'calibration':calibration,'thresholds':thresholds},artifact)
                manifest.setdefault('model_artifacts',[]).append({'path':artifact.name,'sha256':sha256(artifact)})
                if kind=='dual_gated':
                    cp=output/f'dual_gated_seed_{seed}.pt'
                    torch.save({'state_dict':fitted['models'][0].state_dict(),
                                'esm_mean':fitted['esm_scaler'].mean_.tolist(),'esm_scale':fitted['esm_scaler'].scale_.tolist(),
                                'phys_mean':fitted['phys_scaler'].mean_.tolist(),'phys_scale':fitted['phys_scaler'].scale_.tolist(),
                                'thresholds':thresholds,'calibration':calibration,'features':manifest['features'],'config':config,'seed':seed},cp)
                    checkpoints.append({'path':cp.name,'sha256':sha256(cp),'seed':seed})
                pd.DataFrame(rows).to_csv(output/'predictions.partial.csv',index=False)
                print(f'Completed {kind}, seed {seed}',flush=True)
        predictions=pd.DataFrame(rows)
        validate_coverage(predictions,config['models'],config['seeds'])
        predictions.to_csv(output/'predictions.csv',index=False)
        ensemble=ensemble_predictions(predictions,config['target_specificity'])
        ensemble.to_csv(output/'ensemble_predictions.csv',index=False)
        write_json(output/'ensemble_metrics.json',aggregate_metrics(ensemble))
        write_json(output/'confidence_intervals.json',cluster_intervals(ensemble))
        write_json(output/'metrics.json',aggregate_metrics(predictions))
        write_json(output/'comparisons.json',compare_models(predictions))
        manifest.update(
            completed_at=utc_now(),
            predictions_sha256=sha256(output/'predictions.csv'),
            checkpoints=checkpoints,
            metrics_sha256=sha256(output/'metrics.json'),
            comparisons_sha256=sha256(output/'comparisons.json'),
            ensemble_predictions_sha256=sha256(output/'ensemble_predictions.csv'),
            ensemble_metrics_sha256=sha256(output/'ensemble_metrics.json'),
            confidence_intervals_sha256=sha256(output/'confidence_intervals.json')
        )
        from run_artifacts import validate_artifact_payloads
        validate_artifact_payloads(output, manifest)
        manifest.update(status='completed', formal_results_available=True, publication_ready=False)
    except Exception as exc:
        manifest.update(status='failed', reason=str(exc), formal_results_available=False, publication_ready=False)
        write_json(output/'manifest.json', manifest)
        raise
    write_json(output/'manifest.json',manifest)
    return manifest

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:print(json.dumps(run(args.dataset,args.output),ensure_ascii=False))
    except (ValueError,RuntimeError,FileNotFoundError) as exc:parser.exit(2,str(exc)+'\n')

if __name__=='__main__':main()
