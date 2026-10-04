# 三折前瞻性修订的固定分区审计

用户明确授权三折可行性修订；protocol-mic-06 和冻结记录先于本审计保存。以同一 15 条分子、22 条 MIC 重算，标签、分子域、0.40 全员同源和原始研究分组均保持原规则。

全部 105 对，6 个不可拆分组件（含阳性 3、含阴性 6）。固定 StratifiedGroupKFold(3, shuffle=True, seed=42) 分区门禁为 passed；没有搜索 seed 或删样本。

| 折 | 训练阳性/阴性 | 验证阳性/阴性 | 两类条件 |
| --- | --- | --- | --- |
| 0 | 2/7 | 2/4 | True |
| 1 | 3/7 | 1/4 | True |
| 2 | 3/8 | 1/3 | True |

跨折超阈值成员边 0；跨折原始研究 0。完整原始证据释放仍未完成，新训练协议未冻结，训练释放为 0，总状态 blocked。小样本三折仅适用于探索，不能用于正式双任务、外部泛化或临床结论。

- Full primary-evidence release is incomplete; no separate frozen training protocol exists.

复跑：`python 02_code/audit_mic_three_fold.py --output 03_experiments/audits/mic_three_fold_my_run`；输出必须是新目录。
