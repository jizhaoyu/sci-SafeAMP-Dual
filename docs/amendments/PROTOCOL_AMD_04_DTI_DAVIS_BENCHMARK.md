# Protocol Amendment 04：DAVIS 激酶亲和力（Kd）基准测试规范与双盲冷启动隔离协议

**协议 ID**：`protocol-dti-01`  
**提案日期**：2026-10-06  
**生效状态**：**FROZEN（已冻结，正式生效）**  
**研究方向**：药物—靶标相互作用（Drug-Target Interaction, DTI）实测 $K_d$ 亲和力连续回归  
**基准数据集**：DAVIS 激酶组高通量亲和力矩阵（Davis et al., *Nat. Biotechnol.* 2011）  
**前置审计凭据**：
* 来源获取审计：`03_experiments/audits/dti_davis_acquisition_20261006_v2/`（官方 MD5: `6c7949b81aea69e9d816db88602d771e`）
* 字段与截断审计：`03_experiments/audits/dti_davis_field_review_20261006_v1/`
* 图拓扑与隔离审计：`03_experiments/audits/dti_davis_isolation_review_20261006_v1/`

---

## 一、协议背景与科学定位

在第一阶段（Task 1 / Task 2）中，对 BindingDB 202610 数据库及 19 篇公开文献的系统审计表明，公共数据库聚合的 $K_d$ 记录存在高达 19.65% 的多肽配体污染、荧光探针（JQ1-TAMRA）误归因、ORF1a 多聚蛋白重复挂载（100% 靶标泄漏）等结构性缺陷。

为此，依据用户正式指令，本协议确立以**公开金标准 DAVIS 激酶基准数据集**作为 DTI 亲和力预测的核心基准。DAVIS 数据集提供了化学空间清晰、实验测定高度标准化的全矩阵实测数据，彻底消除多肽污染与多源测定系统误差。

---

## 二、数据集与实体规范 (Entity & Benchmark Specifications)

### 2.1 基础统计与完整度
* **数据总对数**：25,772 条严格实测配对。
* **小分子激酶抑制剂**：68 种（均为临床期或已获 FDA 批准的小分子药物，0% 多肽污染）。
* **人类催化激酶靶点**：379 种人类催化激酶结构域。
* **矩阵密度**：**100.0% 完整矩阵**（$68 \times 379 = 25,772$），无任何未测空洞或推测插值。

### 2.2 预测目标与截断处理 (Endpoint & Censoring)
* **原始测定值**：解离常数 $K_d$（单位：$\text{nM}$）。
* **标准连续回归目标**：负对数亲和力转化值 $pK_d$：
  * $pK_d = -\log_{10}(K_d \times 10^{-9}) = 9 - \log_{10}(K_d)$
* **截断上限分布（Censoring Audit）**：
  * **截断无活性对**：18,343 对（占比 **71.17%**），测定上限 $K_d = 10,000\,\text{nM}$，即 $pK_d = 5.00$；
  * **确证活性对**：7,429 对（占比 **28.83%**），亲和力范围 $K_d \in [0.015\,\text{nM}, 9,900\,\text{nM}]$，对应 $pK_d \in [5.004, 10.824]$；
  * **模型评估原则**：统一在 $pK_d$ 空间进行连续回归预测。

---

## 三、拓扑图聚类与双盲零泄漏隔离 (Topological Isolation Protocol)

为杜绝传统随机划分造成的严重信息泄漏，本协议确立严格的双端图拓扑聚类隔离标准。

### 3.1 小分子拓扑图聚类（Cold Drug Isolation）
* **分子表征**：Morgan 拓扑环形指纹（半径 2，2048 维，等价于 ECFP4）。
* **相似度度量**：Tanimoto 系数。
* **隔离阈值**：$T_{\text{cutoff}} = 0.40$。
* **聚类结果**：68 种小分子聚类为 **58 个独立拓扑簇**，最大连通分量仅 5 个小分子，平均簇大小 1.17。
* **5 折划分**：各折药物数分别为 14, 14, 14, 13, 13。
* **泄漏控制证明**：折间最大 Tanimoto 相似度为 **0.3796 < 0.40**，数学上严格证明零结构泄漏。

### 3.2 激酶靶点同源聚类（Cold Target Isolation）
* **比对算法**：全局 Needleman-Wunsch（NW）动态规划比对。
* **比对参数**：Match = $+2$，Mismatch = $-1$，Gap Penalty = $-2$。
* **同源度量**：比对相同氨基酸数除以比对总长度（Sequence Identity）。
* **隔离阈值**：$I_{\text{cutoff}} = 0.40$。
* **聚类结果**：379 种激酶聚类为 **197 个同源簇**，最大连通分量仅 11 个激酶（Eph 家族），平均簇大小 1.92。
* **5 折划分**：各折激酶数分别为 76, 76, 76, 76, 75。
* **泄漏控制证明**：折间最大序列一致性为 **0.3993 < 0.40**，数学上严格证明零序列同源泄漏。

### 3.3 双图块正交划分与四大评估域 (Bi-clustering Block Partition)

依据冷药与冷靶的五折划分方案，取前 4 折作为已知域（Seen），第 5 折作为留出未知域（Unseen），形成四大互斥评估子域：

| 评估子域 (Domain) | 构成规模 | 样本量 (对) | 占比 (%) | 科学评测目标与泄漏控制 |
|---|---|---:|---:|---|
| **1. 训练主块 (Train Block)** | 55 药 $\times$ 304 靶 | **16,720** | **64.88%** | 训练已知化学骨架与已知激酶家族的相互作用规律 |
| **2. 严格双盲冷启动测试块 (Strict Dual-Cold Test)** | 13 新药 $\times$ 75 新靶 | **975** | **3.78%** | **两端皆未见**；测试药物对训练集最大相似度仅 0.3333，测试激酶对训练集最大一致性仅 0.3983；绝对零泄漏 |
| **3. 冷靶点/见药物测试块 (Cold Target Test)** | 55 已知药 $\times$ 75 新靶 | **4,125** | **16.01%** | 评估已知抑制剂针对全新同源簇激酶的结合亲和力泛化能力 |
| **4. 冷药物/见靶点测试块 (Cold Drug Test)** | 13 新药 $\times$ 304 已知靶 | **3,952** | **15.33%** | 评估未知化学骨架抑制剂针对已知激酶的虚拟筛选能力 |
| **全集总计** | 68 药 $\times$ 379 靶 | **25,772** | **100.00%** | 四个子域正交无重叠，总和严格等于全集 |

---

## 四、表征工程与模型基准体系 (Representation & Baselines)

### 4.1 输入特征规范
* **药物小分子特征**：
  * 2048 维 Morgan 拓扑环形指纹（Bit Vector, Radius=2）。
* **激酶靶点特征**：
  * 20 维氨基酸组成频率（Amino Acid Composition, AAC）；
  * 8 维全局理化特征（归一化长度、平均疏水性、归一化电荷、电荷密度、疏水比例、阳离子比例、Boman 结合指数、半胱氨酸存在性指示器，共 28 维）。
* **特征拼接**：配对特征向量为药物特征与靶点特征的拼接向量（维数：$2048 + 28 = 2076$ 维）。

### 4.2 候选基准模型 (Predeclared Baselines)
1. **Dummy Regressor (Mean Baseline)**：始终预测训练集 $pK_d$ 均值，确立性能统计学下界。
2. **Ridge Regression**：L2 正则化线性岭回归（$\alpha = 1.0$），测试简单线性组合的表征能力。
3. **HistGradientBoostingRegressor (GBDT)**：直方图梯度提升决策树（`max_iter=50`, `max_depth=6`, `learning_rate=0.1`, `random_state=42`），测试非线性树模型能力。
4. **Multi-Layer Perceptron (MLP)**：多层感知机（`hidden_layer_sizes=(128, 64)`, `activation='relu'`, `max_iter=50`, `early_stopping=True`, `random_state=42`），测试轻量神经网络拟合能力。

### 4.3 评估指标定义
* **均方根误差 (RMSE)**：$\sqrt{\frac{1}{N} \sum_{i=1}^N (y_i - \hat{y}_i)^2}$
* **平均绝对误差 (MAE)**：$\frac{1}{N} \sum_{i=1}^N |y_i - \hat{y}_i|$
* **皮尔逊相关系数 (Pearson $r$)**：预测值与真实值的线性相关程度。
* **斯皮尔曼等级相关 (Spearman $\rho$)**：预测值与真实值的单调排序相关性。
* **一致性指数 (Concordance Index, CI)**：真实值不同的样本对中预测排序一致的概率，药物虚拟筛选核心指标。

---

## 五、不可变约束与数据防篡改门禁 (Gatekeeper & Immutability)

1. **历史六大受保护文件不可变**：
   * `04_paper/research_status.json`
   * `03_experiments/prepared/amd02_evidence_clean_20261001/records.csv`
   * `03_experiments/prepared/amd02_evidence_clean_20261001/cluster_membership.csv`
   * `03_experiments/prepared/amd02_evidence_clean_20261001/manifest.json`
   * `03_experiments/audits/mic_training_readiness_20261004_v26.json`
   * `03_experiments/audits/project_closeout_20261005_v1/review/merged_candidate_decisions.csv`
   在任何训练和评估前后必须校验 SHA-256 哈希，保持 100% 不变。
2. **划分方案只读冻结**：
   * 严格锁定 `03_experiments/audits/dti_davis_isolation_review_20261006_v1/fold_memberships.json`（SHA-256: `f74409e6d62f20fbb9ee9481cda4120c9fa4fa704d2817461ca595f8ada1b500`）。
   * 严禁在训练过程中根据测试集表现微调或泄露任何划分。
3. **环境锁定**：
   * Python 3.11, NumPy 2.4.4, Pandas 3.0.2, Scikit-learn 1.8.0。不引入外部未经审计的黑盒依赖。
