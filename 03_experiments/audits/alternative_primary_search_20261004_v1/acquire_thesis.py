"""Acquire author-deposited thesis containing the published study, not a secondary review."""
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent
target = ROOT / 'raw/mechkarska2013_thesis.pdf'
if target.exists():
    raise FileExistsError(target)
url = 'https://edepot.wur.nl/255770'
entry = {'url': url, 'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'source_role': 'author_deposited_thesis_chapter_6_contains_2012_original_study',
         'reuse_license': 'not_yet_verified; do_not_assume_CC_BY_from_public_access'}
try:
    with urllib.request.urlopen(url, timeout=25) as response:
        data = response.read()
        entry['content_type'] = response.headers.get('Content-Type')
    assert data.startswith(b'%PDF-')
    with target.open('xb') as stream:
        stream.write(data)
    entry.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), valid_pdf=True)
except Exception as error:
    entry['error'] = str(error)
entry['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
with (ROOT / 'thesis_acquisition.json').open('x', encoding='utf-8') as stream:
    json.dump(entry, stream, indent=2)
print(json.dumps(entry, indent=2))
