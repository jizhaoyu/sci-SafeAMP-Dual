"""Read original COAs, retaining page text and file hashes; no endpoint labels."""
import datetime
import hashlib
import io
import json
import pathlib
import zipfile
from pypdf import PdfReader

root = pathlib.Path(__file__).resolve().parent
output = root / 'coa_text.json'
if output.exists():
    raise FileExistsError(output)
records = []
with zipfile.ZipFile(root / 'raw/COA_archaeasins.zip') as archive:
    for name in archive.namelist():
        if not name.endswith('.pdf') or name.startswith('__MACOSX'):
            continue
        data = archive.read(name)
        reader = PdfReader(io.BytesIO(data))
        records.append({'archive_member': name, 'sha256': hashlib.sha256(data).hexdigest(),
                        'pages': [page.extract_text() for page in reader.pages],
                        'admitted': False, 'label': None})
with output.open('x', encoding='utf-8') as handle:
    json.dump({'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'review_mode': 'agent_primary_source_review', 'records': records}, handle, indent=2)
assert len(records) == 80
print('Extracted 80 COAs; no sequence-to-assay mapping assumed.')
print(records[0]['pages'][0].encode('ascii', errors='backslashreplace').decode())
