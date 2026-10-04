# 外部实验数据来源筛查

筛查日期：2026-10-01（Asia/Shanghai）  
冻结协议：`protocol-amd-02`，SHA-256 `6bcf8993a08f8da1ebae4609f4ef9e4ebae7205257d136dfa059a1b93db4bc4c`  
开发集：`amd02_evidence_clean_20261001`（417 条 DBAASP 开发记录）

## 结论

本轮全网文献筛查**没有得到可纳入正式外部队列的记录**。目前最接近要求的是 Wang et al. 2025 的 AI18、KW13：论文报告了 *E. coli* ATCC 25922 MIC（AI18 8、KW13 4 μg/mL）和人红细胞 HC50（两者均 `>1000 μg/mL`），且序列、单位及主要 MIC 条件可核验。但两条肽均为 C 端酰胺化；独立按冻结协议算法对照全部 417 条开发记录，AI18 的最大序列一致性为 0.474，KW13 为 0.500，均达到/超过 0.40 门槛。即使不考虑修饰，该来源也无法进入严格零泄漏队列。

因此没有创建带记录的外部 `records.csv`，也没有生成模型结果或解除阻断状态。原始候选材料与本筛查记录独立存放，正式状态仍为 `blocked`。

## 已筛查来源

| 来源 | 可用证据 | 判定 |
|---|---|---|
| Wang et al., Science Advances (2025), DOI `10.1126/sciadv.ads8932`, PMID 40043127 | AI18、KW13：标准株 *E. coli* ATCC 25922 MIC 分别 8/4 μg/mL；人红细胞 HC50 均 >1000 μg/mL。MIC 使用 CAMHB 微量肉汤稀释，37°C、16–20 h、最终约 5×10⁵ CFU/mL、三重复。序列为 `AIPKRLRRFYLRALARRL`、`KWKKWVRAIKKLV`。 | **排除**：两者 C 端酰胺化；全开发集最大身份 0.474/0.500；文章 CC BY-NC 4.0，非商业使用限制须单独纳入复用审查。原始来源：[期刊全文](https://doi.org/10.1126/sciadv.ads8932)、[PMC 许可与全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC13109931/)、[专利 AI18 末端修饰](https://patents.google.com/patent/CN117886889A/en)。 |
| Pandi et al., Nature Communications (2023), DOI `10.1038/s41467-023-42434-9`, PMID 37938588 | 补充表 10 有 22 条候选的 *E. coli* MIC 与人红细胞 HC50；测定条件与序列见补充材料。文章 CC BY 4.0。官方补充 PDF 已保存于 `raw/Pandi_2023_supplementary_information.pdf`，SHA-256 `c0afe2d35b4dae592c00333f86a3fe6d210ffd662e683973c6438925c2831ebf`。 | **排除**：合成使用 TentaGel S RAM / Rink amide 树脂，产物为 C 端酰胺，违反 `modifications=none`。来源：[期刊全文](https://doi.org/10.1038/s41467-023-42434-9)、[论文数据与补充材料](https://github.com/amirpandi/Deep_AMP)、[树脂产品说明](https://www.sigmaaldrich.com/PL/en/product/aldrich/86407)。 |
| HydrAMP, Nature Communications (2023), DOI `10.1038/s41467-023-36994-8` | 有新设计肽的 *E. coli* MIC 与红细胞 HC50，包含序列及定量值。 | **排除**：红细胞为羊来源，不是协议要求的人红细胞。来源：[全文及方法](https://pmc.ncbi.nlm.nih.gov/articles/PMC10017685/)。 |
| Tripathi et al., Scientific Reports (2015), DOI `10.1038/srep09127` | IsCT 与三个突变体有 *E. coli* MIC 和人红细胞 HC50；序列可核验。 | **排除**：全部 C 端酰胺化。来源：[论文全文](https://www.nature.com/articles/srep09127)。 |
| Conlon et al., BBRC (2004), DOI `10.1016/j.bbrc.2004.05.141` | 从天然蛙皮分泌物分离 ascaphins，报告 *E. coli* MIC、人红细胞 HC50 与序列；部分肽的末端状态需逐条依据质谱核实。 | **暂不纳入**：本轮尚未建立可复用许可、逐条端点及末端状态的数据级证据，也未抽取并审计全部原始记录。该论文可作为下一轮追查的原始来源线索，不能把数据库二次整理值替代原文。来源：[论文 PDF](https://carlosdavidson.org/wp-content/uploads/2023/06/conlon-ascaphin.pdf)。 |
| Dong et al., Frontiers in Microbiology (2018), DOI `10.3389/fmicb.2018.02832` | 新设计肽有 MIC 与红细胞数据。 | **排除**：明确为 C 端酰胺化。来源：[全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC6277555/)。 |
| ACS J. Med. Chem. (2018), DOI `10.1021/acs.jmedchem.7b01831` | SI 汇编许多肽的 *E. coli* MIC、HC50。 | **不作为来源**：这是跨论文训练集汇总，不是独立原始实验队列；需回溯每条记录对应原始论文后逐篇核验。来源：[论文与 SI](https://pubs.acs.org/doi/full/10.1021/acs.jmedchem.7b01831)。 |
| QMAP benchmark (2026), DOI `10.1038/s41598-026-56004-8` | 汇总大量 AMP 定量数据。 | **不作为外部来源**：其数据来自 DBAASP，不能满足相对当前开发集的来源独立性。可作为定位原始论文的索引。来源：[论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC13473575/)。 |

## 核验规则与搜索范围

- 只接受原始实验观察，不接受人工二值标签、分类数据库记录或模型预测。
- 同一记录需同时有可追溯序列、*E. coli* MIC、人红细胞 HC50、数值/单位、菌株/实验条件、原始论文，以及序列端点修饰证据。
- 按冻结协议阈值从原始观察推标签；修饰序列、物种不符、二手整理值或来源缺失者排除。
- 与 417 条开发集成员逐条比较，固定全局比对 identity 定义为相同残基数/比对列数；任何最大 identity ≥0.40 即排除。
- 搜索主题覆盖：`E. coli MIC human erythrocyte HC50 peptide sequence supplementary data`、`free acid/non-amidated antimicrobial peptide HC50 E. coli`、`original AMP assay human RBC MIC`，并追查上述研究的论文、补充材料、GitHub/数据附件、PMID/DOI 与许可。

## 后续可行路径

当前正式规则下，继续扩大同类 AMP 文献搜索不太可能解决本轮门禁，因为候选大多有 C 端酰胺化，而且已测序候选会受到全开发集 0.40 同源门禁约束。下一步应继续找具有**明确未修饰端点**的原始测定队列，并先批量执行全成员比对筛除，再投入逐条证据整理。若找不到足量独立记录，应如实维持 `blocked`；不能放宽同源阈值或把修饰肽当作未修饰肽。
