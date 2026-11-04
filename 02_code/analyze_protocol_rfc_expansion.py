import pandas as pd
import json
import hashlib
from collections import Counter
import os

RECORDS_PATH = r"D:\桌面文件\sci\03_experiments\prepared\amd02_evidence_clean_20261001\records.csv"
CLUSTERS_PATH = r"D:\桌面文件\sci\03_experiments\prepared\amd02_evidence_clean_20261001\cluster_membership.csv"

df_records = pd.read_csv(RECORDS_PATH)
df_clusters = pd.read_csv(CLUSTERS_PATH)

df_records['sample_id'] = df_records['seq'].apply(lambda s: hashlib.sha256(s.encode()).hexdigest()[:24])

df_merged = pd.merge(df_records, df_clusters, on="sample_id")

print(f"Total merged records: {len(df_merged)}")
print(f"Unique sequences: {df_merged['seq'].nunique()}")
print(f"Total clusters: {df_merged['cluster_id'].nunique()}")

# Check distribution of labels in current prepared dataset
print("\n--- Current Label Distribution in Prepared Dataset ---")
print("hemo value counts:")
print(df_merged['hemo'].value_counts(dropna=False))
print("\namp value counts:")
print(df_merged['amp'].value_counts(dropna=False))

# Clusters with hemo=1 vs hemo=0
hemo1_clusters = df_merged[df_merged['hemo'] == 1.0]['cluster_id'].unique()
hemo0_clusters = df_merged[df_merged['hemo'] == 0.0]['cluster_id'].unique()
print(f"\nClusters with hemo=1.0: {len(hemo1_clusters)} -> {sorted(hemo1_clusters)}")
print(f"Clusters with hemo=0.0: {len(hemo0_clusters)} -> {len(hemo0_clusters)} clusters")

# Let's inspect which records have hemo=1.0 in df_merged
print("\n--- Records with hemo=1.0 in df_merged ---")
hemo1_df = df_merged[df_merged['hemo'] == 1.0]
for idx, row in hemo1_df.iterrows():
    print(f"Record: {row['record_id']}, Cluster: {row['cluster_id']}, Seq: {row['seq'][:15]}... ({len(row['seq'])}aa), amp: {row['amp']}, hemo: {row['hemo']}")
