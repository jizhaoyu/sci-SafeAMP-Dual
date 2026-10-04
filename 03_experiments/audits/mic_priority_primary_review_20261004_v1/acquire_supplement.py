"""Acquire actual PMC linked supplement and record failures without admission."""
import datetime
import hashlib
import json
import pathlib
import urllib.request

root = pathlib.Path(__file__).resolve().parent
output = root / 'foundation_acquisition.json'
if output.exists():
    raise FileExistsError(output)
url = 'https://pmc.ncbi.nlm.nih.gov/articles/instance/13109931/bin/sciadv.ads8932_sm.pdf'
metadata = {'url': url, 'retrieved_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
try:
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as response:
        data = response.read()
        metadata.update(resolved_url=response.url, content_type=response.headers.get('Content-Type'),
                        bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), valid_pdf=data.startswith(b'%PDF-'))
    suffix = '.pdf' if metadata['valid_pdf'] else '.html'
    target = root / ('raw/foundation_supplement_response' + suffix)
    with target.open('xb') as handle:
        handle.write(data)
except Exception as error:
    metadata['error'] = str(error)
with output.open('x', encoding='utf-8') as handle:
    json.dump(metadata, handle, indent=2)
print(json.dumps(metadata, indent=2))
