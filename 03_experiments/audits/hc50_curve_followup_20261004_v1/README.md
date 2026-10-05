# 曲线与补充表跟进

本批于2026-10-04开始获取材料，2026-10-05完成代理复核。固定4条候选、3篇原始研究；没有改变协议、训练状态或原双任务门禁。

- 当前报告：`review_20261005_v1/report.md`。
- 当前累计清单：`review_20261005_v1/merged_candidate_decisions.csv`（78条；累计筛查34条，仍44条缺原文）。
- 本批逐条决定、原始测定及冲突：同目录 `candidate_decisions.csv`、`raw_assay_observations.csv`、`conflicts.csv`。
- 条件换算：`conditional_threshold_checks.csv`；正式标签全部留空。该表解释阈值缺口，不是训练准入表。
- 原文图像与获取记录：`acquisition/`。旧XML仍使用上一批冻结来源文件，未复制修改。
- 最终补充表：`publisher_static_content_acquisition_20261005/raw/` 中三份原样DOCX。
- 渲染与视觉复核：`inspection_20261005/`。既有 LibreOffice 直接导出成功，使用既有 PyMuPDF 渲染；没有安装依赖或编辑原始DOCX。技能附带渲染脚本先前失败的辅助目录保留。
- 实际验收：`review_20261005_v1/verification.json`；直接解析原始DOCX的 `word/document.xml`，独立核对测定单元格、删失符号、条件算术与保护摘要。`passed` 只表示此范围的核查通过，不代表科学门禁放行或独立人工审查。

中间获取结果全部保留。PMC DOCX请求返回检查HTML；`springer-cdn.com` 构造地址连接失败；正常的出版方 `static-content.springer.com` 公开附件地址成功。Nature正文的本地HTTP 200响应实际上是Client Challenge，审查记录已标明不可作为原文，未解决或执行访问挑战。

复跑使用不存在的输出位置：

```powershell
python -X utf8 03_experiments/audits/hc50_curve_followup_20261004_v1/scripts/review_evidence.py --output 03_experiments/audits/hc50_curve_followup_20261004_v1/review_my_run
python -X utf8 03_experiments/audits/hc50_curve_followup_20261004_v1/scripts/verify_evidence.py --review 03_experiments/audits/hc50_curve_followup_20261004_v1/review_my_run --output 03_experiments/audits/hc50_curve_followup_20261004_v1/review_my_run/verification.json
```

本批得到两条分子的可追溯人RBC删失端点，仍不能确定协议HC50类别且完整形式待核实，正式外部新增0。CT7明确二硫键形式不合格，ToAP2保留图文冲突。原双任务保持 `blocked`。
