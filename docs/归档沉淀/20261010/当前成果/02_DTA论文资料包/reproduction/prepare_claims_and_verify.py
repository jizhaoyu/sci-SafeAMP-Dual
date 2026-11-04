"""Bind authored claims to checked source IDs and verify the manuscript package."""
import csv
import hashlib
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image

OUT=Path(__file__).resolve().parent.parent
ROOT=OUT.parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

CLAIMS=[
 ('C001','本地DAVIS包含68药、379靶、25772对，文献版本不同。','E003,E013','方法2.1/摘要','不能说明差异形成原因'),
 ('C002','训练16720、双冷975、冷药3952、冷靶4125；长靶子集属于冷靶域。','E003,E004','方法2.2/表T7','长靶子集不能与四块重复求和'),
 ('C003','特征采用自定义循环哈希、8维近似摘要、100维序列统计、512维启发式图特征及320维ESM；F1–F4维度一致。','E005,E007,E008,E009','方法2.3/表T8','不是标准Morgan、实验口袋、ProtVec或真实Uni-Mol'),
 ('C004','三种固定基模型及无截距NNLS在训练OOF上拟合，外层结果单独评价。','E005,E010','方法2.4','元层拟合诊断不能当未见评价；不是新训练前快照'),
 ('C005','A配对五折、D25块实体隔离；主种子五个，B/C和辅助对照seed42。','E004,E005,E006','方法2.2','不同内折训练规模，不能归因于单一机制'),
 ('C006','主要效应为各种子CI差均值，使用共同实体乘积重数Bootstrap描述性区间。','E002,E005,E011','方法2.6','种子不是独立测试样本；无p值'),
 ('C007','全样本点差+0.070184，95%描述性区间[-0.000964,0.157289]包含0。','E002,E011','摘要/结果3.1/图1','不能确认稳定优势或等效'),
 ('C008','pKd>5的263对子集点差+0.030647，区间[-0.003347,0.091659]包含0。','E002,E003,E011','结果3.1/图1','子集不替代主终点'),
 ('C009','F4下五个D种子的Stacking均低于对应Ridge，seed42基模型结果已核实。','E001,E011','结果3.2/图2','限当前配置和划分'),
 ('C010','seed42 Stacking的F2较F1低0.008399，F3较F1低0.054543；Ridge的F3略高于F1。','E001,E002','结果3.3/图3','单种子模块结果，不否定预训练模型普遍有效性'),
 ('C011','L1/L2按C评估15个未见长靶、825对；Stacking CI差-0.003750，部分误差指标改善。','E001,E002,E005,E009','结果3.4/图4','没有等效检验或多种子确认'),
 ('C012','保存标签采用nM到pKd约定，18343对为5、7429对高于5，逐条边界语义未知。','E003,E013','方法2.1','不自动认定每条删失或真实强活性'),
 ('C013','DeepDTA原论文Table 1/Equation 1提供版本统计和pKd转换背景。','E013','引言/参考核验R1','文献表不证明本地转换链'),
 ('C014','ESM官方表为6层8M320维型号，本地窗口均值代码可定位。','E009,E014','引言/方法2.5','官方架构文档不单独证明历史运行身份'),
 ('C015','历史测试已经查看，当前结果始终为探索性。','E010,E012','方法2.1/讨论','多种子和审计不恢复盲测'),
 ('C016','seed42分域CI为冷药0.748009、冷靶0.746004、双冷0.681706。','E001,E002','结果3.4/表T6','不同域不是同一样本上的因果比较'),
 ('C017','历史训练前完整代码绑定、墙钟日志及若干科学有效性检查仍缺证据。','E010,E011,E012','讨论/待补清单','当前摘要只提供事后身份锚定'),
 ('C018','本轮作者、刊物、声明和人工核验未确认，资料包不能直接投稿。','E019','作者事项/README','准备状态记录，不是科学结果主张')]

def main():
    sources=json.loads((OUT/'evidence/source_manifest.json').read_text(encoding='utf-8'))
    if not any(s['evidence_id']=='E019' for s in sources['sources']):
        status_path=OUT/'evidence/preparation_status.json'
        sources['sources'].append({'evidence_id':'E019','type':'local','path':str(status_path),
            'sha256':sha(status_path),'locator':'draft status and author/venue confirmation fields',
            'agent_checked':True,'human_verified':False,'status':'pending_author_verification'})
        (OUT/'evidence/source_manifest.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')
    source_ids={s['evidence_id'] for s in sources['sources']}
    readable=['# 主张与证据表','',
        '状态：代理已核对的工作稿；人工原文与文件核验待作者完成。CSV保存主张文本SHA256，本文提供可读文本。','',
        '| 主张编号 | 可写内容 | 证据编号 | 定位 | 结论边界 |','|---|---|---|---|---|']
    rows=[]
    for cid,text,evidence,locator,limit in CLAIMS:
        assert set(evidence.split(','))<=source_ids
        readable.append(f'| {cid} | {text} | {evidence} | {locator} | {limit} |')
        rows.append({'claim_id':cid,'claim_text_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'evidence_ids':evidence,'manuscript_locator':locator,
            'agent_check_status':'checked_with_stated_limits','human_verification_status':'pending',
            'human_verifier':'','human_verified_at':'','limitation':limit})
    with (OUT/'evidence/claims.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (OUT/'主张与证据表.md').write_text('\n'.join(readable)+'\n',encoding='utf-8')
    known={r[0] for r in CLAIMS}
    used=set()
    for path in OUT.glob('*.md'):
        used.update(re.findall(r'\[claim:(C\d+)\]',path.read_text(encoding='utf-8')))
    assert used<=known and known<=used
    for source in sources['sources']:
        assert source['human_verified'] is False
        if source['type']=='local':
            assert sha(Path(source['path']))==source['sha256']
    for original in sources['artifact_bindings']:
        assert sha(Path(original['path']))==original['sha256']
    t1=pd.read_csv(OUT/'tables/T1_primary_seed_pairs.csv')
    t2=pd.read_csv(OUT/'tables/T2_primary_effect_intervals.csv')
    assert np.allclose(t1.ci_design_d-t1.ci_design_a,t1.delta_d_minus_a,rtol=0,atol=1e-11)
    assert abs(t1.delta_d_minus_a.mean()-t2.iloc[0].delta)<1e-11
    assert all(t2.interval_low<0) and all(t2.interval_high>0)
    t3=pd.read_csv(OUT/'tables/T3_models_all_seeds.csv')
    pivot=t3.pivot(index='seed',columns='model',values='concordance_index')
    assert (pivot['Ridge']>pivot['NNLS Stacking']).all()
    t4=pd.read_csv(OUT/'tables/T4_feature_ablation_seed42.csv')
    ab=t4[t4.model=='NNLS Stacking'].set_index('feature')
    assert abs((ab.loc['F2','concordance_index']-ab.loc['F1','concordance_index'])+0.008399)<1e-9
    for path in (OUT/'figures').glob('*.png'):
        with Image.open(path) as im:
            assert im.width>=2000 and im.height>=1000
            im.verify()
    result={'status':'PASS','claims':len(CLAIMS),'claim_tags_used':len(used),
        'local_sources_sha_match':True,'original_artifact_bindings':len(sources['artifact_bindings']),
        'figure_pngs':len(list((OUT/'figures').glob('*.png'))),
        'figure_svgs':len(list((OUT/'figures').glob('*.svg'))),
        'visual_review':'Four figures manually viewed; F1 labels adjusted and re-viewed.',
        'publication_status':'not_submission_ready','human_source_verification':'pending',
        'fit_calls':0,'inputs_modified':False,'new_experiments':False}
    (OUT/'reproduction/package_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    files={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='artifact_manifest.json'}
    (OUT/'artifact_manifest.json').write_text(json.dumps({'status':'draft_pending_author_review','submission_ready':False,
        'files':files,'verification':result},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
