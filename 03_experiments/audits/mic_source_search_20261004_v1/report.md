# MIC 与人红细胞 HC50 来源搜索：第一轮

审查日期：2026-10-04（Asia/Shanghai）。精确获取时间与文件 SHA256 见 acquisition 文件；分析生成时间见 `inspection_v2/inspection.json`。

## 结论

找到真实实验来源，当前还没有新增通过全部门禁的分子。已经保存 8 篇原文 XML，并取得古菌研究的两个有效原始工作簿。搜索通过通用网页检索、PubMed/PMC、Europe PMC、期刊原站、GitHub、Hugging Face 和 Mendeley Data 线索进行；不是穷尽式系统综述。

优先继续核查两个 2025 年原始实验研究。它们的 DOI/PMID 未在当前 417 条正式开发记录及 MIC 已释放来源中命中。此检查只表示未发现这些精确标识重叠；完整别名、受测分子和全员同源审计仍未完成，不能称为已确认的独立外部队列。

## 优先来源

### 1. 古菌蛋白组实验研究

[Torres 等，Nature Microbiology 2025](https://doi.org/10.1038/s41564-025-02061-0)，PMID 40796684，PMCID PMC12408343。论文许可证 CC BY 4.0。

- 已取得原文 XML、Source Data Fig. 2 和 Source Data Fig. 4。
- `41564_2025_2061_MOESM8_ESM.xlsx` 的 `Fig 2a` 有 80 个实验 ID。C、D、E 列分别是三个 E. coli 对象；240 个槽位中 156 个是非空原始 MIC 数字，84 个为空。空值没有填成 0、64、128 或阴性。
- `41564_2025_2061_MOESM10_ESM.xlsx` 的 `Fig 4c` 提供 80 个作者 HC50 线性拟合输出。保留原始值、单位和坐标，没有生成标签。55 个超过图注的 64 µM 测量上界，13 个大于 1,000,000 µM；这些超范围拟合不能作为精确实验端点直接释放。
- 原始工作簿把 `Archaeasin` 写成 `Archeasin`，仅在唯一 ID 连接时记录明确的拼写映射；没有按行号猜测分子。
- 本文主图 HC50 面板标记与工作簿工作表名称有差异；方法与扩展图的浓度范围也存在不同描述，记录为待核实。
- 已下载的 Supplementary Data 2 有 265 条预测序列和预测 MIC；整张表排除于实验端点释放，不能把预测行顺序对应到 80 个实验 ID。
- 受测分子序列及末端形式需要分析证书。论文指向 [Mendeley Data v3](https://data.mendeley.com/datasets/d8yzgtdrcp/3)，另检索到 [v5](https://data.mendeley.com/datasets/d8yzgtdrcp/5)。页面/公开文件列表请求返回 HTTP 403，尚未取得证书，不假设其内容。
- Extended Data Fig. 7 的下载响应是 HTML，虽然 URL 以 `.xlsx` 结尾，已识别并拒绝作为工作簿解析。

**当前决定：高优先级待核实；准入 0。** 获取证书、原剂量响应和正确 ID 映射后，才可进行分子身份、端点范围及全员隔离审计。

### 2. AMP-Designer 原始实验研究

[Wang 等，Science Advances 2025](https://doi.org/10.1126/sciadv.ads8932)，PMID 40043127，PMCID PMC13109931。论文许可证 CC BY-NC 4.0，应核对具体用途的非商业限制。

- 原文 Table 3 有 18 条针对 E. coli ATCC 25922 的逐肽 MIC，包括受测范围以上的结果。保留为实验线索，不依据原模型分数筛选。
- 原文对 AI18、KW13 明确报告人红细胞 HC50 范围结论；需用补充 Figure S4 核对曲线、受测浓度和端点依据。
- Materials 指向 Table S8 的序列，不能用肽名猜序列或假设末端形式。
- 补充 PDF 的出版社下载返回 HTTP 403；检索到的镜像实际下载返回 HTTP 404。原文 XML 已保存，补充表及原图尚未核实。

**当前决定：高优先级待核实；准入 0。** 先取得 S8、S4 及分子质量/形式证据，再审计。预测训练数据和作者模型输出不作为新实验标签。

## 其他原文的决定

| 原始出处 | 本轮发现 | 决定 |
|---|---|---|
| [Pandi 2023](https://doi.org/10.1038/s41467-023-42434-9) | 同时有 MIC 与人红细胞 HC50；PMID 37938588 已在正式开发集中对应 DBAASP:21528、21534；合成方法使用 RAM 树脂 | 不作为原正式研究的独立外部测量来源；末端形式另核实 |
| [Hybrid C–L 2018](https://doi.org/10.3390/molecules23061491) | Table 1 有逐对象 MIC；Methods 4.8 明确羊红细胞 | 不进入人 HC50 任务；MIC 单任务资格另核实 |
| [HydrAMP 2023](https://doi.org/10.1038/s41467-023-36994-z) | Methods Sec35 明确羊红细胞，Sec33 明确 Rink Amide 树脂 | 不补人 HC50；不能将酰胺化分子变成当前未修饰肽记录 |
| [Capitellacin 2022](https://doi.org/10.3390/md20030167) | 二硫键 beta-hairpin 分子；结果与方法的溶血时间描述需核实 | 当前未修饰线性分子范围的障碍，未准入 |
| [Spectrum 2020](https://doi.org/10.3390/molecules25153526) | Methods 2.5 明确 HC50 含外推输出 | 需回溯直接测量范围，不自动释放外推 HC50 |
| [QMAP 2026](https://doi.org/10.1038/s41598-026-56004-8) | DBAASP 衍生聚合；HC50 处理包含非人红细胞回退和平均 | 仅用作发现入口；回到原始论文，不能直接视为独立实测队列 |

既有 [Conlon 2004](https://doi.org/10.1016/j.bbrc.2004.05.141) 的 ascaphin 来源已审计为论文重叠及超阈值同源，见历史 `external_cohort_screen_20261001/screen_manifest.json`。本轮再次检索到它，继续保留既有拒绝结论，未重复计算为新增来源。

## 交付物与边界

- `inspection_v2/source_inventory.json`：8 篇来源的标识、许可证、原文哈希、开发来源命中和逐来源决定。
- `inspection_v2/archaeome_observations.json`：240 个 MIC 槽位和 80 个作者 HC50 拟合输出，共 320 个观察条目。均无派生标签；序列/分子形式缺失显式保留为空。
- `inspection_v2/inspection.json`：实际提取数量、检索障碍与输入摘要。
- `raw/` 与各 acquisition JSON：保留原始响应、URL、获取时间和 SHA256。
- `acquire.py`：一次性不可覆盖的原文获取入口。
- `inspect_evidence.py`：原文标识检查和工作簿提取入口；需要已有 bundled openpyxl，只读原工作簿。

一次初始工作簿解析在空单元格坐标处理处失败，保留产生的初始 `source_inventory.json`；修复使用显式列坐标后，完整结果写入独立 `inspection_v2/`。没有覆盖前一次产物，也没有把失败说成通过。

本轮实际运行原文获取和证据提取，并读到输出及内部覆盖断言结果。未运行模型训练、性能调参或新的科学准入门禁。现有 MIC v22 状态、冻结协议和历史模型保持原样；原双任务仍 blocked。

## 后续顺序

1. 取得古菌研究证书和原溶血剂量响应，确认实验 ID—完整分子身份对应，处理超范围拟合。
2. 取得 AMP-Designer Supplementary S8/S4，核对序列、末端形式和受测范围。
3. 对证据完整的记录核对原论文研究别名，再按两个研究任务各自的开发集执行全员相似度比较；不承诺通过当前 0.40 阈值。
4. 根据实验事实生成准入/排除决定；仅在证据、类别和固定评估结构门禁均通过后，建立新的冻结协议和队列。

任何一篇论文中的多个分子仍属于同一测量研究，不能把 80 个实验 ID 当作 80 个独立研究组件。
