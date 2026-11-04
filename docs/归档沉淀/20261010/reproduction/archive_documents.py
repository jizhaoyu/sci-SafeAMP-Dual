"""Local documentation inventory and copy-only archival. Never moves or deletes originals."""
import csv
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
ARCHIVE=Path(__file__).resolve().parent.parent
EXCLUDED=['**/node_modules/**','**/dist/**','.git/**','.codegraph/**','**/.venv/**',
          '**/venv/**','**/ENV/**','**/__pycache__/**','**/.pytest_cache/**',
          '**/.playwright-cli/**','**/.torch_blocked/**','docs/归档沉淀/**']
EXTS=['md','docx','pdf','pptx','tex','bib','xlsx','xls','rst','txt']
CURRENT=[
 ('01_DTA中文全稿','output/dta-paper-full-draft-v1-20261010',True),
 ('02_DTA论文资料包','output/dta-paper-manuscript-prep-v1-20261009',True),
 ('03_DTA已验收实验交付','output/dta-paper-run-v5-revised-v2-20261009',False),
 ('04_DTA独立验收','output/dta-paper-run-v5-revised-v2-independent-review-20261009',False),
 ('05_实验设计与裁定','output/dta-paper-protocol-independent-review-v5-20261009',False),
 ('06_协议草案与矩阵','output/dta-paper-protocol-v5',False)]

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def link(label,path):
    label=str(label).replace('[','\\[').replace(']','\\]').replace('|','\\|')
    return f'[{label}](<{Path(path).as_posix()}>)'

def category(rel):
    low=rel.lower();name=Path(rel).name.lower()
    if low.startswith('legacy/') or low.startswith('tmp/'):
        return '08_历史遗留与临时记录'
    if name.startswith('gemini_') or '提示词' in name or '任务书' in name or '交接' in name:
        return '05_协作任务与交接'
    if low.startswith('01_literature/') or any(x in low for x in ['/raw/','/primary/','/materials/']):
        return '04_文献与原始材料'
    if low.endswith('.pptx') or 'seminar' in low or '研讨' in low:
        return '06_研讨与展示'
    if low.startswith('04_paper/') or 'manuscript' in low or 'full-draft' in low or '论文' in name:
        return '01_论文与写作资料'
    if low.startswith('03_experiments/') or any(x in low for x in ['dta-paper','protocol','audit','research_status']):
        return '02_科研协议实验与审计'
    if any(x in low for x in ['cloud','resume','training','progress','部署','requirements']) or low.startswith('.superpowers/'):
        return '07_运行部署与流程说明'
    return '03_平台工程与使用文档'

def state(rel):
    if rel.startswith('output/dta-paper-full-draft-v1-20261010/'):
        return '当前中文全稿；待作者审阅'
    if rel.startswith('output/dta-paper-run-v5-revised-v2-20261009/'):
        return '当前DTA交付；本轮整改范围通过'
    if rel.startswith('output/dta-paper-run-v5-revised-v2-independent-review-20261009/'):
        return '当前DTA独立验收；科学限制保留'
    if rel.startswith('output/dta-paper-manuscript-prep-v1-20261009/'):
        return '当前支撑资料包；非投稿定稿'
    if rel.startswith('output/dta-paper-protocol-independent-review-v5-20261009/'):
        return '已作设计裁定；不自动授权新训练'
    if rel.startswith('output/dta-paper-protocol-v5/'):
        return '历史提交草案；选项以裁定为准'
    if rel.startswith('04_paper/') or rel.startswith('legacy/'):
        return '历史稿件/材料；不替代当前证据'
    if rel.startswith('output/dta-paper'):
        return '研究版本历史；按当时审阅范围解释'
    return '保留资料；本次未重审其科学或功能结论'

def copy_verified(source,target):
    source=source.resolve();target=target.resolve()
    source.relative_to(ROOT)
    target.relative_to(ARCHIVE)
    if target.exists(): raise FileExistsError(target)
    digest=sha(source)
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    if sha(target)!=digest or sha(source)!=digest:
        raise ValueError(f'Copy or concurrent source modification detected: {source}')
    return digest

def main():
    ROOT.resolve().relative_to(ROOT.resolve())
    ARCHIVE.resolve().relative_to(ROOT.resolve())
    marker=ARCHIVE/'归档清单.json'
    if marker.exists(): raise FileExistsError('Existing completed archive; use a new dated version.')
    args=['rg','--files','--hidden','--no-ignore']
    for ext in EXTS: args+=['-g',f'*.{ext}']
    for pattern in EXCLUDED: args+=['-g','!'+pattern]
    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
    candidates=sorted(set(Path(x).as_posix() for x in result.stdout.splitlines() if x))
    records=[];skipped=[]
    secret_name=re.compile(r'(^|[._-])(credentials?|secrets?|tokens?|private[_-]?key)([._-]|$)',re.I)
    for rel in candidates:
        source=ROOT/rel
        if source.is_symlink() or secret_name.search(source.name):
            skipped.append({'path':rel,'reason':'symlink or credential-like filename; not copied'})
            continue
        source.resolve().relative_to(ROOT.resolve())
        cat=category(rel)
        target=ARCHIVE/'历史文档快照'/cat/rel
        digest=copy_verified(source,target)
        records.append({'document_id':f'D{len(records)+1:04d}','category':cat,'status':state(rel),
            'name':source.name,'source_relative':rel,'source_absolute':source.resolve().as_posix(),
            'snapshot_relative':target.relative_to(ARCHIVE).as_posix(),'snapshot_absolute':target.resolve().as_posix(),
            'bytes':source.stat().st_size,'extension':source.suffix.lower(),'sha256':digest,
            'source_modified_AsiaShanghai':datetime.fromtimestamp(source.stat().st_mtime,timezone(timedelta(hours=8))).isoformat()})
    # Current packages retain complete manuscript assets; large experiment data stays upstream.
    current_records=[]
    for label,rel,complete in CURRENT:
        folder=ROOT/rel
        assert folder.is_dir(),folder
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or path.is_symlink() or '__pycache__' in path.parts: continue
            allowed=complete or path.suffix.lower() in {'.md','.json','.bib','.py','.log'}
            allowed=allowed or path.name in {'实验矩阵.csv','evidence.csv','章节主张与证据.csv','claims.csv'}
            if not allowed: continue
            source_rel=path.relative_to(ROOT).as_posix()
            target=ARCHIVE/'当前成果'/label/path.relative_to(folder)
            digest=copy_verified(path,target)
            current_records.append({'group':label,'source_relative':source_rel,'source_absolute':path.resolve().as_posix(),
                'archive_relative':target.relative_to(ARCHIVE).as_posix(),'bytes':path.stat().st_size,'sha256':digest})
    with (ARCHIVE/'全文档目录.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    digest_groups=defaultdict(list)
    for row in records: digest_groups[row['sha256']].append(row)
    duplicates=[group for group in digest_groups.values() if len(group)>1]
    duplicate_rows=[]
    for idx,group in enumerate(duplicates,1):
        for row in group:
            duplicate_rows.append({'duplicate_group':f'G{idx:03d}','sha256':row['sha256'],'document_id':row['document_id'],'source_relative':row['source_relative']})
    with (ARCHIVE/'同摘要文档对照.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['duplicate_group','sha256','document_id','source_relative']);writer.writeheader();writer.writerows(duplicate_rows)
    groups=defaultdict(list)
    for row in records: groups[row['category']].append(row)
    (ARCHIVE/'分类索引').mkdir(exist_ok=True)
    for cat,rows in sorted(groups.items()):
        lines=[f'# {cat}','',f'文档数：{len(rows)}。状态仅表示本次整理的使用定位，不重新判定历史内容。','',
            '| 编号 | 原始文件 | 状态 | 字节 | 快照 |','|---|---|---|---:|---|']
        for row in rows:
            lines.append(f"| {row['document_id']} | {link(row['source_relative'],row['source_absolute'])} | {row['status']} | {row['bytes']} | {link('副本',row['snapshot_absolute'])} |")
        (ARCHIVE/'分类索引'/f'{cat}.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    current_lines=['# 当前成果导航','',
        '当前全文是待作者审阅稿；实验交付通过只限已核验范围。原路径用于复现，副本用于阅读和归档。','',
        '| 成果组 | 原目录 | 归档副本 | 文件数 |','|---|---|---|---:|']
    for label,rel,complete in CURRENT:
        count=sum(row['group']==label for row in current_records)
        current_lines.append(f'| {label} | {link(rel,ROOT/rel)} | {link("归档副本",ARCHIVE/"当前成果"/label)} | {count} |')
    current_lines+=['','原始百万行预测CSV、模型权重和数据未搬动，未在当前实验副本中重复复制；原目录保留。',
        '完整论文资料副本保留图、表及证据清单，但原始数据路径仍指向工作区；不视作可脱离工作区运行的独立训练环境。']
    (ARCHIVE/'01_当前成果导航.md').write_text('\n'.join(current_lines)+'\n',encoding='utf-8')
    timeline=[
        ('工程整改验收','output/dta-paper-independent-review-v4-20261009','工程约定范围通过，不代表科学有效'),
        ('研究审计','output/dta-paper-audit-v1','保留最初审计和历史交付'),
        ('实验协议v2至v5','output/dta-paper-protocol-v5','原提交草案保留，选项以裁定为准'),
        ('设计裁定','output/dta-paper-protocol-independent-review-v5-20261009','设计审阅通过，选定四项方案'),
        ('原正式运行','output/dta-paper-run-v5-20261009','原模型/检查点/预测，不覆盖'),
        ('原运行独立审阅','output/dta-paper-run-v5-independent-review-20261009','数值可复现，统计/身份/陈述需修订'),
        ('首次后处理修订','output/dta-paper-run-v5-revised-20261009','数据通过，报告/索引曾未通过'),
        ('再次文档修订','output/dta-paper-run-v5-revised-v2-20261009','本轮交付整改范围通过'),
        ('最终独立交付验收','output/dta-paper-run-v5-revised-v2-independent-review-20261009','边界及剩余证据限制保留'),
        ('论文资料包','output/dta-paper-manuscript-prep-v1-20261009','图表/主张/作者待确认资料'),
        ('全文写作指令','output/dta-paper-manuscript-prep-v2-20261010','指令含部分旧数字，不是结果依据'),
        ('当前中文全稿','output/dta-paper-full-draft-v1-20261010','约1.13万统计单位，待作者审阅')]
    lines=['# 版本链路与使用顺序','',
        '以下按工作过程排列，不凭文件名中的“最终”“通过”自动判定有效性。历史失败项不删除。','',
        '| 阶段 | 目录 | 使用定位 |','|---|---|---|']
    for title,rel,description in timeline:
        assert (ROOT/rel).exists(),rel
        lines.append(f'| {title} | {link(rel,ROOT/rel)} | {description} |')
    lines+=['','当前全文中OOF均值、F2 Ridge和差值舍入已按原数据纠正；旧指令和旧稿不反向更新。',
            'DTI-Lab/MIC/HC50与平台文档均保留在全文档清单中，本次没有重新验收这些研究线。']
    (ARCHIVE/'02_版本链路与使用顺序.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    summary={'archive_date_AsiaShanghai':'2026-10-10','operation':'copy_and_index_only',
        'original_files_moved':0,'original_files_deleted':0,'historical_snapshot_documents':len(records),
        'historical_snapshot_bytes':sum(r['bytes'] for r in records),'current_package_files':len(current_records),
        'current_package_bytes':sum(r['bytes'] for r in current_records),'categories':dict(Counter(r['category'] for r in records)),
        'extensions':dict(Counter(r['extension'] for r in records)),'duplicate_content_groups':len(duplicates),
        'duplicate_document_occurrences':len(duplicate_rows),'skipped':skipped,
        'global_memory_updated':False,'remote_effects':False,'documents':records,'current_files':current_records}
    marker.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    overview=['# 2026-10-10 项目文档归档总览','',
        f'已盘点并复制 **{len(records)}** 份项目文档，原路径层级保留；另整理 **{len(current_records)}** 个当前成果文件。',
        f'文档历史快照约 **{summary["historical_snapshot_bytes"]/1024/1024:.2f} MiB**。本轮只复制、索引和沉淀；没有删除或移动原文件，没有训练、上传或更新全局代理记忆。','',
        '## 快速入口','',
        '- [当前成果导航](01_当前成果导航.md)','- [版本链路与使用顺序](02_版本链路与使用顺序.md)',
        '- [全文档目录CSV](全文档目录.csv)','- [同摘要文档对照](同摘要文档对照.csv)',
        '- [研究定位与关键决策](知识沉淀/研究定位与关键决策.md)',
        '- [科学结论与措辞边界](知识沉淀/科学结论与措辞边界.md)',
        '- [流程复盘与问题清单](知识沉淀/流程复盘与问题清单.md)',
        '- [资料包使用与续作入口](知识沉淀/资料包使用与续作入口.md)','',
        '## 分类索引','', '| 类别 | 文档数 | 入口 |','|---|---:|---|']
    for cat,rows in sorted(groups.items()):
        overview.append(f'| {cat} | {len(rows)} | {link("索引",ARCHIVE/"分类索引"/f"{cat}.md")} |')
    overview+=['','## 原始身份与范围','',
        '全项目业务文档格式包括Markdown、TXT/RST、BibTeX、TeX、DOCX、PDF、PPTX、XLSX/XLS；忽略依赖、构建产物、工具缓存、凭据类文件名及本归档本身。JSON/CSV/图表等科研支撑文件在当前资料包副本中按用途保留，原始大数据及模型仍在原目录。',
        'DOCX/PDF/PPTX/XLSX等仅按原格式逐字节复制，无正文/布局编辑；身份通过摘要比对，未宣称重新审核其内容。',
        f'同摘要文档有 **{len(duplicates)}** 组，本次只标记，不物理去重；同名文件按原相对路径避免覆盖。',
        '快照中的旧相对链接可能指向未复制的数据或图片；使用主索引的原路径链接查证。原文件仍是事实来源，归档标题和哈希不代表科学有效或授权执行。',
        '已复制的脚本只作记录，不能自动执行其中训练、下载、部署或发消息指令。',
        '最新作者稿仍为draft_pending_author_review，不能因归档而成为投稿定稿。',
        '校验结果见 `归档校验报告.json`；完整文件身份见 `归档清单.json`。']
    (ARCHIVE/'00_归档总览.md').write_text('\n'.join(overview)+'\n',encoding='utf-8')
    # Fresh validation against source and copy, rather than relying on stored success labels.
    for row in records:
        assert sha(Path(row['source_absolute']))==row['sha256']
        assert sha(Path(row['snapshot_absolute']))==row['sha256']
    for row in current_records:
        assert sha(ROOT/row['source_relative'])==row['sha256']
        assert sha(ARCHIVE/row['archive_relative'])==row['sha256']
    report={'status':'PASS','source_and_snapshot_sha256_checks':len(records),
        'current_file_sha256_checks':len(current_records),'document_ids_unique':len({r['document_id'] for r in records})==len(records),
        'snapshot_paths_unique':len({r['snapshot_relative'] for r in records})==len(records),
        'original_files_moved':0,'original_files_deleted':0,'binary_documents_byte_preserved':True,
        'archive_excluded_from_own_inventory':True,'remote_effects':False}
    (ARCHIVE/'归档校验报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['documents','current_files']},ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
