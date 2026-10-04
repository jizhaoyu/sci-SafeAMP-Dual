# SafeAMP-Dual Research Remediation Implementation Plan

> **For agentic workers:** Implement with available tools and repository conventions.

**Goal:** Replace unsupported publication outputs with an auditable, fail-closed research workflow.
**Architecture:** Preserve the original assets under `legacy/`; separate provenance-aware datasets, grouped experiments, evaluation artifacts, inference readiness and publication reporting. Unknown labels remain missing.
**Tech Stack:** Existing Python, NumPy, pandas, scikit-learn, SciPy, PyTorch, FastAPI and pytest; real ESM backend required for ESM experiments.

## Global Constraints
- Do not invent experimental labels, results, author identities, funding or evidence.
- Do not publish, push, deploy or submit manuscripts.
- Keep snapshots of affected original assets; no unrelated frontend rewrite.
- Primary isolation cutoff: global alignment matches / shorter sequence length < 0.40 across partitions.
- Five group folds; seeds 11, 23, 42; hemolysis average precision is primary.
- Dataset feasibility or unavailable real embeddings must block formal experiments.

## Implementation checkpoints
- [x] Preserve legacy assets; require canonical input and masked binary labels.
- [x] Add public-source download manifests, record provenance and group isolation checks; primary-source review remains pending.
- [x] Implement seven model configurations, out-of-fold calibration and thresholds, full-development refits and per-sample predictions.
- [x] Replace hardcoded statistics with cluster-bootstrap and paired cluster-permutation analysis of saved predictions.
- [x] Require validated model/embedding provenance at inference; expose actual readiness.
- [x] Implement bounded reports and publication exports; repair bibliography metadata and mark declarations unverified.
- [ ] Run `python -m pytest 02_code/tests 02_code/test_helical_wheel.py -q`, real-data preparation, feasible experiments, API and browser checks.

## Acceptance gates
- Formal experiments and external evaluation are blocked by a single 417-sequence component and no validated external cohort.
- Claim-level citation review and authorship/declarations remain pending factual human verification.
- No new formal performance estimates were generated. LaTeX compilation returned an environment failure (unable to find standard directories for platform); source is preserved.
- No remote deployment, push or submission was performed.

Formal data reject synthetic records and unsupported negative labels. Every scored record links to source evidence and a split. Every comparison uses paired samples. Missing classes, contaminated splits, invalid inputs and absent/mismatched weights produce explicit failures. Manuscript results are emitted only from completed validated runs.
