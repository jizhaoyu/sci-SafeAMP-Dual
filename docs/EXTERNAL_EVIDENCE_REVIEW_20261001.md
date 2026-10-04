# 外部队列证据复核（2026-10-01）

## 复核依据与结论

输入为历史 `combined_v2/records.csv`、其 `raw/external_gold_standard.json` 及 `phase_d_blocked_combined_v2/evidence_audit.json`。对每条记录核对原始测定观察后，13 条外部记录均只有二值标签，无法从 *E. coli* MIC 或人红细胞 HC50 原始数值重推导标签。下表逐条记录处置；全部已从 `combined_v3_evidence_clean_20261001/records.csv` 排除，原快照保留作追溯。排除不表示该肽一定无相关生物活性。

| 记录 ID | 历史标称来源 | 目前缺口 | 处置 |
| --- | --- | --- | --- |
| `EXT_HemoPI-1_HP1_0234` | HemoPI-1 | 无原始 MIC/HC50 观察；使用 APD3 概述 DOI 作兜底 | 排除 |
| `EXT_APD3_AP00124` | APD3 | 无原始 MIC/HC50 观察 | 排除 |
| `EXT_APD3_AP00201` | APD3 | 无原始 MIC/HC50 观察 | 排除 |
| `EXT_UniProt_P02871` | UniProt | 无原始 MIC/HC50 观察；兜底 DOI | 排除 |
| `EXT_UniProt_P60709` | UniProt | 无原始 MIC/HC50 观察；兜底 DOI | 排除 |
| `EXT_UniProt_P68082` | UniProt | 无原始 MIC/HC50 观察；兜底 DOI | 排除 |
| `EXT_UniProt_P00695` | UniProt | 无原始 MIC/HC50 观察；兜底 DOI | 排除 |
| `EXT_UniProt_P62829` | UniProt | 无原始 MIC/HC50 观察；兜底 DOI | 排除 |
| `EXT_UniProt_P02452` | UniProt | 无原始 MIC/HC50 观察；兜底 DOI | 排除 |
| `EXT_UniProt_P01009` | UniProt | 无原始 MIC/HC50 观察；兜底 DOI | 排除 |
| `EXT_HemoPI-1_HP1_0411` | HemoPI-1 | 无原始 MIC/HC50 观察；兜底 DOI | 排除 |
| `EXT_HemoPI-1_HP1_0901` | HemoPI-1 | 无原始 MIC/HC50 观察；兜底 DOI | 排除 |
| `EXT_HemoPI-2_HP2_0544` | HemoPI-2 | 无原始 MIC/HC50 观察；兜底 DOI | 排除 |

不能用数据库类别补足实验端点。[HemoPI 原始方法论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC4782144/)说明 HemoPI-1 的阴性例来自 Swiss-Prot 随机肽；这一类别不等同于逐条测定的 HC50 阴性。历史文件把 `P02871` 命名为“Ubiquitin-frag”，但 [UniProt 原始条目](https://www.uniprot.org/uniprotkb/P02871/entry)将该 accession 标为蚕豆凝集素 Favin；该对应关系也不能作为肽段实测标签的依据。

## 现有独立候选复核

本地 DRAMP 快照中 10 条具人红细胞 HC50 信息的候选，在 `protocol-amd-02` 下与 417 条开发记录的全部 4,170 对比对结果见 `03_experiments/audits/dramp_amd02_20261001/all_pairs.csv`。每条候选的最高一致性为 0.421–0.962，均达到或超过 0.40；因此没有候选能进入严格隔离的外部队列。这是序列筛查结果，不能替代原始论文的测定核验。

## 取得新队列所需证据

每条新候选须保存独立来源的原始文件及 SHA-256、序列和修饰状态、可定位的原始实验研究、*E. coli* MIC 和/或人红细胞 HC50 的原始值、单位、测定条件。导入器从这些观察重推导可用标签，再检查与开发集的研究来源重合、所有序列对一致性和各分区两类实测标签。找不到原始测定、文献或独立性证据的记录继续排除；当前准备状态保持 `blocked`。
