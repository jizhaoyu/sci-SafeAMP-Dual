"""Acquisition script for alternative primary sources v2."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'raw'

def verify_all():
    records = []
    files = {
        'pandinin2014.xml': ('10.1371/journal.pone.0101742', 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4096598/'),
        'corvus2023.xml': ('10.1038/s41598-023-45875-w', 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10618271/'),
        'chmap2018.xml': ('10.3389/fphar.2018.01501', 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6308165/'),
        'goat_antibacterial2018.xml': ('10.3389/fmicb.2018.02983', 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6284057/'),
        'mechkarska2013_thesis.pdf': ('10.1016/j.peptides.2012.03.029', 'https://edepot.wur.nl/255770'),
    }
    for filename, (doi, url) in files.items():
        path = RAW / filename
        if not path.exists():
            raise FileNotFoundError(f'Missing required raw file: {path}')
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        records.append({
            'filename': filename,
            'doi': doi,
            'url': url,
            'bytes': len(data),
            'sha256': digest,
            'verified_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
    return records

if __name__ == '__main__':
    recs = verify_all()
    print(json.dumps(recs, indent=2))
