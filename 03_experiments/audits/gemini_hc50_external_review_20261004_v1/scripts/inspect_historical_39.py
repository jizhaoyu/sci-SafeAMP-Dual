import pandas as pd
import json

df = pd.read_csv('D:/桌面文件/sci/03_experiments/audits/dramp_dual_task_primary_audit_20261003_v1/candidate_primary_audit.csv')
print(f"Total rows: {len(df)}")

pmid_groups = df.groupby('pubmed_id')
for pmid, grp in pmid_groups:
    names = list(grp['name'])
    dramp_ids = list(grp['dramp_id'])
    primary_barrier = list(grp['primary_barrier'].unique())
    dispositions = list(grp['disposition'].unique())
    print(f"\nPMID: {pmid} (N={len(grp)})")
    print(f"  Names: {names[:4]}")
    print(f"  DRAMP IDs: {dramp_ids[:4]}")
    print(f"  Dispositions: {dispositions}")
    print(f"  Barriers: {primary_barrier}")
