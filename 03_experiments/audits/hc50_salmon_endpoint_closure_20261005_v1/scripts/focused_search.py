"""Supplement punctuation-sensitive discovery with explicit biological context."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlencode
from acquire import BASE, EPMC, fetch, save, sha


def main():
    out = BASE / 'focused_search'
    if out.exists():
        raise FileExistsError(out)
    queries = {
        'fragment_names_biological': 'cathelicidin AND ("TT(1-24)" OR "TT(1-35)" OR "SF(18-45)" OR "rtCATH2(1-40)" OR "rtCATH2(5-40)")',
        'literal_sequences': '("KFRTRRSKSSSNGGRKGSKG" OR "KFRTRRSKSSSNGGRKGSKGGSKGRPGSGSSIAGA" OR "KFRSNGRHGSGSRLGGGSLIGRPGGGS" OR "RRGKDSGGPKMGRKNSKGGWRGRPGSGSRPGFGSGI" OR "KIRTRRGKDSGGPKMGRKNSKGGWRGRPGSGSRPGFGSGI")',
        'index_control_2016': 'EXT_ID:27818338 AND SRC:MED',
    }
    requests = [(name+'.json', EPMC+urlencode({'query':query,'format':'json','resultType':'core','pageSize':100}), '', '', 'discovery/metadata; incomplete full-text indexing cannot establish evidence absence') for name,query in queries.items()]
    (out/'raw').mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(lambda request: fetch(request,out), requests))
    save(out/'queries.json', {'queries':queries, 'page_size':100, 'limitations':'Names containing punctuation produced unrelated hits in first query; retain original results and screen explicitly. Sequence search and name search do not cover unindexed supplementary material.'})
    save(out/'source_acquisition.json',records)
    save(out/'manifest.json', {'generated_at':datetime.now(timezone.utc).isoformat(), 'script_sha256':sha(__import__('pathlib').Path(__file__)), 'outputs':{p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}})
    print([(r['requested_file'],r['status']) for r in records])


if __name__ == '__main__':
    main()
