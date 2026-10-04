"""Resolve two DOI discovery leads against Europe PMC before retrieving full text."""
import datetime
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
target = ROOT / 'extra_acquisition.json'
if target.exists():
    raise FileExistsError(target)
sources = [('goat_antibacterial2018', '10.3389/fmicb.2018.02983'),
           ('hymenochirin2012', '10.1016/j.peptides.2012.03.029')]
results = []
for key, doi in sources:
    entry = {'source_id': key, 'doi': doi, 'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urllib.parse.urlencode({'query': f'DOI:"{doi}"', 'format': 'json', 'resultType': 'core'})
    entry['metadata_url'] = url
    try:
        with urllib.request.urlopen(url, timeout=25) as response:
            data = response.read()
        with (ROOT / 'raw' / f'{key}_metadata.json').open('xb') as stream:
            stream.write(data)
        matches = [row for row in json.loads(data)['resultList']['result'] if row.get('doi', '').lower() == doi.lower()]
        assert len(matches) == 1
        row = matches[0]
        entry.update(pmid=row['id'], pmcid=row.get('pmcid'), title=row['title'], metadata_sha256=hashlib.sha256(data).hexdigest())
        if row.get('pmcid'):
            xml_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{row['pmcid']}/fullTextXML"
            entry['xml_url'] = xml_url
            with urllib.request.urlopen(xml_url, timeout=25) as response:
                data = response.read()
            with (ROOT / 'raw' / f'{key}.xml').open('xb') as stream:
                stream.write(data)
            entry['xml_sha256'] = hashlib.sha256(data).hexdigest()
        else:
            entry['full_text_status'] = 'no_pmc_full_text_in_metadata; abstract_not_sufficient_for_admission'
    except Exception as error:
        entry['error'] = str(error)
    entry['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    results.append(entry)
with target.open('x', encoding='utf-8') as stream:
    json.dump(results, stream, indent=2)
print(json.dumps(results, indent=2))
