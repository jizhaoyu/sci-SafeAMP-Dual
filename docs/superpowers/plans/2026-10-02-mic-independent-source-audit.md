# MIC 独立来源补充审计 Implementation Plan

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补充原始受测分子形式与 MIC 均可核查的来源，并重算五折训练门禁。

**Architecture:** 读取原文 XML/PDF 与补充表，保留全来源的逐记录纳入/暂缓决定。新目录存储证据和哈希；复用冻结的标签与序列比较函数，对最终候选做全员和研究整体分组，再生成新状态。

**Tech Stack:** 现有 Python、requests、ElementTree、pandas、PyMuPDF、scikit-learn；无需新增依赖。

## Global Constraints

- 固定 `protocol-mic-01`、0.40 阈值、5 折、seed 42；MIC 上界 <=32 µg/mL 为阳性，下界 >=128 µg/mL 为阴性。
- 10–50 aa、20 canonical amino acids、linear、modifications none；不把未声明修饰推定为无修饰。
- 原始测定要求具名 *E. coli* 菌株、数值、单位、受测分子和出处；不得转换 IC50、MBC、MIC90、混合物或 D 型肽为域内 MIC。
- 完整来源中相反标签和阈值空档均保留审计，不挑选有利测定；相同序列及同源/原始研究整体合并。
- 不覆盖旧目录、协议、状态、模型；任何门禁失败保持 blocked，不启动训练。

## 文件与责任

- `03_experiments/audits/mic_independent_sources_20261002_v1/raw/`：原始论文、补充材料与渲染。
- `02_code/audit_mic_independent_sources.py`：逐条来源决定、原始端点、身份与来源哈希，生成候选审计。
- `02_code/audit_mic_extended_acid_cohort.py`：原 11 条与新增候选的全员和研究分组；必要条件不足时跨折结果 null。
- `03_experiments/audits/mic_independent_sources_review_20261002_v1/`：逐记录审计与不可覆盖来源清单。
- `03_experiments/audits/mic_extended_acid_cohort_20261002_v1/`：全员对表、组件、分折与新清单。
- README、整改页、任务看板、索引：只在机器状态生成之后更新当前版本和时间。

## Task 1: 原始来源核查

- [x] 下载原文；验证 XML 含 body、PDF 签名、精确原始 URL，并记录 SHA-256。
- [x] 逐表核对序列、端点、菌株、单位、条件及分子形式；图片表渲染后目视核对。
- [x] 对单位/端点冲突、末端形式缺失、修饰与空档分别写明确暂缓/排除原因。
- [x] 保存全部来源决定；只有字段已核实的域内记录进入局部候选，训练释放为 0。

## Task 2: 严格分组与状态

- [x] 调用 `measurement_label(assay, sequence, 32, 128)` 重推导每条标签，完整合并同序列测定并拒绝相反标签。
- [x] 用 `sequence_identity(a, b, identity_mode='alignment')` 比较每一对成员，>=0.40 连边；合并分子与测定共享研究标识。
- [x] 检查组件及含两类组件的必要条件；满足才执行固定 StratifiedGroupKFold，并审核全部跨折边/研究及每折类别。
- [x] 新文件写入前检查不存在；记录来源、协议、脚本、输出哈希。
- [x] 新机器状态生成后同步活动文档，不把局部证据或必要组件数当成训练放行。

## Task 3: 实際验证

- [x] 执行新增脚本，读取实际输出与退出码；`py_compile` 检查新增模块。
- [x] 独立全矩阵全局比对与图遍历核对所有对和组件，逐条复核标签。
- [x] 校验所有新旧来源哈希、当前文档路径/时间/协议和原正式状态哈希。
- [x] 已有输出重复执行必须拒绝；记录软件审计通过与科学训练门禁的分别结论。

## 实际结果

- 原始来源：10 篇完整 XML，70 项决定；新增 4 条局部确认分子、6 条原始 MIC。
- 当前候选版本：`mic_extended_acid_cohort_20261002_v1`，15 条分子、22 条测定、105 对。
- 研究/同源组件：6 个；含阳性 3、含阴性 6。阳性仍至少缺 2 个独立组件，必要条件不满足，未生成五折。
- 状态：`mic_training_readiness_20261002_v9.json`，2026-10-02 16:50:31（Asia/Shanghai），科研仍 blocked，训练释放为 0。
- 独立复核：`mic_independent_progress_validation_20261002_v1.json`；3 个新模块编译退出码 0；3 个已有产物入口拒绝覆盖，见 `mic_independent_immutability_20261002_v1.json`。
- 原协议、旧证据清单及正式双任务状态保持冻结。冻结分组报告中的复跑示例漏写 `audit` 子命令，README 已给出完整命令及更正说明。

已获用户“开始吧”执行授权，直接在当前工作区执行；无需新任务、提交、部署或再次确认。
