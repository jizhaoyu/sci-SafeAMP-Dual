import glob
import json
import pandas as pd
import sys
sys.path.insert(0, 'D:/桌面文件/sci/02_code')
from research_data import sequence_identity

# Load development records
dev_df = pd.read_csv('D:/桌面文件/sci/03_experiments/prepared/amd02_evidence_clean_20261001/records.csv')
dev_seqs = dev_df['seq'].tolist()
dev_record_ids = dev_df['record_id'].tolist()

# Load all DBAASP files
files = glob.glob('D:/桌面文件/sci/02_code/data/sources/dbaasp_v1/raw/peptide_*.json')
print(f"Total DBAASP peptide files: {len(files)}")

results = []

for f in files:
    with open(f, 'r', encoding='utf-8') as fp:
        data = json.load(fp)
    
    pid = data.get('id')
    name = data.get('name', '')
    seq = data.get('sequence', '')
    if not seq:
        continue
    
    # Check length
    length = len(seq)
    
    # Check amino acids
    standard_aas = set("ACDEFGHIKLMNPQRSTVWY")
    is_standard = all(aa in standard_aas for aa in seq)
    
    # Check terminal modifications
    cterm = data.get('cTerminus') or data.get('CTerminus')
    nterm = data.get('nTerminus') or data.get('NTerminus')
    
    # Hemolysis
    hemo_list = data.get('hemoliticCytotoxicActivities', [])
    human_hemo_50 = []
    for h in hemo_list:
        tc = (h.get('targetCell') or {}).get('name', '')
        if 'human' in tc.lower() and ('erythrocyte' in tc.lower() or 'rbc' in tc.lower() or 'red blood' in tc.lower()):
            val = str(h.get('activityMeasureForLysisValue', ''))
            grp = str((h.get('activityMeasureForLysisGroup') or {}).get('name', ''))
            if '50%' in val or '50%' in grp or 'hc50' in val.lower() or 'hc50' in grp.lower():
                human_hemo_50.append(h)
                
    if not human_hemo_50:
        continue
        
    # E. coli MIC
    target_acts = data.get('targetActivities', [])
    ecoli_mics = []
    for t in target_acts:
        sp = ((t.get('targetSpecies') or {}).get('name', '')).lower()
        grp = (t.get('activityMeasureGroup') or {}).get('name', '')
        if 'escherichia coli' in sp and grp == 'MIC':
            ecoli_mics.append(t)
            
    # Articles
    articles = data.get('articles', [])
    pmids = [(a.get('pubmed') or {}).get('pubmedId') for a in articles if (a.get('pubmed') or {}).get('pubmedId')]
    
    # Check if already in dev records
    in_dev = f"DBAASP:{pid}" in dev_record_ids
    
    # Check max identity to dev set
    max_id = 0.0
    nearest_dev = None
    if 10 <= length <= 50 and is_standard:
        for d_id, d_seq in zip(dev_record_ids, dev_seqs):
            ident = sequence_identity(seq, d_seq, identity_mode='alignment')
            if ident > max_id:
                max_id = ident
                nearest_dev = d_id
                
    results.append({
        'dbaasp_id': pid,
        'name': name,
        'sequence': seq,
        'length': length,
        'is_standard': is_standard,
        'nterm': nterm,
        'cterm': cterm,
        'human_hemo_50_count': len(human_hemo_50),
        'human_hemo_50_sample': human_hemo_50[0].get('activity'),
        'human_hemo_50_unit': (human_hemo_50[0].get('unit') or {}).get('name'),
        'ecoli_mic_count': len(ecoli_mics),
        'ecoli_mic_sample': ecoli_mics[0].get('activity') if ecoli_mics else None,
        'ecoli_mic_unit': (ecoli_mics[0].get('unit') or {}).get('name') if ecoli_mics else None,
        'pmids': pmids,
        'in_dev': in_dev,
        'max_identity_to_dev': max_id,
        'nearest_dev': nearest_dev
    })

res_df = pd.DataFrame(results)
print(f"Total peptides with Human RBC 50% hemolysis: {len(res_df)}")
print(f"In dev set: {res_df['in_dev'].sum()}")
print(f"Not in dev set: {(~res_df['in_dev']).sum()}")
print(f"Length 10-50 and standard AAs: {((res_df['length'] >= 10) & (res_df['length'] <= 50) & res_df['is_standard']).sum()}")
print(f"Has E. coli MIC: {(res_df['ecoli_mic_count'] > 0).sum()}")

# Cross check: Not in dev, standard, len 10-50, has E. coli MIC, max_identity < 0.40
dual_cands = res_df[
    (~res_df['in_dev']) & 
    (res_df['length'] >= 10) & 
    (res_df['length'] <= 50) & 
    res_df['is_standard'] & 
    (res_df['ecoli_mic_count'] > 0)
]
print(f"\nDual candidates (not in dev, len 10-50, standard, has E. coli MIC): {len(dual_cands)}")
for idx, row in dual_cands.iterrows():
    print(f"DBAASP:{row['dbaasp_id']}, {row['name']}, len={row['length']}, max_id={row['max_identity_to_dev']:.4f} (to {row['nearest_dev']}), MIC_n={row['ecoli_mic_count']}, PMIDs={row['pmids']}, C-term={row['cterm']}")
