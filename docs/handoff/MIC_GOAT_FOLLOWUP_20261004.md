# 山羊肽证据释放与固定基线交付

## 当前结论

状态来源：`03_experiments/audits/mic_training_readiness_20261004_v26.json`，生成时间为 `2026-10-04T07:17:45.230443+00:00`。训练协议 `protocol-mic-13`，数据版本 `mic_goat_followup_release_20261004_v1`。

MIC 探索性扩充已完成训练及独立复核，`training_blocked=false`。原双任务继续 `blocked`；正式结果与投稿就绪均为 `false`。

## 原始证据与取舍

原始测量研究：[Combined Antibacterial Effects of Goat Cathelicidins With Different Mechanisms of Action](https://www.frontiersin.org/journals/microbiology/articles/10.3389/fmicb.2018.02983/full)，DOI `10.3389/fmicb.2018.02983`，PMID `30555455`，PMCID `PMC6284057`，原文标注 CC BY 4.0。

官方补充 DOCX 已获取，序列表 S1 与测定表 S2 已结构化提取并渲染核对。身份依据来自受测重组成熟肽、原文分子形式、明确序列及质谱一致性；不以数据库类别或预测判定。末端形式的判断是根据上述联合证据作出的推断，未声称独立人工评审。

| 候选 | 原始单药 MIC 表格提及数 | 可推导标签集合 | 决定 |
|---|---:|---|---|
| ChMAP-28 | 19 | 正类 | 证据通过，新增一个分子 |
| mini-ChBac7.5Nα | 18 | 正类和负类 | 标签冲突，阻止释放 |
| mini-ChBac7.5Nα(1-16) | 8 | 正类和负类 | 标签冲突，阻止释放 |

45 条提及覆盖正文 Tables 2–5 与补充 Table S2 的单药 E. coli MIC。Table 3 只读取单药 MIC 列，组合浓度不生成标签。不同菌株、盐条件和选择历史分别保留；未报告的表格条件记为缺失，不自行推断。未删去高 MIC 条件来取得一致标签。

补充表 S1 的质量为单同位素 `[M+H]+`，没有把它直接作为中性平均分子量；浓度换算和标签沿用既有序列质量工具与阈值。

42 条准入表格表述由原 23 条及新增 19 条组成，可能包含重复提及，不代表 42 次独立实验或 42 个训练样本。训练始终每个分子一行。

## 分区和训练

- [x] 17 个分子，6 正类、11 负类；全部 136 对成员比较。
- [x] 同源与原始测量研究关系联合分组；7 个组件，其中 4 个含正类、6 个含负类。
- [x] 固定三折、shuffle=True、seed=42，唯一一次划分；全部训练/验证包含两类。
- [x] 跨折同源边 0、跨折测量研究重叠 0。
- [x] 冻结 44 维特征、标签规则、分组、折角色、环境及入口摘要。
- [x] 固定 LR/RF/Dummy 共 9 个折模型、51 条 OOF；无调参、校准、特征筛选或最佳模型选择。
- [x] 独立复核重载全部模型，禁止 fit，复算预测及指标，检查缩放器训练范围。
- [x] 五份文档当前状态块与 v26 完全一致，旧文档已备份。

描述性汇总（判定阈值 0.5）：

| 模型 | AUROC | AUPRC | 平衡准确率 | MCC |
|---|---:|---:|---:|---:|
| Dummy | 0.4091 | 0.3154 | 0.5000 | 0.0000 |
| LR | 0.4545 | 0.3780 | 0.5303 | 0.0636 |
| RF | 0.5758 | 0.4316 | 0.6136 | 0.2273 |

样本量很小，历史模型性能已经看过，这属于后续探索；不据此宣称广泛泛化、临床用途或外部验证成功，也不作最佳模型选择。

## 中断与修复记录

首次 `protocol-mic-12` 运行在首个 LR 折模型保存后，因训练循环的 `compute_metrics` 未绑定而中断。失败产物及 v24 失败状态已归档，没有覆盖或当作完整结果。

修复使用新入口 `02_code/train_mic_goat_baseline_v2.py` 和新冻结 `protocol-mic-13`，显式绑定指标函数，科学定义、折划分、特征与模型参数均未改变。完整运行位于 `03_experiments/runs/mic_goat_baseline_20261004_v2`。

## 验证与限制

新增 8 项回归通过。相关现行检查合计 **60 passed，1 deselected**。首次运行旧检查集合为 **52 passed，1 failed**：失败的 `test_all_current_documents_agree` 使用冻结的旧发布器，固定要求 16 分子、23 条观察。该旧检查保留；新增状态一致性检查实际核对 v26 的五份文档。没有声称完整历史测试套件通过。

旧 16 分子基线通过既有兼容验证入口 `02_code/validate_mic_followup_run.py` 再次复核：9 模型、48 OOF、零 fit。直接调用冻结训练脚本中的旧验证函数会遇到 TP/FP/TN/FN 列不在历史指标表中的已知格式兼容问题；兼容入口核对所有历史声明指标，并单独重算混淆计数，未更改历史文件。

## 复跑入口

```powershell
python 02_code/train_mic_goat_baseline_v2.py validate --run 03_experiments/runs/mic_goat_baseline_20261004_v2 --output 03_experiments/audits/mic_goat_run_validation_20261004_v2.json --protocol 03_experiments/protocols/protocol-mic-13.json --freeze 03_experiments/audits/protocol_mic_13_freeze_20261004_v1.json
python 02_code/publish_mic_goat_status.py validate --state 03_experiments/audits/mic_training_readiness_20261004_v26.json
```

复核输出必须使用尚不存在的路径。不要重写已有冻结协议、训练目录或审计目录。
