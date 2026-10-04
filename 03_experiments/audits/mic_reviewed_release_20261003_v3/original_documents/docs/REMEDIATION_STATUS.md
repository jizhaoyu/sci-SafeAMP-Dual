# SafeAMP-Dual 当前整改状态

<!-- RESEARCH_STATUS_CURRENT_START -->
## 当前研究状态（机器生成）

状态来源：`03_experiments/audits/mic_training_readiness_20261003_v16.json`。
生成时间：2026-10-03 11:44:05（Asia/Shanghai）。审查数据版本：`mic_evidence_repair_20261003_v1`；目录：`03_experiments/audits/mic_evidence_repair_20261003_v1`。
当前状态：`historical_training_completed_evidence_review_blocked`。来源审查协议：`protocol-mic-08`；当前可执行训练协议：`null`；训练命令：`null`。

| 状态轴 | 当前结论 |
|---|---|
| 工程实现 | 已实现；证据门禁已修复为缺失即拒绝 |
| 扩充队列证据 | `blocked`；17 条历史候选、24 条观察；新增候选完整释放为 0 |
| 历史探索训练 | 手工 9 个模型/51 条 OOF，ESM2 对比 27 个模型/153 条 OOF；产物可复现，17 条准入声明已撤回 |
| 新训练 | `blocked`；扩充队列释放为 0，不提供训练命令 |
| 外部候选 | 39 条保留为线索；完整原测定资格批准为 0 |
| 原双任务正式研究 | `blocked`；`protocol-amd-02`；正式运行 `none` |
| 正式结果 / 投稿就绪 | `false` / `false` |

旧 15 条基线的完整证据和训练结果保留（protocol-mic-07，15 分子/22 观察）。v12–v15 及下方旧时点结论为历史记录；17 条队列的旧放行/已确证声明不能用于当前研究准入。
历史训练协议：`protocol-mic-09` / `protocol-mic-10`；历史数据：`mic_source_expansion_result_20261002_v2`。
历史运行：`03_experiments/runs/mic_three_fold_20261002_v2`、`03_experiments/runs/mic_three_fold_esm2_20261002_v1`。
本次仅整改证据与软件门禁，未重新训练。下一步补齐逐分子/逐测定原始证据，再冻结新的训练协议。
<!-- RESEARCH_STATUS_CURRENT_END -->

## 历史记录（旧准入声明已由上述审查状态替代）

**状态日期**：正式双任务 2026-10-01，MIC-only 更新至 2026-10-02（精确时间见各机器状态的 `generated_at`）  
**机器状态来源**：正式双任务 `04_paper/research_status.json`；MIC-only 最新状态为 `03_experiments/audits/mic_training_readiness_20261002_v15.json`（2026-10-02 21:43:53，Asia/Shanghai）；前序手工基线为 `03_experiments/audits/mic_training_readiness_20261002_v14.json`（2026-10-02 21:17:33，Asia/Shanghai）；历史不可变基线为 `03_experiments/audits/mic_training_readiness_20261002_v12.json`（2026-10-02 18:51:38，Asia/Shanghai）。  
**数据版本**：`02_code/data/sources/combined_v3_evidence_clean_20261001`  
**协议**：`protocol-amd-02`，摘要 `6bcf8993a08f8da1ebae4609f4ef9e4ebae7205257d136dfa059a1b93db4bc4c`。
MIC-only 历史表征探索版本基于 `mic_source_expansion_result_20261002_v2`；训练协议为 `protocol-mic-10`。历史记录 **local_exploratory_esm2_training_completed**：17 条分子完成手工（44 维）、ESM-2（320 维）及 Hybrid（364 维）三种表征空间的三折训练，运行目录 `03_experiments/runs/mic_three_fold_esm2_20261002_v1` 保存 27 个模型与 153 条 OOF 预测。RF 在 ESM-2 嵌入下实现 0 假阳性（FP=0，特异性 100%），MCC 为 0.494413，平衡准确率 0.666667；LR 在 ESM-2 下成功识别 4 条阳性（TP=4）。前序手工基线版本（协议 `protocol-mic-08` / `protocol-mic-09`，状态 **local_exploratory_three_fold_training_completed**，运行目录 `03_experiments/runs/mic_three_fold_20261002_v2`）及既有 15 分子基线（协议 `protocol-mic-06` / `protocol-mic-07`，运行目录 `03_experiments/runs/mic_three_fold_20261002_v1`）作为不可变历史事实完整保留。

| 状态轴 | 当前值 | 依据 |
| --- | --- | --- |
| 工程实施 | 已完成核心管线 | Phase D 软件交付日志；本次新增严格协议和证据清理 |
| 数据准备 | `blocked` | `03_experiments/prepared/amd02_evidence_clean_20261001/manifest.json`：缺独立外部队列 |
| 实验运行 | `none` | 无通过门禁的正式运行 |
| 正式结果 | `false` | 无完成并通过产物校验的运行 |
| 投稿审批 | `false` | 尚无正式结果和人工审核回执 |
| MIC-only 候选分区 | `passed` | 相同 15 条分子、105 对；固定三折各训练/验证均有两类，跨折同源及原始研究均为 0 |
| MIC-only 证据释放 | `passed` | 15 条分子/22 条冻结 MIC 逐条原文复核；七个研究及引用方法绑定摘要，未补写缺失条件 |
| MIC-only 探索训练 | `completed` | protocol-mic-07；LR/RF/prior 固定三折，九个模型和 45 条 OOF 预测已保存 |
| MIC-only 产物复核 | `passed` | 九个模型重新加载；12 行指标、105 对和 15×44 特征独立复算；验证期间禁止 fit |
| MIC-only 扩充审查 | `passed` | protocol-mic-08；12 篇研究、81 条记录审查，纳入 2 条游离酸候选（Piscidin 1 与 BMAP-27B，阳性 2，注明局限）、36 条暂缓、43 条排除 |
| MIC-only 扩充三折结构 | `passed (audit-only)` | 17 条分子、24 条测定、136 对；8 个组件（含阳性 5、含阴性 6），固定 seed 42 三折可行且各折严格 2 阳性 |
| MIC-only 扩充基线训练 | `completed` | protocol-mic-09；17 条分子完成 LR/RF/prior 固定三折训练，九个模型和 51 条 OOF 预测已保存 |
| MIC-only 扩充产物复核 | `passed` | 九个模型重新加载；12 行指标、136 对和 17×44 特征独立复算；验证期间禁止 fit |
| MIC-only ESM-2 探索训练 | `completed` | protocol-mic-10；手工/ESM-2/Hybrid 三空间，27 个折模型和 153 条 OOF 预测已保存 |
| MIC-only ESM-2 产物复核 | `passed` | 27 个模型重新加载；27 行指标、153 条 OOF 独立复算；RF在ESM-2下FP=0 (MCC=0.494)；验证期间禁止 fit |

## 已核实的数据与隔离情况

- 旧 `combined_v2` 中的 13 条外部记录缺少可重推导的原始实验测定；新候选源逐条排除并在 `exclusions.json` 留下原因。417 条 DBAASP 开发记录通过本地原始文件和标签重推导校验。
- 新协议使用固定全局比对的“相同残基列数 ÷ 全部比对列数”，并将所有达到 0.40 的样本对归入同一连通分量。417 条开发记录形成 89 个簇，最大簇 318 条。该结果不等于可行的五折评估。
- 本地 DRAMP 的 10 条候选与 417 条开发记录全部 4,170 对均按新口径重算；10 条候选各至少有一对达到阈值。筛查产物见 `03_experiments/audits/dramp_amd02_20261001`。
- 外部队列目前为 0，正式训练继续由门禁阻断。历史代表序列聚类的“61 个独立簇”和“门禁已放行”属于过时探索结论，不能用于当前正式状态。
- 独立的 MIC-only 探索线历史记录为[本地探索训练完成 v12](../03_experiments/audits/mic_training_readiness_20261002_v12.json)：[三折前瞻性修订](amendments/PROTOCOL_MIC_06_THREE_FOLD.md)、[完整原文释放复核](../03_experiments/audits/mic_three_fold_primary_release_20261002_v1/report.md)及冻结 protocol-mic-07 已执行。旧 324 条序列队列的 458 条测定仍仅局部核对且有原始 MIC 冲突；旧[就绪声明 v1](../03_experiments/audits/mic_training_readiness_20261001_v1.json)已撤回，`protocol-mic-05` 入口仍拒绝该队列。此次完成仅适用于当前 15 条分子的本地探索。
- [原论文逐测定核对 v3](../03_experiments/audits/mic_primary_review_20261001_v3/manifest.json)（2026-10-01 13:15 UTC）已检查 PMID 42206144 的 10 条数据库记录：10 条序列均与原文补充表一致。原论文 30 个 *E. coli* 靶标对应完整数据库快照的 31 条测定，其中 30 条数值一致、1 条冲突；旧二值清单只保留其中 21 条。`DBAASP:25512`／AIC222 的原始活动 ID 202714 为 `16 µM`（CRE，与原表一致），ID 202721 为 `>64 µM`（VRE，与原表冲突）；不猜测后者真正的目标菌株。[逐原始测定表](../03_experiments/audits/mic_primary_review_20261001_v3/raw_activity_review.csv)与[其余论文优先队列](../03_experiments/audits/mic_primary_review_20261001_v3/paper_queue.csv)保留出处和哈希；该局部审计时点释放为 0，这些冲突记录未纳入当前训练。
- [Ross 等 2020 原论文审计 v2](../03_experiments/audits/mic_primary_review_pmid33281785_20261002_v2/manifest.json)（2026-10-02 01:51 UTC）把 PMID 33281785 的 8 条冻结记录分别对应到 Figure 1 的序列与 Table 1 的 *E. coli* BL21 MIC；8 条均与数据库原始活动值一致。[逐记录审计表](../03_experiments/audits/mic_primary_review_pmid33281785_20261002_v2/record_review.csv)保留活动 ID 和原文件哈希。Figure 1 图片序列仍需独立复核；论文用绵羊血测溶血，不能充作人红细胞 HC50。其余论文及前一篇的冲突未解决，因此该历史时点两条训练线阻断、释放为 0；这些 Ross 候选仍未进入当前 15 条释放队列。
- [Richter 等 2022](../03_experiments/audits/mic_primary_review_pmid36551368_20261002_v2/report.md)、[Nagarajan 等 2018](../03_experiments/audits/mic_primary_review_pmid29259134_20261002_v2/report.md)和[Okimura 等 2021](../03_experiments/audits/mic_primary_review_pmid33790103_20261002_v2/report.md)分别核对 7、3、3 条冻结测定。Nagarajan 的图片表格仍待独立复核；所有局部核对训练释放数均为 0。
- [Pandi 等 2023](../03_experiments/audits/mic_primary_review_pmid37938588_20261002_v2/report.md)两条记录因 C 端酰胺化与冻结分子形式不符而排除；[Guan 等 2025](../03_experiments/audits/mic_primary_review_pmid40645962_20261002_v2/report.md)只有 4 条 MIC 数值与原始 Source Data 精确对应，8 条 `80` 编码未推断为 `>64 µM`。[此前候选隔离审计 v1](../03_experiments/audits/mic_reviewed_subset_groups_20261002_v1/report.md)对 37 条唯一序列的全部 666 对进行核查，得到 7 个同源加论文组件、4 个含阴性；该历史候选版本已由下述 v2 扩展。
- [Wang 等 2025](../03_experiments/audits/mic_primary_review_pmid39908380_20261002_v2/report.md)两条原始补充表阴性候选与数据库数值相符，但补充表 `>400 µM` 和正文方法的最高 `200 µM` 不一致；原始菌株 GD004 也未在冻结目标字段体现。两条暂不计入上面的 37 条候选，训练释放数为 0。
- [Hirsch 等 2020 EtCec3-OH 原文审计](../03_experiments/audits/mic_primary_review_pmid32344933_20261002_v2/report.md)核实游离羧酸端及两个菌株的 `>1024 µg/mL` MIC。它与旧 324 条队列有 1 条同源边，不能作为原双任务独立外部样本。此前[候选结构 v2](../03_experiments/audits/mic_reviewed_subset_groups_20261002_v2/report.md)的 38 条分子仍有一折缺阳性；该历史版本现由下述 v3 扩展。
- [Ludwig 等 2022 原文审计](../03_experiments/audits/mic_primary_review_pmid35735615_20261002_v1/report.md)保留 Api801、Api805、Api810，排除 Api802 空档和 Api806 冲突；共享论文与同源成员整体连接。[历史结构审计 v3](../03_experiments/audits/mic_reviewed_subset_groups_20261002_v3/report.md)的 41 条分子、54 条测定、820 对曾通过五折结构，但候选未释放；该通过结果不能迁移到当前队列。
- [历史完整证据审查队列](../03_experiments/audits/mic_candidate_release_review_20261002_v1/report.md)将缺口落实到全部 41 条分子：7 条当时已局部确认游离酸端；34 条仍待确认身份、图片转录或补充测定依据。数据库“none”和商业合成概述不能补作原始化学证据。该历史审查时点释放为 0；随后原文释放复核入选的 15 条已完成当前探索训练。
- [此前游离酸证据筛选](../03_experiments/audits/mic_confirmed_acid_subset_20261002_v1/report.md)保留原队列 7 条局部确认分子，补充 Aurein 2.3-COOH、MSI-103-COOH、PGLa-COOH、MAP-COOH 的 7 条原始 MIC；该 11 条分子队列是本轮扩展的冻结输入。Tiltak 学位论文与其 2007 原研究整体合并，未虚增独立来源。
- [本轮 10 篇原始来源审计](../03_experiments/audits/mic_independent_sources_review_20261002_v1/report.md)保存 70 项纳入/暂缓/排除决定，新增 Zhang 2021 两个未接枝阴性对照，以及 Sharma 2013 的 Tritrpticin / 12PhD1，共 4 条分子、6 条 MIC。原始结构、序列图及 MIC 表已目视核对，缺失的后续培养时间和重复数保持缺失。Equinin 的 MIC90/单位冲突、LBP/L7 浓度冲突、AamAP1-Lys 35 µg/mL 空档和 Histatin/Buforin 末端不明均未放行。
- [前版五折全员分组](../03_experiments/audits/mic_extended_acid_cohort_20261002_v1/report.md)：15 条分子、22 条测定、105 对完整比较，6 个同源/研究组件，含阳性 3、含阴性 6。阳性不足旧五折，未生成分折，跨折结果为 `null`。[当前三折分区](../03_experiments/audits/mic_three_fold_20261002_v1/report.md)沿用全部样本及科学规则，各验证折阳性/阴性为 2/4、1/4、1/3，对应训练为 2/7、3/7、3/8；跨折同源及原始研究均为 0，结构门禁 passed。分区审计时的未释放快照原样保留；v11 记录随后释放的历史就绪时点，历史 v12 记录真实训练完成。
- 新 latarcin 来源的 COOH 描述与 Rink amide 合成方法冲突，4 条未入选。已取得 PLP2 补充材料，但天然质谱不能证明受测合成分子身份；Richter 的 PeNi12 虽明确非酰胺端，半胱氨酸成键状态仍待核实。原 34 条暂缓原因见[逐条筛选表](../03_experiments/audits/mic_confirmed_acid_subset_20261002_v1/prior_candidate_decisions.csv)。
- [Bhaumik 等 2024 额外来源审计](../03_experiments/audits/mic_primary_review_pmid39367191_20261002_v1/report.md)的 6 条阳性证据候选未合入当前队列。Buforin II 删失标记不同，来源 CC BY-NC-ND 4.0 再利用范围待审。[Cateslytin 2021 复核](../03_experiments/audits/mic_cateslytin_source_review_20261002_v1.md)的两条 L 型肽缺明确末端形式，未转用 D 型肽值，均未入选。
- [新来源扩充审查与三折可行性审计](../03_experiments/audits/mic_source_expansion_result_20261002_v2/report.md)（protocol-mic-08）：审查 12 篇公开原始文献、81 条记录；纳入 2 条局部确认分子（Chekmenev 等 2006 的 Piscidin 1 游离羧酸端，E. coli ATCC 25922 MIC 2–10 µM 即 5.14–25.72 µg/mL，阳性 1，明确记录 UTSW 树脂未报告及 Todd Hewitt 培养基局限；bmap2025 的 BMAP-27B 游离羧酸端，Fmoc-Gly Wang 树脂固相合成，NDM-CRE E. coli 临床株 MIC 1.563–6.250 µg/mL，阳性 1，注明多重耐药株及色阶热图区间局限）、暂缓 36 条（因未声明载体树脂、末端形式不详，或正文未取得等）、排除 43 条（Rink amide 酰胺化、空档、二硫键/非标残基或抗生素对照）。与既有 15 条合并为 17 条候选分子（6 阳性、11 阴性）、24 条测定；136 对全员比较，11 条同源边，8 个不可拆分组件（含阳性 5、含阴性 6，最大组件 6 条）；在固定 seed 42 下固定三折结构门禁通过（各验证折阳性数严格平衡，均为 2 条；跨折同源边及原始研究均为 0）。
- [扩充队列（17 分子）本地探索训练完成 v14](../03_experiments/audits/mic_training_readiness_20261002_v14.json)：依据用户授权实施决策点 A，冻结 [protocol-mic-09 协议](amendments/PROTOCOL_MIC_09_EXPANDED_TRAINING.md) 与三折拓扑独立复核；17 条分子、24 条测定完成固定三折基线拟合（运行目录 `03_experiments/runs/mic_three_fold_20261002_v2`）。[产物复核报告](../03_experiments/audits/mic_three_fold_run_validation_20261002_v5.md)重新加载九个模型并独立重算 51 条 OOF 预测与全部指标。RF 的历史预测识别出 4 条阳性（包括 Piscidin 1 游离酸），MCC 为 0.203091，平衡准确率 0.606061；样本量极小，不作为广泛泛化或临床效用证据。旧 15 条基线（v12）和原双任务正式阻断状态保持原样。
- [扩充队列（17 分子）ESM-2 预训练表征探索完成 v15](../03_experiments/audits/mic_training_readiness_20261002_v15.json)：依据用户授权选项 2，冻结 [protocol-mic-10 协议](amendments/PROTOCOL_MIC_10_ESM2_REPRESENTATION.md)；在 17 分子固定三折拓扑下完成手工（44 维）、ESM-2（320 维）及 Hybrid（364 维）三种表征空间的拟合（运行目录 `03_experiments/runs/mic_three_fold_esm2_20261002_v1`）。[产物复核报告](../03_experiments/audits/mic_esm2_run_validation_20261002_v2.md)重新加载 27 个模型并独立重算 153 条 OOF 预测与全部指标。RF 在 ESM-2 嵌入下实现 0 假阳性（FP=0，特异性 100%），MCC 达到 0.494413，平衡准确率 0.666667；LR 在 ESM-2 下成功识别 4 条阳性（TP=4）。高维小样本过拟合风险明确披露，原双任务正式门禁严格保持 blocked。
- 2026-10-01 本地全量软件测试：`182 passed`。测试通过不解除数据与科研门禁。

## 下一步

先审阅[ESM-2 表征探索产物复核报告](../03_experiments/audits/mic_esm2_run_validation_20261002_v2.md)、[扩充训练产物复核报告](../03_experiments/audits/mic_three_fold_run_validation_20261002_v5.md)、[阶段性综合学术技术纪要](MIC_COHORT_EXPANSION_AND_TOPOLOGY_REPORT_20261002.md)及[来源扩充审计报告](../03_experiments/audits/mic_source_expansion_result_20261002_v2/report.md)。17 条分子三折基线已完成固定训练，LR/RF/prior 模型及 51 条 OOF 预测（v14）与 153 条表征对比预测（v15，运行目录 `03_experiments/runs/mic_three_fold_esm2_20261002_v1`）如实保留。各验证折严格平衡包含 2 条阳性。原 15 条基线（`mic_three_fold_20261002_v1`，产物复核 `mic_three_fold_run_validation_20261002_v4.md`）作为历史不可变事实保留。原双任务正式门禁仍 blocked。
