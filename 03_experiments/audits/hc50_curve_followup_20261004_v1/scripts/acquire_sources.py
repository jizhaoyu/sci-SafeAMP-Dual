"""Archive fixed public originals and observed attachment links without solving challenges."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
PRIOR = ROOT / '03_experiments/audits/slay_primary_review_20261004_v1/review'
PRIOR_SHA = '997fc0e593b86acba732b427aaa202d35c6b9b9650f7a7b39eb5b3a80333095a'
IDS = {'DBAASP_19706', 'DBAASP_9865', 'DBAASP_25709', 'DBAASP_25712'}
PAPERS = {'35323465': 'PMC8953592', '27917162': 'PMC5114273', '41735465': 'PMC13031288'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def fetch(name, url, out, basis):
    row = {'requested_file': name, 'url': url, 'url_basis': basis,
           'retrieved_at': datetime.now(timezone.utc).isoformat(),
           'license': 'not yet reviewed; acquisition does not grant redistribution rights'}
    try:
        with urlopen(Request(url, headers={'User-Agent': 'ResearchEvidenceAudit/1.0'}), timeout=25) as response:
            data = response.read()
            row.update(final_url=response.url, http_status=response.status, content_type=response.headers.get('Content-Type', ''))
        text = data.decode('utf-8', errors='replace').lower()
        status = 'response_requires_review'
        suffix = name.rsplit('.', 1)[-1]
        valid = {'docx': data.startswith(b'PK'), 'jpg': data.startswith(b'\xff\xd8'), 'pdf': data.startswith(b'%PDF-')}
        if suffix in valid:
            if not valid[suffix]:
                name += '.response.html'
                status = 'unexpected_format_not_original'
            else:
                status = 'expected_format_requires_content_review'
        elif any(word in text for word in ['recaptcha', 'pow_challenge', 'checking your browser']):
            status = 'challenge_page_not_original'
        path = out / 'raw' / name
        with path.open('xb') as stream:
            stream.write(data)
        row.update(status=status, file=path.relative_to(out).as_posix(), sha256=sha(path), bytes=len(data))
    except HTTPError as exc:
        row.update(status='request_failed', http_status=exc.code, error=str(exc))
    except Exception as exc:
        row.update(status='request_failed', error=f'{type(exc).__name__}: {exc}')
    return row


def main():
    out = BASE / 'acquisition'
    if out.exists():
        raise FileExistsError(out)
    if sha(PRIOR / 'manifest.json') != PRIOR_SHA:
        raise ValueError('Prior review changed')
    prior = json.loads((PRIOR / 'manifest.json').read_text(encoding='utf-8'))
    protected = dict(prior['protected'])
    protected.update(prior['inputs'])
    for path in PRIOR.iterdir():
        if path.is_file():
            protected[path.relative_to(ROOT).as_posix()] = sha(path)
    old_sources = ROOT / '03_experiments/audits/hc50_primary_followup_20261004_v1/acquisition'
    for pmid in PAPERS:
        source = old_sources / f'raw/pmid_{pmid}.xml'
        protected[source.relative_to(ROOT).as_posix()] = sha(source)
    inventory = old_sources / 'candidate_inventory.csv'
    protected[inventory.relative_to(ROOT).as_posix()] = sha(inventory)
    for name, expected in protected.items():
        if sha(ROOT / name) != expected:
            raise ValueError(f'Protected input changed: {name}')
    with (PRIOR / 'merged_candidate_decisions.csv').open(encoding='utf-8-sig') as stream:
        subset = [r for r in csv.DictReader(stream) if r['candidate_id'] in IDS]
    if len(subset) != 4:
        raise ValueError('Fixed coverage is not four')
    (out / 'raw').mkdir(parents=True, exist_ok=False)
    with (out / 'candidate_subset.csv').open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(subset[0]))
        writer.writeheader(); writer.writerows(subset)
    results = []
    for pmid, pmcid in PAPERS.items():
        url = f'https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/'
        row = fetch(f'pmid_{pmid}.html', url, out, 'PMCID in previously bound original XML')
        results.append(row)
        if not row.get('file') or row['status'] == 'challenge_page_not_original':
            continue
        soup = BeautifulSoup((out / row['file']).read_bytes(), 'html.parser')
        if pmid == '35323465':
            for number in [1, 2]:
                fig = soup.find(id=f'marinedrugs-20-00167-f00{number}')
                if fig is not None and fig.find('img'):
                    results.append(fetch(f'ct7_figure_{number}.jpg', urljoin(url, fig.find('img')['src']), out, f'Observed primary HTML Figure {number} img src'))
        if pmid == '27917162':
            fig = soup.find(id='F3')
            if fig is not None and fig.find('img'):
                results.append(fetch('toap2_figure_3.jpg', urljoin(url, fig.find('img')['src']), out, 'Observed primary HTML Figure 3 img src'))
        if pmid == '41735465':
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'MOESM' in href and href.endswith('.docx'):
                    filename = href.rsplit('/', 1)[-1]
                    if filename not in {r['requested_file'] for r in results}:
                        results.append(fetch(filename, urljoin(url, href), out, 'Observed public primary article attachment href'))
    write_json(out / 'source_acquisition.json', results)
    record = {'generated_at': datetime.now(timezone.utc).isoformat(), 'fixed_candidates': sorted(IDS),
              'protected': protected, 'script_sha256': sha(Path(__file__)),
              'outputs': {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()},
              'formal_release': False, 'model_fit_calls': 0}
    write_json(out / 'manifest.json', record)
    print(json.dumps([{k: r.get(k) for k in ['requested_file', 'status', 'bytes', 'error']} for r in results]))


if __name__ == '__main__':
    main()
