"""Build manuscript source tables, evidence, and provisional figures from accepted artifacts.

No fitting, feature extraction, dependency installation, or modification of upstream files.
"""
import csv
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent.parent
REV=ROOT/'output/dta-paper-run-v5-revised-v2-20261009'
SEEDS=[42,123,456,789,1024]
MODEL_TAGS={'Ridge':'RIDGE','HistGBM':'HGB','RandomForest':'RF','NNLS Stacking':'STACK'}
COLORS={'Ridge':'#0072B2','HistGBM':'#D55E00','RandomForest':'#009E73','NNLS Stacking':'#6A3D9A'}
MARKERS={'Ridge':'o','HistGBM':'s','RandomForest':'D','NNLS Stacking':'^'}
METRICS=['concordance_index','rmse','mae','pearson_r','spearman_rho']

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def save_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def markdown_table(frame):
    columns=frame.columns.tolist()
    lines=['| '+' | '.join(columns)+' |','| '+' | '.join(['---']*len(columns))+' |']
    for row in frame.itertuples(index=False,name=None):
        vals=[f'{v:.6f}' if isinstance(v,(float,np.floating)) else str(v) for v in row]
        lines.append('| '+' | '.join(vals)+' |')
    return '\n'.join(lines)

def main():
    if (OUT/'artifact_manifest.json').exists():
        raise FileExistsError('Existing manuscript package: do not overwrite it.')
    for name in ['tables','figures','evidence']:
        (OUT/name).mkdir(parents=True,exist_ok=True)
    manifest=json.loads((REV/'manifests/file_digests_manifest.json').read_text(encoding='utf-8'))
    for record in manifest.values():
        assert sha(REV/record['path'])==record['sha256']
    metrics=json.loads((REV/'metrics_summary_revised.json').read_text(encoding='utf-8'))
    stats=json.loads((REV/'statistical_inference_report_revised.json').read_text(encoding='utf-8'))
    metadata=pd.read_csv(ROOT/'03_experiments/prepared/dti_davis_clean_features_20261009_v1/pairs_metadata.csv',dtype={'drug_id':str,'target_id':str})
    primary=stats['primary_comparison']['overall_sample_bootstrap']
    subset=stats['primary_comparison']['active_subset_pkd_gt_5_bootstrap']
    pairing=pd.DataFrame([{'seed':s,'ci_design_d':primary['point_ci_design_d_by_seed'][str(s)],
        'ci_design_a':primary['point_ci_design_a_by_seed'][str(s)],
        'delta_d_minus_a':primary['point_ci_design_d_by_seed'][str(s)]-primary['point_ci_design_a_by_seed'][str(s)]} for s in SEEDS])
    assert abs(pairing.delta_d_minus_a.mean()-primary['primary_point_estimate_delta'])<1e-12
    summary=pd.DataFrame([{'track':name,'n_pairs':n,'delta':source['primary_point_estimate_delta'],
        'interval_low':source['percentile_95_descriptive_interval'][0],
        'interval_high':source['percentile_95_descriptive_interval'][1],
        'seed_difference_sd':source['training_stochasticity_diff_std_ddof1'],
        'b_requested':source['b_requested'],'b_valid':source['b_valid'],
        'interval_definition':'entity-paired bootstrap percentile descriptive interval'}
        for name,n,source in [('all_pairs',975,primary),('pkd_gt_5',263,subset)]])
    model_rows=[]
    for name,tag in MODEL_TAGS.items():
        for seed in SEEDS:
            exp=f'EXP-MAIN-D-{tag}-S{seed}'
            model_rows.append({'experiment_id':exp,'model':name,'seed':seed,
                'feature':'F4','scenario':'strict_dual_cold_test',**{k:metrics[exp]['eval_overall'][k] for k in METRICS}})
    model_frame=pd.DataFrame(model_rows)
    ablation_rows=[]
    for feature,dim in [('F1',2156),('F2',2476),('F3',2668),('F4',2988)]:
        for name,tag in MODEL_TAGS.items():
            exp=f'EXP-ABL-{feature}-{tag}-S42' if feature!='F4' else f'EXP-MAIN-D-{tag}-S42'
            ablation_rows.append({'experiment_id':exp,'feature':feature,'dimension':dim,
                'model':name,'seed':42,**{k:metrics[exp]['eval_overall'][k] for k in METRICS}})
    ablation=pd.DataFrame(ablation_rows)
    sequence_rows=[]
    for code,label in [('TRUNC','L1: first 1022 residues'),('WINDOW','L2: sliding-window means')]:
        for name,tag in MODEL_TAGS.items():
            exp=f'EXP-SEQ-{code}-{tag}-S42'
            sequence_rows.append({'experiment_id':exp,'sequence_handling':label,'model':name,
                'seed':42,'n_targets':15,'n_pairs':825,
                **{k:metrics[exp]['eval_overall'][k] for k in METRICS}})
    sequence=pd.DataFrame(sequence_rows)
    domain_rows=[]
    for domain in ['strict_dual_cold_test','cold_drug_test','cold_target_test']:
        for name,tag in MODEL_TAGS.items():
            exp=f'EXP-MAIN-D-{tag}-S42' if domain=='strict_dual_cold_test' else f'EXP-EVAL-{domain.upper()}-{tag}'
            domain_rows.append({'experiment_id':exp,'scenario':domain,'model':name,'seed':42,
                **{k:metrics[exp]['eval_overall'][k] for k in METRICS}})
    domains=pd.DataFrame(domain_rows)
    dataset=pd.DataFrame([{'domain':domain,'pairs':len(frame),'drugs':frame.drug_id.nunique(),
        'targets':frame.target_id.nunique(),'pkd_gt_5_pairs':int((frame.pkd>5).sum()),
        'is_disjoint_partition':True} for domain,frame in metadata.groupby('domain')])
    assert dataset.pairs.sum()==25772
    features=pd.DataFrame([
        {'feature':'F1','drug_base':2056,'drug_heuristic':0,'target_statistics':100,'esm2':0,'dimension':2156},
        {'feature':'F2','drug_base':2056,'drug_heuristic':0,'target_statistics':100,'esm2':320,'dimension':2476},
        {'feature':'F3','drug_base':2056,'drug_heuristic':512,'target_statistics':100,'esm2':0,'dimension':2668},
        {'feature':'F4','drug_base':2056,'drug_heuristic':512,'target_statistics':100,'esm2':320,'dimension':2988}])
    tables={'T1_primary_seed_pairs.csv':pairing,'T2_primary_effect_intervals.csv':summary,
        'T3_models_all_seeds.csv':model_frame,'T4_feature_ablation_seed42.csv':ablation,
        'T5_sequence_handling_seed42.csv':sequence,'T6_domains_seed42.csv':domains,
        'T7_data_partitions.csv':dataset,'T8_feature_dimensions.csv':features}
    for name,frame in tables.items():
        frame.to_csv(OUT/'tables'/name,index=False,float_format='%.12g',encoding='utf-8-sig')
    flat=[]
    for exp,record in metrics.items():
        flat.append({'experiment_id':exp,'model_id':record['model_id'],'feature_version':record['feature_version'],
            'seed':record['seed'],'inner_validation_design':record['inner_validation_design'],
            'evaluation_domain':record['evaluation_domain'],**record['eval_overall']})
    pd.DataFrame(flat).to_csv(OUT/'tables/S1_all_76_experiments.csv',index=False,encoding='utf-8-sig')
    figure_registry=[]
    style={'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':12,
           'axes.labelsize':10,'axes.spines.top':False,'axes.spines.right':False,
           'svg.fonttype':'none','savefig.facecolor':'white','axes.grid':False}
    def export(fig,name,tables_used,description):
        fig.savefig(OUT/'figures'/f'{name}.png',dpi=300,facecolor='white')
        fig.savefig(OUT/'figures'/f'{name}.svg',facecolor='white')
        png=OUT/'figures'/f'{name}.png'
        with Image.open(png) as im:
            pixels=list(im.size)
        figure_registry.append({'figure_id':name,'formats':['png','svg'],'png_pixels':pixels,
            'tables':tables_used,'description':description,'journal_requirements':'not_selected',
            'status':'provisional_author_review_pending','uncertainty':'defined in captions; no p-values',
            'transformations':'existing values only; no filtering by outcome, no fit, no smoothing'})
        plt.close(fig)
    with plt.rc_context(style):
        fig,axes=plt.subplots(1,2,figsize=(11.2,4.5),layout='constrained',gridspec_kw={'width_ratios':[1.15,1]})
        ax=axes[0]
        for i,row in pairing.iterrows():
            ax.plot([0,1],[row.ci_design_a,row.ci_design_d],color='#AAAAAA',linewidth=1,zorder=1)
        ax.scatter(np.zeros(5),pairing.ci_design_a,color='#D55E00',marker='s',s=50,label='A: pair random 5-fold',zorder=2)
        ax.scatter(np.ones(5),pairing.ci_design_d,color='#0072B2',marker='o',s=50,label='D: entity grid 25-block',zorder=2)
        for label_y,(_,row) in zip(np.linspace(.57,.75,5),pairing.sort_values('ci_design_d').iterrows()):
            ax.annotate(str(int(row.seed)),(1,row.ci_design_d),xytext=(1.20,label_y),textcoords='data',
                fontsize=8,va='center',arrowprops={'arrowstyle':'-','color':'#AAAAAA','lw':.6})
        ax.set(xlim=(-.25,1.55),ylim=(0,1),xticks=[0,1],xticklabels=['Design A','Design D'],ylabel='Concordance index',title='A  Paired seed realizations')
        ax.legend(loc='lower left',fontsize=8)
        ax=axes[1]
        ax.axvline(0,color='#777777',linestyle='--',linewidth=1)
        for i,row in summary.iterrows():
            center=row.delta
            ax.errorbar(center,1-i,xerr=np.array([[center-row.interval_low],[row.interval_high-center]]),
                color='#333333',marker='o',capsize=5,linewidth=2)
            ax.text(.177,1-i,f'{center:+.4f}',ha='right',va='bottom',fontsize=9)
        ax.set(yticks=[1,0],yticklabels=['All pairs (n=975)','pKd > 5 (n=263)'],ylim=(-.5,1.5),
            xlim=(-.035,.185),xlabel='Mean paired CI difference (D minus A)',title='B  Descriptive entity-bootstrap intervals')
        fig.suptitle('Primary comparison on the same dual-cold domain | five seeds',fontsize=13)
        export(fig,'F1_primary_comparison',['T1_primary_seed_pairs.csv','T2_primary_effect_intervals.csv'],
            'Paired points for each seed and two 95% percentile descriptive intervals crossing zero.')
        fig,ax=plt.subplots(figsize=(8.0,4.5),layout='constrained')
        for j,(name,tag) in enumerate(MODEL_TAGS.items()):
            frame=model_frame[model_frame.model==name]
            x=j+np.linspace(-.12,.12,5)
            ax.scatter(x,frame.concordance_index,color=COLORS[name],marker=MARKERS[name],s=50,zorder=3)
            ax.plot([j-.18,j+.18],[frame.concordance_index.mean()]*2,color='#222222',linewidth=2,zorder=4)
        ax.set(xticks=range(4),xticklabels=list(MODEL_TAGS),ylim=(0,1),ylabel='Concordance index',
            title='F4 models on the dual-cold domain | Design D, five seeds')
        ax.text(.02,.05,'Points: individual seeds; black lines: arithmetic means.\nSeeds describe algorithmic variation, not independent test datasets.',
            transform=ax.transAxes,fontsize=8)
        export(fig,'F2_model_comparison',['T3_models_all_seeds.csv'],
            'All five seed values per model; Ridge exceeds the other current F4 models.')
        fig,ax=plt.subplots(figsize=(8.8,4.7),layout='constrained')
        for j,name in enumerate(MODEL_TAGS):
            frame=ablation[ablation.model==name]
            x=np.arange(4)+(j-1.5)*.12
            ax.scatter(x,frame.concordance_index,color=COLORS[name],marker=MARKERS[name],s=55,label=name,zorder=3)
        ax.set(xticks=range(4),xticklabels=['F1: base','F2: + ESM-2','F3: + heuristic','F4: both'],
            ylim=(0,1),ylabel='Concordance index',title='Feature-module ablation | Design D, seed 42 only')
        ax.legend(loc='lower left',ncol=2,fontsize=9)
        ax.text(.02,.20,'Single-seed descriptive ablation; no uncertainty or significance claim.',transform=ax.transAxes,fontsize=8)
        export(fig,'F3_feature_ablation',['T4_feature_ablation_seed42.csv'],
            'Four feature sets for all four model outputs, including adverse and model-dependent effects.')
        fig,ax=plt.subplots(figsize=(8.2,4.6),layout='constrained')
        for j,name in enumerate(MODEL_TAGS):
            frame=sequence[sequence.model==name]
            vals=frame.concordance_index.to_numpy()
            ax.plot([j-.12,j+.12],vals,color='#BBBBBB',linewidth=1,zorder=1)
            ax.scatter(j-.12,vals[0],color='#0072B2',marker='s',s=60,label='L1: first 1022' if j==0 else None,zorder=2)
            ax.scatter(j+.12,vals[1],color='#D55E00',marker='o',s=60,label='L2: window means' if j==0 else None,zorder=2)
        ax.set(xticks=range(4),xticklabels=list(MODEL_TAGS),ylim=(0,1),ylabel='Concordance index',
            title='Long-target sequence handling | Design C, seed 42')
        ax.legend(loc='lower left',fontsize=9)
        ax.text(.02,.18,'15 unseen long targets; 55 known drugs; 825 pairs.\nPoint estimates only; no equivalence conclusion.',transform=ax.transAxes,fontsize=8)
        export(fig,'F4_long_sequence_comparison',['T5_sequence_handling_seed42.csv'],
            'L1 and L2 point estimates for all models on the same fifteen unseen long targets.')
    save_json(OUT/'figures/figure_manifest.json',figure_registry)
    local_sources=[
        ('E001',REV/'metrics_summary_revised.json','experiment_id -> eval_overall/oof_diagnostic'),
        ('E002',REV/'statistical_inference_report_revised.json','primary_comparison and secondary comparisons'),
        ('E003',CLEAN_PATH:=ROOT/'03_experiments/prepared/dti_davis_clean_features_20261009_v1/pairs_metadata.csv','domain/drug_id/target_id/pkd'),
        ('E004',ROOT/'output/dta-paper-protocol-v5/实验矩阵.csv','76 experiment IDs, feature/version/seed/dependencies'),
        ('E005',ROOT/'output/dta-paper-run-v5-20261009/scripts/run_experiments_v5.py','DTADataLoader/get_base_model/execute_all_experiments'),
        ('E006',ROOT/'output/dta-paper-run-v5-20261009/scripts/split_generator.py','generate_design_a/b/c/d'),
        ('E007',ROOT/'02_code/extract_dti_davis_enhanced_features.py','extract_enhanced_drug_features/extract_enhanced_kinase_features'),
        ('E008',ROOT/'02_code/extract_unimol_features.py','extract_heuristic_geom_features and component functions'),
        ('E009',ROOT/'02_code/extract_esm_kinase_features.py','extract_esm_kinase_representation'),
        ('E010',ROOT/'output/dta-paper-run-v5-20261009/preflight/frozen_execution_contract.json','assets_binding/model_configurations/environment'),
        ('E011',ROOT/'output/dta-paper-run-v5-independent-review-20261009/independent-results.json','independent bootstrap/model/split/numerical checks'),
        ('E012',ROOT/'output/dta-paper-run-v5-revised-v2-independent-review-20261009/DTA修订交付v2独立验收结论_本轮通过.md','bounded acceptance and remaining limitations')]
    sources=[{'evidence_id':eid,'type':'local','path':str(path),'sha256':sha(path),'locator':locator,
              'agent_checked':True,'human_verified':False,'status':'pending_author_verification'}
             for eid,path,locator in local_sources]
    for eid,title,url,locator,state in [
        ('E013','DeepDTA original paper','https://arxiv.org/html/1801.10193v2','Data sets/Table 1/Equation 1','primary_full_text_opened'),
        ('E014','ESM official repository','https://github.com/facebookresearch/esm','Pre-trained models table/ESM-2 citation','official_document_opened'),
        ('E015','Scientific Agent Skills','https://arxiv.org/abs/2609.00065','metadata and abstract','primary_metadata_opened'),
        ('E016','Davis original study','https://www.nature.com/articles/nbt.1990','not verified due access restriction','access_failed_not_used_to_verify_claims')]:
        sources.append({'evidence_id':eid,'type':'external','title':title,'url':url,'locator':locator,
            'accessed_at':'2026-10-09','agent_check_status':state,'human_verified':False,'status':'pending_author_verification'})
    # Bind all actual manifests, high-precision checkpoints and final weights without duplicating them.
    extra=[]
    for folder,pattern in [('splits','*.json'),('checkpoints','SET-*.npz'),('models','*')]:
        for path in sorted((ROOT/'output/dta-paper-run-v5-20261009'/folder).glob(pattern)):
            if path.is_file(): extra.append({'path':str(path),'sha256':sha(path),'role':folder})
    save_json(OUT/'evidence/source_manifest.json',{'human_verification_required':True,'sources':sources,'artifact_bindings':extra})
    facts={'primary':primary,'subset':subset,
        'data_counts':{'pairs':len(metadata),'drugs':metadata.drug_id.nunique(),'targets':metadata.target_id.nunique(),
            'pkd_eq_5':int((metadata.pkd==5).sum()),'pkd_gt_5':int((metadata.pkd>5).sum())},
        'feature_dimensions':dict(zip(features.feature,features.dimension))}
    save_json(OUT/'evidence/numeric_facts.json',facts)
    presentation=['# 结果表（供作者核对）','',
        '所有表由已验收JSON或元数据生成。完整精度见CSV；展示数值不代表重新训练。','',
        '## 表1 五种子主比较','',markdown_table(pairing),'',
        '## 表2 主比较描述性区间','',markdown_table(summary.drop(columns=['interval_definition'])),'',
        '## 表3 F4/设计D/seed42模型比较','',markdown_table(model_frame[model_frame.seed==42][['model']+METRICS]),'',
        '## 表4 seed42特征消融（所有模型）','',markdown_table(ablation[['feature','dimension','model']+METRICS]),'',
        '## 表5 seed42长序列对照','',markdown_table(sequence[['sequence_handling','model','n_targets','n_pairs']+METRICS]),'',
        '## 表6 数据划分','',markdown_table(dataset)]
    (OUT/'结果表.md').write_text('\n'.join(presentation)+'\n',encoding='utf-8')
    expected_rows={'T1_primary_seed_pairs.csv':5,'T2_primary_effect_intervals.csv':2,
        'T3_models_all_seeds.csv':20,'T4_feature_ablation_seed42.csv':16,
        'T5_sequence_handling_seed42.csv':8,'T6_domains_seed42.csv':12,
        'T7_data_partitions.csv':4,'T8_feature_dimensions.csv':4}
    assert all(len(tables[name])==n for name,n in expected_rows.items())
    save_json(OUT/'reproduction/build_checks.json',{'status':'PASS','table_row_counts':expected_rows,
        'experiments_in_supplement':len(flat),'figure_count':len(figure_registry),
        'fit_calls':0,'feature_extraction_calls':0,'inputs_hash_checked':True,
        'python':platform.python_version(),'matplotlib':matplotlib.__version__,
        'numerical_stage':'accepted artifacts reused; no new scientific experiment'})
    files={str(path.relative_to(OUT)):sha(path) for path in OUT.rglob('*') if path.is_file()}
    save_json(OUT/'artifact_manifest.json',{'status':'draft_pending_author_review','submission_ready':False,
        'files':files,'note':'Bibliographic human verification and final visual review pending.'})
    print(json.dumps({'status':'PASS','tables':len(tables)+1,'figures':len(figure_registry),'sources':len(sources),'bound_original_files':len(extra)},ensure_ascii=False))

if __name__=='__main__':
    main()
