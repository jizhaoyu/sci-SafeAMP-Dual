"""Acquire the publicly linked author certificates without overwriting evidence."""
import datetime
import hashlib
import json
import pathlib
import urllib.request
import zipfile

root = pathlib.Path(__file__).resolve().parent
raw = root / 'raw'
raw.mkdir(exist_ok=True)
target = raw / 'COA_archaeasins.zip'
if target.exists():
    raise FileExistsError(target)
url = 'https://data.mendeley.com/public-files/datasets/d8yzgtdrcp/files/b1307377-6e4d-4f63-b2c1-da070f075949/file_downloaded'
request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(request, timeout=60) as response:
    data = response.read()
    metadata = {'url': url, 'resolved_url': response.url,
                'content_type': response.headers.get('Content-Type'),
                'retrieved_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
target.write_bytes(data)
metadata.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                valid_zip=zipfile.is_zipfile(target),
                landing_page='https://data.mendeley.com/datasets/d8yzgtdrcp/5',
                dataset_version=5, dataset_doi='10.17632/d8yzgtdrcp.5')
if metadata['valid_zip']:
    with zipfile.ZipFile(target) as archive:
        metadata['members'] = archive.namelist()
(root / 'coa_acquisition.json').open('x', encoding='utf-8').write(json.dumps(metadata, indent=2))
print(json.dumps(metadata, indent=2))
