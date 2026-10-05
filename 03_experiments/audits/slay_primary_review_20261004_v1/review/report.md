# SLAY 原始证据审查

生成时间：2026-10-04T13:50:25.688167+00:00。数据版本：`slay_primary_review_20261004_v1`；协议：`protocol-amd-02`（未修改）。模式：代理原文及图像复核，不声称独立人工评审。

## 结论

本批固定 14 条候选全部与[原文 Table 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC5786472/#T2)序列一致；原文 HTML 与官方 BioC 嵌入表逐格一致。存档 28 条 *E. coli* MBC 表述（每分子 W3110 和 NDM 两列），均不转换为 MIC。14 条属于同一测量研究，尚未通过开发集研究别名独立性审计。

[Figure 5C 与人红细胞方法](https://pmc.ncbi.nlm.nih.gov/articles/PMC5786472/#F5)只有名义 50 µM 单点溶血；无数值 HC50。图像已逐项核对肽名，没有读图估算数值或反推 HC50。P3–P18 组低于 20% 的正文陈述不扩展到 P2。图注浓度与方法混合前浓度存在歧义，已保留；不擅自计算并替换。

Table S2 才是数值 MIC 来源。本批公共渠道未取得 S2/S3；PMC PDF 请求返回下载挑战页，Europe PMC PDF 和出版方页面返回 403。仅是这些渠道的访问结果，不代表材料不存在。P2 的定性活性不补写数值；另外 13 条在 Mueller-Hinton 中“无活性、数据未展示”的陈述不改写为数值下界或阴性标签。

完整末端、立体化学、二硫键状态未明确核实；GenScript 和 >90% 纯度不能替代分子身份。许可未确认，仅本地核查，不声明可再分发。

## 本批决定与累计跟进

- 14 条：`current_source_insufficient_for_dual_release`；缺 HC50、数值 MIC 和完整分子身份，均未释放。结论只针对已审查来源。
- 既定 78 条清单累计筛查 34 条；仍有 44 条当前渠道缺原文。
- 累计分类：{"current_source_insufficient_for_dual_release": 14, "pending": 56, "excluded_by_known_molecular_form": 8}。上批已找到的 8 条人 HC50 记录保持原结论，未新增 HC50。
- 正式外部新增 0；原双任务 `blocked`；MIC 探索训练及其状态原样保留，没有训练新模型。

## 产物与后续

逐条决定见 `candidate_decisions.csv`；累计清单见 `merged_candidate_decisions.csv`；分子核对、MBC、MIC缺口及单点溶血分别存表。原文、来源响应与摘要保存在上一层的三个 acquisition 目录。`verification.json` 记录覆盖、逐值检查及保护文件摘要核查。

继续优先审查累计清单中的真实人红细胞剂量曲线和未取得原文的研究。SLAY 的 S2/S3 保留补充获取任务；即使取得 MIC，仍需另有可核实 HC50、完整分子身份、研究与全员同源隔离，不能自动准入。

复跑（替换为不存在的目录）：

```powershell
python 03_experiments/audits/slay_primary_review_20261004_v1/scripts/review_primary.py --output 03_experiments/audits/slay_primary_review_20261004_v1/review_my_run
```
