"""Archive three observed public full-text routes without changing the first capture."""
from acquire_sources import BASE, ROOT, fetch, save, sha
from datetime import datetime, timezone


def main():
    out = BASE / 'additional_acquisition'
    if out.exists():
        raise FileExistsError(out)
    (out / 'raw').mkdir(parents=True)
    requests = [
        ('pmid_16753133_public.pdf', 'https://citeseerx.ist.psu.edu/document?doi=9ab656eae275ec38d64cb3695aabcf32528ccfe1&repid=rep1&type=pdf', '16753133', '10.1016/j.bbamem.2006.03.010', 'public manuscript; observed exact-title search result'),
        ('pmid_10338113_publisher.pdf', 'https://febs.onlinelibrary.wiley.com/doi/pdf/10.1016/S0014-5793%2899%2900411-1', '10338113', '10.1016/s0014-5793(99)00411-1', 'publisher PDF link observed in CiNii metadata'),
        ('pmid_22467870_bioc.xml', 'https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/PMC3366795/unicode', '22467870', '10.1074/jbc.m111.338970', 'official BioC; one later retry after rate-limited first attempt'),
    ]
    records = [fetch(request, out) for request in requests]
    save(out / 'source_acquisition.json', records)
    save(out / 'manifest.json', {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'inputs': {'acquisition/manifest.json': sha(BASE / 'acquisition/manifest.json')},
        'scripts': {p.relative_to(ROOT).as_posix(): sha(p) for p in [BASE / 'scripts/acquire_sources.py', BASE / 'scripts/acquire_additional.py']},
        'outputs': {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()},
        'formal_release': False, 'model_fit_calls': 0,
    })
    print([(r['requested_file'], r['status'], r.get('bytes', 0)) for r in records])


if __name__ == '__main__':
    main()
