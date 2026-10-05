"""Reports are rendered from the same audited rows and summary as CSV/JSON."""


def render_report(summary, molecules, observations, pool):
    c = summary['counts']
    rows = []
    for m in molecules:
        if not m['source_reviewed']:
            continue
        assays = [a for a in observations if a['candidate_id'] == m['candidate_id']]
        details = '; '.join(f"{a['endpoint']}: {a['raw_value'] or '未取得'} {a['unit']}，{a['target']}，位置 `{a['source_location']}`" for a in assays)
        rows.append(f"| {m['name']} | {m['sequence'] or '待确认受测构建体序列'} | {details} |")
    return f"""# HC50 与外部候选证据修复报告 v2

生成时间：`{summary['generated_at']}`；原正式协议：`{summary['protocol_id']}`；输入摘要：`{summary['input_manifest_sha256']}`。

## 当前结论

原正式双任务保持 **blocked**。已核查人红细胞 HC50 为 **{c['verified_human_hc50']} 条**；完整准入外部候选为 **{c['eligible_external']} 条**。这是一轮代理原文复核，未完成独立人工审批。模型 fit 为 0；没有修改正式研究状态。

## 范围和统计

- 本轮没有重新联网检索；修复已有五份 XML 和候选清单。历史检索响应和命中数量没有重新验证，见 search_log.csv。
- 候选记录 {c['candidate_records']}；非空序列种类 {c['distinct_nonempty_sequences']}；原文已确认序列 {c['primary_sequence_verified']}；受测序列缺失 {c['missing_sequence']}。
- 待原文复核 {c['pending_primary_article_review']} 条，包含全部历史 DRAMP 和 DBAASP 线索；不能写成已经逐条复核原始测定。
- 测定/缺失端点记录 {c['assay_observations']} 条，不等于独立实验次数。
- 候选—开发集比较 {c['candidate_development_comparisons']} 对；候选内部比较 {c['candidate_internal_comparisons']} 对。缺失序列未参与比对。
- 对非空清单序列的暂定筛查：{c['provisional_inventory_homology_failed']} 条达到 ≥0.40；{c['provisional_inventory_homology_passed']} 条低于 0.40。未复核序列的结果是线索筛查，不证明正式科学隔离通过。
- 检出研究别名重叠 {c['alias_overlap_detected']} 条。其余仍待原始测量论文、别名和历史研究暴露复核；不把“未发现重叠”写成独立性通过。

## 五篇原文记录

| 对象 | 原文序列 | 端点、实验对象和位置 |
|---|---|---|
{chr(10).join(rows)}

Dermatoxin 和 Arg2MP-C 序列、MIC 均从原文表格提取；保留 Dermatoxin 全部三条 E. coli 测定。Arg2MP-C 使用兔红细胞。Han-Def1 的 E. coli 原文为 No effect，不补写有限 MIC；受测重组构建体序列尚未从归档资料确认。

## HC50 证据池与外部资格

Brevinin-1 E8.13：原文 HC50 41.87 µM，原文表 1 分子量用于估算质量浓度，约 105.90 µg/mL；MIC >24.8 µM，下界约 62.72 µg/mL、上界无穷。两项标签均为 unknown。质量定义未明确，转换仅作本次证据描述。合成方法报告 C 端酰胺化；Rana-box 为文中结构描述，本轮未独立确认共价配对。记录不具备原协议外部资格。

不能根据这轮有限审查推断全网不存在合格样本，也没有依据声明酰胺化占比 80%。待核实、原文未获取与明确不合格分别记录，不互相替代。

## 复现与下一步

README.md 包含固定输入摘要及命令。流水线拒绝任何已存在输出目录；新运行使用新目录。manifest.json 绑定输入、脚本、CSV、报告和 README。原 v1 与 MIC 冻结材料保留原样。

下一步是对 78 条待核实线索补齐原始测定表、化学身份、单位和原始研究归属，核实 Han-Def1 受测构建体序列及历史论文暴露。任何一个必要门禁未完成都不释放正式外部队列。
"""


def render_readme(summary):
    return f"""# HC50 审计修复 v2

当前结论：blocked；详情与限定范围见 report.md 和 audit_summary.json。生成时间 `{summary['generated_at']}`。

## 复跑

从项目根目录运行，输出必须不存在：

```powershell
python -B 03_experiments/audits/gemini_hc50_external_review_20261004_v2/scripts/evidence_audit.py --input-manifest {summary['input_manifest']} --input-sha256 {summary['input_manifest_sha256']} --output 03_experiments/audits/gemini_hc50_external_review_20261004_v2/reproduction_01
python -B 03_experiments/audits/gemini_hc50_external_review_20261004_v2/scripts/test_evidence_audit.py
```

## 产物

逐对象身份、原始观察、派生标签、HC50 已核实池、待核实/排除表、原始研究别名、历史暴露检查、全员比较、冲突、历史搜索声明、原文许可、机器摘要、报告、manifest 均在本目录。0 行准入表保留表头。

不训练模型，不修改原协议，不替代人工审批。原文未报告的条件和无法确认的序列保持缺失。候选线索序列筛查不等于正式独立性验收。
"""
