"""Inspect the 16 remaining open original XML papers and their 84 observations."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

originals_dir = Path('03_experiments/audits/dti_open_original_acquisition_20261006_v1')
assay_pending = json.loads(Path('03_experiments/audits/dti_assay_link_review_20261006_v1/assay_evidence_pending.json').read_text(encoding='utf-8'))
manifest = json.loads((originals_dir / 'acquisition_manifest.json').read_text(encoding='utf-8'))

reviewed_3 = {'24497639', '27775715', '25089924'}
acquired_records = [r for r in manifest['records'] if r['status'] == 'acquired_not_reviewed' and r['pmid'] not in reviewed_3]

by_pmid = defaultdict(list)
for r in assay_pending:
    if r.get('PMID') in {rec['pmid'] for rec in acquired_records}:
        by_pmid[r['PMID']].append(r)
def text_clean(n):
    return ' '.join(''.join(n.itertext()).split()) if n is not None else ''

for i, rec in enumerate(acquired_records):
    pmid = rec['pmid']
    xml_path = originals_dir / rec['filename']
    root = ET.parse(xml_path).getroot()
    title = text_clean(root.find('.//article-title'))
    obs = by_pmid[pmid]
    
    print(f"=== [{i+1}/16] PMID {pmid} ({len(obs)} obs) DOI: {rec.get('doi')} ===")
    print(f"  Title: {title[:90]}...")
    
    # Check tables
    tables = root.findall('.//table-wrap')
    for t in tables:
        t_id = t.attrib.get('id', '')
        caption = text_clean(t.find('.//caption'))
        tbl_text = text_clean(t)
        matched_obs = []
        for o in obs:
            kd_val = float(o['Kd (nM)'])
            kd_str = str(o['Kd (nM)'])
            kd_um = kd_val / 1000.0
            kd_um_str1 = f"{kd_um:.1f}"
            kd_um_str2 = f"{kd_um:.2f}"
            kd_um_str3 = f"{kd_um:.3f}".rstrip('0').rstrip('.')
            if (kd_str in tbl_text or (kd_um_str1 in tbl_text and len(kd_um_str1) > 2)
                    or (kd_um_str2 in tbl_text and len(kd_um_str2) > 3)
                    or (kd_um_str3 in tbl_text and len(kd_um_str3) > 1)):
                matched_obs.append(o['observation_id'])
        if matched_obs:
            print(f"  Table {t_id} matched {len(matched_obs)} obs: {caption[:80]}")
    
    # Check if any obs not matched in tables
    full_body = text_clean(root.find('.//body'))
    matched_in_body = []
    for o in obs:
        kd_val = float(o['Kd (nM)'])
        kd_str = str(o['Kd (nM)'])
        kd_um = kd_val / 1000.0
        kd_um_str = f"{kd_um:.2f}".rstrip('0').rstrip('.')
        if kd_str in full_body or (kd_um_str and kd_um_str in full_body and len(kd_um_str) > 2):
            matched_in_body.append(o['observation_id'])
    print(f"  Matched in full body text: {len(matched_in_body)} / {len(obs)} obs")
    
    # Check protein targets & constructs
    for o in obs[:2]:
        tgt = o['raw_identity_context'].get('Target Name')
        seq_len = len(o.get('BindingDB Target Chain Sequence 1', ''))
        print(f"  Obs {o['observation_id']}: Kd={o['Kd (nM)']} nM, Target={tgt} (seq_len={seq_len})")
    print()
