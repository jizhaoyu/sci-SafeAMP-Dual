"""Acquire alternative original research, preserving all responses and provenance."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'raw'
if RAW.exists():
    raise FileExistsError(RAW)
RAW.mkdir()
SOURCES = [('pandinin2014', 'PMC4096598'), ('corvus2023', 'PMC10618271'),
           ('chmap2018', 'PMC6308165')]

def acquire(item):
    key, pmcid = item
    url = f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML'
    entry = {'source_id': key, 'pmcid': pmcid, 'url': url,
             'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read()
            entry['content_type'] = response.headers.get('Content-Type')
        with (RAW / f'{key}.xml').open('xb') as stream:
            stream.write(data)
        article = ET.fromstring(data)
        entry.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                     valid_article=article.tag == 'article',
                     title=' '.join(article.find('.//article-title').itertext()))
        entry['identifiers'] = {node.attrib.get('pub-id-type'): node.text
                                for node in article.findall('.//article-meta/article-id')}
        entry['license'] = [' '.join(node.itertext()) for node in article.findall('.//license')]
    except Exception as error:
        entry['error'] = str(error)
    entry['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return entry

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    entries = list(pool.map(acquire, SOURCES))
with (ROOT / 'acquisition.json').open('x', encoding='utf-8') as stream:
    json.dump(entries, stream, indent=2)
print(json.dumps(entries, indent=2, ensure_ascii=True))
