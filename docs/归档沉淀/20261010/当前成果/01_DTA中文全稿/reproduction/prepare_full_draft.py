"""Assemble data-bound manuscript tables and consistency evidence. No model fit or extraction."""
import hashlib
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd
import runpy

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent.parent
REV=ROOT/'output/dta-paper-run-v5-revised-v2-20261009'
RUN=ROOT/'output/dta-paper-run-v5-20261009'
PREP=ROOT/'output/dta-paper-manuscript-prep-v1-20261009'
SEEDS=[42,123,456,789,1024]
TAGS={'Ridge':'RIDGE','HistGBM':'HGB','RandomForest':'RF','NNLS Stacking':'STACK'}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def table(frame):
    cols=list(frame.columns)
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for row in frame.itertuples(index=False,name=None):
        out.append('| '+' | '.join(f'{x:.6f}' if isinstance(x,(float,np.floating)) else str(x) for x in row)+' |')
    return '\n'.join(out)

def main():
    for folder in ['tables','evidence']:
        (OUT/folder).mkdir(parents=True,exist_ok=True)
    m=json.loads((REV/'metrics_summary_revised.json').read_text(encoding='utf-8'))
    stats=json.loads((REV/'statistical_inference_report_revised.json').read_text(encoding='utf-8'))
    index=json.loads((REV/'manifests/file_digests_manifest.json').read_text(encoding='utf-8'))
    for item in index.values():
        assert sha(REV/item['path'])==item['sha256']
    helper=runpy.run_path(str(ROOT/'output/dta-paper-run-v5-independent-review-20261009/reproduction/audit_run.py'))
    pairs=pd.read_csv(ROOT/'03_experiments/prepared/dti_davis_clean_features_20261009_v1/pairs_metadata.csv',dtype={'drug_id':str,'target_id':str})
    train=pairs[pairs.domain=='train_block'].sort_values(['drug_id','target_id']).reset_index(drop=True)
    y=train.pkd.to_numpy(dtype=np.float32)
    p=stats['primary_comparison']['overall_sample_bootstrap']
    primary=[];derived=[]
    for seed in SEEDS:
        with np.load(RUN/'checkpoints'/f'SET-D-S{seed}.npz') as d,np.load(RUN/'checkpoints'/f'SET-A-S{seed}.npz') as a:
            doof=helper['ci'](y,d[f'oof_EXP-MAIN-D-STACK-S{seed}'])
            aoof=helper['ci'](y,a[f'oof_EXP-MAIN-A-STACK-S{seed}'])
            diffs={tag:float(np.max(np.abs(d[f'eval_EXP-MAIN-D-{tag}-S{seed}']-a[f'eval_EXP-MAIN-A-{tag}-S{seed}']))) for tag in ['RIDGE','HGB','RF']}
        assert abs(doof-m[f'EXP-MAIN-D-STACK-S{seed}']['oof_diagnostic']['concordance_index'])<1e-6
        assert abs(aoof-m[f'EXP-MAIN-A-STACK-S{seed}']['oof_diagnostic']['concordance_index'])<1e-6
        primary.append({'种子':seed,'D外层CI':p['point_ci_design_d_by_seed'][str(seed)],
            'A外层CI':p['point_ci_design_a_by_seed'][str(seed)],
            'D减A外层CI':p['point_ci_design_d_by_seed'][str(seed)]-p['point_ci_design_a_by_seed'][str(seed)],
            'D元层拟合诊断CI':doof,'A元层拟合诊断CI':aoof})
        derived.append({'seed':seed,**diffs})
    primary=pd.DataFrame(primary)
    display=primary.copy()
    values=primary.iloc[:,1:]
    display=pd.concat([display,pd.DataFrame([{'种子':'均值',**values.mean().to_dict()}, {'种子':'样本标准差',**values.std(ddof=1).to_dict()}])],ignore_index=True)
    model=pd.DataFrame([{'模型':name,**{k:m[f'EXP-MAIN-D-{tag}-S42']['eval_overall'][k] for k in ['concordance_index','rmse','mae','pearson_r','spearman_rho']}} for name,tag in TAGS.items()])
    ablation=[]
    for f,dim in [('F1',2156),('F2',2476),('F3',2668),('F4',2988)]:
        st=f'EXP-ABL-{f}-STACK-S42' if f!='F4' else 'EXP-MAIN-D-STACK-S42'
        rid=f'EXP-ABL-{f}-RIDGE-S42' if f!='F4' else 'EXP-MAIN-D-RIDGE-S42'
        v=m[st]['eval_overall']
        ablation.append({'特征':f,'维度':dim,'Stacking CI':v['concordance_index'],
            'RMSE':v['rmse'],'MAE':v['mae'],'Pearson r':v['pearson_r'],
            '较F1的CI点差':v['concordance_index']-m['EXP-ABL-F1-STACK-S42']['eval_overall']['concordance_index'],
            'Ridge CI':m[rid]['eval_overall']['concordance_index']})
    sequence=[]
    for tag,label in [('TRUNC','L1硬截断'),('WINDOW','L2滑窗均值')]:
        sequence.append({'处理':label,**{k:m[f'EXP-SEQ-{tag}-STACK-S42']['eval_overall'][k] for k in ['concordance_index','rmse','mae','pearson_r','spearman_rho']}})
    domain=[]
    for code,label,n in [('cold_drug_test','冷药',3952),('cold_target_test','冷靶',4125),('strict_dual_cold_test','双冷',975)]:
        exp=f'EXP-EVAL-{code.upper()}-STACK' if code!='strict_dual_cold_test' else 'EXP-MAIN-D-STACK-S42'
        domain.append({'域':label,'配对':n,**{k:m[exp]['eval_overall'][k] for k in ['concordance_index','rmse','mae','pearson_r','spearman_rho']}})
    weights=[]
    for seed in SEEDS:
        w=json.loads((RUN/'models'/f'EXP-MAIN-D-STACK-S{seed}_weights.json').read_text(encoding='utf-8'))['weights']
        weights.append({'种子':seed,'Ridge系数':w['ridge'],'HistGBM系数':w['hist_gradient_boosting'],
            'RF系数':w['random_forest'],'树模型系数和':w['hist_gradient_boosting']+w['random_forest'],
            '全部系数和':sum(w.values())})
    tables={'表1_五种子主比较':display,'表2_F4基模型与集成':model,'表3_特征消融':pd.DataFrame(ablation),
        '表4_长序列对照':pd.DataFrame(sequence),'表5_分域结果':pd.DataFrame(domain),'表6_NNLS原始系数':pd.DataFrame(weights)}
    for name,frame in tables.items():
        frame.to_csv(OUT/'tables'/f'{name}.csv',index=False,encoding='utf-8-sig',float_format='%.12g')
        (OUT/'tables'/f'{name}.md').write_text(table(frame)+'\n',encoding='utf-8')
    corrections=[
        {'项目':'F2 Ridge CI','任务书':'0.721201','已验收实际':'0.715267','证据':'EXP-ABL-F2-RIDGE-S42/eval_overall'},
        {'项目':'A元层拟合诊断CI均值','任务书':'0.725424','已验收实际':f"{values['A元层拟合诊断CI'].mean():.6f}",'证据':'SET-A-S*.npz OOF独立重算'},
        {'项目':'D元层拟合诊断CI均值','任务书':'0.589021','已验收实际':f"{values['D元层拟合诊断CI'].mean():.6f}",'证据':'SET-D-S*.npz OOF独立重算'},
        {'项目':'seed42外层差值','任务书':'0.102613','已验收实际':f"{primary.iloc[0]['D减A外层CI']:.6f}",'证据':'高精度CI先相减再四舍五入'},
        {'项目':'seed789外层差值','任务书':'0.074149','已验收实际':f"{primary.iloc[3]['D减A外层CI']:.6f}",'证据':'高精度CI先相减再四舍五入'},
        {'项目':'seed1024外层差值','任务书':'0.039445','已验收实际':f"{primary.iloc[4]['D减A外层CI']:.6f}",'证据':'高精度CI先相减再四舍五入'},
        {'项目':'HistGBM外层指标','任务书':'RMSE0.8987/MAE0.6115/r0.0987/rho0.1512','已验收实际':'与当前JSON一致，不应误改','证据':'EXP-MAIN-D-HGB-S42/eval_overall'}]
    pd.DataFrame(corrections).to_csv(OUT/'evidence/任务书数值差异.csv',index=False,encoding='utf-8-sig')
    save={'primary_outer':p,'oof_diagnostic_means':values.mean().to_dict(),
        'oof_diagnostic_sds':values.std(ddof=1).to_dict(),'corrections':corrections,
        'base_prediction_difference_d_vs_a':derived,'fit_calls':0,'scope':'read-only manuscript preparation checks',
        'input_hashes':{str(REV/item['path']):item['sha256'] for item in index.values()}}
    (OUT/'evidence/numeric_basis.json').write_text(json.dumps(save,ensure_ascii=False,indent=2),encoding='utf-8')
    for filename in ['references.bib','图注与图表说明.md','参考文献核验.md']:
        (OUT/filename).write_bytes((PREP/filename).read_bytes())
    # Source manifest copied as evidence, retaining author-verification pending state.
    (OUT/'evidence/source_manifest.json').write_bytes((PREP/'evidence/source_manifest.json').read_bytes())
    print(json.dumps({'status':'PASS','tables':6,'oof_means':{'A':values['A元层拟合诊断CI'].mean(),'D':values['D元层拟合诊断CI'].mean()},'fit_calls':0},ensure_ascii=False))

if __name__=='__main__': main()
