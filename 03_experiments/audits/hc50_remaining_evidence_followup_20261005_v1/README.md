# 保留候选证据跟进

生成时间2026-10-05T04:00:01.072102+00:00，版本`hc50_remaining_evidence_followup_20261005_v1`，协议`protocol-amd-02`。

- [报告](review/report.md)
- [32条原始缺口分类](review/evidence_gap_triage.csv)，其中2条本轮按已知形式排除
- [17条本轮原文/来源决定](review/followup_decisions.csv)
- [当前41条范围](review/current_scope_records.csv)，其中11条已按形式排除、30条仍有证据缺口
- [78条历史追溯表](review/merged_candidate_decisions.csv)，归档37条原样保留
- [原表及来源定位核对](review/primary_source_checks.csv)
- [机器状态](review/summary.json)、[摘要清单](review/manifest.json)、[核查结果](review/verification.json)及[复跑比较](reproduction_check.json)

## 本轮结论

原文明确确认AY1C-AgNP、CAY1-AgNP是银纳米颗粒缀合受测对象，违反现行未修饰单体形式要求，2条排除。SLAY的S2/S3仍未取得；PLP2仅有固定浓度溶血百分比，方法种属尚未核实，没有数值HC50释放。正式外部新增0，原双任务仍blocked，既有MIC模型与状态v26不变。未重启已关闭37条检索。

本批6次限定请求全部保存；2个PMC附件非PDF、2个出版方派生附件404、方法元数据成功及DOI跳转页。失败响应不是原文，派生PDF编号没有确认。现有JATS原表核对为代理文本审查，不是独立人工评审。

## 本地复跑

在`D:/桌面文件/sci`执行，输出路径必须不存在：

```powershell
python 03_experiments/audits/hc50_remaining_evidence_followup_20261005_v1/scripts/review.py review --output 03_experiments/audits/hc50_remaining_evidence_followup_20261005_v1/review_my_run
python 03_experiments/audits/hc50_remaining_evidence_followup_20261005_v1/scripts/review.py verify --review 03_experiments/audits/hc50_remaining_evidence_followup_20261005_v1/review_my_run --output 03_experiments/audits/hc50_remaining_evidence_followup_20261005_v1/review_my_run/verification.json
```

核查361份保护文件、11份输入、7份输出，32条分类、17条本轮决定、61条批外不变及37条归档不变；原表/引用/缀合物身份核对通过，五份当前状态块一致且未变。未拟合模型或运行pytest。
