"""Pre-flight self-check script for DTI T4 bundle."""
import sys
import json
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
SPLITS_DIR = DATA_DIR / 'splits'


def main():
    print("======================================================================")
    print("=== [Pre-flight Check 1/3] Python & Library Versions ===")
    print("======================================================================")
    print(f"Python: {sys.version.split()[0]}")
    print(f"PyTorch: {torch.__version__}")
    cuda_avail = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_avail}")
    if cuda_avail:
        print(f"Device: {torch.cuda.get_device_name(0)}")
        print(f"Device Count: {torch.cuda.device_count()}")
    else:
        print("Notice: CUDA is not available in this check. Training will fallback to CPU if on CPU instance.")

    print("\n======================================================================")
    print("=== [Pre-flight Check 2/3] Data & Splits Integrity ===")
    print("======================================================================")
    d_feat_p = DATA_DIR / 'drug_features.npy'
    t_feat_p = DATA_DIR / 'target_features_esm2.npy'
    d_ids_p = DATA_DIR / 'drug_ids.json'
    t_ids_p = DATA_DIR / 'target_ids.json'
    pairs_p = DATA_DIR / 'internal_pairs.json'
    manifest_p = SPLITS_DIR / 'splits_manifest.json'

    for p in [d_feat_p, t_feat_p, d_ids_p, t_ids_p, pairs_p, manifest_p]:
        if not p.exists():
            raise FileNotFoundError(f"Missing required file: {p}")

    d_feats = np.load(d_feat_p)
    t_feats = np.load(t_feat_p)
    d_ids = json.loads(d_ids_p.read_text(encoding='utf-8'))
    t_ids = json.loads(t_ids_p.read_text(encoding='utf-8'))
    pairs = json.loads(pairs_p.read_text(encoding='utf-8'))
    manifest = json.loads(manifest_p.read_text(encoding='utf-8'))

    assert len(d_ids) == d_feats.shape[0] == 68, f"Unexpected drug shape: {d_feats.shape}"
    assert d_feats.shape[1] == 2048, f"Unexpected drug feature dim: {d_feats.shape[1]}"
    assert len(t_ids) == t_feats.shape[0] == 379, f"Unexpected target shape: {t_feats.shape}"
    assert t_feats.shape[1] == 480, f"Unexpected target ESM-2 dim: {t_feats.shape[1]}"
    assert len(pairs) == 15704, f"Unexpected pairs count: {len(pairs)}"
    assert len(manifest) == 4, f"Unexpected folds count: {len(manifest)}"

    for item in manifest:
        fold = item['fold']
        fold_p = SPLITS_DIR / f'fold_{fold}.json'
        if not fold_p.exists():
            raise FileNotFoundError(f"Missing split file for fold {fold}: {fold_p}")
        f_data = json.loads(fold_p.read_text(encoding='utf-8'))
        for k in ['train_idx', 'val_dual_cold_idx', 'val_drug_cold_idx', 'val_target_cold_idx']:
            assert k in f_data, f"Missing key {k} in fold {fold}"

    print(f"Data verified: {len(d_ids)} drugs, {len(t_ids)} targets, {len(pairs)} pairs across 4 entity-isolated folds.")

    print("\n======================================================================")
    print("=== [Pre-flight Check 3/3] Neural Model Instantiation & Forward Pass ===")
    print("======================================================================")
    from model import BilinearInteractionDTI
    model = BilinearInteractionDTI(d_drug=2048, d_target=480, hidden_dim=128)
    dummy_d = torch.randn(4, 2048)
    dummy_t = torch.randn(4, 480)
    out = model(dummy_d, dummy_t)
    assert out.shape == (4, 1), f"Unexpected model output shape: {out.shape}"
    print(f"Model initialized successfully. Output shape: {list(out.shape)}")

    print("\n" + "=" * 70)
    print("[PREFLIGHT CHECK PASS] Everything is intact and ready for training!")
    print("=" * 70)


if __name__ == '__main__':
    main()
