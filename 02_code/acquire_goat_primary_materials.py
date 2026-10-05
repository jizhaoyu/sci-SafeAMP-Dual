"""Acquire the official supplement with bounded requests and no overwrites."""
import argparse
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path
from research_utils import ROOT, sha256, utc_now


def acquire(output):
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / '03_experiments/audits'):
        raise ValueError('An unused local audit output is required')
    raw = output / 'raw'
    raw.mkdir(parents=True, exist_ok=False)
    source = ROOT / '03_experiments/audits/alternative_primary_search_20261004_v2/raw/goat_antibacterial2018.xml'
    shutil.copyfile(source, raw / source.name)
    url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6284057/supplementaryFiles'
    record = {'generated_at': utc_now(), 'doi': '10.3389/fmicb.2018.02983',
              'pmid': '30555455', 'pmcid': 'PMC6284057', 'url': url,
              'license_as_reported_in_primary_xml': 'CC BY 4.0',
              'review_mode': 'agent_original_source_review; no human signoff claimed',
              'prior_primary_sha256': sha256(source), 'supplement_acquired': False}
    try:
        with urllib.request.urlopen(url, timeout=35) as response:
            data = response.read(20 * 1024 * 1024 + 1)
        if len(data) > 20 * 1024 * 1024 or not data.startswith(b'PK'):
            raise ValueError('Unexpected supplementary archive format or size')
        archive = raw / 'official_supplement.zip'
        with archive.open('xb') as stream:
            stream.write(data)
        with zipfile.ZipFile(archive) as bundle:
            record['archive_members'] = bundle.namelist()
            candidates = [n for n in bundle.namelist() if n.lower().endswith('.docx')]
            if len(candidates) != 1:
                raise ValueError('Expected exactly one supplementary DOCX')
            info = bundle.getinfo(candidates[0])
            if info.file_size > 20 * 1024 * 1024:
                raise ValueError('Supplementary document exceeds limit')
            with (raw / 'Data_Sheet_1.docx').open('xb') as stream:
                stream.write(bundle.read(info))
            record['docx_archive_member'] = candidates[0]
            record['supplement_acquired'] = True
    except Exception as error:
        record['error'] = str(error)
    record['finished_at'] = utc_now()
    record['outputs'] = {p.relative_to(output).as_posix(): sha256(p) for p in raw.iterdir() if p.is_file()}
    record['acquisition_script_sha256'] = sha256(Path(__file__))
    with (output / 'acquisition.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    print(json.dumps(record, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    acquire(parser.parse_args().output)
