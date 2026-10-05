# 五条鲑鱼候选：HC50与正式图核查

本批仅跟进既有五条；数据版本`hc50_salmon_endpoint_closure_20261005_v1`，协议`protocol-amd-02`。报告时间2026-10-05T03:31:45.973158+00:00。正式外部新增0，双任务blocked，MIC探索状态不变。

- [报告](review/report.md)
- [逐候选决定](review/candidate_decisions.csv)及[累计78条](review/merged_candidate_decisions.csv)
- [质量与序列诊断](review/mass_and_sequence_diagnostics.csv)
- [原始研究端点筛查](review/primary_endpoint_screen.csv)
- [查询覆盖](review/search_coverage.csv)及[逐命中审查](review/search_hit_review.csv)
- [机器状态](review/summary.json)、[来源及输出摘要](review/manifest.json)
- [核查结果](review/verification.json)及[复跑比较](reproduction_check.json)

出版方正式图与作者稿一致，未解除TT(1-24)20残基及质量冲突。两篇新增原文为鱼RBC及不同分子；两篇引用来源仍缺全文。检索0命中和元数据没有勘误条目均不能证明不存在实验或勘误。既有36残基身份更正提案仍未准入。

## 本地复跑

在`D:/桌面文件/sci`执行；所有输出路径必须不存在：

```powershell
python 03_experiments/audits/hc50_salmon_endpoint_closure_20261005_v1/scripts/review.py --output 03_experiments/audits/hc50_salmon_endpoint_closure_20261005_v1/review_my_run
python 03_experiments/audits/hc50_salmon_endpoint_closure_20261005_v1/scripts/verify.py --review 03_experiments/audits/hc50_salmon_endpoint_closure_20261005_v1/review_my_run --output 03_experiments/audits/hc50_salmon_endpoint_closure_20261005_v1/review_my_run/verification.json
```

核查通过：292份历史/工程保护文件、27份输入、9份审计输出，五条条件质量算术、两篇原文目标、8条查询及5条无关命中拒绝。其他73条决定保持原样。复跑7份内容输出字节一致，summary及report仅生成时间不同。

审查为代理原文/图像复核，程序核对摘要和转录一致性，不是独立人工评审；未进行新训练或运行pytest。理论质量仅用于检查来源内部一致性，未用于标签或单位转换。原始来源获取时间及失败请求保留在`acquisition/source_acquisition.json`与`focused_search/source_acquisition.json`，不从失败响应提取证据。
