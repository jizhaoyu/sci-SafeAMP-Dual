# 鲑鱼论文S1与分子身份跟进

生成时间：2026-10-05T03:12:27.925152+00:00。数据版本`hc50_salmon_supplement_20261005_v1`，协议`protocol-amd-02`，>=0.40全员边界保持原样。

## 已完成

取得[出版方DOCX补充文件](https://ars.els-cdn.com/content/image/1-s2.0-S1050464816306994-mmc1.docx)，含S1–S3。链接最初按已核对PII构造；下载后以DOCX包、主文交叉引用及三图主题核实，未把猜测链接或HTTP 200本身视为证据。S1获取缺口已解除。

S1是人RBC单点溶血图。既定候选中仅TT(1-24)、TT(1-35)、rtCATH2(5-40)、SF(18-45)在100 µM有柱；图中没有rtCATH2(1-40)。可见实验肽柱低于50%，不读出精确百分比、不拟合或填HC50。图注提及10/100 µM，但图示10 µM仅属于SMAP-29对照，不能给全部候选补写10 µM观测。S2是通透性/菌落计数，S3是吞噬效应，均不替代MIC/HC50。

[2006原始论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC1346769/)的方法序列与2016原图的rtCATH2(5-40)一致：36残基。现行DRAMP和历史清单为35残基；DRAMP自身长度字段为39。已保存一份**未准入的身份更正候选**，没有修改历史数据，也没有把旧分子的标签移给更正分子。2006论文只用于身份交叉核对，不转移该研究测定或把两论文当作已通过隔离的研究。

## 新记录的冲突

|记录|当前数据库与原文核查|处理|
|---|---|---|
|rtCATH2(5-40)|数据库序列35残基/长度字段39；原文36残基|更正提案单独保存，完整形式及测定待准入|
|rtCATH2(1-40)|数据库序列实际40残基/长度字段42；S1未显示此肽|不从其他肽补图或改字段后放行|
|TT(1-24)|原图/数据库可见序列20残基；论文MW 2510.8、数据库质量2181.45|保留质量/身份冲突，不按名称推补残基或换算标签|

DRAMP结构、类别、质量等属于数据库注释，不自动成为原始测量或分子形式证明。2016和2006对36残基肽分别报告MW 3686.1和3687.1，原值及研究身份分别保留，不混成一个正式换算口径。

## 交付与状态

新增复核5条**既有**候选，累计仍41/78、37条缺原文。新增正式外部准入0；正式双任务**blocked**，既有MIC探索性训练和交付未改。HC50数值缺口仍在；补充图可访问不等于所有科学门禁通过。

逐条结论见`candidate_decisions.csv`，累计清单见`merged_candidate_decisions.csv`；原图观察见`single_point_observations.csv`；身份冲突及提案分别见`sequence_identity_review.csv`、`identity_correction_proposal.csv`。不声称独立人工评审。

当前主机没有可用soffice；使用既有PyMuPDF渲染并视觉查看DOCX内全部三张原始TIFF，图注从XML读取。未声称完成DOCX整页排版核查，未更改或重新制作来源文档。原文版权与再分发许可未建立CC授权；原数据库版权声明不扩展到原论文或补充材料。

`manifest.json`保存来源和历史绑定，`verification.json`记录原始文本、包内媒体、覆盖、哈希验收。

```powershell
python -X utf8 03_experiments/audits/hc50_salmon_supplement_20261005_v1/scripts/review.py --output 03_experiments/audits/hc50_salmon_supplement_20261005_v1/review_reproduction_v1
python -X utf8 03_experiments/audits/hc50_salmon_supplement_20261005_v1/scripts/verify.py --review 03_experiments/audits/hc50_salmon_supplement_20261005_v1/review_reproduction_v1 --output 03_experiments/audits/hc50_salmon_supplement_20261005_v1/review_reproduction_v1/verification.json
```

后续需要可核查HC50原值/剂量系列，以及解决TT(1-24)和更正分子的完整实验身份；其余37条公开原文仍需跟进。
