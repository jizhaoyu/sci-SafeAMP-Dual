# MIC 原始论文逐测定核对：PMID 42206144

生成时间：2026-10-01T13:15:43.312246+00:00；状态：`blocked_primary_review_in_progress`。

原论文：[DOI 10.1038/s42256-026-01237-5](https://www.nature.com/articles/s42256-026-01237-5)；序列来自补充 PDF 的表 1、表 2；MIC 来自补充 Data 1 CSV，单位 µmol/L，菌株定义与微量肉汤稀释法见原论文 Methods。

10 条数据库记录的序列均与原文相符；30 个论文靶标对应 31 条原始数据库测定，其中 30 条 MIC 与原表一致、1 条冲突。当前二值训练清单保留 21 条测定；另 10 条未进入二值清单。

冲突：`DBAASP:25512` / Hydrodamin-3-6 / E. coli AIC222：原始数据库有 `16 µM` （活动 ID 202714，备注 CRE）及 `>64 µM`（活动 ID 202721，备注 VRE）两条，原论文补充 CSV 仅有 `16 µM`。后者进入了旧二值清单；不猜测 VRE 条目本应属于哪个菌株，也不直接修补旧数据。

本次未核实末端化学形式及所有实验条件是否逐记录一致，不能据此释放训练。完整逐靶标、逐原始活动和逐记录结果见 `paper_assays.csv`、`raw_activity_review.csv` 与 `record_review.csv`；其余论文按 `paper_queue.csv` 继续。
