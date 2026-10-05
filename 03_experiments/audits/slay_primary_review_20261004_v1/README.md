# SLAY 公开原文核查

范围：PMID 29307492 对应的既定 14 条候选；DOI `10.1016/j.cell.2017.12.009`。不改变 `protocol-amd-02` 或训练状态。

- 报告：`review/report.md`。
- 逐条决定与累计 78 条清单：`review/candidate_decisions.csv`、`review/merged_candidate_decisions.csv`。
- 表格：`review/sequence_identity_review.csv`、`review/mbc_observations.csv`、`review/mic_endpoint_gaps.csv`、`review/single_point_hemolysis_review.csv`。
- 实际验收：`review/verification.json`；覆盖、逐值、摘要检查通过，不是独立人工评审。
- 原始来源：`acquisition/raw/pmc_article.html`、`acquisition/raw/bioc_article.xml`、`figure_acquisition/raw/figure_5.jpg`。PDF 请求取得的挑战 HTML 明确以 `.response.html` 保存，不能作为 PDF 原文。
- 补充表：S2/S3 尚未取得，继续待获取。公开替代渠道失败存档于 `alternate_acquisition/source_acquisition.json`。

图像首次清单误包含自身空文件摘要。原文件保留，`figure_acquisition/manifest_v2.json` 删除该自引用并绑定原清单真实摘要；图像及获取记录未改变。验证器核查修订清单和原清单，不将旧清单作为正确证据绑定。

复跑仅生成新审查目录；已有目录拒绝覆盖。网络获取脚本使用固定路径，已存在时拒绝写入，不自动替换来源。

```powershell
python -X utf8 03_experiments/audits/slay_primary_review_20261004_v1/scripts/review_primary.py --output 03_experiments/audits/slay_primary_review_20261004_v1/review_my_run
python -X utf8 03_experiments/audits/slay_primary_review_20261004_v1/scripts/verify_review.py --review 03_experiments/audits/slay_primary_review_20261004_v1/review_my_run --output 03_experiments/audits/slay_primary_review_20261004_v1/review_my_run/verification.json
```

许可未核实，仅本地证据核查，不声明可再分发。脚本使用当前环境已有的 BeautifulSoup，未安装新依赖。没有模型拟合、实验操作或正式数据释放。
