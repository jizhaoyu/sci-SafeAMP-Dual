# DTI T4 Bilinear Interaction Training Results

- **Run Timestamp**: 2026-10-12T18:49:58
- **Device**: Tesla T4 (cuda)
- **Epochs per Fold**: 25 | **Batch Size**: 256

## Key Screening Metrics Summary
| Metric | Value | Reference / Notes |
|---|---|---|
| **Dual-Cold P@10** | **0.1615 +/- 0.0243** | Primary candidate screening accuracy |
| **Cold-Drug P@10** | 0.2885 | Single-entity cold drug scenario |
| **Cold-Target P@10** | 0.1981 | Single-entity cold target scenario |
| **Dual-Cold AP** | 0.2846 | Macro AP across eligible drugs |
| **Ranking Diversity (Spearman)** | **0.1003** | <0.85 confirms drug-specific ranking |
| **Ranking Degeneracy Broken** | **True** | Breaks linear additive identical rank bug |

## Decision Gate
- **Breakthrough Gate (P@10 >= 0.1500)**: MET
- **Diversity Gate (Spearman < 0.85)**: MET
