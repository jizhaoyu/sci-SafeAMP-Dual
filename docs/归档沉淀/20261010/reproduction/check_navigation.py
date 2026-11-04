"""Verify generated navigation only; old snapshots may retain historical resource links."""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
ARCHIVE=Path(__file__).resolve().parent.parent

def main():
    files=[ROOT/'文档导航.md',ARCHIVE/'00_归档总览.md',ARCHIVE/'01_当前成果导航.md',ARCHIVE/'02_版本链路与使用顺序.md']
    files+=list((ARCHIVE/'分类索引').glob('*.md'))
    files+=list((ARCHIVE/'知识沉淀').glob('*.md'))
    checked=0;missing=[]
    for path in files:
        text=path.read_text(encoding='utf-8')
        for match in re.finditer(r'\]\((?:<([^>]+)>|([^\)]+))\)',text):
            target=(match.group(1) or match.group(2)).strip()
            if target.startswith(('http://','https://','#','app://')): continue
            target=target.split('#',1)[0]
            resolved=Path(target) if Path(target).is_absolute() else path.parent/target
            if not resolved.exists(): missing.append({'file':str(path),'target':target})
            checked+=1
    result={'status':'PASS' if not missing else 'FAIL','generated_navigation_pages':len(files),
        'local_links_checked':checked,'missing_links':missing,
        'scope':'Generated entrypoints, category indexes and knowledge pages; not old snapshot links.'}
    (ARCHIVE/'导航校验报告.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if missing: raise SystemExit(1)

if __name__=='__main__': main()
