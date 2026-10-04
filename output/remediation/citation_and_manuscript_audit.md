# SafeAMP-Dual 论文手稿与引用完整性审计报告 (Citation & Manuscript Audit)

**生成时间**：2026-09-29  
**执行模块**：`02_code/audit_references.py`  
**依据文档**：[`docs/SAFEAMP_DUAL_REMEDIATION_PLAN.md`](file:///D:/桌面文件/sci/docs/SAFEAMP_DUAL_REMEDIATION_PLAN.md) 第 10 节与 Task 7 规范  
**审计结论**：**手稿属于方案协议草案 (Protocol Draft)；引用元数据已修正但正文论点支撑未人工审校；作者及基金声明未验证；严禁标记为投稿就绪 (`publication_ready = false`)。**

---

## 一、参考文献元数据与 DOI 审计结果 (Citation Audit)

对 `04_paper/references.bib` 中全部 34 篇文献通过 Crossref API 官方元数据进行严格核对（产物见 `04_paper/evidence/reference_audit.json`）：

### 1. 总体概况
* **总参考文献数**：34 篇
* **官方 Crossref 元数据匹配成功 (`metadata_match_pending_claim_review`)**：29 篇 (85.3%)
  * 包含已修正的历史错配 DOI：
    * `kang2019dramp`：已从错误的 SEAweb DOI 修正为 Scientific Data 官方 DOI `10.1038/s41597-019-0154-y`。
    * `chung2020dbamp`：已从错误的 PATRIC DOI 修正为 NAR 官方 DOI `10.1093/nar/gky1030`。
* **无 DOI / 需原始文献手工审验 (`no_doi_requires_primary_source_check`)**：5 篇 (14.7%)
  * `who2021amr`：WHO 报告无固定 DOI。
  * `vaswani2017attention`：NeurIPS 经典 Transformer 论文。
  * `pedregosa2011scikit`：JMLR scikit-learn 论文。
  * `paszke2019pytorch`：NeurIPS PyTorch 论文。
  * `loshchilov2019decoupled`：ICLR AdamW 论文。
  * `kingma2015adam`：ICLR Adam 优化器论文。
* **存在元数据冲突或抓取失败 (`metadata_mismatch` / `lookup_failed`)**：**0 篇 (0%)**。
* **所有声明是否获得正文论点审验 (`all_claims_verified`)**：**False**（客观记录：机器检索仅核验了标题/作者/年份元数据，具体论文是否支持正文所引用的具体生物学观点，需待责任作者逐条人工复核）。

---

## 二、手稿数值与科学一致性审计 (Numerical Consistency Audit)

依据 `04_paper/evidence/consistency_manifest.json` 与 `04_paper/manuscript.tex` 进行逐字对照：

1. **样本数量一致性**：
   * 论文正文明确声明数据来源于 417 条真实 DBAASP 记录 (`\section{Current feasibility assessment}`：`The pilot contains 417 experimental source records`)。
   * 表格如实汇报：
     * *E. coli* MIC：阳性 253、阴性 138、未测 26。
     * Human RBC HC50：阳性 18、阴性 44、未测 355。
   * 无任何捏造或拼接更大样本集的表述。
2. **算法定义与同源隔离一致性**：
   * 论文明确写明使用全局 Needleman–Wunsch (+2/-1/-2, `matches / min(L1, L2)`)，并明确指出 **“This algorithm is explicitly not CD-HIT”**。
   * 如实披露聚类结果：417 条序列全部聚为一个单一连通分量 (`The current data form 1 connected component(s), with 417 sequences in the largest component`)。
3. **模型性能数字审计**：
   * 正式论文完全**不包含任何伪造的测试集指标、ROC-AUC、AUPRC、MCC 或 P 显著性数值**。
   * 论文标题与摘要明确定义为方案描述与数据可行性评估 (`SafeAMP-Dual: A Reproducible Protocol...`)，明确指出“The present pilot fails the required partition checks; consequently, training and publication-result generation are blocked.”。

---

## 三、作者、单位、基金与道德声明审计 (Declarations Audit)

依据 `04_paper/evidence/declarations.json` 进行合规性排查：

* **作者身份与排序 (`authors`, `author_order_confirmed`)**：未验证 (`unverified` / `false`)，手稿标为 `Authorship and affiliations not yet verified`。
* **单位署名 (`affiliations`)**：未绑定，严禁使用虚构机构。
* **资助基金 (`funding`)**：`null`，严禁编造任何基金编号。
* **利益冲突 (`competing_interests`)**：`null`，未申报。
* **伦理审查 (`ethics_applicability`)**：`null`，待作者根据数据来源性质判断是否需要免责声明。
* **AI 协助声明 (`ai_assistance`)**：透明披露为“Code remediation and protocol drafting; accountable author review and venue-specific disclosure pending”。
* **人工责任签署 (`human_approval`)**：**False**。

---

## 四、Fail-Closed 发布门禁与投稿阻断结论

当前论文绝对**不可**用于投稿或对外宣称成果。系统通过以下规则实行强制阻断：

```text
run_manifest.status == "completed"             --> FAIL (当前 status: blocked)
dataset_manifest.status == "validated"         --> FAIL (当前可行性阻断)
publication_ready == true                      --> FAIL (当前强制 false)
formal_results_available == true               --> FAIL (当前强制 false)
reference_audit.all_claims_verified == true    --> FAIL (当前 claim_support 未复核)
```

**结论**：`02_code/publication_artifacts.py` 已激活防护，若有调用将直接触发异常中断，确保无虚假结果外溢。
