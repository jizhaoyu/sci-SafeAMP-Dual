# Prespecified computational research protocol

Status: exploratory research design; `protocol-amd-02` is the frozen strict-isolation implementation, but current data preparation is blocked. No confirmed scientific result or clinical use.

## Population and endpoints
The importer includes canonical, linear, unmodified monomeric peptides of 10–50 residues. Terminal modifications, noncanonical residues and covalent cyclization are excluded and logged.

The legacy amp field has a narrow endpoint: measured E. coli MIC <=32 ug/ml is positive, MIC >=128 ug/ml is weak activity (negative at this operational endpoint). This is NOT proof of no antimicrobial activity against other organisms. Hemo denotes measured human-erythrocyte HC50 <=100 ug/ml versus >=250 ug/ml. Intermediate, unsupported, contradictory or missing measurements remain unknown. Source measurements, censoring, medium, organism/cell and publication references are retained. uM is converted only for unmodified molecules using calculated molecular weight. Ranges receive labels only when the entire interval supports the label.

These cutoffs operationalize the pilot and are not universal biological or clinical thresholds. Changed endpoints require a new protocol version. Chemical synthesis followed by a measured experiment is distinct from computationally invented labels; the latter are forbidden.

## Partition and feasibility gates
The historical `legacy-v1` identity uses global Needleman-Wunsch alignment (match +2, mismatch -1, gap -2, diagonal-first ties), normalized by shorter length. The current formal eligibility protocol is [Amendment 02](amendments/PROTOCOL_AMENDMENT_02_ALL_MEMBER.md): the same fixed global alignment uses matches divided by all alignment columns, including gap columns, and every >=40% pair is grouped transitively. Identical molecules are consolidated and source overlap is excluded with reasons. Different source names alone do not establish independence. Amendment 01's representative clustering remains exploratory and does not establish all-member isolation.

Five development folds and a separate holdout are assigned by groups. The external cohort needs a separately documented source and compatible endpoints. Both observed classes must exist for each task in every evaluation and corresponding training partition. Infeasible grouping or cross-set violations block formal experiments. No automatic cutoff relaxation or selective removal to rescue scores.

## Models and evaluation
Fixed seeds: 11, 23, 42. Seven configurations: SVM, RF, gated dual network, concatenation dual network, physicochemical-only dual network, ESM-only dual network and independent single-task gated networks. All use identical partitions. The first run uses fixed hyperparameters declared in configuration for every method (no unreported search). StandardScaler is fitted only on training folds. Networks train 15 epochs and refit on all development samples for held-out inference.

Primary: hemolysis average precision (AUPRC). Secondary: both tasks' AUROC, MCC, sensitivity, specificity, confusion counts, Brier score and calibration bins. Thresholds target specificity >=95% using development out-of-fold predictions, then remain fixed. Achieved test specificity is reported, not guaranteed. Scores are not clinically validated probabilities.

Seed variability is descriptive. Paired differences use matched held-out samples, probabilities averaged across seeds and cluster bootstrap with 2,000 resamples. Invalid single-class resamples are counted. Holm adjustment covers prespecified comparisons; folds are not independent replicates.

## Claims and publication
P(amp)*(1-P(hemo)) is a heuristic ranking score, not a therapeutic index or an established joint probability. Residue coloring describes physicochemical properties, not gradients or causal mechanisms. Mutation suggestions remain exploratory. Author identities, grants, source licenses and journal policies require factual confirmation before submission.


## Calibration, ensemble and provenance clarification
SVC uses probability=False so its internal ungrouped calibration CV is not used. Every model/task fits a logistic calibration map (C=1, clipped logits at 1e-6) on development out-of-fold scores. Final base models refit on the complete development set. Saved development predictions are explicitly oof_selection because the same outcomes fit calibration and choose thresholds; these are not unbiased evaluation estimates.

All three seeds and the mean ensemble are reported. Ensemble thresholds are independently selected from mean development scores and fixed for held-out evaluation. Calibration bins and Brier scores are reported for both calibrated and raw ensemble scores in publication exports. Bootstrap intervals condition on fitted models and do not include retraining uncertainty. Paired permutation tests exchange predictions at the sequence-component level. Folds and seeds are never counted as independent experimental observations.

The identity implementation now uses lexicographic input orientation before diagonal-first traceback tie handling, making sequence_identity(a,b) symmetric. The exact definition is recorded in every new dataset manifest. A different isolation design would be a prospective protocol amendment, not a silent rescue of a blocked analysis.
