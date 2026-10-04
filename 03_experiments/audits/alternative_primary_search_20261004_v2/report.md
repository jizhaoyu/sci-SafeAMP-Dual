# 替代原始测定检索与证据审查报告 (第二轮)

> **审计执行时间**：2026-10-04（Asia/Shanghai）  
> **审计目录**：[`03_experiments/audits/alternative_primary_search_20261004_v2/`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/)  
> **审查模式**：公开实测数据证据审查与全员同源拓扑隔离门禁（Agent Primary Source Review）  
> **机器基线**：[`03_experiments/audits/mic_training_readiness_20261004_v22.json`](file:///D:/桌面文件/sci/03_experiments/audits/mic_training_readiness_20261004_v22.json)  

---

## 核心结论先行 (Executive Summary)

* **新准入分子数**：**0**；**新释放二值标签数**：**0**；**新模型训练执行**：**否**（无新数据，严禁无故重训）。
* **MIC 单任务状态**：保持不变，基线为 16 分子、23 观察、固定三折 9 个模型，独立无 fit 复核通过（`status = local_exploratory_training_independently_verified`，`training_blocked = false`）。
* **原双任务状态**：严格阻断（`formal_dual_task_status = blocked`，`formal_results_available = false`，`publication_ready = false`）。
* **本轮突破性发现**：
  * **成功获取并解析瓦赫宁根大学作者学位论文原文**（`mechkarska2013_thesis.pdf`，1,803,832 字节，SHA256: `25885f2e02aaadba1929c4723570104dc95520964dd6e4b3698e9562fe9f1da4`），完整提取第 6 章原始实验表（Table 1）与序列质谱表（Fig. 4）。
  * 证实 Hymenochirin-1B 为 C 端酰胺化（`-NH2`），超出当前未修饰分子范围；Hymenochirin-2B 至 5B 的大肠杆菌实测 MIC 均为 20~40 µM（对应 56.35~114.43 µg/ml），**全部落入 32 < MIC < 128 µg/ml 的中间不确定区间**，依科学规程无法导出二值标签；且 5 条序列跨队列比对正式开发集 417 条记录时，同源相似度高达 0.5172~0.8276，均严重违反 ≥0.40 隔离门禁。
  * 山羊抗菌肽研究（PMC6284057）实测数据虽然真实存在，但其直接命中正式开发集已知来源（DBAASP:12306 第一原始参考文献），且 ChMAP-28 与现有 MIC 成员 BMAP-27B 同源性达 0.6071（必须同组件），mini-ChBac 与 Component 0（Bac7 家族）同源性达 0.6400 且对开发集有 24 处同源冲突。
  * 蝎毒素 Pandinin 2 系列突变体实测 MIC（12.5~25 µM，对应 32.15~68.16 µg/ml）同样全数落入中间不确定区间，且与正式开发集 DBAASP:948 存在 100% 同源重叠。

---

## 阶段 A：现状核验 (Status Verification)

1. **状态核验依据**：读取最新机器状态 [`03_experiments/audits/mic_training_readiness_20261004_v22.json`](file:///D:/桌面文件/sci/03_experiments/audits/mic_training_readiness_20261004_v22.json)。
2. **MIC 单任务**：
   - 训练协议为 `protocol-mic-11`，绑定队列包含 16 个分子、23 条实测观察（5 个阳性、11 个阴性）。
   - 7 个连通组件，固定 seed=42 三折划分，各折训练集和验证集均含两类，跨折同源边严格为 0。
   - 9 个折模型（LR、RF、Dummy）已训练，48 行 OOF 样本外预测已落盘，无 fit 独立复核结果保存在 [`03_experiments/audits/mic_followup_run_validation_20261004_v2.json`](file:///D:/桌面文件/sci/03_experiments/audits/mic_followup_run_validation_20261004_v2.json)。
   - `training_blocked = false`。
3. **原双任务（MIC + 人红细胞 HC50）**：
   - 依据 `protocol-amd-02` 与 [`04_paper/research_status.json`](file:///D:/桌面文件/sci/04_paper/research_status.json)，由于 417 条开发集记录缺乏能通过 ≥0.40 全员同源隔离的独立外部队列，`formal_dual_task_status = blocked`，`run_status = none`，`formal_results_available = false`，`publication_ready = false`。
4. **既有成果索引**：已整理形成独立文档 [`existing_mic_index.md`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/existing_mic_index.md)。

---

## 阶段 B：分批公开来源检索 (Batch Open Source Search)

本轮重点排查 5 篇具有原始湿实验测定的公开论文，避免依赖未回复的邮件或间接综述：

| 来源 ID | DOI / 出处 | 文档格式与位置 | 许可证 | 检索依据与目标分子 |
|---|---|---|---|---|
| `pandinin2014` | `10.1371/journal.pone.0101742` (PMC4096598) | JATS XML | CC BY 4.0 | 探讨野生型 Pin2 及 4 种合成变体的大肠杆菌实测 MIC 与人 RBC 溶血 |
| `corvus2023` | `10.1038/s41598-023-45875-w` (PMC10618271) | JATS XML | CC BY 4.0 | 家鸦转录组预测 AMP 的重组/合成实测活性 |
| `chmap2018` | `10.3389/fphar.2018.01501` (PMC6308165) | JATS XML | CC BY 4.0 | 山羊抗菌肽 ChMAP-28 的抗肿瘤活性 |
| `goat_antibacterial2018` | `10.3389/fmicb.2018.02983` (PMC6284057) | JATS XML | CC BY 4.0 | 山羊抗菌肽（ChMAP-28、mini-ChBac7.5Nα 及其短片段）大肠杆菌微量肉汤稀释法实测 MIC 与人 RBC 溶血 |
| `hymenochirin2012` | `10.1016/j.peptides.2012.03.029` (PMID 22497805)；瓦赫宁根大学论文库 `https://edepot.wur.nl/255770` 第 6 章 | PDF (226页，正文第6章) | Open Access Thesis | 侏儒爪蟾天然抗菌肽 Hymenochirin-1B~5B 的原始化学结构（MALDI-TOF）、大肠杆菌实测 MIC 与人红细胞 LC50 |

---

## 阶段 C：逐观察审查 (Per-Observation Audit)

所有 13 条候选多肽分子的化学形式、端点实测值、单位转换与标签规则判定详见下表：

| 候选分子名 | 来源 | 序列 (长度) | N/C 端化学形式 | 大肠杆菌实测 MIC (原始单位) | 换算值 (µg/ml) | 标签规则判定 (≤32 阳, ≥128 阴) | 准入判定 | 排除 / 阻断具体原因 |
|---|---|---|---|---|---|---|---|---|
| Pin2 | pandinin2014 | `FWGALAKGALKLIPSLFSSFSKKD` (24) | 游离羧基 | MHB: 12.5 µM | 32.65 | 中间值 (32 < MIC < 128) | 排除 | 换算值 32.65 µg/ml 越过 32 上界；无二值标签；与 DBAASP:948 100% 同源重叠 |
| Pin2 [G] | pandinin2014 | `FWGALAKGALKLIGSLFSSFSKKD` (24) | 游离羧基 | MHB: 12.5 µM | 32.15 | 中间值 (32 < MIC < 128) | 排除 | 换算值 32.15 µg/ml 越过 32 上界；无二值标签；与 DBAASP:948 重叠 |
| Pin2 [GPG] | pandinin2014 | `FWGALAKGALKLIGPGSLFSSFSKKD` (26) | 游离羧基 | MHB: 12.5 µM | 34.08 | 中间值 (32 < MIC < 128) | 排除 | 换算值 34.08 µg/ml 落入中间区间；无二值标签 |
| Pin2 [14] | pandinin2014 | `FWGLKGLKKFSKKL` (14) | 游离羧基 | MHB: 25.0 µM | 42.33 | 中间值 (32 < MIC < 128) | 排除 | 换算值 42.33 µg/ml 落入中间区间；无二值标签 |
| Pin2 [17] | pandinin2014 | `FWGALAKGLKKFSKKL` (16) | 游离羧基 | MHB: >25.0 µM | 46.23 | 中间值 / 删失值 | 排除 | 删失不确定值；无二值标签 |
| CS-AMP 序列群 | corvus2023 | 多个 (15~35) | C 端酰胺化 | 表内多个 | - | 排除 | 排除 | 方法学明确使用 Rink Amide 树脂合成，属修饰肽，不符合未修饰线性肽范围 |
| ChMAP-28 | chmap2018 | `GRFKRFRKKLKRLWHKVGPFVGPILHY` (27) | 游离羧基 | 未测 | - | 缺失 | 排除 | 肿瘤细胞 IC50 测定，无原始大肠杆菌 MIC 表 |
| ChMAP-28 | goat2018 | `GRFKRFRKKLKRLWHKVGPFVGPILHY` (27) | 游离羧基 (CNBr切割) | C600: 0.06 µM (无盐) / 0.125 µM (生理盐) | 0.20 / 0.42 | 阳性 (≤32) | 阻断 | 命中开发集 DBAASP:12306 第一参考文献；与 BMAP-27B 同源 0.6071，须同组件 |
| mini-ChBac7.5Nα | goat2018 | `RRLRPRRPRLPRPRPRPRPRPR` (22) | 游离羧基 (CNBr切割) | C600: 2.0 µM (无盐) / 4.0 µM (生理盐) | 5.82 / 11.64 | 阳性 (≤32) | 阻断 | 对开发集有 24 处同源冲突；与 MIC Component 0 同源 0.6400，须归并入老组件 |
| mini-ChBac7.5Nα(1-16) | goat2018 | `RRLRPRRPRLPRPRPR` (16) | 游离羧基 (CNBr切割) | C600: 2.0 µM (无盐) / 16.0 µM (生理盐) | 4.27 / 34.12 | 盐敏感波动 | 阻断 | 生理盐下活性降至 34.12 µg/ml (中间值)；与 Component 0 同源 0.6111 |
| Hymenochirin-1B | hymenochirin2012 | `IKLSPETKDNLKKVLKGAIKGAIAVAKMV` (29) | C 端 α-酰胺化 (`.NH2`) | ATCC 25726: 20 µM | 61.24 | 排除 | 排除 | 质谱与序列明确为 C 端酰胺化修饰分子，超出未修饰线性肽范围 |
| Hymenochirin-2B | hymenochirin2012 | `LKIPGFVKDTLKKVAKGIFSAVAGAMTPS` (29) | 游离羧基 | ATCC 25726: 20 µM | 59.47 | 中间值 (32 < MIC < 128) | 排除 | 换算值 59.47 µg/ml 落入中间区间，无二值标签；对开发集 DBAASP:14150 相似度 0.8276 |
| Hymenochirin-3B | hymenochirin2012 | `IKIPAVVKDTLKKVAKGVLSAVAGALTQ` (28) | 游离羧基 | ATCC 25726: 20 µM | 56.35 | 中间值 (32 < MIC < 128) | 排除 | 换算值 56.35 µg/ml 落入中间区间；对开发集相似度 0.6552 |
| Hymenochirin-4B | hymenochirin2012 | `IKIPAFVKDTLKKVAKGVISAVAGALTQ` (28) | 游离羧基 | ATCC 25726: 20 µM | 57.31 | 中间值 (32 < MIC < 128) | 排除 | 换算值 57.31 µg/ml 落入中间区间；对开发集相似度 0.6897 |
| Hymenochirin-5B | hymenochirin2012 | `IKIPPIVKDTLKKVAKGVLSTIAGALST` (28) | 游离羧基 | ATCC 25726: 40 µM | 114.43 | 中间值 (32 < MIC < 128) | 排除 | 换算值 114.43 µg/ml 落入中间区间；溶解度受限凝胶化；对开发集相似度 0.5172 |

---

## 阶段 D：队列门禁与全员同源审计 (Cohort Gating & Homology Audit)

采用项目标准全局 Needleman–Wunsch 比对（match=2, mismatch=-1, gap=-2，alignment 模式），对 13 条候选序列与两组基准队列开展全对齐两两计算（合计完成 **5,629 对**，记录于 [`sequence_pairs.csv`](file:///D:/桌面文件/sci/03_experiments/audits/alternative_primary_search_20261004_v2/sequence_pairs.csv)）：

```
┌────────────────────────────────────────────────────────┐
│                   全员同源审计结果摘要                   │
├──────────────────────┬─────────────┬──────────┬────────┤
│ 候选多肽             │ 对正式 417  │ 违规对数 │ 对 MIC │
│                      │ 最高相似度  │ (≥0.40)  │ 相似度 │
├──────────────────────┼─────────────┼──────────┼────────┤
│ Pin2                 │ 1.0000      │ 24       │ 0.3333 │
│ Pin2 [G]             │ 0.9583      │ 24       │ 0.3333 │
│ Pin2 [GPG]           │ 0.9231      │ 24       │ 0.3077 │
│ Pin2 [14]            │ 0.5833      │ 6        │ 0.3889 │
│ Pin2 [17]            │ 0.6667      │ 12       │ 0.3684 │
│ ChMAP-28             │ 1.0000      │ 2        │ 0.6071 │ (命中 BMAP-27B)
│ mini-ChBac7.5Nα      │ 0.5000      │ 24       │ 0.6400 │ (命中 Bac7 家族)
│ mini-ChBac7.5Nα(1-16)│ 0.4444      │ 24       │ 0.6111 │ (命中 Bac7 家族)
│ Hymenochirin-1B      │ 0.4118      │ 2        │ 0.3793 │
│ Hymenochirin-2B      │ 0.8276      │ 2        │ 0.3103 │ (命中 DBAASP:14150)
│ Hymenochirin-3B      │ 0.6552      │ 1        │ 0.3571 │
│ Hymenochirin-4B      │ 0.6897      │ 1        │ 0.3571 │
│ Hymenochirin-5B      │ 0.5172      │ 2        │ 0.3214 │
└──────────────────────┴─────────────┴──────────┴────────┘
```

### 拓扑图聚类与同源阻断分析
1. **原双任务独立外部队列全军覆没**：
   - 13 条候选序列中，**100% (13/13)** 对正式开发集（417 记录）的最高相似度均超过了 0.40 门禁（最低 0.4118，最高 1.0000）。
   - 这意味着，没有任何一条候选能够作为不受开发集同源影响的独立外部验证样本。
2. **MIC 扩充组件坍缩风险**：
   - ChMAP-28（0.6071）必须与 BMAP-27B 合并归入 Component 4。
   - mini-ChBac（0.6400）必须与 `3e656d2ae8d48ae33078fcd4` 等合并归入 Component 0。
   - 它们不能产生独立的新实验组件；强行纳入只会加剧组件样本不均衡，且 mini-ChBac 具有强盐敏感性（0.9% NaCl 下 MIC 急剧恶化）。

---

## 阶段 E：后续训练或阻断确认 (Training Execution Decision)

依据既定科学协议规范：
- 本轮**新增准入分子为 0**，**新释放标签为 0**。
- 当前有效数据集队列与 `protocol-mic-11` 下的 16 分子基线完全一致，未发生任何改变。
- **决定**：严格复用既有训练结果，坚决不启动新的模型拟合（Zero-Fit Discipline）。不虚假占用新协议编号，不覆盖已冻结的 9 个折模型和 48 条 OOF 记录。

---

## 终审回答：交接提示词五大核心问题

### 1. 哪些数据真实可用？
* **真实可用且通过独立复核的 MIC 数据**：仅限 [`03_experiments/audits/mic_followup_release_20261004_v1/`](file:///D:/桌面文件/sci/03_experiments/audits/mic_followup_release_20261004_v1/) 中的 **16 个分子、23 条实测观察**（5 阳性、11 阴性）。该数据基于 BMAP-27B 原图 CREC6 单株测定及前序审查准入，已在 `protocol-mic-11` 下完成固定三折基线训练并经无 fit 独立复核。
* **正式双任务开发集**：[`03_experiments/prepared/amd02_evidence_clean_20261001/records.csv`](file:///D:/桌面文件/sci/03_experiments/prepared/amd02_evidence_clean_20261001/records.csv) 的 **417 条开发集记录**，证据链清洗完备，但仅作为开发集保留。

### 2. 哪些仍缺证据？
* **古菌研究 (Archaeome 2025, Nature Micro)**：
  - 80 份分析证书已取得，但证书片段名与论文中 Archaeasin-1…80 测定编号的映射关系依然缺失。
  - 受测分子的明确末端形式（是否游离羧基）尚未获得质谱或合成规程确认。
  - 240 个大肠杆菌 MIC 槽位中有 84 个空值；人红细胞 HC50 数据中存在 55 个超范围外推拟合值；原图剂量响应数据缺失。
* **Hymenochirin 研究 (Peptides 2012 / 学位论文第 6 章)**：
  - Hymenochirin-1B 为 C 端酰胺化；Hymenochirin-2B~5B 大肠杆菌实测 MIC 为 20~40 µM（56.35~114.43 µg/ml），缺乏足以判定为阳性（≤32 µg/ml）或阴性（≥128 µg/ml）的明确端点证据。
* **AMP-Designer (Science Advances 2025)**：
  - Table S8 明确全量 23 条多肽均为 C 端酰胺化，缺乏天然未修饰形式的实测数据。

### 3. MIC 研究的实际状态？
* **实际状态**：**已完成探索性验证的小样本基线，处于冻结就绪状态**（`status = local_exploratory_training_independently_verified`）。
* **技术细节**：16 个分子基于 44 维理化特征构建了 LR、RF、Dummy 三折基线。RF 实现 1 个真阳性（MCC = -0.1636），受限于样本量微小，该性能仅作为历史已知的描述性事实留存，不具备外部统计推广意义。

### 4. 原双任务为何仍阻断或凭什么解除？
* **为何仍阻断**：
  - 原双任务（MIC + 人红细胞 HC50）要求外部验证队列必须与全部 417 条开发集记录保持 ≥0.40 全员 Needleman–Wunsch 同源隔离。
  - 历经 DRAMP（6,107 条）、AMP-Designer、Archaeome（80 条）、Pandinin、ChMAP、山羊抗菌肽及 Hymenochirin 等多轮筛选，所有候选外部序列对开发集的最高相似度均超过 0.40，跨队列同源泄漏率达 100%。
  - 在没有满足物理测定完整性、端点二值化规则及零泄漏拓扑隔离前，系统严格执行 **Fail-Closed** 安全门禁。
* **凭什么解除**：
  - 必须取得一组完全来源于独立实验室、未收录于开发集、具有确凿人红细胞实测 HC50 和大肠杆菌实测 MIC、末端为游离酸/氨基且全员序列对 417 条记录相似度严格 <0.40 的多肽测定。

### 5. 下一步最具体的补证动作？
* **第一优先动作（古菌论文作者核实）**：
  - 使用已就绪的草稿 [`author_data_request_draft.md`](file:///D:/桌面文件/sci/03_experiments/audits/archaeome_identity_followup_20261004_v1/author_data_request_draft.md)，由用户向 Nature Microbiology 作者（Torres 等）发送数据核实邮件，索取 80 个实验编号与证书的精确对应表、末端合成规格书以及原始微孔吸光度数据。
* **第二优先动作（扩充公共未修饰来源筛选）**：
  - 锁定专注两栖类天然宿主防御肽（未酰胺化亚型，如 Magainin、Brevinin、Temporin 游离羧基亚型）的原始纯化文献，检索具完整 ATCC 25922 MIC 与健康人红细胞 50% 溶血测定的直接文献。
