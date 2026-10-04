"""Cache public Crossref metadata; flag mismatches without inventing citations."""
import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from research_utils import ROOT,write_json,utc_now

def entries(text):
    blocks=[]
    for m in re.finditer(r'@\w+\s*\{([^,]+),',text):
        level=1;i=m.end()
        while i<len(text) and level:
            level+=(text[i]=='{')-(text[i]=='}');i+=1
        body=text[m.end():i-1];fields={}
        for field in ['title','doi','year','author']:
            f=re.search(r'\b'+field+r'\s*=\s*\{',body,re.I)
            if f:
                start=f.end();j=start;depth=1
                while j<len(body) and depth:
                    depth+=(body[j]=='{')-(body[j]=='}');j+=1
                fields[field]=' '.join(body[start:j-1].split())
        blocks.append({'key':m.group(1),'text':text[m.start():i],**fields})
    return blocks

def normalized(s):return re.sub(r'[^a-z0-9]+','',unicodedata.normalize('NFKD',s.lower()))

def get_metadata(doi,folder):
    name=re.sub(r'[^a-zA-Z0-9]+','_',doi)+'.json';path=folder/name
    if path.exists():return json.loads(path.read_text(encoding='utf-8'))
    url='https://api.crossref.org/works/'+urllib.parse.quote(doi,safe='/')
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'SafeAMP-citation-audit/1.0'})
            with urllib.request.urlopen(req,timeout=20) as r:payload=json.load(r)['message']
            write_json(path,{'url':url,'retrieved_at':utc_now(),'metadata':payload})
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            if attempt==2:raise
            time.sleep(2*(attempt+1))

def audit(bib,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);rows=[]
    for entry in entries(Path(bib).read_text(encoding='utf-8-sig')):
        row={'key':entry['key'],'expected_title':entry.get('title'),'doi':entry.get('doi'),
             'claim_support':'not_checked','status':'no_doi_requires_primary_source_check'}
        if entry.get('doi'):
            try:
                response=get_metadata(entry['doi'],output/'crossref');actual=response['metadata']
                title=actual.get('title',[''])[0]
                similarity=SequenceMatcher(None,normalized(entry.get('title','')),normalized(title)).ratio()
                expected_authors=[normalized(x.split(',')[0]) for x in entry.get('author','').split(' and ') if x.strip()!='others']
                resolved_authors=[normalized(x.get('family',x.get('name',''))) for x in actual.get('author',[])]
                authors_match=bool(expected_authors) and expected_authors==resolved_authors[:len(expected_authors)]
                years={str(actual[k]['date-parts'][0][0]) for k in ['published','published-print','published-online','issued'] if actual.get(k,{}).get('date-parts')}
                year_match=entry.get('year') in years
                text_quality='replacement_character_requires_publisher_check' if '\ufffd' in title else 'ok'
                row.update(resolved_title=title,title_similarity=similarity,metadata_text_quality=text_quality,metadata_path=str((output/'crossref'/ (re.sub(r'[^a-zA-Z0-9]+','_',entry['doi'])+'.json')).relative_to(ROOT)),
                           author_metadata_match=authors_match,year_metadata_match=year_match,
                           status='metadata_match_pending_claim_review' if similarity>=.98 and authors_match and year_match and text_quality=='ok' else 'metadata_mismatch')
            except Exception as e:row.update(status='lookup_failed',reason=str(e))
        rows.append(row)
        write_json(output/'reference_audit.json',{'checked_at':utc_now(),'all_claims_verified':False,'entries':rows})
        print(entry['key'],row['status'],flush=True)
        time.sleep(.2)
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bib',type=Path,default=ROOT/'04_paper/references.bib')
    p.add_argument('--output',type=Path,default=ROOT/'04_paper/evidence')
    a=p.parse_args();audit(a.bib,a.output.resolve())
