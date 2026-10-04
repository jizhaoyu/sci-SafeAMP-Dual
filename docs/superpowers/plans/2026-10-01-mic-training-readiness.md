# MIC-only Training Readiness Implementation Plan

> 2026-10-02 02:29 UTC 更新：最新状态见 `03_experiments/audits/mic_training_readiness_20261002_v4.json`。局部原论文核查已扩展，但新候选仅有 4 个含阴性的独立组件，五折仍失败。旧训练就绪状态 v1 已撤回；训练入口继续拒绝旧队列。下面的已完成勾选仅记录当时实施步骤，不代表当前科学门禁通过。

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a versioned MIC-only cohort and frozen training input that satisfy the existing evidence, homology, study-source, and five-fold gates without changing the 0.40 cutoff or deriving labels from missing data.

**Architecture:** Curate an evidence-qualified subset by removing entire records with unresolved target identifiers, retaining original raw paths and hashes. Re-run the frozen MIC-only all-member audit, then freeze a new study-disjoint audit and training protocol only if every required gate passes. Historical audit directories and formal dual-task status remain untouched.

**Tech Stack:** Python 3.11, pandas, scikit-learn, existing `research_data.py` and `audit_mic_only_cohort.py`.

## Global Constraints

- `protocol-mic-01` stays unchanged: 10–50 canonical residues, linear unmodified molecules, MIC positive `<=32 µg/mL`, negative `>=128 µg/mL`, 0.40 all-member global alignment identity, five folds with both classes.
- Unresolved strain or isolate observations cause record exclusion; no guessed strain, assay value, chemistry, or label.
- Group related sequences and shared primary MIC papers in the same validation fold; no seed search or threshold tuning.
- New outputs use unused versioned paths; existing audits, runs, and `04_paper/research_status.json` remain historical or formally blocked.
- This request is for training readiness. No model fit, metric export, or formal study release is part of this plan.

---

### Task 1: Curate evidence-qualified MIC records

**Files:** Create `02_code/curate_mic_training_source.py`; create a new `03_experiments/audits/mic_training_source_20261001_v1/` output; modify `02_code/audit_mic_only_cohort.py` only if its fixed input label becomes misleading.

**Interfaces:** Consume source `records.csv` and v7 `target_identifier_audit.csv`; produce `records.csv`, `exclusions.csv`, and `manifest.json` with input and script SHA-256 values.

- [x] Read every labeled development record and all of its MIC target audit rows. Preserve a record only when it has a binary MIC label and no `unresolved_strain_or_isolate` row; preserve the source field values and raw provenance columns.
- [x] Write each excluded record ID and a concrete reason (`no_binary_mic_label` or `unresolved_target_identifier`) to a versioned exclusion table. Reject source/audit ID mismatches and duplicate record IDs.
- [x] Run the curator once to a new directory; inspect positive and negative counts and confirm no excluded ID appears in the output.

### Task 2: Rebuild homology and study-disjoint audits

**Files:** Create a new MIC audit directory; create `03_experiments/protocols/protocol-mic-study-03.json`; modify `02_code/audit_mic_study_disjoint.py` to recognize the new frozen protocol and the active parent audit.

**Interfaces:** Consume Task 1 source plus `dramp_verified_ecoli_mic_20261001_v8/records.csv`; produce immutable all-member and study-disjoint manifests and fold tables.

- [x] Run `audit_mic_only_cohort.py` with unchanged `protocol-mic-01`; inspect target, label, exact-duplicate, all-member, and five-fold gates.
- [x] If any gate fails, keep `blocked` and do not create a training protocol. If it passes, freeze `protocol-mic-study-03` with the new cohort manifest, 0.40 all-member components, primary-study aliases, and seed 42.
- [x] Run `audit_mic_study_disjoint.py` once into a new directory. Confirm no shared homology component, primary paper, or >=0.40 pair crosses folds, and that each train and validation partition has both labels.

### Task 3: Make the training entry point accept only the new frozen input

**Files:** Create `03_experiments/protocols/protocol-mic-05.json`; modify `02_code/train_mic_baselines.py`; update `README.md`, `docs/REMEDIATION_STATUS.md`, and `03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md`.

**Interfaces:** The training loader accepts the exact new cohort manifest and fold table only when the current evidence and study-disjoint manifests pass; the protocol fixes existing features, three baseline models, parameters, and metrics.

- [x] Freeze a new training protocol with explicit cohort, study-disjoint audit, and fold hashes. Do not repoint or modify `protocol-mic-04`.
- [x] Remove hard-coded historical molecule count from the training loader; derive it from the approved manifest while checking one validation assignment per unique sequence and full fold coverage.
- [x] Require the current evidence and study-disjoint statuses to be `feasible_for_training_review`, verify file hashes, and refuse old/superseded inputs.
- [x] Update status documents with actual timestamps, paths, protocol IDs, counts, and limits. The initial MIC-only `training_ready` decision was later withdrawn after the primary-study evidence gap was identified; both research tracks currently remain `blocked`.

## Completion check

The new manifests must provide the actual status and provenance. If any gate fails, leave the project blocked and record the exact blocker; no training is authorized by a partial audit.
