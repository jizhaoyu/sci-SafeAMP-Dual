"""Generates publication-quality figures for DTI Candidate Screening and Bilinear Model.

Figure 1: Multi-model screening performance comparison (P@10 in Dual-Cold & Cold-Drug settings).
Figure 2: Empirical cross-drug ranking diversity heatmap (Additive degeneracy vs. Bilinear specificity).
Outputs both high-resolution PNG (300 DPI) and vector PDF formats.
"""
import json
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from scipy.stats import spearmanr
import torch

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / '04_paper/figures'
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Add package directory to path to load BilinearInteractionDTI
PKG_DIR = ROOT / 'output/dti-t4-esm2-bilinear-package-20261012/dti_t4_esm2_bilinear_v1'
sys.path.insert(0, str(PKG_DIR))
from model import BilinearInteractionDTI

# Configure Matplotlib styles for academic publication
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans'],
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9.5,
    'ytick.labelsize': 9.5,
    'legend.fontsize': 9.5,
    'figure.titlesize': 13,
    'axes.linewidth': 1.0,
    'grid.linewidth': 0.5,
    'grid.alpha': 0.4,
    'axes.edgecolor': '#333333',
    'xtick.color': '#333333',
    'ytick.color': '#333333',
})


def plot_figure_1_screening_performance():
    """Generates Figure 1: Model comparison across screening evaluation domains."""
    models = [
        'Constant Reference',
        'Additive Tobit (CPU)',
        'Additive HGB (CPU)',
        'Additive LogReg (CPU)',
        'Bilinear Interaction\n+ ESM-2 (T4 GPU)'
    ]
    
    # Dual-Cold P@10 means and standard deviations
    dual_cold_p10 = [0.0970, 0.0417, 0.1019, 0.1038, 0.1615]
    dual_cold_std = [0.0, 0.0, 0.0157, 0.0310, 0.0243]
    
    # Cold-Drug P@10 means and standard deviations
    cold_drug_p10 = [0.0970, 0.1154, 0.3000, 0.1385, 0.2885]
    cold_drug_std = [0.0, 0.0, 0.0350, 0.0280, 0.0886]

    colors = ['#888888', '#D55E00', '#E69F00', '#56B4E9', '#0072B2']
    edge_colors = ['#555555', '#993300', '#B37400', '#2B83BA', '#004477']
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.0), layout='constrained')
    
    x = np.arange(len(models))
    width = 0.55
    
    # --- Panel A: Dual-Cold Screening Precision ---
    bars1 = ax1.bar(x, dual_cold_p10, width, yerr=dual_cold_std, capsize=4,
                    color=colors, edgecolor=edge_colors, linewidth=1.2, zorder=3)
    
    # Benchmark lines
    ax1.axhline(0.0970, color='#666666', linestyle='--', linewidth=1.2, zorder=2,
                label='Random/Constant Baseline (0.0970)')
    ax1.axhline(0.1500, color='#D55E00', linestyle=':', linewidth=1.4, zorder=2,
                label='Pre-registered Breakthrough Gate (0.1500)')
    
    # Highlight the winning model bar
    bars1[-1].set_hatch('//')
    
    # Value annotations on top of bars
    for i, bar in enumerate(bars1):
        yval = bar.get_height()
        err = dual_cold_std[i]
        offset = 0.006 if err == 0 else err + 0.005
        ax1.text(bar.get_x() + bar.get_width() / 2.0, yval + offset,
                 f'{yval:.4f}', ha='center', va='bottom', fontsize=8.5,
                 fontweight='bold' if i == 4 else 'normal')
        
    ax1.set_title('(a) Dual-Cold Candidate Screening Precision (P@10)', fontweight='bold', pad=10)
    ax1.set_ylabel('Top-10 Precision (P@10)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(models, rotation=22, ha='right')
    ax1.set_ylim(0, 0.22)
    ax1.yaxis.set_major_locator(ticker.MultipleLocator(0.05))
    ax1.grid(axis='y', linestyle='--', zorder=0)
    ax1.legend(loc='upper left', framealpha=0.9)
    
    # Annotation note
    ax1.annotate('Gate Passed\n(+66.5% gain)', xy=(4, 0.1615), xytext=(3.4, 0.195),
                 arrowprops=dict(arrowstyle='->', color='#0072B2', lw=1.2),
                 fontsize=9, fontweight='bold', color='#0072B2', ha='center')

    # --- Panel B: Cold-Drug Screening Precision ---
    bars2 = ax2.bar(x, cold_drug_p10, width, yerr=cold_drug_std, capsize=4,
                    color=colors, edgecolor=edge_colors, linewidth=1.2, zorder=3)
    
    ax2.axhline(0.0970, color='#666666', linestyle='--', linewidth=1.2, zorder=2,
                label='Random/Constant Baseline (0.0970)')
    
    bars2[-1].set_hatch('//')
    
    for i, bar in enumerate(bars2):
        yval = bar.get_height()
        err = cold_drug_std[i]
        offset = 0.010 if err == 0 else err + 0.008
        ax2.text(bar.get_x() + bar.get_width() / 2.0, yval + offset,
                 f'{yval:.4f}', ha='center', va='bottom', fontsize=8.5,
                 fontweight='bold' if i in (2, 4) else 'normal')
        
    ax2.set_title('(b) Cold-Drug Candidate Screening Precision (P@10)', fontweight='bold', pad=10)
    ax2.set_ylabel('Top-10 Precision (P@10)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(models, rotation=22, ha='right')
    ax2.set_ylim(0, 0.44)
    ax2.yaxis.set_major_locator(ticker.MultipleLocator(0.10))
    ax2.grid(axis='y', linestyle='--', zorder=0)
    ax2.legend(loc='upper left', framealpha=0.9)

    out_png = FIG_DIR / 'fig1_screening_ablation_comparison.png'
    out_pdf = FIG_DIR / 'fig1_screening_ablation_comparison.pdf'
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)
    print(f"Generated Figure 1 -> {out_png}")


def plot_figure_2_ranking_diversity():
    """Generates Figure 2: Ranking correlation heatmap comparing Additive vs Bilinear."""
    # Load actual fold 1 weights and validation data to compute empirical ranking correlation
    data_dir = PKG_DIR / 'data'
    drug_feats = np.load(data_dir / 'drug_features.npy')
    target_feats = np.load(data_dir / 'target_features_esm2.npy')
    drug_ids = json.loads((data_dir / 'drug_ids.json').read_text(encoding='utf-8'))
    target_ids = json.loads((data_dir / 'target_ids.json').read_text(encoding='utf-8'))
    pairs = json.loads((data_dir / 'internal_pairs.json').read_text(encoding='utf-8'))

    with (data_dir / 'splits/fold_1.json').open(encoding='utf-8') as f:
        split = json.load(f)

    val_pairs = [pairs[i] for i in split['val_dual_cold_idx']]
    val_drugs = sorted({r['drug_id'] for r in val_pairs})
    candidate_target_ids = sorted({r['target_id'] for r in val_pairs})

    dm = {d: i for i, d in enumerate(drug_ids)}
    tm = {t: i for i, t in enumerate(target_ids)}

    model = BilinearInteractionDTI(d_drug=2048, d_target=480, hidden_dim=128)
    ckpt = ROOT / 'output/dti-t4-esm2-bilinear-results-20261012/checkpoints/best_fold_1.pt'
    model.load_state_dict(torch.load(ckpt, map_location='cpu'))
    model.eval()

    sample_n = 10
    sample_drugs = val_drugs[:sample_n]
    t_x = torch.from_numpy(target_feats[[tm[t] for t in candidate_target_ids]]).float()

    bilinear_ranks = []
    with torch.no_grad():
        for d in sample_drugs:
            d_x = torch.from_numpy(drug_feats[dm[d]]).float().unsqueeze(0).expand(len(t_x), -1)
            scores = model(d_x, t_x).squeeze().numpy()
            bilinear_ranks.append(np.argsort(-scores))

    corr_bilinear = np.zeros((sample_n, sample_n))
    for i in range(sample_n):
        for j in range(sample_n):
            corr_bilinear[i, j] = spearmanr(bilinear_ranks[i], bilinear_ranks[j]).statistic

    # Additive model always yields identical ranks across all drugs (rho = 1.000)
    corr_additive = np.ones((sample_n, sample_n))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.2), layout='constrained')
    drug_labels = [f"Drug {i+1}" for i in range(sample_n)]

    # Colormap normalization from -0.2 to 1.0
    import matplotlib as mpl
    norm = mpl.colors.Normalize(vmin=-0.2, vmax=1.0)
    cmap = plt.get_cmap('RdBu_r')

    # Panel A: Additive Linear Model
    im1 = ax1.imshow(corr_additive, cmap=cmap, norm=norm, aspect='auto')
    ax1.set_title('(a) Additive Model (Linear Tobit / Ridge)\nSpearman Correlation = 1.000 (Identical Ranking Degeneracy)',
                  fontweight='bold', fontsize=10.5, pad=10)
    ax1.set_xticks(range(sample_n))
    ax1.set_yticks(range(sample_n))
    ax1.set_xticklabels(drug_labels, rotation=45, ha='right')
    ax1.set_yticklabels(drug_labels)
    
    # Overlay text annotations
    for i in range(sample_n):
        for j in range(sample_n):
            ax1.text(j, i, "1.00", ha='center', va='center', color='black', fontsize=7.5)

    # Panel B: Bilinear Interaction Model
    im2 = ax2.imshow(corr_bilinear, cmap=cmap, norm=norm, aspect='auto')
    mean_off_diag = np.mean(corr_bilinear[np.triu_indices(sample_n, k=1)])
    ax2.set_title(f'(b) Bilinear Interaction + ESM-2 (T4 GPU)\nMean Pairwise Spearman = {mean_off_diag:.3f} (Drug-Specific Selectivity)',
                  fontweight='bold', fontsize=10.5, pad=10)
    ax2.set_xticks(range(sample_n))
    ax2.set_yticks(range(sample_n))
    ax2.set_xticklabels(drug_labels, rotation=45, ha='right')
    ax2.set_yticklabels(drug_labels)

    for i in range(sample_n):
        for j in range(sample_n):
            val = corr_bilinear[i, j]
            txt_color = 'white' if val > 0.65 or val < -0.15 else 'black'
            ax2.text(j, i, f"{val:.2f}", ha='center', va='center', color=txt_color, fontsize=7.5)

    cbar = fig.colorbar(im2, ax=[ax1, ax2], location='right', shrink=0.85, aspect=25, pad=0.03)
    cbar.set_label('Pairwise Spearman Rank Correlation (\u03c1)', rotation=270, labelpad=15)

    out_png = FIG_DIR / 'fig2_ranking_diversity_heatmap.png'
    out_pdf = FIG_DIR / 'fig2_ranking_diversity_heatmap.pdf'
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)
    print(f"Generated Figure 2 -> {out_png}")


if __name__ == '__main__':
    plot_figure_1_screening_performance()
    plot_figure_2_ranking_diversity()
