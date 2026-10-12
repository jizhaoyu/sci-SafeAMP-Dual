# DTI 激酶候选筛选重构与自纠错实验验证计划 (Phase 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 DTI 预测从受限的连续亲和力逼近重构为面向候选靶点排序与强结合筛选（$pKd \ge 7.0$）的受控分类框架，在严格实体隔离的 4 折内部验证集上对比回归与分类目标，集成具备自动化根因归因、双轨无偏复算与硬熔断机制的自我纠错协议，并为云端 T4 服务器的两阶段特征与交互探索建立受控输入与退出准则。

**Architecture:**
1. **目标对齐层**：固定当前 2,076 维特征（2048 药物指纹 + 28 靶点特征），严格对比第一阶段 HGB 回归基线、正则化逻辑回归（LogReg）分类与 HGB 分类，验证改变损失函数是否能提升双冷前列命中率（P@10 / AP）。
2. **自纠错保障层**：建立四级故障归因（代码缺陷、优化失败、表达能力瓶颈、数据天花板）、状态哈希锁定、双算法指标对账（$\Delta = 0$）与前向重放门禁，禁止通过事后调参或修饰指标掩饰模型失败。
3. **算力探索层**：为云端 T4（16GB 显存 / 32GB 内存 / 8 核 CPU）制定两阶段受控方案（Step 1: 预计算蛋白表示替换；Step 2: 显式双线性/轻量深度交互项打破加性排序退化），限制单轮 1 小时冒烟预算。
4. **数据溯源层**：脱离“等待作者邮件回复”依赖，基于本地公开测定表构建逐测定血缘追踪，隔离身份缺失突变体。

**Tech Stack:** Python 3.11, scikit-learn 1.8.0, SciPy 1.17.1, NumPy 2.4.4, PyTorch, pytest, JSON-Schema

**Spec:** 本计划基于 `output/dti-linear-tobit-phase2-20261012/线性Tobit训练与评估交付报告.md`、`output/dti-phase1-training-20261012/第一阶段训练与评估交付报告.md` 以及 thread `01a125e4-e7ec-79a3-9b93-26ef374d110a` 的研讨证据。

---

## Global Constraints

- **特征与数据冻结**：当前基准仅采用 64 药物 × 375 靶点严格临时加工数据（总计 15,704 对训练块）；特征严格锁定为 2,076 维；未获授权前不添加未经审查的外部特征。
- **零数据泄露防线**：所有标准化（`StandardScaler`）必须严格在当前折的内部训练集上 `fit`，严禁跨折归一化或在评估集上提取任何统计量。
- **已暴露外层集封存**：历史上的 3 个外层测试集（冷药物 3624 对、冷靶点 3796 对、双冷 876 对）已被多次查看，仅作为固定复用对比基准，不得参与内部超参数选择、早停判定或特征筛选。
- **分类标签口径**：强结合二分类阈值严格固定为 $pKd \ge 7.0$；未删失样本与删失编码值（5.0）严格按照既有定义转换为二分类标签（$5.0 < 7.0$ 判定为负例）。
- **确定性与算力限制**：本地 CPU 实验限制最大 4 线程，固定全局随机种子 `seed=42`；云端 T4 首次探索限制单次显存基准测试不超过 1 小时。
- **环境版本底线**：Python 3.11.9, NumPy 2.4.4, SciPy 1.17.1, scikit-learn 1.8.0。

---

## Review Focus

1. **零阳性药物处理失真**：双冷场景下部分药物在候选集中无任何 $pKd \ge 7$ 强结合靶点。宏平均 AP 必须显式排除无阳性药物并报告有效药物数（如 5/12），而 P@10 必须对全部 12 个药物计算（无阳性计为 0）。严禁混淆两者的计算人群。
2. **加性特征导致的跨药物排序退化**：纯线性模型 $w_d \cdot x_d + w_t \cdot x_t$ 在固定候选靶点集合下必定导致所有药物的靶点顺序完全相同。评测脚本必须包含“排序多样性检测”，若 Spearman 跨药物相关系数恒为 1.0，必须明确标记为结构退化。
3. **将模型效果差误报为程序 Bug 或反向粉饰**：模型未击败常数参考属于科学结论，不得通过放宽阈值（如改为 $pKd \ge 6.0$）、剔除困难样本或修改指标定义强行扭转结果。
4. **静默覆盖历史模型与污染审计日志**：代码修复若改变了已训练模型的权重或预测输出，必须保留旧模型为归档快照，不得直接覆盖同名文件。
5. **外层测试集被用作超参验证**：任何基于外层测试集表现反推调整超参数的行为，均被视为协议违规并触发自纠错熔断。

---

## 自我纠错协议规范 (Self-Correction Protocol)

执行代理（Gemini / 辅助子代理）必须严格遵照以下自纠错机制运行：

### 1. 根因四分法隔离规则 (Root-Cause Taxonomy)
遇到异常或负面结果时，必须首先判定并输出故障类型，严禁混淆：
- **Type A (代码与环境缺陷)**：语法错误、数组越界、Scaler 泄漏、随机种子漂移、类型不匹配。**处理方式**：原地修复代码，运行单元测试验证，并在日志记录 Bug 修复轨迹。
- **Type B (数值与优化未收敛)**：L-BFGS-B 超过最大迭代、梯度爆炸/消失、HGB 提前退出且损失未降。**处理方式**：调整数值稳定性参数（如容差、学习率、初始值），不得改变数学目标本身。
- **Type C (模型表达能力瓶颈)**：优化正常收敛，但验证集指标（P@10 / AP）未超过常数参考或 HGB 对照。**处理方式**：如实接受并归档实验结果，确认“该模型在此特征下不具备筛选增益”，触发停止条件，不得反复微调超参。
- **Type D (数据分布与标签天花板)**：由于基因聚合或测定空白导致的标签噪声。**处理方式**：记录数据局限性并输出敏感性分析，不得手动清洗剔除“异常点”。

### 2. 双轨独立复算与前向重放门禁 (Dual-Track Replay Gate)
- 所有核心指标（未删失 RMSE, AP 宏平均, P@10 宏平均, C-index）必须由两套独立编写的 Python 算子（如 `sklearn.metrics` 与纯 NumPy 向量化算子）各自计算。
- 两套算子计算结果的最大绝对偏差必须满足：
  * RMSE / MAE: $\Delta \le 10^{-6}$
  * AP / P@10 / C-index: $\Delta \le 10^{-6}$
- 模型预测结果必须使用保存的系数/树结构进行纯算术前向重放，重放输出与训练后直接输出差值满足 $\max |y_{\text{replay}} - y_{\text{pred}}| \le 10^{-12}$。

### 3. 锁相验证与审计追踪 (Phase-Locked Verification)
- 任何训练启动前，自动扫描并记录所有源码、输入数据、划分文件的 SHA-256，生成 `pre_run_lock.json`。
- 若执行过程中修改了算法实现且该修改影响了已经生成的权重，必须：
  1. 将旧产物重命名为 `_superseded_<timestamp>` 保留；
  2. 在 `delivery_status.json` 中标记 `superseded_reason`；
  3. 重新生成锁定哈希并重新执行完整流程。

### 4. 自动熔断与退出机制 (Circuit Breakers)
- **熔断准则 1 (无效调参熔断)**：在内部验证集上，若模型连续 3 次调整超参数（如正则化强度 C）后，双冷 P@10 提升均低于 0.005，立刻停止参数搜索，采纳默认配置。
- **熔断准则 2 (常数基线熔断)**：若最佳分类模型在 4 折双冷验证集上的平均 P@10 未能战胜常数期望参考（0.0970），立即终止该类模型的部署流程，严禁替换线上系统。

---

## 任务拆解与执行清单

### Task 1: 协议固化与 4 折实体隔离验证集构建 (Pre-registration & 4-Fold Entity-Isolated Splits)

**Files:**
- Create: `02_code/dti_phase3_split_generator.py`
- Test: `02_code/tests/test_dti_phase3_split_generator.py`
- Output: `output/dti-phase3-candidate-screening-20261012/splits/`

**Interfaces:**
- Consumes: `02_code/dti_linear_tobit.py` 中的数据加载器与 15,704 对训练块
- Produces: 4 折药物、靶点及双实体完全隔离的交叉验证索引 `train_idx`, `val_drug_cold_idx`, `val_target_cold_idx`, `val_dual_cold_idx`

- [ ] **Step 1: 编写拆分器单元测试，验证双实体隔离与无交叉泄露**
```python
def test_four_fold_entity_isolation():
    # 验证每一折的验证集药物/靶点与训练集完全无交集
    # 验证双冷子集同时满足药物冷与靶点冷
```
- [ ] **Step 2: 运行测试确保在未实现时失败**
Run: `pytest 02_code/tests/test_dti_phase3_split_generator.py -v`
Expected: FAIL (ModuleNotFoundError)
- [ ] **Step 3: 实现 `dti_phase3_split_generator.py`**
基于 GroupKFold / 分层聚类拆分算法，在 15,704 对数据上生成并保存 4 组确定性划分，固化到 `splits/fold_{0..3}.json`。
- [ ] **Step 4: 运行测试并验证通过**
Run: `pytest 02_code/tests/test_dti_phase3_split_generator.py -v`
Expected: PASS
- [ ] **Step 5: 提交并生成预先登记锁定**
```bash
git add 02_code/dti_phase3_split_generator.py 02_code/tests/test_dti_phase3_split_generator.py
git commit -m "feat(phase3): add 4-fold entity-isolated split generator with strict test gate"
```

---

### Task 2: 受控目标对齐：三模型严格对比引擎实现 (Controlled 3-Model Engine)

**Files:**
- Create: `02_code/dti_candidate_classifiers.py`
- Test: `02_code/tests/test_dti_candidate_classifiers.py`

**Interfaces:**
- Consumes: 2,076 维标准化特征与二分类标签（$y \ge 7.0$ 为 1，否则为 0）
- Produces: `HGBContinuousBaseline`, `LogRegCandidateClassifier`, `HGBBinaryClassifier` 三个统一规范模型类，均提供 `fit(X, y)` 与 `predict_score(X) -> np.ndarray`

- [ ] **Step 1: 编写三模型接口与一致性测试**
```python
def test_classifier_interfaces_and_scores():
    # 验证三种模型均能输出连续排序分数
    # 验证无 NaN、无越界，且对于纯常数输入有确定性降级
```
- [ ] **Step 2: 运行测试验证失败**
Run: `pytest 02_code/tests/test_dti_candidate_classifiers.py -v`
Expected: FAIL
- [ ] **Step 3: 实现 `dti_candidate_classifiers.py`**
封装 scikit-learn 的 `HistGradientBoostingRegressor` (对照), `LogisticRegression(penalty='l2', solver='lbfgs')`, 及 `HistGradientBoostingClassifier(loss='log_loss')`。
- [ ] **Step 4: 运行测试验证全部通过**
Run: `pytest 02_code/tests/test_dti_candidate_classifiers.py -v`
Expected: PASS
- [ ] **Step 5: 提交**
```bash
git add 02_code/dti_candidate_classifiers.py 02_code/tests/test_dti_candidate_classifiers.py
git commit -m "feat(phase3): implement controlled 3-model candidate screening engine"
```

---

### Task 3: 内部验证双轨评估与熔断门禁自检 (Internal Verification & Circuit Breakers)

**Files:**
- Create: `02_code/dti_phase3_evaluator.py`
- Create: `02_code/run_phase3_internal_benchmark.py`
- Test: `02_code/tests/test_dti_phase3_evaluator.py`
- Output: `output/dti-phase3-candidate-screening-20261012/internal_results.json`

**Interfaces:**
- Consumes: Task 1 的划分数据与 Task 2 的三模型类
- Produces: 4 折交叉验证指标表（AP, P@10, P@30, C-index, RMSE），双轨无偏复算审计报告，以及熔断裁决标志 `circuit_breaker_triggered: bool`

- [ ] **Step 1: 编写双轨复算与人群隔离测试**
```python
def test_dual_track_metrics_precision():
    # 校验自研 NumPy 算子与 sklearn 算子最大差 <= 1e-6
    # 校验 AP 排除零阳性药物、P@10 覆盖全体药物的严密性
```
- [ ] **Step 2: 运行测试验证失败**
Run: `pytest 02_code/tests/test_dti_phase3_evaluator.py -v`
Expected: FAIL
- [ ] **Step 3: 实现 `dti_phase3_evaluator.py` 与运行器**
编写双轨指标计算模块与 12 次拟合（3 模型 × 4 折）受控训练流程，计算常数基线期望并实施熔断检查。
- [ ] **Step 4: 运行测试验证通过**
Run: `pytest 02_code/tests/test_dti_phase3_evaluator.py -v`
Expected: PASS
- [ ] **Step 5: 提交**
```bash
git add 02_code/dti_phase3_evaluator.py 02_code/run_phase3_internal_benchmark.py 02_code/tests/test_dti_phase3_evaluator.py
git commit -m "feat(phase3): implement dual-track evaluation and circuit breaker logic"
```

---

### Task 4: 云端 T4 两阶段实验包准备与显存冒烟测试 (Cloud T4 Readiness & 2-Stage GPU Pilot)

**Files:**
- Create: `02_code/cloud_t4_pilot/benchmark_t4_runtime.py`
- Create: `02_code/cloud_t4_pilot/esm2_embedding_loader.py`
- Create: `02_code/cloud_t4_pilot/bilinear_interaction_model.py`
- Test: `02_code/tests/test_cloud_t4_pilot.py`

**Interfaces:**
- Consumes: 本地固化的 4 折划分与预计算 ESM-2 蛋白特征
- Produces: T4 冒烟基准数据（显存占用、单 epoch 耗时、前向重放精度），确认是否满足 16GB 显存上限

- [ ] **Step 1: 编写 GPU 内存分配与模型轻量化单元测试**
```python
def test_bilinear_interaction_forward_and_memory():
    # 验证模型在 CPU/CUDA 上均可无缝执行前向与反向传播
    # 验证参数量在 500 万以内，单批次显存不超过 2GB
```
- [ ] **Step 2: 运行测试验证失败**
Run: `pytest 02_code/tests/test_cloud_t4_pilot.py -v`
Expected: FAIL
- [ ] **Step 3: 实现 T4 适配代码与显存基准探测脚本**
编写双线性交互层 $f(d, t) = d^T W t + w_d^T d + w_t^T t + b$ 及 ESM-2 嵌入加载校验器，加入自动回退与耗时监控。
- [ ] **Step 4: 运行测试验证通过**
Run: `pytest 02_code/tests/test_cloud_t4_pilot.py -v`
Expected: PASS
- [ ] **Step 5: 提交**
```bash
git add 02_code/cloud_t4_pilot/ 02_code/tests/test_cloud_t4_pilot.py
git commit -m "feat(phase3): create cloud T4 pilot suite with bilinear interaction and esm2 loader"
```

---

### Task 5: 逐测定数据血缘解耦与交付出口对账 (Assay-Level Lineage & 3-Way Project Exit Closeout)

**Files:**
- Create: `02_code/dti_assay_lineage_audit.py`
- Output: `output/dti-phase3-candidate-screening-20261012/assay_lineage_manifest.csv`
- Output: `output/dti-phase3-candidate-screening-20261012/phase3_delivery_report.md`
- Test: `02_code/tests/test_dti_assay_lineage_audit.py`

**Interfaces:**
- Consumes: 本地原始测定表与当前 64×375 基因聚合加工基准
- Produces: 逐条测定的可追溯性清单、突变体状态分类表（已闭合 / 身份不完整）、以及符合 3 种出口标准的最终交付总结

- [ ] **Step 1: 编写血缘对账测试**
```python
def test_assay_lineage_integrity():
    # 验证本地原始测定行数与聚合前记录完全对应
    # 验证无法闭合的突变体样本打上受限标签
```
- [ ] **Step 2: 运行测试验证失败**
Run: `pytest 02_code/tests/test_dti_assay_lineage_audit.py -v`
Expected: FAIL
- [ ] **Step 3: 实现血缘审计脚本与出口判定生成器**
解析本地原始文件，建立全链路映射清单；根据 Task 3 内部验证指标自动判定出口类型（A: 仅发布受限冷药物筛选; B: 推进交互模型与校准; C: 诚实终止并转为证据检索工具）。
- [ ] **Step 4: 运行测试验证通过**
Run: `pytest 02_code/tests/test_dti_assay_lineage_audit.py -v`
Expected: PASS
- [ ] **Step 5: 提交**
```bash
git add 02_code/dti_assay_lineage_audit.py 02_code/tests/test_dti_assay_lineage_audit.py
git commit -m "feat(phase3): add assay-level lineage audit and automated exit closeout"
```

---

## 交付与执行交接

计划已完整固化至 `docs/superpowers/plans/2026-10-12-dti-phase3-candidate-screening-and-self-correction.md`。

请审阅本方案。你希望采用哪种执行模式？
- **Native (推荐)**：由我在当前会话中逐项编写测试与实现代码，执行验证与自纠错审计，成本最低、反馈最快。
- **Subagent-driven**：为每个 Task 派发独立的子代理执行，并由独立审查代理进行把关。
