# Gemini 交接提示：公开 MIC 证据扩充与严格分组审计

以下正文可直接粘贴到能够访问本地工作区的 Gemini 编码代理。若使用 Gemini 网页版，应先提供其所需的公开项目文件；本地路径本身不代表模型已经获得访问权限。

---

你接手一个已经完成小样本基线训练、正在扩充公开实验依据的计算生物学项目。请先读取真实文件，再执行未完成步骤，逐阶段交付可复跑代码和审计产物。

## 1. 工作环境与本轮目标

- 项目根目录：`D:\桌面文件\sci`。
- 系统：Windows；Shell：PowerShell；时区：Asia/Shanghai。
- 首先读取用户提供的 AGENTS.md 工作约定和仓库中适用的局部约定。使用补丁编辑，保留无关修改，优先复用现有代码和依赖。
- 项目具有 `.codegraph/`；先尝试 CodeGraph 定位相关符号。新增的 MIC 脚本尚未进入索引，查询未找到时直接读取当前源码，不自动重建索引。
- 本轮目标：完成 `protocol-mic-08` 授权的公开原始 MIC 来源审查、候选资格审计和固定三折可行性检查。
- 所有访问和处理遵守目标平台规则；不能执行的步骤记录状态和原因，继续完成允许的工作。
- 若你无法访问本地目录，先列出完成审计所需的最小文件集合；取得文件后再核查。只有读取实际文件和输出后，才能声称已经执行或通过。

## 2. 已完成的事实

### 2.1 MIC-only 已真实训练

当前机器状态：

`03_experiments/audits/mic_training_readiness_20261002_v12.json`

状态为 `local_exploratory_three_fold_training_completed`，生成于 **2026-10-02 18:51:38（Asia/Shanghai）**。

- 数据版本：`mic_three_fold_20261002_v1`。
- 15 条唯一分子、22 条原始 MIC，4 条阳性、11 条阴性。
- 审计协议 `protocol-mic-06`，训练协议 `protocol-mic-07`。
- 固定 44 维特征；逻辑回归、随机森林、prior 对照；固定三折、seed 42。
- 105 对全员序列比较；6 个不可拆分的同源/原始研究组件。
- 验证折阳性/阴性：2/4、1/4、1/3；训练对应为 2/7、3/7、3/8。
- 跨折同源边和共享原始测定研究均为 0。
- 运行目录：`03_experiments/runs/mic_three_fold_20261002_v1`。
- 已保存 9 个折模型、45 条折外（OOF）预测、逐折和合并描述性指标。
- 已经加载模型复算预测，独立重算全部指标，并核对五份状态文档。

阅读最终复核：

`03_experiments/audits/mic_three_fold_run_validation_20261002_v2.json`

`03_experiments/audits/mic_three_fold_run_validation_20261002_v2.md`

真实结果并不理想：LR / RF / prior 的合并 OOF AUROC 分别为 0.454545 / 0.318182 / 0.420455，AUPRC 分别为 0.300595 / 0.242262 / 0.238889。在预先冻结的 0.5 阈值下，三个基线均漏判全部四条阳性。prior 的 11/15 准确率来自全判阴性。每折 prior 的 AUROC 为 0.5，合并不同训练先验后可偏离 0.5。

这些结果已知；后续扩充明确属于新的探索阶段，不能追称为原训练前的预注册。原基线数据、参数、阈值、模型和负面结果作为不可变历史事实保留。

### 2.2 原正式双任务仍被数据门禁阻断

`04_paper/research_status.json` 仍为 `blocked`；协议 `protocol-amd-02`。417 条开发记录形成 89 个全员同源组件，最大组件 318 条。13 条缺底层测定依据的历史外部记录已经排除；目前没有通过全部门禁的独立外部队列。

该文件 SHA-256 必须继续为：

`846c1fc2452646f3df9c2055b0a4a1b5140132acc2433bb2c304b133b6e8012c`

正式结果与投稿授权均为 false。MIC-only 的完成状态不构成人红细胞 HC50 或独立外部队列的证据。

## 3. 接手后按顺序读取

1. `03_experiments/protocols/protocol-mic-01.json`
2. `03_experiments/protocols/protocol-mic-06.json`
3. `03_experiments/protocols/protocol-mic-07.json`
4. `03_experiments/protocols/protocol-mic-08.json`
5. `03_experiments/audits/protocol_mic_08_freeze_20261002_v1.json`
6. `docs/amendments/PROTOCOL_MIC_08_SOURCE_EXPANSION.md`
7. `docs/superpowers/plans/2026-10-02-mic-source-expansion.md`
8. `03_experiments/audits/mic_source_expansion_20261002_v1/discovery_catalog.json`
9. `03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/manifest.json`
10. `02_code/fetch_mic_expansion_sources.py`
11. `02_code/audit_mic_independent_sources.py`
12. `02_code/review_mic_three_fold_evidence.py`
13. `02_code/audit_mic_three_fold.py`
14. `02_code/validate_mic_acid_progress.py`
15. `02_code/validate_mic_three_fold_run.py`

读取后核对冻结记录中的全部输入摘要、采集清单的原始文件摘要，以及当前训练状态和原正式状态。任何不一致先定位根因，保存诊断；不要通过覆盖历史文件或降低门禁消除错误。

## 4. 新协议已冻结，但新候选尚未释放

`protocol-mic-08` 只授权**来源扩充审计**，冻结时间 **2026-10-02 19:22:32（Asia/Shanghai）**。

协议 SHA-256：

`b6a4d6071ef2dec6c4e79ee20bcf80bae5bd3af1b9a8511a04a0f629dfd58a01`

固定本批详细审查最多 12 个原始研究，按来源清单顺序记录全部对应肽行。现有基线性能已经知道，但候选选择依据是证据和冻结的分子域，不使用模型预测、错分分子身份或特征归因挑样本。

采集脚本已完成一次真实运行：

`03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/manifest.json`

采集完成时间 **2026-10-02 19:28:33（Asia/Shanghai）**。12 个线索中 8 个已取得可解析正文 XML 或真实 PDF；**这仅表示正文可用，尚未核查测定资格，新增训练释放数仍为 0**。

## 5. 本批来源与获取缺口

原始文件均在：

`03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/`

| source_id | 已保存正文 | DOI / PMCID / 其他标识 |
| --- | --- | --- |
| chekmenev2006 | PDF | 10.1016/j.bbamem.2006.03.034；作者机构 National MagLab 原文 |
| foundation2024 | XML | 10.1038/s41467-024-51933-2 |
| lactoferricin2015 | XML | PMC4359834 |
| boncat2025 | XML | PMC12748266 |
| carrier2016 | XML | 10.1371/journal.pone.0146552 |
| drosocin2002 | 仅元数据 | PMID12238928；10.1021/jm020861d |
| pexiganan2016 | PDF | arXiv:1606.00620；需核对发表版本及重复测定别名 |
| brucin2020 | 下载失败 | WHO IMSEAR 原刊 PDF 链接在 discovery_catalog.json |
| apidaecin2009 | XML 请求失败 | PMC2648157；保存的文件是错误响应，不能作为正文 |
| neopeptides2005 | XML 请求失败 | PMC1196242；保存的文件是错误响应，不能作为正文 |
| bmap2025 | XML | PMC12207908 |
| tat2026 | XML | PMC13112966 |

四条 Europe PMC 主题查询已保存响应。OpenAlex 四条查询均返回 HTTP 429，保留失败响应，不可描述为成功取得 OpenAlex 检索结果。可依正常服务规则稍后重试，或从原出版方公开页面核对，并记录检索渠道的实际覆盖。

取得不足的四个来源可从正常公开出版方、作者机构或文献数据库寻找原文和补充材料；不可取得时明确暂缓。保留失败响应和原采集 manifest，另用新目录保存后续获取结果。

## 6. 逐记录证据审查要求

对每个入选详细审查研究的所有可对应 E. coli MIC 肽行，保存以下字段：

- 来源标识、DOI/PMID/PMCID、标题、年份及原文 URL。
- 论文中的肽名、准确序列、实际受测分子的 N/C 端与共价化学形式。
- 菌株或分离株标识；端点必须为 MIC。
- 原始值、单位、区间和 `<` / `>` / `≤` / `≥` 标记。
- 原文报告的条件、重复信息；未报告时明确 missing，不补写。
- 表格、行、列、图、页码或补充文件定位；底层原始文件 SHA-256。
- 原文许可文本、未解决的再利用限制。
- 单位转换依据、重推导标签、资格决定与具体原因。
- 来源审核阶段与审核者类型；代理核查不能写成独立人工审稿。

对涉及序列图或 PDF 表格的数值，应渲染原始页并目视核对，保存对应页图与摘要；XML 解析和 OCR 只能辅助定位。

维持当前分子域：标准 20 种 L 氨基酸、线性、10–50 aa、游离 N 端及 C 端羧酸、无共价修饰。受测形式缺证据时暂缓；酰胺化、D 型、非标准残基、环化/交联、接枝或缀合物按冻结分子域排除。只报告“Fmoc 合成”或数据库“none”不足以补齐实际化学身份。

沿用 MIC 标签规则：可信上界 <=32 µg/mL 为阳性，可信下界 >=128 µg/mL 为阴性，空档或删失界不足支持时不进入二值训练。保留真实符号，使用冻结平均分子量转换。原始研究中具有相反二值结果的同一分子整体阻止释放，保存全部冲突依据。

未测记录保持缺失；数据库类别、预测、抑菌区、IC50、MBC 和其他对象的测定不能转换为该目标 MIC 标签。

## 7. 可复跑代码与数据结构交付

创建 `02_code/audit_mic_source_expansion.py`，复用现有规则和比对实现。具体模块结构可在读取源码后小范围调整，但保持职责清楚，禁止修改冻结实现。

建议 CLI：

```powershell
python 02_code/audit_mic_source_expansion.py --output 03_experiments/audits/mic_source_expansion_result_20261002_v1
```

输出目录必须不存在。至少输出：

- `source_inventory.csv`：元数据、原始文件、哈希、许可、获取情况及研究别名。
- `record_decisions.csv`：全部对应肽行的纳入、暂缓和排除决定。
- `assay_observations.csv`：逐原始 MIC，真实符号/单位及引用定位。
- `candidate_molecules.csv`：同分子去重后的候选，真实标签及完整研究标识。
- `all_member_similarity.csv`：候选与既有 15 条组成队列的全部唯一分子对。
- `combined_components.csv` 与组件/类别统计。
- `fold_assignments.csv` 和 `fold_roles.csv`：仅固定结构可行时产生；失败时使用明确失败状态，不虚构“跨折为 0”。
- `manifest.json`：生成时间、协议、全部输入/输出摘要、门禁状态、失败原因、候选数、释放数。
- `report.md`：证据、冲突、分组可行性、实际进展和局限。

所有候选资格决定先于分折。完整记录处理失败，不能只留下成功记录而隐藏失败。

## 8. 严格分组与可行性检查

使用 `protocol-mic-06` 的固定全局 Needleman–Wunsch：match=2、mismatch=-1、gap=-2；回溯优先级 diagonal、up、left；一致性=相同残基列数/全部比对列数，gap 为不匹配。

对候选队列所有唯一分子两两比较，达到 **>=0.40** 的边加入传递闭包；原始测定研究及其 DOI/PMID/重复发表别名也整体连接。严格整组件分配，不只比较代表序列。

固定 `StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)`；各训练和验证均需两类，跨折同源边和原始研究均为 0。若新记录形成巨型组件、减少独立阳性组件或导致不可分折，如实记录结构失败；不挑种子、不删桥接记录、不调阈值。

同一研究重复出现不算新独立来源。同源关系充分影响组件后再报告净新增独立组件；不要把“新序列数”直接称为“新独立样本数”。

## 9. 训练范围与下一阶段

本轮 protocol-mic-08 审计无权释放新训练记录，因此 `new_records_released_for_training=0`。

即使证据和结构审计通过，先交付完整报告和明确的后续训练方案；新队列另需完整证据释放与新的不可变训练协议。当前 protocol-mic-07 不能用于任意扩充队列，也不能通过改硬编码摘要来替换输入。

后续方案应记录原基线结果已知、固定新队列、预先声明分析、指标和使用限制；获得对应授权后再执行。用户继续要求严格真实证据与零泄漏，任何失败项保留 blocked/withheld。

处理范围为公开测定数据整理、普通分类基线及验证。不开展新肽序列设计、生成或定向生物活性增强，不提供病原体工程或湿实验操作步骤。

## 10. 验证与文档同步

语法检查：

```powershell
python -m py_compile 02_code/fetch_mic_expansion_sources.py 02_code/audit_mic_source_expansion.py
```

证据审计完成后，检查所有原始文件摘要、原文表格定位、单位/标签、候选完整性、分组连通性及固定三折；核对新脚本拒绝覆盖既有审计。

更新五份当前文档，明确区分：原双任务仍阻断、旧 MIC-only 三折训练已完成、新来源扩充处于证据或结构审查阶段：

1. `README.md`
2. `docs/REMEDIATION_STATUS.md`
3. `docs/DOCUMENTATION_INDEX.md`
4. `docs/handoff/TASK_STATE.md`
5. `03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md`

当前训练状态仍以 v12 的时间、路径和协议为准；给扩充审计另外列出实际时间和 protocol-mic-08。把 v2 文档校验当成历史快照，生成新验证：

```powershell
python 02_code/validate_mic_three_fold_run.py --run 03_experiments/runs/mic_three_fold_20261002_v1 --output 03_experiments/audits/mic_three_fold_run_validation_20261002_v3.json --state 03_experiments/audits/mic_training_readiness_20261002_v12.json --check-documents
```

输出路径若已存在，应选新的版本路径。旧 182 passed 是 2026-10-01 的软件结果，不能称为本轮测试或模型有效性验证。

## 11. 最终验收与汇报格式

请以实际文件和命令输出交付：

1. 审查了多少原始研究、多少对应肽行和测定；多少纳入、暂缓、排除，各自原因。
2. 证据充分的新增分子与去重后候选数；全员比较对数、组件总数、含阳性/阴性组件数、最大组件及三折是否可行。
3. 是否存在重复研究、分子化学冲突、目标/端点冲突、单位或删失界问题。
4. 新增候选的训练释放状态；本轮应为未释放，不将可行性审计写成训练完成。
5. 新建/修改文件路径、复跑命令、实际退出码和未覆盖项。
6. 原正式状态、原 15 条数据、v12、协议和九个模型摘要保持不变的核查结果。
7. 若后续阶段仍有门禁失败，给出具体可补证据清单或前瞻性方案，不虚构成功或平台权限。

请直接开始读取并核查上述文件，优先处理当前批次，不重复运行已完成的小样本训练。不需要先泛泛解释项目，也不需要等待确认才执行已授权的公开证据审计。涉及新的训练协议、研究问题变化或外部发布时，先给出具体、可审查的方案。
