"""Explicit, frozen training and no-fit verification for the original-figure release."""
from __future__ import annotations

import argparse
import json
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import train_mic_reviewed_baseline as base
from mic_followup_release import audit_partition
from research_evidence_gate import verify_manifest, workspace_path
from research_utils import ROOT, read_json, sha256, utc_now, write_json
from validate_mic_three_fold_run import independent_metrics
from train_mic_baselines import compute_metrics

ENTRY=Path(__file__).resolve()
DEPENDENCIES=('02_code/train_mic_reviewed_baseline.py','02_code/train_mic_three_fold_v2.py',
              '02_code/research_evidence_gate.py','02_code/mic_followup_release.py',
              '02_code/research_data.py','02_code/public_data.py','02_code/feature_extractor.py',
              '02_code/validate_mic_acid_progress.py','02_code/validate_mic_three_fold_run.py',
              '02_code/research_utils.py')
MODELS={'logistic_regression':{'C':1.0,'class_weight':'balanced','max_iter':5000,'solver':'lbfgs','random_state':42},
        'random_forest':{'n_estimators':500,'min_samples_leaf':2,'max_depth':None,'class_weight':'balanced','n_jobs':1,'random_state':42},
        'dummy_prior':{'strategy':'prior'}}


def check(condition, message):
    if not condition: raise ValueError(message)


def verify_state(path):
    state=read_json(path)
    check(state['status']=='ready_for_local_exploratory_training' and state['training_blocked'] is False
          and state['training_started'] is False and state['blockers']==[], 'Not an admitted pre-training state')
    for name,digest in state['inputs'].items():
        check(sha256(workspace_path(name))==digest,'Readiness input changed: '+name)
    check(state['inputs'].get(ENTRY.relative_to(ROOT).as_posix())==sha256(ENTRY),'Readiness does not bind this entry')
    return state


def check_partition(cohort_dir, release_dir, audit_path):
    cohort=verify_manifest(cohort_dir);release=verify_manifest(release_dir)
    audit=read_json(audit_path)
    check(release['full_release_review_complete'] is True and release['cohort_manifest_sha256']==sha256(cohort_dir/'manifest.json'),'Incomplete/mismatched release')
    mol=pd.read_csv(cohort_dir/'candidate_molecules.csv',keep_default_na=False)
    obs=pd.read_csv(cohort_dir/'candidate_observations.csv',keep_default_na=False)
    src=pd.read_csv(release_dir/'source_review.csv',keep_default_na=False)
    roles=pd.read_csv(cohort_dir/'fold_roles.csv',keep_default_na=False)
    pairs=pd.read_csv(cohort_dir/'all_member_similarity.csv',keep_default_na=False)
    current=audit_partition(mol,obs,src,roles,pairs)
    check(current['status']==audit['status']=='passed','Independent partition gate blocked')
    for key in ('molecules','observations','pairs_recomputed','cross_fold_homology_edges','cross_fold_primary_studies'):
        check(current[key]==audit[key],'Independent partition differs: '+key)
    check(cohort['validation']=={'folds':3,'shuffle':True,'seed':42},'Fixed split specification differs')
    return mol,obs,roles


def freeze(cohort_dir,release_dir,audit_path,ready_path,protocol_path,freeze_path):
    paths=[Path(p).resolve() for p in (cohort_dir,release_dir,audit_path,ready_path,protocol_path,freeze_path)]
    cohort_dir,release_dir,audit_path,ready_path,protocol_path,freeze_path=paths
    check(all(p.is_relative_to(ROOT) for p in paths),'Freeze paths must be in workspace')
    check(protocol_path==ROOT/'03_experiments/protocols/protocol-mic-11.json','Unexpected reserved protocol location')
    if protocol_path.exists() or freeze_path.exists(): raise FileExistsError('Protocol/freeze already exists')
    state=verify_state(ready_path)
    mol,obs,roles=check_partition(cohort_dir,release_dir,audit_path)
    check(len(mol)>15 and len(obs)>22,'No scientifically admitted expansion')
    scientific_path=ROOT/'03_experiments/protocols/protocol-mic-06.json'
    scientific=read_json(scientific_path)
    protocol={'protocol_id':'protocol-mic-11','protocol_version':1,
              'status':'frozen_local_exploratory_baseline_training','frozen_at':utc_now(),
              'research_stage':'follow-up exploratory analysis; historical performance already known; not preregistration',
              'scope':'E. coli MIC classification; small sample; no external or clinical claim; no dual-task or publication authorization',
              'scientific_protocol_path':scientific_path.relative_to(ROOT).as_posix(),
              'scientific_protocol_sha256':sha256(scientific_path),
              'label_rule':scientific['label_rule'],'similarity':scientific['similarity'],
              'molecule_domain':scientific['molecule_domain'],
              'environment':base._environment(),'readiness_state':ready_path.relative_to(ROOT).as_posix(),
              'readiness_state_sha256':sha256(ready_path),'models':MODELS,'decision_threshold':.5,
              'validation':{'folds':3,'shuffle':True,'seed':42,'identity_cutoff':.40,'identity_mode':'alignment','features':'fixed_handcrafted_44'},
              'features_spec':{'extractor':'02_code/feature_extractor.py','extractor_sha256':sha256(ROOT/'02_code/feature_extractor.py'),'dimensions':44},
              'observation_ids':sorted(obs.record_id.astype(str)),
              'training_entry_sha256':sha256(ENTRY),'models_training_entry':ENTRY.relative_to(ROOT).as_posix(),
              'dependency_sha256':{name:sha256(ROOT/name) for name in DEPENDENCIES},
              'model_selection':'none; all predeclared models; no tuning, calibration or feature selection',
              'formal_state_path':'04_paper/research_status.json','formal_state_sha256':sha256(ROOT/'04_paper/research_status.json')}
    materials={'cohort_manifest':cohort_dir/'manifest.json','evidence_release_manifest':release_dir/'manifest.json',
               'independent_partition_validation':audit_path,'molecules':cohort_dir/'candidate_molecules.csv',
               'observations':cohort_dir/'candidate_observations.csv','fold_roles':cohort_dir/'fold_roles.csv'}
    for key,path in materials.items():
        protocol[key]=path.relative_to(ROOT).as_posix();protocol[key+'_sha256']=sha256(path)
    base._make_models(protocol)
    protocol_path.parent.mkdir(parents=True,exist_ok=True);write_json(protocol_path,protocol)
    record={'protocol_id':'protocol-mic-11','frozen_at':utc_now(),'protocol_file_sha256':sha256(protocol_path),
            'training_entry_sha256':sha256(ENTRY),'model_training_started':False,
            'dependency_sha256':protocol['dependency_sha256'],'readiness_state_sha256':sha256(ready_path)}
    write_json(freeze_path,record)
    return record


def load(protocol_path,freeze_path):
    check(Path(protocol_path).is_file() and Path(freeze_path).is_file(),'Mandatory frozen protocol and record missing')
    protocol=read_json(protocol_path)
    check(protocol['training_entry_sha256']==sha256(ENTRY),'Frozen entry changed')
    scientific_path=workspace_path(protocol['scientific_protocol_path'])
    check(sha256(scientific_path)==protocol['scientific_protocol_sha256'],'Scientific protocol changed')
    scientific=read_json(scientific_path)
    check(all(protocol[key]==scientific[key] for key in ('label_rule','similarity','molecule_domain')),'Scientific definitions differ')
    check(set(protocol['dependency_sha256'])==set(DEPENDENCIES),'Incomplete dependency binding')
    for name,digest in protocol['dependency_sha256'].items():
        check(sha256(ROOT/name)==digest,'Frozen dependency changed: '+name)
    verify_state(workspace_path(protocol['readiness_state']))
    base.TRAIN_ENTRY=ENTRY
    result=base._load_and_validate(Path(protocol_path),Path(freeze_path))
    check_partition(workspace_path(protocol['cohort_manifest']).parent,
                    workspace_path(protocol['evidence_release_manifest']).parent,
                    workspace_path(protocol['independent_partition_validation']))
    return result


def train(output,protocol_path,freeze_path):
    load(protocol_path,freeze_path)
    base.TRAIN_ENTRY=ENTRY
    base.compute_metrics=compute_metrics
    return base.train(Path(output),Path(protocol_path),Path(freeze_path))


def validate(run_dir,output,protocol_path,freeze_path):
    run_dir,output=Path(run_dir).resolve(),Path(output).resolve()
    if output.exists(): raise FileExistsError(output)
    check(not output.is_relative_to(run_dir),'Validation must not mutate frozen run')
    protected=[Path(protocol_path),Path(freeze_path),run_dir/'manifest.json',ROOT/'04_paper/research_status.json']
    before={p:sha256(p) for p in protected}
    with ExitStack() as stack:
        for cls in (LogisticRegression,RandomForestClassifier,DummyClassifier,StandardScaler,Pipeline):
            stack.enter_context(patch.object(cls,'fit',side_effect=AssertionError('No fit during independent verification')))
        protocol,mol,roles,features=load(protocol_path,freeze_path)
        manifest=read_json(run_dir/'manifest.json')
        check(manifest['protocol_sha256']==sha256(protocol_path) and manifest['freeze_sha256']==sha256(freeze_path),'Run binding changed')
        check(manifest['training_started'] is True and manifest['publication_ready'] is False and manifest['formal_results_available'] is False,'Run scope changed')
        for name,digest in manifest['outputs'].items(): check(sha256(run_dir/name)==digest,'Run artifact changed: '+name)
        actual_files={p.relative_to(run_dir).as_posix() for p in run_dir.rglob('*') if p.is_file() and p.name!='manifest.json'}
        check(actual_files==set(manifest['outputs']),'Unmanifested run artifacts')
        expected_files={'fixed_features.npy','fold_metrics.csv','oof_predictions.csv','pooled_descriptive_metrics.csv','report.md'}|{f'fold_models/{name}_fold{fold}.joblib' for name in MODELS for fold in range(3)}
        check(actual_files==expected_files,'Expected nine models and complete outputs')
        np.testing.assert_allclose(np.load(run_dir/'fixed_features.npy',allow_pickle=False),features,rtol=0,atol=1e-12)
        predictions=pd.read_csv(run_dir/'oof_predictions.csv',float_precision='round_trip')
        check(len(predictions)==len(mol)*3 and not predictions.duplicated(['model','sample_id']).any(),'OOF sample coverage differs')
        positions={sample:i for i,sample in enumerate(mol.sample_id)}
        y=mol.amp.astype(int).to_numpy();metrics=[]
        for fold in range(3):
            selected=roles[roles.fold.astype(int).eq(fold)]
            train_ids=selected[selected.role.eq('train')].sample_id.tolist()
            val_ids=selected[selected.role.eq('validation')].sample_id.tolist()
            tr=np.asarray([positions[s] for s in train_ids]);va=np.asarray([positions[s] for s in val_ids])
            for name in MODELS:
                model=joblib.load(run_dir/f'fold_models/{name}_fold{fold}.joblib')
                estimator=model.named_steps['clf'] if isinstance(model,Pipeline) and 'clf' in model.named_steps else (model.steps[-1][1] if isinstance(model,Pipeline) else model)
                expected=base._make_models(protocol)[name]
                expected_estimator=expected.steps[-1][1] if isinstance(expected,Pipeline) else expected
                check(estimator.get_params(deep=False)==expected_estimator.get_params(deep=False),'Model parameters changed')
                check(estimator.classes_.tolist()==[0,1],'Class ordering differs')
                if isinstance(model,Pipeline):
                    check(len(model.steps)==2 and isinstance(model.steps[0][1],StandardScaler),'Unexpected preprocessing')
                    scaler=model.steps[0][1]
                    np.testing.assert_allclose(scaler.mean_,features[tr].mean(axis=0),rtol=0,atol=1e-12)
                    np.testing.assert_allclose(scaler.var_,features[tr].var(axis=0),rtol=0,atol=1e-12)
                    check(int(scaler.n_samples_seen_)==len(tr),'Scaler fit sample count differs')
                if name=='dummy_prior': np.testing.assert_allclose(estimator.class_prior_,np.bincount(y[tr],minlength=2)/len(tr),rtol=0,atol=1e-12)
                scores=model.predict_proba(features[va])[:,1]
                rows=predictions[(predictions.model==name)&(predictions.fold==fold)].set_index('sample_id')
                check(len(rows)==len(val_ids) and set(rows.index)==set(val_ids),'OOF fold membership differs')
                np.testing.assert_allclose(rows.loc[val_ids,'probability'].to_numpy(),scores,rtol=0,atol=1e-12)
                check(rows.loc[val_ids,'observed_label'].astype(int).tolist()==y[va].tolist(),'OOF labels changed')
                metrics.append({'model':name,'fold':fold,**independent_metrics(y[va],scores)})
        pooled=[{'model':name,**independent_metrics(part.observed_label.to_numpy(),part.probability.to_numpy())} for name,part in predictions.groupby('model',sort=True)]
        for filename,expected_rows,keys in [('fold_metrics.csv',metrics,['model','fold']),('pooled_descriptive_metrics.csv',pooled,['model'])]:
            stored=pd.read_csv(run_dir/filename).sort_values(keys).reset_index(drop=True)
            expected=pd.DataFrame(expected_rows).sort_values(keys).reset_index(drop=True)
            check(stored[keys].to_dict('records')==expected[keys].to_dict('records'),'Metric row inventory differs')
            cols=[c for c in expected.columns if c not in keys]
            np.testing.assert_allclose(stored[cols].to_numpy(dtype=float),expected[cols].to_numpy(dtype=float),rtol=0,atol=1e-12,equal_nan=True)
        check(all(sha256(p)==digest for p,digest in before.items()),'Verification mutated protected artifacts')
    result={'status':'passed','generated_at':utc_now(),'protocol_id':'protocol-mic-11','models_reloaded':9,
            'oof_rows_independently_recomputed':len(predictions),'fit_calls_during_validation':0,
            'scaler_training_range_verified':True,'pooled_descriptive_metrics':pooled,'formal_results_available':False,
            'publication_ready':False,'inputs':{p.relative_to(ROOT).as_posix():sha256(p) for p in protected+[ENTRY]},
            'run_directory':run_dir.relative_to(ROOT).as_posix()}
    write_json(output,result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('freeze')
    for name in ('cohort','release','partition','readiness','protocol','freeze'):p.add_argument('--'+name,required=True,type=Path)
    for command in ('train','validate'):
        p=sub.add_parser(command)
        p.add_argument('--output',required=True,type=Path);p.add_argument('--protocol',required=True,type=Path);p.add_argument('--freeze',required=True,type=Path)
        if command=='validate':p.add_argument('--run',required=True,type=Path)
    args=parser.parse_args()
    if args.command=='freeze':result=freeze(args.cohort,args.release,args.partition,args.readiness,args.protocol,args.freeze)
    elif args.command=='train':result=train(args.output,args.protocol,args.freeze)
    else:result=validate(args.run,args.output,args.protocol,args.freeze)
    print(json.dumps(result,ensure_ascii=False,indent=2))
