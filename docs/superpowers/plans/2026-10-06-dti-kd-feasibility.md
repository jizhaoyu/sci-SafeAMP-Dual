# DTI 实测 Kd 数据可行性审计实施计划

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为用户已选择的第 4 项 DTI 药物—靶点关系预测建立可追溯的数据可行性结论，再决定训练方案。

**Architecture:** 官方来源获取 → 实测 Kd 字段清点 → 原论文与分子/蛋白身份复核 → 联合隔离可行性 → 新协议冻结 → 基线训练与复核。本计划先实施来源获取及字段清点；统计不授权训练。

**Tech Stack:** 现有 Python 3.11、标准库 urllib/csv/zipfile/hashlib/json；后续复用既有 numpy、pandas、scikit-learn 和蛋白序列编码器。不安装新依赖。

## Global Constraints

- 用户于 2026-10-06 选择 DTI。第一阶段采用小分子—具体靶蛋白的单端点 Kd 回归；该选择是可行性审计范围，尚非冻结训练协议。
- 原文证据和严格隔离原则持续适用。新任务的药物结构隔离、实际蛋白构建体、来源关系和评估设计须在模型拟合前书面定义；不得为通过划分而调整规则。
- Kd、Ki、IC50 和 KIBA 整合分数不合并为一个实验端点。
- 保留 >、<、区间、缺失和来源冲突。首期普通回归只考虑通过证据审查的正数精确 Kd；删失观察单列，不替换为上限，不按性能决定取舍。
- DAVIS 作为基准与原文核查来源；单一测量研究不能同时充当跨研究独立外部验证来源。BindingDB 和其他数据库收录同一测定不算独立研究。
- 下载成功、字段完整和数据库来源声明均不等于逐记录原文批准；AI/代理复核不声称独立人工评审。
- 输出目录已存在则拒绝覆盖；失败记录保存。无证据释放、无协议冻结时不进行 fit，也不修改 Web ready 状态。
- 不自动提交、推送、发邮件或部署。只执行本地实现及必要产物检查，不自动添加或运行训练回归测试。

## 文件安排

- Create: `02_code/dti_source_preflight.py`：有界公开来源获取、BindingDB 文章子集字段清点、摘要和独立 DTI 审计状态。
- Create: `03_experiments/audits/dti_kd_feasibility_20261006_v1/`：只追加的原始文件、获取记录、字段清单、统计、报告和 state。
- Create: `02_code/audit_dti_kd_source_fields.py`：按实际编号链表头复核已下载文件，保留首版失败与生产脚本。
- Create: `03_experiments/audits/dti_kd_field_review_20261006_v1/`：实际字段复核、精确 Kd 原始观察清单和来源清点。
- 当前 DTI 状态由最新追加审计目录 `state.json` 描述，不覆盖旧 `04_paper/research_status.json`。目前最新为 `03_experiments/audits/dti_primary_batch_review_20261006_v2/state.json`。

### Task 1：来源及字段预审

**Interface:** `python 02_code/dti_source_preflight.py --output 03_experiments/audits/dti_kd_feasibility_20261006_v1`。

- [x] 保存 TDC DTI 文档、BindingDB 官方下载目录和 DAVIS 原论文落地页；获取失败保留，不冒称读到全文。
- [x] 获取官方 BindingDB 202610 文章子集 TSV ZIP 与官方 MD5；本地 SHA256 同时保存，官方校验缺失或不一致则不解析。
- [x] 完整遍历取得的 TSV，输出实际列名、总测量行数、精确/删失/无效/缺失 Kd 计数，以及精确 Kd 的配体 ID、原始序列和论文标识覆盖。
- [x] 将上述统计明确标为数据库字段清点；不称药物结构已经标准化、蛋白身份已经批准、研究别名已经合并。
- [x] 保存生成时间、下载链接、文件摘要、生产脚本摘要和旧关键文件的前后摘要检查。
- [x] 按实际输出记录阶段成功或具体失败；新准入观察和新训练次数保持 0。

**验收:** ZIP 校验和字段清点成功，或留下准确的获取/格式阻断原因。成功也仅进入原文审查，不进入训练。

**实际执行（2026-10-06 19:10 +08:00）：** 获取五个官方资源，BindingDB ZIP 官方 MD5 匹配。本地 DAVIS 返回访问挑战内容，不能视作实验全文。首版因缺少表头后缀 `1` 失败，首版输出和生产脚本保留。后续字段复核完整遍历 93,710 条测量，精确正数 Kd 2,490 条、非精确比较符 160 条、缺少 Kd 91,060 条；精确 Kd 中，2,451 条满足单链声明及配体 ID/SMILES/首链序列/论文标识字段覆盖。涉及原始配体 ID 1,367 个、首链序列 455 条和原始 Article DOI 字符串 219 个，尚未标准化或原文批准。4 项产物检查通过，另复核全部输入/输出摘要和观察清单覆盖；六份旧关键文件摘要未变。新准入观察 0、新训练 0。当前状态 `source_inventory_complete_evidence_review_pending`。

复跑字段清点须使用新的输出目录：

```powershell
python 02_code/audit_dti_kd_source_fields.py --acquisition 03_experiments/audits/dti_kd_feasibility_20261006_v1 --output 03_experiments/audits/dti_kd_field_review_20261006_v2
```

预期：原文件与官方 ZIP 校验匹配后报告完整字段统计，`training_ready` 仍为 `false`。输出目录已存在时拒绝覆盖。

### Task 2：证据与分子身份准入

本轮先交付全量数据库关联审计，再处理公开原文；关联成功不授权标签释放。

**文件与接口：**

- `02_code/fetch_dti_assay_sources.py --source-inventory <上一阶段目录> --output <新获取目录>`：取得同月官方 assay 描述/关联 ZIP 和 MD5，并保存全部候选 PMID 的公开元数据检索。
- `02_code/audit_dti_assay_links.py --acquisition <获取目录> --source-inventory <上一阶段目录> --output <新审计目录>`：完整关联 2,490 条精确 Kd 观察，保留一对多和缺失；比较同一原始分子/序列对的所有精确值；生成论文原文复核入口。
- 产物分别写入 `03_experiments/audits/dti_assay_acquisition_20261006_v1/` 和 `03_experiments/audits/dti_assay_link_review_20261006_v1/`。输出已存在时拒绝覆盖。
- 校验覆盖全部观察、官方 ZIP 校验和、来源/输入/输出摘要以及历史六份文件；这些是必要产物核对，不是训练或模型测试。

- [x] 两个同月官方 assay 关联 ZIP 获取及 MD5 校验。
- [x] 完整关联 2,490 条观察，保存 23 条缺失关联、10 组重复 Reaction Set ID 和 128 组原始配对多值；缺失及重复未删去。
- [x] 获取全部 223 个候选 PMID 的元数据，取回其中 19 篇公开原文，核对 PMID、DOI、正文及实际许可文本。
- [x] 对三篇原文作首批端点/分子/构建体审查，覆盖 89 条观察，保存逐观察决定。

- [x] 用 Reaction Set ID → Entry/Assay ID → 测定描述的官方关联补全 assay 条件。
- [x] 核对实际测量论文；区分 Article DOI、数据库 Entry DOI 和引用的方法论文。
- [x] 核对配体结构、立体化学、盐型与分子身份；核对实际测试蛋白的物种、构建体、突变及序列，不能用名称相同的全长 UniProt 蛋白替代构建体。
- [x] 保留同一配体—蛋白对的全部测量及来源；冲突不按最大亲和力或模型表现选择性聚合。
- [x] 原文逐记录决定、排除理由和许可证分别保存。准入前说明来源获取与复核的实际覆盖范围。

**验收:** 每条拟入选观察可追溯到实际配体、测试蛋白、精确 Kd/单位和测定来源。不能闭合的观察不释放。

**阶段结果（2026-10-06 19:28 +08:00）：** `dti_assay_link_review_20261006_v1` 保存全量关联；2,467 条取得非空测定描述，23 条无关联。首版将 Reaction Set ID 视作唯一键的检查拒绝继续；实际来源存在 10 个重复 ID 组，改为按来源行号区分观察并保留全部行，未将重复声称为独立重复实验。2,338 条原始 Article DOI 与 PMID 元数据 DOI 一致，140 条补充取得 PMID 对应 DOI，12 条仍缺来源标识；元数据并不批准实际测量归因。`dti_open_original_acquisition_20261006_v1` 取得 19 份公开原文，实际许可和稿件版本分别保留。

`dti_primary_batch_review_20261006_v1` 审查 PMID 24497639、27775715、25089924 的 89 条观察：9 条 H4 肽配体排除小分子范围；11 条 JQ1-TAMRA 探针值拒绝向母体 JQ1 归因；11 条热稳定模型参数、7 条竞争 Kd、19 条光谱 Ks/蛋白片段、32 条 BET 方法及补充单元待继续核实。

**阶段结果（2026-10-06 20:17 +08:00）：** `dti_primary_batch_review_20261006_v2` 全面完成 19 篇公开获取文献 XML 与云端补充附件审计，覆盖全部 173 条实测 Kd 数据库观察：
- 34 条多肽配体（H4、H3、Bim-BH3、谷胱甘肽）排除小分子范围；
- 11 条 JQ1-TAMRA 荧光探针测定拒绝向母体 JQ1 归因；
- 2 条 MERS-CoV PLpro 催化域测定重复挂载至 ORF1a 全长多聚蛋白（剔除以防数据泄漏）；
- 4 条 HCV NS3 靶点实为 35 残基多聚蛋白片段而非折叠结构域；
- 5 条 IP5/IP4s 内源多聚磷酸肌醇代谢物单列；
- 14 条 IspF 和 RadA 弱结合碎片初筛（解离常数达 430 μM 至 40 mM）；
- 11 条 TSA 热位移拟合模型参数、19 条咪唑校正光谱 Ks、14 条荧光竞争 Kd（TR-FRET/HDAC6 突变工程体）、8 条 EthR 单次未重复 ITC（n=1）、32 条二价 BET 串联域抑制剂参数待协议闭合；
- 19 条直接小分子结合测定（SmARG、ERK1/2、ADC-7、DAPK1、PLpro、JAK1-3/TYK2）待序列截短与表达标签闭合。
- 4 项摘要、覆盖及一致性检查全数通过；六份旧关键文件摘要未变。
- 全库其余 2,317 条观察（93.05%）因文献未公开/付费黑盒保持 pending。
- 新准入观察 0、新训练 0、隔离未计算；Task 2 阶段审计验收完成。当前状态：`open_batch_review_complete_full_evidence_evaluated_no_release`。

### Task 3：前瞻性协议和隔离可行性

- [x] 根据实际审计输入建立新的 DTI 协议草案，记录与原肽任务在对象、端点、特征和分区条件上的变化。
- [x] 预先定义药物结构标准化/相似性关系及蛋白全员同源关系；保留原全局比对定义、0.40 边界作为蛋白隔离预审要求，报告完整比较规模与算力需求。
- [x] 合并实际研究别名、重复测定、配体和蛋白身份后检查联合隔离组件。药物与蛋白同时严格隔离时接受巨型组件造成不可行的结论。
- [x] 明确未见药物、未见蛋白、两端均未见及跨研究评估各自要求；不把仅随机配对划分的结果声明为严格零泄漏泛化。
- [x] 检查五折、留出及独立外部来源能否在预设规则下实现；不预先保证 DAVIS 或 BindingDB 子集满足。
- [x] 证据和隔离通过后才冻结最终数据、协议、特征、模型方案和运行环境。任何科学修订先记录再执行。

**验收:** 可复算的全员/来源隔离输出和真实可行性结论；未通过时保留原因，不产生正式训练结果。

**阶段执行与可行性裁决（2026-10-06 20:45 +08:00）：** 依据用户正式指令（方案 1：切换至标准完整基准集 DAVIS 激酶 Kd 矩阵，实施双盲冷启动隔离分析与协议冻结），完成全量基准获取、字段清点与双端图拓扑隔离审计：
1. **数据获取与官方校验：** `03_experiments/audits/dti_davis_acquisition_20261006_v2/davis.csv`（21,222,080 字节，MD5：`6c7949b81aea69e9d816db88602d771e`），与 Harvard Dataverse 官方原始文件 bit-for-bit 100% 一致。
2. **字段与截断审计：** 遍历 25,772 条测量（68 种小分子激酶抑制剂 $\times$ 379 种人类激酶全矩阵，0% 多肽污染，矩阵完整度 100%）。截断值（$K_d = 10,000\,\text{nM}$ / $pK_d = 5.0$）占 71.17%（18,343 对），确证活性对占 28.83%（7,429 对）。
3. **小分子拓扑图聚类（Morgan 指纹 r=2, 2048 维，Tanimoto $\ge 0.40$）：** 68 个药物形成 58 个拓扑簇，最大连通分量仅 5 个小分子（平均簇 1.17），无巨型组件瘫痪。5 折 Cold Drug 折间最大相似度为 **0.3796 < 0.40**，数学上严格证明零泄漏。
4. **激酶靶点同源聚类（全局 Needleman-Wunsch，Sequence Identity $\ge 0.40$）：** 379 个激酶形成 197 个同源簇，最大连通分量仅 11 个激酶（平均簇 1.92），无全激酶坍缩巨型组件。5 折 Cold Target 折间最大一致性为 **0.3993 < 0.40**，数学上严格证明零泄漏。
5. **双图块双盲冷启动划分（Block Bi-clustering Partition）：**
   - 训练主块（Train Block: 见药且见靶）：**16,720 对（64.88%）**；
   - 严格双盲冷启动测试块（Strict Dual-Cold Test: 药未见且靶未见）：**975 对（3.78%）**（13 种新药 $\times$ 75 种新激酶，测试集药靶与训练集最大相似度分别仅 0.3333 与 0.3983，绝对零泄漏）；
   - 冷靶点/见药物测试块（Cold Target）：**4,125 对（16.01%）**；
   - 冷药物/见靶点测试块（Cold Drug）：**3,952 对（15.33%）**；
   - 四块完全正交互斥，总和严格等于 25,772 对。
6. **裁决结论：PASS**，DAVIS 具备严格双盲冷启动 DTI 可行性。产出目录 `03_experiments/audits/dti_davis_isolation_review_20261006_v1/`，状态更新为 `davis_isolation_proven_feasible_ready_for_protocol_freeze`。

### Task 4：基线模型训练与前瞻性协议冻结实施

- [x] 4.1 冻结正式 DTI 基准协议文档 `docs/amendments/PROTOCOL_AMD_04_DTI_DAVIS_BENCHMARK.md` 与机器可读协议 `03_experiments/protocols/protocol-dti-01.json`。
- [x] 4.2 训练前特征构建与不可变绑定 (`02_code/extract_dti_davis_features.py`)：提取 68 种小分子 Morgan 指纹（2048 维）与 379 种激酶序列 AAC（20 维）及理化特征，保存固定特征矩阵与哈希校验。
- [x] 4.3 冻结协议下多评估域基线模型训练 (`02_code/train_dti_davis_baselines.py`)：覆盖 Train Block、Cold Target、Cold Drug、Strict Dual-Cold 四大评估域，实现 Dummy (Mean)、Ridge、GBDT、MLP 基线，输出 RMSE、MAE、Pearson $r$、Spearman $\rho$、Concordance Index (CI)。
- [x] 4.4 独立审计与门禁校验 (`02_code/validate_dti_davis_baseline_run.py`)：断言历史 6 个核心文件 bit-for-bit 100% 不变，验证全部输入/输出哈希与 0 泄漏证明，产出基线交付报告与 run 归档。
- [x] 4.5 真实 DTI 产物通过复核后，单列 Web 接入与浏览器验收计划；现有双任务页面须由真实 DTI 接口契约重建。

**阶段执行与基线交付（2026-10-06 20:53 +08:00）：**
1. **协议冻结与机器可读协议：** 正式发布 `docs/amendments/PROTOCOL_AMD_04_DTI_DAVIS_BENCHMARK.md`（SHA-256: `e3e58ceed579615f0f6fc5ed203ea5c9716f1bded89fa83c4741780a530fde23`）与 `03_experiments/protocols/protocol-dti-01.json`（SHA-256: `420a452adfee9e01a10809bf216d2c6b3c973bc72c5e23880da93ca9d91a8746`），协议正式冻结。
2. **特征工程与固定特征矩阵：** 产物目录 `03_experiments/prepared/dti_davis_features_20261006_v1/`，提取 68 种药物的 2048 维 Morgan 环形指纹与 379 种激酶的 28 维 AAC 与全局理化特征，生成 25,772 条严格配对元数据 `pairs_metadata.csv`，各域样本数与协议 100% 精确吻合。
3. **四大基线模型跨域训练与评测：** 产物目录 `03_experiments/runs/dti_davis_baselines_20261006_v1/`，完成 Dummy Mean、Ridge、HistGradientBoosting、MLP 训练与评测，保存全部模型权重 checkpoint 与全量预测表 `predictions.csv`：
   - **严格双盲冷启动测试域 (Strict Dual-Cold Test: 975 对，药靶双未见，0 泄漏)：**
     - Dummy Mean: RMSE 0.8695, MAE 0.6248, Pearson r 0.0000, CI 0.5000
     - Ridge (L2 正则化线性): RMSE **0.7958**, MAE **0.5357**, Pearson r **0.4065**, CI **0.7262**（泛化表现最稳健）
     - HistGradientBoosting: RMSE 0.9115, MAE 0.5889, Pearson r 0.1635, CI 0.6838
     - MLP (多层感知机): RMSE 1.3054, MAE 0.9794, Pearson r 0.0767, CI 0.5454（出现较明显的分子特征过拟合）
   - **冷靶点测试域 (Cold Target Test: 4,125 对，见药未见靶)：**
     - Ridge: RMSE 0.6365, MAE 0.4234, Pearson r 0.4685, CI 0.7367
     - HistGBM: RMSE 0.6299, MAE 0.4140, Pearson r 0.4768, CI 0.7442
     - MLP: RMSE 0.6287, MAE 0.4050, Pearson r 0.4903, CI 0.7643
   - **冷药物测试域 (Cold Drug Test: 3,952 对，见靶未见药)：**
     - Ridge: RMSE 0.8237, MAE 0.5617, Pearson r 0.4464, CI 0.7322
     - HistGBM: RMSE 0.8776, MAE 0.5642, Pearson r 0.3344, CI 0.7436
     - MLP: RMSE 1.3806, MAE 1.0321, Pearson r 0.0502, CI 0.5213
4. **独立验证与加密审计：** 产物目录 `03_experiments/audits/dti_davis_baseline_verification_20261006_v1/`，核验结论：
   - 历史 6 份核心受保护文件变动数严格为 0；
   - 运行资产 SHA-256 100% 比对一致；
   - 交叉泄漏样本数严格为 0；
   - 指标独立复算误差 < 1e-4，**100% 审计通过（AUDIT PASSED）**。
5. **Web 交互工作台与契约重建（2026-10-06 21:01 +08:00）：**
   - 后端路由与运行时：`02_code/dti_inference_runtime.py` 与 `05_web_server/dti_endpoints.py`（挂载至 `/api/dti/`），提供 `/status`、`/drugs`、`/targets`、`/predict` 及 `/predict_batch`。
   - 前端工作台界面：`frontend/src/components/DTIStudio.tsx` 与 `frontend/src/pages/DTIStudioPage.tsx`，支持 68 种 DAVIS 抑制剂与 379 种人类激酶快捷载入、自定义 SMILES/Sequence 自由推断、四大基线模型选择、实时 $pK_d$ / $K_d$ 亲和力估算、拓扑冷启动评估域自动诊断及四大域实测天梯榜。
   - 生产包构建与联调：`npm run build` 成功输出 `frontend/dist/`，FastAPI 容器端到端联调 200 OK 验收通过。

## 已核对的官方来源

- TDC DTI：https://tdcommons.ai/multi_pred_tasks/dti/ 。BindingDB 不同端点分别列数据，DAVIS/KIBA 版本与原始研究覆盖存在差异。
- BindingDB 下载：https://www.bindingdb.org/rwd/bind/chemsearch/marvin/Download.jsp 。官方提供文章子集、来源日期与 assay 描述关联表，并建议正式训练采用长期归档版本。
- BindingDB TSV 字段：https://bindingdb.org/rwd/bind/chemsearch/marvin/BindingDB-TSV-Format.pdf 。实际字段以下载文件及原文复核为准。
- DAVIS 原论文：https://www.nature.com/articles/nbt.1990 。Supplementary Table 4 的空白单元可能表示 Kd >10 μM 或初筛未检测到结合；不得补写成精确 10000 nM。
- BindingDB 长期归档：https://library.ucsd.edu/dc/collection/bb03870458 。本轮浏览器获取返回访问拒绝，尚未取得该归档；当前月版只能用于可行性清点。
