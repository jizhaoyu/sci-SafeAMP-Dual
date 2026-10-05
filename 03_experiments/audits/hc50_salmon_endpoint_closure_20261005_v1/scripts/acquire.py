"""Public metadata/primary-source search for five existing salmonid candidates."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import quote, urlencode

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parents[2]
PRIOR=ROOT/'03_experiments/audits/hc50_salmon_supplement_20261005_v1'
sys.path.insert(0,str(ROOT/'03_experiments/audits/hc50_missing_originals_20261005_v1/scripts'))
from acquire_sources import fetch

PRIOR_SHA='5ec38cf298a87e9c647d1769808d37d568d2659e9921c006570030b37e319d91'
EPMC='https://www.ebi.ac.uk/europepmc/webservices/rest/search?'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)


def main():
    out=BASE/'acquisition'
    if out.exists():
        raise FileExistsError(out)
    previous=PRIOR/'review/manifest.json'
    if sha(previous)!=PRIOR_SHA:
        raise ValueError('Previous review changed')
    m=json.loads(previous.read_text(encoding='utf-8'))
    protected={**m['protected'],**m['inputs']}
    protected.update({p.relative_to(ROOT).as_posix():sha(p) for p in PRIOR.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    protected['02_code/feature_extractor.py']=sha(ROOT/'02_code/feature_extractor.py')
    for name,expected in protected.items():
        if sha(ROOT/name)!=expected:
            raise ValueError(f'Changed protected input: {name}')
    queries={
        'exact_fragments':'("TT(1-24)" OR "TT(1-35)" OR "SF(18-45)" OR "rtCATH2(1-40)" OR "rtCATH2(5-40)")',
        'rtcath_hemolysis':'"rtCATH2" AND (hemolysis OR haemolysis OR erythrocytes OR HC50)',
        'grayling_hemolysis':'(grayling OR "Thymallus thymallus") AND cathelicidin AND (hemolysis OR haemolysis OR HC50)',
        'pmid19168146':'EXT_ID:19168146 AND SRC:MED',
        'pmid25876762':'EXT_ID:25876762 AND SRC:MED',
    }
    requests=[(name+'.json',EPMC+urlencode({'query':query,'format':'json','resultType':'core','pageSize':100}),'','','Europe PMC discovery/metadata; not automatically original measurements') for name,query in queries.items()]
    requests.extend([
        ('publisher_figure1_large.jpg','https://ars.els-cdn.com/content/image/1-s2.0-S1050464816306994-gr1_lrg.jpg','27818338','10.1016/j.fsi.2016.11.004','DERIVED public publisher Figure 1 route from verified PII; content must be visually identified'),
        ('publisher_figure1.jpg','https://ars.els-cdn.com/content/image/1-s2.0-S1050464816306994-gr1.jpg','27818338','10.1016/j.fsi.2016.11.004','DERIVED public publisher Figure 1 route; not yet identity-verified'),
        ('crossref_2016.json','https://api.crossref.org/works/'+quote('10.1016/j.fsi.2016.11.004',safe=''),'27818338','10.1016/j.fsi.2016.11.004','Crossref deposited citation/update metadata only; absence does not prove no correction'),
        ('chang2005_pmc.html','https://pmc.ncbi.nlm.nih.gov/articles/PMC1201231/','','10.1128/iai.73.8.5053-5064.2005','cited primary paper; assay target and molecule must match before any use'),
        ('bridle2011_pmc.html','https://pmc.ncbi.nlm.nih.gov/articles/PMC3153500/','','10.1371/journal.pone.0023417','cited primary paper; preserve different molecules and RBC species'),
        ('zhang2015_doi.html','https://doi.org/10.4049/jimmunol.1500182','25876762','10.4049/jimmunol.1500182','cited primary publisher page; abstract/metadata alone cannot release an assay'),
        ('scocchi2009_doi.html','https://doi.org/10.1016/j.cbpb.2009.01.003','19168146','10.1016/j.cbpb.2009.01.003','cited genetic source; not presumed experimental HC50 evidence'),
        ('nature2020_citation_route.html','https://www.nature.com/articles/s41598-020-73644-6','','10.1038/s41598-020-73644-6','citation route only; predictions and literature statements never generate assay labels'),
    ])
    (out/'raw').mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        records=list(pool.map(lambda request:fetch(request,out),requests))
    save(out/'queries.json',{'queries':queries,'capture_limit':100,'meaning':'public search coverage, not exhaustive proof of absence'})
    save(out/'source_acquisition.json',records)
    save(out/'manifest.json',{'generated_at':datetime.now(timezone.utc).isoformat(),'protected':protected,'previous_review_manifest_sha256':PRIOR_SHA,
                              'script_sha256':sha(Path(__file__)),'outputs':{p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()},
                              'formal_release':False,'model_fit_calls':0})
    print(json.dumps([{'file':r['requested_file'],'status':r['status'],'bytes':r.get('bytes'),'http_status':r.get('http_status')} for r in records]))


if __name__=='__main__':
    main()
