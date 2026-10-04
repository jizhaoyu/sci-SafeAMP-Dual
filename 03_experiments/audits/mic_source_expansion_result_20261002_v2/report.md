# 公开 MIC 实测来源扩充审计报告 (protocol-mic-08)

## 1. 执行结论与概览

- **协议与审计版本**：`protocol-mic-08`，冻结于 `2026-10-02T11:22:32.120817+00:00`。
- **审查原始研究数**：12 篇（按 `discovery_catalog.json` 顺序逐篇审查）。
- **审查对应肽行/测定数**：共 81 条记录。
- **资格决定统计**：
  - 局部确认候选（未释放训练）：2 条（`chekmenev2006:p1-COO-`，Piscidin 1 游离羧酸；`bmap2025:BMAP-27B`，BMAP-27B 游离羧酸）。
  - 暂缓记录：36 条（包括末端化学未明确、正文未取得）。
  - 排除记录：43 条（包括 C 端羧酰胺化、非标准残基/二硫键/多聚体、小分子抗生素对照、阈值空档）。
- **扩充后候选队列**：17 条唯一分子（既有 15 条 + 新增 2 条），24 条原始 MIC 测定（4 条阳性 -> 6 条阳性，11 条阴性）。
- **全员同源比较**：全部 136 对，同源边 11 条（>=0.40）。
- **同源与研究传递闭包**：共 8 个不可拆分组件（含阳性 5 个、含阴性 6 个，最大组件 6 条分子）。
- **固定三折可行性检查**：`StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)` 门禁为 **PASSED**。
- **跨折泄漏检查**：跨折同源边 = 0，跨折原始研究 = 0，零泄漏。
- **训练释放状态**：`new_records_released_for_training = 0`，本轮审计**无权释放新训练记录**，训练状态保持阻断。
- **原正式状态**：`04_paper/research_status.json` 保持 `blocked`（SHA-256 校验一致）。

## 2. 12 篇原始研究审查清单与证据决定

| 序号 | source_id | DOI / 标识 | 原始文件 | 获取状态 | 审查肽行 | 核心决定与依据 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | chekmenev2006 | 10.1016/j.bbamem.2006.03.034 | chekmenev2006.pdf | acquired_pdf | 4 | 1 candidate molecule locally confirmed with condition limitations; 2 amidated excluded; 1 threshold gap excluded |
| 2 | foundation2024 | 10.1038/s41467-024-51933-2 | foundation2024.xml | acquired_xml | 32 | 30 peptides withheld due to undeclared solid-phase resin and unverified C-terminal chemistry; 2 antibiotic controls excluded |
| 3 | lactoferricin2015 | 10.1155/2015/480874 | lactoferricin2015.xml | acquired_xml | 24 | 24 rows excluded; Methods 2.2 explicitly declares Rink amide resin solid support (C-terminal carboxyamides); noncanonical residues and branched multimers also excluded |
| 4 | boncat2025 | 10.1039/d4md00742c | boncat2025.xml | acquired_xml | 10 | 4 peptides withheld (purchased from NovoPro Bioscience or gift without resin/terminal specification); 6 antibiotic/solvent controls excluded |
| 5 | carrier2016 | 10.1371/journal.pone.0146552 | carrier2016.xml | acquired_xml | 2 | 2 peptides withheld; recombinant (P)GKY20 has extra N-terminal Pro and unverified C-terminal acid; synthetic GKY20 from INBIOS s.r.l. lacks resin/terminal specification |
| 6 | drosocin2002 | 10.1021/jm020861d | drosocin2002_metadata.json | metadata_only | 1 | Withheld; primary article XML/PDF full text was not retrievable in this acquisition batch |
| 7 | pexiganan2016 | 10.48550/arXiv.1606.00620 | pexiganan2016.pdf | acquired_pdf | 1 | 1 peptide excluded; Section 2.2 explicitly declares solid-phase synthesis on Rink amide-MBHA resin (GIGKFLKKAKKFGKAFVKILKK-NH2) |
| 8 | brucin2020 | who_imsear:0dabbda4-b70a-402d-ac2c-c2d64c37e124 | N/A | download_failed | 1 | Withheld; WHO IMSEAR PDF download failed during acquisition |
| 9 | apidaecin2009 | 10.1007/s00726-009-0261-2 | apidaecin2009.xml | request_failed_500 | 1 | Withheld; Europe PMC fullTextXML endpoint returned HTTP 500 error response during acquisition |
| 10 | neopeptides2005 | 10.1128/AAC.49.8.3368-3374.2005 | neopeptides2005.xml | request_failed_500 | 1 | Withheld; Europe PMC fullTextXML endpoint returned HTTP 500 error response during acquisition |
| 11 | bmap2025 | 10.1002/mlf2.12157 | bmap2025.xml | acquired_xml | 1 | 1 candidate molecule locally confirmed with multiresistant isolate condition limitations; synthesis on Fmoc-Gly Wang Resin confirmed; NDM-CRE E. coli MIC 1.563-6.250 ug/mL <= 32 ug/mL (positive); CREC6 sub-MIC 3.125 ug/mL |
| 12 | tat2026 | 10.3390/biom16040511 | tat2026.xml | acquired_xml | 4 | 4 peptides excluded; Table 1 explicitly declares C-terminal amidation (-NH2) and intramolecular disulfide bonds for all analogues |

## 3. 详细来源化学与测定分析

### 3.1 chekmenev2006 (Biochim Biophys Acta 1758:1359-1372)
- **论文受测对象**：amidated 和 non-amidated piscidins 1 与 3。
- **序列**：
  - Piscidin 1: `FFHHIFRGIVHVGKTIHRLVTG` (22 aa, MW=2572.10 Da)
  - Piscidin 3: `FIHHIFRGIVHAGRSIGRFLTG` (22 aa, MW=2491.96 Da)
- **受测化学形式**：
  - `p1-NH2` / `p3-NH2`：明确标注 carboxyamidated end，按冻结分子域排除 (`excluded_c_terminal_amidation`)。
  - `p3-COO-`：明确标注 free carboxyl end，Table 1 报告 E. coli ATCC 25922 MIC 为 10–20 µM，换算为 24.92–49.84 µg/mL，落入 32–128 µg/mL 阈值空档，无法推导二值标签，整分子排除 (`excluded_whole_molecule_threshold_gap`)。
  - `p1-COO-`：明确标注 free carboxyl end (`COO-: free carboxyl end`)，Table 1 报告 E. coli ATCC 25922 MIC 为 2–10 µM，换算为 5.14–25.72 µg/mL <= 32.0 µg/mL，推导为阳性标签（`1`）。
- **限制与局限**：Piscidin 1 样品由德州大学西南医学中心（UTSW）提供并经 HPLC 纯化，论文未报告 UTSW 固相合成所用树脂；培养基为 Todd Hewitt Broth；终点采用无扰动生长与最大致死浓度区间定义；MIC 重复数未单独标明。局限如实保留，状态设为 `local_fields_confirmed_not_training_released`，训练释放为 `False`。

### 3.2 foundation2024 (Nat Commun 15:7538)
- **论文受测对象**：Penetratin、18 条 T1-AMP、11 条 T2-AMP 及抗生素对照，共 32 行。
- **合成证据**：方法明确报告使用 CSBio 163 仪器的标准 Fmoc 固相合成，但未声明所用固相树脂（Wang 树脂或 Rink 树脂）及末端封端形式。
- **决定**：只报告“Fmoc 合成”不足以确立游离羧酸末端化学身份，依据 protocol-mic-08 全部 30 条肽暂缓（`withheld_terminal_identity_unestablished`；其中 Penetratin、T1-3、T1-17、T2-11 MIC=62.5 µg/mL 同时处于阈值空档）。抗生素对照排除。

### 3.3 lactoferricin2015 (PMC4359834)
- **合成证据**：方法 2.2 明确报告“Rink amide resin (100 mg) was used as solid support”。
- **决定**：全篇合成肽均为 C 端羧酰胺化形式，依据冻结分子域全部排除（`excluded_c_terminal_amidation`；β-丙氨酸、多聚体和全蛋白对照分别排除）。

### 3.4 boncat2025 (PMC12748266)
- **来源证据**：肽段购自 NovoPro Bioscience 或赠自帕多瓦大学，未声明树脂和末端形式。
- **决定**：4 条肽暂缓（`withheld_terminal_identity_unestablished`），6 条小分子抗生素/溶剂排除。

### 3.5 carrier2016 (PLOS ONE 11:e0146552)
- **受测对象**：重组融合酸裂解产物 (P)GKY20（具额外 N 端 Pro）与商业合成 GKY20（INBIOS s.r.l.）。
- **决定**：商业来源与重组裂解产物均未建立末端游离羧酸证据，暂缓（`withheld_terminal_identity_unestablished`）。

### 3.6 pexiganan2016 (arXiv:1606.00620)
- **受测对象**：Pexiganan (MSI-78)。
- **合成证据**：Section 2.2 明确报告在 Rink amide-MBHA resin 上合成（`GIGKFLKKAKKFGKAFVKILKK-NH2`）。
- **决定**：明确 C 端羧酰胺化，排除（`excluded_c_terminal_amidation`）。

### 3.7 tat2026 (PMC13112966)
- **受测对象**：OSTI-1872、OSTI-2734、OSTI-2886、OSTI-2785。
- **结构与合成**：Table 1 明确报告所有类似物均为 `-NH2` 酰胺化，且含分子内二硫键抑制环。
- **决定**：排除（`excluded_c_terminal_amidation_and_disulfide`）。

### 3.8 bmap2025 (PMC12207908)
- **合成证据**：方法明确报告使用 Fmoc-Gly Wang Resin（王树脂保证 C 端游离羧酸）。RP-HPLC 纯度 > 95%。
- **序列**：`GRFKRLRKKLKKLFKKLSPVIPLLHLG` (27 aa, 标准 L 氨基酸)。
- **测定终点**：正文 Results 明确报告对所有 NDM-CRE 菌株 MIC 在 1.563–6.250 µg/mL（<=32 µg/mL，阳性 1）；选定株 CREC6 sub-MIC 3.125 µg/mL（1x MIC 6.250 µg/mL）。
- **决定与局限**：局部字段确认纳入，受测多重耐药分离株背景及色阶热图区间（标称上界 6.250 µg/mL）如实注明为局限，未释放训练（`local_fields_confirmed_not_training_released`）。

### 3.9 未取得可用正文的四个来源
- `drosocin2002`：仅元数据，正文未取得（`withheld_source_text_unavailable`）。
- `brucin2020`：WHO IMSEAR 下载失败（`withheld_source_text_unavailable`）。
- `apidaecin2009`：Europe PMC fullTextXML 返回 500 错误响应（`withheld_source_text_unavailable`）。
- `neopeptides2005`：Europe PMC fullTextXML 返回 500 错误响应（`withheld_source_text_unavailable`）。

## 4. 全员同源性比对与传递闭包分析

- **比较范围**：17 条唯一分子两两比较，共 136 对。
- **比对参数**：Needleman-Wunsch，match=2，mismatch=-1，gap=-2，优先斜向，分母为比对列总数。
- **新增候选同源边分析**：
  - Piscidin 1 与既有 15 条分子的最高一致性为 **0.2727**（与 Aurein 2.3-COOH），远低于 0.40 阈值，独立形成**新组件 6**。
  - BMAP-27B 与既有 16 条分子的最高一致性为 **0.3333**（与 12PhD1），远低于 0.40 阈值，独立形成**新组件 7**。
  - 两条新候选间一致性仅为 0.1852，组件彼此完全独立。
- **组件统计**：
  - 组件总数：8 个（原 6 个 + 新增 2 个）。
  - 含阳性组件数：5 个（组件 1、组件 3、组件 5、组件 6、组件 7）。
  - 含阴性组件数：6 个（组件 0、组件 1、组件 2、组件 3、组件 4、组件 5）。
  - 最大组件：组件 5（6 条分子，含 2 阳性 4 阴性）。

## 5. 固定三折可行性检查

- **划分参数**：`StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)`。
- **划分结果**：
| 折 | 训练分子数 (阳性/阴性) | 验证分子数 (阳性/阴性) | 验证组件 | 跨折同源边 | 跨折原始研究 | 两类完整性 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 11 (4/7) | 6 (2/4) | 严格整组件 | 0 | 0 | True |
| 1 | 12 (4/8) | 5 (2/3) | 严格整组件 | 0 | 0 | True |
| 2 | 11 (4/7) | 6 (2/4) | 严格整组件 | 0 | 0 | True |

- **跨折同源边**：0 条。
- **跨折原始研究**：0 个。
- **结构门禁**：PASSED。固定三折在数学和生物学上完全可行，各验证折阳性数均为 2，未搜索种子，未删除桥接样本，未调整阈值。

## 6. 门禁与后续阶段约束

1. **新训练释放数**：`0`。protocol-mic-08 仅授权来源扩充审计，未授权任何模型训练。
2. **历史基线不可变**：旧 protocol-mic-07 训练结果、模型（9 个 joblib）、45 条 OOF 预测及 v12 状态作为历史不可变事实严格保留。
3. **原正式状态保持**：`04_paper/research_status.json` 继续处于 `blocked` 门禁阻断状态。
4. **后续推进路径**：若要开展扩充队列训练，必须：
   - 完成 UTSW 树脂或独立来源的原文补充确认；
   - 冻结新的不可变训练协议并由用户显式授权后方可执行。
