# 现有 MIC 研究成果与证据链可复核索引 (Existing MIC Research Index)

本索引整理截至 2026-10-04 项目内已冻结、已训练、已独立复核的 MIC 单任务成果及关键机器文件路径。依据科研规范，所有历史基线与协议均作为不可变制品永久保留。

---

## 一、 当前基线机器状态 (Machine State Baseline)

- **当前最新状态文件**：[`03_experiments/audits/mic_training_readiness_20261004_v22.json`](file:///D:/桌面文件/sci/03_experiments/audits/mic_training_readiness_20261004_v22.json)
- **状态代码**：`local_exploratory_training_independently_verified`
- **训练阻断标志**：`training_blocked = false`（MIC 单任务小样本探索性训练已完成并通过独立复核）
- **正式双任务状态**：`formal_dual_task_status = blocked`
- **正式结果可用性**：`formal_results_available = false`
- **正式投稿就绪性**：`publication_ready = false`

---

## 二、 协议与冻结记录 (Protocols & Freezes)

| 协议编号 | 冻结记录文件 | 适用队列 | 状态与用途 |
|---|---|---|---|
| `protocol-mic-07` | [`03_experiments/audits/protocol_mic_07_freeze_20261002_v2.json`](file:///D:/桌面文件/sci/03_experiments/audits/protocol_mic_07_freeze_20261002_v2.json) | 15 分子、22 观察 | 历史首发基线（不可变归档） |
| `protocol-mic-09` | [`03_experiments/audits/protocol_mic_09_freeze_20261002_v1.json`](file:///D:/桌面文件/sci/03_experiments/audits/protocol_mic_09_freeze_20261002_v1.json) | 17 分子（含历史撤回条目） | 历史探索基线（探索归档） |
| `protocol-mic-10` | [`03_experiments/audits/protocol_mic_10_freeze_20261002_v1.json`](file:///D:/桌面文件/sci/03_experiments/audits/protocol_mic_10_freeze_20261002_v1.json) | 17 分子表征探索 | ESM-2 表征探索（探索归档） |
| **`protocol-mic-11`** | [`03_experiments/audits/protocol_mic_11_freeze_20261004_v1.json`](file:///D:/桌面文件/sci/03_experiments/audits/protocol_mic_11_freeze_20261004_v1.json) | **16 分子、23 观察** | **当前正式有效训练协议** |

---

## 三、 数据集释放与队列构成 (Current Release: mic_followup_release_20261004_v1)

- **数据集目录**：[`03_experiments/audits/mic_followup_release_20261004_v1/`](file:///D:/桌面文件/sci/03_experiments/audits/mic_followup_release_20261004_v1/)
- **分子清单**：[`cohort/candidate_molecules.csv`](file:///D:/桌面文件/sci/03_experiments/audits/mic_followup_release_20261004_v1/cohort/candidate_molecules.csv)（共 16 个分子，5 阳性、11 阴性）
- **观察清单**：[`cohort/candidate_observations.csv`](file:///D:/桌面文件/sci/03_experiments/audits/mic_followup_release_20261004_v1/cohort/candidate_observations.csv)（共 23 条实测观察）
- **分区划分**：[`cohort/fold_roles.csv`](file:///D:/桌面文件/sci/03_experiments/audits/mic_followup_release_20261004_v1/cohort/fold_roles.csv)（固定三折，seed=42，各训练折与验证折均含两类）
- **全员同源审计**：[`cohort/all_member_similarity.csv`](file:///D:/桌面文件/sci/03_experiments/audits/mic_followup_release_20261004_v1/cohort/all_member_similarity.csv)（120 对两两比对，跨折同源 ≥0.40 边数严格为 0）
- **分区审计结果**：[`partition_audit.json`](file:///D:/桌面文件/sci/03_experiments/audits/mic_followup_release_20261004_v1/partition_audit.json)（状态为 `passed`，7 个连通组件）
- **新分子依据**：BMAP-27B（`5445b7b645f69b6d7f8abdf3`），来自 DOI `10.1002/mlf2.70020` Figure 1 原图实测单株 `CREC6`（3.125 µg/ml，阳性），游离末端由 Wang resin 及 Fmoc 合成规程支持。

---

## 四、 实验运行与模型产物 (Experimental Runs & Models)

- **运行目录**：[`03_experiments/runs/mic_followup_baseline_20261004_v1/`](file:///D:/桌面文件/sci/03_experiments/runs/mic_followup_baseline_20261004_v1/)
- **模型文件**：
  - `models/logistic_regression_fold_0.joblib` ~ `fold_2.joblib` (3 个折模型)
  - `models/random_forest_fold_0.joblib` ~ `fold_2.joblib` (3 个折模型)
  - `models/dummy_prior_fold_0.joblib` ~ `fold_2.joblib` (3 个折模型)
  - 共 9 个模型，严格无外部泄漏。
- **样本外预测**：[`oof_predictions.csv`](file:///D:/桌面文件/sci/03_experiments/runs/mic_followup_baseline_20261004_v1/oof_predictions.csv)（48 条 OOF 记录）
- **指标摘要**：[`metrics.csv`](file:///D:/桌面文件/sci/03_experiments/runs/mic_followup_baseline_20261004_v1/metrics.csv)

---

## 五、 独立无 fit 交叉复核 (Independent Zero-Fit Verification)

- **复核脚本**：[`02_code/validate_mic_followup_run.py`](file:///D:/桌面文件/sci/02_code/validate_mic_followup_run.py)
- **复核输出**：[`03_experiments/audits/mic_followup_run_validation_20261004_v2.json`](file:///D:/桌面文件/sci/03_experiments/audits/mic_followup_run_validation_20261004_v2.json)
- **复核原则**：严格禁止在验证阶段调用任何 `fit()` 或 `fit_transform()`，完全重载磁盘保存的 9 个模型与训练折 Scaler，独立重算所有 OOF 预测与混淆矩阵。
- **复核核算混淆矩阵**：
  - **Logistic Regression (LR)**：TP=0, FP=3, TN=8, FN=5 (AUPRC=0.3163, AUROC=0.4545, MCC=-0.3239)
  - **Random Forest (RF)**：TP=1, FP=4, TN=7, FN=4 (AUPRC=0.3081, AUROC=0.4364, MCC=-0.1636)
  - **Dummy Classifier**：TP=0, FP=0, TN=11, FN=5 (AUPRC=0.3000, AUROC=0.4636, MCC=0.0000)
- **结论**：独立复核 100% 通过（`status: passed`），样本量极小，性能为历史已知基线描述，不具有临床泛化效用。
