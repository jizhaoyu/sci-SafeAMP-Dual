# MIC-only 三折探索训练产物复核

复核生成时间：2026-10-02T12:10:48.202662+00:00
机器状态生成时间：2026-10-02 18:51:38（Asia/Shanghai）
状态：`local_exploratory_three_fold_training_completed`；运行：`03_experiments/runs/mic_three_fold_20261002_v1`。
数据版本 `mic_three_fold_20261002_v1`；审计协议 `protocol-mic-06`，训练协议 `protocol-mic-07`。

## 已完成与复核范围

15 条分子（4 阳性、11 阴性），22 条原始 MIC，6 个不可拆分组件。
三个预先声明的基线完成固定三折训练；九个模型已重新加载，45 条 OOF 预测、12 行指标及 15×44 特征核对通过。
LR 标准化器和 prior 仅使用各自训练折。独立重算 105 对全员序列，跨折同源及原始研究均为 0。
当前状态文档已复核 5 份；复核期间禁止 fit 调用。

## 合并 OOF 描述性指标

AUPRC 按 average precision 定义；判定阈值预先固定为 0.5。
| 模型 | AUPRC | AUROC | MCC | 平衡准确率 | 准确率 | TP / FP / TN / FN |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| logistic_regression | 0.300595 | 0.454545 | -0.161165 | 0.454545 | 0.666667 | 0 / 1 / 10 / 4 |
| random_forest | 0.242262 | 0.318182 | -0.363636 | 0.318182 | 0.466667 | 0 / 4 / 7 / 4 |
| dummy_prior | 0.238889 | 0.420455 | 0.000000 | 0.500000 | 0.733333 | 0 / 0 / 11 / 4 |

## 逐折结果与解释边界

| 模型 | 折 | 阳性 / 阴性 | AUPRC | AUROC | 平衡准确率 | TP / FP / TN / FN |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| logistic_regression | 0 | 2 / 4 | 0.450000 | 0.500000 | 0.500000 | 0 / 0 / 4 / 2 |
| random_forest | 0 | 2 / 4 | 0.366667 | 0.375000 | 0.375000 | 0 / 1 / 3 / 2 |
| dummy_prior | 0 | 2 / 4 | 0.333333 | 0.500000 | 0.500000 | 0 / 0 / 4 / 2 |
| logistic_regression | 1 | 1 / 4 | 0.333333 | 0.500000 | 0.375000 | 0 / 1 / 3 / 1 |
| random_forest | 1 | 1 / 4 | 0.250000 | 0.250000 | 0.125000 | 0 / 3 / 1 / 1 |
| dummy_prior | 1 | 1 / 4 | 0.200000 | 0.500000 | 0.500000 | 0 / 0 / 4 / 1 |
| logistic_regression | 2 | 1 / 3 | 0.250000 | 0.000000 | 0.500000 | 0 / 0 / 3 / 1 |
| random_forest | 2 | 1 / 3 | 0.250000 | 0.000000 | 0.500000 | 0 / 0 / 3 / 1 |
| dummy_prior | 2 | 1 / 3 | 0.250000 | 0.500000 | 0.500000 | 0 / 0 / 3 / 1 |

各验证折仅 1–2 条阳性，不能据此确定模型优劣或推广至其他肽、菌株及条件。
prior 每折预测为训练集阳性比例，每折 AUROC 为 0.5；合并 OOF 含三个不同训练先验，所以汇总 AUROC 可不等于 0.5。
prior 在 0.5 阈值下全判阴性，准确率 11/15 反映类别比例，不能作为识别阳性的证据。
合并 OOF 是不同折模型的描述性汇总，不代表单个部署模型的独立外部验证。
未进行模型选择、调参、校准、全样本重训或部署。此次结果没有证明可靠的预测能力，不能用结果反向修改冻结协议。
原正式双任务保持 blocked；正式结果与投稿状态仍 false，正式状态文件摘要未变。
原文核查为代理复核，未声称独立人工审稿；原文未报告的测定条件仍明确缺失。

## 来源与复跑

本报告所有数值由同目录 JSON 的 inputs、fold_metrics 和 pooled_descriptive_metrics 绑定至真实运行文件。
复核命令只加载模型，不再次训练；输出路径必须不存在：

```powershell
python 02_code/validate_mic_three_fold_run.py --run 03_experiments/runs/mic_three_fold_20261002_v1 --output 03_experiments/audits/mic_run_validation_my_run.json --state 03_experiments/audits/mic_training_readiness_20261002_v12.json --check-documents
```

报告整理使用 scientific-writing 技能；技能方法来源为 Kassis T, Agarwal V, He Y, Patel D, Brueckner AM (2026).
[Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065)。
2026-10-02 核对 arXiv 元数据，当前版本 v2；该引用仅说明写作工具来源，不支持本研究的实验或模型结论。
