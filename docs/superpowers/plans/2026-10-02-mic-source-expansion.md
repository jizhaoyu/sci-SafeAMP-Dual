# MIC 实测来源扩充 Implementation Plan

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不修改既有结果、标签和隔离规则的前提下，审查一批新的公开原始 MIC 来源，形成可追溯的候选扩充审计。

**Architecture:** 新增 protocol-mic-08，仅授权来源检索、证据审查和候选分组可行性检查。先冻结检索边界，保存原文及检索响应摘要，再对各论文所有可对应的肽与 E. coli MIC 记录纳入、暂缓或排除决定。新候选不自动获得训练许可；已完成的 protocol-mic-07 运行和 v12 状态保留。

**Tech Stack:** 现有 Python、requests、pandas、XML/PDF 解析工具及严格全局比对实现，不新增依赖。

## Global Constraints

- 原 protocol-mic-01/06/07、当前 15 条分子与 22 条测定、训练运行、v12 和原正式状态保持原样。
- 同一分子必须有明确序列、线性标准 L 氨基酸形式、游离末端及真实 MIC 依据；长度 10–50 aa。
- 32/128 µg/mL 标签边界、单位转换、阈值空档、删失标记和冲突处置保持原规则。
- 全员阈值 >=0.40 的传递闭包与同一原始研究整体分组继续执行；不丢弃桥接记录，不挑种子或折参数。
- 只执行源审计；没有完整证据释放和新的冻结训练协议，不启动扩充队列训练。
- 当前基线性能已知，扩充阶段明确为后续探索；不得宣称这批数据曾用于原训练前的预注册。

---

### Task 1: 冻结扩充审查协议

**Files:**
- Create: `03_experiments/protocols/protocol-mic-08.json`
- Create: `03_experiments/audits/protocol_mic_08_freeze_20261002_v1.json`
- Create: `docs/amendments/PROTOCOL_MIC_08_SOURCE_EXPANSION.md`

- [x] 保存固定检索主题、化学与端点边界、全部候选决定要求、既有数据和协议摘要。
- [x] 先保存协议摘要及冻结时间，再开始新来源检索与候选标签推导。

### Task 2: 多来源检索和原文审查

**Files:**
- Create: `03_experiments/audits/mic_source_expansion_20261002_v1/`
- Create: `02_code/fetch_mic_expansion_sources.py`
- Create: `03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/`

- [ ] 以 PubMed/Europe PMC 和 OpenAlex/出版方原文作为两个发现渠道，保存可重复的查询及响应。
- [ ] 对数据库/搜索结果仅作线索；下载原始 XML/PDF/补充文件后核查标题、引用、许可证与原始文件摘要。
- [ ] 保存全部遇到的论文去重与检索失败记录，不把以前的论文或重新发表的测定当成独立研究。
- [ ] 检查每篇进入详细审查的所有对应分子，记录纳入、阈值空档、化学形式、端点、目标、冲突或缺证据决定；PDF 表格和序列图按 PDF 技能目视复核。

### Task 3: 可复跑证据与结构审计

**Files:**
- Create: `02_code/audit_mic_source_expansion.py`
- Create: `03_experiments/audits/mic_source_expansion_20261002_v1/manifest.json`
- Create: `03_experiments/audits/mic_source_expansion_20261002_v1/report.md`

- [ ] 从原始测定重新推导候选标签，去重分子身份；对原 15 条和所有证据充分的新候选全员比较，输出每对一致性及研究/同源组件。
- [ ] 固定三折仅做可行性审查；所有候选决定先于分折，禁止根据分折结果删样本或改种子。
- [ ] 输出门禁失败与未解决证据；拒绝覆盖已有目录；不产生扩充队列模型。
- [ ] 运行新脚本语法检查和证据/分组审计，读取实际输出后报告新增记录及独立组件数量。

```powershell
python -m py_compile 02_code/audit_mic_source_expansion.py
python 02_code/audit_mic_source_expansion.py --output 03_experiments/audits/mic_source_expansion_result_20261002_v1
```

### Task 4: 交付来源审计并维持状态一致

**Files:**
- Modify: `README.md`
- Modify: `docs/REMEDIATION_STATUS.md`
- Modify: `docs/DOCUMENTATION_INDEX.md`
- Modify: `docs/handoff/TASK_STATE.md`
- Modify: `03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md`
- Create: `03_experiments/audits/mic_three_fold_run_validation_20261002_v3.json` 和 Markdown

- [ ] 将来源扩充进展链接到五份文档；v12 已完成的训练状态不因新候选未释放而撤销。
- [ ] 将旧文档复核标记为历史快照，用既有产物复核脚本验证当前五份文档，确认正式状态与旧模型未变。

```powershell
python 02_code/validate_mic_three_fold_run.py --run 03_experiments/runs/mic_three_fold_20261002_v1 --output 03_experiments/audits/mic_three_fold_run_validation_20261002_v3.json --state 03_experiments/audits/mic_training_readiness_20261002_v12.json --check-documents
```

- [ ] 交付原始来源、逐条决定、全员审计和报告；无法通过的证据明确保持暂缓，不声称已增加可训练样本。

## 交接时点记录

2026-10-02，用户改为要求生成 Gemini 具体交接提示；本轮停止继续来源审查，按该要求交付提示文件。

- Task 1 的协议与冻结记录已真实完成：protocol-mic-08 冻结于 2026-10-02 19:22:32（Asia/Shanghai）。
- 来源清单已固定；`02_code/fetch_mic_expansion_sources.py` 已执行，`mic_source_expansion_acquisition_20261002_v1` 于 19:28:33 保存 12 个来源的获取结果，其中 8 个有正文 XML/PDF。
- OpenAlex 四条查询均返回 429；brucin2020 下载失败；apidaecin2009 和 neopeptides2005 的 XML 请求返回 500。失败响应不能作为原文，元数据和可取得正文均保留。
- Task 2 的完整逐分子证据审查、Task 3 的扩充审计脚本/候选分组及 Task 4 的状态文档更新尚未完成；新训练释放为 0。
- 交接提示：`docs/handoff/GEMINI_MIC_SOURCE_EXPANSION_20261002.md`。既有 v12 训练完成状态、协议、原数据和模型保持原样。
