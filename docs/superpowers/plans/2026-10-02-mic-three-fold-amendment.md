# MIC 三折前瞻性修订 Implementation Plan

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 依据用户明确选择，评估小样本 MIC 探索研究的三折可行性，保留真实证据和全员零泄漏门禁。

**Architecture:** 先新增不可变 `protocol-mic-06`，绑定当前 15 条候选及旧协议摘要，再执行三折分组审计。运行结果和证据释放状态分开；任何失败不启动训练，不改 seed、标签或样本选择。

**Tech Stack:** 现有 Python、pandas、scikit-learn、原标签及全局比对工具；不新增依赖。

## Global Constraints

- 用户在本轮明确选择“前瞻性修订评估协议，例如评估三折是否可行，继续要求真实证据与零泄漏”。本轮可行性审计已获授权。
- 只将探索线的验证折数由 5 改成 3；继续使用 StratifiedGroupKFold、shuffle=True、seed=42。
- 全员 NW match=2、mismatch=-1、gap=-2，canonical orientation，diagonal/up/left；identity=matches/alignment columns，gap mismatch；>=0.40 同源成员和同原始研究整体分组。
- MIC 标签边界 32/128 µg/mL；10–50 aa、20 canonical、linear、modifications none；不能补写分子身份或标签。
- `protocol-mic-01`、旧五折产物、旧模型和正式双任务状态不覆盖。15 条候选/22 条测定保持冻结；不得依结果删样本、挑 seed 或改阈值。
- 这是样本量受限的探索研究；三折通过不代表完整证据释放，更不代表独立外部验证或正式结果。

## Task 1: 协议冻结

**Create:** `03_experiments/protocols/protocol-mic-06.json`、`docs/amendments/PROTOCOL_MIC_06_THREE_FOLD.md`。

- [x] 记录用户授权、修订原因、前版队列与协议哈希、结论范围、无模型性能参与设计。
- [x] 在首次三折分区运行前创建协议，不覆盖现有路径；记录冻结时间。

## Task 2: 全员与分折审计

**Create:** `02_code/audit_mic_three_fold.py`、`03_experiments/audits/mic_three_fold_20261002_v1/`。

- [x] 校验原始来源清单及脚本摘要，重推导 22 条测定标签。
- [x] 重算全部 105 对成员及同研究组件；固定三折一次分区，逐折核查训练/验证都有两类。
- [x] 逐对审核跨折超阈值边，逐来源审核论文泄漏；失败保持 blocked，不搜索参数。
- [x] 输出完整组件、折角色、类别数量、原始来源和协议哈希；训练释放为 0。

**Run:** `python 02_code/audit_mic_three_fold.py --output 03_experiments/audits/mic_three_fold_20261002_v1`

预期：产生新的审计清单；实际门禁状态取决于固定分折结果。

## Task 3: 独立复核与状态

**Create:** `02_code/validate_mic_three_fold.py`、新的不可覆盖机器声明及复核记录。

- [x] 独立全矩阵回溯重算全部成员对、图分量与标签，复核每条 train/validation 分区。
- [x] 若结构通过，状态明确为“分折通过、完整证据释放阻断”，不直接改成训练 ready。
- [x] 读取真实生成时间和协议版本后，同步 README、整改页、任务看板、索引、筛查页。
- [x] 编译新增脚本；重复运行对已有目录必须拒绝；校验旧正式状态哈希未改变。

若三折无法通过，本轮仍以新的协议和真实失败原因交付，继续按零泄漏原则补证据。

## 实际结果

- 协议冻结时间 2026-10-02 09:12:09 UTC；首次审计 09:15:10 UTC，状态 v10 09:20:14 UTC；未先运行再补写修订。
- 三折结构门禁 passed：验证阳性/阴性 2/4、1/4、1/3；训练 2/7、3/7、3/8；跨折同源和原始研究均为 0。
- 独立复核于 09:30:16 UTC 完成：105 对、22 条测定、45 条角色、六个历史清单及五份当前文档通过。初次逐字符串比较发现两处归一化浮点文本的 CSV 往返差异，核查原始字段完全一致；复核仅对归一化数值使用绝对 1e-12 容差，标签仍独立重算。
- 两个新增脚本 py_compile 退出 0；审计、状态生成和复核三个覆写尝试均退出 1 并拒绝已有输出，全部产物哈希不变。正式双任务状态摘要保持不变。
- 整体状态 blocked：完整原始证据释放尚未完成，新训练协议待冻结；本轮没有训练模型或产生性能结果。
