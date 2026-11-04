"""Verify documentary corrections and unchanged previously audited numerical artifacts."""
import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
REV=ROOT/'output/dta-paper-run-v5-revised-v2-20261009'
PREV=ROOT/'output/dta-paper-run-v5-revised-20261009'
OUT=Path(__file__).resolve().parent.parent

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    trace=json.loads((REV/'manifests/traceability_index.json').read_text(encoding='utf-8'))
    script_checks={rel: {'exists':(ROOT/rel).is_file(),
                        'hash_matches':(ROOT/rel).is_file() and sha(ROOT/rel)==digest}
                   for rel,digest in trace['codebase_anchor']['key_script_hashes_sha256'].items()}
    assert all(v['exists'] and v['hash_matches'] for v in script_checks.values())
    manifest=json.loads((REV/'manifests/file_digests_manifest.json').read_text(encoding='utf-8'))
    artifact_checks={key: {'digest_matches':sha(REV/info['path'])==info['sha256'],
                           'same_as_previous_audited':sha(REV/info['path'])==sha(PREV/info['path'])}
                     for key,info in manifest.items()}
    assert all(v['digest_matches'] and v['same_as_previous_audited'] for v in artifact_checks.values())
    data_anchor=trace['input_data_anchor']
    metadata=pd.read_csv(data_anchor['benchmark_dataset']['path'],dtype={'drug_id':str,'target_id':str})
    totals={'total_pairs':len(metadata),'total_drugs':int(metadata.drug_id.nunique()),'total_targets':int(metadata.target_id.nunique())}
    expected=data_anchor['benchmark_dataset']['total_dataset_statistics']
    assert all(totals[k]==expected[k] for k in totals)
    actual_domains={}
    for domain,group in metadata.groupby('domain'):
        actual={'pairs':len(group),'drugs':int(group.drug_id.nunique()),'targets':int(group.target_id.nunique())}
        assert actual==data_anchor['benchmark_dataset']['evaluation_domains_statistics'][domain]
        actual_domains[domain]=actual
    splitdir=Path(data_anchor['split_manifests_directory'])
    splits={name:(splitdir/name).is_file() for name in data_anchor['split_manifests']}
    assert all(splits.values()) and len(splits)==12
    metrics=json.loads((REV/'metrics_summary_revised.json').read_text(encoding='utf-8'))
    stats=json.loads((REV/'statistical_inference_report_revised.json').read_text(encoding='utf-8'))
    primary=stats['primary_comparison']['overall_sample_bootstrap']
    assert round(primary['primary_point_estimate_delta'],6)==0.070184
    assert primary['percentile_95_descriptive_interval'][0]<0<primary['percentile_95_descriptive_interval'][1]
    actual_models=[m['name'] for m in trace['model_configurations']['base_models']]
    assert actual_models==['ridge','hist_gradient_boosting','random_forest']
    assert trace['model_configurations']['meta_learner']['name']=='nnls_meta_learner'
    report={'status':'PASS','code_anchors':script_checks,'numerical_artifacts':artifact_checks,
       'dataset_statistics':totals,'domain_statistics':actual_domains,'actual_split_paths':splits,
       'model_names':actual_models,'model_ci_seed42':{name:metrics[f'EXP-MAIN-D-{tag}-S42']['eval_overall']['concordance_index']
           for name,tag in [('ridge','RIDGE'),('hist_gradient_boosting','HGB'),('random_forest','RF'),('stacked_ensemble','STACK')]},
       'primary_effect':primary['primary_point_estimate_delta'],
       'primary_interval':primary['percentile_95_descriptive_interval'],
       'historical_omissions':trace['historical_record_omissions'],
       'document_hashes':{p.name:sha(p) for p in REV.glob('*.md')}}
    (OUT/'independent-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
