"""Independent matrix and declared split checks. Never fits models."""
import json
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent.parent
DELIVERY=ROOT/'output/dta-paper-protocol-v5'

def main():
    m=pd.read_csv(DELIVERY/'实验矩阵.csv')
    assert m.experiment_id.is_unique
    by_id={r.experiment_id:r for r in m.itertuples()}
    graph={}
    for row in m.itertuples():
        deps=[] if row.reuse_source_exp_id=='none' else row.reuse_source_exp_id.split(',')
        assert all(d in by_id for d in deps),(row.experiment_id,deps)
        for d in deps:
            other=by_id[d]
            assert row.feature_version==other.feature_version
            assert row.seed==other.seed
            if row.inner_validation_design!='none_evaluation_only':
                assert row.inner_validation_design==other.inner_validation_design
        graph[row.experiment_id]=deps
    visited=set()
    active=set()
    def visit(key):
        assert key not in active,key
        if key in visited:
            return
        active.add(key)
        for dep in graph[key]:
            visit(dep)
        active.remove(key)
        visited.add(key)
    for key in graph:
        visit(key)
    parts=['param_selection_fits','oof_fits','meta_fits','final_refits']
    assert (m[parts].sum(axis=1)==m.total_fits).all()
    assert np.allclose(m.total_fits*m.est_sec_per_fit,m.total_cost_sec,rtol=0,atol=1e-8)
    pure=m[m.inner_validation_design=='none_evaluation_only']
    assert (pure[parts+['total_fits']]==0).all().all()
    seeds=[42,123,456,789,1024]
    for design in ['pair_kfold_5','bicluster_group_kfold_25']:
        subset=m[(m.model_id=='stacked_ensemble')&(m.research_question=='Primary RQ')&(m.inner_validation_design==design)]
        assert sorted(subset.seed.tolist())==seeds
    split_checks=[]
    for seed in seeds:
        drug_groups=np.array_split(np.random.default_rng(seed).permutation(55),5)
        target_groups=np.array_split(np.random.default_rng(seed+10000).permutation(304),5)
        counts=np.zeros((55,304),dtype=np.int8)
        for d in drug_groups:
            for t in target_groups:
                counts[np.ix_(d,t)]+=1
                assert not set(d)&set(np.setdiff1d(np.arange(55),d))
                assert not set(t)&set(np.setdiff1d(np.arange(304),t))
        assert np.all(counts==1)
        split_checks.append({'seed':seed,'unique_oof_pairs':int((counts==1).sum()),'blocks':25})
    report={'status':'PASS','matrix_rows':len(m),'dependency_resolution':'PASS',
        'dependency_feature_seed_matching':'PASS','acyclic':True,
        'totals':{key:int(m[key].sum()) for key in parts+['total_fits']},
        'estimated_fit_seconds':float(m.total_cost_sec.sum()),'pure_inference_rows':len(pure),
        'primary_seeds':seeds,'declared_split_formula_checks':split_checks,
        'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DELIVERY.iterdir() if p.is_file()}}
    (OUT/'independent-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='source_hashes'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
