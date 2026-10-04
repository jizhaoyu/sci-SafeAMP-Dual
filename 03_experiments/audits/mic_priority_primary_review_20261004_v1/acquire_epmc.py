"""Fetch official supplementary bundles through documented Europe PMC API."""
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import urllib.request
import zipfile

root = pathlib.Path(__file__).resolve().parent
output = root / 'epmc_acquisition.json'
if output.exists():
    raise FileExistsError(output)

def acquire(pmcid):
    url = f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/supplementaryFiles'
    result = {'pmcid': pmcid, 'url': url,
              'retrieved_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        target = root / f'raw/{pmcid}_supplementary.zip'
        if target.exists():
            raise FileExistsError(target)
        with urllib.request.urlopen(url, timeout=45) as response:
            data = response.read()
            result.update(content_type=response.headers.get('Content-Type'), resolved_url=response.url)
        with target.open('xb') as handle:
            handle.write(data)
        result.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), valid_zip=zipfile.is_zipfile(target))
        if result['valid_zip']:
            with zipfile.ZipFile(target) as archive:
                result['members'] = archive.namelist()
    except Exception as error:
        result['error'] = str(error)
    return result

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(acquire, ['PMC12408343', 'PMC13109931']))
with output.open('x', encoding='utf-8') as handle:
    json.dump(results, handle, indent=2)
print(json.dumps(results, indent=2))
