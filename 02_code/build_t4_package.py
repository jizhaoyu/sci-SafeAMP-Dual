"""Builds self-contained Cloud T4 training package for ESM-2 + Bilinear Interaction DTI.

Extracts:
1. 480-dim ESM-2 target embeddings for 379 kinases
2. 2048-dim Morgan fingerprints for 68 drugs
3. 15,704 pairs internal dataset with binary labels (pKd >= 7.0)
4. Phase 3 4-fold entity-isolated split indices
"""
import csv
import json
import zipfile
import io
import shutil
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_PKG = ROOT / 'output/dti-t4-esm2-bilinear-package-20261012/dti_t4_esm2_bilinear_v1'
DATA_DIR = OUT_PKG / 'data'
SPLITS_OUT = DATA_DIR / 'splits'

REVIEW = ROOT / 'output/dti-internal-validation-review-20261012'
PREP_DIR = ROOT / '03_experiments/prepared/dti_davis_features_20261006_v1'
PHASE3_SPLITS = ROOT / 'output/dti-phase3-candidate-screening-20261012/splits'
ESM_ZIP = ROOT / 'ESM2_DTI_results_20261010T093423_969769Z.zip'


def build():
    OUT_PKG.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SPLITS_OUT.mkdir(parents=True, exist_ok=True)
    
    print('1. Extracting 480-dim ESM-2 target embeddings...')
    with zipfile.ZipFile(ESM_ZIP) as z:
        b = z.read('representations/target_features.npz')
        esm_npz = np.load(io.BytesIO(b))
        esm_feats = esm_npz['features'].astype(np.float32)
        esm_ids = [str(x) for x in esm_npz['ids']]
        
    np.save(DATA_DIR / 'target_features_esm2.npy', esm_feats)
    with (DATA_DIR / 'target_ids.json').open('w', encoding='utf-8') as f:
        json.dump(esm_ids, f, indent=2)
    print(f'   Target features saved: shape {esm_feats.shape}, ids {len(esm_ids)}')
    
    print('2. Loading 2048-dim drug fingerprints...')
    drug_feats = np.load(PREP_DIR / 'drug_features.npy', allow_pickle=False).astype(np.float32)
    drug_ids = json.loads((PREP_DIR / 'drug_ids.json').read_text(encoding='utf-8-sig'))
    
    np.save(DATA_DIR / 'drug_features.npy', drug_feats)
    with (DATA_DIR / 'drug_ids.json').open('w', encoding='utf-8') as f:
        json.dump(drug_ids, f, indent=2)
    print(f'   Drug features saved: shape {drug_feats.shape}, ids {len(drug_ids)}')
    
    print('3. Loading internal assignments dataset (15,704 rows)...')
    with (REVIEW / 'internal_assignments.csv').open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
        
    pairs = []
    for r in rows:
        pairs.append({
            'drug_id': r['drug_id'],
            'target_id': r['target_id'],
            'encoded_pKd': float(r['encoded_pKd']),
            'binary_label': 1 if float(r['encoded_pKd']) >= 7.0 else 0
        })
        
    with (DATA_DIR / 'internal_pairs.json').open('w', encoding='utf-8') as f:
        json.dump(pairs, f, indent=2)
    print(f'   Internal pairs saved: {len(pairs)} records')
    
    print('4. Copying 4-fold entity-isolated splits...')
    for split_file in PHASE3_SPLITS.glob('*.json'):
        shutil.copy(split_file, SPLITS_OUT / split_file.name)
    print(f'   Copied splits to {SPLITS_OUT}')
    
    print('Package data assets built successfully!')


if __name__ == '__main__':
    build()
