"""Scientific Figure Exporter for Supplementary Materials and Publications.

Generates publication-quality figures (SVG vector, PDF vector, high-res PNG)
alongside underlying CSV data tables to ensure 100% auditability and reproducibility.
Uses matplotlib Agg headless backend.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # Ensure headless operation
import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)

# Nature / Science styled colors and styling params
COLOR_PRIMARY = "#3b82f6"     # Sky blue
COLOR_SECONDARY = "#6366f1"   # Indigo
COLOR_SUCCESS = "#10b981"     # Emerald
COLOR_WARNING = "#f59e0b"     # Amber
COLOR_MUTED = "#64748b"       # Slate
COLOR_GRID = "#e2e8f0"        # Slate-200


def _setup_figure_style():
    """Apply clean scientific plotting style."""
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica", "sans-serif"]
    plt.rcParams["axes.edgecolor"] = "#94a3b8"
    plt.rcParams["axes.linewidth"] = 0.8
    plt.rcParams["xtick.color"] = "#475569"
    plt.rcParams["ytick.color"] = "#475569"
    plt.rcParams["xtick.labelsize"] = 9
    plt.rcParams["ytick.labelsize"] = 9
    plt.rcParams["axes.labelsize"] = 10
    plt.rcParams["axes.titlesize"] = 11


def export_affinity_distribution(
    predictions_or_scores: List[float],
    baseline_pkd: Optional[float] = None,
    output_dir: Optional[Path] = None,
    target_name: str = "Target Kinase",
    filename_prefix: str = "fig1_affinity_distribution"
) -> Dict[str, str]:
    """Export pKd distribution histogram & KDE curve with baseline benchmark line.
    
    Generates:
      - {filename_prefix}.svg
      - {filename_prefix}.pdf
      - {filename_prefix}_data.csv
    """
    _setup_figure_style()
    out_dir = Path(output_dir or ".")
    out_dir.mkdir(parents=True, exist_ok=True)

    scores = [float(s) for s in predictions_or_scores if s is not None and not np.isnan(s)]
    if not scores:
        raise ValueError("No affinity observations were supplied")

    # 1. Save underlying CSV data
    data_csv_path = out_dir / f"{filename_prefix}_data.csv"
    with open(data_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Index", "Target_Name", "Predicted_pKd", "Estimated_Kd_nM"])
        for idx, s in enumerate(scores):
            kd_nm = 10 ** (9.0 - s)
            writer.writerow([idx + 1, target_name, round(s, 4), round(kd_nm, 2)])

    # 2. Render plot
    fig, ax = plt.subplots(figsize=(6.5, 4.2), dpi=300)
    bins = np.linspace(min(min(scores), 4.0), max(max(scores), 10.0), 25)
    counts, _, patches = ax.hist(scores, bins=bins, color=COLOR_PRIMARY, alpha=0.75, edgecolor="#1e40af", linewidth=0.6, label="Screened Profiles")

    # Baseline line if available
    if baseline_pkd is not None and baseline_pkd > 0:
        ax.axvline(baseline_pkd, color="#dc2626", linestyle="--", linewidth=1.5, label=f"Baseline Lead ({baseline_pkd:.2f} pKd)")

    # Affinity tier boundaries
    ax.axvline(7.0, color="#10b981", linestyle=":", alpha=0.7, label="High Affinity (pKd ≥ 7)")
    ax.axvline(6.0, color="#f59e0b", linestyle=":", alpha=0.7, label="Moderate Affinity (pKd ≥ 6)")

    ax.set_xlabel("Predicted Binding Affinity (pKd = -log10 Kd)", fontsize=10, labelpad=8)
    ax.set_ylabel("Candidate Count / Frequency", fontsize=10, labelpad=8)
    ax.set_title(f"Affinity Distribution for {target_name} Screen", fontsize=11, fontweight="bold", pad=12)
    ax.grid(True, linestyle="--", alpha=0.4, color=COLOR_GRID)
    ax.legend(frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=8.5, loc="upper right")

    plt.tight_layout()

    svg_path = out_dir / f"{filename_prefix}.svg"
    pdf_path = out_dir / f"{filename_prefix}.pdf"
    png_path = out_dir / f"{filename_prefix}.png"

    fig.savefig(svg_path, format="svg", bbox_inches="tight")
    fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
    fig.savefig(png_path, format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    return {
        "svg": str(svg_path),
        "pdf": str(pdf_path),
        "png": str(png_path),
        "data_csv": str(data_csv_path)
    }


def export_screening_funnel(
    funnel_stages: List[Dict[str, Any]],
    output_dir: Optional[Path] = None,
    filename_prefix: str = "fig2_screening_funnel"
) -> Dict[str, str]:
    """Export horizontal bar chart representing multi-stage compound funnel.
    
    Generates:
      - {filename_prefix}.svg
      - {filename_prefix}.pdf
      - {filename_prefix}_data.csv
    """
    _setup_figure_style()
    out_dir = Path(output_dir or ".")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not funnel_stages:
        raise ValueError("No observed screening stages were supplied")

    labels = [s.get("stage", f"Stage {i+1}") for i, s in enumerate(funnel_stages)]
    counts = [int(s.get("count", 0)) for s in funnel_stages]

    # 1. Save data CSV
    data_csv_path = out_dir / f"{filename_prefix}_data.csv"
    with open(data_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Stage_Order", "Stage_Name", "Remaining_Count", "Retention_Pct"])
        initial = max(counts[0], 1)
        for idx, (lbl, cnt) in enumerate(zip(labels, counts)):
            pct = round((cnt / initial) * 100, 2)
            writer.writerow([idx + 1, lbl, cnt, pct])

    # 2. Render plot
    fig, ax = plt.subplots(figsize=(6.8, 3.8), dpi=300)
    y_pos = np.arange(len(labels))
    colors = [COLOR_PRIMARY, COLOR_SECONDARY, "#06b6d4", COLOR_SUCCESS][:len(labels)]
    if len(colors) < len(labels):
        colors = [COLOR_PRIMARY] * len(labels)

    bars = ax.barh(y_pos, counts, color=colors, alpha=0.85, edgecolor="#334155", linewidth=0.6, height=0.55)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9.5)
    ax.invert_yaxis()  # Highest at top
    ax.set_xlabel("Number of Candidate Compounds", fontsize=10, labelpad=8)
    ax.set_title("Hierarchical Molecular Screening Funnel", fontsize=11, fontweight="bold", pad=12)
    ax.grid(True, axis="x", linestyle="--", alpha=0.4, color=COLOR_GRID)

    # Label counts at end of bars
    max_c = max(counts) if counts else 100
    for bar in bars:
        width = bar.get_width()
        ax.text(width + (max_c * 0.02), bar.get_y() + bar.get_height()/2, f"{int(width):,}",
                va="center", ha="left", fontsize=9, fontweight="bold", color="#1e293b")

    plt.tight_layout()

    svg_path = out_dir / f"{filename_prefix}.svg"
    pdf_path = out_dir / f"{filename_prefix}.pdf"
    png_path = out_dir / f"{filename_prefix}.png"

    fig.savefig(svg_path, format="svg", bbox_inches="tight")
    fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
    fig.savefig(png_path, format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    return {
        "svg": str(svg_path),
        "pdf": str(pdf_path),
        "png": str(png_path),
        "data_csv": str(data_csv_path)
    }


def export_candidate_sar_comparison(
    candidates: List[Dict[str, Any]],
    baseline_pkd: Optional[float] = None,
    output_dir: Optional[Path] = None,
    filename_prefix: str = "fig3_sar_comparison"
) -> Dict[str, str]:
    """Export SAR delta-pKd comparison bar chart showing scaffold retention vs hopping.
    
    Generates:
      - {filename_prefix}.svg
      - {filename_prefix}.pdf
      - {filename_prefix}_data.csv
    """
    _setup_figure_style()
    out_dir = Path(output_dir or ".")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not candidates:
        raise ValueError("No SAR observations were supplied")

    cands_to_plot = candidates[:10]  # Plot top 10
    names = [c.get("name", f"Cand-{i+1}") for i, c in enumerate(cands_to_plot)]
    deltas = []
    for candidate in cands_to_plot:
        delta = candidate.get("delta_pkd")
        if delta is None or delta == "":
            if baseline_pkd is None or candidate.get("predicted_pkd") is None:
                raise ValueError("A reported affinity delta or baseline is required for SAR plotting")
            delta = float(candidate["predicted_pkd"]) - float(baseline_pkd)
        if not np.isfinite(float(delta)):
            raise ValueError("SAR affinity deltas must be finite")
        deltas.append(float(delta))
    scaffold_types = [c.get("scaffold_type", "") for c in cands_to_plot]

    # 1. Save data CSV
    data_csv_path = out_dir / f"{filename_prefix}_data.csv"
    with open(data_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Rank", "Candidate_Name", "Predicted_pKd", "Delta_pKd", "Scaffold_Type", "Source"])
        for idx, c in enumerate(cands_to_plot):
            pkd = c.get("predicted_pkd")
            if pkd is None and baseline_pkd is not None:
                pkd = float(baseline_pkd) + deltas[idx]
            writer.writerow([idx + 1, names[idx], round(float(pkd), 3) if pkd is not None else "", round(deltas[idx], 3), scaffold_types[idx], c.get("source", "")])

    # 2. Render plot
    fig, ax = plt.subplots(figsize=(7.2, 4.0), dpi=300)
    x_pos = np.arange(len(names))
    bar_colors = [COLOR_WARNING if st == "scaffold_hopping" else COLOR_SUCCESS if d > 0 else COLOR_MUTED for st, d in zip(scaffold_types, deltas)]

    bars = ax.bar(x_pos, deltas, color=bar_colors, alpha=0.85, edgecolor="#1e293b", linewidth=0.6, width=0.55)
    ax.axhline(0, color="#475569", linewidth=0.8)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(names, rotation=35, ha="right", fontsize=8.5)
    ax.set_ylabel("ΔpKd relative to Lead Baseline", fontsize=10, labelpad=8)
    ax.set_title("Structure-Activity Relationship (SAR) Affinity Gain", fontsize=11, fontweight="bold", pad=12)
    ax.grid(True, axis="y", linestyle="--", alpha=0.4, color=COLOR_GRID)

    # Custom legend
    import matplotlib.patches as mpatches
    patch_gain = mpatches.Patch(color=COLOR_SUCCESS, label="Reported Affinity Gain")
    patch_hop = mpatches.Patch(color=COLOR_WARNING, label="Scaffold Hopping")
    ax.legend(handles=[patch_gain, patch_hop], fontsize=8.5, loc="upper right", frameon=True)

    plt.tight_layout()

    svg_path = out_dir / f"{filename_prefix}.svg"
    pdf_path = out_dir / f"{filename_prefix}.pdf"
    png_path = out_dir / f"{filename_prefix}.png"

    fig.savefig(svg_path, format="svg", bbox_inches="tight")
    fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
    fig.savefig(png_path, format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    return {
        "svg": str(svg_path),
        "pdf": str(pdf_path),
        "png": str(png_path),
        "data_csv": str(data_csv_path)
    }
