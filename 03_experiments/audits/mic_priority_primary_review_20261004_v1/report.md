# 两篇优先研究的原始材料复核

审查日期：2026-10-04。准确获取和生成时间、文件摘要见同目录各 acquisition 和 inspection JSON。审查模式为代理原文复核，不声称独立人工评审。

## 本轮完成

- [x] 获取古菌研究作者公开的 80 份分子分析证书，验证 ZIP 并保留每份 PDF 的 SHA256、逐页文本和逐分子决定。
- [x] 获取 AMP-Designer 正式补充 PDF；文件 777641 字节，MD5 `c0e137ba50af6075f92cacd79de1bf4e`，与原文 XML 中的大小和摘要一致。
- [x] 渲染并查看分析证书示例、补充 PDF 第 5 页 Figure S4 和第 11 页 Table S8。
- [x] 保存证据缺口、分子形式不符的决定；没有派生或释放新标签。
- [ ] 古菌证书名称与 Archaeasin-1…80 测定编号的可核查映射。
- [ ] 古菌受测分子的明确末端形式及 Extended Data Fig. 7 原始剂量响应。
- [ ] 合格分子的来源别名、全员同源与外部队列门禁；本轮没有合格新分子，因此未运行正式隔离审计。

## 古菌研究：证书已取得，身份仍待核实

原文：[Torres 等，2025](https://doi.org/10.1038/s41564-025-02061-0)。作者数据集：[Mendeley Data v5](https://data.mendeley.com/datasets/d8yzgtdrcp/5)，DOI `10.17632/d8yzgtdrcp.5`，CC BY 4.0。原文引用 v3，本轮取得 v5，明确保留版本差异，未声称二者内容完全相同。

公开网页加载成功后显示 `COA_archaeasins.zip`。从实际文件链接取得有效 ZIP，11297157 字节，SHA256 `982cd9a9f6d497c14c67a1b72ea25106cc865743ae63f2e1275d73bad37ef0b3`。排除 macOS 元数据后有 80 份 PDF；提取到 80 个唯一肽名和 80 条序列。

证书以 `PYRAE-LWL12` 等蛋白片段名标识，80 份证书中均未发现 `Archaeasin` 实验编号。已渲染的证书明确给出序列、TFA 盐形式、理论质量和质谱信息；提取文本未找到明确的酰胺化、乙酰化或游离末端标记。TFA 盐形式和质量信息不能替代完整末端身份审查。逐条决定见 `molecule_identity_review.csv`，均为 pending。

不能按 ZIP 文件顺序、预测表行号或文件名排列，把这些分子配给测定 ID。前轮 MIC 的 84 个空槽仍为空，超范围 HC50 拟合仍不作为精确端点。Europe PMC 的古菌补充包请求发生读取超时，未得到文件，见 `epmc_acquisition.json`。

## AMP-Designer：补充材料确认分子形式不符

原文：[Wang 等，2025](https://doi.org/10.1126/sciadv.ads8932)，PMCID PMC13109931。论文及补充材料按 CC BY-NC 4.0 核对用途；本轮仅本地科研审查。

PMC 页面有真实补充文件链接，但下载返回浏览器验证 HTML，不作为 PDF。通过 [Europe PMC 官方补充材料接口](https://europepmc.org/RestfulWebService) 获得有效 ZIP，再取得补充 PDF，并验证原文记载的文件摘要。失败响应与成功响应均保留。

Table S8 的全部 23 条受测肽均明确带 `-NH2`，包括 Table 3 的 18 条 E. coli MIC 肽和另 5 条 P. acnes 设计肽。它们是 C 端酰胺化分子，按当前 MIC 未修饰线性分子的既定范围排除；不能去掉 `-NH2` 后沿用测定。逐条决定见 `foundation_molecule_review.csv`。这项决定针对当前 MIC 队列，原双任务中的分子范围和隔离要求须单独核查，未声称该论文在所有未来协议下均无资格。

第 5 页 Figure S4 给出 KW13、AI18 的人红细胞溶血图，最高标出的肽浓度为 1000 µg/ml；图支持原文所述 HC50 >1000 µg/ml 的范围结论。保留删失关系，不填写精确 HC50，不把柱形图读取值冒充原始重复观察。正文方法所写 100 µg/ml 程序与补充图梯度范围的条件对应仍待核实。详见 `foundation_endpoint_review.json`。

## 实际准入与状态

本轮新增准入分子 **0**。古菌 80 份证书对应的候选保持待核实；AMP-Designer 23 条身份因当前 MIC 分子范围不符被排除。没有执行新训练，没有修改冻结协议、历史队列或模型。

当前机器状态仍以 `../mic_training_readiness_20261004_v22.json` 为准：MIC 小样本探索性训练及独立复核已完成，`training_blocked=false`；原双任务仍 `blocked`，投稿资格仍为 false。新增材料获取进展不能自动解除科学准入门禁。

后续最关键的缺口是古菌研究中实验编号到证书肽名的明确映射、末端身份以及真实剂量响应。完整后才能对全部成员实施隔离检查。若公开附件无法提供，需向作者索取；本轮未向作者发送消息。

## 可复核产物

- `coa_acquisition.json` / `epmc_acquisition.json` / `foundation_acquisition.json`：来源、获取时间、摘要、成功和失败。
- `coa_text.json` / `molecule_identity_review.csv`：80 份证书的逐页证据和决定。
- `foundation_pages.json` / `foundation_molecule_review.csv` / `foundation_endpoint_review.json`：补充材料的页面定位、23 条分子形式决定和端点边界。
- `raw/`：原始 ZIP、PDF、被拒绝的 HTML；PNG 为视觉复核副本。
- 各 Python 入口拒绝覆盖已有输出；复跑应复制脚本到新的版本目录，先获取再解析。
- `manifest.json`：本轮产物及受保护输入的摘要，真实生成时间与准入结论。
