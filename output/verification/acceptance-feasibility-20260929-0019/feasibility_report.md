# SafeAMP-Dual 可行性与门禁判定报告 (Research Feasibility Report)

**生成时间**：2026-09-28T16:24:14.208121+00:00  
**判定状态**：**❌ BLOCKED: GATING CONDITIONS UNMET**  
**比对一致性阈值**：0.4  
**评估数据集**：`02_code\data\sources\dbaasp_v1\records.csv`  

---

## 1. 核心判定总结
- **可运行性 (Engineering)**: 软件工程全链路健全。
- **数据可行性 (Scientific Feasibility)**: 被科学门禁阻断，禁止启动正式模型实验。

### 阻断原因清单 (Blockers):
- ⛔ **Fewer than 6 independent homology clusters (1 clusters found, largest contains 417/417 molecules, 100.0%). Cannot perform 5-fold cross-validation plus holdout test without homology leakage.**
- ⛔ **No qualified independent external validation cohort present.**

---

## 2. 标签覆盖统计 (Label Coverage)
- **分子总量**: 417 条未修饰单体肽
- **AMP 抗菌标签**: 阳性 253 条, 阴性 138 条, 未测 26 条 (覆盖率 93.8%)
- **Hemo 溶血标签**: 阳性 18 条, 阴性 44 条, 未测 355 条 (覆盖率 14.9%)
- **双任务均有实验测定**: 36 条 (8.6%)

---

## 3. 序列隔离拓扑诊断 (Sequence Isolation)
- **独立连通分量总数**: 1
- **最大连通分量包含序列数**: 417 / 417 (100.0%)
- **判定结论**: 连通簇过少且单一超大簇坍缩，无法在严禁泄漏前提下划分 5 折

---

## 4. 外部验证队列 (External Cohort)
- **外部队列样本数**: 0 条
- **来源独立性**: 缺失符合标准的独立外部队列

