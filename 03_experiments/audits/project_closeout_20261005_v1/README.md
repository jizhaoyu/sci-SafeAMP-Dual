# 本批证据结案与MIC交付

机器状态时间2026-10-05T05:05:20.652390+00:00，版本`project_closeout_20261005_v1`。

- [项目交接入口](D:/桌面文件/sci/docs/handoff/PROJECT_CLOSEOUT_20261005.md)
- [结案报告](review/report.md)与[机器状态](review/project_delivery_status.json)
- [30条逐记录最终决定](review/final_evidence_decisions.csv)、[当前41条范围](review/current_scope_records.csv)、[累计78条追溯](review/merged_candidate_decisions.csv)
- [合格外部表（0条）](review/eligible_external_records.csv)
- [全部模型指标](review/mic_all_model_metrics.csv)
- [工作区外ZIP运行检查](delivery_check/summary.json)、[包内复核](delivery_check/verify.json)、[单个样本重放](delivery_check/replay.json)
- [来源/保护/输出摘要](review/manifest.json)、[核查结果](review/verification.json)、[复跑比较](reproduction_check.json)

本批证据已结案：30条本批不准入，11条形式排除、37条缺原文归档，共78条完整追溯；继续检索待办0，合格外部0。原双任务仍blocked，原科学目标未完成，正式结果/投稿false。隔离未执行，不写成通过。

MIC探索17样本、9模型、51OOF已可交接，复用原冻结包。实际核对394份绑定文件及ZIP395份文件，在工作区外解压并用`python -I -B`运行包内verify/replay；零fit，所有指标/缩放器通过，临时目录已安全清理。

## 本地复跑

在`D:/桌面文件/sci`执行，输出路径必须不存在。`close`仅消费已保存交付检查和原始审计，不启动网络或训练：

```powershell
python 03_experiments/audits/project_closeout_20261005_v1/scripts/closeout.py close --delivery-check 03_experiments/audits/project_closeout_20261005_v1/delivery_check --output 03_experiments/audits/project_closeout_20261005_v1/review_my_run
python 03_experiments/audits/project_closeout_20261005_v1/scripts/closeout.py verify --review 03_experiments/audits/project_closeout_20261005_v1/review_my_run --output 03_experiments/audits/project_closeout_20261005_v1/review_my_run/verification.json
```

若需重新做ZIP及包内运行检查，使用`check-delivery --output <本批中的新目录>`，不要覆盖本次输出。既有训练包及ZIP均未改写；闭案不会改变科学准入。
