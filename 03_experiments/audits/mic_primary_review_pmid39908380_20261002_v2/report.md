# Wang 等 2025 原论文阴性候选冲突审计

[原论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC11797553/)；[原始补充包](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11797553/supplementaryFiles)。Supplementary Table S18 可核对 2 条序列；Table S5 的 *E. coli* GD004 MIC 均记 `>400 µM`，与 DBAASP 原始数值相同。正文明确 GD004 是临床来源菌株，但冻结数据库目标只写 *E. coli*，须在新来源版本中补齐。

正文 MIC Methods 声明肽浓度梯度为 1.5625–200 µM，与补充表 `>400 µM` 的右删失界限不一致。未找到解释前，不把这两条当作已核实阴性，也不计入五折候选；不以推断或改写阈值消除冲突。训练释放数为 0。
