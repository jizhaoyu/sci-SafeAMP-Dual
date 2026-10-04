"""Verify supplement against original XML metadata and retain page-level text."""
import datetime
import hashlib
import json
import pathlib
import zipfile
from pypdf import PdfReader
import pypdfium2

root = pathlib.Path(__file__).resolve().parent
target = root / 'raw/sciadv.ads8932_sm.pdf'
if target.exists():
    raise FileExistsError(target)
with zipfile.ZipFile(root / 'raw/PMC13109931_supplementary.zip') as archive:
    data = archive.read('sciadv.ads8932_sm.pdf')
assert data.startswith(b'%PDF-')
assert len(data) == 777641
assert hashlib.md5(data).hexdigest() == 'c0e137ba50af6075f92cacd79de1bf4e'
with target.open('xb') as handle:
    handle.write(data)
reader = PdfReader(target)
pages = [{'page': i + 1, 'text': page.extract_text()} for i, page in enumerate(reader.pages)]
with (root / 'foundation_pages.json').open('x', encoding='utf-8') as handle:
    json.dump(pages, handle, indent=2)
pdf = pypdfium2.PdfDocument(str(target))
selected = []
for entry in pages:
    if 'Fig. S4.' in entry['text'] or 'Table S8.' in entry['text']:
        number = entry['page']
        pdf[number - 1].render(scale=1.8).to_pil().save(root / f'foundation_page_{number}.png')
        selected.append(number)
        print(('PAGE ' + str(number) + '\n' + entry['text']).encode('ascii', errors='backslashreplace').decode())
with (root / 'foundation_inspection.json').open('x', encoding='utf-8') as handle:
    json.dump({'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'sha256': hashlib.sha256(data).hexdigest(), 'xml_size_and_md5_verified': True,
               'pages': len(pages), 'selected_pages': selected,
               'admitted_molecules': 0, 'review_mode': 'agent_primary_source_review'}, handle, indent=2)
