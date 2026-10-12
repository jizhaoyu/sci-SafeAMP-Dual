"""Test molecular graph parsing and circular Weisfeiler-Lehman (ECFP-like) fingerprints."""
import re
from collections import defaultdict
import numpy as np

def parse_smiles(smiles: str):
    """Parse simple organic SMILES into atom and bond graph."""
    # Split salts if any
    parts = smiles.split('.')
    main_smiles = max(parts, key=len)
    
    # Tokenize SMILES
    pattern = r'(\[[^\]]+\]|Cl|Br|Si|Se|[A-Z]|[a-z]|[\(\)]|[-=#/:\\]|[0-9])'
    tokens = re.findall(pattern, main_smiles)
    
    atoms = []
    bonds = [] # (u, v, bond_type)
    
    stack = []
    prev_atom = None
    curr_bond = 1 # 1: single, 2: double, 3: triple, 4: aromatic
    ring_closures = {}
    
    for tok in tokens:
        if tok == '(':
            stack.append(prev_atom)
        elif tok == ')':
            prev_atom = stack.pop()
        elif tok == '=':
            curr_bond = 2
        elif tok == '#':
            curr_bond = 3
        elif tok == '-':
            curr_bond = 1
        elif tok in (':', '/'):
            curr_bond = 1
        elif tok.isdigit():
            ring_num = int(tok)
            if ring_num in ring_closures:
                other_atom, b_type = ring_closures.pop(ring_num)
                bonds.append((other_atom, prev_atom, b_type))
            else:
                ring_closures[ring_num] = (prev_atom, curr_bond)
                curr_bond = 1
        else:
            # Atom
            atom_idx = len(atoms)
            is_aromatic = tok.islower()
            atoms.append((tok, is_aromatic))
            if prev_atom is not None:
                bonds.append((prev_atom, atom_idx, 4 if (is_aromatic and atoms[prev_atom][1]) else curr_bond))
                curr_bond = 1
            prev_atom = atom_idx
            
    return atoms, bonds

import hashlib

def _deterministic_hash(val) -> int:
    """Compute cross-process 100% deterministic 32-bit hash regardless of PYTHONHASHSEED."""
    s = str(val).encode('utf-8')
    return int.from_bytes(hashlib.md5(s).digest()[:4], byteorder='big')

def get_morgan_fingerprint(smiles: str, radius=2, n_bits=2048):
    """Compute deterministic circular Weisfeiler-Lehman fingerprint (2048 bits)."""
    atoms, bonds = parse_smiles(smiles)
    n = len(atoms)
    adj = defaultdict(list)
    for u, v, b in bonds:
        adj[u].append((v, b))
        adj[v].append((u, b))
        
    # Initial invariants
    curr_env = []
    for i, (sym, arom) in enumerate(atoms):
        deg = len(adj[i])
        curr_env.append(_deterministic_hash((sym.upper(), arom, deg)))
        
    features = set(curr_env)
    
    for r in range(radius):
        next_env = []
        for i in range(n):
            nbr_info = tuple(sorted((b, curr_env[v]) for v, b in adj[i]))
            h = _deterministic_hash((curr_env[i], nbr_info))
            next_env.append(h)
            features.add(h)
        curr_env = next_env
        
    fp = np.zeros(n_bits, dtype=bool)
    for f in features:
        fp[f % n_bits] = True
    return fp

def tanimoto(fp1, fp2):
    b1 = np.asarray(fp1) > 0
    b2 = np.asarray(fp2) > 0
    intersection = np.sum(b1 & b2)
    union = np.sum(b1 | b2)
    return float(intersection / union) if union > 0 else 0.0

if __name__ == '__main__':
    import json
    drugs = json.loads(open('03_experiments/audits/dti_davis_field_review_20261006_v1/drugs.json', 'r', encoding='utf-8').read())
    fps = [get_morgan_fingerprint(d['smiles']) for d in drugs.values()]
    print(f"Generated fingerprints for {len(fps)} drugs.")
    sims = []
    for i in range(len(fps)):
        for j in range(i + 1, len(fps)):
            s = tanimoto(fps[i], fps[j])
            sims.append(s)
    print(f"Pairwise similarities: min={min(sims):.3f}, mean={np.mean(sims):.3f}, max={max(sims):.3f}")
    print(f"Pairs with similarity >= 0.40: {sum(s >= 0.40 for s in sims)} / {len(sims)} ({sum(s >= 0.40 for s in sims)/len(sims)*100:.1f}%)")
    print(f"Pairs with similarity >= 0.60: {sum(s >= 0.60 for s in sims)} / {len(sims)} ({sum(s >= 0.60 for s in sims)/len(sims)*100:.1f}%)")
