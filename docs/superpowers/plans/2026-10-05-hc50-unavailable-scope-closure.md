# 缺原文37条候选退出本轮审查计划

> **For agentic workers:** 按共享工作区约定顺序执行，以实际产物记录复选框；不覆盖历史审计。

**Goal:** 执行用户停止检索缺原文37条的决定，形成当前41条审查范围及可追溯的37条归档清单。

**Architecture:** 绑定前一批78条及摘要 → 根据`screen_status=original_not_acquired`精确提取37条 → 新版本保存41条范围、37条范围排除和78条累计表 → 核对覆盖、历史保护与文档状态。

**Tech Stack:** 当前Python标准库CSV/JSON/hashlib；沿用现有机器审计表格式，不新增依赖。

## Global Constraints

- 37条退出本轮审查，不继续网络获取、不发邮件；历史原文尝试、记录和论文标识保留。
- 退出理由为来源尚未取得及用户收缩范围，不代表实验不存在、阴性或分子形式不合格。
- 其余41条逐字段保持原审查决定；其中已按形式排除的9条继续排除，尚待证据的32条不自动准入。
- `protocol-amd-02`、>=0.40全员隔离、标签与形式门禁保持原样；原双任务仍blocked，MIC探索状态v26不变。
- 新产物位于`03_experiments/audits/hc50_unavailable_scope_closure_20261005_v1`，输出存在时拒绝覆盖。
- 本次仅范围及数据一致性核查，不新增测试、不训练、不提交或推送。

## Task 1：生成范围收缩审计

文件：新建本批`scripts/close_scope.py`；输入前一批`review/manifest.json`及`merged_candidate_decisions.csv`。

- [x] 校验前一批、冻结历史和当前机器状态摘要；绑定用户范围决定。
- [x] 生成`current_scope_records.csv`（41条，逐字段不变）、`scope_exclusions.csv`（37条退出决定）、`merged_candidate_decisions.csv`（78条追溯清单）、`summary.json`和报告。
- [x] 37条新决定使用`excluded_from_current_scope_original_unavailable`，保留`original_not_acquired`事实及旧理由；明确当前未完成原文检索待办为0、归档缺原文记录为37。

## Task 2：核查与导航

文件：本批`verification.json`、`README.md`；根`README.md`的最新证据检查点；本计划复选框。

- [x] 检查37+41=78、ID唯一、25个来源对，41条原样、37条仅范围决定变化、无准入标签或模型变化。
- [x] 核对历史保护文件以及五份当前状态块；用新输出目录复跑，内容仅允许生成时间不同。
- [x] 根README明确历史37条仍有访问缺口，但已退出当前检索待办；保存报告链接和真实状态。

实际验收：两份输出均通过`verify`，核对344份保护文件、5份输出及五份当前状态块。三份CSV复跑字节一致，summary/report仅时间不同，见本批`reproduction_check.json`。37条退出，41条保留原结论；正式外部准入0，未训练或发起新网络请求。
