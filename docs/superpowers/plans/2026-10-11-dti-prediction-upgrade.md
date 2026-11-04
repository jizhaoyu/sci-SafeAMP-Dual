# DTI 激酶亲和力预测系统升级与学术真实性工程实施计划 (P0 阶段)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 彻底解决 71.17% 删失样本造成的强结合区负偏置（Negative Shrinkage Bias），引入 Tobit 删失似然回归与可微排序损失，修复 Playwright E2E 测试脚本断裂，并对齐论文与参考文献数据口径。

**Architecture:** 
1. 理论层：用 Tobit 区间删失似然与 Pairwise Surrogate CI 替代单纯 MSE 均方误差，彻底松绑非结合物对活性化合物的向下牵引。
2. 工程层：修正测试定位符与前端交互脱节，打通真实的 Exit 0 质量门禁。
3. 学术层：订正论文 18,343（71.17%）删失数据笔误，替换历史遗留 TeX 与 BibTeX 资产。

**Tech Stack:** PyTorch, NumPy, SciPy, scikit-learn, FastAPI, Playwright, React, RDKit

---

## 任务拆解与执行清单

### 任务 1: 论文数据口径订正与历史残留清理 (Paper & Reference Realignment)
- [x] 1.1 修改 `04_paper/MANUSCRIPT_DTI_DAVIS_STACKED_FRAMEWORK.md` 第 16 行与第 58 行，将 `73.1% (18,837 / 25,772 pairs)` 严格修正为 `71.17% (18,343 / 25,772 pairs)`。
- [x] 1.2 将 `04_paper/manuscript.tex` 重构为 DTI 专版。
- [x] 1.3 更新 `04_paper/references.bib`：从 `output/dta-paper-full-draft-v1-20261010/references.bib` 引入 Davis 2011、DeepDTA、ESM-2 等核心文献。
- [x] 1.4 验证文档中无违规 LaTeX 多行环境（如 `\begin{aligned}`、`&=`、`\\` 等）。

### 任务 2: 修复 Playwright E2E UI 自动化测试断裂 (E2E Test Gate Fix)
- [x] 2.1 检查 `frontend/scripts/run_e2e_ui_test.mjs` 中的按钮选择器：
  - 将第 159 行与第 249 行的 `'执行单点结合亲和力预测'` 更新为真实 React UI 文本 `'开始预测'`。
  - 针对被置灰锁定的 `普纳替尼 → ABL1-T315I` 预设，调整测试策略为有效靶点（如 `奥希替尼 → EGFR(T790M)`）或从临床库载入。
- [x] 2.2 运行 `node frontend/scripts/run_e2e_ui_test.mjs`，确保测试完整走完 6 个阶段，生成 21 张截图，并实现 Exit 0。

### 任务 3: 实现 Tobit 删失回归与可微排序混合损失模型 (Tobit-Ranking Engine)
- [x] 3.1 创建 `02_code/dti_tobit_ranking_model.py`：
  - 实现标准 Tobit 负对数似然损失（针对 $y > 5.0$ 的高斯项与针对 $y \le 5.0$ 的存活概率项 $\Phi$）。
  - 实现可微 Pairwise CI 排序损失（对偶样本 Sigmoid 差值梯度）。
  - 实现混合优化器（`TobitRankingRegressor`）。
- [x] 3.2 编写单元测试 `02_code/test_dti_tobit_ranking_model.py`，验证梯度计算正常、删失惩罚逻辑符合统计学预期。
- [x] 3.3 编写训练与基准评估脚本 `02_code/train_dti_tobit_ranking_model.py`，在 DAVIS 训练块上拟合并在 4 大域上对比评估。

### 任务 4: 分层评估与客观对账 (Stratified Re-evaluation & Bias Audit)
- [x] 4.1 在严格双冷测试域（Strict Dual-Cold）和冷靶点域（Cold Target）上，重新核算：
  - 全样本 MAE / RMSE / CI；
  - 删失样本 MAE；
  - 强结合样本（$pK_d \ge 7.0$）的预测均值偏差 Mean Bias 与 MAE。
- [x] 4.2 导出对账成果至 `output/dti-tobit-upgrade-20261011/`，验证强结合区的负偏置是否被有效消解。

### 任务 5: 推理运行时挂载与全栈联调 (Runtime & Full-Stack Integration)
- [x] 5.1 在 `02_code/dti_inference_runtime.py` 中注册并挂载 `tobit_ranking_model`。
- [x] 5.2 运行 `python -m pytest 02_code/test_dti_real_backend_integration.py` 确保后端全接口测试通过。
