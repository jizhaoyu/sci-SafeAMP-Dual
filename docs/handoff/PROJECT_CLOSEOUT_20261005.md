# 项目收尾与交付指南

结案时间：2026-10-05 13:05:20（Asia/Shanghai，05:05:20 UTC）。结案版本`project_closeout_20261005_v1`。

## 交付结论

| 工作 | 实际状态 |
|---|---|
| MIC探索训练 | 已完成：17分子、42条测定表述、44维特征、固定三折、9模型、51条OOF |
| MIC模型及结果交付 | 本轮ZIP解压至工作区外实际运行通过；重载9模型、复算51条OOF、核对全部指标与缩放器，零fit |
| 本批外部证据审查 | 已结案：30条本批不准入、11条形式排除、37条缺原文归档；继续检索待办0 |
| 合格独立外部队列 | 0条；跨队列隔离未执行，原因是没有证据合格记录 |
| 原MIC/HC50双任务目标 | 未完成，仍blocked；正式结果与投稿就绪false |

当前可交接内容为固定方案的MIC小样本探索结果及完整证据审计。原双任务的科学目标尚未达成；工程包验收不会改变其状态。

状态来源：[本批机器结案状态](D:/桌面文件/sci/03_experiments/audits/project_closeout_20261005_v1/review/project_delivery_status.json)。MIC状态仍为v26，训练协议`protocol-mic-13`；外部证据继续沿用`protocol-amd-02`及>=0.40全员隔离规则。

## 文件交接

- [MIC训练交付ZIP](D:/桌面文件/sci/03_experiments/deliveries/mic_baseline_20261004_v1.zip)：58,090,263字节，含9模型、特征、样本/折角色、OOF、全部指标、协议、证据与独立运行时。
- [结案报告](D:/桌面文件/sci/03_experiments/audits/project_closeout_20261005_v1/review/report.md)。
- [30条最终证据决定](D:/桌面文件/sci/03_experiments/audits/project_closeout_20261005_v1/review/final_evidence_decisions.csv)：逐条阻断类别、原文审计依据和重新打开所需证据。
- [78条完整追溯表](D:/桌面文件/sci/03_experiments/audits/project_closeout_20261005_v1/review/merged_candidate_decisions.csv)：37条归档及11条原形式排除决定不变。
- [所有模型的完整描述性指标](D:/桌面文件/sci/03_experiments/audits/project_closeout_20261005_v1/review/mic_all_model_metrics.csv)。
- [本轮工作区外交付运行检查](D:/桌面文件/sci/03_experiments/audits/project_closeout_20261005_v1/delivery_check/summary.json)：stdout/stderr、退出码、verify/replay结果在同目录。
- [本批覆盖及保护核查](D:/桌面文件/sci/03_experiments/audits/project_closeout_20261005_v1/review/verification.json)。

| 摘要对象 | SHA256 |
|---|---|
| ZIP | `858f6aa9a09dfc822b6a7c155a629ae13caf0e2c922abe3448d81119e3491b2b` |
| 包内manifest.json | `f8b8606dc807279cc78c6728260f6d3d7da463f2416bf47e8d3bafbdf1789ed3` |

ZIP的394份绑定文件及manifest共395份文件，本轮内容/CRC核对通过。包保持原样，来源资料用于本地研究交接；公开再分发范围遵守包内`LICENSE_NOTICE.md`逐项说明，打包不产生额外授权。

## 如何使用现有交付包

环境必须匹配冻结版本：Python3.11.9、numpy2.4.4、pandas3.0.2、scikit-learn1.8.0、joblib1.5.3。交付目录内已有`runtime.py`与环境说明。以下两条命令的等价ZIP解压版本已在本轮工作区外运行成功：

```powershell
Set-Location 'D:\桌面文件\sci\03_experiments\deliveries\mic_baseline_20261004_v1'
python -I -B runtime.py verify --bundle . --manifest-sha256 f8b8606dc807279cc78c6728260f6d3d7da463f2416bf47e8d3bafbdf1789ed3
python -I -B runtime.py replay --bundle . --manifest-sha256 f8b8606dc807279cc78c6728260f6d3d7da463f2416bf47e8d3bafbdf1789ed3 --sample-id 3e656d2ae8d48ae33078fcd4
```

`verify`重新加载九模型，独立重算51条预测和所有指标；`replay`返回指定已准入样本的三个留出折模型结果。未知样本会被拒绝。输出保存到包外，保持包内摘要不变。完整固定训练复跑入口及原文资料绑定见[原交付说明](D:/桌面文件/sci/docs/handoff/MIC_TRAINING_DELIVERY_20261004.md)，本轮没有重新训练。

## 全部模型结果与解释范围

固定判定阈值0.5，17个分子中6阳性、11阴性；以下仅展示部分指标，完整结果及混淆计数一并交付。

| 模型 | AUROC | AUPRC | 平衡准确率 | MCC |
|---|---:|---:|---:|---:|
| Dummy | 0.4091 | 0.3154 | 0.5000 | 0.0000 |
| LR | 0.4545 | 0.3780 | 0.5303 | 0.0636 |
| RF | 0.5758 | 0.4316 | 0.6136 | 0.2273 |

小样本、历史性能已知后的探索、没有合格独立外部验证；这些结果不足以证明可靠泛化或临床用途。42条测定表述可能重复，每个分子只产生一个训练样本。全部模型报告，不作最佳模型选择。本轮未调参、校准或追加全数据拟合。

## 证据批次为什么结案

30条的现有原始依据仍有目标端点/种属不符、类别区间不确定、身份或图文/条件冲突、完整形式缺失等问题。最终决定是“本批不准入”，不生成阴性标签、不推断实验不存在。11条既有形式排除、37条此前用户关闭的原文缺口保留原记录。

合格外部记录为0，因此全员/来源隔离状态为`not_run_no_evidence_eligible_records`；没有执行，也没有宣称通过。当前批次检索和证据审查待办已关闭；提供新的可核查原始证据后，须另建审计版本并通过原协议全部门禁才能重新审查。不会自动继续这批检索或训练。

## 验证范围

本轮实际完成ZIP/摘要、包内运行、模型预测/全部指标、30条/41条/78条覆盖与历史保护检查。审计通过不代表整个项目测试套件通过。

此前相关历史回归为60 passed、1 failed，失败来自冻结旧发布器不兼容17分子/42表述；此前新增交付回归58 passed。本轮未重新运行pytest或修补历史冻结文件。既有科学数据、模型、失败运行、历史状态和五份MIC当前状态块均保留。
