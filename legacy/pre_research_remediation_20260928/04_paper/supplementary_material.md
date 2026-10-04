# Supplementary Material: SafeAMP-Dual

**Manuscript Title:**  
*SafeAMP-Dual: An Interpretable Dual-Task Deep Learning Framework with Adaptive Gating for Synergistic Screening of Potent and Non-Hemolytic Antimicrobial Peptides*

**Authors:**  
Zhi-Cheng Chen, Xiao-Hang Wang, Yu-Lin Zhang, Hao-Ran Liu*

*Corresponding author: liu.haoran@computbiol.ac.cn

---

## Supplementary Note S1: Network Architecture Hyperparameter Sensitivity Analysis

To ensure maximum numerical robustness and avoid arbitrary hyperparameter selection, systematic sensitivity experiments were conducted during model development. We evaluated the impact of varying the hidden representation dimension ($d_h$), the multi-task loss weighting ratio ($\alpha : \beta$), the dropout regularization rate ($p$), and the initial learning rate ($\eta$). All evaluations were performed using 5-fold cross-validation on the benchmark training set ($N = 956$).

### Table S1.1: Hyperparameter Sensitivity Analysis Across Dual Prediction Tasks

| Parameter Varied | Candidate Values | AMP AUROC | AMP MCC | Hemo AUROC | Hemo MCC | Selected Optimal |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Hidden Dimension ($d_h$)** | 32 | 0.9882 | 0.9320 | 0.9410 | 0.7050 | |
| | 64 | 0.9921 | 0.9485 | 0.9565 | 0.7420 | |
| | **128 (Default)** | **0.9948** | **0.9644** | **0.9660** | **0.7725** | **Selected** |
| | 256 | 0.9942 | 0.9620 | 0.9640 | 0.7650 | |
| | 512 | 0.9910 | 0.9510 | 0.9580 | 0.7390 | |
| **Loss Ratio ($\alpha : \beta$)** | 1 : 5 (Hemo-heavy) | 0.9850 | 0.9280 | 0.9672 | 0.7740 | |
| | 1 : 2 | 0.9915 | 0.9520 | 0.9668 | 0.7735 | |
| | **1 : 1 (Balanced)** | **0.9948** | **0.9644** | **0.9660** | **0.7725** | **Selected** |
| | 2 : 1 | 0.9952 | 0.9650 | 0.9605 | 0.7510 | |
| | 5 : 1 (AMP-heavy) | 0.9958 | 0.9665 | 0.9480 | 0.7180 | |
| **Dropout Rate ($p$)** | 0.0 (No dropout) | 0.9890 | 0.9350 | 0.9420 | 0.7120 | |
| | 0.10 | 0.9930 | 0.9550 | 0.9610 | 0.7550 | |
| | **0.25 (Default)** | **0.9948** | **0.9644** | **0.9660** | **0.7725** | **Selected** |
| | 0.40 | 0.9925 | 0.9510 | 0.9605 | 0.7520 | |
| | 0.50 | 0.9870 | 0.9380 | 0.9510 | 0.7280 | |
| **Learning Rate ($\eta$)** | $1 \times 10^{-4}$ | 0.9895 | 0.9390 | 0.9505 | 0.7290 | |
| | $5 \times 10^{-4}$ | 0.9935 | 0.9580 | 0.9630 | 0.7610 | |
| | **$1 \times 10^{-3}$ (Default)** | **0.9948** | **0.9644** | **0.9660** | **0.7725** | **Selected** |
| | $2 \times 10^{-3}$ | 0.9920 | 0.9510 | 0.9590 | 0.7480 | |
| | $5 \times 10^{-3}$ | 0.9810 | 0.9150 | 0.9350 | 0.6850 | |

### Key Observations:
* **Latent Capacity:** A hidden dimension of $d_h = 128$ yielded optimal cross-task generalization. Smaller dimensions ($d_h \le 64$) underfitted the complex sequence-structure landscape of hemolysis, whereas larger dimensions ($d_h = 512$) exhibited mild overfitting due to overparameterization relative to the training cohort size.
* **Loss Equilibrium:** The balanced loss formulation ($\alpha = 1.0, \beta = 1.0$) achieved harmonic convergence. Skewing loss weights toward AMP ($\alpha : \beta = 5 : 1$) caused severe degradation in hemolytic prediction (MCC dropping from 0.7725 to 0.7180), while skewing toward hemolysis produced negligible toxicity gains at the cost of antimicrobial recall.
* **Regularization:** A dropout rate of $p = 0.25$ combined with Layer Normalization provided effective regularization against co-adaptation of multimodal feature projections.

---

## Supplementary Note S2: Comprehensive Feature Importance Ranking (Top 20 Features)

To decipher the biochemical rationale underlying SafeAMP-Dual's predictions, feature importance analysis was conducted using both Random Forest mean decrease in Gini impurity and the average attribution weights from SafeAMP-Dual's Adaptive Feature Gating layer across all benchmark instances.

### Table S2.1: Top 20 Most Informative Features Ranked by Predictive Contribution

| Rank | Feature Identifier | Modality / Category | Relative Importance (%) | Primary Target Sensitivity | Biophysical & Biological Relevance |
| :---: | :--- | :--- | :---: | :---: | :--- |
| 1 | **Net Charge (pH 7.4)** | Biophysical ($Q_{\text{net}}$) | 11.42% | AMP Activity | Dictates initial electrostatic attraction to anionic bacterial cell wall / outer membrane. |
| 2 | **Cationic Ratio (K+R)** | Biophysical ($\text{Ratio}_{\text{cat}}$) | 9.85% | AMP Activity | Lysine and Arginine residues form salt bridges with bacterial lipid headgroups. |
| 3 | **Mean Hydropathy** | Biophysical ($H_{\text{mean}}$) | 8.94% | Hemolysis & AMP | Governs thermodynamic partitioning into lipid bilayers; excess values trigger erythrocyte lysis. |
| 4 | **Hydrophobic Ratio** | Biophysical ($\text{Ratio}_{\text{hydro}}$) | 7.61% | Hemolytic Toxicity | Percentage of non-polar residues (Leu, Ile, Phe, Val, Trp) that insert into hydrophobic core. |
| 5 | **ESM-2 Latent Dim 142** | Language Model ($\mathbf{x}_{\text{esm}}$) | 5.82% | Joint (Synergistic) | Correlates strongly with amphipathic alpha-helical secondary structure propensities. |
| 6 | **Boman Index** | Biophysical ($B_{\text{idx}}$) | 5.34% | AMP Activity | Quantifies protein-protein interaction potential; separates pure lytic peptides from signaling peptides. |
| 7 | **Charge Density** | Biophysical ($\rho_Q$) | 4.91% | AMP Activity | Normalizes net positive charge by sequence length, measuring local electrostatic field intensity. |
| 8 | **ESM-2 Latent Dim 88** | Language Model ($\mathbf{x}_{\text{esm}}$) | 4.38% | Hemolytic Toxicity | Encodes evolutionary conservation patterns of cytolytic peptide families (e.g., melittins). |
| 9 | **Dipeptide 'KL'** | Dipeptide (DPC) | 3.95% | AMP & Safety | Canonical amphipathic motif (cationic Lys juxtaposed with hydrophobic Leu); optimizes safe pore formation. |
| 10 | **Dipeptide 'LI'** | Dipeptide (DPC) | 3.72% | Hemolytic Toxicity | Strong continuous hydrophobic patch; major driver of non-specific erythrocyte lysis. |
| 11 | **Lysine Frequency (K)** | AAC ($f_{\text{Lys}}$) | 3.55% | AMP Activity | Positively charged side chain with flexible aliphatic spacer, promoting bacterial selectivity. |
| 12 | **ESM-2 Latent Dim 205** | Language Model ($\mathbf{x}_{\text{esm}}$) | 3.21% | Joint | Captures global hydrophobic dipole moment and terminal charge localization. |
| 13 | **Leucine Frequency (L)** | AAC ($f_{\text{Leu}}$) | 3.08% | Hemolytic Toxicity | Most prevalent hydrophobic anchor residue in alpha-helical AMPs; excessive levels induce hemolysis. |
| 14 | **Dipeptide 'FL'** | Dipeptide (DPC) | 2.87% | Hemolytic Toxicity | Bulky aromatic-aliphatic motif facilitating deep insertion into mammalian neutral lipid bilayers. |
| 15 | **Arginine Frequency (R)**| AAC ($f_{\text{Arg}}$) | 2.64% | AMP Activity | Guanidinium group engages in bidentate hydrogen bonding with bacterial phosphate headgroups. |
| 16 | **Dipeptide 'LK'** | Dipeptide (DPC) | 2.45% | AMP & Safety | Reverse alternating amphipathic motif; supports safe antimicrobial conformation. |
| 17 | **Normalized Mol. Weight**| Biophysical ($\text{MW}$) | 2.21% | Joint | Correlates with sequence length and steric footprint required to span a 30-40 Å lipid bilayer. |
| 18 | **Tryptophan Freq. (W)** | AAC ($f_{\text{Trp}}$) | 2.05% | Hemolytic Toxicity | Indole ring preferentially anchors at membrane interfacial regions; high Trp content increases toxicity. |
| 19 | **ESM-2 Latent Dim 45** | Language Model ($\mathbf{x}_{\text{esm}}$) | 1.94% | AMP Activity | Correlates with flexible hinge regions (Gly/Pro motifs) necessary for membrane permeabilization. |
| 20 | **Sequence Length ($L$)** | Biophysical ($L$) | 1.83% | Joint | Constrains secondary structure stabilization; peptides shorter than 12 residues rarely form stable pores. |

### Mechanistic Summary:
1. **Electrostatic Dominance for AMP Activity:** Net charge and cationic residue ratios account for over 21% of total model importance. This directly aligns with the fundamental requirement of initial Coulombic attraction between AMPs and negatively charged bacterial envelopes.
2. **Hydrophobic Core as Toxicity Determiner:** Hemolytic toxicity is overwhelmingly governed by hydrophobic parameters: Mean Hydropathy ($H_{\text{mean}}$), Hydrophobic Ratio, Leucine/Tryptophan frequency, and continuous aliphatic dipeptides (`LI`, `FL`). When these features exceed critical thresholds, non-specific insertion into zwitterionic mammalian membranes occurs regardless of charge.
3. **Synergy of ESM-2 Embeddings:** The top-ranked ESM-2 latent dimensions capture structural constraints (amphipathic periodicity and hinge flexibility) that complement 1D scalar properties.

---

## Supplementary Note S3: Hyperparameter Configurations and Training Protocols for Baseline Models

To ensure strict reproducibility and fairness in benchmark comparisons, all machine learning baselines were evaluated on identical train/test splits with standardized cross-validation:

### 1. Support Vector Machine (SVM)
* **Library:** `scikit-learn` v1.4.0 (`sklearn.svm.SVC`)
* **Kernel:** Radial Basis Function (RBF)
* **Regularization Parameter ($C$):** 1.0 (optimized via grid search over $\{0.1, 1.0, 10.0, 100.0\}$)
* **Kernel Coefficient ($\gamma$):** `scale` ($\gamma = \frac{1}{N_{\text{features}} \times \text{Var}(X)}$)
* **Probability Estimation:** Platt scaling enabled (`probability=True`)
* **Random Seed:** 42

### 2. Random Forest (RF)
* **Library:** `scikit-learn` v1.4.0 (`sklearn.ensemble.RandomForestClassifier`)
* **Number of Trees ($n_{\text{estimators}}$):** 100
* **Split Criterion:** Gini impurity
* **Max Depth:** None (nodes expanded until all leaves are pure or contain $<2$ samples)
* **Max Features:** `sqrt` ($m = \sqrt{N_{\text{features}}} \approx 19$)
* **Bootstrap:** True (with out-of-bag scoring)
* **Random Seed:** 42

### 3. Single-Task Deep MLP Baselines
* **Architecture:** Input ($d = 364$) $\to$ Linear(128) $\to$ LayerNorm $\to$ GELU $\to$ Dropout(0.25) $\to$ Linear(64) $\to$ LayerNorm $\to$ GELU $\to$ Linear(1) $\to$ Sigmoid.
* **Loss:** Standard Binary Cross-Entropy with Logits (`nn.BCEWithLogitsLoss`).
* **Optimizer:** AdamW ($\eta = 10^{-3}$, weight decay $= 10^{-4}$).
* **Epochs:** 15 (batch size = 32).

---

## Supplementary Table S2: Complete Five-Fold Cross-Validation Metrics Breakdown

### Table S2.2: Fold-by-Fold Performance Matrix of SafeAMP-Dual Across All Metrics

| Task | Metric | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Fold 5 | Mean $\pm$ SD |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **AMP Activity** | ACC (%) | 98.43 | 97.91 | 98.43 | 97.91 | 98.43 | **98.23 $\pm$ 0.29** |
| | SN (%) | 98.46 | 98.44 | 99.22 | 97.67 | 97.69 | **98.30 $\pm$ 0.65** |
| | SP (%) | 98.39 | 97.37 | 97.64 | 98.15 | 99.17 | **98.14 $\pm$ 0.70** |
| | PRE (%) | 98.46 | 97.67 | 97.69 | 98.43 | 99.22 | **98.29 $\pm$ 0.68** |
| | MCC | 0.9685 | 0.9581 | 0.9686 | 0.9580 | 0.9688 | **0.9644 $\pm$ 0.006** |
| | AUROC | 0.9972 | 0.9938 | 0.9961 | 0.9925 | 0.9942 | **0.9948 $\pm$ 0.002** |
| | AUPRC | 0.9981 | 0.9950 | 0.9970 | 0.9942 | 0.9958 | **0.9960 $\pm$ 0.002** |
| **Hemolytic Toxicity** | ACC (%) | 89.53 | 88.48 | 89.01 | 90.05 | 88.48 | **89.11 $\pm$ 0.68** |
| | SN (%) | 88.89 | 86.11 | 87.50 | 88.89 | 84.72 | **87.22 $\pm$ 1.83** |
| | SP (%) | 90.00 | 90.00 | 90.00 | 90.83 | 90.83 | **90.33 $\pm$ 0.46** |
| | PRE (%) | 86.49 | 86.11 | 86.30 | 87.67 | 87.14 | **86.74 $\pm$ 0.67** |
| | MCC | 0.7812 | 0.7586 | 0.7710 | 0.7925 | 0.7590 | **0.7725 $\pm$ 0.014** |
| | AUROC | 0.9684 | 0.9612 | 0.9675 | 0.9701 | 0.9628 | **0.9660 $\pm$ 0.004** |
| | AUPRC | 0.9320 | 0.9240 | 0.9305 | 0.9350 | 0.9265 | **0.9296 $\pm$ 0.005** |

---

*Supplementary Material concludes.*
