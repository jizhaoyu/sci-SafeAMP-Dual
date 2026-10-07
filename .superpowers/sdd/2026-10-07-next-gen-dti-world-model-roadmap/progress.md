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

- [x] Task 2.2: SE(3) 等变几何图匹配网络 (`02_code/equivariant_pocket_matcher.py`)
  - Tests: `02_code/tests/test_equivariant_pocket_matcher.py` (5/5 PASSED)
  - Features: RBF 连续距离展开、软化 Lennard-Jones 位阻势能、铰链区定向氢键几何匹配、EGFR T790M 耐药突变空间位阻敏化、Kabsch 3-点唯一取向刚体对齐、PyTorch `EquivariantPocketMatcherNN`。

- [x] Task 2.3: 激酶 DFG 构象翻转自适应与诱导契合打分模块 (`02_code/kinase_conformation_adapter.py`)
  - Tests: `02_code/tests/test_kinase_conformation_adapter.py` (4/4 PASSED)
  - Features: 药物结合模式分类 (Type I / Type II / Covalent)、激酶活化环 DFG 翻转热力学重组能估算、诱导契合结合自由能补偿 (解析 BCR-ABL 对比 EGFR 选择性机制)。

- [x] Task 3.1: MM-GBSA 热力学粗粒度物理引擎与微扰修正器 (`02_code/thermodynamic_physics_engine.py`)
  - Tests: `02_code/tests/test_thermodynamic_physics_engine.py` (3/3 PASSED)
  - Features: 第一性原理结合自由能分解 (MM + GB + SA - T*Delta_S)、环感知可旋转键构象熵惩罚、Still 广义玻恩极性溶剂化与疏水表面脱溶剂化能、物理 Delta-Learning 校准。

- [x] Task 3.2: 基于集成方差的主动学习推荐引擎 (`02_code/active_learning_recommender.py`)
  - Tests: `02_code/tests/test_active_learning_recommender.py` (2/2 PASSED)
  - Features: 贝叶斯获取函数 (Expected Improvement, UCB, Max Uncertainty)、四象限探索与利用分类、湿实验高信息增益验证分子清单自动导出。

Status: All 3 Phases Complete and Fully Verified (24/24 Tests Passed, Check MIC Exit 0, Frontend 0 Errors).
