import glob
import json
import pandas as pd
import sys
sys.path.insert(0, 'D:/桌面文件/sci/02_code')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from research_data import sequence_identity

dev_df = pd.read_csv('D:/桌面文件/sci/03_experiments/prepared/amd02_evidence_clean_20261001/records.csv')
dev_seqs = dev_df['seq'].tolist()
dev_record_ids = dev_df['record_id'].tolist()

files = glob.glob('D:/桌面文件/sci/02_code/data/sources/dbaasp_v1/raw/peptide_*.json')

candidates = []
for f in files:
    with open(f, 'r', encoding='utf-8') as fp:
        data = json.load(fp)
    pid = data.get('id')
    seq = data.get('sequence', '')
    if not seq:
        continue
    length = len(seq)
    if length < 10 or length > 50:
        continue
    standard_aas = set("ACDEFGHIKLMNPQRSTVWY")
    if not all(aa in standard_aas for aa in seq):
        continue
        
    # Check if in dev
    if f"DBAASP:{pid}" in dev_record_ids:
        continue
        
    # Hemolysis 50%
    hemos = data.get('hemoliticCytotoxicActivities', [])
    h50 = []
    for h in hemos:
        tc = (h.get('targetCell') or {}).get('name', '')
        if 'human' in tc.lower() and ('erythrocyte' in tc.lower() or 'rbc' in tc.lower()):
            val = str(h.get('activityMeasureForLysisValue', ''))
            grp = str((h.get('activityMeasureForLysisGroup') or {}).get('name', ''))
            if '50%' in val or '50%' in grp or 'hc50' in val.lower() or 'hc50' in grp.lower():
                h50.append(h)
    if not h50:
        continue
        
    # MIC
    targets = data.get('targetActivities', [])
    mics = []
    for t in targets:
        sp = ((t.get('targetSpecies') or {}).get('name', '')).lower()
        grp = (t.get('activityMeasureGroup') or {}).get('name', '')
        if 'escherichia coli' in sp and grp == 'MIC':
            mics.append(t)
    if not mics:
        continue
        
    # Max identity to dev
    max_id = 0.0
    nearest = None
    for d_id, d_seq in zip(dev_record_ids, dev_seqs):
        ident = sequence_identity(seq, d_seq, identity_mode='alignment')
        if ident > max_id:
            max_id = ident
            nearest = d_id
            
    bonds = data.get('intrachainBonds', []) + data.get('interchainBonds', [])
    cys_count = seq.count('C')
    cterm = data.get('cTerminus') or data.get('CTerminus')
    nterm = data.get('nTerminus') or data.get('NTerminus')
    name = data.get('name', '')
    arts = data.get('articles', [])
    pmids = [(a.get('pubmed') or {}).get('pubmedId') for a in arts]
    
    candidates.append({
        'dbaasp_id': pid,
        'name': name,
        'seq': seq,
        'len': length,
        'cys': cys_count,
        'bonds': len(bonds),
        'bond_types': [b.get('type', {}).get('name') for b in bonds],
        'cycle_types': [b.get('cycleType', {}).get('name') for b in bonds],
        'cterm': cterm,
        'nterm': nterm,
        'max_id': max_id,
        'nearest': nearest,
        'pmids': pmids,
        'hemo_act': h50[0].get('activity'),
        'hemo_unit': (h50[0].get('unit') or {}).get('name'),
        'mic_act': mics[0].get('activity'),
        'mic_conc': mics[0].get('concentration'),
        'mic_unit': (mics[0].get('unit') or {}).get('name'),
        'mic_strain': (mics[0].get('targetSpecies') or {}).get('name')
    })

df_c = pd.DataFrame(candidates)
df_c = df_c.sort_values('max_id')
print(f"Total candidates meeting basic dual criteria: {len(df_c)}")
for idx, r in df_c.iterrows():
    print(f"ID: {r['dbaasp_id']} | {r['name']} | max_id: {r['max_id']:.4f} ({r['nearest']}) | Cys: {r['cys']} | Bonds: {r['bonds']} ({r['cycle_types']}) | Hemo: {r['hemo_act']} {r['hemo_unit']} | MIC: {r['mic_conc']} {r['mic_unit']} | PMIDs: {r['pmids']}")
