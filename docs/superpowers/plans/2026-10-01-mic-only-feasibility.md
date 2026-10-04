# MIC-only 数据集与五折可行性审计实施计划

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 417 条已准备记录和 4 条 DRAMP 原文核实候选，冻结独立的 MIC-only 研究协议，审计 MIC 证据覆盖、全员同源组和五折标签可行性。

**Architecture:** 保持 `legacy-v1`、`protocol-amd-01`、`protocol-amd-02` 及其哈希和正式状态原样。新协议采用单独的版本化 JSON 与摘要；专用审计脚本复用现有记录来源验证、标签重算、全局 Needleman–Wunsch 一致性和 `StratifiedGroupKFold`，只生成新的可审查审计目录，不写正式模型目录。

**Tech Stack:** Python、pandas、scikit-learn `StratifiedGroupKFold`、现有 `research_data.validate_records` 和 `assay_records`。

## Global Constraints

- 只分析 *E. coli* MIC 单任务；不得将 HC50 纳入训练目标。
- MIC `<=32 µg/mL` 为阳性，`>=128 µg/mL` 为阴性，中间区间或无法判定的删失值保留为未知。
- 纳入对象为 10–50 aa 的线性、标准氨基酸、未修饰肽；每个标签必须能由原始实验观察重算。
- 全员全局比对一致性以 `matches / aligned_columns` 计算，含 gap 列按不匹配处理，超阈值为 `>=0.40`。
- 同源连通分量不得跨五折；固定 5 折与 seed 42；任何门禁失败保持 `blocked`，不训练、不生成性能结果。
- 新建输出目录必须有版本号且不存在时才创建；不得覆盖旧协议、正式准备集或先前审计目录。

---

### Task 1: 冻结 MIC-only 协议记录

**Files:**
- Create: `03_experiments/protocols/protocol-mic-01.json`

**Interfaces:** 记录协议 ID、版本、目标端点、标签阈值、纳入范围、序列算法参数、相似度门槛、折数、seed 和训练放行门槛；审计脚本计算 JSON 规范化 SHA-256 并在清单记录。

- [x] 写入 `protocol-mic-01` v1 完整定义；字段包含 `task=ecoli_mic_binary`、阳性/阴性阈值 `32/128 µg/mL`、灰区未知、长度 `10..50`、未修饰线性序列、`alignment_identity=matches/aligned_columns`、Needleman–Wunsch `match=2,mismatch=-1,gap=-2`、全成员、cutoff `0.40`、5 folds、seed 42。
- [x] 声明五折每个验证折与训练部分都必须有正负两类；单一来源研究的重复序列/样本合并后再分折；外部留出不是 MIC-only 五折必需条件。
- [x] 保留 `protocol-amd-02` 等现有协议文件与摘要不变。

### Task 2: 构建 MIC-only 证据盘点与折审计脚本

**Files:**
- Create: `02_code/audit_mic_only_cohort.py`
- Reuse: `02_code/research_data.py`, `02_code/assay_records.py`, `02_code/feature_extractor.py`

**Interfaces:** CLI 参数 `--records`, `--supplement`, `--protocol`, `--output`；输出协议哈希清单、筛选/排除表、记录级证据核验表、全成员成对同源表、组件成员表、固定五折分配表、折类别覆盖表及 Markdown 判定。返回状态仅为 `feasible_for_training_review` 或 `blocked`，绝不训练模型。

- [x] 载入 417 条记录和候选补充表，先通过现有原始证据验证器重算其 AMP 标签；原始证据失败的记录进入拒绝表。
- [x] 只保留协议规定长度、标准序列、未修饰且具有可判定 MIC 标签的分子；同序列来源先合并并报告标签冲突。
- [x] 按全局比对协议逐对计算相似度；用 `>=0.40` 边构建连通分量，并把组件整体传入固定种子的 5 折分层分组切分。
- [x] 报告全队列正负数、唯一分子数、独立同源组件数、最大组件、每折训练/验证正负数、来源研究数、证据失败与排除原因。
- [x] 任一类别样本不足、任一分折缺类、同源组件数不足、证据验证失败或标签冲突未决时，输出 `blocked`，仍保存完整诊断结果。
- [x] 拒绝已存在的输出目录，避免覆写历史审计。

### Task 3: 运行数据盘点与可行性审计

**Files:**
- Create: `03_experiments/audits/mic_only_cohort_20261001_v2/` 下脚本声明的所有结果。

- [x] 使用 `03_experiments/prepared/amd02_evidence_clean_20261001/records.csv` 作为 417 条输入，使用 `03_experiments/audits/dramp_verified_ecoli_mic_20261001_v5/records.csv` 作为四条补充输入。
- [x] 运行记录级来源核验和 MIC 标签重算。
- [x] 运行全员相似性和五折分组可行性分析。
- [x] 核对 manifest 中输入文件 SHA、协议 SHA、行数和状态与所有结果文件一致；本轮止于训练前评审，不训练。

### Task 4: 报告项目状态与下一阻塞项

**Files:**
- Modify: `03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md`

- [x] 追加 MIC-only 协议、记录覆盖与五折审计结果链接。
- [x] 明确正式 417 条队列、旧协议与正式结果状态未被改变。
- [x] 写明类别、同源组件和折大小风险；不写“正式放行”或性能结论。

## Acceptance

- 旧协议摘要保持原值；新协议 ID、定义与 SHA 被新审计 manifest 引用。
- 417 条原始记录和 4 条候选均经过实验来源和 MIC 标签重算门禁。
- 每一对合并候选的相似度可回查；任一 `>=0.40` 的序列只能进入同一折。
- 五折类覆盖满足协议才判为可进入训练评审；本计划不训练模型。
- 成功通过类别与组件隔离门禁不抹去折大小高度不均衡这一审阅风险。

后续纠错记录：本计划当时使用的 DRAMP v5 中，PLP2 的结构化测定条件与原始证据不一致。当前有效版本为 DRAMP v6、MIC 审计 v3、探索性基线 v3；详见 `03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md`。本计划保留原始版本号作为历史执行记录。
