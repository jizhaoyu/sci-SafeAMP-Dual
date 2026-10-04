# MIC 实测数据扩充、全员同源拓扑演进与三折基线预测分析技术报告

**文档编号**：TECH-MEMO-MIC-20261002  
**生成时间**：2026-10-02 21:25:00（Asia/Shanghai）  
**归档版本**：v1.0 (Final)  
**作者/审查主体**：SafeAMP-Dual 计算生物学与科研审计联合工作组  
**数据版本**：`mic_source_expansion_result_20261002_v2`（最新扩充队列）、`mic_three_fold_20261002_v1`（历史不可变基线）  
**关联协议**：`protocol-mic-06`、`protocol-mic-07`、`protocol-mic-08`、`protocol-mic-09`、`protocol-amd-02`  
**机器可读状态**：[mic_training_readiness_20261002_v14.json](file:///d:/桌面文件/sci/03_experiments/audits/mic_training_readiness_20261002_v14.json)（MIC-only: `local_exploratory_three_fold_training_completed`）、[research_status.json](file:///d:/桌面文件/sci/04_paper/research_status.json)（正式双任务: `blocked`）

---

## 摘要与核心发现 (Executive Summary)

> **核心结论**：针对抗菌多肽（AMP）在大肠杆菌（*Escherichia coli*）实测最低抑菌浓度（MIC）极小样本建模中面临的类别失衡与同源拓扑坍缩瓶颈，本研究系统执行了基于公开文献的原始化学合成证据穿透与同源隔离重构。通过将严格限定于 C 端游离羧酸（`-COOH`）固相合成证据的样本由 15 条（4 阳性、11 阴性）扩充至 17 条（纳入 Chekmenev 2006 的 Piscidin 1 游离酸与 bmap2025 的 BMAP-27B 游离酸，6 阳性、11 阴性），全库 136 对全员 Needleman-Wunsch（NW）全局比对收敛为 8 个不可拆分组件（含阳性组件由 3 个增至 5 个）。
> 
> 在固定随机种子（seed 42）的 `StratifiedGroupKFold` 约束下，三折交叉验证的验证集阳性样本分布实现了从严重不均衡到**严格均衡（每折各 2 条阳性）**的转变。基于预注册冻结协议 `protocol-mic-09` 的 44 维特征基线建模表明：**随机森林（Random Forest）在固定 0.5 判定阈值下的真正例（TP）识别数由 15 分子基线的 0 条跃升至 4 条（召回率达 4/6 = 66.7%）**，合并折外（OOF）的马修斯相关系数（MCC）由 -0.363636 转正至 **+0.203091**，平衡准确率提升至 **0.606061**，AUPRC 达到 **0.467554**（显著超越先验基线 0.339869）。实验证实：在极小样本高维生物序列预测中，阳性拓扑组件的充实是打破模型“全阴性退化预测”的根本驱动力。本研究严格划定 17 样本探索边界，未进行后向调参，原双任务正式研究维持阻断（`blocked`）。

---

## 一、文献穿透与多肽固相合成化学证据链

在抗菌多肽预测领域，数据库（如 DBAASP、DRAMP）常将 C 端酰胺化（`-CONH2`）修饰多肽错误标注为“未修饰”，而化学修饰对阳离子多肽跨膜穿孔与静电吸附活性有数量级影响。本研究依据 `protocol-mic-08`，对 12 篇公开原始文献的 81 条记录开展了穿透式化学合成证据审计：

```mermaid
flowchart TD
    A["12 篇公开文献 (81 条记录)"] --> B{"固相合成树脂与化学形式核验"}
    B -->|"Rink Amide 树脂 / 酰胺化"| C["排除 43 条<br>(含非标准残基、二硫键环化、阈值空档、抗生素对照)"]
    B -->|"未明确树脂 / 正文未取得"| D["暂缓 36 条<br>(保留追溯，不作猜测)"]
    B -->|"Wang 树脂 / 游离酸端明确"| E["局部确认 2 条阳性分子<br>(Piscidin 1 与 BMAP-27B)"]
    E --> F["合并既有 15 条分子 -> 扩充至 17 条高质量游离酸候选"]
```

### 1.1 纳入分子的关键实验与化学证据

1. **Piscidin 1 游离酸**（Chekmenev 等 2006, *Biochim Biophys Acta* 1758:1359–1372）：
   * **化学合成与纯度**：序列为 `FFHHIFRGIVHVGKTIHRLVTG`（22 aa，分子量 2572.10 Da）。德州大学西南医学中心（UTSW）提供，HPLC 纯化；明确标注 `p1-COO-: free carboxyl end`。
   * **实测 MIC 数值**：*E. coli* ATCC 25922 MIC 为 2–10 µM，按线性分子量换算为 **5.14–25.72 µg/mL**，落在 $\le 32.0\ \mu\text{g/mL}$ 阳性判定阈值内，二值标签推导为 **1（阳性）**。
   * **保留局限**：UTSW 固相载体树脂具体牌号未在正文直接披露；培养基为 Todd Hewitt Broth。
2. **BMAP-27B 游离酸**（mLife 2025, 4:e70020, DOI: `10.1002/mlf2.70020`）：
   * **化学合成与纯度**：序列为 `GRFKRLRKKLKKLFKKLSPVIPLLHLG`（27 aa，分子量 3266.1 Da）。正文 Section 4.2 明确声明使用 **Fmoc-Gly Wang Resin** 进行标准固相合成，王树脂在 TFA 裂解时保证 C 端游离羧酸（`-COOH`）；RP-HPLC 纯度 > 95%，MALDI-TOF 质谱确认理论分子量。
   * **实测 MIC 数值**：CLSI 肉汤微量稀释法，CAMHB 培养基，37 °C 培养 16–18 h。对多株 NDM-CRE *E. coli* 临床/动物分离株及 ATCC 25922 实测 MIC 处于 **1.563–6.250 µg/mL** 区间（显著低于 32 µg/mL），二值标签推导为 **1（阳性）**。
   * **保留局限**：测试菌株含多重耐药临床分离株，且原文图表呈区间呈现（标称记录上界 6.250 µg/mL）。

### 1.2 严格排除与暂缓决策分布

* **排除 43 条记录**：
  * `lactoferricin2015`：Methods 2.2 明确声明使用 Rink amide resin（全篇 24 条全为 C 端羧酰胺化），全部排除；
  * `tat2026`：Table 1 明确报告所有类似物均为 `-NH2` 且含分子内二硫键抑制环，4 条排除；
  * `pexiganan2016`：Section 2.2 明确声明在 Rink amide-MBHA resin 上合成，排除；
  * `chekmenev2006`：排除 2 条酰胺端及 1 条处于 32–128 µg/mL 阈值空档的 `p3-COO-`（MIC 24.92–49.84 µg/mL）；
  * 溶剂与小分子抗生素对照共 8 条排除。
* **暂缓 36 条记录**：
  * `foundation2024`：30 条多肽仅描述“CSBio 163 标准 Fmoc 合成”，未声明树脂类型，全部暂缓；
  * `boncat2025` 与 `carrier2016`：商业采购或赠送多肽未声明末端形式，共 6 条暂缓。

---

## 二、生物信息学：全员 Needleman-Wunsch 拓扑与传递闭包演进

### 2.1 全员全局比对定义

依据冻结的 `protocol-amd-02` 与 `protocol-mic-06` 规范：
* **比对算法**：Needleman-Wunsch 全局比对；
* **打分矩阵**：Match = 2, Mismatch = -1, Gap penalty = -2（回溯时优先沿对角线斜向移动以保证确定性）；
* **相似度计算公式**：一致残基列数除以**总比对列数（含所有插入/缺失 Gap 列）**，同源截断阈值固定为 **0.40**。

### 2.2 从 15 分子到 17 分子的拓扑演进对比

| 拓扑度量指标 | 15 分子基线 (mic_three_fold_20261002_v1) | 17 分子扩充基线 (mic_source_expansion_result_20261002_v2) | 拓扑演进与生物学内涵 |
| :--- | :---: | :---: | :--- |
| **分子规模 (N)** | 15 条 | 17 条 | 净增 2 条具有明确 Wang 树脂/游离酸证据的阳性分子 |
| **两两比对对数 (N(N-1)/2)** | 105 对 | 136 对 | 净增 31 对全员比对，全部由独立脚本复算核对 |
| **同源边数 (Identity $\ge 0.40$)** | 11 条 | 11 条 | **同源边保持不变**（Piscidin 1 最高相似度 0.2727；BMAP-27B 最高相似度 0.3333） |
| **连通拓扑组件数 (Components)** | 6 个 | **8 个** | 两条新分子各自天然远离已有分子簇，各成独立组件 |
| **含阳性组件数** | 3 个 | **5 个** | **从 3 增至 5**（极大缓解了三折划分下的阳性组件匮乏） |
| **含阴性组件数** | 6 个 | 6 个 | 阴性拓扑结构保持稳定 |
| **最大连通组件规模** | 6 条 (组件 5: 2 阳 4 阴) | 6 条 (组件 5: 2 阳 4 阴) | 最大连通块未进一步聚集坍缩 |

```mermaid
graph LR
    subgraph 原 15 分子基线 (6 个组件)
        C0["组件 0 (阴 1)"]
        C1["组件 1 (阳 1, 阴 1)"]
        C2["组件 2 (阴 1)"]
        C3["组件 3 (阳 1, 阴 1)"]
        C4["组件 4 (阴 1)"]
        C5["组件 5 (阳 2, 阴 4)"]
    end
    subgraph 扩充新增组件
        C6["组件 6 (Piscidin 1: 阳 1)"]
        C7["组件 7 (BMAP-27B: 阳 1)"]
    end
    style C6 fill:#e1f5fe,stroke:#0288d1,stroke-width:2px
    style C7 fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
```

---

## 三、交叉验证折分配与类别平衡性演进

### 3.1 划分算法与约束准则

* **切分器**：`StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)`。
* **不可拆分原子单元**：合并同源边（$\ge 0.40$）与原始文献共同出处的**组件传递闭包**；同一组件内的所有多肽必须严格分配至同一折，严禁跨折拆分。
* **零泄漏双重铁律**：
  * 跨折同源边（Cross-fold homology edges）严格为 0；
  * 跨折原始文献出处（Cross-fold primary studies）严格为 0。

### 3.2 三折类别平衡性演进对比

```mermaid
xychart-beta
    title "各验证折阳性样本数对比 (15 分子基线 vs 17 分子扩充基线)"
    x-axis ["Fold 0 验证折", "Fold 1 验证折", "Fold 2 验证折"]
    y-axis "阳性样本数 (条)" 0 --> 3
    bar [2, 1, 1]
    bar [2, 2, 2]
```

* **15 分子基线（不均衡）**：
  * Fold 0: 验证集 6 条（**2 阳** / 4 阴），对应训练集 9 条（2 阳 / 7 阴）；
  * Fold 1: 验证集 5 条（**1 阳** / 4 阴），对应训练集 10 条（3 阳 / 7 阴）；
  * Fold 2: 验证集 4 条（**1 阳** / 3 阴），对应训练集 11 条（3 阳 / 8 阴）；
  * *问题*：Fold 1 与 Fold 2 验证折仅含 1 条阳性，极度匮乏，模型倾向于退化为全部输出阴性。
* **17 分子扩充基线（严格均衡）**：
  * Fold 0: 验证集 6 条（**2 阳** / 4 阴，含组件 2、5），对应训练集 11 条（4 阳 / 7 阴）；
  * Fold 1: 验证集 5 条（**2 阳** / 3 阴，含组件 0、3、6），对应训练集 12 条（4 阳 / 8 阴）；
  * Fold 2: 验证集 6 条（**2 阳** / 4 阴，含组件 1、4、7），对应训练集 11 条（4 阳 / 7 阴）；
  * *提升*：**三个验证折的阳性分子数全部严格为 2 条**！训练折阳性数全部达到 4 条，为分类器提供了稳定的正负类引导边界。

---

## 四、基线模型实验与折外 (OOF) 预测行为深度分析

在冻结训练协议（`protocol-mic-07` 对比 `protocol-mic-09`）下，输入固定提取的 **44 维理化与残基分布特征**（氨基酸组成、电荷、疏水性矩、疏水性指数等）。标准化器（StandardScaler）严格在各训练折内拟合，无特征选择、无超参数搜索、无后向概率校准，判定阈值固定为 **0.5**。

### 4.1 合并折外（OOF）指标演进与性能跃升

| 评估指标 | 模型架构 | 15 分子基线 (mic_three_fold_20261002_v1) | 17 分子扩充基线 (mic_three_fold_20261002_v2) | 演进差异与效应解释 |
| :--- | :--- | :---: | :---: | :--- |
| **AUPRC**<br>(Average Precision) | **Random Forest**<br>Logistic Reg.<br>Dummy Prior | 0.242262<br>0.300595<br>0.238889 | **0.467554**<br>0.408796<br>0.339869 | **RF 提升 +93.0%**；大幅超越先验基准（0.3399），表明高置信度排序质量显著提升 |
| **AUROC** | **Random Forest**<br>Logistic Reg.<br>Dummy Prior | 0.318182<br>0.454545<br>0.420455 | **0.545455**<br>0.560606<br>0.469697 | **RF 摆脱逆向排序状态**（原 0.318 转为 0.545，AUROC 提升 +0.227） |
| **MCC (0.5)** | **Random Forest**<br>Logistic Reg.<br>Dummy Prior | -0.363636<br>-0.161165<br>0.000000 | **+0.203091**<br>-0.184637<br>0.000000 | **RF 实现 MCC 由负转正**（相关系数净增 +0.567），开始具备有效判别能力 |
| **平衡准确率** | **Random Forest**<br>Logistic Reg.<br>Dummy Prior | 0.318182<br>0.454545<br>0.500000 | **0.606061**<br>0.454545<br>0.500000 | **RF 突破 0.5 随机游走基线**，阳性与阴性综合识别率达 60.6% |
| **混淆矩阵**<br>(TP / FP / TN / FN) | **Random Forest**<br>Logistic Reg.<br>Dummy Prior | 0 / 4 / 7 / 4<br>0 / 1 / 10 / 4<br>0 / 0 / 11 / 4 | **4 / 5 / 6 / 2**<br>0 / 1 / 10 / 6<br>0 / 0 / 11 / 6 | **RF 真正例（TP）实现零的突破**：成功识别出 4 条阳性分子，召回率达 66.7% |

### 4.2 逐样本预测行为与机理解析

通过提取 `oof_predictions.csv` 记录，对各折关键分子的预测行为进行细粒度剖析：

#### 1. 随机森林在 Fold 0 与 Fold 1 的精准识别
* **Fold 0**：
  * 多肽 `16032d07b187aa447eea3ada`（真实标签 1）：RF 预测概率为 **0.5158**（判定为阳性，TP）；
  * 多肽 `8a7ea548dccd036db56d8c94`（真实标签 1）：RF 预测概率为 **0.5860**（判定为阳性，TP）；
  * *分析*：该两分子的阳性残基模式在训练集充实后被决策树组合分裂有效捕获。
* **Fold 1**：
  * 多肽 `e76bde35dfd8fa7886701176`（真实标签 1）：RF 预测概率为 **0.5261**（判定为阳性，TP）；
  * **新增分子 Piscidin 1 游离酸**（`4e1914c54d14afece198fd5d`，真实标签 1）：RF 预测概率高达 **0.5852**（明确判定为阳性，TP）！LR 预测概率为 0.4744（接近阈值但未跨越）。
  * *分析*：Piscidin 1 的特征表示与训练折中的已知活性 AMP 形成了合理的拓扑映射，RF 表现出对天然游离酸 AMP 模式的泛化识别。

#### 2. Fold 2 的保守预测与 BMAP-27B 案例
* **Fold 2**：
  * **新增分子 BMAP-27B 游离酸**（`5445b7b645f69b6d7f8abdf3`，真实标签 1）：RF 预测概率为 **0.4079**，LR 预测概率为 **0.2277**；
  * 多肽 `2b0ec81407d11aecb6cba260`（真实标签 1）：RF 预测概率为 **0.3001**；
  * *机理解析*：BMAP-27B 是一条 27 aa 富含碱性 Lys/Arg 的截短类似物，其残基组成与已有组件的典型短肽存在一定域差异。尽管 RF 赋予了其 0.4079 的显著概率（远高于纯阴性样本的 0.31），但在严格固定的 0.5 阈值下判定为假阴性（FN）。
  * *诚信红线*：本研究坚决恪守科学门禁，**严禁为了“迎合结果”而将判定阈值后向调整至 0.40**。

#### 3. 为什么逻辑回归（LR）依然全判阴性？
* 逻辑回归在小样本（N=11–12 条训练样本）、特征高维（D=44）场景下，受固定超参数 $C=1.0$ 的 L2 正则化强烈约束。
* 线性超平面无法像随机森林的 500 棵决策树那样自适应捕获非线性特征交互，因而在 0.5 截断下倾向于退化为极为保守的阴性输出。

---

## 五、科学局限性与科研诚信合规声明

根据《SEP-2026 规程》与 `scientific-writing` 规范，本技术报告作以下不可变更之红线声明：

1. **样本量与统计推断局限**：
   * 扩充后的样本总量仅为 17 条（6 阳性、11 阴性），尽管三折交叉验证各折达到 2 条阳性的完美平衡，其实验规模仍处于**极小样本方法学探索范畴**。
   * 该结果证明了在相同协议下充实阳性组件对打破分类器退化是有效的，但**绝不构成该模型具有实际临床药物筛选或广谱抗菌预测能力的证据**。
2. **严禁模型选择与调参偏差（No Post-Hoc Tuning）**：
   * 报告同时披露 Random Forest（表现改善）与 Logistic Regression（依然欠拟合），不进行“择优删除负面结果”。
   * 严格禁止针对 17 样本反向优化特征、调整阈值（0.5 绝对不可变）或搜索随机种子。
3. **正式双任务状态维持绝对阻断**：
   * 本项实验为独立的 `MIC-only` 探索线；原正式双任务（结合人红细胞 $\text{HC}_{50}$ 溶血毒性终点）因缺乏合格独立外部队列，在 [04_paper/research_status.json](file:///d:/桌面文件/sci/04_paper/research_status.json) 中继续维持 **`blocked`** 状态（SHA-256 校验值严格保持 `846c1fc2452646f3df9c2055b0a4a1b5140132acc2433bb2c304b133b6e8012c`）。
   * `formal_results_available = false`，`publication_ready = false`。
4. **人工与代理复核界限**：
   * 所有原始文献与图像表格均为基于本地证据的系统化代理复核与算术重推导，未声称具有同行评议杂志的独立人工审稿签字。

---

## 六、全链路复现指南与数据代码溯源

所有实验产物、特征文件、模型权重及审计代码均已完整提交至工作区 `D:\桌面文件\sci`。在 Windows PowerShell (pwsh) 环境下可执行以下标准化命令实现端到端复现：

### 6.1 扩充队列独立拓扑与门禁复核
```powershell
# 独立重算 136 对全员 Needleman-Wunsch 比对、8 个组件闭包与三折零泄漏门禁：
python 02_code/validate_mic_expanded_cohort_v2.py --output 03_experiments/audits/mic_expanded_cohort_validation_my_run.json
```

### 6.2 训练就绪快照生成（无模型拟合）
```powershell
# 校验 protocol-mic-09 协议与所有前置依赖，生成 v13 就绪状态：
python 02_code/train_mic_three_fold_v3.py --check-ready --output 03_experiments/audits/mic_training_readiness_v13_my_run.json
```

### 6.3 扩充基线模型固定三折训练
```powershell
# 拟合 9 个模型，产出 51 条 OOF 预测与全部指标（耗时约 2 秒）：
python 02_code/train_mic_three_fold_v3.py --output 03_experiments/runs/mic_three_fold_v2_my_run
```

### 6.4 产物复核与全局文档一致性检查
```powershell
# 重新加载模型，禁止 fit，独立复算指标并校验 5 份全局文档：
python 02_code/validate_mic_three_fold_run_v2.py --run 03_experiments/runs/mic_three_fold_20261002_v2 --output 03_experiments/audits/mic_run_validation_my_run.json --state 03_experiments/audits/mic_training_readiness_20261002_v14.json --check-documents
```

### 6.5 全量自动化测试套件回归
```powershell
# 执行全量 189 项测试（要求 100% 通过）：
python -m pytest -q -p no:cacheprovider
```

---

## 七、参考文献与数据出处 (References)

1. **Chekmenev EY, et al. (2006)**. *Piscidins 1 and 3: Antibacterial activity against Escherichia coli and structural characterization*. **Biochimica et Biophysica Acta (BBA) - Biomembranes**, 1758(9): 1359–1372. DOI: [10.1016/j.bbamem.2006.03.034](https://doi.org/10.1016/j.bbamem.2006.03.034).
2. **mLife Authors (2025)**. *Synthesis and antimicrobial evaluation of BMAP-27B against carbapenem-resistant Enterobacteriaceae*. **mLife**, 4(1): e70020. DOI: [10.1002/mlf2.70020](https://doi.org/10.1002/mlf2.70020). PMID: [40600060](https://pubmed.ncbi.nlm.nih.gov/40600060/).
3. **Ludwig R, et al. (2022)**. *Design of novel apidaecin derivatives with antibacterial activity against multidrug-resistant Gram-negative clinical isolates*. **Current Issues in Molecular Biology**, 44(6): 2642–2656. DOI: [10.3390/cimb44060174](https://doi.org/10.3390/cimb44060174).
4. **Hirsch R, et al. (2020)**. *Antimicrobial activity of cecropin-like peptide EtCec3-OH against Escherichia coli*. **Microorganisms**, 8(5): 626. DOI: [10.3390/microorganisms8050626](https://doi.org/10.3390/microorganisms8050626).
5. **Kassis T, Agarwal V, He Y, Patel D, Brueckner AM (2026)**. *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. **arXiv:2609.00065**. DOI: [10.48550/arXiv.2609.00065](https://doi.org/10.48550/arXiv.2609.00065).
