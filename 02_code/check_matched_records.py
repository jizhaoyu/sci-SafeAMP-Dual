import pandas as pd
import hashlib

RECORDS_PATH = r"D:\桌面文件\sci\03_experiments\prepared\amd02_evidence_clean_20261001\records.csv"
CLUSTERS_PATH = r"D:\桌面文件\sci\03_experiments\prepared\amd02_evidence_clean_20261001\cluster_membership.csv"

df_records = pd.read_csv(RECORDS_PATH)
df_clusters = pd.read_csv(CLUSTERS_PATH)
df_records['sample_id'] = df_records['seq'].apply(lambda s: hashlib.sha256(s.encode()).hexdigest()[:24])
df_merged = pd.merge(df_records, df_clusters, on="sample_id")

records_to_check = ['DBAASP:166', 'DBAASP:18177', 'DBAASP:22898', 'DBAASP:7043', 'DBAASP:12537', 'DBAASP:22345', 'DBAASP:9494', 'DBAASP:12243', 'DBAASP:12887', 'DBAASP:144', 'DBAASP:4262']

for r_id in records_to_check:
    row = df_merged[df_merged['record_id'] == r_id]
    if len(row) > 0:
        c = row.iloc[0]['cluster_id']
        seq = row.iloc[0]['seq']
        amp = row.iloc[0]['amp']
        hemo = row.iloc[0]['hemo']
        print(f"{r_id} -> Cluster {c} | amp={amp}, hemo={hemo} | seq={seq}")
    else:
        print(f"{r_id} not found in df_merged!")
