# SafeAMP-Dual 整改与 SCI 复现实施方案

> 文档用途：本文件是 SafeAMP-Dual 项目的工程整改、数据重建、实验复现和论文准备规范，也可直接作为 Gemini 长时间开发任务的主任务说明。
>
> 当前状态：**工程链路可运行，科学证据仍被门禁阻断，不得直接投稿。**
> 当前正式数据协议采用 `protocol-amd-02`；本历史方案中的旧状态示例或代表序列隔离步骤不得作为门禁通过依据。状态以 `04_paper/research_status.json` 为准。
>
> 适用范围：纯计算研究、公开数据、可追溯数据处理、模型实验、预测服务和论文材料。

## 1. 总体目标和不可违反的原则

项目最终要回答的问题是：

> 在真实公开实验数据和严格序列隔离条件下，联合学习是否改善抗菌活性与溶血风险预测之间的性能权衡和概率校准？

所有开发和分析必须遵守以下原则：

1. 模拟数据只能用于软件测试，不能进入正式训练、验证、测试、图表或论文结果。
2. 未测量的标签必须保留为缺失，不能自动转成阴性。
3. 训练集、验证集、独立测试集和外部测试集必须保存逐样本清单。
4. 序列隔离必须检查所有样本，不能只检查簇代表序列。
5. 外部数据必须同时满足测量终点、证据来源、许可、文献和序列隔离要求。
6. 每一个论文数值都必须能从保存的逐样本预测记录重新计算。
7. 当前科学门禁未通过时，禁止正式训练、性能宣传和投稿。
8. 分类概率、计算排序分数和理化提示不得表述为实测杀菌率、实测降毒效果、临床安全性或作用机制。
9. AI 生成内容必须由项目负责人核验；AI 不是作者，也不能替代数据和文献证据。

## 2. 当前问题和风险等级

### P0：必须先修复的科学证据问题

| 问题 | 当前表现 | 风险 | 修复要求 |
|---|---|---|---|
| 数据来源断裂 | 旧基准数据包含大量 `Benchmark_Synthetic` 记录 | 高分不能作为真实实验泛化证据 | 模拟数据退出正式研究；只使用可追溯实验记录 |
| 序列泄漏风险 | 当前开发试采样 417 条序列在 40% 规则下形成单一主要连通分量 | 普通随机划分或代表序列隔离会产生同源泄漏 | 保留当前隔离规则，未通过时硬阻断 |
| 外部集缺失 | 当前没有通过端点、证据、许可和同源检查的独立外部队列 | 无法证明跨来源泛化 | 建立独立来源队列并进行逐样本审计 |
| 溶血标签稀疏 | 当前有效溶血标签只有 62 条，阳性 18、阴性 44，其他缺失 | 双任务结果不稳定，类别和覆盖度不足 | 扩充真实测量；缺失保持缺失；重新做样本量评估 |
| 结果不可追溯 | 旧消融表、主结果表和统计脚本缺少对应逐样本运行记录 | 论文数字无法复核 | 所有结果从不可变运行目录自动生成 |
| 引用错配 | 已发现部分数据库引用 DOI 与题名或数据库不对应 | 论文可信度和学术合规风险 | 全部引用逐条核验，未核验不得投稿 |

### P1：必须修复的结论和服务问题

- 理化规则热图不能称为模型梯度归因。
- TSI 只能称为计算排序分数，不能表示临床治疗窗口。
- 同一预测器给自己推荐的突变不是独立有效性验证。
- ESM 或分类器权重缺失、损坏或不匹配时，服务必须失败关闭。
- 服务不能使用随机初始化模型或伪嵌入返回看似正常的预测。

### P2：工程质量问题

- 公开数据下载默认并发应为 1，并限制请求速率。
- 来源清单需要保存原始文件路径、哈希、下载时间、版本、URL 和许可信息。
- 代码、数据、模型和运行配置需要统一版本化。
- lint 警告、过时文档和旧结果链接必须清理。

## 3. 实施阶段总览

| 阶段 | 目标 | 允许的结果 | 通过条件 |
|---|---|---|---|
| A | 工程基线和文档纠偏 | 测试、状态报告、错误处理 | 无旧结果被误标为正式结果 |
| B | 数据来源和证据链 | 原始快照、来源清单、标准化记录 | 每条记录可追溯，许可状态明确 |
| C | 序列隔离和科学门禁 | 可行性报告和阻断诊断 | 隔离、类别、外部集全部满足门禁 |
| D | 正式实验 | 训练、预测、指标和区间 | 所有结果从运行产物重新计算 |
| E | 论文和投稿材料 | 论文、补充材料、引用和声明 | 数字、引用、作者和许可全部核验 |

阶段必须按顺序完成。阶段 C 未通过时，不得执行阶段 D。

## 4. 阶段 A：工程基线和文档纠偏

### 4.1 必须检查的文件

- `02_code/research_data.py`
- `02_code/research_feasibility.py`
- `02_code/experiment_runner.py`
- `02_code/dramp_importer.py`
- `02_code/public_data.py`
- `02_code/inference_runtime.py`
- `05_web_server/research_api.py`
- `04_paper/manuscript.tex`
- `04_paper/references.bib`
- `docs/DELIVERABLES_SUMMARY.md`
- `docs/handoff/FEASIBILITY_REPORT.md`

### 4.2 重写项目状态报告

重写 `docs/DELIVERABLES_SUMMARY.md`，删除以下未经证实的内容：

- “7×24 云端常驻运行”；
- “1,200 条真实正式数据”；
- “35 篇引用 100% 真实”；
- `p < 0.001`；
- 已完成 40% 同源隔离；
- 临床安全性、治疗窗口、实测降毒效果；
- 已经实验验证的突变推荐。

新报告必须显示：

- 当前为 pilot/protocol 阶段；
- 当前开发记录数和各任务标签覆盖度；
- 当前同源连通分量诊断；
- 当前外部队列状态；
- `publication_ready=false`；
- `formal_results_available=false`；
- 当前阻断原因和下一步条件。

旧图表、旧权重和旧结果可以保留在 `legacy/` 或 `03_experiments/retired_unsupported/`，但不能被正式 README、论文和网页引用。

### 4.3 建立 fail-closed 的发布门禁

所有论文表格和图表导出函数必须检查：

```text
run_manifest.status == "completed"
dataset_manifest.status == "validated"
publication_ready == true
formal_results_available == true
reference_audit.all_claims_verified == true
```

任何条件不满足时，导出程序必须报错，并说明缺失条件。

## 5. 阶段 B：数据来源和证据链

### 5.1 允许使用的数据来源

候选来源包括：

- DBAASP 官方数据库或官方接口：开发数据候选；
- DRAMP 官方数据或官方导出：外部数据候选；
- PubMed、Europe PMC：论文、PMID 和实验条件核验；
- Crossref、OpenAlex：DOI 元数据交叉核验；
- 论文作者公开的补充数据：仅在许可和实验端点明确时使用。

下载前必须检查当前网站的访问和复用条款。可下载不等于可以再发布、再分发或用于商业用途。

### 5.2 原始快照规则

每次下载必须保存：

- 原始文件，不直接覆盖旧版本；
- 文件相对路径；
- 文件大小；
- SHA256；
- 下载 URL；
- UTC 下载时间；
- 数据库版本或版本缺失原因；
- 许可原文或许可页面；
- 复用决定：`approved`、`pending_author_review` 或 `rejected`；
- 获取脚本代码哈希；
- 请求配置和重试记录。

来源清单建议结构：

```json
{
  "schema_version": "1.0",
  "source_name": "DBAASP",
  "source_version": null,
  "version_note": "来源未提供公开版本号",
  "acquisition_url": "https://...",
  "retrieved_at_utc": "...",
  "license_text": "...",
  "reuse_decision": "pending_author_review",
  "raw_files": [
    {
      "path": "raw/index_0.json",
      "size_bytes": 0,
      "sha256": "..."
    }
  ],
  "records_path": "records.csv",
  "records_sha256": "...",
  "importer_code_hash": "...",
  "request_policy": {
    "workers": 1,
    "min_interval_seconds": 1.0,
    "max_retries": 3
  }
}
```

### 5.3 标准化记录规则

每条记录至少必须包含：

```text
record_id
seq
amp
hemo
source_dataset
source_accession
source_url
evidence_reference
label_basis
assay_conditions
modifications
evidence_type
is_synthetic
source_role
raw_path
raw_sha256
```

标签要求：

- 只有明确实验观测才能产生 0 或 1；
- 未测量值为缺失值；
- 区间、截尾、单位不兼容和条件不完整的值不能强行二值化；
- 冲突实验结果不能通过简单多数投票隐藏；
- 修饰肽必须单独定义表示和分析范围；
- 合成数据必须被 `validate_records` 拒绝进入正式研究。

### 5.4 DOI 和 PMID 重叠检查

文献标识符必须先标准化：

1. 转为小写；
2. 去除 `https://doi.org/`、`http://dx.doi.org/` 和 `doi:` 前缀；
3. 去除末尾句号、逗号、分号和括号；
4. 去除多余空白；
5. PMID 以完整标识符匹配，不能使用简单子字符串。

DRAMP 与开发集之间只要 DOI 或 PMID 任一相同，就必须记录文献重叠并排除，除非研究协议明确规定了重复实验的处理方式。

审计输出必须包含：

```text
candidate_pmids
candidate_dois
development_pmids
development_dois
pmid_overlap
doi_overlap
overlap_identifiers
rejection_reasons
```

## 6. 阶段 C：序列隔离和科学门禁

### 6.1 当前正式隔离定义

在作者完成预先记录和方法审查之前，正式协议继续使用项目当前定义：

- global Needleman–Wunsch；
- 当前匹配和缺口分数；
- 当前确定性回溯规则；
- `identity = matches / min(length(sequence_a), length(sequence_b))`；
- 隔离阈值为 0.40。

不得为了获得更多连通分量而事后放宽阈值、删除桥接序列或改用随机划分。

其他身份定义可以做敏感性诊断，但必须单独标记，不能替代正式门禁。

### 6.2 所有样本的隔离检查

必须检查：

- 开发集内部所有序列对；
- 五折之间所有序列对；
- 开发集与独立测试集所有序列对；
- 开发集与外部测试集所有序列对；
- 精确序列重复；
- 数据库交叉引用；
- DOI/PMID 文献重复；
- 通过非代表序列连接的桥接关系。

逐对诊断输出至少包括：

```text
sample_a
sample_b
identity
alignment_length
min_length
max_length
cutoff
rule_id
violates
```

### 6.3 正式训练的硬门禁

以下条件必须全部满足：

1. 数据记录和原始证据通过校验；
2. AMP 存在两个观测类别；
3. 溶血存在两个观测类别；
4. 各任务达到预先记录的最小观测量；
5. 至少有 6 个独立同源连通分量；
6. 开发集和外部集之间无超阈值序列；
7. 外部集来源、文献和测量端点独立；
8. 缺失标签未被补成阴性；
9. 数据许可和再利用条件已记录；
10. 运行清单、划分清单和代码哈希完整。

任一条件失败，`research_feasibility.py` 必须返回 `blocked`，并以退出码 2 终止。此时不得启动 `experiment_runner.py`。

### 6.4 当前数据的处理决定

当前 417 条开发试采样仍作为诊断材料，不作为正式论文训练数据。当前溶血标签稀疏和同源连通分量不足，必须在可行性报告中如实记录。追加数据库记录不能自动修复已有开发集的同源连通结构。

## 7. 外部测试集建设流程

### 7.1 候选记录筛选

外部候选必须满足：

- 人红细胞 HC50 终点明确；
- 测量值、单位和实验条件可解释；
- 记录来自独立来源或独立研究记录；
- 有 PMID、DOI、数据库 accession 或可核查原始记录；
- 无非标准氨基酸或未声明修饰；
- 不与开发集共享精确序列；
- 不与开发集共享超阈值同源序列；
- 不存在 DOI、PMID 或明确数据库交叉引用重叠；
- 复用条款允许研究用途，或已完成人工许可审查。

### 7.2 外部集输出

每轮导入必须生成：

- `candidate_audit.csv`；
- `records.csv`；
- `exclusions.json`；
- `source_manifest.json`；
- `sequence_diagnostics.csv`；
- `summary.json`；
- 可复现的运行命令和代码哈希。

所有被排除的记录都要有可读的排除原因，例如：

```text
no_human_hc50_measurement
intermediate_or_censored_hemo
exact_sequence_overlap_with_development
literature_doi_overlap_with_development
literature_pmid_overlap_with_development
homology_cross_isolation_violation
license_pending
```

## 8. 阶段 D：正式实验协议

### 8.1 数据划分

- 使用同一份经验证的数据划分；
- 以独立同源连通分量为分组单位；
- 预处理器只能在训练部分拟合；
- 验证集用于阈值和校准选择；
- 模型选择结束后，在完整开发集上重新训练最终模型；
- 独立外部测试集只在最终模型固定后评估。

### 8.2 模型和消融

在相同数据、分组、调参预算和随机种子下比较：

- SVM；
- Random Forest；
- 单任务抗菌模型；
- 单任务溶血模型；
- 双任务模型；
- 双任务门控模型；
- 预先定义的特征和任务消融。

每个实验至少保存：

- 配置文件；
- 数据集哈希；
- 分组和折分配；
- 模型权重哈希；
- 训练日志；
- 逐样本预测；
- 指标文件；
- 运行清单。

### 8.3 指标和统计

主指标建议为溶血任务 AUPRC，同时报告：

- AMP AUROC 和 AUPRC；
- Hemo AUROC 和 AUPRC；
- MCC；
- 混淆矩阵；
- Brier score 或其他概率校准指标；
- 校准曲线；
- 阈值确定后的敏感度、特异度和置信区间；
- 外部测试集的独立结果。

置信区间和模型比较应以独立序列簇为重采样单位。禁止把五折简单视为五个独立生物学实验，也禁止使用没有来源记录的硬编码数组。

可以使用 bootstrap、置换检验或其他预先记录的配对方法，但必须保存原始预测和统计配置。若结果不显著，必须如实报告，不得改用另一种检验直到获得显著性。

## 9. 阶段 E：推理服务和接口要求

### 9.1 fail-closed 条件

正式预测必须拒绝以下情况：

- 未设置有效 `SAFEAMP_RUN_DIR`；
- 运行清单不是 `completed`；
- 数据清单不是 `validated`；
- 预测文件校验和不匹配；
- 不是完整的三个种子集成；
- 检查点校验和不匹配；
- 特征后端、版本或 ESM 权重哈希不匹配；
- 模型配置和运行清单不一致；
- 预处理参数无效或包含非有限值；
- 模型权重包含 NaN 或无穷值。

接口必须返回明确的 503 错误，例如：

```json
{
  "code": "MODEL_NOT_VALIDATED",
  "message": "Research run or dataset did not pass validation."
}
```

### 9.2 术语和输出边界

| 当前输出 | 允许表述 | 禁止表述 |
|---|---|---|
| AMP probability | 模型端点概率或计算分数 | 实测杀菌率 |
| Hemo probability | 模型端点概率或计算分数 | 实测溶血率 |
| TSI | 计算排序分数 | 临床治疗窗口、临床安全指数 |
| 残基热图 | 理化属性提示 | 梯度归因、机制证明 |
| 突变推荐 | 同模型探索性排序 | 实验降毒、活性保留、临床候选 |
| 报告 | 计算研究报告 | 医疗建议、临床批准 |

## 10. 论文、引用和投稿材料

### 10.1 论文状态

在正式实验完成前，论文只能使用以下定位：

- 数据来源和质量控制方案；
- 研究协议；
- 可行性和隔离诊断；
- 软件和复现接口；
- 未完成正式验证的探索性功能。

不能把旧的模拟基准、旧模型权重、旧图表或旧统计表写成正式结果。

### 10.2 引用审计

对 `references.bib` 每条文献核对：

- DOI 是否存在；
- DOI 是否对应当前题名；
- 作者是否匹配；
- 年份和期刊是否匹配；
- 引用用途是否由原文支持；
- 数据库论文是否真的描述当前使用的数据来源。

任何 `metadata_mismatch`、`lookup_failed` 或未完成用途核查的条目都必须阻止投稿材料生成。

### 10.3 作者、基金和声明

投稿前人工核验：

- 作者姓名和顺序；
- 单位；
- 基金编号和资助方；
- 利益冲突；
- 数据和代码可用性；
- AI 工具使用披露；
- 数据库许可和再发布限制；
- 是否需要伦理审查或豁免说明。

不得保留模板作者、模板基金、虚构审稿人或未经授权的仓库声明。

## 11. 个人开发者工具和环境

### 11.1 最小软件栈

- Windows 或 Linux；
- Python 3.11；
- Git；
- pandas、NumPy、SciPy、scikit-learn；
- PyTorch 和 fair-esm；
- Biopython；
- pytest；
- LaTeX 或 Overleaf，仅用于排版，不用于制造研究证据；
- 可选 DVC，用于大文件和数据版本管理。

不需要购买商业统计软件或云 GPU。正式运行前必须确认本地 ESM 权重已下载、哈希已记录、磁盘空间足够。

### 11.2 建议的公开网站和服务

- DBAASP：候选开发数据；
- DRAMP：候选外部数据；
- PubMed、Europe PMC：实验文献和 PMID；
- Crossref、OpenAlex：DOI 元数据；
- GitHub 或其他公开仓库：只在确认数据许可后发布代码和非受限文件。

任何网站都必须在运行清单中记录访问地址、访问日期和使用条款状态。

## 12. Gemini 长时间开发任务清单

Gemini 必须按照以下顺序执行，每一阶段完成后保存报告，不得跳过科学门禁。

### Task 0：建立基线

输入：当前工作区。

执行：

```powershell
python -m pytest 02_code/tests
python -m compileall 02_code 05_web_server
codegraph explore "research_feasibility experiment_runner dramp_importer public_data inference_runtime"
```

输出：

- `output/baseline/pytest.txt`；
- `output/baseline/compileall.txt`；
- `output/baseline/codegraph.txt`；
- 基线问题清单。

不得删除或覆盖用户已有修改。

### Task 1：修复文档和发布门禁

输入：旧文档、论文、实验结果和状态 JSON。

输出：

- 新的项目状态报告；
- 旧结果归档说明；
- 发布门禁检查；
- 不支持的数值和临床表述清单。

验收：旧模拟数据和旧显著性结论不再被正式文档引用。

### Task 2：修复来源清单和导入器

输入：DBAASP、DRAMP 原始快照。

输出：

- 完整 `source_manifest.json`；
- 原始文件哈希清单；
- DOI/PMID 标准化函数；
- 文献重叠审计；
- 导入器单元测试。

验收：同一篇文献只要 DOI 或 PMID 相同就能被检测；来源元数据缺失时验证失败。

### Task 3：修复下载速率和断点恢复

输入：公开数据下载器。

输出：

- 默认单 worker；
- 全局请求节流；
- Retry-After 支持；
- 断点恢复测试；
- 请求配置写入 manifest。

验收：缓存命中不重复请求，失败可恢复，校验和错误会停止流程。

### Task 4：完成科学门禁

输入：标准化真实记录。

输出：

- `summary.json`；
- `feasibility_report.md`；
- `sequence_diagnostics.csv`；
- 外部候选审计表；
- 阻断原因列表。

验收：当前 417 条试采样仍会正确阻断，不得通过随机切分绕过。

### Task 5：建立外部验证队列

输入：正式来源快照和候选记录。

输出：

- 独立外部 `records.csv`；
- 逐样本文献和序列审计；
- 许可审查结果；
- 交叉来源排除清单。

验收：外部集通过端点、文献、许可和全样本序列隔离检查。

### Task 6：门禁通过后才训练

输入：`status=ready_for_formal_experiments` 的数据集。

输出：

- 三个随机种子；
- 五折分组预测；
- 主模型和基线模型；
- 消融实验；
- 逐样本预测；
- 指标、校准和置信区间；
- 完整运行清单。

验收：任何论文数字都可以从预测记录重新计算。

### Task 7：论文和投稿审计

输入：正式运行产物、引用库、作者声明。

输出：

- 统一表格和图；
- 引用审计；
- 数字一致性报告；
- 作者、基金、许可和 AI 披露检查；
- 最终投稿包。

验收：只有所有声明、引用、结果和数据来源都通过人工核验后，才允许设置 `publication_ready=true`。

## 13. 推荐命令和验收命令

基础检查：

```powershell
python -m pytest 02_code/tests
python -m compileall 02_code 05_web_server
```

科学门禁：

```powershell
python 02_code/research_feasibility.py `
  --records <validated-records.csv> `
  --output <versioned-gate-directory> `
  --cutoff 0.40
```

正式实验前必须看到：

```text
status=ready_for_formal_experiments
external_cohort_isolation=passed
homology_clusters>=6
publication_ready=false
```

正式实验完成后必须看到：

```text
manifest.status=completed
dataset_manifest.status=validated
predictions.csv exists
metrics.json exists
confidence_intervals.json exists
comparisons.json exists
all prediction coverage checks passed
```

## 14. 最终验收标准

项目只有同时满足以下条件，才可进入投稿准备：

- 正式数据逐条可追溯；
- 模拟数据不会进入正式结果；
- 数据、来源、模型和运行清单均有哈希；
- 所有划分和序列隔离检查通过；
- 有合格独立外部测试集；
- 缺失标签没有被补成阴性；
- 消融和统计结果有对应运行记录；
- 每个论文数值可重新计算；
- ESM 和分类器权重缺失时服务明确失败；
- 理化提示、模型解释和实验机制已分开；
- TSI 和突变推荐没有临床或实测表述；
- 引用、作者、基金、仓库和许可证声明全部核验；
- 正式实验结果与论文、图表和补充材料来自同一批产物。

## 15. 假设、禁止事项和失败处理

### 假设

- 项目以纯计算研究为主；
- 数据优先来自公开、可追溯实验记录；
- 当前 40% 隔离定义在作者正式审查前保持不变；
- 最终论文可能报告“无显著改善”或“数据不足”，不预设正向结果；
- 作者本人负责最终科学判断、署名、许可证和投稿批准。

### 禁止事项

- 禁止把模拟数据写成真实数据；
- 禁止随机划分代替同源分组；
- 禁止为了通过门禁而删除桥接序列；
- 禁止把未测量标签补成阴性；
- 禁止修改硬编码统计数组来制造显著性；
- 禁止把同一模型的突变排序当成独立验证；
- 禁止伪嵌入或随机权重静默降级；
- 禁止未经许可公开原始数据库文件；
- 禁止生成虚构 DOI、作者、基金、伦理审批或实验结果。

### 失败处理

- 数据证据缺失：标记为 `unverified`，停止进入正式数据集；
- 许可证不清：标记为 `pending_author_review`，停止公开发布；
- 序列隔离失败：生成诊断报告，保留数据，不绕过门禁；
- 标签数量不足：报告可行性失败，重新设计数据采集，不补标签；
- 模型权重或特征后端不匹配：服务返回 503，不返回预测；
- 引用元数据错误：修正文献或从论文移除，不保留未经核实的引用；
- 正式实验失败：保留不可变运行目录和错误清单，修复后生成新版本，不覆盖旧运行。

## 16. 交付物目录建议

```text
docs/
  SAFEAMP_DUAL_REMEDIATION_PLAN.md
  DELIVERABLES_SUMMARY.md
  handoff/FEASIBILITY_REPORT.md

02_code/data/sources/<source>_v<version>/
  raw/
  source_manifest.json
  records.csv
  exclusions.json
  candidate_audit.csv

02_code/data/prepared/<dataset_version>/
  records.csv
  dataset.csv
  manifest.json
  split_assignments.csv
  sequence_diagnostics.csv

03_experiments/runs/<run_id>/
  manifest.json
  predictions.csv
  ensemble_predictions.csv
  metrics.json
  comparisons.json
  confidence_intervals.json
  model_artifacts/

04_paper/evidence/
  reference_audit.json
  consistency_manifest.json
  claim_registry.csv
```

本文件完成的是整改规范，不代表科学门禁已经通过，也不代表项目已经具备投稿资格。
