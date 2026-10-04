# MIC 候选推进验证记录（2026-10-02）

当前机器状态：[readiness v7](mic_training_readiness_20261002_v7.json)。候选数据版本为 `mic_reviewed_subset_groups_20261002_v3`，审计协议为 `protocol-mic-01`。新训练协议未冻结，训练释放数为 0。

## 已执行检查

| 检查 | 实际结果 | 范围 |
| --- | --- | --- |
| 5 个新增审计及状态脚本 `py_compile` | 通过 | Python 语法；不等于所有行为已测试 |
| `python -m pytest 02_code/tests/test_protocol_contract.py 02_code/tests/test_research_data.py -q` | `32 passed in 1.14s` | 已有协议与研究数据回归；不是模型性能验证 |
| 重新逐对调用 `sequence_identity(..., identity_mode='alignment')` | 820/820 与结构审计值一致 | 全部 41 条候选，不只比对代表序列 |
| 固定五折复核 | 5/5 折训练、验证均具备两类；跨折超阈值同源边和论文标识均为 0 | 未改变 0.40、5 折或 seed 42 |
| 结构及证据 manifest 哈希复核 | 通过 | 新输出与其冻结输入；不证明未复核的化学形式正确 |
| 仅调用旧 `train_mic_baselines.load_and_validate(protocol-mic-05)` | 抛出 `PrimaryStudyReviewRequired`，指出 458 条原文靶标确认未完成 | 旧训练入口仍拒绝；未调用模型训练 |
| Bhaumik 额外来源哈希及排除状态 | 通过 | CC BY-NC-ND 4.0、删失标记待核实；未并入 41 条候选，释放数为 0 |
| 主要状态文档检索 | 当前入口均指向 v7；旧 v6 引用仅出现在注明历史的纠错记录 | README、整改状态页、文档索引与数据审计报告 |

新增脚本为 `audit_mic_primary_ludwig2022.py`、`audit_mic_reviewed_subset_ludwig.py`、`audit_mic_candidate_release.py`、`mic_training_readiness_v7.py` 和 `audit_mic_primary_bhaumik2024.py`，均位于 `02_code/`。

## 未完成及检查限制

- 41 条候选中仍有 34 条分子的身份或补充证据待核实，详见[逐分子审查队列](mic_candidate_release_review_20261002_v1/molecule_review_queue.csv)。7 条局部确认分子未组成已释放训练队列。
- 证据筛选后的最终队列必须再次执行完整隔离和类别覆盖检查；不能直接继承候选的结构通过状态。
- 没有训练、调参或新增模型结果；原双任务正式状态未修改。
- 本次没有运行全量软件回归。`git diff --stat` 无法使用：当前目录未被 Git 识别为工作树；未创建或推送提交。
