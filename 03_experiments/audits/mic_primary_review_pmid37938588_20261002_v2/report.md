# Pandi 等 2023 原始测定与分子形式冲突审计

[原论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC10632401/)；[出版方补充 PDF](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-023-42434-9/MediaObjects/41467_2023_42434_MOESM1_ESM.pdf)。Supplementary Table 10 的 *E. coli* MIC 与 2 条冻结测定数值相符；Supplementary Fig. 16–17 的合成信息给出对应完整序列，且均写明 C 端 `-CONH2`。

- 冻结 `records.csv` 两条均写 `modifications=none`；原始 DBAASP `cTerminus` 均为空。序列字母虽相同，受测分子的末端化学形式未被来源清单表达。
- 两条均暂时排除训练。只有在新版本来源与特征协议明确表达酰胺化、重新核对分子身份和重建隔离审计后，才能重新评估；不修改旧记录或旧协议。
