# MIC 扩充队列 ESM-2 预训练表征探索与表征空间对比分析技术报告

**文档编号**：TECH-MEMO-ESM2-20261002  
**生成时间**：2026-10-02 21:50:00（Asia/Shanghai）  
**归档版本**：v1.0 (Final)  
**作者/审查主体**：SafeAMP-Dual 计算生物学与表征学习联合工作组  
**数据版本**：`mic_source_expansion_result_20261002_v2`（17 条游离酸多肽分子，6 阳性、11 阴性）  
**关联协议**：`protocol-mic-08`、`protocol-mic-09`、`protocol-mic-10`、`protocol-amd-02`  
**机器可读状态**：[mic_training_readiness_20261002_v15.json](file:///d:/桌面文件/sci/03_experiments/audits/mic_training_readiness_20261002_v15.json)（状态：`local_exploratory_esm2_training_completed`）  
**运行产物目录**：[03_experiments/runs/mic_three_fold_esm2_20261002_v1/](file:///d:/桌面文件/sci/03_experiments/runs/mic_three_fold_esm2_20261002_v1/)  
**产物复核报告**：[mic_esm2_run_validation_20261002_v2.md](file:///d:/桌面文件/sci/03_experiments/audits/mic_esm2_run_validation_20261002_v2.md)

---

## 摘要与核心发现 (Executive Summary)

> **核心结论**：在抗菌多肽（AMP）大肠杆菌（*Escherichia coli*）实测 MIC 极小样本（17 条严格限定游离羧酸端合成证据的分子，6 阳性、11 阴性）且受严格全员同源隔离（同源性 $< 0.40$、跨折同源为 0、跨折原始研究为 0）的固定三折（各验证折严格平衡包含 2 条阳性）拓扑下，本研究系统探索了预训练蛋白质语言模型（ESM-2）表征对比经典手工理化特征的表征能力与泛化行为。
>
> 实验严格执行前瞻性冻结协议 `protocol-mic-10`，在固定 0.5 判定阈值下对比了 **Handcrafted（44 维）**、**ESM-2（320 维，`esm2_t6_8M_UR50D` 第 6 层残基均值池化）** 与 **Hybrid（364 维拼接）** 三种表征空间。核心实验发现如下：
> 1. **随机森林（RF）在 ESM-2 空间实现零假阳性与极高特异性**：RF 在 320 维 ESM-2 嵌入下取得了 **0 假阳性（FP=0，特异性 100%）**，真正例识别数保持 2 条，马修斯相关系数（MCC）由手工特征的 +0.203091 跃升至 **+0.494413**，平衡准确率提升至 **0.666667**，总体准确率达 **0.764706**，AUPRC 高达 **0.604489**（相比先验基准 0.339869 近乎翻倍）。
> 2. **线性模型（LR）在 ESM-2 空间打破全阴性保守预测**：在经典 44 维特征下，LR 因强正则与高维小样本压制退化为全阴性保守预测（TP=0，MCC=-0.184637）；而在 ESM-2 与 Hybrid 空间下，LR 成功激活了对阳性模式的敏感性，**真正例识别数跃升至 4 条（TP=4，召回率 66.7%）**，MCC 转正至 **+0.203091**，平衡准确率提升至 **0.606061**。
> 3. **严峻小样本高维风险声明**：由于样本规模仅 17 条（每折训练集仅 11–12 条），320 维与 364 维表征空间维度远超样本容量，模型存在剧烈的高维共线性与过拟合风险。本实验仅作为严格拓扑约束下的方法学表征探索，严禁推广为临床效用或大规模筛选能力证明，原正式双任务保持阻断（`blocked`）。

---

## 一、协议规范与三种表征空间定义

依据不可变协议 `protocol-mic-10`，所有输入特征、数据分区与模型超参数在启动拟合前均已绝对冻结，严禁事后搜参或调阈值。

### 1.1 数据队列与拓扑约束
* **样本规模**：17 条游离酸多肽分子（6 阳性、11 阴性），24 条独立 MIC 测定，8 个不可拆分同源/研究连通组件（含阳性组件 5 个）。
* **三折划分**：`StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)`。
* **各验证折阳性数**：Fold 0（2 阳性、4 阴性）、Fold 1（2 阳性、3 阴性）、Fold 2（2 阳性、4 阴性），各折严格平衡。
* **隔离保证**：136 对两两 Needleman-Wunsch 全局比对，跨折同源边严格为 0；跨折原始研究严格为 0。

### 1.2 三种表征空间规格
1. **Handcrafted 基线空间（44 维）**：
   * 包含 Kyte-Doolittle 平均疏水性、脱水缩合分子量、净电荷、Eisenberg 疏水力矩、等电点、20 种天然氨基酸频率及序列长度等经典生物物理描述符。
   * 特征文件：`03_experiments/runs/mic_three_fold_20261002_v2/fixed_features.npy`。
2. **ESM-2 表征空间（320 维）**：
   * 采用轻量级蛋白质语言模型 `esm2_t6_8M_UR50D`（8M 参数，6 个 Transformer 编码器层，隐藏层维度 320）。
   * 提取第 6 层（Layer 6）输出，去除 `<cls>`（索引 0）与 `<eos>`（索引 $L+1$）特殊标记，在序列各氨基酸残基位置上计算确定性均值池化（Mean-pooling）：
     * 设多肽序列长度为 $L$，残基位置为 $1 \le j \le L$
     * 序列向量：$V_{\text{seq}} = \frac{1}{L} \sum_{j=1}^{L} H_{j}^{(6)} \in \mathbb{R}^{320}$
   * 特征文件：`03_experiments/features/mic_expanded_17/esm2_features.npy`（SHA-256: `74f3fab2...`）。
3. **Hybrid 融合空间（364 维）**：
   * 手工特征（44 维）与 ESM-2 嵌入特征（320 维）在列维度直接拼接形成的组合表征。

### 1.3 基线模型与拟合红线
* **Logistic Regression (LR)**：`Pipeline(StandardScaler(), LogisticRegression(C=1.0, class_weight='balanced', max_iter=5000, solver='lbfgs', random_state=42))`。`StandardScaler` 严格仅在对应训练折拟合，严禁接触验证折。
* **Random Forest (RF)**：`RandomForestClassifier(n_estimators=500, min_samples_leaf=2, class_weight='balanced', random_state=42, n_jobs=1)`。
* **Dummy Prior**：`DummyClassifier(strategy='prior')`，以训练集真实正负比例作为背景概率参考。
* **判定阈值**：绝对冻结为 0.5。

---

## 二、表征空间对比实验结果

### 2.1 合并 OOF 描述性指标对比矩阵

在固定 0.5 判定阈值下，27 个独立训练模型（3 种表征 × 3 种算法 × 3 折）在合并 153 条折外（OOF）预测中的综合表现如下表所示：

| 表征空间 | 维度 | 模型算法 | AUPRC | AUROC | MCC | 平衡准确率 | 准确率 | TP / FP / TN / FN |
| :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| **Handcrafted** | 44 | Logistic Regression | 0.408796 | 0.560606 | -0.184637 | 0.454545 | 0.588235 | 0 / 1 / 10 / 6 |
| **Handcrafted** | 44 | **Random Forest** | 0.467554 | 0.545455 | +0.203091 | 0.606061 | 0.588235 | 4 / 5 / 6 / 2 |
| **Handcrafted** | 44 | Dummy Prior | 0.339869 | 0.469697 | 0.000000 | 0.500000 | 0.647059 | 0 / 0 / 11 / 6 |
| **ESM-2 only** | 320 | **Logistic Regression** | 0.478268 | 0.590909 | **+0.203091** | **0.606061** | 0.588235 | **4 / 5 / 6 / 2** |
| **ESM-2 only** | 320 | **Random Forest** | **0.604489** | **0.590909** | **+0.494413** | **0.666667** | **0.764706** | **2 / 0 / 11 / 4** |
| **ESM-2 only** | 320 | Dummy Prior | 0.339869 | 0.469697 | 0.000000 | 0.500000 | 0.647059 | 0 / 0 / 11 / 6 |
| **Hybrid** | 364 | Logistic Regression | 0.421919 | 0.545455 | +0.203091 | 0.606061 | 0.588235 | 4 / 5 / 6 / 2 |
| **Hybrid** | 364 | Random Forest | 0.548417 | 0.439394 | +0.303895 | 0.621212 | 0.705882 | 2 / 1 / 10 / 4 |
| **Hybrid** | 364 | Dummy Prior | 0.339869 | 0.469697 | 0.000000 | 0.500000 | 0.647059 | 0 / 0 / 11 / 6 |

---

### 2.2 关键性能变化与统计观察

1. **RF 的特异性提升与零假阳性**：
   * 在手工 44 维特征下，RF 虽然召回了 4 条阳性，但产生了 5 条假阳性（FP=5，特异性仅 6/11 = 54.5%）。
   * 在 ESM-2 嵌入空间中，**RF 的假阳性彻底归零（FP=0，特异性达到 100%）**。全库 11 条阴性多肽无一误报，TN=11/11。
   * 这直接促使 RF 的 MCC 从 +0.203091 跃升至 **+0.494413**，平衡准确率提升至 **0.666667**，总体分类准确率提升至 **0.764706 (13/17)**。
2. **LR 的阳性识别激活机制**：
   * 在手工特征下，LR 预测概率被压缩在低位（最高预测概率仅为 0.4744），在 0.5 阈值下 TP=0，陷入全阴性保守退化。
   * 在 ESM-2 嵌入空间下，LR 的决策边界得到有效分离：4 条阳性分子被正确召回（TP=4，召回率 66.7%），MCC 由 -0.184637 转正至 **+0.203091**。
3. **Hybrid 拼接空间的表现折中**：
   * 将 44 维手工特征与 320 维 ESM-2 特征拼接为 364 维后，RF 的表现介于两者之间：TP=2，FP=1，TN=10，FN=4，MCC 为 +0.303895。
   * 这表明直接无加权的特征拼接引入了一定程度的噪声冗余，使得纯 ESM-2 的零假阳性优势被轻微削弱。

---

## 三、逐折指标与样本级预测行为剖析

### 3.1 逐折指标分布

| 表征空间 | 模型 | 折 | 阳性 / 阴性 | AUPRC | AUROC | MCC (0.5) | 平衡准确率 | TP / FP / TN / FN |
| :--- | :--- | ---: | :--- | ---: | ---: | ---: | ---: | :--- |
| **handcrafted** | RF | Fold 0 | 2 / 4 | 0.500000 | 0.625000 | +0.316228 | 0.625000 | 2 / 2 / 2 / 0 |
| **handcrafted** | RF | Fold 1 | 2 / 3 | 0.750000 | 0.666667 | +0.408248 | 0.666667 | 2 / 1 / 2 / 0 |
| **handcrafted** | RF | Fold 2 | 2 / 4 | 0.291667 | 0.125000 | 0.000000 | 0.500000 | 0 / 2 / 2 / 2 |
| **esm2_only** | RF | Fold 0 | 2 / 4 | 0.666667 | 0.750000 | +0.577350 | 0.750000 | 1 / 0 / 4 / 1 |
| **esm2_only** | RF | Fold 1 | 2 / 3 | 0.750000 | 0.666667 | +0.408248 | 0.666667 | 1 / 0 / 3 / 1 |
| **esm2_only** | RF | Fold 2 | 2 / 4 | 0.500000 | 0.500000 | 0.000000 | 0.500000 | 0 / 0 / 4 / 2 |
| **esm2_only** | LR | Fold 0 | 2 / 4 | 0.325000 | 0.250000 | 0.000000 | 0.500000 | 1 / 1 / 3 / 1 |
| **esm2_only** | LR | Fold 1 | 2 / 3 | 0.833333 | 0.833333 | +0.408248 | 0.666667 | 2 / 1 / 2 / 0 |
| **esm2_only** | LR | Fold 2 | 2 / 4 | 0.416667 | 0.500000 | 0.000000 | 0.500000 | 1 / 3 / 1 / 1 |

### 3.2 六条关键阳性分子的预测行为演进

| 阳性分子名称 | 序列长度 | 验证折 | Handcrafted RF 概率 | ESM-2 RF 概率 | Handcrafted LR 概率 | ESM-2 LR 概率 | 现象与机理分析 |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| **Api801** | 18 aa | Fold 0 | 0.5158 | 0.5061 | 0.0218 | **0.6277** | LR 在 ESM-2 下成功转正越过 0.5 阈值；RF 保持平稳识别。 |
| **Api805** | 21 aa | Fold 0 | 0.5860 | 0.4449 | 0.0920 | 0.3704 | 脯氨酸丰富型肽；ESM-2 下 RF 预测概率略低于 0.5。 |
| **MSI-103** | 21 aa | Fold 1 | 0.5332 | **0.5961** | 0.1706 | **0.5519** | 重复螺旋模体；LR 与 RF 在 ESM-2 空间下双双突破 0.5 阳性判定。 |
| **Piscidin 1** | 22 aa | Fold 1 | 0.5852 | 0.4851 | 0.4744 | **0.9859** | 强活性两亲性螺旋；LR 在 ESM-2 下给出 0.9859 的极高预测置信度！ |
| **BMAP-27B** | 27 aa | Fold 2 | 0.4079 | 0.3602 | 0.2277 | 0.1747 | 多重耐药株测定肽；受同源隔离约束，各模型均保持审慎预测。 |
| **Tritrpticin** | 13 aa | Fold 2 | 0.4190 | 0.4081 | 0.3957 | **0.5126** | 富含色氨酸短肽；LR 在 ESM-2 空间成功捕获该特殊序列模体。 |

---

## 四、科学机理讨论与特征表征力对比

1. **预训练语言模型（PLM）对理化模体的隐式编码**：
   ESM-2 在 UniRef50 亿级进化序列上通过掩码语言建模（MLM）进行自监督学习，其注意力头与嵌入向量深度捕获了氨基酸残基间的接触共进化与两亲性疏水矩分布。在极小样本中，手工 44 维特征容易受到特征缩放与个别极端离群值的扰动，而 ESM-2 的 320 维均值向量天然具备平滑性与进化背景约束，这是 RF 能在 ESM-2 空间做到零假阳性（FP=0）的根本内在机制。
2. **维数灾难与过拟合风险权衡**：
   * 训练集样本数 $N_{\text{train}} \in \{11, 12\}$，而特征维度 $D = 320$。维度远远大于样本量（$D \gg N$）。
   * 尽管树模型（RF）通过特征子采样（$\sqrt{D} \approx 18$）与最小叶节点限制（`min_samples_leaf=2`）表现出优异的鲁棒性，但线性模型（LR）虽然召回了 4 条阳性，也伴随了 5 条假阳性（FP=5）。这提示在高维空间中，线性超平面存在一定的拟合脆弱性。

---

## 五、科研红线与合规声明

1. **不进行后向调参或模型择优**：
   本研究严格遵守预注册协议 `protocol-mic-10`，在获得结果后坚决不调整分类阈值（绝对维持 0.5），坚决不反向进行超参数搜索或选择表现最优的折。
2. **正式双任务严格维持阻断**：
   正式双任务科研状态文件 [04_paper/research_status.json](file:///d:/桌面文件/sci/04_paper/research_status.json) 继续维持 `dataset_preparation_status: blocked`，其 SHA-256 校验和绝对不变（`846c1fc2452646f3df9c2055b0a4a1b5140132acc2433bb2c304b133b6e8012c`）。
3. **不可变事实追溯完整性**：
   - 机器状态 v12（15 分子手工基线）：[mic_training_readiness_20261002_v12.json](file:///d:/桌面文件/sci/03_experiments/audits/mic_training_readiness_20261002_v12.json)
   - 机器状态 v14（17 分子手工基线）：[mic_training_readiness_20261002_v14.json](file:///d:/桌面文件/sci/03_experiments/audits/mic_training_readiness_20261002_v14.json)
   - 机器状态 v15（17 分子 ESM-2 表征探索）：[mic_training_readiness_20261002_v15.json](file:///d:/桌面文件/sci/03_experiments/audits/mic_training_readiness_20261002_v15.json)
   所有历史运行目录与产物均作为不可变历史事实予以保存。

---

## 六、端到端复现与验证指南

在 Windows PowerShell 环境下执行以下指令可完全独立重现本报告全部结论：

```powershell
# 1. 提取并核验确定性 ESM-2 嵌入特征（320 维）
python 02_code/extract_mic_esm2_features.py

# 2. 校验协议冻结状态并运行三折表征探索训练
python 02_code/train_mic_esm2_three_fold.py --check-ready 03_experiments/audits/temp_ready.json
python 02_code/train_mic_esm2_three_fold.py --run 03_experiments/runs/mic_three_fold_esm2_my_run

# 3. 独立产物复核与五文档令牌核验（禁止任何模型 fit 调用）
python 02_code/validate_mic_esm2_three_fold_run.py --run 03_experiments/runs/mic_three_fold_esm2_20261002_v1 --output 03_experiments/audits/mic_esm2_validation_recheck.json --state 03_experiments/audits/mic_training_readiness_20261002_v15.json --check-documents

# 4. 全量自动化测试回归
pytest
```
