# Richter 等 2022 原始测定审计

[原论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC9774241/)；[出版方补充包](https://mdpi-res.com/d_attachment/antibiotics/antibiotics-11-01710/article_deploy/antibiotics-11-01710-s001.zip)。正文 Methods 确认 *E. coli* ATCC 25922 与肉汤微量稀释法；补充 Table S1 给出三次实验的 MIC。

- 冻结清单中关联该论文的 7 条测定，肽序列均在 Table S1，表中 *E. coli* MIC 均为 `>128 µg/mL`，与原始 DBAASP 活动一致。逐条名称、活动 ID、测定引用及原文件哈希见 `record_review.csv`。
- `DBAASP:20336` 同时列有 PMID 35884206 和 36551368；Table S1 已证实该值出现在后者，但保留其双论文出处标识以防跨论文折间泄漏。
- `>128` 表示在最高测试浓度下未见抑制，是右删失结果。论文溶血使用猪红细胞，不能当作人红细胞 HC50。
- 本审计只证明这 7 条原文对应关系；训练释放数为 0。全队列其余测定及既有冲突仍需处理。
