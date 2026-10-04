"""Archive primary-source discovery inputs; never release labels or train models."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent
SOURCES = {
    'pandi2023': 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10632401/fullTextXML',
    'foundation2025': 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13109931/fullTextXML',
    'hybrid2018': 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6099547/fullTextXML',
    'spectrum2020': 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7436000/fullTextXML',
    'capitellacin2022': 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC8953592/fullTextXML',
    'qmap2026': 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13473575/fullTextXML',
    'hydramp2023': 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10017685/fullTextXML',
}

def retrieve(item):
    name, url = item
    record = {'source_id': name, 'requested_url': url,
              'retrieved_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ScientificEvidenceReview/1.0'})
        with urllib.request.urlopen(req, timeout=35) as response:
            data = response.read()
            record.update(status_code=response.status, final_url=response.url,
                          content_type=response.headers.get('Content-Type'))
        path = ROOT / 'raw' / (name + '.xml')
        with path.open('xb') as stream:
            stream.write(data)
        record.update(status='retrieved_unreviewed', path=str(path.relative_to(ROOT)),
                      bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    except Exception as error:
        record.update(status='retrieval_failed', error=str(error))
    return record

if __name__ == '__main__':
    if (ROOT / 'acquisition.json').exists() or (ROOT / 'raw').exists():
        raise SystemExit('Refusing to overwrite an existing acquisition')
    (ROOT / 'raw').mkdir()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(retrieve, SOURCES.items()))
    manifest = {'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'status': 'discovery_only_not_evidence_release', 'sources': records,
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with (ROOT / 'acquisition.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    for record in records:
        print(record['source_id'], record['status'], record.get('bytes', record.get('error')))
