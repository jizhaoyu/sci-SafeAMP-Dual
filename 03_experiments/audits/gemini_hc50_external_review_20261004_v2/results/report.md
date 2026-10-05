# HC50 与外部候选证据修复报告 v2

生成时间：`2026-10-04T12:43:07.114078+00:00`；原正式协议：`protocol-amd-02`；输入摘要：`e08370d9a391a849aa690470dc7574b13b07130727727daa76d60330b57d0e85`。

## 当前结论

原正式双任务保持 **blocked**。已核查人红细胞 HC50 为 **1 条**；完整准入外部候选为 **0 条**。这是一轮代理原文复核，未完成独立人工审批。模型 fit 为 0；没有修改正式研究状态。

## 范围和统计

- 本轮没有重新联网检索；修复已有五份 XML 和候选清单。历史检索响应和命中数量没有重新验证，见 search_log.csv。
- 候选记录 83；非空序列种类 75；原文已确认序列 4；受测序列缺失 1。
- 待原文复核 78 条，包含全部历史 DRAMP 和 DBAASP 线索；不能写成已经逐条复核原始测定。
- 测定/缺失端点记录 168 条，不等于独立实验次数。
- 候选—开发集比较 34194 对；候选内部比较 3321 对。缺失序列未参与比对。
- 对非空清单序列的暂定筛查：26 条达到 ≥0.40；56 条低于 0.40。未复核序列的结果是线索筛查，不证明正式科学隔离通过。
- 检出研究别名重叠 3 条。其余仍待原始测量论文、别名和历史研究暴露复核；不把“未发现重叠”写成独立性通过。

## 五篇原文记录

| 对象 | 原文序列 | 端点、实验对象和位置 |
|---|---|---|
| Dermatoxin-PD1 | SLGSFLKGVGKGLATVGKIVADQFGKLLEAGK | MIC: 4 µM，Escherichia coli ATCC 8739，位置 `molecules-31-02748-t002/E. coliATCC 8739/Dermatoxin-PD1/MIC`; MIC: 2 µM，Escherichia coli NCTC 13846，位置 `molecules-31-02748-t002/E. coliNCTC 13846/Dermatoxin-PD1/MIC`; MIC: 2 µM，Escherichia coli ATCC 2340，位置 `molecules-31-02748-t002/E. coliATCC 2340/Dermatoxin-PD1/MIC`; HC50: 46.47 µM，Horse erythrocytes，位置 `molecules-31-02748-t004/Dermatoxin-PD1/HC50; sec4dot11dot1-molecules-31-02748` |
| D-TN6 | RLLRLLLRLLR | MIC: 1 µg/ml，Escherichia coli ATCC 25922，位置 `antibiotics-15-00813-t001/D-TN6/E. coli ATCC 25922`; not_reported: 未取得 ，RBC assay not found in reviewed XML，位置 `reviewed XML; IC50 cell assays are not RBC HC50` |
| Arg2MP-C | LRLKALLAVAKKIL | MIC: 2 µM，Escherichia coli; Table 2 does not state strain ID，位置 `T2/E. coli/Arg2MP-C/MIC`; HC50: 372.3 ± 35.57 µM，Rabbit erythrocytes，位置 `Results HC50 paragraph/Arg2MP-C; s2-6-2` |
| Han-Def1/rDef1 | 待确认受测构建体序列 | MIC: No effect ，Escherichia coli (CMCC 44102)，位置 `tab1/Escherichia coli/Def1/MIC`; HC50: >750 µg/ml，Sheep erythrocytes，位置 `sec22/HC50 >750 ug/mL` |
| Brevinin-1 E8.13 | FLGALFKVASKLVPAAICSFSKKC | MIC: >24.8 µM，Escherichia coli hospital isolate; individual isolate ID not reported，位置 `cimb-47-00673-t003/Brevinin-1 E8.13/E. coli`; HC50: 41.87 µM，Human erythrocytes，位置 `sec3dot6-cimb-47-00673/HC50; Figure 7` |

Dermatoxin 和 Arg2MP-C 序列、MIC 均从原文表格提取；保留 Dermatoxin 全部三条 E. coli 测定。Arg2MP-C 使用兔红细胞。Han-Def1 的 E. coli 原文为 No effect，不补写有限 MIC；受测重组构建体序列尚未从归档资料确认。

## HC50 证据池与外部资格

Brevinin-1 E8.13：原文 HC50 41.87 µM，原文表 1 分子量用于估算质量浓度，约 105.90 µg/mL；MIC >24.8 µM，下界约 62.72 µg/mL、上界无穷。两项标签均为 unknown。质量定义未明确，转换仅作本次证据描述。合成方法报告 C 端酰胺化；Rana-box 为文中结构描述，本轮未独立确认共价配对。记录不具备原协议外部资格。

不能根据这轮有限审查推断全网不存在合格样本，也没有依据声明酰胺化占比 80%。待核实、原文未获取与明确不合格分别记录，不互相替代。

## 复现与下一步

README.md 包含固定输入摘要及命令。流水线拒绝任何已存在输出目录；新运行使用新目录。manifest.json 绑定输入、脚本、CSV、报告和 README。原 v1 与 MIC 冻结材料保留原样。

下一步是对 78 条待核实线索补齐原始测定表、化学身份、单位和原始研究归属，核实 Han-Def1 受测构建体序列及历史论文暴露。任何一个必要门禁未完成都不释放正式外部队列。
