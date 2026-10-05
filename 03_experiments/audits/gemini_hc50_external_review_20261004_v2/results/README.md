# HC50 审计修复 v2

当前结论：blocked；详情与限定范围见 report.md 和 audit_summary.json。生成时间 `2026-10-04T12:43:07.114078+00:00`。

## 复跑

从项目根目录运行，输出必须不存在：

```powershell
python -B 03_experiments/audits/gemini_hc50_external_review_20261004_v2/scripts/evidence_audit.py --input-manifest 03_experiments/audits/gemini_hc50_external_review_20261004_v2/input_manifest.json --input-sha256 e08370d9a391a849aa690470dc7574b13b07130727727daa76d60330b57d0e85 --output 03_experiments/audits/gemini_hc50_external_review_20261004_v2/reproduction_01
python -B 03_experiments/audits/gemini_hc50_external_review_20261004_v2/scripts/test_evidence_audit.py
```

## 产物

逐对象身份、原始观察、派生标签、HC50 已核实池、待核实/排除表、原始研究别名、历史暴露检查、全员比较、冲突、历史搜索声明、原文许可、机器摘要、报告、manifest 均在本目录。0 行准入表保留表头。

不训练模型，不修改原协议，不替代人工审批。原文未报告的条件和无法确认的序列保持缺失。候选线索序列筛查不等于正式独立性验收。
