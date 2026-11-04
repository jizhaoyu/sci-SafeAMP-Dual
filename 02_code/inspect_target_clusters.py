import pandas as pd
import hashlib

RECORDS_PATH = r"D:\桌面文件\sci\03_experiments\prepared\amd02_evidence_clean_20261001\records.csv"
CLUSTERS_PATH = r"D:\桌面文件\sci\03_experiments\prepared\amd02_evidence_clean_20261001\cluster_membership.csv"

df_records = pd.read_csv(RECORDS_PATH)
df_clusters = pd.read_csv(CLUSTERS_PATH)
df_records['sample_id'] = df_records['seq'].apply(lambda s: hashlib.sha256(s.encode()).hexdigest()[:24])
df_merged = pd.merge(df_records, df_clusters, on="sample_id")

target_clusters = [6, 14, 20, 29, 32, 53, 66, 82]

for c in target_clusters:
    sub = df_merged[df_merged['cluster_id'] == c]
    print(f"=== Cluster {c} (Total members: {len(sub)}) ===")
    print("hemo labels:", sub['hemo'].value_counts(dropna=False).to_dict())
    print("amp labels:", sub['amp'].value_counts(dropna=False).to_dict())
    for _, r in sub.iterrows():
        print(f"  {r['record_id']} | seq={r['seq']} | amp={r['amp']} | hemo={r['hemo']}")
