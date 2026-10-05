# 人红细胞 HC50 实验证据与双任务独立外部队列穿透式审计报告 (完全修正版)

**审计目录**：[gemini_hc50_external_review_20261004_v1](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1)  
**审计基线**：正式双任务协议 `protocol-amd-02` 与筛查规范 `protocol-amd-03`  
**审查方式**：`agent_primary_source_review`（穿透式文献与数据库实验数据审计，非独立人工审批）  
**审计结论**：`blocked`（客观科研阻断；合格独立双任务外部候选数为 **0**）  
**正式研究状态**：严格维持 [research_status.json](file:///d:/桌面文件/sci/04_paper/research_status.json) 中的 `blocked`，未做任何修改（`formal_state_modified = false`，`model_fit_calls = 0`）

---

## 零、前序版本错误复盘与全要素穿透修正说明

针对此前审计脚本与报告中存在的五大严重缺陷，本版本已全面完成逻辑重构、数据清洗与报告数字的完全同步修正：

1. **马红细胞误判为人红细胞问题彻底修正**：
   - **原错误**：Dermatoxin-PD1（PMC13515218）原文明确记载使用新鲜脱纤维马血（Section 4.11.1: *defibrinated horse blood*），但前期代码误将其当作人红细胞纳入证据池。
   - **本次修正**：已将靶标细胞类型纠正为 `Horse erythrocytes`，严格判定为动物红细胞终点，依据门禁 2 予以坚决否决，排除出人红细胞证据池。
2. **Brevinin-1 E8.13 序列与实验实测值彻底修正**：
   - **原错误**：多肽序列记录错误；原文 HC50 明确为 41.87 µM，被误写为 16.2 µM；原文 *E. coli* MIC 明确为 >24.8 µM，被误写为 6.25 µM。
   - **本次修正**：
     - 序列纠正为原文 Table 1 确证序列：`FLGALFKVASKLVPAAICSFSKKC`（24 aa，中性分子量 2529.14 Da，含一对二硫键构成的 Rana box 环，C 端采用 Rink amide 树脂合成具有酰胺化 `-CONH2` 修饰）。
     - *E. coli* MIC 纠正为原文 Table 3 实测值：`>24.8 µM`（折合标准化浓度为下界 62.72 µg/mL，上界为 $+\infty$），处于灰色区间 $(32, 128)$，标签确切判定为 `unknown`。
     - 人红细胞 HC50 纠正为原文 Section 3.7 拟合实测值：`41.87 µM`（折合标准化浓度为 105.89 µg/mL），处于不确定区间 $(100, 250)$，标签确切判定为 `unknown`。
     - 全局对齐最大一致性为 **0.5833**（与开发集 `DBAASP:948` 产生显著泄漏，门禁 3 否决）；同时由于 C 端酰胺化与二硫键环，门禁 1 否决。
3. **单浓度溶血百分比冒充 HC50 漏洞彻底封堵**：
   - **原错误**：前期代码因包含匹配逻辑错误（`'50%' in grp`），误将 DBAASP 中分组名为 `40-50% Hemolysis` 的离散单点测定（如 43%、48%、45.9±3.9%）当成 HC50 纳入。
   - **本次修正**：建立严格的字符串与数值解析断言，所有含 `%` 的百分比数值或属于单浓度分组（如 `40-50% Hemolysis`）的记录一律标记为 `single_concentration_percentage`，严禁作为 HC50 终点，直接从池 A 中剔除。
4. **数据库缓存未经原文复核标记不实问题彻底修正**：
   - **原错误**：39 条 DBAASP 数据库记录仅凭数据库元数据被标记为“无缺失”并塞入池 A。
   - **本次修正**：所有未查阅原始文献方法、图表与全文测定谱图的 39 条 DBAASP 记录，一律实事求是标记为：
     - `evidence_type = unverified_database_cache`
     - `missing_fields = primary_article_tables_and_methods_not_retrieved`
     - `decision = pending_primary_article_review`
     并全数归档至 [excluded_or_pending.csv](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/excluded_or_pending.csv)，严禁进入已核实池 A。
5. **报告与机器输出数据口径彻底统一**：
   - **原错误**：实际机器计算结果为 83 条候选、76 条不同序列、26 条同源隔离失败；报告笔误写成 83 条不同序列、47 条失败。
   - **本次修正**：报告正文、筛选漏斗与表格中的全部统计数字与脚本、CSV、JSON 机器产物实现 100% 严格一致：
     - 候选记录总数：**83 条**
     - 唯一序列数：**76 条**
     - 全员同源隔离失败数（$\ge 0.40$）：**26 条**（31.3%）
     - 全员同源隔离通过数（$< 0.40$）：**57 条**（68.7%）
     - 两两比对总量：**34,611 对**
     - 池 A（人红细胞 HC50 原文已核实）：**1 条**（Brevinin-1 E8.13，带明确结构与泄漏局限性说明）
     - 池 B（合格外部候选）：**0 条**

---

## 一、核心结论先行

1. **证据池 A（人红细胞 HC50 测定证据池）**：
   - 经穿透式原文复核，仅确证 **1 个分子**（Brevinin-1 E8.13，PMC12412326，HC50 = 41.87 µM / 105.89 µg/mL）。
   - 该分子明确存在 C 端酰胺化（Rink amide 树脂合成）与 Rana box 二硫键环结构，且与开发集序列最大全局一致性达到 **0.5833**，不能作为双任务测试集。
   - 其余 39 条 DBAASP 记录因未取得原始文献图表全文复核，一律标记为 `pending_primary_article_review` 并隔离至未决池。
2. **证据池 B（正式双任务独立外部候选队列池）**：
   - 经四重门禁全要素穿透判定，在全部 **83 个候选分子**（76 条不同序列）中：
     - **门禁 1（化学形式与拓扑结构）**：40 个通过，43 个被否决（主要原因：Rink Amide 树脂合成酰胺化 `-CONH2`、含 2–6 个 Cys 的二硫键环肽、环状主链、纳米颗粒修饰）。
     - **门禁 2（双端点定量实测与二值标签判定）**：0 个通过，83 个被否决（缺少人红细胞 HC50、单浓度溶血率冒充 HC50、MBC 代替 MIC、或实测值处于灰色区间）。
     - **门禁 3（全员 Needleman–Wunsch 同源隔离 < 0.40）**：57 个通过，26 个被否决（与 417 条开发集记录对齐中存在最大一致性 $\ge 0.40$ 的泄漏边）。
     - **门禁 4（研究源头独立性）**：80 个通过，3 个因与开发集原始 PMID 重叠被否决。
   - **最终合格双任务独立外部候选数：0**。
   - 维持正式研究状态 `blocked`。

---

## 二、筛选漏斗统计 (Screening Funnel)

```
[原始组装候选池]：83 个分子记录（76 条不同序列：DRAMP 历史 39 条 + DBAASP 缓存 39 条 + PMC 原文 5 条）
        │
        ▼ (门禁 1：分子化学身份与线性游离酸结构审查)
[线性、天然、未修饰游离酸]：40 个记录通过
  └─ 否决 43 个：二硫键/环肽 (23)、酰胺化/树脂修饰 (12)、脂肪酸/纳米修饰 (3)、非标准氨基酸/长度超限 (5)
        │
        ▼ (门禁 2：双任务定量实测且二值标签确切解析)
[双端点有效且标签明确]：0 个记录通过
  └─ 否决全部 83 个：
     * 39 条 DRAMP 历史记录：缺少定量 HC50（仅报告单浓度溶血百分比）、MBC 替代 MIC、或大鼠/绵羊红细胞
     * 39 条 DBAASP 缓存记录：未取得原始文献图表穿透核验，处于 pending_primary_article_review
     * 5 条 PMC 新检记录：马红细胞 (1)、无溶血测定 (1)、绵羊红细胞 (2)、HC50处于灰色区间且MIC为下界区间 (1)
        │
        ▼ (门禁 3：全员 Needleman–Wunsch 同源隔离 < 0.40)
[全员 NW < 0.40 通过]：57 个记录通过；26 个记录失败（存在 >= 0.40 的开发集同源边）
        │
        ▼ (门禁 4：文献独立性)
[独立无重叠研究]：80 个记录通过；3 个记录失败（与开发集研究重叠）
        │
        ▼
[最终合格双任务外部独立候选集]：0 个 (N = 0)
```

---

## 三、证据池 A（人红细胞 HC50 证据库）分析

证据池 A 收集所有经过原始文献图表核查的人红细胞定量 HC50 测定：

1. **入池规模**：共归档 **1 个分子**（Brevinin-1 E8.13，PMC12412326）。
2. **端点实测详情**：
   - 靶细胞：Human erythrocytes（人新鲜红细胞）；
   - 实测 HC50：$41.87\ \mu\text{M}$（折合 $105.89\ \mu\text{g/mL}$）；
   - 标签判定：处于不确定区间 $(100, 250)$，标签为 `unknown`；
   - 配对 MIC：$E.\ coli$ MIC $>24.8\ \mu\text{M}$（折合下界 $62.72\ \mu\text{g/mL}$），处于不确定区间 $(32, 128)$，标签为 `unknown`；
   - 结构特征：含 Rana box 二硫键环（Cys18–Cys24），C 端为 Rink amide 树脂合成酰胺化；
   - 开发集同源性：与 `DBAASP:948` 全局比对一致性为 0.5833（严重泄漏）。
3. **未决记录状态**：
   - 39 条 DBAASP 候选记录全数归入 [excluded_or_pending.csv](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/excluded_or_pending.csv)，状态为 `pending_primary_article_review`，待未来取得商业数据库原始文献授权和图表后再行核验。

---

## 四、历史 39 条候选逐条穿透核验复核

对 [candidate_primary_audit.csv](file:///d:/桌面文件/sci/03_experiments/audits/dramp_dual_task_primary_audit_20261003_v1/candidate_primary_audit.csv) 中的 39 条历史候选进行逐条穿透文献核验：

1. **Tucker et al. 2018 (PMID 29307492, SLAY 肽系列，共 14 条)**：
   - **抗菌端点缺陷**：原文报告的是最小杀菌浓度（MBC），非微量肉汤稀释法 MIC。
   - **溶血端点缺陷**：原文仅报告在单固定浓度（$50\ \mu\text{M}$）下的单点溶血率（如 0.7%、1.7%、3.1%），从未测定或拟合定量 $\text{HC}_{50}$。
2. **Xu et al. 2017 (PMID 28258530, Catesbeianin-1 / DRAMP20968)**：
   - **穿透核查真相**：该论文发表于 *Biotechnol Lett*，为商业付费全文（非开源 PMC）。数据库文本记录的阶梯溶血率（0% 到 95%）为离散单点读数，未报告规范的标准拟合 $\text{HC}_{50}$；且其合成未排除 C 端酰胺化可能性。在未取得合法全文与谱图前，必须保持 `pending_access`，坚决撤销入选资质。
3. **D'Este et al. 2016 (PMID 27818338, 鲑鱼 Cathelicidin 衍生肽系列，共 5 条)**：
   - **溶血端点缺陷**：原文溶血活性仅报告定性表述“No hemolytic activity to human”与“No hemolytic activity to trout”，缺少定量测定浓度与半数溶血数据。
4. **Mathew & Nagaraj 2015 (PMID 26206286, HD5 线性类似物，共 6 条)**：
   - MyD5R / MyD5r 与 LaD5R / LaD5r 带有 N 端肉豆蔻酰基 / 月桂酰基共价脂肪酸修饰，违反未修饰肽边界；
   - D5R 与 D5r 仅报告在 $100\ \mu\text{M}$ 下为 0% 溶血，无 $\text{HC}_{50}$。
5. **非人红细胞溶血研究**：
   - Barksdale 2016 (PMID 27542832)：绵羊红细胞；且文献与开发集重叠；
   - Lee 2020 (PMID 32291307)：小鼠红细胞；
   - Shigeri 2015 (PMID 25312021)、Tani 2019 (PMID 30658410)：大鼠红细胞；
   - Li 2017 (PMID 28661457)：小鼠红细胞；
   - Seo 2014 (PMID 24495783)：鱼红细胞。
6. **纳米颗粒与偶联物**：
   - Pal 2019 (PMID 30872680)：银纳米颗粒（AgNP）复合体系，非单体多肽。

---

## 五、新检 5 篇公开文献的穿透核查情况

针对 Europe PMC 与 PubMed 检索获取的 5 篇开放获取 XML 全文（均归档于 `raw/` 目录）：

1. **PMC13515218 (PMID 42653830, *Molecules* 2026, Dermatoxin-PD1 系列)**：
   - 原文 Section 4.11.1 明确记载采用 **新鲜脱纤维马血（defibrinated horse blood）**，靶细胞为马红细胞，非人红细胞；且采用 Rink amide MBHA 树脂合成（C 端酰胺化）。门禁 1 与门禁 2 否决。
2. **PMC13510277 (PMID 42650737, *Antibiotics* 2026, D-TN6)**：
   - 为 D-型立体异构肽设计；毒性测试采用成纤维细胞与角质形成细胞（3T3 / HaCaT IC50），**未进行红细胞溶血测定**。门禁 2 否决。
3. **PMC13436381 (PMID 42370696, *Microbiol Spectr* 2026, Arg2MP-C)**：
   - 溶血测定使用的是 **绵羊红细胞（Sheep erythrocytes）**，非人红细胞。门禁 2 否决。
4. **PMC13216044 (PMID 42221479, *Front Microbiol* 2026, Han-Def1 / Han-Def2)**：
   - 具备 6 个 Cys、3 对二硫键的 CS$\alpha\beta$ 防御素；溶血靶标为 **绵羊红细胞**。门禁 1 与门禁 2 否决。
5. **PMC12412326 (PMID 40864826, *CIMB* 2025, Brevinin-1 E8.13)**：
   - 序列：`FLGALFKVASKLVPAAICSFSKKC`（24 aa）；
   - 人红细胞 HC50 = 41.87 µM（105.89 µg/mL）；*E. coli* MIC > 24.8 µM（下界 62.72 µg/mL）；
   - 采用 Rink amide 树脂合成（C 端酰胺化），含 Rana box 二硫键环；
   - 与开发集 `DBAASP:948` 比对一致性达到 0.5833。门禁 1、2、3 均否决。

---

## 六、全员序列同源性与泄漏审计结果

复用 `02_code/research_protocol_config.py` 中冻结的 Needleman-Wunsch 比对算法：
- 参数：Match `+2`，Mismatch `-1`，Gap `-2`，严格按对角优先字典序回溯；
- 统计口径：`identity_mode = 'alignment'`（比对列总长为分母，Gap 列视为不匹配计入分母）；
- 对全部 83 个候选分子与开发集 417 条记录完成 $83 \times 417 = 34,611$ 次全员两两对齐计算。

**确切统计结果**：
- **全员同源隔离失败（$\ge 0.40$）**：**26 个候选分子（31.3%）** 与开发集中至少一条记录的全局一致性 $\ge 0.40$。
- **全员同源隔离通过（$< 0.40$）**：**57 个候选分子（68.7%）**。
- 确切等于 0.4000 的边界样本（如 Brevinin 2-Ia、V-Protegrin 1 等）按协议一律判定为泄漏边并予以否决。
- 完整比较矩阵见 [similarity_to_development.csv](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/similarity_to_development.csv)。

---

## 七、科学阻断根源与对用户的具体建议

### 1. 阻断根源剖析
- 抗菌肽文献中，高活性的两亲性螺旋肽在化学合成时约有 **80% 以上常规采用 C 端酰胺化（Rink Amide 树脂）** 以提高体液稳定性；
- 天然提取的动物防御素、蛙皮素绝大多数依赖 **二硫键构象环（如 Rana box、CS$\alpha\beta$ 结构）**；
- 多数论文在初筛溶血毒性时，仅报告低浓度（如 $50\ \mu\text{M}$）下的单点溶血百分比，未进行完整的剂量反应拟合，导致缺少规范的半数溶血浓度 $\text{HC}_{50}$。
- 因此，在严格限定为“**天然 L-型、未修饰游离酸 `-COOH`、无二硫键线性单体、具备人红细胞定量 $\text{HC}_{50}$ 与 *E. coli* 测定 MIC、且与现有 417 条序列全员 NW $< 0.40$**”的超严格科学约束下，公开数据池中目前不存在合格的双任务独立测试样本。

### 2. 需用户补充的最小具体输入（若希望未来破局）
若希望推进双任务外部队列建立，建议采取以下科学方案之一：
1. **湿实验定向合成验证**：定向合成 5–10 条全同源 $< 0.40$ 的线性游离酸多肽，送第三方进行统一批次的人红细胞 $\text{HC}_{50}$ 与 *E. coli* ATCC 25922 MIC 湿实验测定，提供第一手不可辩驳的盲测数据。
2. **获取特定文献的高清补充材料/作者原始数据**：针对 Xu et al. 2017（Catesbeianin-1，PMID 28258530），需获取其质谱确证末端为 `-COOH` 的实测谱图与原始溶血曲线拟合数据表。
3. **方法学拓展（需制定新协议修订并经人工评审签署）**：若项目决定接纳含二硫键的环肽（如蛙皮 Rana box 多肽），必须在模型中引入拓扑/二硫键编码器，并对二硫键配对完整性建立独立的测定门禁；但这属于未来新协议范畴，不得擅自改动现行基线。

---

## 八、审计产物清单与文件摘要 (Manifest Summary)

主审计产物目录位于：
[gemini_hc50_external_review_20261004_v1](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1)

- [molecule_review.csv](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/molecule_review.csv) (83 行)
- [assay_observations.csv](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/assay_observations.csv) (166 行)
- [derived_labels.csv](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/derived_labels.csv) (166 行)
- [hc50_verified_pool.csv](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/hc50_verified_pool.csv) (1 条已核实，附带二硫键与泄漏局限性)
- [excluded_or_pending.csv](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/excluded_or_pending.csv) (84 行)
- [external_candidate_decisions.csv](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/external_candidate_decisions.csv) (83 行)
- [eligible_external_candidates.csv](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/eligible_external_candidates.csv) (1 行表头，0 行数据)
- [similarity_to_development.csv](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/similarity_to_development.csv) (34,611 行比对矩阵)
- [audit_summary.json](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/audit_summary.json) (记录 `status = "blocked"`, `model_fit_calls = 0`)
- [manifest.json](file:///d:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/manifest.json) (记录全量输入输出 SHA-256)
