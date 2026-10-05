# 缺失原文候选公开来源跟进

生成时间：2026-10-05T02:51:43.691539+00:00。数据版本：`hc50_missing_originals_20261005_v1`；协议：`protocol-amd-02`。本批代理原文复核，不是独立人工审稿。

## 本批结果

固定44条、28个来源，保存40次公开请求记录；取得并核对3篇原文，新增筛查7条。累计 **41/78** 已筛查，**37条**仍缺原文。已取得来源涉及3个测量/候选来源，不代表3个通过隔离的外部研究。

发现1条真实人RBC HC50范围；新增正式准入 **0**。正式双任务保持 **blocked**；未运行训练、修订协议或生成正式模型结果。此前MIC探索性训练与交付状态保持原样。

## 原文决定

### 鲑鱼肽：5条，同一论文

[作者接受稿](https://air.uniud.it/bitstream/11390/1102192/1/D%27Este%20et%20al%20FSI%202016%20accepted.pdf)，DOI `10.1016/j.fsi.2016.11.004`。Figure 1、Tables 1/2及人RBC方法/结果已视觉复核。4条清单序列匹配；rtCATH2(5-40)清单35残基，原图36残基，少一个S，不修改历史清单、不将测定移给不一致分子。片段编号保留原名，不用编号推算缺失序列。

Table 2的大肠杆菌MIC在稀培养基下有数值；正文同时报告完整MH培养基菌群MIC >64 µM。两种条件均保留；完整MH是菌群陈述、未逐菌株列值，不伪装为独立大肠杆菌单株测量。完整TSB只有未显示数据的无活性陈述，不复制MH的数值。本文人RBC结果为100 µM范围内未见溶血，所引Figure S1未取得。Figure 4A是鱼红细胞，不能补成人HC50；不从文字填精确HC50。分子完整形式未释放。

### Nc1a：1条，HC50是真实范围，标签不能确定

[PMC原文](https://pmc.ncbi.nlm.nih.gov/articles/PMC10167921/)，DOI `10.1016/j.bcp.2021.114693`。Table 1序列一致，正文支持线性且未检测到翻译后修饰；Table 3人RBC HC50为 **28.6–48.2 µM**，Table 2对应E. coli MIC为 **25.8–51.6 µM**。保存原范围，不平均、不只取端点；Table 3跨物种最低MIC及细胞CC50不作为目标标签。

原文单同位素观测质量只作条件换算展示：HC50 **70.8708–119.4396 µg/mL**，跨100阈值；MIC **63.9324–127.8648 µg/mL**，处于32与128之间。单同位素质量不是已确认的正式换算口径，以上均不产生正式标签。论文HTML的菌株号显示为259922，保留其排版歧义。来源别名、分子完整准入和全员隔离均未释放。

### Dhvar3：1条，只有分子身份可核对

[PMC原文](https://pmc.ncbi.nlm.nih.gov/articles/PMC1563894/)，DOI `10.1128/JVI.00796-06`。方法中序列匹配，未找到本任务要求的人RBC HC50和E. coli MIC。其他端点不转为标签。该节FITC标签属于其他分子，不归到Dhvar3。本结论仅限已取得原文，不断言全部文献没有合格测定。

## 访问与许可缺口

其余25个来源/37条仍缺可归档原文。DOI重定向存根、访问检查、403、429、超时、TLS失败及非XML服务页面均单列。追加公开PDF尝试未成功。没有处理访问挑战，也未将错误响应计为原文。原文访问可用不等于允许再分发：作者稿/PMC的版权说明保留，未建立CC许可的来源标为权限待确认。

## 复跑与验收

三份CSV分别保留逐候选决定、逐研究访问结论、原始测定；累计清单固定78条。`sequence_identity_review.csv`包括源图转录与序列冲突。所有正式标签留空，准入为False。`manifest.json`绑定来源响应、前序审计、脚本、转录及视觉产物；核查结果见`verification.json`。

```powershell
python -X utf8 03_experiments/audits/hc50_missing_originals_20261005_v1/scripts/review_sources.py --output 03_experiments/audits/hc50_missing_originals_20261005_v1/review_reproduction_v1
python -X utf8 03_experiments/audits/hc50_missing_originals_20261005_v1/scripts/verify_sources.py --review 03_experiments/audits/hc50_missing_originals_20261005_v1/review_reproduction_v1 --output 03_experiments/audits/hc50_missing_originals_20261005_v1/review_reproduction_v1/verification.json
```

输出目录必须不存在；复跑从已绑定本地来源重建决定，网络获取不是可保证相同的过程。核查覆盖、单元格及摘要不等同独立人工复核。后续优先补鲑鱼稿S1、原始序列冲突和剩余37条原文；找到合格证据后仍需按既有规则执行完整准入与全员隔离。
