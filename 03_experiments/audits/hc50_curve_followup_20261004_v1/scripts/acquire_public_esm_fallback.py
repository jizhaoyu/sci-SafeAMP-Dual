"""Try Springer's standard public static-content host; retain previous failures."""
from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET
from acquire_sources import BASE, ROOT, fetch, sha, write_json

out = BASE / 'publisher_static_content_acquisition_20261005'
if out.exists():
    raise FileExistsError(out)
(out / 'raw').mkdir(parents=True, exist_ok=False)
source = ROOT / '03_experiments/audits/hc50_primary_followup_20261004_v1/acquisition/raw/pmid_41735465.xml'
r = ET.parse(source).getroot()
doi = next(x.text for x in r.findall('.//article-id') if x.get('pub-id-type') == 'doi')
rows = []
for media in r.findall('.//supplementary-material/media'):
    filename = media.get('{http://www.w3.org/1999/xlink}href')
    if not filename.endswith('.docx') or '/' in filename:
        raise ValueError('Unexpected supplementary filename')
    url = f'https://static-content.springer.com/esm/art%3A{quote(doi, safe="")}/MediaObjects/{filename}'
    rows.append(fetch(filename, url, out, 'Standard public Springer static-content route; DOI and filename from primary XML; constructed URL, not an observed hyperlink'))
write_json(out / 'source_acquisition.json', rows)
record = {'script_sha256': sha(Path(__file__)), 'source_file': source.relative_to(ROOT).as_posix(),
          'source_sha256': sha(source), 'outputs': {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()},
          'formal_release': False}
write_json(out / 'manifest.json', record)
print([{k: row.get(k) for k in ['requested_file', 'status', 'bytes', 'error']} for row in rows])
