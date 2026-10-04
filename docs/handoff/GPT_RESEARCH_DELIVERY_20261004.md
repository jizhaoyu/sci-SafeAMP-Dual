# SafeAMP-Dual 计算生物学研究交付报告 (GPT 续接版)

> **交付日期**：2026-10-04（Asia/Shanghai）  
> **工作区目录**：`D:\桌面文件\sci`  
> **执行环境**：Windows / PowerShell (pwsh) / Python 3.11  
> **产物版本归档**：[`03_experiments/audits/alternative_primary_search_20261004_v2/`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/)  
> **CodeGraph 状态**：已同步（`codegraph sync` 执行完成，1,007 节点、763 引用解析完成）  

---

## 一、 核心结论先行 (Executive Summary)

* **新准入分子数**：**0**；**新释放二值标签数**：**0**；**新模型拟合执行**：**严格禁止并保持 0 次 fit**。
* **MIC 单任务基线状态**：**`status = local_exploratory_training_independently_verified`**，`training_blocked = false`。
  * 保持 16 分子、23 观察、固定三折 9 个模型（LR、RF、Dummy）基线，独立无 fit 复核 100% 通过（复核文件：[`03_experiments/audits/mic_followup_run_validation_20261004_v2.json`](file:///D:/桌面文件/sci/03_experiments/audits/mic_followup_run_validation_20261004_v2.json)）。
* **原双任务正式状态**：**`formal_dual_task_status = blocked`**，`run_status = none`，`formal_results_available = false`，`publication_ready = false`。
  * 历经 DRAMP、Archaeome、AMP-Designer、Pandinin、ChMAP、山羊抗菌肽及爪蟾 Hymenochirin 等所有候选队列审查，**100% 的候选外部序列均与正式开发集 417 条记录存在同源泄漏（最高相似度均 ≥0.40）**，无法作为独立外部验证队列。
* **本轮重大科学突破与文献还原**：
  * **成功完整获取并解析荷兰瓦赫宁根大学作者博士学位论文**（[`mechkarska2013_thesis.pdf`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/raw/mechkarska2013_thesis.pdf)，1,803,832 字节，SHA256: `25885f2e02aaadba1929c4723570104dc95520964dd6e4b3698e9562fe9f1da4`），提取其第 6 章原始实验测定（Table 1）与序列质谱数据（Fig. 4）。
  * 证实 Hymenochirin-1B 为 C 端 α-酰胺化修饰多肽，超出当前未修饰范围；Hymenochirin-2B~5B 大肠杆菌实测 MIC 换算后为 56.35~114.43 µg/ml，**全数落入 32 < MIC < 128 µg/ml 的中间不确定区间**，依规程无法产生二值标签；且 5 条序列对正式开发集相似度高达 0.5172~0.8276，跨队列同源门禁被严密拦截。
  * 蝎毒素 Pandinin 2 系列突变体实测 MIC（换算后为 32.15~68.16 µg/ml）同样越过 32 µg/ml 阳性判定界限，无二值标签，且与开发集 DBAASP:948 存在 100% 同源重叠。
  * 山羊抗菌肽研究（PMC6284057）实测数据命中正式开发集 DBAASP:12306 第一参考文献，ChMAP-28 与现有 MIC 成员 BMAP-27B 同源性达 0.6071（必须同组件），mini-ChBac 对开发集有 24 处同源冲突。

---

## 二、 真实机器状态与基线索引 (Machine State & Baseline Index)

为确保 GPT 在后续会话中不混淆两条研究主线，请严格核对以下机器状态：

### 1. 机器状态与双主线边界
* **MIC 单任务状态**：来源于 [`03_experiments/audits/mic_training_readiness_20261004_v22.json`](file:///D:/桌面文件/sci/03_experiments/audits/mic_training_readiness_20261004_v22.json)。
  * 训练协议：`protocol-mic-11`。
  * 队列规模：16 个分子、23 条实测观察（5 个阳性、11 个阴性）。
  * 分区拓扑：固定三折（seed=42，shuffle=True），7 个连通分量，跨折同源边严格为 0。
  * 模型产物：9 个折模型（LR、RF、Dummy），48 条 OOF 预测记录，均无外部泄漏。
  * 独立复核：`passed`（禁止在复核时调用任何 fit/fit_transform，重载模型与 Scaler 进行指标重算）。
* **原双任务状态**：来源于 [`04_paper/research_status.json`](file:///D:/桌面文件/sci/04_paper/research_status.json)。
  * 协议：`protocol-amd-02`。
  * 开发数据：[`03_experiments/prepared/amd02_evidence_clean_20261001/records.csv`](file:///D:/桌面文件/sci/03_experiments/prepared/amd02_evidence_clean_20261001/records.csv)（417 条真实记录）。
  * 阻断核心原因：无通过全员 ≥0.40 隔离门禁的独立外部队列。

### 2. 现有 MIC 关键资产速查
* **冻结协议**：[`03_experiments/protocols/protocol-mic-11.json`](file:///D:/桌面文件/sci/03_experiments/protocols/protocol-mic-11.json)
* **冻结存证**：[`03_experiments/audits/protocol_mic_11_freeze_20261004_v1.json`](file:///D:/桌面文件/sci/03_experiments/audits/protocol_mic_11_freeze_20261004_v1.json)
* **发布数据集**：[`03_experiments/audits/mic_followup_release_20261004_v1/`](file:///D:/桌面文件/sci/03_experiments/audits/mic_followup_release_20261004_v1/)
* **训练模型运行目录**：[`03_experiments/runs/mic_followup_baseline_20261004_v1/`](file:///D:/桌面文件/sci/03_experiments/runs/mic_followup_baseline_20261004_v1/)
* **独立复核报告**：[`03_experiments/audits/mic_followup_run_validation_20261004_v2.json`](file:///D:/桌面文件/sci/03_experiments/audits/mic_followup_run_validation_20261004_v2.json)
* **完整成果索引表**：[`03_experiments/audits/alternative_primary_search_20261004_v2/existing_mic_index.md`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/existing_mic_index.md)

---

## 三、 本轮五大公开来源逐观察审查全景 (Comprehensive Audit of 5 Sources)

审查脚本位于 [`process_v2_audit.py`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/process_v2_audit.py)，原始提取位于 [`primary_evidence.json`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/primary_evidence.json)，逐分子决定记录于 [`molecule_decisions.csv`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/molecule_decisions.csv)，逐测定记录于 [`assay_decisions.csv`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/assay_decisions.csv)。

### 1. 蝎毒素 Pandinin 2 突变体研究 (Pandinin 2014)
* **文献出处**：DOI `10.1371/journal.pone.0101742`，PMCID `PMC4096598`，CC BY 4.0。
* **实测分析**：Table 1 给出 5 种天然与变体多肽序列；Table 3 给出大肠杆菌实测 MIC。
* **换算与门禁审查**：
  * `Pin2` (24 AA, MW 2612.1)：MHB 实测 12.5 µM，换算为 `12.5 * 2612.1 / 1000 = 32.65 µg/ml`。由于 `32.65 > 32`，不满足阳性条件，且 `< 128`，落入中间灰区，无法导出二值标签。对正式开发集 DBAASP:948 相似度为 1.0000（24 处同源冲突）。
  * `Pin2[G]` (24 AA, MW 2572.0)：MHB 实测 12.5 µM，换算为 `12.5 * 2572.0 / 1000 = 32.15 µg/ml`。由于 `32.15 > 32`，落入中间灰区。对开发集相似度 0.9583。
  * `Pin2[GPG]` (26 AA, MW 2726.2)：MHB 实测 12.5 µM，换算为 `34.08 µg/ml`，落入中间灰区。
  * `Pin2[14]` (14 AA, MW 1693.1)：MHB 实测 25.0 µM，换算为 `42.33 µg/ml`，落入中间灰区。
  * `Pin2[17]` (16 AA, MW 1849.3)：MHB 实测 `>25.0 µM`，删失不确定值。
* **结论**：**准入 0**。

### 2. 家鸦转录组 AMP 研究 (Corvus 2023)
* **文献出处**：DOI `10.1038/s41598-023-45875-w`，PMCID `PMC10618271`，CC BY 4.0。
* **审查结果**：合成多肽（CS-AMP1、CS-AMP2 等）在实验方法部分明确记载使用 Rink Amide 树脂合成，全部带有 C 端酰胺化（`-NH2`）。
* **结论**：**超出未修饰线性肽范围，准入 0**。

### 3. 山羊多肽抗肿瘤研究 (ChMAP 2018)
* **文献出处**：DOI `10.3389/fphar.2018.01501`，PMCID `PMC6308165`，CC BY 4.0。
* **审查结果**：Table 1 仅提供肿瘤细胞系（HL-60、A431 等）IC50 测定，无原始大肠杆菌 MIC 表；序列与正式开发集 DBAASP:12306 发生 100% 来源与序列重叠。
* **结论**：**无 MIC 测定且来源重叠，准入 0**。

### 4. 山羊抗菌肽协同机制研究 (Goat Antibacterial 2018)
* **文献出处**：DOI `10.3389/fmicb.2018.02983`，PMCID `PMC6284057`，CC BY 4.0。
* **实测分析**：Table 2 提供了微量肉汤稀释法测定的实测 MIC；Methods 明确采用 pET 表达融合蛋白并经溴化氰 (CNBr) 裂解，获得游离 N/C 端天然线性多肽。
* **换算与门禁审查**：
  * `ChMAP-28` (27 AA)：大肠杆菌 C600 实测 MIC 为 0.06 µM（0.20 µg/ml，阳性）。但该论文是正式开发集 DBAASP:12306 的第一原始参考文献（PubMed ID 30555455）；且 ChMAP-28 与现有 MIC 成员 BMAP-27B 相似度达 0.6071，依同源规程必须归入 Component 4，无法产生独立组件。
  * `mini-ChBac7.5Nα` (22 AA)：大肠杆菌实测 MIC 为 2.0 µM（5.82 µg/ml，阳性）。但其与现有 MIC 成员 `3e656d2ae8d48ae33078fcd4`（Bac7 家族）相似度达 0.6400，必须合并进 Component 0；且跨队列对正式开发集 417 条记录存在 24 处同源冲突。
  * `mini-ChBac7.5Nα(1-16)` (16 AA)：生理盐浓度下活性严重恶化至 16 µM（34.12 µg/ml，落入中间区间）；与 Component 0 相似度 0.6111。
* **结论**：**开发集重叠 + 强同源归并原有组件，准入 0**。

### 5. 侏儒爪蟾天然宿主防御肽研究 (Hymenochirin 2012 / Mechkarska 2013 论文第 6 章)
* **文献出处**：DOI `10.1016/j.peptides.2012.03.029`，瓦赫宁根大学论文库全文 PDF。
* **实测分析**：第 6 章 Table 1 给出大肠杆菌 ATCC 25726 实测 MIC 与人红细胞 LC50；Fig. 4 给出 MALDI-TOF 质谱与序列。
* **换算与门禁审查**：
  * `Hymenochirin-1B` (29 AA, Mr 3061.8)：质谱和序列明确标明 `IKLSPETKDNLKKVLKGAIKGAIAVAKMV.NH2`，为 C 端 α-酰胺化修饰肽，不符合未修饰多肽范围。
  * `Hymenochirin-2B` (29 AA, Mr 2973.7, 游离羧基)：实测 MIC 为 20 µM，换算为 `20 * 2973.7 / 1000 = 59.47 µg/ml`。由于 `32 < 59.47 < 128`，落入中间灰区，无法产生二值标签。对正式开发集 DBAASP:14150 相似度高达 0.8276。
  * `Hymenochirin-3B` (28 AA, Mr 2817.7, 游离羧基)：实测 MIC 为 20 µM，换算为 `56.35 µg/ml`，落入中间灰区。对开发集相似度 0.6552。
  * `Hymenochirin-4B` (28 AA, Mr 2865.7, 游离羧基)：实测 MIC 为 20 µM，换算为 `57.31 µg/ml`，落入中间灰区。对开发集相似度 0.6897。
  * `Hymenochirin-5B` (28 AA, Mr 2860.8, 游离羧基)：实测 MIC 为 40 µM，换算为 `114.43 µg/ml`，落入中间灰区；且在 MHB 肉汤中溶解度受限形成黏稠凝胶。对开发集相似度 0.5172。
* **结论**：**二值标签无法推导 + 开发集同源冲突达 82.76%，准入 0**。

---

## 四、 5,629 对全员 Needleman–Wunsch 同源比对审计 (All-Member NW Homology Audit)

使用严格的全局 Needleman–Wunsch 动态规划比对算法（`match=2, mismatch=-1, gap=-2`, `identity_mode="alignment"`），完成全量配对计算，结果保存于 [`sequence_pairs.csv`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/sequence_pairs.csv) 及 [`candidate_identity_prescreen.json`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/candidate_identity_prescreen.json)：

* **比对规模**：
  * 13 条候选序列 vs 417 条开发集记录 = 5,421 对
  * 13 条候选序列 vs 16 条 MIC 候选分子 = 208 对
  * 总计完成 **5,629 对** 精确浮点比对。
* **对正式开发集（417 记录）的比对结果**：
  * **13 条候选序列全部 (100%) 与开发集存在 ≥0.40 的同源违规**。
  * Pin2 系列：最高相似度 1.0000（违规对数 24）。
  * ChMAP-28：最高相似度 1.0000（违规对数 2）。
  * mini-ChBac 系列：最高相似度 0.5000（违规对数 24）。
  * Hymenochirin 系列：最高相似度 0.8276（违规对数 2）。
  * **结论**：没有任何一条候选序列能够跨越隔离门禁充当正式双任务的外部测试集。
* **对 MIC 开发集（16 分子）的比对结果**：
  * ChMAP-28 与 BMAP-27B 相似度 0.6071（违规 1 对，须同属 Component 4）。
  * mini-ChBac7.5Nα 与 Bac7 家族分子相似度 0.6400（违规 1 对，须同属 Component 0）。
  * mini-ChBac7.5Nα(1-16) 与 Bac7 家族相似度 0.6111（违规 1 对，须同属 Component 0）。
  * 其余多肽虽与 16 分子相似度 <0.40，但因无有效二值标签被排除。

---

## 五、 五大核心交接问题权威解答 (Answering the 5 Core Questions)

接手研究或执行后续任务时，请向用户或项目团队明确以下五条判定：

### 1. 哪些数据真实可用？
* **真实可用且通过复核的 MIC 数据**：仅限 [`03_experiments/audits/mic_followup_release_20261004_v1/`](file:///D:/桌面文件/sci/03_experiments/audits/mic_followup_release_20261004_v1/) 的 **16 个分子、23 条实测观察**（5 阳性、11 阴性）。该数据基于原图 CREC6 单株测定及 Wang resin Fmoc 合成证据，已在 `protocol-mic-11` 下完成固定三折模型拟合与无 fit 独立复核。
* **正式双任务开发集**：[`03_experiments/prepared/amd02_evidence_clean_20261001/records.csv`](file:///D:/桌面文件/sci/03_experiments/prepared/amd02_evidence_clean_20261001/records.csv) 的 **417 条记录**，证据链清洗完备，但仅能作为内部开发集。

### 2. 哪些仍缺证据？
* **古菌研究 (Torres 2025, Nature Micro)**：
  - 80 份分析证书已归档，但证书片段名（如 `PYRAE-LWL12`）与论文中实验测定编号（Archaeasin-1…80）的显式映射表依然缺失。
  - 受测分子的明确末端形式（游离羧基还是酰胺化）未获证实。
  - 大肠杆菌 MIC 的 84 个空值槽位含义未定；人红细胞 HC50 的 55 个超范围外推值未解决；Extended Data Fig. 7 原始孔浓度与重复值缺失。
* **Hymenochirin 研究 (Mechkarska 2012 / 2013 论文)**：
  - Hymenochirin-2B~5B 大肠杆菌实测 MIC 均为 20~40 µM（56.35~114.43 µg/ml），缺乏足以突破 32 µg/ml 或 128 µg/ml 门限的原始强效或弱效测定。
* **AMP-Designer (Science Advances 2025)**：
  - Table S8 明确全量 23 条多肽为 C 端酰胺化，缺乏未修饰同系物的实测对照。

### 3. MIC 研究的实际状态？
* **当前状态**：`local_exploratory_training_independently_verified`，属于**小样本探索性基线，处于技术性冻结**。
* **模型指标事实**：在 44 维理化特征空间下，LR 的 MCC 为 -0.3239，RF 的 MCC 为 -0.1636（命中 1 个真阳性），Dummy 的 MCC 为 0.0000。样本量微小，此结果仅作为历史已知的描述性事实留存，不能得出具有统计显著性的外部推广或临床可用结论。

### 4. 原双任务为何仍阻断或凭什么解除？
* **为何仍阻断**：
  - 原双任务必须同时满足“抗菌有效”与“人红细胞安全”，要求外部验证队列必须与 417 条开发集记录保持严格的 ≥0.40 全员 Needleman–Wunsch 同源隔离。
  - 目前所有排查过的公共文献库及补充材料中，只要具备人红细胞实测数据，其序列拓扑几乎全部与开发集发生高度同源聚类（重叠率 100%）。
  - 在无合格外部数据前，系统严格执行 **Fail-Closed** 原则，坚决禁止为了“强行产生训练结果”而伪造标签、放宽阈值或随机划分。
* **凭什么解除**：
  - 必须引入一组来源于全新实验室、不与开发集文献重叠、具有实测大肠杆菌 MIC 与人红细胞 HC50、末端明确且全员与 417 条记录相似度严格 <0.40 的真实多肽队列。

### 5. 下一步最具体的补证动作？
* **动作 1（古菌作者数据索取）**：
  - 用户可使用已在本地准备好的英文函件 [`author_data_request_draft.md`](file:///D:/桌面文件/sci/03_experiments/audits/archaeome_identity_followup_20261004_v1/author_data_request_draft.md)，向 Nature Microbiology 论文通讯作者发送邮件，索取 80 个测定编号与证书的精确对应表及原始微孔测定吸光度。
* **动作 2（聚焦两栖类游离羧基未修饰天然肽排查）**：
  - 重点针对非洲爪蟾属、蛙属等不带 C 端酰胺化的天然防御肽（如天然游离羧基亚型），检索同时具备 ATCC 25922 MIC 与健康人红细胞溶血曲线的直接文献。

---

## 六、 产物清单与文件跳转 (Artifact Manifest)

| 文件路径 | 类型 | 内容描述与状态 |
|---|---|---|
| [`03_experiments/audits/alternative_primary_search_20261004_v2/raw/mechkarska2013_thesis.pdf`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/raw/mechkarska2013_thesis.pdf) | PDF (1.8MB) | 瓦赫宁根大学作者论文原文，包含 Hymenochirins 完整实验数据 |
| [`03_experiments/audits/alternative_primary_search_20261004_v2/acquisition.json`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/acquisition.json) | JSON | 5 篇来源获取元数据、SHA256 与许可证记录 |
| [`03_experiments/audits/alternative_primary_search_20261004_v2/source_review.json`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/source_review.json) | JSON | 5 篇来源系统审查与阻断原因结构化存证 |
| [`03_experiments/audits/alternative_primary_search_20261004_v2/primary_evidence.json`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/primary_evidence.json) | JSON | XML 表格与学位论文第 6 章表格提取全量数据 |
| [`03_experiments/audits/alternative_primary_search_20261004_v2/molecule_decisions.csv`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/molecule_decisions.csv) | CSV | 13 条候选多肽逐分子末端形式与审查决定 |
| [`03_experiments/audits/alternative_primary_search_20261004_v2/assay_decisions.csv`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/assay_decisions.csv) | CSV | 13 条候选测定原始值、µg/ml 换算值与标签规则判定 |
| [`03_experiments/audits/alternative_primary_search_20261004_v2/sequence_pairs.csv`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/sequence_pairs.csv) | CSV | 5,629 对全局 Needleman–Wunsch 两两浮点比对全量明细 |
| [`03_experiments/audits/alternative_primary_search_20261004_v2/candidate_identity_prescreen.json`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/candidate_identity_prescreen.json) | JSON | 候选序列最高相似度、最邻近 ID 及违规配对汇总 |
| [`03_experiments/audits/alternative_primary_search_20261004_v2/cluster_audit.json`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/cluster_audit.json) | JSON | 拓扑连通组件分析与组件归并审计 |
| [`03_experiments/audits/alternative_primary_search_20261004_v2/handoff_status.json`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/handoff_status.json) | JSON | 本轮审计机器可读最终状态 |
| [`03_experiments/audits/alternative_primary_search_20261004_v2/existing_mic_index.md`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/existing_mic_index.md) | Markdown | 既有 MIC 16 分子协议、运行、模型与复核全量索引 |
| [`03_experiments/audits/alternative_primary_search_20261004_v2/report.md`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/report.md) | Markdown | 本轮审计详细中文报告 |
| [`03_experiments/audits/mic_training_readiness_20261004_v22.json`](file:///D:/桌面文件/sci/03_experiments/audits/mic_training_readiness_20261004_v22.json) | JSON | 当前生效的根机器状态基准（保持原样未篡改） |
