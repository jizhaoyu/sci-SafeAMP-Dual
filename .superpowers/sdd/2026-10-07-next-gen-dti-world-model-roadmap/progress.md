# SDD ledger — plan: docs/superpowers/plans/2026-10-07-next-gen-dti-world-model-roadmap.md

Pre-flight: Phase 1 tasks defined and executed.

- [x] Task 1.1: Uni-Mol / 3D 构象小分子特征提取器 (`02_code/extract_unimol_features.py`)
  - Commit: `1fa0e02`
  - Tests: `02_code/tests/test_unimol_features.py` (3/3 PASSED)
- [x] Task 1.2: ESM-2 激酶催化中心上下文表征管道 (`02_code/extract_esm_kinase_features.py`)
  - Commit: `db48c13`
  - Tests: `02_code/tests/test_esm_kinase_features.py` (3/3 PASSED)
- [x] Task 1.2b: 统一 2988 维生物世界模型交互表征流水线 (`02_code/extract_worldmodel_features.py`)
  - Commit: `c9d9dd7`
  - Tests: `02_code/tests/test_worldmodel_features.py` (1/1 PASSED)
- [x] Task 1.3: 基础大模型特征融合与 DAVIS 基准复训及运行时接入 (`02_code/train_dti_davis_worldmodel_v1.py` & `02_code/dti_inference_runtime.py`)
  - Commit: `739e6e5`
  - Training metrics:
    - Train block CI: 0.8652, RMSE: 0.5109, MAE: 0.3120 (误差较基线大幅压缩)
    - Cold target CI: 0.7447 (较前代 0.7289 提升)
    - Cold drug Ridge-10 CI: 0.7619 (较前代 0.7504 提升)
    - Dual cold Ridge-50 CI: 0.6999 (较前代提升并接近 0.70)
  - Tests: `02_code/tests/test_dti_worldmodel_runtime.py` (1/1 PASSED)
  - Regression: 13/13 DTI tests PASSED, check_mic_project exit 0, npm run lint/build 0 errors.

- [x] Task 2.1: 激酶催化深腔全原子 3D 几何建模与配体度量距离几何生成器 (`02_code/fetch_kinase_pocket_3d.py`)
  - Tests: `02_code/tests/test_kinase_pocket_3d.py` (2/2 PASSED)
  - Features: Classical Multidimensional Scaling + Distance Geometry relaxation for 3D coordinates, kinase pocket atom extraction.

Status: Phase 1 Complete; Phase 2 in progress (Task 2.1 done).
