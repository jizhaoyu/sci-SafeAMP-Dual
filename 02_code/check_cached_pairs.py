import pandas as pd
import hashlib
from collections import Counter
from research_data import sequence_identity

RECORDS_PATH = r"D:\桌面文件\sci\03_experiments\prepared\amd02_evidence_clean_20261001\records.csv"
df_records = pd.read_csv(RECORDS_PATH)
df_records['sample_id'] = df_records['seq'].apply(lambda s: hashlib.sha256(s.encode()).hexdigest()[:24])

seqs = df_records['seq'].tolist()
n = len(seqs)

# Precalculate pairwise alignments (or sample/upper bound to be fast)
# Since n=417, n*(n-1)/2 = 86,736 pairs. We can compute them or load if precalculated.
# Let's check if pairwise similarities are already cached in 03_experiments/prepared/amd02_evidence_clean_20261001
# Wait, let's check what's in that folder first!
