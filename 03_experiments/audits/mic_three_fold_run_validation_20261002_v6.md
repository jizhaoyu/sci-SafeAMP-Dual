# 扩充队列（17 分子）MIC 三折探索训练产物复核

复核生成时间：2026-10-02T13:21:59.749476+00:00
机器状态生成时间：2026-10-02 21:17:33（Asia/Shanghai）
状态：`local_exploratory_three_fold_training_completed`；运行：`03_experiments/runs/mic_three_fold_20261002_v2`。
数据版本 `mic_source_expansion_result_20261002_v2`；审计协议 `protocol-mic-08`，训练协议 `protocol-mic-09`。

## 已完成与复核范围

17 条分子（6 阳性、11 阴性），24 条原始 MIC，8 个不可拆分组件（含阳性 5 个）。
三个预先声明的基线完成固定三折训练；九个模型已重新加载，51 条 OOF 预测、12 行指标及 17×44 特征核对通过。
LR 标准化器和 prior 仅使用各自训练折。独立重算 136 对全员序列，跨折同源及原始研究均为 0。
当前状态文档已复核 5 份；复核期间禁止 fit 调用。

## 合并 OOF 描述性指标

AUPRC 按 average precision 定义；判定阈值预先固定为 0.5。
| 模型 | AUPRC | AUROC | MCC | 平衡准确率 | 准确率 | TP / FP / TN / FN |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| logistic_regression | 0.408796 | 0.560606 | -0.184637 | 0.454545 | 0.588235 | 0 / 1 / 10 / 6 |
| random_forest | 0.467554 | 0.545455 | 0.203091 | 0.606061 | 0.588235 | 4 / 5 / 6 / 2 |
| dummy_prior | 0.339869 | 0.469697 | 0.000000 | 0.500000 | 0.647059 | 0 / 0 / 11 / 6 |

## 逐折结果与解释边界

| 模型 | 折 | 阳性 / 阴性 | AUPRC | AUROC | 平衡准确率 | TP / FP / TN / FN |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| logistic_regression | 0 | 2 / 4 | 0.325000 | 0.250000 | 0.500000 | 0 / 0 / 4 / 2 |
| random_forest | 0 | 2 / 4 | 0.500000 | 0.625000 | 0.625000 | 2 / 3 / 1 / 0 |
| dummy_prior | 0 | 2 / 4 | 0.333333 | 0.500000 | 0.500000 | 0 / 0 / 4 / 2 |
| logistic_regression | 1 | 2 / 3 | 0.833333 | 0.833333 | 0.500000 | 0 / 0 / 3 / 2 |
| random_forest | 1 | 2 / 3 | 0.750000 | 0.666667 | 0.666667 | 2 / 2 / 1 / 0 |
| dummy_prior | 1 | 2 / 3 | 0.400000 | 0.500000 | 0.500000 | 0 / 0 / 3 / 2 |
| logistic_regression | 2 | 2 / 4 | 0.416667 | 0.500000 | 0.375000 | 0 / 1 / 3 / 2 |
| random_forest | 2 | 2 / 4 | 0.291667 | 0.125000 | 0.500000 | 0 / 0 / 4 / 2 |
| dummy_prior | 2 | 2 / 4 | 0.333333 | 0.500000 | 0.500000 | 0 / 0 / 4 / 2 |

各验证折严格平衡包含 2 条阳性，总验证规模分别为 6、5、6 条。
RF 在 0.5 阈值下识别出 3 条阳性（包括新增候选 Piscidin 1 游离酸），MCC 为 0.203091，平衡准确率 0.606061；样本量极小，不作为广泛泛化或临床效用证据。
prior 每折预测为训练集阳性比例，合并 OOF 汇总 AUROC 为 0.469697；prior 在 0.5 阈值下全判阴性，准确率 11/17 反映类别比例，不能作为识别阳性的证据。
合并 OOF 是不同折模型的描述性汇总，不代表单个部署模型的独立外部验证。
未进行模型选择、调参、校准、全样本重训或部署。此次结果没有证明可靠的预测能力，不能用结果反向修改冻结协议。
原正式双任务保持 blocked；正式结果与投稿状态仍 false，正式状态文件摘要未变。
原文核查为代理复核，未声称独立人工审稿；原文未报告的测定条件仍明确缺失。

## 来源与复跑

本报告所有数值由同目录 JSON 的 inputs、fold_metrics 和 pooled_descriptive_metrics 绑定至真实运行文件。
复核命令只加载模型，不再次训练；输出路径必须不存在：

```powershell
python 02_code/validate_mic_three_fold_run_v2.py --run 03_experiments/runs/mic_three_fold_20261002_v2 --output 03_experiments/audits/mic_run_validation_my_run.json --state 03_experiments/audits/mic_training_readiness_20261002_v14.json --check-documents
```
