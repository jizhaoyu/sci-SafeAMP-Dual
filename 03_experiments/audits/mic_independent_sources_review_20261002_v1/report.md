# 独立原始来源补充审计

本轮保存 10 篇有完整正文的原始 XML，逐表原始单元格、来源 URL、许可原文与哈希均单列。未获取的 Tritrpticin 2006 / poly(Arg-His) 2004 原文接口、Dermcidin 原文接口只保留为访问线索，未生成候选。

## 局部证据确认

- [Zhang 2021](https://doi.org/10.3389/fmicb.2021.624465)：G3K5(RW)3、G3(RW)3K5，均为游离酸阴性对照；ATCC 8739 的暗条件 MIC >215.6 µM。图 1 明确自由末端，表 2 与方法已核对；Pc 接枝和 IC50 均排除。
- [Sharma 2013](https://doi.org/10.1371/journal.pone.0075582)：Tritrpticin 的 MIC 3.12 µM，12PhD1 的 MIC 400 µM；各有 BL21λD3、ATCC 25922 两条测定。Figure 3A 与 Table 2 目视核对，合成使用羟甲基苯氧甲基聚苯乙烯酸型树脂和 TFA 裂解；同研究整体分组。免疫原 K-tritrpticin-DT 与径向扩散对照均排除。后续 LB 培养时间/重复数未报告，保持缺失。

以上 4 条分子、6 条 MIC 为局部确认候选；标签按冻结协议的平均分子量规则重推导，不手写类别。这不是完整训练释放，所有记录 training_release=false。

## 明确暂缓项

Equinin 的 MIC90/单位及部分序列冲突；LBP/L7 的方法剂量与表格数值冲突；AamAP1-Lys 的 35 µg/mL 空档测定导致整个酸型分子暂缓；Histatin、Buforin 等受测末端不明。完整决定见 record_decisions.csv，未仅挑选阳性或阴性结果。候选仍需完整证据释放和研究/全员分组门禁，阈值、分子域、折数、seed 均未调整。

## 复跑

`python 02_code/audit_mic_independent_sources.py --output 03_experiments/audits/mic_independent_review_my_run`
输出路径必须不存在；原始文件仅供本地核查，未将所有来源文件的公开访问等同于再发布授权。
