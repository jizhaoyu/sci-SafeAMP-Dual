"""Repair bibliographic metadata from cached Crossref records; never certify claims."""
from pathlib import Path
import re
from audit_references import entries,get_metadata
from research_utils import ROOT,write_json,sha256,utc_now

CORRECTED_DOIS={
    'kang2019dramp':'10.1038/s41597-019-0154-y',
    'chung2020dbamp':'10.1093/nar/gky1030',
    'santos2020macrel':'10.7717/peerj.10555',
    'plisson2020happenn':'10.1038/s41598-020-67701-3',
    'oren1997selective':'10.1021/bi962507l',
}

def escape(s):
    return str(s).replace('&',r'\&').replace('%',r'\%').replace('_',r'\_').replace('#',r'\#')

def refresh():
    source=ROOT/'legacy/pre_research_remediation_20260928/04_paper/references.bib'
    target=ROOT/'04_paper/references.bib';cache=ROOT/'04_paper/evidence/crossref'
    rows=[];blocks=[]
    for e in entries(source.read_text(encoding='utf-8-sig')):
        key=e['key'];doi=CORRECTED_DOIS.get(key,e.get('doi'))
        if key=='who2021amr':
            rows.append({'key':key,'status':'retired_unverified_report_metadata','claim_support':'not_checked'})
            continue
        if not doi:
            blocks.append(e['text']);rows.append({'key':key,'status':'retained_pending_primary_source_review','claim_support':'not_checked'});continue
        try:
            record=get_metadata(doi,cache);m=record['metadata']
            names=[]
            for author in m.get('author',[]):
                names.append(author.get('family',author.get('name',''))+', '+author['given'] if author.get('given') else author.get('family',author.get('name','')))
            date=m.get('published-print') or m.get('published') or m.get('issued')
            fields={'title':m.get('title',[''])[0],'author':' and '.join(names),'journal':m.get('container-title',[''])[0],
                    'year':str(date['date-parts'][0][0]),'volume':m.get('volume'),'number':m.get('issue'),
                    'pages':m.get('page',m.get('article-number')),'doi':m['DOI']}
            missing=[k for k in ['volume','pages'] if not fields.get(k)]
            # Article numbers are valid locators. Missing fields remain explicitly unresolved.
            if missing:fields['note']='Metadata fields unresolved: '+', '.join(missing)+'. Check publisher before submission.'
            blocks.append('@article{'+key+',\n'+',\n'.join('  '+k+'={'+escape(v)+'}' for k,v in fields.items() if v)+'\n}')
            rows.append({'key':key,'original_doi':e.get('doi'),'resolved_doi':doi,'status':'metadata_refreshed_claim_unverified',
                         'source_url':record['url'],'retrieved_at':record['retrieved_at'],'missing_fields':missing,'claim_support':'not_checked'})
        except Exception as exc:
            blocks.append(e['text']);rows.append({'key':key,'status':'lookup_failed_unverified','error':str(exc),'claim_support':'not_checked'})
    target.write_text('% Metadata audit only. Claim support and author approval remain pending.\n\n'+'\n\n'.join(blocks)+'\n',encoding='utf-8')
    write_json(ROOT/'04_paper/evidence/bibliography_repair.json',{'created_at':utc_now(),'original_sha256':sha256(source),
                'current_sha256':sha256(target),'all_claims_verified':False,'entries':rows})
    print({'entries':len(blocks),'unverified_claim_support':len(blocks),'failed':sum(r['status']=='lookup_failed_unverified' for r in rows)})

if __name__=='__main__':refresh()
