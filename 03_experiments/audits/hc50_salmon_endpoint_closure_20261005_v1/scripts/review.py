"""Immutable follow-up of five existing records; no new labels or training."""
import argparse
import ast
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from bs4 import BeautifulSoup
import fitz
from acquire import BASE, ROOT, PRIOR, PRIOR_SHA, save, sha


def require(value, message):
    if not value:
        raise ValueError(message)


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_rows(path, data):
    with path.open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    require(out.is_relative_to(BASE) and not out.exists(), 'Output must be a new directory inside this audit')
    acquisition = json.loads((BASE/'acquisition/manifest.json').read_text(encoding='utf-8'))
    require(sha(PRIOR/'review/manifest.json') == PRIOR_SHA, 'Prior review changed')
    for name, expected in acquisition['protected'].items():
        require(sha(ROOT/name) == expected, 'Protected file changed: '+name)
    for folder in ['acquisition', 'focused_search']:
        manifest = json.loads((BASE/folder/'manifest.json').read_text(encoding='utf-8'))
        for name, expected in manifest['outputs'].items():
            require(sha(BASE/folder/name) == expected, 'Captured source changed: '+name)
        script = 'acquire.py' if folder == 'acquisition' else 'focused_search.py'
        require(sha(BASE/'scripts'/script) == manifest['script_sha256'], 'Acquisition script changed')
    notes = json.loads((BASE/'scripts/review_notes.json').read_text(encoding='utf-8'))
    require(sha(BASE/notes['publisher_figure']) == notes['publisher_figure_sha256'], 'Visual review source changed')
    identities = rows(PRIOR/'review/sequence_identity_review.csv')
    old = rows(PRIOR/'review/merged_candidate_decisions.csv')
    scope = set(notes['visual_transcriptions'])
    require(len(old) == 78 and len(scope) == 5 and scope == {r['candidate_id'] for r in identities}, 'Five-record scope changed')
    # Read only the existing constant dictionary, without importing training code.
    tree = ast.parse((ROOT/'02_code/feature_extractor.py').read_text(encoding='utf-8-sig'))
    mass = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MOLECULAR_WEIGHTS' for t in n.targets))
    diagnostics = []
    for row in identities:
        cid = row['candidate_id']
        seq = notes['visual_transcriptions'][cid]
        require(seq == row['primary_2016_sequence'], 'Published and accepted figure differ: '+cid)
        value = sum((Decimal(str(mass[a])) for a in seq), Decimal(0)) - Decimal('18.0152')*(len(seq)-1)
        diagnostics.append({'candidate_id':cid, 'name':row['name'], 'publisher_figure_sequence':seq,
                            'sequence_length':len(seq), 'accepted_figure_agreement':True,
                            'inventory_sequence_agreement':seq == row['inventory_sequence'],
                            'conditional_linear_free_termini_average_mass_da':str(value),
                            'source_table_mass_da':row['primary_2016_reported_mw_da'],
                            'source_minus_conditional_mass_da':str(Decimal(row['primary_2016_reported_mw_da'])-value),
                            'formal_identity_release':False, 'used_for_label_conversion':False})
    screens = []
    for note in notes['primary_screens']:
        soup = BeautifulSoup((BASE/note['file']).read_bytes(), 'html.parser')
        text = soup.get_text(' ', strip=True)
        require(note['title_marker'] in soup.select_one('h1').get_text(' ', strip=True), 'Wrong primary title')
        require(note['identity_marker'] in text and note['target_marker'] in text, 'Expected primary molecule/target absent')
        require(note['doi'].lower() in text.lower(), 'Expected primary DOI absent')
        screens.append(dict(note, file_sha256=sha(BASE/note['file']), human_hc50_released=False))
    hits, searches = [], []
    for folder in ['acquisition', 'focused_search']:
        query_log = json.loads((BASE/folder/'queries.json').read_text(encoding='utf-8'))
        for name, query in query_log['queries'].items():
            path = BASE/folder/'raw'/(name+'.json')
            result = json.loads(path.read_text(encoding='utf-8'))
            data = result.get('resultList', {}).get('result', [])
            searches.append({'query_name':name, 'query':query, 'source_file':path.relative_to(BASE).as_posix(),
                             'hit_count':result['hitCount'], 'captured_records':len(data), 'truncated':result['hitCount'] > len(data),
                             'limitation':'Discovery coverage only; no proof of absence in unindexed full texts/supplements'})
            for record in data:
                rid = record['id']
                disposition = ('unrelated punctuation/name match; not a peptide source' if name == 'exact_fragments' else
                               'prior 2006 primary source, already screened; sequence corroboration only' if rid == '16377685' else
                               'captured primary full text screened: fish RBC/different molecules' if rid == '21858109' else
                               '2016 index control: already reviewed exact source; no new endpoint' if rid == '27818338' else
                               'metadata only; full text not acquired, endpoint unknown' if rid in {'19168146','25876762'} else
                               'review/citation route; not original measurement evidence')
                hits.append({'query_name':name, 'id':rid, 'source':record.get('source',''), 'title':record.get('title',''),
                             'doi':record.get('doi',''), 'pmcid':record.get('pmcid',''), 'disposition':disposition, 'formal_release':False})
    require(all(not r['truncated'] for r in searches), 'Search pagination incomplete')
    new = []
    for prior in old:
        if prior['candidate_id'] not in scope:
            continue
        row = dict(prior)
        row['screen_status'] = 'publisher_figure_and_cited_primary_followup_reviewed'
        row['review_scope'] = notes['review_mode']
        row['source_location'] += '; publisher Figure 1; cited primary 2005 Figure 6 / 2011 Figure 4 (fish RBC, different molecules)'
        row['reason'] += '本轮出版方正式图1与作者稿序列一致；已检查的相关原始论文采用鱼RBC和不同分子，不能转移成人HC50；其他引用来源未取得原文，不宣称全网无证据。'
        if row['candidate_id'] == 'HIST_DRAMP20859':
            row['reason'] += '20残基条件理论质量2181.4312 Da与原表2510.8 Da仍冲突；未修补序列或按此换算标签。'
        row.update(formal_release='False', sequence_and_form_release='False')
        new.append(row)
    updates = {r['candidate_id']:r for r in new}
    merged = [updates.get(r['candidate_id'],r) for r in old]
    generated = datetime.now(timezone.utc).isoformat()
    summary = {'generated_at':generated, 'data_version':BASE.name, 'protocol_id':'protocol-amd-02',
               'review_mode':notes['review_mode'], 'independent_human_review':False,
               'existing_candidates_followed_up':5, 'additional_candidates_screened':0,
               'new_primary_fulltexts_screened_for_transfer':2, 'publisher_figure_sequence_checks':5,
               'human_exact_hc50_values_added':0, 'identity_release_count':0,
               'tt_1_24_conflict_resolved':False, 'merged_candidate_records':78,
               'merged_candidates_endpoint_screened':41, 'remaining_original_access_gaps':37,
               'merged_decision_counts':dict(Counter(r['decision'] for r in merged)),
               'formal_external_released':0, 'formal_scientific_status':'blocked',
               'homology_boundary':'>=0.40 unchanged', 'model_fit_calls':0, 'training_state_changed':False,
               'search_queries':len(searches), 'all_search_pages_fully_captured':True,
               'conclusion_scope':'No qualifying human HC50 added from sources actually inspected; worldwide absence is not established.'}
    out.mkdir(parents=True)
    write_rows(out/'candidate_decisions.csv',new)
    write_rows(out/'merged_candidate_decisions.csv',merged)
    write_rows(out/'mass_and_sequence_diagnostics.csv',diagnostics)
    write_rows(out/'primary_endpoint_screen.csv',screens)
    write_rows(out/'search_coverage.csv',searches)
    write_rows(out/'search_hit_review.csv',hits)
    save(out/'summary.json',summary)
    pix = fitz.Pixmap(str(BASE/notes['publisher_figure']))
    save(out/'figure_review.json', {'source':notes['publisher_figure'], 'sha256':notes['publisher_figure_sha256'],
                                  'width':pix.width,'height':pix.height,'agent_visually_inspected':True,
                                  'independent_human_review':False,'transcriptions':notes['visual_transcriptions']})
    report = f'''# 鲑鱼五候选：HC50检索与正式图身份核查

生成时间：{generated}（UTC）。数据版本 `{BASE.name}`；协议 `protocol-amd-02`。

## 本轮结论

复核既有五条，未新增候选；本轮未增加可准入的人红细胞数值HC50，正式外部新增0，原双任务仍blocked。既有MIC探索训练及协议不变，未训练新模型。这里的结论仅覆盖实际检查的来源，不能推断全网没有数据。

## 原始来源核查

- 出版方[正式Figure 1](https://ars.els-cdn.com/content/image/1-s2.0-S1050464816306994-gr1_lrg.jpg)与作者稿五条序列一致。地址由已核对的PII推导，下载后人工视读核实内容；不声称从文章网页观察到此附件链接。原图未改动，来源和转录分别绑定摘要。
- TT(1-24)仍显示20残基；原表MW为2510.8 Da。按项目现有质量常数、假设线性游离末端复算为2181.4312 Da，差329.3688 Da。仅为条件一致性诊断，不证明实际形式或错误原因，不补写4个残基，不据此换算测定单位或标签。
- rtCATH2(5-40)正式图为36残基，与前一批2006原文一致，仍与历史35残基清单冲突。前一批身份更正提案继续未准入。
- [Chang 2005](https://pmc.ncbi.nlm.nih.gov/articles/PMC1201231/)测定对象为虹鳟红细胞和rtCATH_1片段；[Bridle 2011](https://pmc.ncbi.nlm.nih.gov/articles/PMC3153500/)为大西洋鲑红细胞及asCATH1/asCATH2。不同RBC物种及分子不能转移为本批人HC50；引用既有研究也不构成新测量来源。原文定位见 `primary_endpoint_screen.csv`。
- [Scocchi 2009](https://pubmed.ncbi.nlm.nih.gov/19168146/)和[Zhang 2015](https://pubmed.ncbi.nlm.nih.gov/25876762/)本批仅获得可核对元数据；前者DOI返回跳转页，后者访问403。不能判断未取得的全文是否含目标端点。2020引用路由返回挑战页，不能作为原始证据。
- [Crossref记录](https://api.crossref.org/works/10.1016/j.fsi.2016.11.004)在获取时没有update-to或relation条目；这不能证明没有勘误。

## 检索覆盖与边界

保存8个Europe PMC查询及逐命中决定。带括号片段名的首个查询返回5条无关命中，全部拒作肽证据。增加生物学限定后0命中；全序列查询仅命中已检查2006论文；PMID索引对照找到了2016论文。这表明片段名和序列检索不能完整覆盖补充材料，0命中不是没有实验的证明。所有页内记录已保存，无分页截断。元数据、综述、预测及单点溶血均不生成标签。

累计78条候选中41条已端点初筛，37条缺原文，五条本轮跟进仍为来源不足。其他73条决定原样保留；22条来源不足、47条待原文、9条形式排除。47与37来自不同计数维度，不能互换。

## 交付及核查方式

`candidate_decisions.csv`保留逐条理由；`merged_candidate_decisions.csv`为78条累计表；`mass_and_sequence_diagnostics.csv`为条件质量/序列诊断；`search_coverage.csv`和`search_hit_review.csv`为检索追溯；`summary.json`为本批机器状态。原始抓取和时间位于上级acquisition及focused_search。manifest绑定输入、历史保护文件及输出。

执行 `python .../scripts/review.py --output <本批中新的目录>` 可重建表格。`verify.py --review <目录> --output <新的JSON文件>`独立核对摘要、五条/78条覆盖、质量算术与原文目标。视觉转录为代理复核，程序只能验证绑定及一致性，不是独立人工作者评审。未运行模型或pytest。

## 仍待解决

取得同一分子的人红细胞数值HC50或足以按现行规则明确类别的原始删失端点；澄清TT(1-24)实测身份与质量、rtCATH2短片段身份；完整形式复核后再按既有协议执行全员/来源隔离。不能通过借用鱼RBC或其他分子的数值解除blocked。未向作者发送邮件。
'''
    with (out/'report.md').open('x', encoding='utf-8') as stream:
        stream.write(report)
    inputs = {p.relative_to(ROOT).as_posix():sha(p) for folder in ['acquisition','focused_search','scripts'] for p in (BASE/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    inputs[ (PRIOR/'review/manifest.json').relative_to(ROOT).as_posix() ] = PRIOR_SHA
    save(out/'manifest.json', {'generated_at':generated, 'protected':acquisition['protected'], 'inputs':inputs,
                              'outputs':{p.relative_to(out).as_posix():sha(p) for p in out.iterdir() if p.is_file()},
                              'formal_release':False, 'model_fit_calls':0})
    print(json.dumps(summary,ensure_ascii=True))


if __name__ == '__main__':
    main()
