# 鲑鱼论文补充材料及序列冲突跟进

协议`protocol-amd-02`和全员>=0.40门禁未改。跟进5条已初筛候选，新增准入0；原双任务仍`blocked`，既有MIC训练产物不变。

## 进度与交付

- [x] 绑定上一检查点，保留历史数据与审计。
- [x] 保存13次公开获取记录；补充链接的构造依据与内容验证分开记录。
- [x] 取得并核对出版方S1–S3；查看三张原始内嵌图，确认S1实验肽/对照/浓度范围。
- [x] 用2006原始论文交叉核对36残基序列，单独保存未释放更正提案。
- [x] 核对五条官方DRAMP注释，记录长度与质量冲突。
- [x] 生成累计78条清单并核查原始包内媒体、来源字段及历史摘要。
- [x] 本地复跑；6份内容产物摘要一致，汇总仅生成时间不同。

关键材料：

- [完整报告](review/report.md)、[机器汇总](review/summary.json)。
- [五条决定](review/candidate_decisions.csv)、[累计清单](review/merged_candidate_decisions.csv)。
- [身份冲突](review/sequence_identity_review.csv)、[未准入的身份更正提案](review/identity_correction_proposal.csv)。
- [四条单点观察](review/single_point_observations.csv)、[原图和视觉复核说明](review/visual_review.json)。
- [获取记录](acquisition/source_acquisition.json)、[出版方DOCX原文件](acquisition/raw/derived_mmc1.docx)。
- [核查结果](review/verification.json)：249份历史保护文件、20份输入、8份输出摘要匹配；3张渲染图像与源媒体像素一致。
- [复跑比较](reproduction_check.json)。

S1获取缺口已解除，数值HC50缺口仍在。单点图不拟合或补标签；未展示分子不补写图值。数据库注释不转换为原始实测或独立来源。身份更正须另行完整准入与隔离审计，不能直接放进训练集或外部验证队列。

## 复跑

以下入口消费已归档来源与图像，输出位置必须不存在：

```powershell
python -X utf8 03_experiments/audits/hc50_salmon_supplement_20261005_v1/scripts/review.py --output 03_experiments/audits/hc50_salmon_supplement_20261005_v1/review_reproduction_v2
python -X utf8 03_experiments/audits/hc50_salmon_supplement_20261005_v1/scripts/verify.py --review 03_experiments/audits/hc50_salmon_supplement_20261005_v1/review_reproduction_v2 --output 03_experiments/audits/hc50_salmon_supplement_20261005_v1/review_reproduction_v2/verification.json
```

当前主机soffice不可用，因此只渲染并查看DOCX内嵌三图，图注由原XML读取，未完成DOCX整页排版核查。不声称独立人工审稿。论文/补充文件公开可读不自动构成再分发许可；抓取网络状态不保证可重复。
