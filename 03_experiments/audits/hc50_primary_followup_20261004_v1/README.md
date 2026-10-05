# HC50 原文来源跟进

当前报告：[review_v2/report.md](review_v2/report.md)；机器汇总：[review_v2/summary.json](review_v2/summary.json)；实际核对结果：[verification.json](verification.json)。

固定 78 条候选；41 个 PMID 元数据全部获取，12 篇 XML 和 1 篇作者机构 PDF 归档。20 条完成代理原文端点筛查，58 条仍缺本批可审查全文。8 条明确人 HC50 测定保存在 `original_human_hc50_observations.csv`，均因已知环化、二硫键或酰胺化不满足当前正式分子边界；其余 70 条 pending。正式外部释放 0，原双任务仍 blocked。已有 MIC 探索性训练状态未改变。

## 文件用途

- `acquisition/`：只记录来源获取、原文件摘要、许可、获取时间和请求失败。
- `additional_metadata/`：额外元数据/访问请求；Crossref 返回 429，PMC 返回 challenge，出版者原文件响应尚需识别，均不当作全文成功。
- `metadata_review_notes.json`：通过原出版者网页核对 Brevinin-2-Ia 的 DOI；Catesbeianin-1 摘要 HC50 线索。没有正式标签。
- `inspection/`：实际查看过的 ECP 表格页；版本绑定图像和原 PDF 摘要。
- `review_v2/`：全部逐记录决定、原始测定观察、访问缺口、来源片段和报告。
- `review/`：保留初次生成记录，CT7 方法位置曾写为 3.5；当前 `review_v2` 已更正为原文 section 3.3。两版未覆盖，旧脚本与绑定保持原样。
- `verification.json`：78 条覆盖、8 条 HC50 记录、6 个数值表格单元复算、历史与新产物摘要检查；不是独立人工评审或全项目测试结论。

## 复跑

在仓库根目录执行，输出路径必须不存在：

```powershell
python -B 03_experiments/audits/hc50_primary_followup_20261004_v1/scripts/review_sources_v2.py --output <新输出目录>
```

本批已执行的独立核对命令：

```powershell
python -B 03_experiments/audits/hc50_primary_followup_20261004_v1/scripts/verify_review.py --review 03_experiments/audits/hc50_primary_followup_20261004_v1/review_v2 --manifest-sha256 a9532b01b58682421330abb4b4e7e41c9aae4b5cc1d2726bcbcc0e4e720968e1 --output <新的核对记录路径>
```

来源获取入口执行过一次，拒绝覆盖归档。本批不包含训练标签释放、模型拟合、外部消息发送或投稿资格判断。作者机构 PDF 未确认开放再分发许可，不能据此加入交付包。后续先补齐原文/补充表，再完整核对分子身份与测定，最后重新审计全员同源、来源别名及历史暴露。
