import json
import pandas as pd
import sys
sys.path.insert(0, 'D:/桌面文件/sci/02_code')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

candidate_ids = [10605, 1886, 1893, 20562, 25709, 25712, 4230, 4283, 4285, 4287, 6545]

for cid in candidate_ids:
    path = f"D:/桌面文件/sci/02_code/data/sources/dbaasp_v1/raw/peptide_{cid}.json"
    with open(path, 'r', encoding='utf-8') as f:
        d = json.load(f)
    seq = d.get('sequence', '')
    name = d.get('name', '')
    cys_count = seq.count('C')
    synth = d.get('synthesisType', {})
    c_term = d.get('cTerminus') or d.get('CTerminus')
    n_term = d.get('nTerminus') or d.get('NTerminus')
    bonds = d.get('intrachainBonds', []) + d.get('interchainBonds', [])
    complexity = d.get('complexity', {})
    arts = d.get('articles', [])
    pmids = [(a.get('pubmed') or {}).get('pubmedId') for a in arts]
    titles = [a.get('title') for a in arts]
    
    # Hemo
    hemos = d.get('hemoliticCytotoxicActivities', [])
    hemo_obs = []
    for h in hemos:
        tc = (h.get('targetCell') or {}).get('name', '')
        if 'human' in tc.lower() and 'erythrocyte' in tc.lower():
            hemo_obs.append((h.get('activity'), (h.get('unit') or {}).get('name'), h.get('activityMeasureForLysisValue')))
            
    # MIC
    targets = d.get('targetActivities', [])
    mic_obs = []
    for t in targets:
        sp = ((t.get('targetSpecies') or {}).get('name', '')).lower()
        if 'escherichia coli' in sp:
            mic_obs.append((t.get('activity'), (t.get('unit') or {}).get('name'), t.get('concentration'), t.get('targetSpecies', {}).get('name')))
            
    print(f"=== DBAASP:{cid} | {name} ===")
    print(f"  Seq: {seq} (Len {len(seq)}, Cys: {cys_count})")
    print(f"  Complexity: {complexity.get('name')}, Synthesis: {synth.get('name')}")
    print(f"  N-term: {n_term}, C-term: {c_term}, Bonds: {bonds}")
    print(f"  PMIDs: {pmids}")
    print(f"  Titles: {titles}")
    print(f"  Hemo obs: {hemo_obs}")
    print(f"  MIC obs: {mic_obs}")
