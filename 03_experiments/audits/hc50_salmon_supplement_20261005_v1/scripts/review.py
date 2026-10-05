"""Reproduce the five-record supplement/identity audit without formal release or fitting."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile
from bs4 import BeautifulSoup
import fitz
from acquire import BASE, ROOT, PREVIOUS, PRIOR_SHA, sha, write_json

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def require(condition,message):
    if not condition:
        raise ValueError(message)


def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream))


def write_rows(path,data):
    with path.open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)


def database_field(soup,name):
    heading=next(node for node in soup.find_all('h4') if node.get_text(strip=True)==name)
    return heading.parent.find_next_sibling().get_text(' ',strip=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve()
    require(out.is_relative_to(BASE) and not out.exists(),'Choose a new output directory in this audit')
    acquisition=BASE/'acquisition'
    manifest=json.loads((acquisition/'manifest.json').read_text(encoding='utf-8'))
    require(sha(PREVIOUS/'review/manifest.json')==PRIOR_SHA,'Prior review changed')
    for name,expected in manifest['protected'].items():
        require(sha(ROOT/name)==expected,f'Protected source changed: {name}')
    for name,expected in manifest['outputs'].items():
        require(sha(acquisition/name)==expected,f'Acquired file changed: {name}')
    require(sha(BASE/'scripts/acquire.py')==manifest['script_sha256'],'Acquisition script changed')
    notes=json.loads((BASE/'scripts/review_notes.json').read_text(encoding='utf-8'))
    old=rows(PREVIOUS/'review/merged_candidate_decisions.csv')
    previous_identity={r['candidate_id']:r for r in rows(PREVIOUS/'review/sequence_identity_review.csv')}
    scope={cid for cid in previous_identity if cid.startswith('HIST_DRAMP208')}
    require(len(scope)==5 and len(old)==78,'Fixed five-record scope changed')
    source=acquisition/'raw/derived_mmc1.docx'
    with zipfile.ZipFile(source) as package:
        doc=ET.fromstring(package.read('word/document.xml'))
        text=''.join(t.text or '' for t in doc.findall(f'.//{W}t'))
        require(all(x in text for x in ['Figure S1. Hemolytic activity','peripheral human blood','10 and 100 µM','three independent measurements','Figure S2.','Figure S3.']),'Unexpected supplement captions')
        for number in [1,2,3]:
            require((BASE/f'inspection/image{number}.tiff').read_bytes()==package.read(f'word/media/image{number}.tiff'),'Extracted media differ from source DOCX')
    # Independent earlier primary paper is corroboration, not transferred assay evidence.
    original=BeautifulSoup((acquisition/'raw/chang2006_pmc.html').read_bytes(),'html.parser')
    original_text=original.get_text(' ',strip=True)
    require('Two Cathelicidin Genes' in original.select_one('h1').get_text() and '16377685' in original_text,'Wrong corroborating paper')
    sequence=notes['corroborated_sequence']
    require(sequence in original_text and '3,687.1' in original_text,'Corroborating sequence/mass absent')
    require(sequence==previous_identity[notes['sequence_correction_candidate']]['source_sequence'] and len(sequence)==36,'Primary sequences disagree')
    require(previous_identity['HIST_DRAMP20863']['source_sequence'][4:]==sequence,'2016 full/short primary fragment relation not reproduced')
    inspections=[]
    for number in [1,2,3]:
        path=BASE/f'inspection/image{number}.tiff'
        render=BASE/('inspection/s1_image.png' if number==1 else f'inspection/supplement_image{number}.png')
        with fitz.open(path) as image_doc:
            width,height=image_doc[0].get_pixmap().width,image_doc[0].get_pixmap().height
        inspections.append({'source_media':f'word/media/image{number}.tiff','extracted_file':path.relative_to(BASE).as_posix(),
                            'extracted_sha256':sha(path),'render':render.relative_to(BASE).as_posix(),'render_sha256':sha(render),
                            'width':width,'height':height,'agent_visually_inspected':True})
    identities=[]
    for cid in sorted(scope):
        number=cid.removeprefix('HIST_DRAMP')
        database=BeautifulSoup((acquisition/f'raw/DRAMP{number}.html').read_bytes(),'html.parser')
        seq=database_field(database,'Sequence')
        length=database_field(database,'Sequence Length')
        mass=database_field(database,'Mass')
        preceding=previous_identity[cid]
        require(seq==preceding['inventory_sequence'],'Live database no longer matches captured inventory; requires new review')
        identities.append({'candidate_id':cid,'name':preceding['source_name'],'inventory_sequence':preceding['inventory_sequence'],
                           'primary_2016_sequence':preceding['source_sequence'],'database_sequence':seq,
                           'computed_database_sequence_length':len(seq),'database_reported_length':length,
                           'database_length_self_consistent':int(length)==len(seq),'primary_sequence_matches_database':seq==preceding['source_sequence'],
                           'database_reported_mass':mass,'primary_2016_reported_mw_da':preceding['reported_mass_da'],
                           'mass_issue':('unresolved 2181.45 vs 2510.8 discrepancy; do not repair using name-derived residues or convert labels' if cid=='HIST_DRAMP20859' else
                                         'different sequence identities; do not compare/transfer molecular masses' if cid=='HIST_DRAMP20862' else
                                         'reported values preserved; source mass basis not independently released'),
                           'database_role':'secondary annotation, not new experimental evidence',
                           'primary_2006_sequence':sequence if cid=='HIST_DRAMP20862' else '',
                           'primary_2006_reported_mw_da':'3687.1' if cid=='HIST_DRAMP20862' else '',
                           'sequence_and_form_release':False})
    correction={'candidate_id':'HIST_DRAMP20862','historical_inventory_sequence':previous_identity['HIST_DRAMP20862']['inventory_sequence'],
                'proposed_source_sequence':sequence,'proposed_length':36,
                'corroboration':'2016 Figure 1 visual reading plus 2006 primary Methods; full 2016 rtCATH2(1-40) suffix matches',
                'status':'identity_correction_proposal_unreleased','formal_release':False,
                'constraint':'Historical inventory untouched; proposed identity requires complete molecule/assay review and renewed isolation before any dataset use'}
    new=[]
    for prior in old:
        if prior['candidate_id'] not in scope:
            continue
        row=dict(prior)
        cid=row['candidate_id']
        shown=cid in notes['s1_visual_findings']['in_scope_candidate_ids']
        row.update(review_scope='agent_original_source_and_embedded_figure_review; not independent human review',
                   source_location=prior['source_location']+'; publisher DOCX S1; official DRAMP annotation; 2006 Methods for rtCATH2(5-40)',
                   screen_status='publisher_s1_and_primary_identity_followup_reviewed',
                   decision='current_source_insufficient_for_dual_release',formal_release='False',sequence_and_form_release='False')
        row['reason']=('S1已取得：该源图分子在100 µM下有单点人RBC溶血柱，视觉低于50%，不数值化、不填精确HC50。' if shown else
                       'S1已取得，但图中未展示rtCATH2(1-40)柱；正文总体陈述不能补成该分子的原图值。')
        if cid=='HIST_DRAMP20862':
            row['reason']+='2006与2016原文支持36残基，清单及现行DRAMP序列35残基，DRAMP长度字段却为39；形成独立身份更正候选，历史清单未改，测定未释放。'
        elif cid=='HIST_DRAMP20859':
            row['reason']+='清单/原图/数据库可见序列20残基，但论文MW 2510.8与DRAMP质量2181.45不一致，完整身份仍待确认；不按片段名补残基。'
        elif cid=='HIST_DRAMP20863':
            row['reason']+='序列本身40残基，DRAMP长度字段42；保存数据库内部不一致。'
        row['reason']+='保留原文培养基条件差异；完整形式、HC50准入和全员隔离未通过。'
        new.append(row)
    decisions={r['candidate_id']:r for r in new}
    merged=[decisions.get(r['candidate_id'],r) for r in old]
    obs=[]
    for cid in notes['s1_visual_findings']['in_scope_candidate_ids']:
        obs.append({'candidate_id':cid,'source_molecule_name':previous_identity[cid]['source_name'],
                    'endpoint':'single_point_human_hemolysis','target':'human red blood cells','concentration':'100','concentration_unit':'µM',
                    'raw_numeric_hemolysis_percent':'','visual_reading':'bar visibly below 50%; not numerically digitized',
                    'source':'publisher DOCX Figure S1; word/media/image1.tiff','repeats':'caption: mean of three independent measurements',
                    'caption_display_issue':'caption mentions 10 and 100 µM; graph displays 10 µM only for SMAP-29 control',
                    'formal_hc50':'','formal_label':'','formal_release':False,
                    'identity_transfer':'not released; rtCATH2(5-40) graph names source peptide, not the inconsistent inventory molecule'})
    generated=datetime.now(timezone.utc).isoformat()
    summary={'generated_at':generated,'data_version':BASE.name,'protocol_id':'protocol-amd-02','homology_boundary':'>=0.40 unchanged',
             'review_mode':notes['review_mode'],'independent_human_review':False,'followed_up_existing_candidates':5,
             'new_candidates_endpoint_screened':0,'verified_publisher_supplement_documents':1,'primary_sequence_corroboration_papers':1,
             'human_single_point_observations':4,'human_exact_hc50_values':0,'identity_correction_proposals':1,
             'database_length_internal_conflicts':sum(not r['database_length_self_consistent'] for r in identities),
             'merged_candidate_records':78,'merged_candidates_endpoint_screened':41,'remaining_original_access_gaps':37,
             'merged_decision_counts':dict(Counter(r['decision'] for r in merged)),'formal_external_released':0,
             'formal_scientific_status':'blocked','model_fit_calls':0,'training_state_changed':False,
             'supplement_access_gap_resolved':True,'full_docx_page_layout_verified':False}
    out.mkdir(parents=True)
    write_rows(out/'candidate_decisions.csv',new)
    write_rows(out/'merged_candidate_decisions.csv',merged)
    write_rows(out/'sequence_identity_review.csv',identities)
    write_rows(out/'identity_correction_proposal.csv',[correction])
    write_rows(out/'single_point_observations.csv',obs)
    write_json(out/'visual_review.json',{'notes':notes,'images':inspections})
    write_json(out/'summary.json',summary)
    with (out/'report.md').open('x',encoding='utf-8') as stream:
        stream.write(f'''# 鲑鱼论文S1与分子身份跟进

生成时间：{generated}。数据版本`{BASE.name}`，协议`protocol-amd-02`，>=0.40全员边界保持原样。

## 已完成

取得[出版方DOCX补充文件](https://ars.els-cdn.com/content/image/1-s2.0-S1050464816306994-mmc1.docx)，含S1–S3。链接最初按已核对PII构造；下载后以DOCX包、主文交叉引用及三图主题核实，未把猜测链接或HTTP 200本身视为证据。S1获取缺口已解除。

S1是人RBC单点溶血图。既定候选中仅TT(1-24)、TT(1-35)、rtCATH2(5-40)、SF(18-45)在100 µM有柱；图中没有rtCATH2(1-40)。可见实验肽柱低于50%，不读出精确百分比、不拟合或填HC50。图注提及10/100 µM，但图示10 µM仅属于SMAP-29对照，不能给全部候选补写10 µM观测。S2是通透性/菌落计数，S3是吞噬效应，均不替代MIC/HC50。

[2006原始论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC1346769/)的方法序列与2016原图的rtCATH2(5-40)一致：36残基。现行DRAMP和历史清单为35残基；DRAMP自身长度字段为39。已保存一份**未准入的身份更正候选**，没有修改历史数据，也没有把旧分子的标签移给更正分子。2006论文只用于身份交叉核对，不转移该研究测定或把两论文当作已通过隔离的研究。

## 新记录的冲突

|记录|当前数据库与原文核查|处理|
|---|---|---|
|rtCATH2(5-40)|数据库序列35残基/长度字段39；原文36残基|更正提案单独保存，完整形式及测定待准入|
|rtCATH2(1-40)|数据库序列实际40残基/长度字段42；S1未显示此肽|不从其他肽补图或改字段后放行|
|TT(1-24)|原图/数据库可见序列20残基；论文MW 2510.8、数据库质量2181.45|保留质量/身份冲突，不按名称推补残基或换算标签|

DRAMP结构、类别、质量等属于数据库注释，不自动成为原始测量或分子形式证明。2016和2006对36残基肽分别报告MW 3686.1和3687.1，原值及研究身份分别保留，不混成一个正式换算口径。

## 交付与状态

新增复核5条**既有**候选，累计仍41/78、37条缺原文。新增正式外部准入0；正式双任务**blocked**，既有MIC探索性训练和交付未改。HC50数值缺口仍在；补充图可访问不等于所有科学门禁通过。

逐条结论见`candidate_decisions.csv`，累计清单见`merged_candidate_decisions.csv`；原图观察见`single_point_observations.csv`；身份冲突及提案分别见`sequence_identity_review.csv`、`identity_correction_proposal.csv`。不声称独立人工评审。

当前主机没有可用soffice；使用既有PyMuPDF渲染并视觉查看DOCX内全部三张原始TIFF，图注从XML读取。未声称完成DOCX整页排版核查，未更改或重新制作来源文档。原文版权与再分发许可未建立CC授权；原数据库版权声明不扩展到原论文或补充材料。

`manifest.json`保存来源和历史绑定，`verification.json`记录原始文本、包内媒体、覆盖、哈希验收。

```powershell
python -X utf8 03_experiments/audits/hc50_salmon_supplement_20261005_v1/scripts/review.py --output 03_experiments/audits/hc50_salmon_supplement_20261005_v1/review_reproduction_v1
python -X utf8 03_experiments/audits/hc50_salmon_supplement_20261005_v1/scripts/verify.py --review 03_experiments/audits/hc50_salmon_supplement_20261005_v1/review_reproduction_v1 --output 03_experiments/audits/hc50_salmon_supplement_20261005_v1/review_reproduction_v1/verification.json
```

后续需要可核查HC50原值/剂量系列，以及解决TT(1-24)和更正分子的完整实验身份；其余37条公开原文仍需跟进。
''')
    inputs={p.relative_to(ROOT).as_posix():sha(p) for folder in [acquisition,BASE/'inspection'] for p in folder.rglob('*') if p.is_file()}
    inputs.update({p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),BASE/'scripts/review_notes.json',BASE/'scripts/acquire.py']})
    write_json(out/'manifest.json',{'generated_at':generated,'previous_review_manifest_sha256':PRIOR_SHA,'protected':manifest['protected'],'inputs':inputs,
                                 'outputs':{p.name:sha(p) for p in out.iterdir() if p.is_file()},'formal_release':False,'model_fit_calls':0})
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    main()
