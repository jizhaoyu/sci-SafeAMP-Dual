import os
import sys
import subprocess
import json

def test_gate1():
    seeds = ['0', '1', '42', '123', '999', '12345', 'random']
    test_smiles = [
        ("Gefitinib", "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1"),
        ("Erlotinib", "COCCOc1cc2ncnc(Nc3cccc(C#C)c3)c2cc1OCCOC"),
        ("Sunitinib", "CCN(CC)CCNC(=O)c1c(C)[nH]c(\C=C2/C(=O)Nc3ccc(F)cc32)c1C"),
        ("Lapatinib", "CS(=O)(=O)CCNCc1ccc(-o2ccc(Nc3ccc(OCc4cccc(F)c4)c(Cl)c3)c2)c1")
    ]
    
    print("=================================================================")
    print("GATE 1 VERIFICATION: Molecular Fingerprint Cross-Process Determinism")
    print("=================================================================")
    
    project_root = r"D:\桌面文件\sci"
    
    for name, smi in test_smiles:
        fps = []
        for s in seeds:
            code = f"""
import sys, os
sys.path.insert(0, r"{project_root}\\02_code")
from test_molecular_similarity import get_morgan_fingerprint
import json
fp = get_morgan_fingerprint("{smi}")
print(json.dumps([int(x) for x in fp]))
"""
            env = dict(os.environ)
            if s != 'random':
                env['PYTHONHASHSEED'] = s
            else:
                env.pop('PYTHONHASHSEED', None)
                
            res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
            if res.returncode != 0:
                print(f"Error executing subprocess: {res.stderr}")
                sys.exit(1)
            fps.append(json.loads(res.stdout.strip()))
            
        # Check if all runs produced exact same 2048-bit vector
        mismatches = 0
        ref = fps[0]
        for run_idx, fp in enumerate(fps[1:], start=1):
            diff = sum(1 for a, b in zip(ref, fp) if a != b)
            if diff > 0:
                mismatches += 1
                print(f"FAILED: {name} run with seed {seeds[run_idx]} has {diff} bit differences!")
                
        if mismatches == 0:
            print(f"PASS: {name:15s} across {len(seeds)} processes/seeds: 100% IDENTICAL (0 bit difference)")
        else:
            print(f"FAIL: {name:15s} had {mismatches} seed mismatches.")
            sys.exit(1)
            
    print("-----------------------------------------------------------------")
    print("GATE 1 PASSED: get_morgan_fingerprint is 100% cross-process deterministic!")
    print("=================================================================")

if __name__ == "__main__":
    test_gate1()
