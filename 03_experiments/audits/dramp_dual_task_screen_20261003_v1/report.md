# DRAMP 外部候选队列穿透式审查报告

**审查时间**：2026-10-03T02:22:47.145930+00:00 (UTC)
**比对协议**：`protocol-amd-02` (Global NW, denominator = alignment length, cutoff = 0.4)
**开发集基线**：417 条开发记录 (records.csv)

## 一、核心筛选统计结论

- **DRAMP 原始多肽总数**：4159 条
- **同时包含 E. coli 与溶血活性描述且符合 10-50 aa 标准天然残基的多肽**：1139 条
- **通过全员同源隔离门禁 (< 0.40) 的候选多肽**：**239** 条
- **被全员同源门禁排除 (≥ 0.40) 的候选多肽**：900 条
- **在同源合格候选中的高优先级潜在线性自由酸候选**：**39** 条
- **在同源合格候选中的二硫键/环肽/酰胺化候选**：200 条

## 二、高优先级潜在天然线性多肽列表 (Top Candidates)

### 1. DRAMP21637 - SLAY-P7
- **序列**：`IHRDQQHESFLDARPEPGLTE` (长度: 21)
- **与 417 开发集最大相似度**：`0.2400` (最接近开发记录: `DBAASP:7996`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`0`
- **PMID / 参考文献**：`29307492` | Cell. 2018 Jan 25;172(3):618-628.e13. doi: 10.1016/j.cell.2017.12.009. Epub 2018 Jan 4.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram- | [Ref.29307492] Gram-negative bacteria: E. coli W3110 (MBC = 4 μM), Acinetobac...
- **溶血活性文本**：[Ref.29307492] The peptide showed 0.7% hemolysis against human red blood cells at 50 μM. PBS was uesd as a negative cont...

### 2. DRAMP21647 - SLAY-P17
- **序列**：`EPCSPKNNYHDLFYRT` (长度: 16)
- **与 417 开发集最大相似度**：`0.2500` (最接近开发记录: `DBAASP:4647`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`1`
- **PMID / 参考文献**：`29307492` | Cell. 2018 Jan 25;172(3):618-628.e13. doi: 10.1016/j.cell.2017.12.009. Epub 2018 Jan 4.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram- | [Ref.29307492] Gram-negative bacteria: E. coli W3110 (MBC = 128 μM), Acinetob...
- **溶血活性文本**：[Ref.29307492] The peptide showed 1.7% hemolysis against human red blood cells at 50 μM. PBS was uesd as a negative cont...

### 3. DRAMP20807 - A1P394-428
- **序列**：`PPPVIKFNRPFLMWIVERDTRSILFMGKIVNPKAP` (长度: 35)
- **与 417 开发集最大相似度**：`0.2857` (最接近开发记录: `DBAASP:4957`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`0`
- **PMID / 参考文献**：`27542832` | BMC Microbiol. 2016 Aug 19;16(1):189.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram+, Anti-Gram- | [Ref.27542832] Gram-positive bacteria:Staphylococcus aureus ATCC ...
- **溶血活性文本**：[Ref.27542832] Not hemolytic to sheep red blood cells. | [Ref.27542832] The cell proliferation of A549 human lung epithe...

### 4. DRAMP21643 - SLAY-P13
- **序列**：`YDLSDSNCLPANRDKRYYVI` (长度: 20)
- **与 417 开发集最大相似度**：`0.2857` (最接近开发记录: `DBAASP:24274`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`1`
- **PMID / 参考文献**：`29307492` | Cell. 2018 Jan 25;172(3):618-628.e13. doi: 10.1016/j.cell.2017.12.009. Epub 2018 Jan 4.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram- | [Ref.29307492] Gram-negative bacteria: E. coli W3110 (MBC = 16 μM), Acinetoba...
- **溶血活性文本**：[Ref.29307492] The peptide showed 3.1% hemolysis against human red blood cells at 50 μM. PBS was uesd as a negative cont...

### 5. DRAMP29065 - AMPR-11(derived from Romo1)
- **序列**：`KTMMQSGGTFGTFMAIGMGIR` (长度: 21)
- **与 417 开发集最大相似度**：`0.2917` (最接近开发记录: `DBAASP:16470`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`0`
- **PMID / 参考文献**：`32291307` | mBio. 2020 Apr 14;11(2):e03258-19. doi: 10.1128/mBio.03258-19.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram-, Anti-Gram+ | [Ref.33291307] Gram-positive bacteria: S. aureus(MBC=100 μg/mL), ...
- **溶血活性文本**：[Ref.33291307]At the concentration of 32 μg/mL, AMPR-11 induced a hemolysis of 20% on mouse red blood cells; At the conc...

### 6. DRAMP21638 - SLAY-P8
- **序列**：`TIDFGVRNINQSNLVYDTER` (长度: 20)
- **与 417 开发集最大相似度**：`0.3000` (最接近开发记录: `DBAASP:144`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`0`
- **PMID / 参考文献**：`29307492` | Cell. 2018 Jan 25;172(3):618-628.e13. doi: 10.1016/j.cell.2017.12.009. Epub 2018 Jan 4.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram- | [Ref.29307492] Gram-negative bacteria: E. coli W3110 (MBC = 8 μM), Acinetobac...
- **溶血活性文本**：[Ref.29307492] The peptide showed 10.8% hemolysis against human red blood cells at 50 μM. PBS was uesd as a negative con...

### 7. DRAMP21640 - SLAY-P10
- **序列**：`TRDTNDLISSRTAAPSMV` (长度: 18)
- **与 417 开发集最大相似度**：`0.3000` (最接近开发记录: `DBAASP:4029`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`0`
- **PMID / 参考文献**：`29307492` | Cell. 2018 Jan 25;172(3):618-628.e13. doi: 10.1016/j.cell.2017.12.009. Epub 2018 Jan 4.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram- | [Ref.29307492] Gram-negative bacteria: E. coli W3110 (MBC = 16 μM), Acinetoba...
- **溶血活性文本**：[Ref.29307492] The peptide showed 8.4% hemolysis against human red blood cells at 50 μM. PBS was uesd as a negative cont...

### 8. DRAMP21646 - SLAY-P16
- **序列**：`SDDAQRCYPHNRTPFTYTYI` (长度: 20)
- **与 417 开发集最大相似度**：`0.3000` (最接近开发记录: `DBAASP:18063`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`1`
- **PMID / 参考文献**：`29307492` | Cell. 2018 Jan 25;172(3):618-628.e13. doi: 10.1016/j.cell.2017.12.009. Epub 2018 Jan 4.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram- | [Ref.29307492] Gram-negative bacteria: E. coli W3110 (MBC = 32 μM), Acinetoba...
- **溶血活性文本**：[Ref.29307492] The peptide showed 3.3% hemolysis against human red blood cells at 50 μM. PBS was uesd as a negative cont...

### 9. DRAMP20860 - TT(1-35)
- **序列**：`KFRTRRSKSSSNGGRKGSKGGSKGRPGSGSSIAGA` (长度: 35)
- **与 417 开发集最大相似度**：`0.3143` (最接近开发记录: `DBAASP:20378`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`0`
- **PMID / 参考文献**：`27818338` | Fish Shellfish Immunol. 2016 Dec;59:456-468.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram+, Anti-Gram- | [Ref.27818338]Gram-negative bacteria:Escherichia coli (ATCC 25922...
- **溶血活性文本**：[Ref.27818338] No hemolytic activity to human;No hemolytic activity to trout | [Ref.27818338] The cell viability of RTG-...

### 10. DRAMP21634 - SLAY-P4
- **序列**：`SNGDGTLDAGSTCAPFYARA` (长度: 20)
- **与 417 开发集最大相似度**：`0.3143` (最接近开发记录: `DBAASP:4129`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`1`
- **PMID / 参考文献**：`29307492` | Cell. 2018 Jan 25;172(3):618-628.e13. doi: 10.1016/j.cell.2017.12.009. Epub 2018 Jan 4.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram- | [Ref.29307492] Gram-negative bacteria: E. coli W3110 (MBC = 2 μM), Acinetobac...
- **溶血活性文本**：[Ref.29307492] The peptide showed 1.8% hemolysis against human red blood cells at 50 μM. PBS was uesd as a negative cont...

### 11. DRAMP21639 - SLAY-P9
- **序列**：`PCNPDHDYRPFGNFRIAFTT` (长度: 20)
- **与 417 开发集最大相似度**：`0.3182` (最接近开发记录: `DBAASP:24870`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`1`
- **PMID / 参考文献**：`29307492` | Cell. 2018 Jan 25;172(3):618-628.e13. doi: 10.1016/j.cell.2017.12.009. Epub 2018 Jan 4.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram- | [Ref.29307492] Gram-negative bacteria: E. coli W3110 (MBC = 8 μM), Acinetobac...
- **溶血活性文本**：[Ref.29307492] The peptide showed 0% hemolysis against human red blood cells at 50 μM. PBS was uesd as a negative contro...

### 12. DRAMP21636 - SLAY-P6
- **序列**：`LSVDKRPVLHPEHIYGHNHY` (长度: 20)
- **与 417 开发集最大相似度**：`0.3200` (最接近开发记录: `DBAASP:774`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`0`
- **PMID / 参考文献**：`29307492` | Cell. 2018 Jan 25;172(3):618-628.e13. doi: 10.1016/j.cell.2017.12.009. Epub 2018 Jan 4.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram- | [Ref.29307492] Gram-negative bacteria: E. coli W3110 (MBC = 4 μM), Acinetobac...
- **溶血活性文本**：[Ref.29307492] The peptide showed 3.1% hemolysis against human red blood cells at 50 μM. PBS was uesd as a negative cont...

### 13. DRAMP21641 - SLAY-P11
- **序列**：`LPLPSCSSHGGDADNTSQRN` (长度: 20)
- **与 417 开发集最大相似度**：`0.3200` (最接近开发记录: `DBAASP:20378`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`1`
- **PMID / 参考文献**：`29307492` | Cell. 2018 Jan 25;172(3):618-628.e13. doi: 10.1016/j.cell.2017.12.009. Epub 2018 Jan 4.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram- | [Ref.29307492] Gram-negative bacteria: E. coli W3110 (MBC = 16 μM), Acinetoba...
- **溶血活性文本**：[Ref.29307492] The peptide showed 2.6% hemolysis against human red blood cells at 50 μM. PBS was uesd as a negative cont...

### 14. DRAMP29144 - Pxt‐6
- **序列**：`IRPVPFFPPVHAKKVFPLH` (长度: 19)
- **与 417 开发集最大相似度**：`0.3226` (最接近开发记录: `DBAASP:24027`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`0`
- **PMID / 参考文献**：`25312021` | FEBS J. 2015 Jan;282(1):102-13.
- **E. coli 活性文本**：Antimicrobial, Antibacterial,Anti-Gram+, Anti-Gram- | [Ref.25312021]Gram-negative bacteria:Escherichia coli DH5α(Not act...
- **溶血活性文本**：[Ref.25312021]0.3% Hemolysis against Rat erythrocytes at 20 µM. | [Ref.25312021]No cytotoxicity information found. | Fun...

### 15. DRAMP20968 - Catesbeianin-1 (Ranidae, Anura, Amphibia, Animals)
- **序列**：`MMRVMRRKTKVIWEKKDFIGLYSID` (长度: 25)
- **与 417 开发集最大相似度**：`0.3333` (最接近开发记录: `DBAASP:25512`)
- **端点与拓扑**：N端=`Free`，C端=`Free`，拓扑=`Linear`，Cys数=`0`
- **PMID / 参考文献**：`28258530` | Biotechnol Lett. 2017 Jun;39(6):897-903. doi: 10.1007/s10529-017-2312-7.
- **E. coli 活性文本**：Antimicrobial, Antibacterial, Anti-Gram+, Anti-Gram- | [Ref.28258530] Gram-positive bacteria : Staphylococcus aureus ATC...
- **溶血活性文本**：[Ref.28258530] 0% hemolysis at 0 μg/ml , hemolysis 3% at 25 μg/ml , 7% hemolysis at 50 μg/ml , 8% hemolysis at 100 μg/ml...
