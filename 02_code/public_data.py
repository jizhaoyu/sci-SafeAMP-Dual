"""Cache original DBAASP records; derive only explicitly measured endpoints.

AMP: E. coli MIC <=32 ug/ml positive, >=128 ug/ml weak-activity negative.
Hemo: human erythrocyte HC50 <=100 ug/ml positive, >=250 ug/ml negative.
Unsupported, intermediate, missing or conflicting measurements stay unknown.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import re
import time
import urllib.request
import urllib.error
import pandas as pd
from feature_extractor import MOLECULAR_WEIGHTS, STANDARD_AMINO_ACIDS
from research_utils import ROOT, sha256, utc_now, write_json
from research_data import REQUIRED

DBAASP = 'https://dbaasp.org'
RETRY_BACKOFFS = [2, 5, 15]


def cached_get(url, path, max_retries=3):
    """Retrieve URL with caching, explicit checksum validation, and exponential backoff."""
    path = Path(path)
    if not path.exists():
        error = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'SafeAMP-reproducible-research/1.0', 'Accept': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    body = r.read()
                json.loads(body)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
                write_json(
                    path.with_suffix('.source.json'),
                    {'url': url, 'retrieved_at': utc_now(), 'sha256': sha256(path)}
                )
                break
            except urllib.error.HTTPError as exc:
                error = exc
                retry_after = exc.headers.get('Retry-After')
                if retry_after and retry_after.isdigit():
                    sleep_sec = int(retry_after)
                else:
                    sleep_sec = RETRY_BACKOFFS[min(attempt, len(RETRY_BACKOFFS) - 1)]
                time.sleep(sleep_sec)
            except Exception as exc:
                error = exc
                sleep_sec = RETRY_BACKOFFS[min(attempt, len(RETRY_BACKOFFS) - 1)]
                time.sleep(sleep_sec)
        else:
            raise RuntimeError(f'Download failed after {max_retries} attempts: {url}: {type(error).__name__} {error}')

    side = path.with_suffix('.source.json')
    if not side.exists() or json.loads(side.read_text(encoding='utf-8'))['sha256'] != sha256(path):
        raise ValueError(f'Cached source checksum mismatch for {path}. Expected matching .source.json')
    return json.loads(path.read_text(encoding='utf-8'))


def bounds(value):
    text = str(value).strip().replace('≤', '<=').replace('≥', '>=')
    number = r'(?:\d+(?:\.\d*)?|\.\d+)'
    m = re.fullmatch(r'([<>]=?)?\s*(' + number + r')', text)
    if m:
        op, x = m.group(1), float(m.group(2))
        if x <= 0:
            return None
        if op and op.startswith('>'):
            return x, math.inf
        if op and op.startswith('<'):
            return 0.0, x
        return x, x
    m = re.fullmatch('(' + number + r')\s*[-–]\s*(' + number + ')', text)
    if m and 0 < float(m.group(1)) <= float(m.group(2)):
        return float(m.group(1)), float(m.group(2))
    return None


def measurement_label(assay, sequence, positive_cutoff, negative_cutoff):
    interval = bounds(assay.get('concentration'))
    if interval is None:
        return None
    unit = (assay.get('unit') or {}).get('name', '').replace('μ', 'u').replace('µ', 'u').lower().replace(' ', '')
    if unit in {'ug/ml', 'mg/l'}:
        factor = 1.0
    elif unit == 'um':
        factor = (sum(MOLECULAR_WEIGHTS[a] for a in sequence) - 18.0152 * (len(sequence) - 1)) / 1000
    else:
        return None
    low, high = interval[0] * factor, interval[1] * factor
    if high <= positive_cutoff:
        return 1
    if low >= negative_cutoff:
        return 0
    return None


def _name(value):
    return value.get('name', '') if isinstance(value, dict) else (value or '')


def extract_record(raw, path):
    seq = raw.get('sequence', '')
    if not isinstance(seq, str) or not 10 <= len(seq) <= 50 or set(seq) - set(STANDARD_AMINO_ACIDS):
        return None, 'noncanonical_or_length'
    if _name(raw.get('complexity')).lower() != 'monomer':
        return None, 'not_monomer'
    if any(raw.get(k) for k in ['cTerminus', 'nTerminus', 'CTerminus', 'NTerminus', 'intrachainBonds', 'interchainBonds', 'coordinationBonds', 'unusualAminoAcids']):
        return None, 'unsupported_modification'
    if not raw.get('articles'):
        return None, 'missing_publication_reference'
    labels = {'amp': set(), 'hemo': set()}
    evidence = {'amp': [], 'hemo': []}
    for a in raw.get('targetActivities', []):
        if a.get('activityMeasureValue') != 'MIC' or not _name(a.get('targetSpecies')).startswith('Escherichia coli'):
            continue
        label = measurement_label(a, seq, 32, 128)
        if label is not None:
            labels['amp'].add(label)
            evidence['amp'].append(a)
    for a in raw.get('hemoliticCytotoxicActivities', []):
        if _name(a.get('targetCell')).lower() != 'human erythrocytes' or a.get('activityMeasureForLysisValue') not in ['50% Hemolysis', 'HC50']:
            continue
        label = measurement_label(a, seq, 100, 250)
        if label is not None:
            labels['hemo'].add(label)
            evidence['hemo'].append(a)
    y = {t: next(iter(v)) if len(v) == 1 else None for t, v in labels.items()}
    if all(v is None for v in y.values()):
        return None, 'missing_or_conflicting_endpoints'
    accession = str(raw.get('dbaaspId') or raw['id'])
    return {
        'record_id': 'DBAASP:' + str(raw['id']),
        'seq': seq,
        **y,
        'source_dataset': 'DBAASP',
        'source_accession': accession,
        'source_url': DBAASP + '/peptides/' + str(raw['id']),
        'evidence_reference': json.dumps(raw['articles'], ensure_ascii=False),
        'label_basis': 'Ecoli_MIC_ugml_32_128;human_HC50_ugml_100_250;conflicts_missing',
        'assay_conditions': json.dumps(evidence, ensure_ascii=False),
        'modifications': 'none',
        'evidence_type': 'experimental',
        'is_synthetic': False,
        'source_role': 'development',
        'raw_path': Path(path).resolve().relative_to(ROOT).as_posix(),
        'raw_sha256': sha256(path)
    }, None


def download_dbaasp(output, limit=1200, resume=True, workers=4):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError('Sources must be stored in the project workspace.')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'raw').mkdir(parents=True, exist_ok=True)

    listing = []
    offset = 0
    while True:
        page = cached_get(f'{DBAASP}/peptides?limit=1000&offset={offset}', output / 'raw' / f'index_{offset}.json')
        batch = page.get('data', [])
        if not batch:
            break
        listing.extend(batch)
        offset += len(batch)
        if offset >= page['totalCount']:
            break
        if len({x['id'] for x in listing}) != len(listing):
            raise ValueError('Pagination repeated identifiers.')

    candidates = [
        r for r in listing
        if isinstance(r.get('sequence'), str) and 10 <= len(r['sequence']) <= 50
        and not (set(r['sequence']) - set(STANDARD_AMINO_ACIDS))
        and str(r.get('complexity', '')).lower() == 'monomer'
        and not any(r.get(k) for k in ['cTerminus', 'nTerminus', 'CTerminus', 'NTerminus'])
    ]
    candidates.sort(key=lambda r: hashlib.sha256(('safeamp-source-v1:' + str(r['id'])).encode()).hexdigest())
    selected = candidates[:limit] if limit else candidates

    checkpoint_file = output / 'checkpoint.json'
    checkpoint = {'completed_ids': [], 'failed_ids': [], 'last_updated': utc_now()}
    if resume and checkpoint_file.exists():
        try:
            checkpoint = json.loads(checkpoint_file.read_text(encoding='utf-8'))
        except Exception:
            pass

    completed_set = set(checkpoint.get('completed_ids', []))

    manifest = {
        'status': 'collecting',
        'created_at': utc_now(),
        'database_url': DBAASP,
        'listed_records': len(listing),
        'eligible_listing_records': len(candidates),
        'selected_records': len(selected),
        'selection': 'smallest SHA256(safeamp-source-v1:ID)',
        'limit': limit,
        'endpoint_definitions': {
            'amp': 'E. coli MIC <=32 vs >=128 ug/ml',
            'hemo': 'Human erythrocyte HC50 <=100 vs >=250 ug/ml'
        },
        'license': 'Database reuse terms require author review before redistribution; raw downloads retained locally.'
    }
    write_json(output / 'source_manifest.json', manifest)

    def fetch(row):
        rid = row['id']
        path = output / 'raw' / ('peptide_' + str(rid) + '.json')
        try:
            data = cached_get(DBAASP + '/peptides/' + str(rid), path)
            record, reason = extract_record(data, path)
            return rid, record, {'id': rid, 'reason': reason} if reason else None
        except Exception as e:
            return rid, None, {'id': rid, 'reason': 'download_error', 'error': str(e)}

    records = []
    exclusions = []

    # If records.csv exists from previous run and resume is enabled, reload existing valid records
    if resume and (output / 'records.csv').exists():
        try:
            prev_df = pd.read_csv(output / 'records.csv')
            records = prev_df.to_dict('records')
        except Exception:
            records = []

    if resume and (output / 'exclusions.json').exists():
        try:
            exclusions = json.loads((output / 'exclusions.json').read_text(encoding='utf-8'))
        except Exception:
            exclusions = []

    todo = [row for row in selected if row['id'] not in completed_set]
    print(f"[DBAASP Downloader] Total selected: {len(selected)}, Already completed: {len(completed_set)}, Remaining: {len(todo)}")

    if todo:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for i, (rid, record, excluded) in enumerate(pool.map(fetch, todo), 1):
                if record:
                    records.append(record)
                if excluded:
                    exclusions.append(excluded)
                completed_set.add(rid)

                if i % 50 == 0 or i == len(todo):
                    checkpoint['completed_ids'] = list(completed_set)
                    checkpoint['last_updated'] = utc_now()
                    write_json(checkpoint_file, checkpoint)
                    print(f"Fetched {i}/{len(todo)} (Total completed: {len(completed_set)}); eligible records: {len(records)}", flush=True)

    frame = pd.DataFrame(records, columns=REQUIRED).drop_duplicates(subset=['record_id'])
    frame.to_csv(output / 'records.csv', index=False)
    write_json(output / 'exclusions.json', exclusions)
    manifest.update(
        status='downloaded',
        retained_records=len(frame),
        records_sha256=sha256(output / 'records.csv'),
        label_counts={
            t: {str(k): int(v) for k, v in frame[t].value_counts(dropna=False).items()}
            for t in ['amp', 'hemo']
        },
        external_source_present=False
    )
    write_json(output / 'source_manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT / '02_code/data/sources/dbaasp_v1')
    p.add_argument('--limit', type=int, default=1200, help='0 fetches all eligible entries; positive limit is a declared pilot.')
    p.add_argument('--no-resume', action='store_true', help='Disable resuming from checkpoint')
    p.add_argument('--workers', type=int, default=4, help='Concurrent worker threads')
    a = p.parse_args()
    if a.limit < 0:
        p.error('limit must be nonnegative')
    print(json.dumps(download_dbaasp(a.output, a.limit, resume=not a.no_resume, workers=a.workers), ensure_ascii=False))
