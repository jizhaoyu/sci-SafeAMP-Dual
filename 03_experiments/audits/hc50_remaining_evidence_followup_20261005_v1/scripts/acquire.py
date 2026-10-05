"""Bounded public source follow-up; the 37 retired records are excluded."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlencode

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
PRIOR = ROOT/'03_experiments/audits/hc50_unavailable_scope_closure_20261005_v1'
PRIOR_SHA = '101dd2d6687d3753a989984c5c38784c4438760f09ec48c664f862957260b84f'
PLP = ROOT/'03_experiments/audits/hc50_primary_followup_20261004_v1/acquisition/raw/pmid_30658410.xml'
SLAY = ROOT/'03_experiments/audits/slay_primary_review_20261004_v1/acquisition/raw/pmc_article.html'
sys.path.insert(0,str(ROOT/'03_experiments/audits/hc50_missing_originals_20261005_v1/scripts'))
from acquire_sources import fetch


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)


def main():
    out = BASE/'acquisition'
    if out.exists():
        raise FileExistsError(out)
    if sha(PRIOR/'review/manifest.json') != PRIOR_SHA:
        raise ValueError('Previous scope review changed')
    previous = json.loads((PRIOR/'review/manifest.json').read_text(encoding='utf-8'))
    protected = {**previous['protected'],**previous['inputs']}
    protected.update({p.relative_to(ROOT).as_posix():sha(p) for p in PRIOR.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for path in [PLP,SLAY,ROOT/'03_experiments/audits/hc50_missing_originals_20261005_v1/scripts/acquire_sources.py']:
        protected[path.relative_to(ROOT).as_posix()] = sha(path)
    for name,expected in protected.items():
        if sha(ROOT/name) != expected:
            raise ValueError('Protected source changed: '+name)
    with (PRIOR/'review/current_scope_records.csv').open(encoding='utf-8-sig',newline='') as stream:
        retained = list(csv.DictReader(stream))
    if len(retained) != 41 or any(r['screen_status'] == 'original_not_acquired' for r in retained):
        raise ValueError('Expected retained 41, without retired originals')
    requests = [
        ('slay_s2_pmc.pdf','https://pmc.ncbi.nlm.nih.gov/articles/instance/5786472/bin/NIHMS926512-supplement-6.pdf','29307492','10.1016/j.cell.2017.12.009','observed prior full article attachment; recheck response'),
        ('slay_s3_pmc.pdf','https://pmc.ncbi.nlm.nih.gov/articles/instance/5786472/bin/NIHMS926512-supplement-7.pdf','29307492','10.1016/j.cell.2017.12.009','observed prior full article attachment; recheck response'),
        ('slay_publisher_mmc6.pdf','https://ars.els-cdn.com/content/image/1-s2.0-S0092867417314514-mmc6.pdf','29307492','10.1016/j.cell.2017.12.009','DERIVED from prior verified PII; supplement numbering/identity not presumed'),
        ('slay_publisher_mmc7.pdf','https://ars.els-cdn.com/content/image/1-s2.0-S0092867417314514-mmc7.pdf','29307492','10.1016/j.cell.2017.12.009','DERIVED from prior verified PII; supplement numbering/identity not presumed'),
        ('plp_method_metadata.json','https://www.ebi.ac.uk/europepmc/webservices/rest/search?'+urlencode({'query':'EXT_ID:15246874 AND SRC:MED','format':'json','resultType':'core','pageSize':100}),'15246874','10.1016/j.abb.2004.05.013','cited method metadata only; no transfer of RBC species or measurements'),
        ('plp_method_doi.html','https://doi.org/10.1016/j.abb.2004.05.013','15246874','10.1016/j.abb.2004.05.013','cited method public entry; not presumed usable full text'),
    ]
    (out/'raw').mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(lambda request:fetch(request,out),requests))
    save(out/'source_acquisition.json',records)
    save(out/'manifest.json',{'generated_at':datetime.now(timezone.utc).isoformat(),'protected':protected,
                            'script_sha256':sha(Path(__file__)), 'outputs':{p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()},
                            'network_requests':len(requests),'archived_37_search_restarted':False,'formal_release':False})
    print(json.dumps([{'requested_file':r['requested_file'],'status':r['status'],'bytes':r.get('bytes'),'http_status':r.get('http_status')} for r in records]))


if __name__ == '__main__':
    main()
