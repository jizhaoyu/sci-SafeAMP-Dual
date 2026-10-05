"""Acquire public metadata/full text for the fixed v2 pending inventory."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
PENDING = ROOT / '03_experiments/audits/gemini_hc50_external_review_20261004_v2/results/molecule_review.csv'
RESULT_MANIFEST = ROOT / '03_experiments/audits/gemini_hc50_external_review_20261004_v2/results/manifest.json'
RESULT_ANCHOR = '3804cc1f919d2a1002caf1ae2edee11031fde85631bf4c6454d0d5084d0a5186'
ECP_PDF = 'https://www.upf.edu/documents/3825543/5673788/44-207-JMedChem2011.pdf/a6394a39-09ef-4911-bb7d-54940e8cd8a9'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    with path.open('xb') as handle:
        handle.write(data)


def retrieve(url):
    request = Request(url, headers={'User-Agent': 'EvidenceReview/1.0 (public literature provenance audit)'})
    with urlopen(request, timeout=25) as response:
        return response.read(), dict(response.headers), response.geturl()


def acquire(output):
    if output.exists():
        raise FileExistsError(output)
    if sha(RESULT_MANIFEST) != RESULT_ANCHOR:
        raise ValueError('v2 manifest anchor changed')
    frozen = json.loads(RESULT_MANIFEST.read_text(encoding='utf-8'))
    if sha(PENDING) != frozen['outputs']['molecule_review.csv']:
        raise ValueError('v2 candidate inventory changed')
    with PENDING.open(encoding='utf-8') as handle:
        candidates = [c for c in csv.DictReader(handle) if c['source_reviewed'] == 'False']
    if len(candidates) != 78:
        raise ValueError('Pending inventory coverage differs')
    pmids = sorted({c['pmid'] for c in candidates if c['pmid']})
    output.mkdir(parents=True, exist_ok=False)
    raw = output / 'raw'
    raw.mkdir()
    records = []
    url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urlencode(dict(query='SRC:MED AND (' + ' OR '.join('EXT_ID:' + p for p in pmids) + ')', format='json', resultType='core', pageSize=100))
    body, headers, final_url = retrieve(url)
    write(raw / 'europepmc_metadata.json', body)
    metadata = json.loads(body)
    found = {str(r['id']): r for r in metadata['resultList']['result'] if r.get('source') == 'MED'}
    records.append(dict(source='Europe PMC metadata', url=url, final_url=final_url, retrieved_at=datetime.now(timezone.utc).isoformat(),
                        file='raw/europepmc_metadata.json', sha256=sha(raw / 'europepmc_metadata.json'), http_content_type=headers.get('Content-Type', '')))
    print(f'Metadata: requested {len(pmids)}, returned {len(found)}', flush=True)

    def get_full(pmid):
        m = found.get(pmid, {})
        record = dict(pmid=pmid, doi=m.get('doi', ''), pmcid=m.get('pmcid', ''), title=m.get('title', ''), status='metadata_only_no_pmcid', source_file='', license='', error='')
        if m.get('pmcid'):
            full_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{m['pmcid']}/fullTextXML"
            record['url'] = full_url
            try:
                data, response_headers, final = retrieve(full_url)
                article = ET.fromstring(data)
                ids = [n.text for n in article.findall('.//article-id') if n.get('pub-id-type') == 'pmid']
                if pmid not in ids:
                    raise ValueError('Full text PMID mismatch')
                path = raw / f'pmid_{pmid}.xml'
                write(path, data)
                record.update(status='full_text_xml_acquired', source_file=path.relative_to(output).as_posix(), sha256=sha(path),
                              retrieved_at=datetime.now(timezone.utc).isoformat(), final_url=final,
                              license=' | '.join(' '.join(l.itertext()) for l in article.findall('.//license')),
                              http_content_type=response_headers.get('Content-Type', ''))
            except Exception as exc:
                record.update(status='full_text_unavailable', error=f'{type(exc).__name__}: {exc}')
        return record

    with ThreadPoolExecutor(max_workers=3) as pool:
        for record in pool.map(get_full, pmids):
            records.append(record)
            print(record['pmid'], record['status'], flush=True)
    # Public author-institution repository found by explicit web search.
    try:
        data, response_headers, final = retrieve(ECP_PDF)
        if not data.startswith(b'%PDF'):
            raise ValueError('Repository did not return PDF')
        path = raw / 'pmid_21696142_author_repository.pdf'
        write(path, data)
        records.append(dict(pmid='21696142', doi='10.1021/jm200701g', url=ECP_PDF, final_url=final,
                            retrieved_at=datetime.now(timezone.utc).isoformat(), status='author_repository_pdf_acquired',
                            source_file=path.relative_to(output).as_posix(), sha256=sha(path),
                            license='Copyright ACS as reported in PDF; public institution repository access; no open reuse license verified'))
    except Exception as exc:
        records.append(dict(pmid='21696142', url=ECP_PDF, status='repository_pdf_unavailable', error=f'{type(exc).__name__}: {exc}'))
    fields = list(dict.fromkeys(k for r in records for k in r))
    with (output / 'source_acquisition.csv').open('x', encoding='utf-8', newline='') as handle:
        w = csv.DictWriter(handle, fieldnames=fields)
        w.writeheader()
        w.writerows(records)
    for c in candidates:
        c['full_text_acquisition'] = '|'.join(r['status'] for r in records if r.get('pmid') == c['pmid']) or 'identifier_missing'
    with (output / 'candidate_inventory.csv').open('x', encoding='utf-8', newline='') as handle:
        w = csv.DictWriter(handle, fieldnames=list(candidates[0]))
        w.writeheader()
        w.writerows(candidates)
    protected = {p.relative_to(ROOT).as_posix(): sha(p) for p in RESULT_MANIFEST.parent.rglob('*') if p.is_file()}
    for p in ('04_paper/research_status.json', '03_experiments/audits/mic_training_readiness_20261004_v26.json'):
        protected[p] = sha(ROOT / p)
    manifest = dict(generated_at=datetime.now(timezone.utc).isoformat(), candidate_records=78, requested_pmids=len(pmids),
                    metadata_pmids=len(found), full_text_xmls=sum(r.get('status') == 'full_text_xml_acquired' for r in records),
                    metadata_query_url=url, evidence_release_performed=False, model_fit_calls=0, protected=protected,
                    outputs={p.relative_to(output).as_posix(): sha(p) for p in output.rglob('*') if p.is_file()},
                    scripts={Path(__file__).relative_to(ROOT).as_posix(): sha(Path(__file__))})
    with (output / 'manifest.json').open('x', encoding='utf-8') as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('protected','outputs','scripts')}, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    acquire(args.output.resolve())
