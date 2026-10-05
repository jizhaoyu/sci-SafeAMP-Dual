# HC50 原文跟进：第一批

生成时间：2026-10-04T13:18:19.555911+00:00；数据版本：hc50_primary_followup_20261004_v1；协议：protocol-amd-02（未修改）。

## 本批结果

- 78 条固定候选，对应 41 个已核对 PMID 和 1 个无 PMID 来源；归档全部 41 个 PubMed 元数据响应。
- 获取 12 篇 XML 原文和 1 篇作者机构 PDF，共对 20 条候选完成端点筛查；58 条尚缺本批可审查全文。
- 原文找到 8 条明确的人红细胞 HC50 测定记录，来自 5 篇论文。这是原始测定观察数量，不是正式合格样本数量。
- 8 条均有已知环化、二硫键或酰胺化形式，不满足当前外部队列分子边界；部分完整序列图还待复核。
- 逐记录决定：8 条因已知分子形式排除于当前正式外部队列，70 条 pending；其中 58 条为获取缺口，12 条为已取得原文但未满足完整证据门禁。
- 新释放外部样本 0，新训练 0。原双任务仍 blocked；既有 MIC 探索性训练状态未改动。

## 人红细胞 HC50 原始记录

| 候选 | 原测定对象 | HC50 原值 | 原文位置 | 当前边界 |
|---|---|---|---|---|
| DBAASP_12233 | PM III | 46 µM | PMID 30486233, section 2.5; Fig. 2; section 4.5 | disulfide_bonded |
| DBAASP_13515 | AR-F | 60.5 µM | PMID 31234579, Table 3 HC50 row, AR-F column; hemolysis methods | disulfide_bonded |
| DBAASP_15043 | cd4(Q5K,D9K) | 10 µM | PMID 32153522, Table 2 HC50 column; section S4.SS12 | head_to_tail_cyclic |
| DBAASP_20562 | 3e [R3W7] | 60 µg/mL | PMID 36442155, Table 1 row 3e, HC50 column; section 4.4 | cyclic |
| DBAASP_20565 | 4c [R4W6] | 75 µg/mL | PMID 36442155, Table 1 row 4c, HC50 column; section 4.4 | cyclic |
| DBAASP_20571 | 7a [R7W4] | 190 µg/mL | PMID 36442155, Table 1 row 7a, HC50 column; section 4.4 | cyclic |
| DBAASP_20579 | 6a [R6W4] | 265 µg/mL | PMID 36442155, Table 1 row 6a, HC50 column; section 4.4 | cyclic |
| DBAASP_6545 | ECP(1–19), peptide 3 in Table 1 | 11.2 ± 0.1 µM | PMID 21696142, PDF page 3 Table 2 row 3; page 2 Table 1 row 3; page 5 methods | C_terminal_amide |

## 必须保留的冲突与缺口

- AI-hemocidin 2：表注 human 与方法/结果 murine 冲突；HC10 和单点溶血不是 HC50。
- A1P 和 AMPR-11：原文分别使用 sheep 和 mouse RBC。ToAP2 的人溶血曲线不从图估值；同篇真菌 MIC 不移作 E. coli MIC。
- AY1C/CAY1 及 AgNP 缀合物：Table 1 使用 MIC80% 端点，现行完全抑制规则不兼容；百分比溶血不能转为 HC50。
- CT7：128 µM 近 50% 未写为精确 HC50；1.5 h 图注与 120 min 方法冲突。
- Hermetia：人 RBC 行 IC50 是明确的溶血 50% 端点，可以作为下界线索；NHill 单独行/完整序列待 Supplementary Table S2，不借用另一分子的数值。
- ECP(1–19)：按 Table 1 序列匹配 Table 2 row 3，保留正文编号交换；PDF 方法用 Rink-amide，不遗漏酰胺化。
- Catesbeianin-1：原始 PubMed 摘要明确写 HC50 300 µg/mL，旧缺失声明被推翻；仍待全文核对，不将摘要直接释放。
- Brevinin-2-Ia：出版者核对 DOI 10.1007/s00049-019-00287-z；PMID 不猜填，测定行继续 pending。
- SLAY：Europe PMC 全文渠道失败，PMC 网页返回 challenge；这仅说明本次获取渠道未成功，不说明世界上不存在全文。

## 后续顺序

1. 优先取得 SLAY 的原文及补充表（14 条）、HD5 六条的原始测量表、鳟鱼五条的原始测量表。
2. 对 Catesbeianin-1、Brevinin-2-Ia 获取合法全文，核对分子形式、实验对象和数值。
3. 对已取得全文的 12 条 pending 按各自缺口补图、补表、核对端点；冲突未解除继续 pending。
4. 只有完整分子与测定证据复核后才能重建合格队列；随后重跑全员序列、论文别名和历史暴露隔离。

## 复核与复跑

本批是代理原文复核，不声称独立人工评审；摘要仅用于检索，未产生任何训练标签。
`scripts/review_sources.py --output <不存在的新目录>` 在运行前核对绑定摘要和覆盖；输出已存在时拒绝覆盖。
汇总来自 summary.json。原始文件、URL、获取时间、许可和失败记录见 acquisition/source_acquisition.csv；完整来源片段见 source_region_excerpts.json。
许可说明：Europe PMC 返回的许可证保留在获取表；作者机构 PDF 未核实开放再分发许可，不作为交付包再分发。
固定 0.40 全员门禁、原协议、历史数据、模型及机器状态保持原样；本轮未把库存相似度结果升级成正式零泄漏结论。
