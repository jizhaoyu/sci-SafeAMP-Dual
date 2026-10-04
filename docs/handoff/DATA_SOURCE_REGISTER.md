# SafeAMP-Dual 数据源登记簿 (DATA_SOURCE_REGISTER)

本文档登记项目中所有使用的公开数据来源、获取规范及复核状态。

**2026-10-01 更新**：旧 `combined_v2` 的 13 条外部记录缺原始实验测定，已在 `combined_v3_evidence_clean_20261001/exclusions.json` 中逐条排除。当前候选源只有 417 条开发记录；DRAMP 的 10 条具人红细胞 HC50 信息的候选按 `protocol-amd-02` 全员复核后均违反 0.40 隔离阈值（`03_experiments/audits/dramp_amd02_20261001`）。项目仍缺合格独立外部队列。

---

## 1. 已获取开发集来源：DBAASP (v1)
- **数据库名称**：Database of Antimicrobial Activity and Structure of Peptides (DBAASP)
- **官方网址**：`https://dbaasp.org`
- **数据目录**：`02_code/data/sources/dbaasp_v1`
- **采样记录总数**：417 条
- **数据用途**：算法开发与原型验证
- **获取规则**：
  - 10–50 AA 单体无修饰肽
  - 抗菌终点：*E. coli* MIC (≤32 阳性，≥128 阴性)
  - 溶血终点：Human erythrocytes HC50 (≤100 阳性，≥250 阴性)
- **标签分布**：
  - AMP: 阳性 253, 阴性 138, 未知 26
  - Hemo: 阳性 18, 阴性 44, 未知 355
- **数据完整性**：原始 JSON 缓存文件均具有 SHA256 校验 (`.source.json`)。

---

## 2. 计划扩充开发集来源：DBAASP (v2)
- **目标目录**：`02_code/data/sources/dbaasp_v2`
- **扩充目的**：获取更多已测定溶血活性的天然/合成单体肽，缓解单簇连通度过高及标签极度稀疏问题。
- **获取策略**：遵守速率限制，支持断点续传与缓存校验，记录完整过滤与排除原因。

---

## 3. 计划外部验证集来源：DRAMP
- **数据库名称**：Data Repository of Antimicrobial Peptides (DRAMP)
- **官方网址**：`https://dramp.cpu-bioinfor.com/`
- **目标目录**：`02_code/data/sources/dramp_v1`
- **设计用途**：纯独立外部评估队列
- **准入门槛**：必须排除与 DBAASP 重合的原始研究文献及序列同源分子。
