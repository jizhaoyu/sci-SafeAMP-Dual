import pandas as pd
import hashlib
from collections import Counter
from research_data import sequence_identity

RECORDS_PATH = r"D:\桌面文件\sci\03_experiments\prepared\amd02_evidence_clean_20261001\records.csv"
df_records = pd.read_csv(RECORDS_PATH)

seqs = df_records['seq'].tolist()
n = len(seqs)
hemo_labels = df_records['hemo'].tolist()

counts = [Counter(s) for s in seqs]

# Let's test multiple cutoffs
cutoffs = [0.40, 0.50, 0.60, 0.70, 0.80]
results = []

for cutoff in cutoffs:
    parent = list(range(n))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
        
    edges = 0
    checked = 0
    for i in range(n):
        a = seqs[i]
        for j in range(i):
            b = seqs[j]
            denom = max(len(a), len(b))
            if sum((counts[i] & counts[j]).values()) / denom < cutoff:
                continue
            checked += 1
            if sequence_identity(a, b, identity_mode='alignment') >= cutoff:
                parent[find(i)] = find(j)
                edges += 1
                
    # Count clusters
    cluster_map = {}
    for i in range(n):
        r = find(i)
        if r not in cluster_map:
            cluster_map[r] = []
        cluster_map[r].append(i)
        
    num_clusters = len(cluster_map)
    sizes = [len(members) for members in cluster_map.values()]
    max_size = max(sizes)
    
    # Check hemo=1.0 distribution
    hemo1_clusters = set()
    hemo0_clusters = set()
    for c_root, members in cluster_map.items():
        for m in members:
            if hemo_labels[m] == 1.0:
                hemo1_clusters.add(c_root)
            elif hemo_labels[m] == 0.0:
                hemo0_clusters.add(c_root)
                
    results.append({
        'cutoff': cutoff,
        'checked_pairs': checked,
        'edges': edges,
        'num_clusters': num_clusters,
        'max_cluster_size': max_size,
        'hemo1_clusters_count': len(hemo1_clusters),
        'hemo0_clusters_count': len(hemo0_clusters)
    })
    print(f"Cutoff {cutoff:.2f} -> Clusters: {num_clusters}, Max Cluster: {max_size}, Hemo=1 Clusters: {len(hemo1_clusters)}, Hemo=0 Clusters: {len(hemo0_clusters)}, Edges: {edges}")

print("\n--- Summary of Cutoff Sensitivity ---")
df_res = pd.DataFrame(results)
print(df_res.to_string(index=False))
