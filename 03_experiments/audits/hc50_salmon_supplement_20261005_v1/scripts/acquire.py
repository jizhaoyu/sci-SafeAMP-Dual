"""Public supplementary/identity followup; captured content never auto-releases evidence."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
PREVIOUS = ROOT / '03_experiments/audits/hc50_missing_originals_20261005_v1'
sys.path.insert(0, str(PREVIOUS / 'scripts'))
from acquire_sources import fetch

PRIOR_SHA = '7dca526dcc1cb94907cab5a2a1d99d0c2e8984d3e252ede7bf94d50b3f95b392'
GOV_PDF = 'https://www.tfrin.gov.tw/redirect_files.php?file_name=2nIc64xhkN8S3WSWGPlus4BWGPluszmiAhvzDgNm7ab9ssN3tFmWmDzIsh0WGSlashTeJrg4HkMEDK9x3Dd4KrBRlr04fCXqsW3dHYWGEqualvwXQt9K8PmAKKzp1nWGSlashzDWGSlash4OdbxJRSlgqElpElv3OKKdFZ6Hjj9R9QzGmWGPlus7pWfakiRxJv5CWGSlashWuwRgwuWilZwHX&id=6940'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)


def main():
    out = BASE / 'acquisition'
    if out.exists():
        raise FileExistsError(out)
    prior_file = PREVIOUS / 'review/manifest.json'
    if sha(prior_file) != PRIOR_SHA:
        raise ValueError('Previous review binding changed')
    prior = json.loads(prior_file.read_text(encoding='utf-8'))
    protected = {**prior['protected'], **prior['inputs']}
    protected.update({p.relative_to(ROOT).as_posix():sha(p) for p in PREVIOUS.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for name, expected in protected.items():
        if sha(ROOT/name) != expected:
            raise ValueError(f'Changed historical input: {name}')
    # Explicit identifiers and public routes, discovered in primary metadata/search.
    # CDN names below are DERIVED attempts, not claimed observed supplement links.
    requests = [
        ('udine_record.html','https://air.uniud.it/handle/11390/1102192','27818338','10.1016/j.fsi.2016.11.004','observed author repository metadata'),
        ('trieste_record.html','https://arts.units.it/handle/11368/2891873','27818338','10.1016/j.fsi.2016.11.004','observed repository; closed PDF is not requested'),
        ('publisher_article.html','https://www.sciencedirect.com/science/article/pii/S1050464816306994','27818338','10.1016/j.fsi.2016.11.004','publisher public article page'),
        ('derived_mmc1.pdf','https://ars.els-cdn.com/content/image/1-s2.0-S1050464816306994-mmc1.pdf','27818338','10.1016/j.fsi.2016.11.004','DERIVED public CDN pattern from verified PII; not an observed or verified S1 link'),
        ('derived_mmc1.docx','https://ars.els-cdn.com/content/image/1-s2.0-S1050464816306994-mmc1.docx','27818338','10.1016/j.fsi.2016.11.004','DERIVED public CDN pattern from verified PII; not an observed or verified S1 link'),
        ('chang2006_pmc.html','https://pmc.ncbi.nlm.nih.gov/articles/PMC1346769/','16377685','10.1128/aac.50.1.185-195.2006','PMC primary study; identity corroboration only'),
        ('chang2006_bioc.xml','https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/PMC1346769/unicode','16377685','10.1128/aac.50.1.185-195.2006','official BioC; identity corroboration only'),
        ('chang2006_government.pdf',GOV_PDF,'16377685','10.1128/aac.50.1.185-195.2006','observed government-hosted original PDF; identity corroboration only'),
    ]
    for number in ['20859','20860','20862','20863','20864']:
        requests.append((f'DRAMP{number}.html',f'https://dramp.cpu-bioinfor.org/browse/All_Information.php?id=DRAMP{number}','27818338','10.1016/j.fsi.2016.11.004','official database entry; secondary annotation, not a primary assay'))
    (out/'raw').mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        records=list(pool.map(lambda request:fetch(request,out),requests))
    discovered=[]
    for record in records:
        if record['requested_file'] not in ['udine_record.html','trieste_record.html'] or not record.get('file'):
            continue
        page=BeautifulSoup((out/record['file']).read_bytes(),'html.parser')
        for link in page.select('a[href]'):
            href=link['href']
            if '/bitstream/' in href:
                discovered.append({'page':record['url'],'url':urljoin(record['url'],href),'link_text':link.get_text(' ',strip=True),
                                   'policy':'metadata only for closed Trieste files; verify public availability before any additional fetch'})
    write_json(out/'source_acquisition.json',records)
    write_json(out/'repository_links.json',discovered)
    write_json(out/'manifest.json',{'generated_at':datetime.now(timezone.utc).isoformat(),'protected':protected,
                                  'script_sha256':sha(Path(__file__)),'previous_review_manifest_sha256':PRIOR_SHA,
                                  'outputs':{p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()},
                                  'formal_release':False,'model_fit_calls':0})
    print(json.dumps([{'file':r['requested_file'],'status':r['status'],'bytes':r.get('bytes'),'http_status':r.get('http_status')} for r in records]))


if __name__=='__main__':
    main()
