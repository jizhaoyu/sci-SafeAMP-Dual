# Gemini 证据门禁与状态修复 Implementation Plan

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复已复现的证据放行、来源映射、外部候选硬编码、ESM2 冻结和状态冲突问题，保持未核实的数据阻断。

**Architecture:** 当前入口调用共享证据门禁；历史脚本先按原摘要归档，历史模型只经不允许 fit 的独立产物检查。新增不可覆盖的证据整改目录和 v16 审查状态，五份文档的当前状态块由同一状态渲染。

**Tech Stack:** 现有 Python、pandas、numpy、scikit-learn、pytest、标准库 XML/hashlib；不新增依赖。

## Global Constraints

- 同源阈值 0.40、全员比较、固定三折 seed 42、真实测定及分子身份要求保持原定义。
- 原双任务 `protocol-amd-02`、所有冻结协议 JSON/冻结记录、旧数据/运行目录和 v12–v15 状态不覆盖。
- 不重新训练、不补写标签、不把多菌株范围改写成单株测定、不操作云服务器。
- 本地文件改动使用补丁；运行前拒绝覆盖任何已有审查输出目录。
- 仅检查已有模型预测；验证过程禁止模型与缩放器 fit。

### Task 1: 保存修复前材料

**Files:**
- Create: `03_experiments/audits/gemini_repair_20261003_v1/original_sources/` 和 `archive_manifest.json`

**Interface:** 原源码/状态文档字节复制；清单记录原路径、归档路径、SHA-256 和真实归档时间，供历史产物校验使用。

- [x] 保存受影响的 Gemini 脚本和五份当前状态文档；读取复制文件并确认摘要相同。
- [x] 把前轮独立检查的八个受保护摘要绑定到修复验证，修复后重新检查。

### Task 2: 阻止无证据释放的入口

**Files:**
- Create: `02_code/research_evidence_gate.py`
- Modify: `02_code/train_mic_three_fold_v3.py`
- Modify: `02_code/train_mic_esm2_three_fold.py`

**Interface:** `require_primary_release(protocol, freeze_path, entry_path) -> dict`，返回绑定且完整的原始证据释放清单；缺失、数量/覆盖/摘要不符、未通过均抛出 `ValueError`。

- [x] 复用既有 15 条完整释放表格式：`molecule_evidence_review.csv`、`assay_evidence_review.csv`、`source_review.csv`；绑定原文件摘要、测定原值/单位/对象及分子批准状态。
- [x] 冻结文件必须存在；证据释放 manifest 必须由协议路径及 SHA 绑定。
- [x] 两个入口先调用门禁，准入状态取实际释放结果，删除直接写入完整释放通过的逻辑。

关键调用：

```python
release = require_primary_release(protocol, FREEZE, Path(__file__))
approved = release["molecules_evidence_approved"]
```

验证：原 protocol-mic-09/10 没有释放清单，应拒绝；真实 protocol-mic-07 的既有完整证据表可经共享门禁检查；模拟冻结文件缺失时应拒绝。

### Task 3: 纠正来源并撤销未经验证的外部资格

**Files:**
- Create: `02_code/audit_mic_evidence_repair.py`
- Modify: `02_code/audit_mic_source_expansion.py`（旧入口转到完整证据整改审查，不再生成未经核实的准入队列）
- Modify: `02_code/curate_dual_task_external_evidence.py`
- Create: `03_experiments/audits/mic_evidence_repair_20261003_v1/`
- Create: `03_experiments/audits/dual_task_external_curation_20261003_v2/`

**Interfaces:** `audit(output: Path) -> dict` 写入来源更正表、逐记录审查状态和哈希清单；`curate_dual_task_evidence(...) -> dict` 仅生成待原始测定复核候选，未绑定证据的资格数始终为 0。

- [x] 从保存 XML 的 article-meta 实际提取 DOI/PMID/PMCID，不把全文参考文献 ID 当论文 ID。
- [x] 保留原字段与更正依据；HTTP 错误正文不可作为文献；未知身份不猜测。
- [x] BMAP-27B 多菌株聚合行标为 withheld，删除其批准标签，保留原范围作为审查线索。
- [x] 旧 15 条批准仅按原完整释放清单确认；两条新增候选均未完成整队列释放。
- [x] 外部审查删除按 DRAMP ID 写死的 MIC、HC50、二值标签及“已确证”分支；已有引用文本作为候选线索保留。

运行：

```powershell
python -X utf8 02_code/audit_mic_evidence_repair.py --output 03_experiments/audits/mic_evidence_repair_20261003_v1
python -X utf8 02_code/curate_dual_task_external_evidence.py --output 03_experiments/audits/dual_task_external_curation_20261003_v2
```

### Task 4: ESM2 完整绑定及历史产物复核

**Files:**
- Modify: `02_code/extract_mic_esm2_features.py`
- Create: `02_code/validate_mic_historical_artifacts.py`
- Create: `03_experiments/audits/gemini_repair_20261003_v1/historical_artifacts.json`

**Interface:** `validate(output: Path) -> dict` 只重载 protocol-mic-09/10 的历史模型；输出全产物摘要、独立预测/指标检查及审查限制，永不生成训练准入状态。

- [x] 提取器拒绝已有输出目录；新元数据绑定序列次序、脚本、预训练 checkpoint SHA、torch/fair-esm/numpy 环境。
- [x] 历史复核使用归档脚本摘要证明原协议绑定，检查已保存特征、模型、预测和指标。
- [x] 所有模型、缩放器及 Pipeline 的 fit 被 mock 禁止；27+9 模型预测及阈值计数独立重算。
- [x] 完整产物摘要生成于真实修复时间，标明为后续绑定，不冒充前瞻性冻结。

### Task 5: 生成统一的阻断审查状态

**Files:**
- Create: `02_code/publish_mic_repair_status.py`
- Create: `03_experiments/audits/mic_training_readiness_20261003_v16.json`
- Modify: `README.md`
- Modify: `docs/REMEDIATION_STATUS.md`
- Modify: `docs/DOCUMENTATION_INDEX.md`
- Modify: `docs/handoff/TASK_STATE.md`
- Modify: `03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md`

**Interfaces:** `publish(output: Path) -> dict` 验证整改产物并写入 v16；`render_current_status(state) -> str` 生成五页相同的当前状态块；`validate_documents(state) -> None` 比较完整状态块并拒绝当前块内的旧版本/错误字段。

- [x] 当前状态为 `historical_training_completed_evidence_review_blocked`；当前训练协议/训练命令为 null，新增队列释放为 0。
- [x] 历史训练完成、产物复核通过与当前科学准入阻断分别记录，旧 15 条基线单列。
- [x] 协议 ID、真实生成时间、数据路径在五份当前状态块中一致；旧 v12/v14/v15 均明确为历史或被后续审查撤销准入结论。
- [x] 更正 RF 的历史 TP 为 4，不保留“当前 v12”或“已确证外部一条”的当前结论。

### Task 6: 验证与交付

**Files:**
- Create: `02_code/tests/test_evidence_gate_repair.py`
- Create: `03_experiments/audits/gemini_repair_20261003_v1/verification.json` 和修复报告

- [x] 按用户工作约定验证修复：完整释放表、缺失释放、缺失冻结、错误原文标识、外部 ID 不产生资格、拒绝覆盖、状态块不一致。
- [x] 运行针对性 pytest，保存实际结果；相关现有门禁用例一起运行。
- [x] 再检查受保护八个摘要、所有原运行产物、全部协议/冻结状态及 v12–v15；记录未执行全量测试和云端验证。
- [x] 交付当前状态、源更正、回归结果；证据无法补齐的项继续 blocked。

## 完成记录

2026-10-03 11:55:49（Asia/Shanghai）完成验证归档。38 项针对性回归通过；36 个扩充队列历史模型及 9 个旧基线模型重载复算通过；99 个受保护文件与 12 份原始归档摘要一致；五份当前状态文档一致。

软件修复已完成；新增队列及原双任务的证据准入继续阻断。未运行全量测试，未重新训练或执行云端操作。交付报告：`03_experiments/audits/gemini_repair_20261003_v1/repair_report.md`；机器验证：同目录 `verification.json`。
