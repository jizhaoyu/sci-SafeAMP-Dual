# SafeAMP-Dual：可追溯的计算研究原型

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

当前状态（`04_paper/research_status.json`）：**原双任务正式研究的数据准备被阻断；无正式实验运行、正式结果或投稿授权**。工程管线已实现。MIC-only 扩充线的[历史机器状态 v15](03_experiments/audits/mic_training_readiness_20261002_v15.json)（2026-10-02 21:43:53，Asia/Shanghai）为 **`local_exploratory_esm2_training_completed`**：依据冻结训练协议 `protocol-mic-10`，在固定三折拓扑下完成手工（44 维）、ESM-2（320 维）及 Hybrid（364 维）三种表征空间的对比拟合，运行目录为 `03_experiments/runs/mic_three_fold_esm2_20261002_v1`，保存 27 个折模型及 153 条 OOF 预测，产物复核报告为 `03_experiments/audits/mic_esm2_run_validation_20261002_v2.md`。RF 在 ESM-2 嵌入下实现 0 假阳性（FP=0，特异性 100%），MCC 为 0.494413，平衡准确率 0.666667；LR 在 ESM-2 下成功识别 4 条阳性（TP=4）。  
前序手工基线[机器状态 v14](03_experiments/audits/mic_training_readiness_20261002_v14.json)（2026-10-02 21:17:33，Asia/Shanghai，数据版本 `mic_source_expansion_result_20261002_v2`，审计协议 `protocol-mic-08`，训练协议 `protocol-mic-09`，状态 **`local_exploratory_three_fold_training_completed`**，运行目录 `03_experiments/runs/mic_three_fold_20261002_v2`，保存 9 个模型与 51 条 OOF 预测，[产物复核报告](03_experiments/audits/mic_three_fold_run_validation_20261002_v5.md)）及历史 15 分子基线（`mic_three_fold_20261002_v1`，[机器状态 v12](03_experiments/audits/mic_training_readiness_20261002_v12.json)，2026-10-02 18:51:38，审计协议 `protocol-mic-06`，训练协议 `protocol-mic-07`，[原文释放复核](03_experiments/audits/mic_three_fold_primary_release_20261002_v1/report.md)）完整保留。各验证折严格平衡包含 2 条阳性，136 对全员同源隔离与研究隔离跨折均为 0。结果范围严格限于 17 条分子的本地小样本探索，原双任务正式门禁维持阻断（`blocked`）。
来源扩充与基线训练进展（`protocol-mic-08` / `protocol-mic-09` / `protocol-mic-10`）：[来源扩充审计报告](03_experiments/audits/mic_source_expansion_result_20261002_v2/report.md)审查了 12 篇公开原始文献、81 条记录；纳入 2 条局部确认分子（Piscidin 1 游离酸与 BMAP-27B 游离酸，分别明确 UTSW 纯化与 Fmoc-Gly Wang Resin 固相合成，E. coli ATCC 25922 MIC 5.14–25.72 µg/mL 与多重耐药株 CREC 1.563–6.250 µg/mL，阳性 2，注明培养基及菌株热图区间局限）、暂缓 36 条、排除 43 条。结合既有 15 条形成 17 条候选分子（6 阳性、11 阴性）、24 条测定；136 对全员比较，11 条同源边，8 个不可拆分组件（含阳性 5、含阴性 6，最大组件 6 条）；在固定 seed 42 下固定三折结构门禁通过。随后完成 `protocol-mic-09` 手工基线训练与 `protocol-mic-10` ESM-2 表征探索训练。本次探索严格限于本地 17 条分子小样本方法学探究，不作为广泛泛化或临床效用证据，原正式双任务保持阻断（`blocked`）。
最新进展与状态见 [整改状态看板](docs/REMEDIATION_STATUS.md)、[机器可读状态声明](04_paper/research_status.json) 及 [全局文档索引](docs/DOCUMENTATION_INDEX.md)。

研究问题：在真实实验标签、缺失标签掩码和严格序列隔离条件下，联合学习能否改善抗菌／溶血预测的性能权衡和校准？

## 核心进展与已实现能力
- **严格隔离协议已实现**：[Protocol Amendment 02](docs/amendments/PROTOCOL_AMENDMENT_02_ALL_MEMBER.md) 冻结全局比对列数作分母、0.40 阈值和全员连通分组。417 条开发记录形成 89 个簇，最大簇 318 条；它仍可能限制可行的五折划分。
- **旧外部队列已逐条审计**：`combined_v2` 中 13 条外部记录只有手写标签、缺少原始测定。新候选源保留 417 条证据通过的开发记录，排除这 13 条，当前没有合格的外部队列。
- **独立候选已复核**：本地 DRAMP 10 条候选与开发集的 4,170 对全员比较已保存；每条候选至少有一对一致性达到 0.40，均未通过隔离门禁。
- **科学门禁保持阻断**：当前准备清单为 `blocked`，正式训练和结果导出尚未开始。2026-10-01 本地全量回归为 **182 passed**；这是软件测试结果，不是模型性能验证。
- **MIC-only 本地探索训练已完成**：[前瞻性三折修订](docs/amendments/PROTOCOL_MIC_06_THREE_FOLD.md)先于分区审计冻结。15 条分子、22 条测定在固定 seed 42 下，各验证折阳性/阴性为 2/4、1/4、1/3，对应训练为 2/7、3/7、3/8；105 对全员重算，跨折同源及原始研究均为 0。[完整证据复核](03_experiments/audits/mic_three_fold_primary_release_20261002_v1/report.md)绑定七个原始研究及一份引用方法，缺失条件如实保留；所有标签由真实 MIC 重推导。训练协议 `protocol-mic-07` 的 44 维特征、固定 LR/RF 和 prior 对照均已执行，训练内标准化，无调参、校准或模型择优。三个模型在固定 0.5 阈值下均未识别四条阳性；[全部描述性结果](03_experiments/audits/mic_three_fold_run_validation_20261002_v2.md)如实保留，不据此修改协议。原 34 条暂缓、末端/单位冲突以及[旧五折不足](03_experiments/audits/mic_extended_acid_cohort_20261002_v1/report.md)继续保留，旧 324 条及 `protocol-mic-05` 仍被拒绝。每验证折仅 1–2 条阳性，不能据此声明广泛泛化或临床效用。
- **原论文核对正在进行**：[逐测定审计 v3](03_experiments/audits/mic_primary_review_20261001_v3/report.md)对一篇原始论文关联的 10 条记录核对序列和 30 个论文 MIC 靶标；完整数据库快照有 31 条相应测定，30 条数值一致、1 条冲突。`DBAASP:25512` 对 AIC222 同时记了 `16 µM`（CRE，与原表一致）和 `>64 µM`（VRE，与原表冲突），旧二值清单只留下后者。[逐原始测定表](03_experiments/audits/mic_primary_review_20261001_v3/raw_activity_review.csv)和[论文核查队列](03_experiments/audits/mic_primary_review_20261001_v3/paper_queue.csv)已保存；没有释放训练记录或修改旧标签。
- **历史第二篇原论文核对**：[Ross 等 2020 审计 v2](03_experiments/audits/mic_primary_review_pmid33281785_20261002_v2/report.md)将 8 条冻结记录对应到 Figure 1 序列及 Table 1 的 *E. coli* BL21 MIC，8 条数值均与数据库原始活动一致。图片序列尚待独立复核；论文溶血实验采用绵羊血，不能作为人红细胞 HC50。这 8 条未进入当前 15 条释放队列。
- **历史第三篇原论文核对**：[Richter 等 2022 审计 v2](03_experiments/audits/mic_primary_review_pmid36551368_20261002_v2/report.md)从出版方补充 Table S1 核对 7 条冻结记录的序列、*E. coli* ATCC 25922 MIC 和原始活动，全部对应 `>128 µg/mL`；其中一条同时关联第二篇论文，保留双重来源以约束分折。论文使用猪红细胞。这 7 条分子身份尚待核实，未进入当前 15 条释放队列。
- **历史局部原论文核对**：[Nagarajan 等 2018](03_experiments/audits/mic_primary_review_pmid29259134_20261002_v2/report.md)核对 1 阳性、2 阴性，图片表格仍待独立复核；[Okimura 等 2021](03_experiments/audits/mic_primary_review_pmid33790103_20261002_v2/report.md)核对 3 阴性及游离羧酸端。两份局部报告生成时均未释放；随后 Okimura 的 3 条已完成代理原文/图像释放复核并进入当前训练队列，未声称独立人工审稿。
- **明确排除和限用**：[Pandi 等 2023](03_experiments/audits/mic_primary_review_pmid37938588_20261002_v2/report.md)的两条受测肽为 C 端酰胺化，旧来源却标为未修饰，暂排除；[Guan 等 2025](03_experiments/audits/mic_primary_review_pmid40645962_20261002_v2/report.md)只有 4 条数值可逐值核对，另 8 条图源值 `80` 缺编码定义，未作 `>64 µM` 推断。Guan 的 4 条也仅是分组可行性候选，未获训练放行。
- **新增阴性候选仍待澄清**：[Wang 等 2025](03_experiments/audits/mic_primary_review_pmid39908380_20261002_v2/report.md)的 2 条序列及补充 Table S5 `>400 µM` 可对应数据库记录；正文 Methods 却把浓度梯度上限写为 `200 µM`，且原文目标为 *E. coli* GD004、冻结记录只写物种。两条未计入可行性分组或训练释放。
- **Ludwig 等 2022 新候选**：[原始表格审计](03_experiments/audits/mic_primary_review_pmid35735615_20261002_v1/report.md)核对 5 条游离酸端 apidaecin 的 8 条 MIC，保留 3 条分子的 4 条候选测定；Api802 存在阈值空档，Api806 跨培养基标签冲突，均排除。Api810 与现有肽同源，整篇论文一起合并，未虚增独立组件。
- **额外来源待审，未合入当前队列**：[Bhaumik 等 2024 审计](03_experiments/audits/mic_primary_review_pmid39367191_20261002_v1/report.md)核查 17 条有明确末端形式的肽：6 条游离酸端阳性证据候选；8 条酰胺端、2 条阈值空档排除。Buforin II 的 `>250`／`250 µg/mL` 原文删失标记不一致，留待核实。原文许可为 CC BY-NC-ND 4.0，项目再利用范围尚待审查；未释放训练。[Cateslytin 2021 原文复核](03_experiments/audits/mic_cateslytin_source_review_20261002_v1.md)的两条 L 型肽缺明确末端形式，也未入选；未转用 D 型肽的测定。
- **已纳入探索的阴性组件**：[Hirsch 等 2020 的 EtCec3-OH](03_experiments/audits/mic_primary_review_pmid32344933_20261002_v2/report.md)有原论文明确的游离羧酸端 41 aa 序列和对两个 *E. coli* 菌株的 `>1024 µg/mL` MIC。它已通过当前 15 条队列的完整证据复核并用于 MIC-only 三折探索训练；与旧 324 条队列中的 1 条同源，仍不能用于原双任务的独立外部队列。
- **Cn-AMP2 退回待核验线索**：原文报告 *E. coli* MIC 170 µg/mL，但未给出受测菌株或分离株标识，另有受测分子质量差异待解释。[DRAMP 候选 v8](03_experiments/audits/dramp_verified_ecoli_mic_20261001_v8/manifest.json)仅收录 4 条阳性记录，[待核验表](03_experiments/audits/dramp_verified_ecoli_mic_20261001_v8/pending_primary_review.csv)单列 Cn-AMP2。旧 396 条和 64 组件审计保留作版本化追溯，不能视为当前可训练队列。
- **七种模型与实验架构就绪**：SVM、RF、门控双任务、拼接双任务、仅理化、仅 ESM、独立单任务，共七种配置，固定三个种子。
- **训练内预处理与防泄漏机制**：StandardScaler 仅在训练折拟合、开发集 OOF 校准及阈值确定、全开发集重训、逐样本预测、簇级 Bootstrap 置信区间和配对比较。
- **真正的 fair-esm 特征与可追溯权重校验**：缺失模型返回 HTTP 503，非法输入返回 422。

## 复现命令（本地 PowerShell 标准数据流）
环境：Python 3.11；直接依赖见 `requirements.txt`，前端以 `package-lock.json` 为准。
注意：已有生成目录具有不可变性，严禁直接覆盖旧版本目录，每次新生成请使用新的输出目录。

MIC-only 的旧 `protocol-mic-05` 训练入口现会拒绝未完成原论文对象核对的 458 条测定；不能用该命令产生新模型。必须先形成逐测定的原始论文证据、剔除无法核实项，重新冻结队列和协议并通过所有分折门禁。

本轮的训练入口绑定冻结证据、`protocol-mic-07`、15 条分子和已核查的三折角色。当前已有上述完整训练运行；以下第一条仅重新生成训练前门禁快照，第二条复跑本地探索训练。当前完成状态以 v12 为准，输出路径必须不存在：

~~~powershell
python 02_code/train_mic_three_fold_v2.py --check-ready --output 03_experiments/audits/mic_training_readiness_my_run.json
python 02_code/train_mic_three_fold_v2.py --output 03_experiments/runs/mic_three_fold_my_run
# 扩充 17 分子队列（protocol-mic-09）本地探索训练与产物复核（当前完成状态以 v14 为准）：
python 02_code/train_mic_three_fold_v3.py --check-ready --output 03_experiments/audits/mic_training_readiness_v13_my_run.json
python 02_code/train_mic_three_fold_v3.py --output 03_experiments/runs/mic_three_fold_v2_my_run
python 02_code/validate_mic_three_fold_run_v2.py --run 03_experiments/runs/mic_three_fold_20261002_v2 --output 03_experiments/audits/mic_three_fold_run_validation_my_run.json --state 03_experiments/audits/mic_training_readiness_20261002_v14.json --check-documents
# 扩充 17 分子队列 ESM-2 预训练表征探索（protocol-mic-10，当前完成状态以 v15 为准）：
python 02_code/train_mic_esm2_three_fold.py --run 03_experiments/runs/mic_three_fold_esm2_my_run
python 02_code/validate_mic_esm2_three_fold_run.py --run 03_experiments/runs/mic_three_fold_esm2_20261002_v1 --output 03_experiments/audits/mic_esm2_run_validation_my_run.json --state 03_experiments/audits/mic_training_readiness_20261002_v15.json --check-documents
~~~

证据和分区复跑命令如下，仍不启动模型拟合：

~~~powershell
python 02_code/audit_mic_three_fold.py --output 03_experiments/audits/mic_three_fold_my_run
python 02_code/audit_mic_three_fold.py --output 03_experiments/audits/mic_three_fold_my_run --publish-state 03_experiments/audits/mic_training_readiness_three_fold_my_run.json
python 02_code/review_mic_three_fold_evidence.py --output 03_experiments/audits/mic_primary_release_my_run
python 02_code/audit_mic_source_expansion.py --output 03_experiments/audits/mic_source_expansion_my_run
python 02_code/validate_mic_three_fold_run.py --run 03_experiments/runs/mic_three_fold_20261002_v1 --output 03_experiments/audits/mic_three_fold_run_validation_20261002_v3.json --state 03_experiments/audits/mic_training_readiness_20261002_v12.json --check-documents
~~~

当前产物复核重新加载九个模型，并独立重算预测、指标和全员隔离，核对 v12 与五份当前文档；不调用 fit。此前 `validate_mic_three_fold.py` 的 v10 文档核查和 `validate_mic_training_ready.py` 的 v11 文档核查属于冻结历史时点，文档已更新后不适合作为当前入口。前版五折来源/队列复跑命令保留如下。冻结的前版分组报告中复跑示例漏写 `audit` 子命令，以这里的完整命令为准：

~~~powershell
python 02_code/audit_mic_independent_sources.py --output 03_experiments/audits/mic_independent_review_my_run
python 02_code/audit_mic_extended_acid_cohort.py audit --output 03_experiments/audits/mic_extended_my_run
python 02_code/audit_mic_extended_acid_cohort.py state --cohort 03_experiments/audits/mic_extended_my_run --output 03_experiments/audits/mic_training_readiness_my_run.json
~~~

分组入口读取冻结的新来源审计 v1 和旧游离酸筛选 v1；另行复跑的来源表供逐值比较，不会自动替换冻结输入。

~~~powershell
# 1. 运行自动化单元测试
python -m pytest -q -p no:cacheprovider

# 2. 从旧快照逐条排除缺实验测定的外部记录（使用新的输出目录）
python 02_code/curate_evidence_clean_source.py --records 02_code/data/sources/combined_v2/records.csv --output 02_code/data/sources/combined_v3_my_run

# 3. 使用冻结的严格协议准备数据；外部队列为空时会如实退出并保存阻断审计
python 02_code/research_data.py --records 02_code/data/sources/combined_v3_my_run/records.csv --output 03_experiments/prepared/amd02_my_run --protocol-id protocol-amd-02

# 4. 从实际准备清单生成当前状态
python 02_code/research_readiness.py --prepared 03_experiments/prepared/amd02_my_run --output 04_paper/research_status.json
~~~

只有新准备目录的清单和可行性复核均为 `validated`，才可将它传给 `train_and_eval.py`。当前示例预期保持阻断。

## 本地交互界面启动
~~~powershell
# 可选构建前端
cd frontend
npm ci
npm run build
cd ..

# 设置已完成实验的产物目录环境变量（若无或未验证，系统 fail-closed 返回 503）
$env:SAFEAMP_RUN_DIR = "03_experiments/runs/phase_d_example"
python -m uvicorn app:app --app-dir 05_web_server --host 127.0.0.1 --port 8000
~~~
服务探针：
- `/api/health`：服务进程存活探针（存活即返回 200）。
- `/api/ready`：模型就绪探针（已加载且验证完成返回 200，未配置或未通过校验返回 503）。
- `/api/system_status`：查看模型与运行时详细状态。
浏览器访问 `http://127.0.0.1:8000`。界面不发送序列到外部 LLM，也不存储 API 密钥。

## 项目证据与文档导航
* **文档全局总索引**：[docs/DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md)
* **协议与修订案**：[docs/research_protocol.md](docs/research_protocol.md) 与 [Protocol Amendment 02](docs/amendments/PROTOCOL_AMENDMENT_02_ALL_MEMBER.md)
* **实时整改状态**：[docs/REMEDIATION_STATUS.md](docs/REMEDIATION_STATUS.md)
* **当前准备清单**：[03_experiments/prepared/amd02_evidence_clean_20261001/manifest.json](03_experiments/prepared/amd02_evidence_clean_20261001/manifest.json)
* **活动稿件**：`04_paper/manuscript.tex`，真实科研方案草稿，不含虚构作者和基金。
* **文献元数据核验**：`04_paper/evidence/` 与 `04_paper/evidence/declarations.json`。
