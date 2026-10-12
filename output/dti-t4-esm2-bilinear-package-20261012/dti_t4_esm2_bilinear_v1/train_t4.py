"""4-Fold Training & Evaluation script for BilinearInteractionDTI on Cloud T4 GPU.

Evaluates candidate screening (P@10, P@30, AP, C-index) and ranking diversity
across 4 entity-isolated folds on NVIDIA T4 with checkpoint resume and auto-export.
"""
import argparse
import json
import os
import time
import zipfile
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score

from model import BilinearInteractionDTI

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
SPLITS_DIR = DATA_DIR / 'splits'
CKPT_DIR = ROOT / 'checkpoints'


class DTIPairDataset(Dataset):
    def __init__(self, drug_feats: np.ndarray, target_feats: np.ndarray,
                 drug_indices: np.ndarray, target_indices: np.ndarray,
                 labels: np.ndarray):
        self.drug_feats = torch.from_numpy(drug_feats).float()
        self.target_feats = torch.from_numpy(target_feats).float()
        self.drug_idx = drug_indices
        self.target_idx = target_indices
        self.labels = torch.from_numpy(labels).float().unsqueeze(1)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        d_feat = self.drug_feats[self.drug_idx[idx]]
        t_feat = self.target_feats[self.target_idx[idx]]
        return d_feat, t_feat, self.labels[idx]


def compute_top_k(scores: np.ndarray, positive: np.ndarray, k: int) -> float:
    scores = np.asarray(scores, dtype=np.float64)
    positive = np.asarray(positive, dtype=np.float64)
    n = len(scores)
    if n == 0:
        return 0.0
    k = min(k, n)
    thresh = np.partition(scores, -k)[-k]
    above = scores > thresh
    tied = scores == thresh
    hits = float(positive[above].sum() + (k - int(above.sum())) * positive[tied].mean())
    return hits / k


def evaluate_domain(model, device, drug_feats, target_feats, rows_subset, di_subset, ti_subset, batch_size=512):
    model.eval()
    dataset = DTIPairDataset(drug_feats, target_feats, di_subset, ti_subset,
                             np.array([r['binary_label'] for r in rows_subset]))
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    
    scores = []
    with torch.no_grad():
        for d_x, t_x, _ in loader:
            d_x = d_x.to(device)
            t_x = t_x.to(device)
            out = model(d_x, t_x)
            scores.append(out.squeeze(1).cpu().numpy())
            
    scores = np.concatenate(scores) if scores else np.array([])
    y_bin = np.array([r['binary_label'] for r in rows_subset])
    
    unique_drugs = sorted({r['drug_id'] for r in rows_subset})
    p10_list, p30_list, ap_list = [], [], []
    drug_candidate_ranks = {}
    
    for d in unique_drugs:
        idx = [i for i, r in enumerate(rows_subset) if r['drug_id'] == d]
        d_scores = scores[idx]
        d_pos = y_bin[idx]
        
        # P@10 and P@30
        p10_list.append(compute_top_k(d_scores, d_pos, 10))
        p30_list.append(compute_top_k(d_scores, d_pos, 30))
        
        # AP (only defined when positive labels exist)
        if d_pos.sum() > 0:
            ap_list.append(float(average_precision_score(d_pos, d_scores)))
            
        drug_candidate_ranks[d] = np.argsort(-d_scores)
        
    # Ranking diversity: Spearman correlation across distinct drugs
    pairwise_rhos = []
    drugs_keys = list(drug_candidate_ranks.keys())
    if len(drugs_keys) >= 2:
        for i in range(min(5, len(drugs_keys))):
            for j in range(i + 1, min(5, len(drugs_keys))):
                r1 = drug_candidate_ranks[drugs_keys[i]]
                r2 = drug_candidate_ranks[drugs_keys[j]]
                common_len = min(len(r1), len(r2))
                if common_len >= 5:
                    rho = spearmanr(r1[:common_len], r2[:common_len]).statistic
                    if np.isfinite(rho):
                        pairwise_rhos.append(float(rho))
                        
    return {
        'macro_p10': float(np.mean(p10_list)) if p10_list else 0.0,
        'macro_p30': float(np.mean(p30_list)) if p30_list else 0.0,
        'macro_ap': float(np.mean(ap_list)) if ap_list else None,
        'ap_eligible_drugs': len(ap_list),
        'ap_excluded_drugs': len(unique_drugs) - len(ap_list),
        'mean_ranking_spearman': float(np.mean(pairwise_rhos)) if pairwise_rhos else None
    }


def export_results_zip(root: Path, final_report: dict):
    """Automatically packages evaluation outcomes and checkpoints into a ZIP archive."""
    ts = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    zip_name = f"DTI_T4_results_{ts}.zip"
    zip_path = root / zip_name
    
    # Write summary Markdown
    summary_md = root / "t4_summary.md"
    summary = final_report['summary']
    md_content = f"""# DTI T4 Bilinear Interaction Training Results

- **Run Timestamp**: {final_report['timestamp']}
- **Device**: {final_report['device_name']} ({final_report['device']})
- **Epochs per Fold**: {final_report['epochs']} | **Batch Size**: {final_report['batch_size']}

## Key Screening Metrics Summary
| Metric | Value | Reference / Notes |
|---|---|---|
| **Dual-Cold P@10** | **{summary['mean_dual_cold_p10']:.4f} +/- {summary['std_dual_cold_p10']:.4f}** | Primary candidate screening accuracy |
| **Cold-Drug P@10** | {summary['mean_cold_drug_p10']:.4f} | Single-entity cold drug scenario |
| **Cold-Target P@10** | {summary['mean_cold_target_p10']:.4f} | Single-entity cold target scenario |
| **Dual-Cold AP** | {f"{summary['mean_dual_cold_ap']:.4f}" if summary['mean_dual_cold_ap'] is not None else 'N/A'} | Macro AP across eligible drugs |
| **Ranking Diversity (Spearman)** | **{summary['mean_ranking_spearman']:.4f}** | <0.85 confirms drug-specific ranking |
| **Ranking Degeneracy Broken** | **{summary['ranking_diversity_verified']}** | Breaks linear additive identical rank bug |

## Decision Gate
- **Breakthrough Gate (P@10 >= 0.1500)**: {'MET' if summary['mean_dual_cold_p10'] >= 0.15 else 'NOT MET'}
- **Diversity Gate (Spearman < 0.85)**: {'MET' if summary['mean_ranking_spearman'] and summary['mean_ranking_spearman'] < 0.85 else 'PENDING'}
"""
    summary_md.write_text(md_content, encoding='utf-8')
    
    files_to_pack = [
        root / 't4_results.json',
        summary_md,
    ]
    log_file = root / 't4_training.log'
    if log_file.exists():
        files_to_pack.append(log_file)
        
    for ckpt in (root / 'checkpoints').glob('*'):
        if ckpt.is_file():
            files_to_pack.append(ckpt)
            
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in files_to_pack:
            if p.exists():
                arcname = p.relative_to(root)
                zf.write(p, arcname)
                
    print("\n" + "=" * 70)
    print(">>> TRAINING & EVALUATION COMPLETED SUCCESSFULLY! <<<")
    print(f"RESULTS ARCHIVE GENERATED: {zip_path.name} ({zip_path.stat().st_size / 1024:.1f} KB)")
    print(f"FULL LOCAL PATH: {zip_path.resolve()}")
    print("ACTION: Download this ZIP file back to your local machine, then STOP the cloud instance.")
    print("=" * 70 + "\n")


def train():
    parser = argparse.ArgumentParser(description="T4 Bilinear DTI Trainer")
    parser.add_argument('--epochs', type=int, default=25)
    parser.add_argument('--batch_size', type=int, default=256)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--smoke', action='store_true', help='Quick smoke run with 1 epoch')
    args = parser.parse_args()

    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'
    print(f"Executing on: {device} (Device Name: {device_name})")

    # Load assets
    drug_feats = np.load(DATA_DIR / 'drug_features.npy')
    target_feats = np.load(DATA_DIR / 'target_features_esm2.npy')
    drug_ids = json.loads((DATA_DIR / 'drug_ids.json').read_text(encoding='utf-8'))
    target_ids = json.loads((DATA_DIR / 'target_ids.json').read_text(encoding='utf-8'))
    pairs = json.loads((DATA_DIR / 'internal_pairs.json').read_text(encoding='utf-8'))

    dm = {d: i for i, d in enumerate(drug_ids)}
    tm = {t: i for i, t in enumerate(target_ids)}
    di_all = np.array([dm[r['drug_id']] for r in pairs], dtype=np.int64)
    ti_all = np.array([tm[r['target_id']] for r in pairs], dtype=np.int64)
    y_bin_all = np.array([r['binary_label'] for r in pairs], dtype=np.float32)

    with (SPLITS_DIR / 'splits_manifest.json').open(encoding='utf-8') as f:
        manifest = json.load(f)

    epochs = 1 if args.smoke else args.epochs
    fold_results = []
    print(f"Starting T4 4-fold training ({epochs} epochs/fold, batch_size={args.batch_size})...")

    for item in manifest:
        fold = item['fold']
        print(f"\n==================== [Fold {fold}/4] ====================")
        fold_ckpt_meta = CKPT_DIR / f'fold_{fold}_result.json'
        
        # Checkpoint Resume Check
        if fold_ckpt_meta.exists():
            try:
                with fold_ckpt_meta.open('r', encoding='utf-8') as f:
                    saved_fold_res = json.load(f)
                print(f"[CHECKPOINT HIT] Fold {fold} already completed. Loaded from {fold_ckpt_meta.name}")
                p10_loaded = saved_fold_res['val_dual_cold']['macro_p10']
                print(f"  Loaded Dual-Cold P@10: {p10_loaded:.4f}")
                fold_results.append(saved_fold_res)
                continue
            except Exception as e:
                print(f"[CHECKPOINT WARNING] Failed to read {fold_ckpt_meta} ({e}); re-running fold {fold}...")

        with (SPLITS_DIR / f'fold_{fold}.json').open(encoding='utf-8') as f:
            split_data = json.load(f)

        tr_idx = np.array(split_data['train_idx'], dtype=np.int64)
        dual_val_idx = np.array(split_data['val_dual_cold_idx'], dtype=np.int64)
        drug_val_idx = np.array(split_data['val_drug_cold_idx'], dtype=np.int64)
        target_val_idx = np.array(split_data['val_target_cold_idx'], dtype=np.int64)

        train_dataset = DTIPairDataset(drug_feats, target_feats, di_all[tr_idx], ti_all[tr_idx], y_bin_all[tr_idx])
        train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)

        model = BilinearInteractionDTI(d_drug=2048, d_target=480, hidden_dim=128).to(device)
        criterion = nn.BCEWithLogitsLoss()
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
        scaler = torch.cuda.amp.GradScaler() if torch.cuda.is_available() else None

        best_dual_p10 = 0.0
        best_ckpt = CKPT_DIR / f'best_fold_{fold}.pt'

        for ep in range(1, epochs + 1):
            model.train()
            loss_acc = 0.0
            t0 = time.monotonic()
            for d_x, t_x, y in train_loader:
                d_x, t_x, y = d_x.to(device), t_x.to(device), y.to(device)
                optimizer.zero_grad()
                if scaler:
                    with torch.cuda.amp.autocast():
                        out = model(d_x, t_x)
                        loss = criterion(out, y)
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    out = model(d_x, t_x)
                    loss = criterion(out, y)
                    loss.backward()
                    optimizer.step()
                loss_acc += loss.item() * len(y)

            ep_loss = loss_acc / len(tr_idx)
            val_dual_metrics = evaluate_domain(model, device, drug_feats, target_feats,
                                               [pairs[i] for i in dual_val_idx],
                                               di_all[dual_val_idx], ti_all[dual_val_idx])
            
            p10 = val_dual_metrics['macro_p10']
            if p10 > best_dual_p10:
                best_dual_p10 = p10
                torch.save(model.state_dict(), best_ckpt)

            dur = time.monotonic() - t0
            print(f"Epoch {ep:2d}/{epochs:2d} | Train Loss: {ep_loss:.4f} | Dual-Cold P@10: {p10:.4f} | Best: {best_dual_p10:.4f} | {dur:.1f}s")

        # Final evaluation of best checkpoint on all domains
        if best_ckpt.exists():
            model.load_state_dict(torch.load(best_ckpt, map_location=device))

        dual_res = evaluate_domain(model, device, drug_feats, target_feats,
                                   [pairs[i] for i in dual_val_idx], di_all[dual_val_idx], ti_all[dual_val_idx])
        drug_res = evaluate_domain(model, device, drug_feats, target_feats,
                                   [pairs[i] for i in drug_val_idx], di_all[drug_val_idx], ti_all[drug_val_idx])
        target_res = evaluate_domain(model, device, drug_feats, target_feats,
                                     [pairs[i] for i in target_val_idx], di_all[target_val_idx], ti_all[target_val_idx])

        fold_res_entry = {
            'fold': fold,
            'val_dual_cold': dual_res,
            'val_drug_cold': drug_res,
            'val_target_cold': target_res
        }
        with fold_ckpt_meta.open('w', encoding='utf-8') as f:
            json.dump(fold_res_entry, f, indent=2)
            
        print(f"[CHECKPOINT SAVED] Fold {fold} finished & saved to {fold_ckpt_meta.name}")
        fold_results.append(fold_res_entry)

    # Global summary across all 4 folds
    p10_dual = [f['val_dual_cold']['macro_p10'] for f in fold_results]
    p10_drug = [f['val_drug_cold']['macro_p10'] for f in fold_results]
    p10_target = [f['val_target_cold']['macro_p10'] for f in fold_results]
    ap_dual = [f['val_dual_cold']['macro_ap'] for f in fold_results if f['val_dual_cold']['macro_ap'] is not None]
    spearmans = [f['val_dual_cold']['mean_ranking_spearman'] for f in fold_results if f['val_dual_cold']['mean_ranking_spearman'] is not None]

    summary = {
        'mean_dual_cold_p10': float(np.mean(p10_dual)),
        'std_dual_cold_p10': float(np.std(p10_dual)),
        'mean_cold_drug_p10': float(np.mean(p10_drug)),
        'mean_cold_target_p10': float(np.mean(p10_target)),
        'mean_dual_cold_ap': float(np.mean(ap_dual)) if ap_dual else None,
        'mean_ranking_spearman': float(np.mean(spearmans)) if spearmans else None,
        'ranking_diversity_verified': bool(np.mean(spearmans) < 0.85) if spearmans else False
    }

    final_report = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'device': str(device),
        'device_name': device_name,
        'epochs': epochs,
        'batch_size': args.batch_size,
        'fold_results': fold_results,
        'summary': summary
    }

    with (ROOT / 't4_results.json').open('w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=2)

    print(f"\nT4 Training Summary:\n"
          f"  Dual-Cold P@10: {summary['mean_dual_cold_p10']:.4f} +/- {summary['std_dual_cold_p10']:.4f}\n"
          f"  Cold-Drug P@10: {summary['mean_cold_drug_p10']:.4f}\n"
          f"  Cold-Target P@10: {summary['mean_cold_target_p10']:.4f}\n"
          f"  Ranking Spearman Diversity: {summary['mean_ranking_spearman']}\n"
          f"  Diversity Verified (<0.85): {summary['ranking_diversity_verified']}\n")

    # Export results archive
    export_results_zip(ROOT, final_report)

    # Clean PID file on successful exit
    pid_file = ROOT / 'train.pid'
    if pid_file.exists():
        try:
            if int(pid_file.read_text().strip()) == os.getpid():
                pid_file.unlink()
        except Exception:
            pass


if __name__ == '__main__':
    train()
