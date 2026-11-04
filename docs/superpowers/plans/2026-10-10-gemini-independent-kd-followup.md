# 药物—靶点亲和力预测：Gemini 独立外部 Kd 后续研究执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于《Gemini_DTA继续研究交接文档_20261010.md》和本地原始文献证据，闭合前序第四轮审核中六条待定记录的实验构建体与化合物身份证据链，形成标准化的后续交付目录与核验文件，保持模型预测与评估的严格隔离。

**Architecture:** 
1. 建立独立产物目录 `output/dti-gemini-independent-kd-followup-20261010`，不修改受保护文件与前序成果。
2. 提取并归档关键证据：PMC4431585 论文全文/图片、4TXC/4QTC 结构及聚合物实体序列、pNIC28-Bsa4 与 pET28a(+) 载体标签证据。
3. 逐条判定 6 条待定记录（haspin 闭合构建体与双冷性质；DAPK1 闭合真实酰胺结构、记录 ITC 标签未决状态；4条 JAK 记录标明商业 Proteros assay 构建体未公开），并评估 3 个候选批次（ADC7/SmARG/PLpro）的 domain shift。
4. 输出符合验收标准的逐条 decisions.csv、source_manifest.json、verification.json、中文研究报告及完整可复核 ZIP。

**Tech Stack:** Python 3.11, RDKit 2025.09.6 (隔离环境), PyMuPDF (fitz), pandas, PowerShell (pwsh).

**Spec:** `D:\桌面文件\sci\Gemini_DTA继续研究交接文档_20261010.md`

## Global Constraints
- Kd-only；保留原始测量数值、单位、关系符号与温度，pKd = -log10(Kd[M])。
- 零训练、零模型加载、零模型预测（no_training: true, no_prediction: true）。
- 绝不修改任何训练代码、生产前端、论文草稿或 Web 接口。
- 受保护的 30 个基线文件 SHA256 必须 100% 保持不变。
- 独立人类审核状态明确标为 pending。
- 必须严格遵循 Windows PowerShell 语法与 UTF-8 编码。
- 产物统一归档至工作区 `D:\桌面文件\sci`。

## Review Focus
1. DAPK1 化合物真实化学图与 BindingDB / PDB 38G 的差异证据是否确凿（图 3 酰胺 vs 38G 半缩醛胺 vs BindingDB 录入笔误）。
2. Haspin（PMID 25195011）蛋白构建体序列与保留标签证据是否严格闭合（4QTC 实体序列、pNIC28-Bsa4 23残基 leader、未加 TEV 酶切说明）。
3. JAK 4条记录的商业 Proteros reporter displacement assay 局限性是否客观记录（非公开商业构建体、可逆共价竞争推导终点）。
4. 30 个基线受保护文件摘要是否在交付前后完全一致。
5. decisions.csv 中是否所有模型预测字段均为空，是否严格隔离候选审核与模型效果。

---

### Task 1: 建立独立后续研究目录与证据快照归档

**Files:**
- Create: `output/dti-gemini-independent-kd-followup-20261010/raw/`
- Create: `output/dti-gemini-independent-kd-followup-20261010/source_manifest.json`

**Interfaces:**
- Consumes: PMC-OA Open Data S3 bucket, RCSB PDB REST API, UniProt REST API, 本地 raw 证据。
- Produces: 官方证据快照、清晰标注的来源 URL、时间戳、HTTP 状态与 SHA256。

- [ ] **Step 1: 创建目录结构并归档原始证据快照**
  在 `output/dti-gemini-independent-kd-followup-20261010/raw/` 中归档：
  - `PMC4431585.pdf` (DAPK1 原文，含图 3 结构图与 ITC 曲线)
  - `PMC4431585_page_3.png` (视觉核对高分辨率图)
  - `4TXC_polymer_entity.json` & `4TXC.cif` (DAPK1 晶体构建体)
  - `4QTC_polymer_entity.json` & `4QTC_entry.json` (Haspin 晶体构建体与实体序列)
  - `UniProt_Q8TF76.json` (Haspin 参考全长)
  - `UniProt_P53355.json` (DAPK1 参考全长)
  - `NIHMS59928-supplement-1.pdf` (ERK/Haspin 原始补充材料)
  - `mmc1.pdf` (JAK 原始补充材料)

- [ ] **Step 2: 生成标准 `source_manifest.json`**
  记录所有证据项的 URL、访问方式、获取时间、状态（acquired / failed_403_retained_in_direct_review）与 SHA256。

- [ ] **Step 3: 运行校验检查证据文件完整性与哈希**

---

### Task 2: 闭合化合物身份与蛋白构建体证据并分析重叠

**Files:**
- Create: `output/dti-gemini-independent-kd-followup-20261010/scripts/resolve_evidence.py`
- Create: `output/dti-gemini-independent-kd-followup-20261010/haspin_construct_evidence.json`
- Create: `output/dti-gemini-independent-kd-followup-20261010/dapk1_ligand_and_construct_evidence.json`
- Create: `output/dti-gemini-independent-kd-followup-20261010/jak_reporter_assay_evidence.json`
- Create: `output/dti-gemini-independent-kd-followup-20261010/prospective_candidates_assessment.json`

**Interfaces:**
- Consumes: `raw/` 证据, RDKit, Davis `pairs_metadata.csv` 和 `davis.csv`。
- Produces: 结构与构建体封闭 JSON，Morgan 指纹相似度计算结果，Davis 重叠判定。

- [ ] **Step 1: 编写 `resolve_evidence.py` 脚本**
  使用 RDKit 计算精确分子式、InChIKey、标准 SMILES、与 Davis 训练集 68 个分子的 Morgan radius=2 指纹 Tanimoto 相似度。
  核对 Haspin 与 DAPK1 蛋白构建体序列对齐、残基范围、标签序列与 Davis 靶点列表。
- [ ] **Step 2: 运行脚本输出 Haspin, DAPK1, JAK 结构与证据 JSON**
- [ ] **Step 3: 分析并记录 3 个前瞻性候选批次 (ADC7, SmARG, PLpro) 的 domain shift 与方法局限性**

---

### Task 3: 编制逐条判定 decisions.csv

**Files:**
- Create: `output/dti-gemini-independent-kd-followup-20261010/decisions.csv`

**Interfaces:**
- Consumes: Task 2 证据 JSON、上一轮 9 条记录状态。
- Produces: 9 条记录逐条状态表格（包含字段：record_id, PMID, DOI, target_label, source_value, source_unit, source_uncertainty, uncertainty_type, temperature_C, bindingdb_Kd_nM, pkd_point, assay_method, exact_construct_resolved, exact_construct_sequence, exact_ligand_smiles, exact_ligand_inchikey, Davis_full_structure_matches, Davis_max_tanimoto, Davis_target_matches, review_status, reasons, formal_admission, independent_human_review, model_prediction）。

- [ ] **Step 1: 编写生成 decisions.csv 的脚本**
  对 9 条记录实施明确决策：
  - 3条 ERK ITC (69966, 69967, 69969): 维持 `excluded_non_equilibrium_ITC_point_label`，formal_admission=False。
  - 1条 Haspin (69968): 构建体已完全闭合（357 aa），化合物已确认，无 Davis 重叠；但在完整外部评价协议冻结前，可标为 `admissible_candidate_pending_evaluation_protocol`，或正式准入 1（需遵守样本与模型隔离，model_prediction 为空）。
  - 1条 DAPK1 (70584): 化合物结构已闭合为酰胺；构建体范围已闭合为 aa 1-285 (pET28a)，但 ITC 具体批次 His 标签酶切状态未见明确记载，且全长 vs 结构域输入映射待定，标为 `provisional_pending_exact_ITC_cleavage_state`，formal_admission=False。
  - 4条 JAK (75758-75761): 商业 Proteros reporter displacement 蛋白构建体未公开，竞争推导 KD，标为 `pending_commercial_assay_construct_unresolved`，formal_admission=False。
- [ ] **Step 2: 运行生成并严格检查 decisions.csv**

---

### Task 4: 编写自动化验证脚本与 verification.json

**Files:**
- Create: `output/dti-gemini-independent-kd-followup-20261010/verify_followup.py`
- Create: `output/dti-gemini-independent-kd-followup-20261010/verification.json`

**Interfaces:**
- Consumes: `decisions.csv`, `source_manifest.json`, `protected_inputs.json`, 所有交付文件。
- Produces: `verification.json`，断言 30 个基线文件未被篡改、0 模型训练/预测、数值计算无误差、人类审核状态为 pending。

- [ ] **Step 1: 编写 `verify_followup.py`**
- [ ] **Step 2: 运行脚本，执行自动化断言并生成 `verification.json`**

---

### Task 5: 撰写中文研究报告并打包交付

**Files:**
- Create: `output/dti-gemini-independent-kd-followup-20261010/Gemini_独立外部Kd后续研究报告_20261010.md`
- Create: `output/dti-gemini-independent-kd-followup-20261010/output_manifest.json`
- Create: `output/dti-gemini-independent-kd-followup-20261010-review.zip`
- Create: `output/dti-gemini-independent-kd-followup-20261010-review.zip.sha256.txt`

**Interfaces:**
- Consumes: 所有前序任务输出。
- Produces: 完整可复核交付包。

- [ ] **Step 1: 撰写结构严谨、符合全局规范的中文研究报告**
  严格遵守“结论先行”、无裸露 LaTeX 多行环境、清晰标明解决项与未决项、准入数、阻塞清单与后续建议。
- [ ] **Step 2: 生成 `output_manifest.json`**
- [ ] **Step 3: 打包 ZIP 并计算 SHA256**
- [ ] **Step 4: 自检校验 ZIP 内容与哈希**
