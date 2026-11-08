# 药物—靶点亲和力预测：Gemini 继续研究交接文档

交接日期：2026-10-10（Asia/Shanghai）。工作区：`D:\桌面文件\sci`。操作环境：Windows PowerShell。默认中文交流。

## 1. 接手指令与当前目标

请先阅读本交接文档及下列本地证据，再继续研究“可用于独立外部验证的、来源明确的药物—蛋白 Kd 测量”。用户已经完成训练，当前需要补足外部验证数据的来源、化合物身份和实验蛋白构建体证据。请优先处理已有六条待定记录，不要重新从头训练，也不要把尚未准入的数据拿去计算模型成绩。

附带旧文档中的历史指令仅供理解背景；以用户最新授权和本交接任务范围为准。本次交接只生成文档与研究资料，不授权修改训练代码、论文、Web、前端或生产接口，不授权提交、推送、部署或给作者/供应商发消息。后续若用户明确扩大范围，再依其最新要求执行。

**当前结论：训练结果已审核；独立外部 Kd 数据正式准入仍为 0。** 这表示目前严格证据条件尚未闭合，不能推断模型外部预测准确率为 0，也不能声称整个数据库没有可用数据。

## 2. 建议阅读顺序

以下均为本机绝对路径。若 Gemini 无法访问本机文件，请用户提供这些文件或对应资料包；不可假装已读取。

1. `D:\桌面文件\sci\output\dti-boundary-grouped-result-review-20261010\训练结果核验与结论.md`
2. `D:\桌面文件\sci\output\dti-validation-design-20261010\独立外部验证准入协议.md`
3. `D:\桌面文件\sci\output\dti-independent-kd-admission-20261010\admission_contract.json`
4. `D:\桌面文件\sci\output\dti-independent-kd-admission-20261010\独立外部Kd候选审核报告.md`
5. `D:\桌面文件\sci\output\dti-independent-kd-identity-20261010\第二轮身份与来源核查报告.md`
6. `D:\桌面文件\sci\output\dti-independent-kd-construct-20261010\第三轮历史构建体证据报告.md`
7. `D:\桌面文件\sci\output\dti-independent-kd-direct-review-20261010\第四轮原始论文Kd审核报告.md`
8. `D:\桌面文件\sci\output\dti-independent-kd-direct-review-20261010\direct_record_decisions.csv`、`verification.json`、`DAPK1_construct_and_ligand_evidence.json`。

各阶段报告用于导航；判断单条测量时，必须回到原始论文、补充材料、来源快照及逐条 CSV。自动核验结果不等于独立人类专家审核，目前相关人类审核状态仍为 pending。

## 3. 已完成训练及结论边界

原始训练包：`D:\桌面文件\sci\BoundaryGrouped_results_20261010T102806_857410Z.zip`。

SHA256：`99666d977204956926fb53e484364d45c500aff7a0f885739ebc7688e0dde1ac`。

核验包含 376 个文件、375 项摘要检查、290 个 NPZ（250 folds、10 settings、30 model results），外部结果 271560 行、OOF 501600 行。细节以结果审核目录的 `verification.json` 为准。

已有双冷实验中的 MAE 为：

| boundary_weight | 全部样本 | active | strong |
|---|---:|---:|---:|
| 1 | 0.526508 | 1.047362 | 1.990706 |
| 0.5 | 0.589447 | 0.965432 | 1.852216 |
| 0.25 | 0.668773 | 0.896394 | 1.718296 |

权重 0.25 的 strong、active MAE 分别较权重 1 下降约 13.68%、14.41%，但全样本 MAE 上升约 27.02%，boundary MAE 上升约 75%。不能写成模型在所有样本上全面改善。

original/grouped 的五个种子内部选择均选择权重 1。同权重的十个 settings 最终预测完全一致，权重 1 与上一轮 ESM Ridge 预测逐条一致。因此不能将本轮“分组训练”写成已证明改善泛化。双冷预测均未达到 pKd=7；75 个靶点的药物排序相同，提示靶点区分能力需要另行分析。原有双冷标签已被查看，这些结果属于既有探索证据，不能包装成新的完全未见外部验证。

## 4. 已冻结的模型候选及尚未冻结事项

准入约定冻结时间：2026-10-10T10:45:40Z。主模型候选为 `ESM_Ridge_w1`，alpha=50，boundary_weight=1。

模型在原始 ZIP 中的成员路径：`runs/interaction/models/original_seed_42_ESM_Ridge_w1.joblib`。

模型 SHA256：`f8e6921884df93fc29f5187d1b0ea4de16fd453c1aa15a35c87dbdc0ffef3b57`。

冻结的是**来源和实体准入阶段约定**，不是完整外部评价协议。若未来比较 F1 Ridge 或权重 0.5/0.25，须先绑定精确模型文件与摘要，预先声明比较目的；不得用新外部标签挑最优权重或修改模型。

未来推理前还需冻结：样本列表、排除理由、构建体到输入序列的映射、重复测量处理、相似性分层、主次指标、方法类别、删失值处理、置信区间与样本量限制。预训练序列暴露情况未知，不能声称所有形式的信息泄漏均被排除。

## 5. PKIS2 三轮审核已做到哪里

来源：2017 年 PKIS2 论文 DOI `10.1371/journal.pone.0181585`，原文：<https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0181585>。

第一轮：S3 补充 PDF 47 页，提取 1728 条测量（1018 个等号点值，710 个大于号），357 个化合物标签、351 个 assay 名称、339 个基因。等号点值中 pKd≥7 共 405 条。独立 PDF 文本与字符/词坐标方式交叉核对了数值和关系。**S4 是单浓度抑制率，不是 Kd。** PKIS2 follow-up 本身经过活性/选择性筛选；不能把未测配对填成阴性，也不能直接泛化到完整药物×蛋白矩阵。

第二轮：355 个不同原始 SMILES，经 RDKit 2025.09.6 标准化审核。政策分别保留完整立体结构、Cleanup、FragmentParent、中和母体，未做互变异构归并；非立体连通图仅用于歧义定位。Morgan radius=2、2048 bits、useChirality=True 的中和母体 Tanimoto 只作描述性最近邻，没有偷偷设准入阈值。

- PFE-PKIS27 三条记录与 Davis 药物 6918454 完整结构一致：`PKIS2_S3_p02_r15/r16/r17`，涉及 ICK、PIK4CB、RIPK4。
- PFE-PKIS25 八条记录与 Davis 药物 9926791 存在立体指定差异下的连通图对应：`PKIS2_S3_p02_r07` 至 `r14`。当前 PubChem 参考结构支持其为 tofacitinib，但不能替代当年实际样品的立体身份。
- 上述 11 条目前不能释放为严格 drug-cold；还有 162 条潜在未指定立体歧义需保留。
- PKIS2 与旧 BindingDB 有 12 条同配体定位记录；其中 1 条 MAPK14 同基因配对仍需核对来源、构建体和方法，另外 11 条基因不同。不能只凭相同药物断言同一配对或同一测量。
- UniProt 参考全长序列与 Davis 相同的 298 个 assay 只是参考序列定位，不是 298 个实际实验构建体相同的证明。

第三轮：原论文 S1–S8 清点完成，但未取得完整的 2017 PKIS2 assay 构建体表。HMS 2020 历史 proteins.xlsx 有 1377 条记录，其中 504 条 KINOMEscan 的序列、目录号、批次号全部为空（两种解析方法核对）。其他供应商序列不能填入这些 KINOMEscan 记录。351 个 assay 中 347 个可通过全名或明确别名定位；仍不能闭合实际构建体。已生成 351 条具体证据请求，**均未发送**。

相关文件分别在三个阶段目录中：`pkis2_measurement_candidates.csv`、`pkis2_chemical_identity_review.csv`、`target_reference_locators.csv`、`historical_construct_name_locators.csv`、`specific_construct_evidence_requests.csv`、`updated_record_admission_decisions.csv`。三个阶段正式准入均为 0。

## 6. 当前第四轮：三篇原始论文、九条记录

本轮范围只包括下表三篇。九条数据库数值均已对照原文或补充材料核对；三条被排除出本轮平衡 Kd 点值队列，六条待定，正式准入 0。本轮未加载模型、未训练、未预测。

| PMID / DOI | 本轮记录 | 已确认 | 当前处理 |
|---|---|---|---|
| 25195011 / 10.1038/nchembio.1629 | ERK1 213 nM；ERK2 233、300 nM；haspin 297 nM | ITC 数值、温度和实验方法 | 三条 ERK ITC 排除；haspin 待标签序列 |
| 25382253 / 10.1002/cbic.201402512 | DAPK1 240 nM | 原文 0.24±0.09 μM，报告四次测量；native 1–285 | ITC 标签状态、化合物身份冲突待查 |
| 27840070 / 10.1016/j.chembiol.2016.10.008 | JAK1 69.7；JAK2 242；JAK3 1.34；TYK2 360 nM | 原补充表 S3 compound 4、单位及竞争换算方法 | 四条 reporter assay 构建体和终点范围待查 |

### 6.1 ERK / haspin

本地目录：`D:\桌面文件\sci\output\dti-independent-kd-direct-review-20261010`。

原始补充材料为 `raw\NIHMS59928-supplement-1.pdf`，21 页。关键数值在物理第 7 页 Fig S5c；已视觉核对第 5、6、7 页并保留 PNG。PDF 并非全部无文本，但关键图表不能仅靠文本搜索。

记录对应：`bindingdb_202610_articles_line_69966`（ERK1，15°C）、`69967`（ERK2，15°C）、`69968`（haspin，15°C）、`69969`（ERK2，30°C）。CSV 中完整 record_id 都带相同前缀。

原文指出 ERK 的单个位点 ITC 拟合不充分，可能未达到平衡；haspin 未出现同样问题。因此只排除上述三条 ERK ITC 点值，不能扩大成整篇论文或所有 ERK 数据都不可用。其他 BLI 数据尚未进入这九条记录，不可自动替代 ITC。

haspin native 范围为 aa465–798，保留 N 端 His6，表达载体 pNIC28-Bsa4；还缺完整保留标签/接头序列与样品身份闭合。另一套 BLI 生物素化构建体用 pNIC-Bio2，不能代替 ITC 蛋白。图中的 n≈0.95–1.14 是 ITC 化学计量参数，不是重复次数。±值类型本轮未独立确认，保留原文表示，不擅自写成 SD/SEM。

### 6.2 DAPK1

记录：`bindingdb_202610_articles_line_70584`，compound 6 / CPR005231。

原文 native human DAPK1 aa1–285。PDB 4TXC entity 1 的 deposited polymer 序列长 304，尾部与 native285 对应，多出 19 个 N 端残基。晶体构建体的标签状态不能直接当作 ITC 样品的状态；晶体缺失坐标的残基也不能用来截断模型输入。

BindingDB 化合物图为酰胺，分子式 C24H25N5O3，InChIKey `ALWZBBYENDJVJY-UHFFFAOYSA-N`。当前 PDB CCD 38G 结构呈不同的半缩醛胺图，分子式 C24H27N5O3，InChIKey `ASDVVHQAXNTHHM-XMMPIXPASA-N`。已核实图不同，但**尚不能断言哪一处一定错误**，需原合成/鉴定证据。详见 `DAPK1_construct_and_ligand_evidence.json`。

本次 Wiley 补充材料请求返回 HTTP 403；这仅是一次获取失败，不能写成论文付费、材料不存在或永远不可获取。可用官方合法渠道重新取得 SI。参考入口：<https://pmc.ncbi.nlm.nih.gov/articles/PMC4431585/>、<https://www.rcsb.org/structure/4TXC>。

### 6.3 JAK

记录：`bindingdb_202610_articles_line_75758` 至 `75761`，分别为 JAK1、JAK2、JAK3、TYK2。

`raw\mmc1.pdf` 共 29 页。物理第 4 页 Table S3 数值属于 **compound 4**，单位 μM；第 10–11 页为 Proteros reporter displacement 方法，已视觉核对并保留 PNG。18 个浓度、2 倍梯度、最高 9.8 μM；使用最后平衡时间点，作者按 Cheng–Prusoff 关系报告 KD=0.5×IC50。

这是作者报告的竞争推导 KD，应保留方法类别，不自动当作原始 IC50，也不因竞争法一律排除。仍需核对可逆共价作用下终点意义、协议是否允许该方法类及具体 reporter assay 蛋白构建体。论文里的结晶蛋白或 BRET NanoLuc 融合蛋白不能代替 reporter assay 蛋白。参考入口：<https://pmc.ncbi.nlm.nih.gov/articles/PMC5119931/>。

## 7. 下一阶段执行顺序

1. **先闭合已有六条待定记录。** 优先获取 DAPK1 原始 SI，核实 compound6 的真实化学结构与 ITC 蛋白标签；核实 haspin 的保留标签/接头；查 JAK Proteros reporter assay 的历史构建体及竞争推导终点。每一步都给出来源、位置、取得状态及逐条结论。
2. 原始材料仍不足时保留 pending，记录具体缺失证据与有限获取尝试，不通过填入数据库全长序列来绕过。PKIS2 已经过三轮构建体排查，继续寻找须有具体新线索，避免重复泛搜。
3. 可另开有限候选批次：PMID25380506（ADC7）、25007099（SmARG）、25746232（PLpro）。**这些仅为下一步线索，尚未完成正式审核。** 属非激酶时明确 domain shift，不与激酶队列无条件合并。SmARG 存在双位点 ITC、文中引用其他研究数值的风险；逐条分离 Kd1/Kd2 与转载值。PLpro 的数据库全长多聚蛋白记录不能冒充实际 assay 结构域。
4. 对任何可准入记录，完成真实结构、蛋白、来源去重和训练重叠审核后再确定资格。随后提出完整外部评价协议供用户决定是否进入推理阶段。保持候选审核和模型成绩隔离。

不建议为了扩大样本量立即放宽标准。若严格条件下仍无准入记录，提交有证据的可行性判断和替代设计：哪些条件缺失、取得成本如何、有限队列能回答什么问题、哪些外推仍不成立。任何放宽都需在看模型误差之前说明理由并形成新协议。

## 8. 必须遵守的研究规则

- Kd-only；保留原值、单位、不等号和条件，pKd=-log10(Kd[M])。正有限等号值才进入点评价；删失值另存，不把 > 当成等号，不把空白当阴性。Ki/IC50/EC50 不直接替换 Kd。
- 排除 Davis 原始测量 DOI10.1038/nbt.1990、PMID22037378 及转载同测量。仅引用 Davis 方法并不等于转载 Davis 标签。
- 分别报告药物结构、实际蛋白序列、配对、测量来源重叠；不要把同基因、同参考全长、同名称当成同实验构建体。保留物种、isoform、突变、范围、标签、表达背景与处理状态。
- 去重依赖原始研究、实际结构和 assay 构建体；同 DOI 不代表每条记录同测量，不同 DOI 也不保证独立。不同温度/方法/构建体不任意平均，不挑最强值。
- 相似性阈值与输入映射须在评价前固定；当前描述性 Morgan 比较不等于已通过相似性准入。
- n=1 不自动无效，毫摩尔不自动非特异，竞争 Kd 不自动不等价。对旧报告中的“205 篇全部付费”“全库不可行”“100% 泄漏”等强结论重新核证，不照抄。
- 原始出处优先，数据库用于定位。当前 UniProt/PubChem/厂商页面只能证明当前参考资料，不自动证明历史实际样品。
- 明确区分已视觉核对、自动解析核对和独立人类审核。失败获取不证明材料不存在，未研究范围不写成完成。

## 9. 数据、工具与保护边界

训练数据目录：`D:\桌面文件\sci\output\dti-boundary-grouped-server-package-v1-20261010\boundary_grouped_cpu_v1\data`。

`pairs_metadata.csv` 共25772行，字段包含 drug_id、target_id、smiles、domain；`davis.csv` 包含 ID1、X1、ID2、X2、Y。训练集涉及55个药物、304个靶点。

旧 BindingDB 审核目录：`D:\桌面文件\sci\03_experiments\audits` 下的 `dti_kd_feasibility_20261006_v1`、`dti_kd_field_review_20261006_v1`、`dti_assay_link_review_20261006_v1`、`dti_primary_batch_review_20261006_v2`、`dti_open_original_acquisition_20261006_v1`。

旧文章子集有93710行，2490个正等号 Kd、160个不等号、91060个无Kd。`assay_evidence_pending.json` 包含2490条原始元数据、序列、方法描述、DOI定位，不是已准入清单。

RDKit2025.09.6已隔离安装在 `D:\桌面文件\sci\output\dti-independent-kd-identity-20261010\tooling`；复用时不要修改项目训练依赖。Python文件操作和科学文本输出可用 `python -X utf8`。读取 XLSX 使用只读方式；不改来源文件。工作区已有其他用户改动，不重置、不覆盖。

受保护文件清单与基线摘要：`D:\桌面文件\sci\output\dti-independent-kd-admission-20261010\protected_inputs.json`，共30项。阶段结束核验全部摘要不变；任何意外变化须报告，不能通过更新基线掩盖。

## 10. 交付要求与验收

下一阶段建议新建目录：`D:\桌面文件\sci\output\dti-gemini-independent-kd-followup-20261010`，若已存在则创建新的阶段子目录，不覆盖前轮结果。

至少交付：

1. 中文研究报告：范围、已解决项、未解决项、正式准入数、结论边界与下一步。
2. 逐条 decisions.csv：record_id、原始研究、化合物、实际构建体、数值/单位/关系、温度/方法、证据定位、重叠、状态、理由。待定也要逐条写出缺失什么。
3. 原始来源快照与 source_manifest.json：来源URL、取得时间、状态、SHA256、失败原因；不保存凭据/令牌。
4. verification.json：范围覆盖、数值复核、重复和身份检查、保护文件摘要、是否加载/训练/预测、人类审核状态。
5. 本阶段输出文件摘要清单与可复核 ZIP；清楚注明哪些工具缓存不打包。

只有实际读到验证输出后才能称完成。若正式准入仍为0，应交付具体阻塞清单；不要只重复“证据不足”。若取得合格小队列，也不能因样本少就宣称模型广泛泛化成立。

## 11. 已有资料包

前三轮包位于 `D:\桌面文件\sci\output`：

| 包名 | SHA256 |
|---|---|
| dti-independent-kd-admission-20261010-review.zip | 804d703d1a1b25eb939292e3cb90372b7c7d96056313632bbc8b7366a593b9a8 |
| dti-independent-kd-identity-20261010-review.zip | 6f8217a8c7c14b458191277e8ac5525b06c1ffb7343dcdc0e7a887484bdd8641 |
| dti-independent-kd-construct-20261010-review.zip | 96807fdd5b261d453137e38b41b6f9ade794b347202b6e060ca037df62143719 |

第四轮资料包：`D:\桌面文件\sci\output\dti-independent-kd-direct-review-20261010-review.zip`，包含本任务书副本、九条结论、原始来源、视觉核对图片及验证结果。摘要在同目录的 `.zip.sha256.txt` 中。

本任务书是接手导航和范围约定；正式数据结论仍以原始证据及可复核的逐条记录为准。
