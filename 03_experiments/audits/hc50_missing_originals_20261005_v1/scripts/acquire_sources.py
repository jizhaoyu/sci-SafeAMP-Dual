"""Capture public source attempts for the exact 44-record missing-original subset."""
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
PRIOR = ROOT / '03_experiments/audits/hc50_curve_followup_20261004_v1/review_20261005_v1'
PRIOR_SHA = 'bc3e1786b8f0290fc626deb5a844a12d8c7b9b0e1221f4187e349de02d655eb8'
METADATA = ROOT / '03_experiments/audits/hc50_primary_followup_20261004_v1/acquisition/raw/europepmc_metadata.json'
AUTHOR_PDF = 'https://air.uniud.it/bitstream/11390/1102192/1/D%27Este%20et%20al%20FSI%202016%20accepted.pdf'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def fetch(item, out):
    name, url, pmid, doi, role = item
    record = {'requested_file': name, 'url': url, 'pmid': pmid, 'doi': doi, 'role': role,
              'retrieved_at': datetime.now(timezone.utc).isoformat(), 'license': 'pending primary-source review'}
    try:
        with urlopen(Request(url, headers={'User-Agent': 'ResearchEvidenceAudit/1.0'}), timeout=20) as response:
            data = response.read()
            record.update(final_url=response.url, http_status=response.status, content_type=response.headers.get('Content-Type', ''))
        low = data.decode('utf-8', errors='replace').lower()
        if data.startswith(b'%PDF-'):
            status = 'pdf_acquired_requires_identity_review'
        elif any(term in low for term in ['pow_challenge', 'recaptcha', 'client challenge', 'checking your browser', 'access denied']):
            status = 'challenge_or_denied_response_not_original'
        elif name.endswith('.xml') and '<collection' in low and '<passage>' in low:
            status = 'bioc_acquired_requires_identity_review'
        elif role == 'pmc_primary_html' and 'article-title' in low:
            status = 'primary_html_acquired_requires_identity_review'
        else:
            status = 'response_archived_requires_full_text_check'
        if name.endswith('.pdf') and not data.startswith(b'%PDF-'):
            name += '.response.html'
            status = 'non_pdf_response_not_original'
        path = out / 'raw' / name
        with path.open('xb') as stream:
            stream.write(data)
        record.update(status=status, file=path.relative_to(out).as_posix(), sha256=sha(path), bytes=len(data))
    except HTTPError as exc:
        record.update(status='request_failed', http_status=exc.code, error=str(exc))
    except Exception as exc:
        record.update(status='request_failed', error=f'{type(exc).__name__}: {exc}')
    return record


def main():
    out = BASE / 'acquisition'
    if out.exists():
        raise FileExistsError(out)
    if sha(PRIOR / 'manifest.json') != PRIOR_SHA:
        raise ValueError('Prior review manifest changed')
    prior = json.loads((PRIOR / 'manifest.json').read_text(encoding='utf-8'))
    protected = {**prior['protected'], **prior['inputs']}
    for path in PRIOR.iterdir():
        if path.is_file():
            protected[path.relative_to(ROOT).as_posix()] = sha(path)
    protected[METADATA.relative_to(ROOT).as_posix()] = sha(METADATA)
    for name, expected in protected.items():
        if sha(ROOT / name) != expected:
            raise ValueError(f'Changed protected input: {name}')
    with (PRIOR / 'merged_candidate_decisions.csv').open(encoding='utf-8-sig') as stream:
        subset = [row for row in csv.DictReader(stream) if row['screen_status'] == 'original_not_acquired']
    groups = {(row['pmid'], row['doi']) for row in subset}
    if len(subset) != 44 or len({r['candidate_id'] for r in subset}) != 44 or len(groups) != 28:
        raise ValueError('Expected fixed 44 records and 28 research sources')
    metadata = {r['id']: r for r in json.loads(METADATA.read_text(encoding='utf-8'))['resultList']['result']}
    requests, catalog = [], []
    for index, (pmid, doi) in enumerate(sorted(groups), 1):
        entry = metadata.get(pmid, {})
        catalog.append({'study_id': f'study_{index:02}', 'pmid': pmid, 'doi': doi, 'pmcid': entry.get('pmcid', ''),
                        'title': entry.get('title', ''), 'candidate_ids': [r['candidate_id'] for r in subset if (r['pmid'], r['doi']) == (pmid, doi)]})
        requests.append((f'study_{index:02}_doi.html', f'https://doi.org/{doi}', pmid, doi, 'doi_public_page_not_automatically_original'))
        if entry.get('pmcid'):
            pmcid = entry['pmcid']
            requests.append((f'pmid_{pmid}_primary.html', f'https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/', pmid, doi, 'pmc_primary_html'))
            requests.append((f'pmid_{pmid}_bioc.xml', f'https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/{pmcid}/unicode', pmid, doi, 'official_bioc'))
    requests.append(('pmid_27818338_author_accepted.pdf', AUTHOR_PDF, '27818338', '10.1016/j.fsi.2016.11.004', 'author_repository; URL discovered through exact-title web search'))
    (out / 'raw').mkdir(parents=True, exist_ok=False)
    with (out / 'candidate_subset.csv').open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(subset[0])); writer.writeheader(); writer.writerows(subset)
    save(out / 'study_catalog.json', catalog)
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(lambda request: fetch(request, out), requests))
    save(out / 'source_acquisition.json', records)
    record = {'generated_at': datetime.now(timezone.utc).isoformat(), 'candidate_records': 44, 'study_sources': 28,
              'protected': protected, 'script_sha256': sha(Path(__file__)),
              'outputs': {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()},
              'formal_release': False, 'model_fit_calls': 0}
    save(out / 'manifest.json', record)
    print(json.dumps([{k: row.get(k) for k in ['requested_file', 'status', 'bytes', 'error']} for row in records]))


if __name__ == '__main__':
    main()
