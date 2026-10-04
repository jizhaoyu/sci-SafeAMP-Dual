# MIC 扩充队列三折基线训练协议 (protocol-mic-09)

## 授权与背景

2026-10-02，用户在完成文献扩充审计后明确选择“决策点 A（启动扩充队列的固定三折训练探索）”。先前依据 `protocol-mic-08` 完成的来源扩充审计（`mic_source_expansion_result_20261002_v2`）审查了 12 篇公开文献，纳入了 2 条具有明确固相合成化学证据与体外实测 MIC 的阳性多肽（Chekmenev 2006 的 Piscidin 1 游离酸 与 bmap2025 的 BMAP-27B 游离酸），与既有 15 条分子合并形成 17 条候选分子（6 阳性、11 阴性）、24 条实测 MIC。

全员比对及同源/研究闭包形成 8 个不可拆分组件（含阳性组件增至 5 个）。在固定 `StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)` 下，各验证折的阳性分子数实现了绝对平衡（各验证折严格为 2 条阳性，总验证规模分别为 6、5、6 条），跨折同源边与跨折原始研究严格为 0。

新增 [`protocol-mic-09`](../../03_experiments/protocols/protocol-mic-09.json)，在启动模型训练前予以不可变冻结，授权释放该 17 条分子用于本地小样本三折探索基线训练。

## 冻结训练设计与模型参数

1. **样本队列与分区角色**：
   - 样本集：严格限定为 `mic_source_expansion_result_20261002_v2/candidate_molecules.csv` 中的 17 条分子及对应 24 条测定；
   - 分区：严格沿用已固化的整组件三折分配（`fold_roles.csv`），不进行任何新切分或随机种子搜索。
2. **特征体系**：
   - 提取固定 44 维手工序列特征（理化性质、残基分布与全局特征）；
   - 严禁任何特征选择或依据测试表现的数据修剪。
3. **基线模型与拟合约束**：
   - **Logistic Regression (LR)**：`C=1.0, class_weight='balanced', max_iter=5000, solver='lbfgs', random_state=42`；`StandardScaler` 标准化器仅在对应训练折拟合，严禁接触验证集；
   - **Random Forest (RF)**：`n_estimators=500, min_samples_leaf=2, class_weight='balanced', random_state=42, n_jobs=1`；
   - **Dummy Prior**：`strategy='prior'`，仅使用训练折类别比例作为对照基线；
   - 训练期间与复核期间绝不进行超参数网格搜索、概率后校准或模型择优。
4. **评价终点与指标**：
   - 固定判定阈值为 0.5；
   - 记录每折及合并折外（OOF）指标：AUPRC（Average Precision）、AUROC、MCC、平衡准确率、准确率以及 TP/FP/TN/FN 混淆矩阵。

## 适用范围与局限披露

- 本协议严格局限于 17 条分子的本地小样本探索，不作为任何部署模型或算法优劣评判依据。
- 各验证折仅包含 2 条阳性样本，样本量极小，不能据此得出具有统计显著性的推广结论。
- Piscidin 1 存在 UTSW 固相树脂未直接详述及 Todd Hewitt 培养基非标准局限；BMAP-27B 包含多重耐药临床株及文献区间局限；所有缺失实验条件如实记录保留。
- 原双任务正式研究在 `04_paper/research_status.json` 中保持 `blocked` 阻断，不提供正式结果或投稿授权。
- 历史不可变的 15 分子训练运行（`mic_three_fold_20261002_v1`）及机器状态 v12 作为不可变基线保留。
