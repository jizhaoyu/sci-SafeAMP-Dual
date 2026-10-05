# 保留候选证据缺口：SLAY、PLP2与AgNP形式复核

生成时间：2026-10-05T04:00:21.367045+00:00（UTC）。版本`hc50_remaining_evidence_followup_20261005_v1`，协议`protocol-amd-02`。

## 实际进展

已梳理32条未解决记录；其中17条进行本轮来源跟进。原文明确区分AY1C-AgNP/CAY1-AgNP与游离肽，两条银纳米颗粒受测对象据现行未修饰单体规则转为已知形式排除。当前41条范围因此为22条来源不足、8条待复核、11条形式排除，仍有证据问题的记录从32降至30；没有新准入样本。37条缺原文归档决定完全保留，未重新检索。

## 原文及访问结果

- [SLAY原文](https://pmc.ncbi.nlm.nih.gov/articles/PMC5786472/)的两份已观察PMC附件本轮仍为非PDF响应；PII派生出版方mmc6/mmc7地址为404，不能确认附件编号对应关系。S2/S3没有取得，不借失败页填MIC/HC50；该14条既有MBC与单点溶血决定保留。仅结束本轮有限路径尝试，不声称没有其他公开来源。
- [PLP2原文](https://pmc.ncbi.nlm.nih.gov/articles/PMC6356579/)的Table3原始JATS行及表头复核通过：E.coli NBRC14237 MIC <6.2 µM，10 µM溶血栏写Negative，50 µM为10.4%。Negative不解释为测定0，两个固定浓度百分比不生成HC50。Section4.5引用文献6，对应DOI10.1016/j.abb.2004.05.013、PMID15246874；本批核对了元数据，但入口只是跳转页，未取得方法全文，RBC物种仍未知，也不能借其他pilosulin分子的结果。Table2的天然加工形式不自动证明合成受测样品的完整形式。
- [银纳米颗粒论文](https://doi.org/10.1038/s41598-019-41005-7)Results直接定义受测缀合物，Table1使用AY1C-NP/CAY1-NP别名，足以核实两条已知形式排除对象。游离AY1C、CAY1仍保留原决定；不因命名带C而推断环化。原文MIC80及百分比溶血仍不能替代目标MIC/HC50。

## 32条缺口分类

14条SLAY为MBC/单点溶血，5条鲑鱼片段保留端点/身份/培养基问题，2条已知动物RBC，1条HC10与RBC图文物种冲突，4条AY体系端点不符（其中2条本轮形式排除），1条PLP2固定浓度溶血，1条Nc1a范围跨类别/空档，2条黑水虻删失下界不足，1条Dhvar3本来源无目标端点，1条ToAP2图文冲突及真菌MIC。逐条所需证据见`evidence_gap_triage.csv`，不是可训练队列。

## 状态和交付

正式外部新增0，原双任务仍blocked；已完成MIC探索状态v26、训练结果及>=0.40全员隔离保持原样。未拟合模型、发邮件或运行pytest。本轮15条原决定未获放行，两条因实验对象形式排除；其他61条累计记录逐字段不变。

`summary.json`为本轮机器审计状态；`current_scope_records.csv`41条与`merged_candidate_decisions.csv`78条保留来源追溯；`primary_source_checks.csv`绑定原文单元格/定位及摘要。访问时间、失败与响应摘要见上级acquisition。本轮为代理JATS原文复核，未声称独立人工评审；访问失败不证明实验不存在。
