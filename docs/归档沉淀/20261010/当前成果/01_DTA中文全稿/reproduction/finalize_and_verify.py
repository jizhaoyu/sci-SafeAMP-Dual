"""Render source-derived tables into the new draft and verify bounded claims."""
import csv
import hashlib
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent.parent
PREP=ROOT/'output/dta-paper-manuscript-prep-v1-20261009'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def counts(text):
    text=re.sub(r'https?://[^\s)]+','',text)
    chinese=len(re.findall(r'[\u4e00-\u9fff]',text))
    english=len(re.findall(r'[A-Za-z]+(?:[-–][A-Za-z]+)*',text))
    numbers=len(re.findall(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?',text))
    return {'chinese_characters':chinese,'english_word_tokens':english,'numeric_tokens':numbers,
            'combined_count_estimate':chinese+english+numbers}

def main():
    template=(OUT/'论文全稿_中文_排版源.md').read_text(encoding='utf-8')
    names=['表1_五种子主比较','表2_F4基模型与集成','表3_特征消融','表4_长序列对照','表5_分域结果','表6_NNLS原始系数']
    text=template
    for i,name in enumerate(names,1):
        token=f'<!-- TABLE{i} -->'
        assert text.count(token)==1
        text=text.replace(token,f'**表{i} {name.split("_",1)[1]}**\n\n'+(OUT/'tables'/f'{name}.md').read_text(encoding='utf-8'))
    assert not re.findall(r'<!-- TABLE\d+ -->',text)
    (OUT/'论文全稿_中文.md').write_text(text,encoding='utf-8')
    # Reuse checked plot assets; do not generate new experimental analysis.
    (OUT/'figures').mkdir(exist_ok=True)
    for p in (PREP/'figures').iterdir():
        if p.is_file(): (OUT/'figures'/p.name).write_bytes(p.read_bytes())
    for p in (PREP/'tables').glob('*.csv'):
        (OUT/'tables'/p.name).write_bytes(p.read_bytes())
    (OUT/'主张与证据表_继承图注编号.md').write_bytes((PREP/'主张与证据表.md').read_bytes())
    (OUT/'evidence/claims_figure_captions.csv').write_bytes((PREP/'evidence/claims.csv').read_bytes())
    source_index=json.loads((OUT/'evidence/source_manifest.json').read_text(encoding='utf-8'))
    source_index['preparation_note']='Inherited local identities; public-source checks refreshed 2026-10-10. Human verification remains pending.'
    if not any(source['evidence_id']=='E020' for source in source_index['sources']):
        source_index['sources'].append({'evidence_id':'E020','type':'local',
            'path':str(ROOT/'output/dta-paper-manuscript-prep-v2-20261010/GPT_DTA论文全稿写作任务提示词.md'),
            'sha256':sha(ROOT/'output/dta-paper-manuscript-prep-v2-20261010/GPT_DTA论文全稿写作任务提示词.md'),
            'locator':'task specification and factual correction items',
            'agent_checked':True,'human_verified':False,'status':'instructions_not_primary_result_evidence'})
    (OUT/'evidence/source_manifest.json').write_text(json.dumps(source_index,ensure_ascii=False,indent=2),encoding='utf-8')
    mapping=[
        ('F001','摘要、2.1、2.2','dataset facts and numeric label convention','E003,E013','已核对','边界语义和版本差异原因未知'),
        ('F002','2.3','actual split rules, coverage and train sizes','E004,E005,E006','代码/实际清单核对','ID隔离不代表所有泄漏路径消失'),
        ('F003','2.4、2.6','feature identities, dimensions and sequence handling','E007,E008,E009,E014','代码及官方模型表核对','不称标准Morgan、真实Uni-Mol或实测口袋'),
        ('F004','2.5、2.7','fixed parameters, NNLS and descriptive interval definition','E005,E010,E011','已核对','参数历史探索、元层分数为拟合诊断'),
        ('F005','3.1、表1','raw precision primary effect and corrected OOF diagnostics','E001,E002,E011','检查点独立重算','区别任务和元层拟合；不作显著性'),
        ('F006','3.2、表2、表6','base/ensemble results and saved NNLS coefficients','E001,E002','已核对','系数不是概率、重要性或已证实机制'),
        ('F007','3.3、表3','feature ablation including corrected F2 Ridge','E001,E002','已核对','seed42探索性，不作普适否定'),
        ('F008','3.4、表4–5','sequence and domain results','E001,E002','已核对','没有等效检验，不是因果衰减估计'),
        ('F009','4.1','readonly D/A final prediction differences','E005,E011','本次额外产物核对','不等于新预设假设检验'),
        ('F010','4.2–4.5','possible explanations and mathematical properties','E005,E007,E009','理论推导/待验证假说','不作已验证生物机制或保证改进'),
        ('F011','5、8','limits, pending declarations and human responsibility','E010,E012,E019','状态/审计范围记录','不是期刊许可或人工已签认')]
    with (OUT/'evidence/章节主张与证据.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['claim_id','section','claim_scope','source_ids','status','limitation']);w.writerows(mapping)
    primary=pd.read_csv(OUT/'tables/表1_五种子主比较.csv')
    seedrows=primary.iloc[:5]
    assert np.allclose(seedrows['D外层CI']-seedrows['A外层CI'],seedrows['D减A外层CI'],atol=1e-11,rtol=0)
    assert abs(seedrows['D减A外层CI'].mean()-0.07018400588529985)<1e-11
    ab=pd.read_csv(OUT/'tables/表3_特征消融.csv')
    assert float(ab[ab['特征']=='F2']['Ridge CI'].iloc[0])==0.715267
    forbidden=['\\begin{aligned}','\\begin{array}','\\mathbf','\\dfrac']
    assert not any(t in text for t in forbidden)
    assert not re.search(r'\bp\s*[<=>]\s*0\.0[15]',text)
    body=text.split('## 7 参考文献')[0]
    without_tables=re.sub(r'(?m)^\|.*\n?','',body)
    abstract=text.split('## 摘要',1)[1].split('## 1 引言',1)[0]
    section_counts={}
    for match in re.finditer(r'(?m)^## ([1-6]) ([^\n]+)',text):
        tail=text[match.end():]
        section=tail.split('\n## ',1)[0]
        section_counts[match.group(1)+' '+match.group(2)]=counts(re.sub(r'(?m)^\|.*\n?','',section))
    report={'status':'PASS','manuscript_body_excluding_tables':counts(without_tables),
        'abstract':counts(abstract),'section_counts':section_counts,'tables':6,'references':4,
        'fit_calls':0,'new_experiments':False,'publication_ready':False,
        'human_verification':'pending','latex_format_checks':'PASS','numeric_checks':'PASS'}
    (OUT/'reproduction/verification_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    # Snapshot sources after preparation: inherited identities must remain unchanged.
    for source in source_index['sources']:
        if source['type']=='local':
            assert sha(Path(source['path']))==source['sha256'],source['evidence_id']
    for binding in source_index['artifact_bindings']:
        assert sha(Path(binding['path']))==binding['sha256'],binding['path']
    files={str(path.relative_to(OUT)):sha(path) for path in OUT.rglob('*') if path.is_file() and path.name!='artifact_manifest.json'}
    (OUT/'artifact_manifest.json').write_text(json.dumps({'status':'draft_pending_author_review',
        'submission_ready':False,'files':files,'verification':report},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
