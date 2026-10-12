# Ablation Study: Resolving Ranking Degeneracy via Bilinear ESM-2 Latent Interaction

## 1. The Mathematical Origin of Ranking Degeneracy in Additive Models

A pervasive but rarely diagnosed failure mode in molecular affinity learning arises from purely additive model structures:
$$f(d, t) = w_d^T d + w_t^T t + b$$
When evaluating a fixed candidate kinase library $\mathcal{T} = \{t_1, t_2, \dots, t_M\}$ for any arbitrary small molecule $d_i$, the drug term $w_d^T d_i$ acts solely as a uniform scalar shift across all candidates:
$$\text{rank}_{t \in \mathcal{T}} \left(f(d_i, t)\right) = \text{rank}_{t \in \mathcal{T}} \left(w_t^T t\right)$$
Consequently, for any pair of distinct small molecules $d_i \neq d_j$, the predicted relative order of kinase targets is mathematically identical, yielding an empirical cross-drug Spearman rank correlation $\rho \equiv 1.000$. This ranking degeneracy severely undermines real-world virtual screening and drug repositioning, because the model cannot distinguish between drug-specific polypharmacology profiles and simply recommends the same "globally promiscuous" kinases to every lead compound.

Under rigorous 4-fold entity-isolated cross-validation (dual-cold regime), additive linear models (including Gaussian left-censored Tobit regression) collapsed to a Top-10 precision of $P@10 = 0.0417$, falling substantially below the constant uninformative expectation ($P@10 = 0.0970$).

---

## 2. Architecture of the Bilinear Interaction DTI Network

To resolve this degeneracy while preserving computational tractability on standard single-GPU workstations, we introduce `BilinearInteractionDTI`:
1. **Drug Latent Projection**: The 2,048-dimensional Morgan circular fingerprint is mapped into a normalized latent space:
   $$h_d = \text{LayerNorm}\left(\text{ReLU}\left(W_d d + b_d\right)\right) \in \mathbb{R}^{128}$$
2. **Kinase ESM-2 Latent Projection**: The 480-dimensional pre-computed protein sequence representation from the 12th layer of ESM-2 (`esm2_t12_35M_UR50D`) is projected into the identical latent dimension:
   $$h_t = \text{LayerNorm}\left(\text{ReLU}\left(W_t t + b_t\right)\right) \in \mathbb{R}^{128}$$
3. **Bilinear Interaction Core & Residual Skip**:
   $$\hat{y}(d, t) = v^T (h_d \odot h_t) + w_{\text{res}, d}^T d + w_{\text{res}, t}^T t + b_0$$
   where $\odot$ denotes the element-wise Hadamard product, capturing explicit second-order cross-feature interactions between chemical substructures and protein evolutionary motifs.
4. **Candidate Screening Objective**: The network is trained with binary cross-entropy loss against strict strong-binding efficacy labels ($pK_d \ge 7.0$), prioritizing high-confidence lead candidate identification.

---

## 3. Quantitative Ablation & Screening Benchmark

We benchmarked `BilinearInteractionDTI` against established baselines across 4 disjoint entity-isolated folds (15,704 training pairs, zero overlap between train and validation drug/target sets):

| Model Architecture | Input Features | Objective / Loss | Dual-Cold P@10 | Cold-Drug P@10 | Mean Ranking Spearman ($\rho$) | Degeneracy Status |
|---|---|---|---|---|---|---|
| **Constant Expectation** | None | Null Prior | 0.0970 | 0.0970 | 0.0000 | Null baseline |
| **Additive Linear Tobit** | 2076-d (Morgan + 28-d Handcrafted) | Censored Normal NLL | 0.0417 | 0.1154 | **1.0000** | Degenerate (Rank collapsed) |
| **Additive HGB Regressor** | 2076-d (Morgan + 28-d Handcrafted) | Continuous MSE | 0.1019 ± 0.0157 | 0.3000 ± 0.0350 | 0.7820 | Tree non-linearity partially relaxes rank |
| **Additive LogReg Classifier** | 2076-d (Morgan + 28-d Handcrafted) | Binary Log-loss ($pK_d \ge 7$) | 0.1038 ± 0.0310 | 0.1385 ± 0.0280 | **1.0000** | Degenerate (Binary label fails to fix rank) |
| **Bilinear Interaction + ESM-2 (Ours)** | **2048-d Morgan + 480-d ESM-2** | **Bilinear Head + BCE** | **0.1615 ± 0.0243** | **0.2885 ± 0.0886** | **0.1003** | **Resolved (True drug-specific ranking)** |

### Key Experimental Insights:
1. **Breakthrough in Dual-Cold Generalization**:
   As depicted in **Figure 1(a)**, our bilinear architecture achieves $P@10 = 0.1615 \pm 0.0243$, surpassing the pre-registered breakthrough threshold ($P@10 \ge 0.1500$) and outperforming the additive Tobit baseline by **3.87-fold** (+66.5% relative gain over random baseline).
2. **Complete Resolution of Ranking Degeneracy**:
   As illustrated in **Figure 2**, pairwise Spearman rank correlation among validation lead inhibitors drops from $\rho \equiv 1.000$ in additive models to $\rho = 0.1003$ in our bilinear network. This confirms that the model successfully predicts distinct, scaffold-specific kinase inhibition profiles.
3. **Ultra-lightweight Compute Footprint**:
   The entire model comprises approximately 350,000 parameters. Training converges in under 30 seconds across 4 folds on an NVIDIA Tesla T4 GPU (batch size 256, peak VRAM < 10 MB), providing an accessible, reproducible blueprint for academic and clinical research.
