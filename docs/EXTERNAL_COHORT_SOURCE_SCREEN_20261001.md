# 独立外部队列来源筛查（2026-10-01）

## 结论

本轮没有找到可按冻结的 `protocol-amd-02` 纳入正式外部队列的来源。机器状态保持 `blocked`；正式模型实验未启动，也没有正式结果。筛查对象是能同时提供 *E. coli* MIC 与人红细胞 HC50 的原始研究。只有论文层面的候选筛查，不代表对这些研究的每条肽记录完成了正式逐条导入与审计。

正式纳入仍要求原始实验数值、单位、条件、对象及可核查引文；标签只能按既定测定规则重算。序列须为 10–50 aa、未修饰线性肽，并与开发集在论文来源及协议定义的全成员序列一致性检查中独立。不得以数据库汇总标签替代原始测定，不得为通过门禁放宽 0.40 阈值或更改类别边界。

## 候选来源处置

| 原始研究 | 已报告的相关数据 | 处置与理由 |
|---|---|---|
| Pandi et al., 2023, “Cell-free biosynthesis combined with deep learning accelerates de novo-development of antimicrobial peptides”, DOI [10.1038/s41467-023-42434-9](https://doi.org/10.1038/s41467-023-42434-9)；[原文](https://pmc.ncbi.nlm.nih.gov/articles/PMC10632401/) | 22 条成功化学合成的设计肽；补充表 10 报告 *E. coli* MIC 与人红细胞 HC50，分别注明重复数和浓度单位。 | **排除。** 方法描述合成采用 TentaGel S RAM 树脂，属于 C 端酰胺化合成形式；不满足当前 `modifications = none` 门禁。不能把酰胺化形式改记为未修饰肽。 |
| Lee et al., 2015, “Antibiotic activity and structural analysis of the scorpion-derived antimicrobial peptide IsCT and its analogs”, DOI [10.1038/srep08585](https://doi.org/10.1038/srep08585)；[原文 PDF](https://www.nature.com/articles/srep09127.pdf) | IsCT 及三个序列类似物；表 3 给出人红细胞 HC50 与对 *E. coli* 的 MIC。 | **排除。** 表 1 的实测分子量/结构将四条肽都明确标为 C 端 `CONH2`，不符合未修饰形式门禁。 |
| Ratajczak et al., 2020, “Antimicrobial Peptides from Rat-Tailed Maggots of the Drone Fly *Eristalis tenax* Show Potent Activity against Multidrug-Resistant Gram-Negative Bacteria”, DOI [10.3390/microorganisms8050626](https://doi.org/10.3390/microorganisms8050626)；[原文](https://pmc.ncbi.nlm.nih.gov/articles/PMC7284870/) | 天然 EtCec 肽有 *E. coli* MIC；研究也做了人红细胞实验。 | **不能形成匹配观测。** 文中人红细胞溶血结果针对酰胺化形式，而表中的天然 EtCec MIC 形式与之不匹配；其他候选亦未提供同时匹配当前端点及修饰条件的完整记录。不可把不同化学形式的 MIC 和 HC50 拼成同一条记录。 |
| von Gundlach et al., 2021, “Rational Designed Hybrid Peptides Show up to a 6-Fold Increase in Antimicrobial Activity…”, DOI [10.3389/fphar.2021.769739](https://doi.org/10.3389/fphar.2021.769739)；[原文](https://www.frontiersin.org/journals/pharmacology/articles/10.3389/fphar.2021.769739/full) | 表 1 报告人红细胞 HC50 与 *E. coli* MIC，且给出序列及实验条件。 | **排除。** 论文明确注明所测肽全部为 C 端酰胺化。 |
| Conlon et al., 2004, “The ascaphins: a family of antimicrobial peptides from the skin secretions of the most primitive extant frog, *Ascaphus truei*”, DOI [10.1016/j.bbrc.2004.05.141](https://doi.org/10.1016/j.bbrc.2004.05.141)；[原文](https://carlosdavidson.org/wp-content/uploads/2023/06/conlon-ascaphin.pdf) | 表 1 中天然 ascaphin-3 和 ascaphin-7（自由 C 端羧基）有 *E. coli* MIC（6、3 μM）和人红细胞 HC50（均 `>200 μM`）。按项目分子量换算，MIC 为 14.904、7.677 μg/mL，HC50 下界为 496.790、511.812 μg/mL；端点本身足以推导两项二值标签。 | **排除。** `PMID 15207717` 已出现在开发记录 `DBAASP:2303`、`DBAASP:2302` 的来源中，违反独立研究来源条件。并且对全部 417 条开发成员执行协议定义的对齐后，最大一致性分别为 0.958333（开发记录 `DBAASP:2303`）和 0.708333（`DBAASP:25169`），均超过 0.40。不能因为端点可用而忽略来源和同源门禁。筛查了论文其余测量后，没有可替代且同时满足门禁的记录。 |

上述判定只回答这些研究能否作为当前正式队列来源，不否定其研究结论或肽的活性。搜索结果中还出现了只测固定浓度溶血、使用猪/羊红细胞、仅给 MHC 而非 HC50，或与 DBAASP 开发来源重叠的记录；这些不满足本项目的兼容端点或独立来源条件，因此未转成候选标签。

## 下一步

继续寻找能提供**同一化学形式**下原始 *E. coli* MIC 与人红细胞 HC50 的独立实验队列，并逐条核查 DOI/PMID、菌株、测定值、单位、培养/溶血条件及肽修饰。原始记录保存后先计算 SHA-256，再进入外部证据导入器；随后审查论文/来源重合，比较每条外部序列与全部 417 条开发成员，并核对类别和其他划分门禁。若最终队列不足或任一全员同源门禁失败，正式状态继续为 `blocked`。

本筛查报告是来源发现记录，不是新的队列、证据清单或正式准备产物。机器可读当前状态与协议摘要仍以 [`research_status.json`](../04_paper/research_status.json) 及其指向的准备清单为准。

2004 年原文 PDF 和两条候选原始观察的逐字结构化记录保存在 [`external_cohort_screen_20261001`](../03_experiments/audits/external_cohort_screen_20261001/)。`screen_manifest.json` 记录检索来源哈希、开发集哈希、协议摘要、单位换算、来源重合和全成员最大一致性。该目录明确标为 screen-only，候选没有写入正式外部队列。
