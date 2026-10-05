# 人红细胞 HC50 证据与双任务独立外部队列审计 (gemini_hc50_external_review_20261004_v1)

本审计目录专用于对公开实验文献中的人红细胞 HC50 测定证据，以及具有同一受测分子形式的 *E. coli* MIC 与人红细胞 HC50 双端点独立外部候选队列进行严格核查与同源隔离审计。

---

## 一、审计范围与边界

1. **唯一目标**：检索、核查公开实验记录中的真实人红细胞 HC50 测定，并审计是否存在符合 `protocol-amd-02` 全员序列隔离与研究独立性的双任务外部候选。
2. **严格禁止**：
   - 不修改 `04_paper/research_status.json`，不擅自解除 blocked 状态。
   - 不修改 `02_code/` 源码，不调整协议阈值与门禁。
   - 不运行任何模型拟合、ESM 推理或训练（`model_fit_calls = 0`）。
   - 不进行 Git 提交或推送。
3. **合格判定标准**：真实、可复核的科学事实为唯一标准；合格数量为零是客观科学阻断的正常结果。

---

## 二、基线输入与密码学校验

| 输入文件 | 相对路径 | 校验 SHA-256 | 记录数 | 校验状态 |
| :--- | :--- | :--- | :--- | :--- |
| 正式开发集 | `03_experiments/prepared/amd02_evidence_clean_20261001/records.csv` | `ccec346bf88c6d3b2da57f058019fb10305019de5dca4ef3402949931ac71f37` | 417 | 通过 |
| 历史候选表 | `03_experiments/audits/dramp_dual_task_primary_audit_20261003_v1/candidate_primary_audit.csv` | `238bcddfa569687b2740314e56476a5b9ae84cdb3e6af97bbd87acaaae98e672` | 39 | 通过 |
| 探索 MIC 队列 | `03_experiments/audits/mic_goat_followup_release_20261004_v1/cohort/candidate_molecules.csv` | `c61beb5ff8ef92375c9eb5f164896f306906c1ff24424a1ec876e6f71a8d2655` | 17 | 通过 |

---

## 三、环境与复跑命令

操作系统：Windows 11 / PowerShell (pwsh)  
Python 环境：Python 3.11  

复跑主审计流程：
```powershell
python "03_experiments/audits/gemini_hc50_external_review_20261004_v1/scripts/audit_pipeline.py"
```

运行合成回归测试套件：
```powershell
python "03_experiments/audits/gemini_hc50_external_review_20261004_v1/scripts/test_audit_rules.py"
```

更新产物清单哈希：
```powershell
python "03_experiments/audits/gemini_hc50_external_review_20261004_v1/scripts/build_manifest.py"
```

---

## 四、产物文件索引

1. `README.md`：本文件，审计说明与命令索引。
2. `search_log.csv`：检索记录表（Europe PMC、DBAASP、DRAMP 等渠道与检索式）。
3. `raw/`：下载与归档的原始论文 XML/文件。
4. `source_manifest.csv`：文献来源清单与 SHA-256 摘要。
5. `molecule_review.csv`：分子身份审查表（序列、长度、形式、中性分子量、身份结论与依据）。
6. `assay_observations.csv`：原始实验测定观察记录表（端点、受测对象、原值、单位、条件、位置）。
7. `derived_labels.csv`：标准化区间推导与二值标签表（含换算公式与依据）。
8. `hc50_verified_pool.csv`：**证据池 A**（穿透核实的人红细胞 HC50 证据集合，1 条，附带二硫键/酰胺化/同源泄漏局限性说明）。
9. `external_candidate_decisions.csv`：**证据池 B**（双任务候选逐条门禁判定表，83 条）。
10. `eligible_external_candidates.csv`：证据池 B 完整通过门禁候选表（空表头，当前通过数 0）。
11. `excluded_or_pending.csv`：排除与待补资料清单（记录具体阻断原因与补正要求）。
12. `conflicts.csv`：数据冲突记录表。
13. `study_aliases.csv`：测量研究与方法引用区分及别名表。
14. `similarity_to_development.csv`：候选多肽 × 417 条开发集记录的完整 Needleman-Wunsch 全员比对表（34,611 行）。
15. `candidate_similarity.csv`：候选内部全员两两同源比对表。
16. `historical_exposure.csv`：历史研究与探索队列暴露/重叠审计表。
17. `audit_summary.json`：审计总结结构化文件（含状态、计数、逐门禁统计与阻断原因）。
18. `manifest.json`：全目录输入、脚本与产物 SHA-256 校验清单。
19. `report.md`：详细审计技术分析报告。
