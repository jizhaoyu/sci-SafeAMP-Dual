# 多数据库 *E. coli* MIC 数据筛查

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

**生成时间：** 2026-10-01 08:56 UTC  
**最近增补：** 2026-10-01 13:15 UTC；具体生成时间以各版本 manifest 为准  
**筛查范围：** DRAMP 3.0、dbAMP 3.0 公开下载数据及一篇原始 MIC 数据论文；与正式开发集 417 条记录比较  
**序列协议：** 候选对开发集预筛用 `protocol-amd-02`，SHA-256 `6bcf8993a08f8da1ebae4609f4ef9e4ebae7205257d136dfa059a1b93db4bc4c`；MIC-only 当前三折队列门禁用 `protocol-mic-06`，旧五折 `protocol-mic-01` 保留原样  
**当前状态：** 原双任务正式研究仍 `blocked`。MIC-only 的[历史机器声明 v15](mic_training_readiness_20261002_v15.json)（2026-10-02 21:43:53，Asia/Shanghai）为 **local_exploratory_esm2_training_completed**：依据训练协议 `protocol-mic-10`，在 17 分子固定三折拓扑下完成手工（44 维）、ESM-2（320 维）及 Hybrid（364 维）三种空间的拟合，运行目录 `03_experiments/runs/mic_three_fold_esm2_20261002_v1` 保存 27 个模型与 153 条 OOF 预测，产物复核见 `mic_esm2_run_validation_20261002_v2.md`。RF 在 ESM-2 下达到 0 假阳性（FP=0），MCC 为 0.494413，平衡准确率 0.666667；LR 在 ESM-2 下识别出 4 条阳性（TP=4）。前序手工基线[机器声明 v14](mic_training_readiness_20261002_v14.json)（2026-10-02 21:17:33，Asia/Shanghai，状态 **local_exploratory_three_fold_training_completed**，数据版本 `mic_source_expansion_result_20261002_v2`，审计协议 `protocol-mic-08`，训练协议 `protocol-mic-09`，运行 `03_experiments/runs/mic_three_fold_20261002_v2` 保存九个模型和 51 条 OOF 预测，各验证折严格平衡包含 2 条阳性，[产物复核](mic_three_fold_run_validation_20261002_v5.md)）及既有 15 分子基线（[机器状态 v12](mic_training_readiness_20261002_v12.json)，2026-10-02 18:51:38，协议 `protocol-mic-06` / `protocol-mic-07`，运行目录 `03_experiments/runs/mic_three_fold_20261002_v1`，[原文释放复核](mic_three_fold_primary_release_20261002_v1/report.md)）作为历史不可变事实完整保留。原 34 条暂缓及冲突继续追溯；旧 `protocol-mic-05` 仍拒绝旧 324 条队列。样本量仍小，高维过拟合风险明确披露，结果仅适用于本地方法学探索。

## 历史：MIC-only 数据审计与训练阻断（2026-10-01）

[证据筛选来源 v1](mic_training_source_20261001_v1/manifest.json)保留 320 条 DBAASP 二值 MIC 记录，剔除 71 条目标菌株或分离株未解决记录与 26 条无二值 MIC 标签记录；每条保留记录仍引用原始文件和哈希。加入 DRAMP v8 的 4 条阳性记录后，[队列审计 v9](mic_only_cohort_20261001_v9/report.md)得到 324 条唯一序列（217 阳性、107 阴性），52,326 对全员比对、84 个同源组件，证据、菌株标识、类别和 0.40 跨折隔离门禁通过。v8 曾因输入来源计数写成 0 而废止；v9 修复计数后在新目录重建，旧目录保持原样。

历史不可变[`protocol-mic-study-03`](../protocols/protocol-mic-study-03.json)要求同论文与同源序列整体分折。[旧审计 v5](mic_study_disjoint_20261001_v5/report.md)将 84 个同源组件合并为 60 个组件；五折均有正负类，跨折超阈值相似边及共享原始 MIC 论文均为 0。[`protocol-mic-05`](../protocols/protocol-mic-05.json)固定原有 44 维手工特征及基线参数，但不能代替原始论文证据。训练入口仍拒绝旧队列；[历史就绪声明 v11](mic_training_readiness_20261002_v11.json)记录当前 15 条三折队列证据和协议通过的训练前时点，当前真实训练完成由顶部 v12 提供。

最大合并组件为 249/324（76.9%），验证折为 19、18、249、19、19；最大折对应的训练集只有 75 条，评估稳定性不足。[目标标识审计 v9](mic_only_cohort_20261001_v9/target_identifier_audit.csv)的 458 条测定均为 `identified_provisionally`：审计报告中的“0 条待原文核对”只表示算法未发现未编号的目标，不表示 458 条均已逐篇核对原论文。数据库原始测定快照和引用可追溯，但不足以满足该冻结协议对原始测定对象的证据要求。必须逐条核对原文中的序列、MIC 值、单位、菌株或分离株及引用，排除无法核实项；随后用新版本重新审计类别、同源和论文隔离，并冻结新训练协议。在此之前不启动新训练，正式双任务队列、模型结果和投稿状态不变。

### 原论文复核进展：PMID 42206144

[原始研究](https://www.nature.com/articles/s42256-026-01237-5)公开了[序列补充表](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs42256-026-01237-5/MediaObjects/42256_2026_1237_MOESM1_ESM.pdf)和[逐肽、逐菌株 MIC CSV](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs42256-026-01237-5/MediaObjects/42256_2026_1237_MOESM3_ESM.csv)。[审计 v3](mic_primary_review_20261001_v3/report.md)把该论文关联的 10 条数据库记录逐一对照原表：序列全部匹配，原论文 30 个 *E. coli* 靶标对应完整数据库快照的 31 条测定，其中 30 条数值一致、1 条冲突。旧二值清单只保留 21 条，另 10 条原始测定未提供二值标签。`DBAASP:25512`（Hydrodamin-3-6）对 AIC222 同时记录 `16 µM`（活动 ID 202714，备注 CRE，与原表一致）和 `>64 µM`（活动 ID 202721，备注 VRE，与原表冲突）。[逐原始测定表](mic_primary_review_20261001_v3/raw_activity_review.csv)、原文件哈希和 458 条测定的[后续论文队列](mic_primary_review_20261001_v3/paper_queue.csv)均已保存；队列有 227 个研究标识键，其中 19 条测定只保留 DBAASP 文章编号，未找到 PMID／DOI，须优先补齐出处。末端化学形式等尚待核实，入训记录仍为 0；旧数据不直接修补。

[Ross 等 2020 原文](https://www.frontiersin.org/journals/microbiology/articles/10.3389/fmicb.2020.589666/full)的 Figure 1 和 Table 1 可分别核对序列及 *E. coli* BL21 MIC。[第二篇审计 v2](mic_primary_review_pmid33281785_20261002_v2/report.md)将冻结清单中 8 条记录逐一对应，8 条序列和 MIC 均与原文一致，原始活动 ID、原文件及哈希见[逐记录表](mic_primary_review_pmid33281785_20261002_v2/record_review.csv)。Figure 1 为图片，转录尚待第二人复核。该论文溶血实验使用绵羊血，不能作为人红细胞 HC50 证据。此审计没有解除先前冲突、释放训练记录或更改任何冻结阈值。

[Richter 等 2022 原文](https://pmc.ncbi.nlm.nih.gov/articles/PMC9774241/)的[出版方补充 Table S1](https://mdpi-res.com/d_attachment/antibiotics/antibiotics-11-01710/article_deploy/antibiotics-11-01710-s001.zip)现已取得。[第三篇逐记录审计 v2](mic_primary_review_pmid36551368_20261002_v2/report.md)从原表复核 7 条冻结测定的序列、*E. coli* ATCC 25922 MIC、单位及数据库原始活动，均为 `>128 µg/mL`。其中 `DBAASP:20336` 同时关联 PMID 35884206 与 36551368；此数值出现在后者的 Table S1，但仍保留两个论文标识参与隔离审计。该文的溶血对象为猪红细胞，不符合正式双任务的人红细胞端点。该篇局部核对未释放训练记录，也未消除全队列阻断。

[Nagarajan 等 2018](mic_primary_review_pmid29259134_20261002_v2/report.md)的 Table 1 核对 3 条冻结测定（1 阳性、2 阴性）；[Okimura 等 2021](mic_primary_review_pmid33790103_20261002_v2/report.md)的 Table 1/4 核对 3 条游离羧酸端阴性测定。图片表格转录仍需独立复核，局部匹配均不等于训练放行。[Pandi 等 2023](mic_primary_review_pmid37938588_20261002_v2/report.md)的 2 条记录存在 C 端酰胺化身份冲突，已从新候选中排除；[Guan 等 2025](mic_primary_review_pmid40645962_20261002_v2/report.md)仅有 4 条原始 Source Data 数值精确对应，8 个 `80` 编码不按 `>64` 猜测。

[Wang 等 2025](mic_primary_review_pmid39908380_20261002_v2/report.md)新增 2 条潜在阴性：Table S18 的序列与 Table S5 的 *E. coli* GD004 `>400 µM` 与冻结数据库数值对应，但正文 MIC 方法仅描述至 `200 µM`，且数据库目标未写 GD004。两条未解决前不得加入下述分组或训练。

[Hirsch 等 2020 原文核查](mic_primary_review_pmid32344933_20261002_v2/report.md)新增 EtCec3-OH：原论文支持游离羧酸端及两个菌株的 `>1024 µg/mL` MIC。它与旧 324 条队列的一条相似性达 0.465，不能作为原双任务独立外部记录。此前[结构审计 v2](mic_reviewed_subset_groups_20261002_v2/report.md)的 38 条分子仍有一折缺阳性；该历史结果由下述 v3 扩展。

[Ludwig 等 2022 原文核查](mic_primary_review_pmid35735615_20261002_v1/report.md)完整审查五条合成游离酸端肽的八条 MIC。保留 Api801、Api805 和 Api810 的四条候选测定；Api802 含 64 µg/mL 空档、Api806 两种培养基的二值标签相反，均排除整条分子。共享原始论文和同源关系整体连接，未把 Api810 计为新的独立阴性组。

[历史结构审计 v3](mic_reviewed_subset_groups_20261002_v3/report.md)有 41 条未释放候选、54 条测定、820 对；当时固定五折通过，但[逐分子证据队列](mic_candidate_release_review_20261002_v1/report.md)有 34 条身份或补充证据待核实。该通过结果由下述筛选后的实际分区阻断结论替代，旧文件保持追溯。

### 原始化学证据筛选后的当前结论（2026-10-02）

[此前游离酸筛选及分组](mic_confirmed_acid_subset_20261002_v1/report.md)保留原队列 7 条局部确认分子，另从 Cheng 2011 原始论文和 Tiltak 2009 原始学位论文补充 4 条明确游离酸对照、7 条 MIC。学位论文与其 2007 论文属于同一研究，整体绑定。该冻结前版的 11 条分子（3 阳性、8 阴性）、16 条测定的全部 55 对产生 11 条同源边；与研究标识一起合并为 4 个组件，其中含阳性 2 个、含阴性 4 个。该前版现作为下述新队列输入。

[此前新来源审计](mic_independent_sources_review_20261002_v1/report.md)补充 Zhang 的两个阴性对照及 Sharma 的 Tritrpticin / 12PhD1，共 4 条分子、6 条 MIC；单位/端点冲突等 66 项没有进入局部候选。[前版五折分组](mic_extended_acid_cohort_20261002_v1/report.md)有 15 条分子（4 阳性、11 阴性）、22 条测定；105 对、11 条同源边，6 个研究/同源组件，含阳性 3、含阴性 6。旧五折至少缺 2 个含阳性组件，未生成分折、跨折为 `null`。随后用户授权的三折协议 06 与完整原文复核通过，冻结训练协议 07；当前训练完成以顶部 v12 为准，不迁移旧五折结论。

原 34 条暂缓项的新复核原因已保存在[逐条筛选表](mic_confirmed_acid_subset_20261002_v1/prior_candidate_decisions.csv)。PLP2 补充材料虽已取得，但天然质谱不能转借为受测合成分子证据。Richter 的 PeNi12 明确非酰胺端，半胱氨酸成键状态仍待核实。新 latarcin 原文将 COOH 与 Rink amide 合成方法同时记载，4 条暂缓；[Cateslytin 2021 复核](mic_cateslytin_source_review_20261002_v1.md)的两条 L 型肽末端形式未明确，且不能转用 D 型肽值。均未加入当前 15 条候选，训练释放数为 0。

[Bhaumik 等 2024 额外来源](mic_primary_review_pmid39367191_20261002_v1/report.md)明确区分 17 条肽的酸端和酰胺端，补充 PDF 第 16 页已渲染复核：6 条游离酸端阳性证据候选；8 条酰胺端和 2 条空档排除。Buforin II 在两表分别记 `>250` 和 `250 µg/mL`，虽均落阴性侧，原始删失标记仍待澄清。来源许可为 CC BY-NC-ND 4.0，项目再利用范围尚待审查。6 条候选与 41 条逐成员比较 246 对，有 3 条达到 0.40 的边，均连到现有一个组件；共享论文整体分组。该来源未合入当前 41 条队列，未获训练放行，后续合并仍需完整重算。

### 公开原始文献扩充审查与三折可行性审计（protocol-mic-08，2026-10-02）

依据 `protocol-mic-08`，[扩充审计报告](mic_source_expansion_result_20261002_v2/report.md)审查了 12 篇公开原始文献、共 81 条肽行与对照记录：
- **纳入 2 条局部确认分子**：Chekmenev 等 2006 的 `p1-COO-`（Piscidin 1，游离羧酸，E. coli ATCC 25922 MIC 2–10 µM 即 5.14–25.72 µg/mL，阳性 1，明确记录 UTSW 树脂未报告及 Todd Hewitt 培养基局限，`training_release=False`）；`bmap2025` 的 BMAP-27B（游离羧酸，Fmoc-Gly Wang 树脂固相合成，NDM-CRE E. coli 临床株 MIC 1.563–6.250 µg/mL，阳性 1，明确记录多重耐药株及色阶热图区间局限，`training_release=False`）；
- **暂缓 36 条**：`foundation2024` 30 条未声明固相树脂、`boncat2025` 4 条赠送/商业肽未注末端、`carrier2016` 2 条重组裂解/商业肽未注、4 篇未取得正文等；
- **排除 43 条**：`lactoferricin2015` 24 条因 Rink amide 树脂酰胺化及非标残基排除、`tat2026` 4 条因 C 端酰胺化及二硫键排除、`pexiganan2016` 1 条因 Rink 酰胺化排除、`chekmenev2006` 2 条酰胺化排除及 1 条 `p3-COO-` 因空档排除、8 条抗生素/溶剂对照排除。
- **候选与分组拓扑**：与既有 15 条分子合并后得到 17 条候选分子（6 阳性、11 阴性）、24 条测定；136 对全员比较，11 条同源边，8 个不可拆分组件（含阳性 5、含阴性 6，最大组件 6 条）；
- **训练释放与基线训练**：依据决策点 A，`protocol-mic-09` 授权释放该 17 条分子用于本地探索基线训练；运行 `03_experiments/runs/mic_three_fold_20261002_v2`，保存 9 个模型及 51 条 OOF 预测。产物复核通过（[复核报告](mic_three_fold_run_validation_20261002_v5.md)），最新完成状态见顶部 v14。旧 15 条小样本三折训练（v12）保持原样，原正式双任务保持阻断。

## 历史：2026-10-01 证据门禁纠错与未解决记录

[历史 MIC-only v7 manifest](mic_only_cohort_20261001_v7/manifest.json)由 417 条开发记录与 DRAMP v8 的 4 条候选重建，协议仍为 `protocol-mic-01`，SHA-256 `d54227ebb5380039cd07f6ddc979561ef6f99efaecdb7644267e6c7d00dffb97`。逐条[菌株标识审计](mic_only_cohort_20261001_v7/target_identifier_audit.csv)把无菌株编号、仅有血清型／耐药表型，或只有未编号的“clinical isolate”的测定列为待核验。来源备注中出现单一编号分离株的 5 条测定被暂列 `identified_provisionally`，仍需与原始论文核对，不能将备注视作已完成原文复核。v6 曾因未读取备注而多计这 5 条；v6 保留为纠错轨迹。

按[旧研究映射的逐测定表](mic_study_disjoint_20261001_v4/assay_observations.csv)与 v7 未解决清单的记录 ID、测定序号交叉，优先核查：

| 原始研究 | 关联未解决测定 | 当前可核实内容 | 下一步 |
|---|---:|---|---|
| [Loose 等，Nature 2006，PMID 17051220](https://pubmed.ncbi.nlm.nih.gov/17051220/) | 22 | [原始论文正文](https://communications.embl-community.io/science-society-archive/discussion/discussion_2006/ref315Nov06.pdf)报告 *E. coli* MIC，并将详细测定方法及逐肽数据指向补充材料；正文没有给出 *E. coli* 菌株编号 | 获取原始补充材料，逐条匹配序列、MIC、单位和菌株；不能从引用的方法论文推定菌株 |
| [Trp/Arg 肽设计研究，PMID 35694289](https://pmc.ncbi.nlm.nih.gov/articles/PMC9186412/) | 4 | 正文说明研究涉及临床菌株，个别菌株的 MIC 列于补充表 | 核对这 4 条数据库测定是否可与补充表的具名菌株、肽序列和数值一一对应 |

其余未解决项继续按[完整清单](mic_only_cohort_20261001_v7/target_identifier_audit.csv)逐篇核查；原文未能定位到具体受测对象时排除相应测定，不靠数据库类别或猜测补齐。这些记录已从新的探索性训练来源中排除；若未来补回，须重新冻结输入并重做五折审计。

另找到一个值得单独筛查的[原始实验数据描述论文](https://doi.org/10.3390/data4010027)：同一实验室对 20 条肽进行统一 MIC 测定，正文给出全部序列，*E. coli* 对象为 K-12 MG1655，补充表 S1 是逐肽、逐菌株的 CSV；论文明确说明空白 MIC 单元格代表 `>128 µg/mL`，并采用 CC BY 4.0 许可。按正文表 1 序列对 417 条开发记录及当前 4 条 DRAMP 候选完成[8,420 对全员序列预筛](uniform_mic_2019_sequence_prescreen_20261001_v2/manifest.json)：20 条中 5 条与这 421 条记录的最高一致性均低于 0.40，分别为 NN2_0001、NN2_0002、NN2_0005、NN2_0008、NN2_0046；[逐条结果](uniform_mic_2019_sequence_prescreen_20261001_v2/sequence_prescreen.csv)保留最近邻和比较次数。这只是**序列预筛**，尚未核对补充 CSV、肽修饰、同论文重叠及这 5 条彼此的同源关系，不生成标签，也不纳入任何队列。该论文中的部分肽曾见于作者更早的研究，审计时须把两篇研究的测定来源分别追溯，避免把重复发表的数据当成独立验证。[论文正文 PDF](https://mdpi-res.com/data/data-04-00027/article_deploy/data-04-00027.pdf?attachment=1&filename=)

## 纳入规则

只把数据库作为候选发现入口。记录必须从原始实验论文核对具体受测分子、末端及成键状态、*E. coli* 菌株、MIC 实测值和单位；不能用数据库预测、标签或“none”字段代替实验依据。域内未修饰分子按既定分子量归一化规则及 `<=32`（阳性）、`>=128`（阴性）推导标签，中间值保持未知。原双任务外部候选须与 417 条开发集成员逐条比较；MIC-only 须对当期全部候选成员比较并合并同一原始研究。均使用全局 Needleman–Wunsch `matches/aligned_columns`、0.40 阈值。

## 历史初筛：DRAMP 3.0

DRAMP 官方下载页当前将活动分类 Excel 标为 DRAMP 3.0；帮助页说明目标生物记录包含引用、目标对象和对应 MIC 字段。[DRAMP 官方下载页](https://cpu-bioinfor.org/downloads/)；[字段说明](https://cpu-bioinfor.org/static/help.php)

下载的抗菌活动表有 4,159 行，其中 2,333 行提及 *E. coli*。按 10–50 个标准氨基酸、明确线性且未注明末端或其他修饰筛选后，有 94 条记录和 152 条 *E. coli* MIC 文本观测。逐条与开发集比较时，76 条候选记录至少有一个超过 0.40 的相似度；13 条序列与开发集完全重复；27 条记录引用开发集中已出现的论文。剩余 18 条低于序列相似度阈值，其中 1 条与开发集共享论文。

在这 18 条中，三条 Chassalia uncyclotide 记录可直接回链至同一篇原始论文。原文报告测试菌株为 *E. coli* ATCC 25922，使用 radial diffusion assay；方法中注明细菌培养于 trypticase soy broth，结果表报告 ChaC7、ChaC8、ChaC11 的 MIC 分别为 6.4、6.6、8.5 µM。[原始论文全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC3366795/)

| DRAMP ID | 肽 | MIC（原始单位） | 项目归一化（µg/mL） | 标签 | 对开发集最高相似度 |
|---|---|---:|---:|---:|---:|
| DRAMP00336 | ChaC7 | 6.4 µM | 18.967 | 阳性 | 0.2857 |
| DRAMP00337 | ChaC8 | 6.6 µM | 20.412 | 阳性 | 0.3103 |
| DRAMP00338 | ChaC11 | 8.5 µM | 25.642 | 阳性 | 0.2857 |

当时 `validate_records`/`validate_source_evidence` 对这三条记录重算标签并通过，未发现与开发集精确序列、0.40 同源或 PMID 重叠；三条两两相似度为 0.7586–0.8000。但该初筛没有完成受测分子的半胱氨酸成键审查，不能据此宣称训练证据已通过。三条目前均暂缓，不在当前 15 条队列中；表内初步阳性数值不能替代分子身份门禁。

DRAMP21455（PLP2）在初筛中匹配到原文表 2 的 33 aa 序列及表 3 合成 PLP2 对 *E. coli* NBRC 14237 的 MIC `<6.2 µM`。论文引用 PMID 15246874 的测定方法，但本文未列培养基和接种量，未自行补值。初筛按所录序列计算 MIC 上界 20.856 µg/mL；然而天然分子的序列及质谱不足以证明受测合成肽的精确异构体和末端形式。补充材料已取得，身份仍待核实，暂缓纳入。对旧开发集最高一致性 0.3939 也不能替代身份审核。[PLP2 原始论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC6356579/)；[其引用的测定方法论文](https://pubmed.ncbi.nlm.nih.gov/15246874/)

这 4 条在初筛中被暂标为阳性，并形成两个同源组；均无 HC50 数据。后续分子身份审核尚未完成，当前均暂缓，不能计作已入选的独立阳性组件。

### Cn-AMP2 阴性线索：证据门禁未通过（2026-10-01 复核）

DRAMP00930（Cn-AMP2，序列 `TESYFVFSVGM`）在[原始论文全文](https://www.researchgate.net/publication/23708261_Identification_and_structural_insights_of_three_novel_antimicrobial_peptides_isolated_from_green_coconut_water)表 2 与纯化的 F2 肽序列一致；表 1 报告 *E. coli* MIC 为 170 µg/mL，方法 2.3 为生长抑制区测定，表注说明使用营养培养基平板。菌株编号和培养基详细配方未报告。若只按数值阈值，`>=128 µg/mL` 会推导为阴性；但冻结的 `protocol-mic-01` 同时要求明确菌株或分离株，因此目前不得纳入候选队列。它与 417 条开发集成员的最高全局一致性为 0.3636，原始论文 PMID 19111587 不与开发集重叠；这些隔离结果不能替代缺失的实验对象证据。[论文 DOI](https://doi.org/10.1016/j.peptides.2008.12.001)

论文表 2 对 Cn-AMP2 列出的计算质量为 1266 Da、观测质量为 1249 Da；论文将类似差异讨论为测序质谱过程中的失水，但目前不能单靠该说明确认受测分子的完整化学形式。菌株身份和受测分子形式均须核实，不能因序列相似度合格而放行。

不可覆盖的[初筛候选表 v8](dramp_verified_ecoli_mic_20261001_v8/records.csv)、[待核验表](dramp_verified_ecoli_mic_20261001_v8/pending_primary_review.csv)、[相似度审计](dramp_verified_ecoli_mic_20261001_v8/similarity_audit.csv)和[来源清单](dramp_verified_ecoli_mic_20261001_v8/manifest.json)保存当时 4 条初步阳性、2 个同源组件的结果，不代表当前入选或训练释放。此前[v7 五条版本](dramp_verified_ecoli_mic_20261001_v7/manifest.json)也仅供历史追溯。

阴性线索继续保守处理：DRAMP01195 只记录 `>126 µg/mL`，这一不等式不足以保证达到项目 `>=128 µg/mL` 阴性阈值；DRAMP00089 的数据库条目给出 39 aa、计算质量 4125.71 Da，而其[原论文摘要](https://pubmed.ncbi.nlm.nih.gov/18293921/)描述纯化肽质量 3339.7 Da。两条均未进入 v8，须先核对原文受测分子与测定表。[DRAMP00089 条目](https://dramp.cpu-bioinfor.org/browse/All_Information.php?dataset=General&id=DRAMP00089)

### 其他候选的原文复核

- DRAMP20804（AI-hemocidin 2）：原文确认 14 aa 序列和 *E. coli* ATCC 25922 MIC 45.54 µM，按序列换算约 75 µg/mL，落入 32–128 µg/mL 标签灰区，排除。[原始论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC5532647/)
- DRAMP18384/18385（sOT2/cOT2）：原文测得 28/32 µM，按质量浓度换算均落入标签灰区，不能强行标正负。[原始论文记录](https://pubmed.ncbi.nlm.nih.gov/28159460/)
- DRAMP20878（重组 VpDef）：数据库 MIC 为 50/75 µg/mL，处于标签灰区；此外尚需确认重组成熟蛋白的折叠/二硫键形式与序列表示一致。[原始研究](https://doi.org/10.1016/j.pep.2018.03.001)
- DRAMP21420/21422（AY1C/CAY1）：论文研究肽与银纳米颗粒构成的系统；在未确认单独肽对照测值前，不把系统活性归因到单独肽序列。[原始论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC6418133/)
- 其他低相似候选仍存在原始条件未充分核实、标签灰区或序列/分子形式问题；数据库的 MIC 字段没有被当作原始论文证据。

## dbAMP 3.0

官方页面提供 2024 年 6 月发布的 dbAMP 3.0 序列表和按抗菌活性整理的数据；官方教程说明记录分为实验来源与预测 AMP，并有 `Evidence` 字段。[dbAMP 3.0 下载页](https://ycclab.cuhk.edu.cn/dbAMP/download2024.php)；[dbAMP 教程字段说明](https://ycclab.cuhk.edu.cn/dbAMP/tutorial.php)

本地序列表有 35,600 行。按目标字段中含数值 *E. coli* MIC、序列为 10–50 个标准氨基酸筛出 7,031 条唯一序列和 11,205 条观测文本；其中 271 条与开发集完全重复。其余 6,760 条中，1,351 条与开发集每条成员的最高相似度低于 0.40。

但下载工作簿没有论文引用、实验条件或修饰状态；需要查询详情页才能补足。对相似度最低的 25 条非重复候选抽查详情页，页面均显示 `Experimental Evidence = NO`。该页面抽查使用的传输端不能通过正常 TLS 证书验证，所以这些页面结果仅作风险提示，未计作可靠的证据通过项。另一个可核查案例 `dbAMP_11396` 将 28 aa 序列与一篇报告 104 aa myticusin-1 的论文关联；原文支持 104 aa 分子，不支持把其 MIC 直接转给数据库中的 28 aa 序列。[原始研究摘要与分子信息](https://www.sciencedirect.com/science/article/abs/pii/S1050464812004329)

因此 dbAMP 本轮只用于寻找线索，尚无记录进入候选训练集。要继续扩大，需要按详情页筛选实验来源、确认数据库条目序列与原文受测分子完全一致，再逐篇核对测定和条件。dbAMP 下载页的许可文件允许免费学术使用；建模和再发布前仍应保留数据库引用并遵守其许可说明。

## 可复跑文件

- DRAMP 初筛脚本：[screen_dramp_ecoli_mic.py](../../02_code/screen_dramp_ecoli_mic.py)
- DRAMP 原文核实候选构建脚本：[curate_dramp_verified_mic_candidates.py](../../02_code/curate_dramp_verified_mic_candidates.py)
- dbAMP 初筛脚本：[screen_dbamp_ecoli_mic.py](../../02_code/screen_dbamp_ecoli_mic.py)
- dbAMP 详情页抽查脚本：[audit_dbamp_detail_pages.py](../../02_code/audit_dbamp_detail_pages.py)
- DRAMP 初筛表与清单：[DRAMP MIC 初筛](dramp_ecoli_mic_screen_20261001_v2/manifest.json)
- DRAMP 历史初筛候选：[候选记录表 v8](dramp_verified_ecoli_mic_20261001_v8/records.csv)、[逐条相似度审计](dramp_verified_ecoli_mic_20261001_v8/similarity_audit.csv)、[待核验阴性线索](dramp_verified_ecoli_mic_20261001_v8/pending_primary_review.csv)、[原始证据 JSON](dramp_verified_ecoli_mic_20261001_v8/raw/primary_assay_evidence.json)、[来源清单](dramp_verified_ecoli_mic_20261001_v8/manifest.json)
- dbAMP 全量候选审计：[dbAMP MIC 初筛](dbamp_ecoli_mic_screen_20261001_numba/manifest.json)、[观测表](dbamp_ecoli_mic_screen_20261001_numba/ecoli_mic_observations.csv)、[唯一序列相似度表](dbamp_ecoli_mic_screen_20261001_numba/unique_sequence_similarity_audit.csv)、[详情页抽查](dbamp_entry_pages_20261001/entry_review.csv)
- 官方原始快照位于 `02_code/data/sources/dramp_mic_screen_20261001/raw/` 和 `02_code/data/sources/dbamp_mic_screen_20261001/raw/`，下载网址、时间和 SHA-256 记在各自的 `download_metadata.json`。

## 状态解释

DRAMP v8 的 4 条初步阳性曾进入历史探索队列，后续因分子身份证据不足，均未进入当前筛选的 15 条队列；Cn-AMP2 也仍待核实。`protocol-amd-02` 和正式准备集 417 条保持冻结，正式研究仍阻断。旧探索基线只供程序诊断。[历史 MIC-only 审计 v7](mic_only_cohort_20261001_v7/report.md)及之后队列 v9 的程序判定均不能代替完整原文证据，不能作当前放行结论。当前三折分区、证据和训练状态统一由本文顶部的机器声明 v12 提供。

## 历史：MIC-only 五折训练可行性复核（2026-10-01）

新增独立审计协议 [`protocol-mic-01`](../protocols/protocol-mic-01.json)，版本 1，规范化 SHA-256：`d54227ebb5380039cd07f6ddc979561ef6f99efaecdb7644267e6c7d00dffb97`。该协议只用于训练前可行性审计；保留 `legacy-v1`、`protocol-amd-01`、`protocol-amd-02` 和原正式状态不变。

合并 417 条现有记录和 4 条 DRAMP 候选后，421 条通过当时的原始来源与实验标签重算门禁；其中 395 条有可判定标签的唯一序列（阴性 138、阳性 257），跨 296 个可识别的研究标识。全员两两比对形成 90 个同源组件；5 折每个验证集和训练补集都包含正负类，组件没有跨折。当时的 `feasible_for_training_review` 判定漏检协议要求的目标菌株标识，已被 v7 的 `blocked` 判定取代。

当时另一个风险是不可拆分的同源组件含 293/395 条序列（74.2%）。固定 seed 42 的验证折大小为 293、25、25、26、26；最大组件所在折的训练集仅 102 条。不拆同源组件、不改阈值或 seed 来修饰结果。这是历史诊断，后来的旧 324 条队列也未获当前训练释放。

审计报告与可复跑产物：[`MIC-only 五折报告`](mic_only_cohort_20261001_v3/report.md)、[`manifest`](mic_only_cohort_20261001_v3/manifest.json)、[`全成员相似度表`](mic_only_cohort_20261001_v3/all_member_similarity.csv)、[`五折分配`](mic_only_cohort_20261001_v3/fold_assignments.csv)、[`记录级证据盘点`](mic_only_cohort_20261001_v3/evidence_inventory.csv)。实现脚本为 [`audit_mic_only_cohort.py`](../../02_code/audit_mic_only_cohort.py)。

## 历史：MIC-only 探索性基线训练（2026-10-01）

曾按冻结训练协议 [`protocol-mic-04`](../protocols/protocol-mic-04.json)，SHA-256：`7847ab1bc5ba47ff20ba4d08e4142a23696ac4a52a03fabed6f838bf2381f7f0`，用现有 44 维手工序列特征、固定逻辑回归/RBF-SVM/随机森林参数，在原五折清单上生成逐样本 OOF 预测；未调参、未挑阈值、未做外部验证。RBF-SVM 的概率来自 scikit-learn 在训练分区内的内置概率估计，没有额外后处理校准。[历史结果目录](../runs/mic_only_baselines_20261001_v3/)及协议保留为审计痕迹。后续菌株标识审计发现该训练输入未满足已冻结协议；不得把这些指标报告为通过证据门禁的模型性能。

汇总 OOF 指标：逻辑回归 AUPRC 0.679、AUROC 0.503、MCC@0.5 -0.015；RBF-SVM 分别为 0.613、0.469、-0.090；随机森林为 0.640、0.528、-0.014。阳性比例为 257/395=0.651，因此 AUPRC 没有显示稳定的强信号；三个模型的 AUROC 接近随机水平，MCC 也接近零。逐折结果见 [`fold_metrics.csv`](../runs/mic_only_baselines_20261001_v3/fold_metrics.csv)，汇总表见 [`pooled_metrics.csv`](../runs/mic_only_baselines_20261001_v3/pooled_metrics.csv)。

解释必须受限：一折有 293 条、其余四折各 25–26 条，汇总 OOF 被大折主导；并且当前菌株标识证据门禁失败。这些数值只证明历史训练程序曾运行，不能作为当前协议下有效的模型性能或投稿结果；旧双任务研究与 `protocol-amd-02` 继续保持原状态。

## 基线诊断与证据纠错（2026-10-01）

诊断时发现旧 DRAMP v5 记录中 PLP2 的 `assay_conditions` 错写为 *E. coli* ATCC 25922、径向扩散法和 trypticase soy broth；其原始测定证据是 *E. coli* NBRC 14237，方法沿用论文引用文献，培养基未在筛查记录中说明。根因是候选生成脚本写入了固定条件，而原门禁仅重算标签，未比对结构化条件。已修正 [`curate_dramp_verified_mic_candidates.py`](../../02_code/curate_dramp_verified_mic_candidates.py) 和 [`evidence_validation.py`](../../02_code/evidence_validation.py)，新 DRAMP v6、MIC 审计 v3、训练协议 `protocol-mic-04` 与基线 v3 均在新目录重建；旧文件未覆盖。新旧折表及逐样本预测的 SHA-256 相同，故性能数字未变。

历史[失败原因诊断报告](mic_baseline_diagnostics_20261001_v8/report.md)和[逐条实验测定表](mic_baseline_diagnostics_20261001_v8/assay_observations.csv)显示：大组件 293 条中仅 1,166/42,778 对序列直接达到 0.40，同一连通组件主要由传递路径形成；折 0 训练集阳性比例 46.1%，验证集为 71.7%，三个模型预测阳性比例分别为 39.9%、11.6%、14.3%。[跨折论文清单](mic_baseline_diagnostics_20261001_v8/cross_fold_study_overlap.csv)记录了 16 个与测定关联且跨折的论文标识；这些标识可为 DOI、PMID 或 DBAASP 内部论文 ID，同一论文可能有多个别名。这是来源相关性风险，尚未证明标签泄漏。完整[序列名称与来源](mic_baseline_diagnostics_20261001_v8/reported_name_inventory.csv)、[各折预测分布](mic_baseline_diagnostics_20261001_v8/fold_prediction_distribution.csv)、[按论文错分统计](mic_baseline_diagnostics_20261001_v8/study_error_summary.csv)与[三个模型共同错分样本](mic_baseline_diagnostics_20261001_v8/shared_errors.csv)可供后续逐项审阅。诊断只做描述分析，不改变五折或正式阻断状态。

## 历史：MIC-only 同论文隔离可行性审计（2026-10-01）

新增冻结的审计协议 [`protocol-mic-study-01`](../protocols/protocol-mic-study-01.json)（规范化 SHA-256：`6ddb23d9b616581961a9ba269fa4eb787b846a1e371dacf8190d3c66085273d8`）。在原 0.40 全员同源组件之上，把共享原始 MIC 测定论文的序列继续合并；同一引用对象内的 DOI、PMID 和 DBAASP 论文 ID 视为别名，不按标题猜测合并。审计输入为 MIC 队列 v3、诊断 v8 和来源记录，并记录输入哈希。

395 条序列从 90 个同源组件合并成 63 个同源加论文组件，最大组件 318 条，连接了 22 个原同源组件。固定 seed 42 的五折验证集为 318、19、20、20、18 条；五折训练补集及验证集都有正负类，共享组件、共享原始论文、跨折超阈值相似边均为 0。最大组件所在折仅有 77 条训练样本。旧 `feasible_for_training_review` 只描述当时的隔离与类别条件，不能覆盖新发现的证据失败；新分折没有训练模型。

可复核文件：[审计报告](mic_study_disjoint_20261001_v2/report.md)、[manifest](mic_study_disjoint_20261001_v2/manifest.json)、[合并组件](mic_study_disjoint_20261001_v2/combined_components.csv)、[论文桥接表](mic_study_disjoint_20261001_v2/study_bridges.csv)与[固定五折清单](mic_study_disjoint_20261001_v2/fold_assignments.csv)。下一步应增加来自新论文且不并入现有大组件的正负样本，再重新审计分折稳定性；不通过调节 0.40 阈值或挑选 seed 消除失衡。原双任务正式状态仍为 `blocked`。

## 历史：增补 Cn-AMP2 后的 MIC-only 审计（已被证据纠错取代）

将 DRAMP v7 的 5 条候选与 417 条现有记录重新进行证据及全员相似度审计：[MIC-only 队列 v4](mic_only_cohort_20261001_v4/report.md)共 396 条唯一有标签序列（257 阳性、139 阴性），91 个同源组件，最大组件仍为 293 条。新候选未与现有大组件合并。研究论文隔离使用单独冻结的 [`protocol-mic-study-02`](../protocols/protocol-mic-study-02.json)（SHA-256：`676b9eaafb916572e15161d9fde10212f78d61e8bb53598b794db84529fe3ff8`）；[同论文隔离审计 v4](mic_study_disjoint_20261001_v4/report.md)产生 64 个组件，最大组件仍为 318/396 条。固定五折验证集为 318、19、20、20、19 条，最大组件所在折训练集 78 条。每折训练、验证均有两类，跨折同源边及原始 MIC 论文均为 0。

该版本 manifest 所写 `feasible_for_training_review` 是当时未检查菌株标识的历史结论。[历史审计 manifest](mic_study_disjoint_20261001_v4/manifest.json)及[逐条主测定论文映射](mic_study_disjoint_20261001_v4/assay_observations.csv)仅供追溯；396 条队列没有训练模型。Cn-AMP2 已从当前候选中移除，正式双任务研究继续 `blocked`。

### 下一批原文线索的排除理由

| 原文线索 | 本轮核查 | 处理 |
|---|---|---|
| [Cateslytin 扰乱序列实验](https://www.nature.com/articles/s41598-021-94749-6) | 论文给出 15 aa L 型扰乱序列 `FMRLRYRSSAFGGRR`，对受测耐药菌 MIC `>128 µg/mL`；本地与 417 条开发记录及 5 条候选全员比对的最高一致性恰为 **0.40** | 达到冻结阈值，会连接既有组件；不能作为新的独立组件加入本轮候选。 |
| [Aurein 1.2 丙氨酸扫描](https://pmc.ncbi.nlm.nih.gov/articles/PMC6695355/) | 论文有多条 *E. coli* MIC `>=128 µg/mL` 的 13 aa 变体，但表 1 明确这些合成肽为 C 端酰胺化形式 | 当前未修饰序列协议不能直接表示受测化学形式，暂不纳入。 |
| [NCR247 测定条件比较](https://pmc.ncbi.nlm.nih.gov/articles/PMC6218624/) | 同一序列对 *E. coli* 在不同培养基下分别报告 16 µM 与 128 µM，相差八倍 | 不能只挑选一个培养基测值生成单一标签，暂不纳入。 |
| [FNZ 真菌 defensin](https://www.mdpi.com/2079-6382/12/4/786) | 原文报告 *E. coli* ATCC 25922 MIC `>128 µg/mL`，但成熟肽精确序列需从补充表核对，且二硫键等化学形式需明确 | 保留为下一轮原文核验线索，不生成记录。 |

这轮扩展没有找到第二个可独立纳入的阴性组件；不能用资料库分类、模型预测或不完整论文信息补足样本数。
