"""Retrieve primary supplements into a new, non-overwriting audit directory."""
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
RAW = ROOT / 'raw'
if RAW.exists():
    raise FileExistsError(RAW)
RAW.mkdir()
BASE = 'https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41564-025-02061-0/MediaObjects/'
SOURCES = [
    ('PMC12408343_supplements.zip', 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12408343/supplementaryFiles'),
    ('41564_2025_2061_MOESM17_ESM.xlsx', BASE + '41564_2025_2061_MOESM17_ESM.xlsx'),
    ('41564_2025_2061_MOESM1_ESM.pdf', BASE + '41564_2025_2061_MOESM1_ESM.pdf'),
]

def acquire(source):
    name, url = source
    entry = {'requested_filename': name, 'url': url,
             'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=90) as response:
            data = response.read()
            entry.update(content_type=response.headers.get('Content-Type'), resolved_url=response.url)
        path = RAW / name
        with path.open('xb') as stream:
            stream.write(data)
        entry.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                     valid_pdf=data.startswith(b'%PDF-'), valid_zip=zipfile.is_zipfile(path))
        if entry['valid_zip']:
            with zipfile.ZipFile(path) as archive:
                entry['members'] = archive.namelist()
        entry['status'] = 'retrieved_valid_container' if entry['valid_pdf'] or entry['valid_zip'] else 'rejected_non_document_response'
    except Exception as error:
        entry.update(status='retrieval_failed', error=str(error))
    entry['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return entry

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    results = list(pool.map(acquire, SOURCES))
with (ROOT / 'acquisition.json').open('x', encoding='utf-8') as stream:
    json.dump(results, stream, indent=2)
print(json.dumps(results, indent=2))
