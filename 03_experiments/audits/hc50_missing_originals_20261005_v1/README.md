# HC50缺失原文公开来源跟进

本批固定上一检查点的44条候选、28个研究来源。所有原始响应和生成目录保留，不覆盖历史产物。正式协议为`protocol-amd-02`；原双任务继续`blocked`，没有新增训练或正式外部准入。

## 实际交付

- [审查报告](review/report.md)：3篇原文、7条新增筛查、1条真实人HC50范围、1条序列冲突；累计41/78已筛查，37条仍缺原文。
- [逐条决定](review/candidate_decisions.csv)、[累计78条清单](review/merged_candidate_decisions.csv)、[28个来源](review/source_review.csv)。
- [17条原始观察](review/raw_assay_observations.csv)、[分子身份](review/sequence_identity_review.csv)。数值MIC、定性溶血陈述与菌群MIC陈述分别标注，不产生正式标签。
- [获取记录](acquisition/source_acquisition.json)、[追加获取](additional_acquisition/source_acquisition.json)、[响应复核](review/response_review.json)。重定向、访问检查、403/429、非原文服务响应等未计为原文。
- [原值、覆盖、摘要核查](review/verification.json)：通过，180份保护文件、45份输入、9份产物摘要均匹配。
- [复跑比较](reproduction_check.json)：7份内容产物摘要一致；汇总仅生成时间/输出版本不同；复跑结果位于`review_reproduction_v1/`，也通过同一原值核查。
- [逐步实施记录](../../../docs/superpowers/plans/2026-10-05-hc50-missing-originals.md)。

## 可复跑入口

使用当前Python环境和已归档来源，不安装依赖。选择新的输出目录，已存在时拒绝覆盖：

```powershell
python -X utf8 03_experiments/audits/hc50_missing_originals_20261005_v1/scripts/review_sources.py --output 03_experiments/audits/hc50_missing_originals_20261005_v1/review_reproduction_v2
python -X utf8 03_experiments/audits/hc50_missing_originals_20261005_v1/scripts/verify_sources.py --review 03_experiments/audits/hc50_missing_originals_20261005_v1/review_reproduction_v2 --output 03_experiments/audits/hc50_missing_originals_20261005_v1/review_reproduction_v2/verification.json
```

`primary_review_notes.json`保存代理视觉转录；脚本仅复现已声明复核，不自动充当原文人工评审。公开网络抓取结果可能变化，获取脚本不允许重写已保存目录。来源版权/许可说明逐项保留，没有将公开阅读权限视为再分发许可。

## 剩余工作

优先补充鲑鱼稿Figure S1、独立核实rtCATH2(5-40)序列冲突，以及剩余37条对应的25个来源原文。Nc1a原始HC50区间跨既定类别界限，不以平均值或挑选端点解除门禁。任何后续合格记录仍须完成分子、测定、来源别名和全员跨队列隔离审计。
