# MIC 扩充队列 ESM-2 预训练表征探索协议 (protocol-mic-10)

## 授权与背景

2026-10-02，用户在完成 17 分子手工特征三折基线训练与学术技术纪要整理后，明确授权选择“选项 2（启动 ESM-2 预训练表征探索）”。先前依据 `protocol-mic-09` 完成的 17 分子固定三折基线训练（`mic_three_fold_20261002_v2`）证实：在 44 维经典手工理化特征下，Random Forest 模型在各折严格平衡（各折 2 阳性）的验证集中打破了全阴性退化预测，真正例识别数达到 4 条（MCC=+0.203091）。

为深入探究在大规模进化多序列上预训练的蛋白质语言模型（Protein Language Model, PLM）表征在极端小样本生物序列同源隔离约束下的泛化性质与边界，新增不可变协议 [`protocol-mic-10`](../../03_experiments/protocols/protocol-mic-10.json)。在启动任何模型拟合前，前瞻性冻结 ESM-2 表征提取、三种表征空间对比、预设分类器超参数及评价约束。

## 冻结实验设计与表征空间

1. **样本队列与分区拓扑**：
   - 样本集：严格限定为 `mic_source_expansion_result_20261002_v2/candidate_molecules.csv` 中的 17 条分子及对应 24 条实测 MIC；
   - 分区：严格沿用已固化的整组件三折分配（`fold_roles.csv`），不进行任何新切分、重新洗牌或随机种子搜索（各验证折严格为 2 条阳性，跨折同源边为 0，跨折原始研究为 0）。

2. **对比的三种表征空间**：
   - **Handcrafted 基线空间（44 维）**：经典手工理化性质、氨基酸组成与全局特征（已由 `fixed_features.npy` 固化）；
   - **ESM-2 表征空间（320 维）**：采用轻量级 `esm2_t6_8M_UR50D` 模型，提取第 6 层（Layer 6）表征，去除 `<cls>` 与 `<eos>` 特殊标记后在序列残基维度进行确定性均值池化（Mean-pooling）；
   - **Hybrid 融合空间（364 维）**：将 44 维手工特征与 320 维 ESM-2 嵌入特征在列维度直接拼接。

3. **基线模型与拟合约束**：
   - 在上述三种表征空间下，分别平行拟合三个预设基线模型：
     - **Logistic Regression (LR)**：`C=1.0, class_weight='balanced', max_iter=5000, solver='lbfgs', random_state=42`；`StandardScaler` 标准化器仅在对应训练折拟合，严禁接触验证集；
     - **Random Forest (RF)**：`n_estimators=500, min_samples_leaf=2, class_weight='balanced', random_state=42, n_jobs=1`；
     - **Dummy Prior**：`strategy='prior'`，仅使用对应训练折的类别比例作为无信息先验对照；
   - 训练与复核期间绝不进行超参数搜索、层选择、特征筛选、后校准或模型择优。

4. **评价终点与指标**：
   - 判定阈值严格冻结为 0.5；
   - 记录每折及合并折外（OOF）指标：AUPRC（Average Precision）、AUROC、MCC、平衡准确率、准确率以及 TP/FP/TN/FN 混淆矩阵。

## 适用范围与严峻局限性披露

- **高维过拟合风险**：样本量极小（仅 17 条分子，训练折仅 11–12 条），ESM-2 的 320 维与 Hybrid 的 364 维特征维度远超样本数量，存在极端的高维共线性与过拟合风险。
- **无泛化性宣称**：本探索严格局限于 17 条分子的方法学性质探究，不作为任何用于实际筛选或临床效用预测的依据。
- **实验条件异质性**：Piscidin 1 存在 UTSW 树脂未直接详述及 Todd Hewitt 培养基非标准局限；BMAP-27B 包含多重耐药临床株及区间局限；所有缺失实验条件如实记录保留。
- **双任务正式阻断**：原双任务正式研究在 `04_paper/research_status.json` 中保持 `blocked` 阻断，不提供正式结果或投稿授权。
- **历史不可变事实保留**：历史 15 分子训练运行（`mic_three_fold_20261002_v1`，机器状态 v12）与 17 分子手工基线训练运行（`mic_three_fold_20261002_v2`，机器状态 v14）作为不可变历史事实完整保留。
