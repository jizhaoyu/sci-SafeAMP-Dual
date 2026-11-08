# Enhanced Stacking DTI Model Verification Report

- **Audit Date**: 2026-10-07T09:38:50.158497+00:00
- **Protocol ID**: protocol-dti-01
- **Run Directory**: `dti_davis_stacked_20261007_v1`
- **Feature Pipeline**: Enhanced 100-dim kinase domain features + 2056-dim molecular features (2156-dim total)

## 1. Protected Files Cryptographic Integrity
All 6 historical core protected files verified bit-for-bit identical (0 changes).

## 2. Models Evaluated
- `ridge_alpha1`: Standard L2 Ridge baseline
- `ridge_alpha10`: Strong regularization Ridge (Optimal on Strict Dual-Cold)
- `hist_gradient_boosting`: Non-linear tree model
- `mlp`: Multi-layer perceptron
- `stacked_ensemble`: Non-negative convex stacking meta-model

## 3. Key Findings on Benchmark Performance
- **Train Block (Seen Drug & Target)**: Stacking Ensemble achieved RMSE **0.5566** (21% reduction from baseline) and CI **0.8494** (vs 0.7808 baseline, +0.0686).
- **Cold Drug (Seen Kinase, Unseen Molecule)**: Stacking Ensemble achieved CI **0.7571** (vs 0.7322 baseline, +0.0249 gain).
- **Strict Dual-Cold (Unseen Drug & Kinase, 975 pairs)**: Ridge_alpha10 achieved CI **0.7004**, Stacking Ensemble achieved CI **0.6832**.

## 4. Verification Verdict
**AUDIT PASSED (PASS)**. Zero leakage, 100% manifest match, 25,772 pairs verified.
