# 本地交付演示

目的：展示冻结包可验证、已准入样本的 OOF 可重放、预测可追溯原始证据。演示限定于既有 MIC 探索成果。

## 1. 展示研究边界

打开 [研究报告](D:/桌面文件/sci/04_paper/reports/mic_baseline_report_20261005_v1/report.md) 和 [机器结案状态](D:/桌面文件/sci/03_experiments/audits/project_closeout_20261005_v1/review/project_delivery_status.json)：17 分子，三类基线，9 折模型；原 MIC/HC50 双任务仍 blocked，没有独立外部验证。

## 2. 验证冻结包

使用冻结版本环境，输出留在包外。以下命令直接写终端输出，不改变模型和数据：

```powershell
Set-Location 'D:\桌面文件\sci\03_experiments\deliveries\mic_baseline_20261004_v1'
python -I -B runtime.py verify --bundle . --manifest-sha256 f8b8606dc807279cc78c6728260f6d3d7da463f2416bf47e8d3bafbdf1789ed3
```

展示输出中的验证状态、9 模型重载、51 条 OOF、fit=0 及缩放器检查。若命令失败，保留输出并停止演示，不能跳过摘要或环境检查。

## 3. 重放一个已准入分子

```powershell
python -I -B runtime.py replay --bundle . --manifest-sha256 f8b8606dc807279cc78c6728260f6d3d7da463f2416bf47e8d3bafbdf1789ed3 --sample-id 3e656d2ae8d48ae33078fcd4
```

输出为该分子唯一留出折上的三类模型结果；不能把三个结果当作三次独立外部实验。运行时只接受已准入 ID，没有面向任意新分子的有效性声明。

## 4. 证据追溯

在 [分子表](D:/桌面文件/sci/03_experiments/deliveries/mic_baseline_20261004_v1/cohort/candidate_molecules.csv) 定位相同 sample_id，关联 [测定表](D:/桌面文件/sci/03_experiments/deliveries/mic_baseline_20261004_v1/cohort/candidate_observations.csv)，查看 target、raw_mic、raw_unit、normalized_low_ug_ml、normalized_high_ug_ml、derived_label、primary_locations 和 condition_limitations。再由 [原始来源索引](D:/桌面文件/sci/03_experiments/deliveries/mic_baseline_20261004_v1/evidence/source_index.json) 的 bundle_primary_file 打开包内原文。检查具体位置及分子形式，不能用同名肽、引用的方法论文或数据库类别代替该条实验依据。

## 5. 展示全部结果与结束

展示报告表 3、表 4，包含 Dummy、LR、RF 全部结果。说明 Dummy 跨折类别比例的影响、小样本及无外部验证的限制。结束时区分“MIC 探索包已交付”与“原双任务未完成”。

## 已完成验收与本次脚本说明

上述 verify/replay 的工作区外运行已有 [实际验收记录](D:/桌面文件/sci/03_experiments/audits/project_closeout_20261005_v1/delivery_check/summary.json)，时间为 2026-10-05T05:04:43.628080+00:00。本文件是演示脚本；报告编写阶段不把历史运行重新标记为本次执行。
