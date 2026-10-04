# 正式双任务外部候选队列穿透式审查与科学判定报告

**审查时间**：2026-10-03T02:52:31.568116+00:00 (UTC)
**审查协议**：`protocol-amd-03` (前瞻性双任务外部队列系统性筛查与穿透式审计协议)
**开发集基线**：417 条 DBAASP 开发记录 (SHA-256: `ccec346bf88c6d3b2da57f058019fb10305019de5dca4ef3402949931ac71f37`)

## 一、核心审查结论与科研诚信判定

> [!IMPORTANT]
> **核心结论**：
> 1. **成功确证 1 条黄金标准合格分子**：牛蛙天然分离多肽 **Catesbeianin-1**（DRAMP20968，PMID 28258530，序列 `MMRVMRRKTKVIWEKKDFIGLYSID`）。经专利（CN101724632A）与质谱分子量（实测 3144.8 Da，理论游离酸 3144.85 Da）严格闭环确证为未修饰游离羧酸（`-COOH`），与 417 条开发集记录最大 Needleman-Wunsch 一致性为 **0.3333**（严格 $< 0.40$），无二硫键，标准株 *E. coli* ATCC 25922 实测 MIC = 3.1 μg/mL（`amp = 1`），人红细胞实测 $	ext{HC}_{50} = 300\ \mu	ext{g/mL}$（`hemo = 0`）。
> 2. **主流候选的文献穿透否决（真假游离酸鉴别）**：Cell 2018（SLAY 系列 14 条）与 Fish Shellfish Immunol 2016（鲑鱼 cathelicidin 衍生肽 5 条）在二次数据库中虽标示为 Free，但经原文穿透核查其化学合成方法，均明确使用 **Rink amide 树脂** 合成，产物全部为 C 端酰胺（`-NH2`），直接被门禁 1 否决；其余候选存在动物红细胞、文献重叠或缺少定量 HC50 问题。
> 3. **正式科研状态严格维持 `blocked`**：由于当前仅有 1 条合规分子（$N = 1$），无法构成具备双任务正负类完备性（正类与负类均存在）的统计学外部评估集，无法计算 MCC、AUROC 等评估指标。**系统绝不为了解除阻断而伪造数据或放宽同源阈值，`04_paper/research_status.json` 继续严格维持 `blocked`！**

## 二、穿透审查候选分子分布与统计

| 专家审查状态 (Expert Status) | 数量 (条) | 核心科学原因 |
|---|---|---|
| `eligible_verified_tier1_candidate` | **1** | 质谱与专利闭环确证游离酸，全员 NW < 0.40，标准 MIC + 人 RBC HC50 |
| `rejected_terminal_amidation` | 14 | 原文采用 Rink amide MBHA 树脂合成，实为 C 端酰胺 (-NH2) |
| `rejected_terminal_amidation_and_label_diversity` | 5 | Rink amide 树脂合成，且溶血未定量 HC50，缺乏正负类多样性 |
| `rejected_fatty_acylation_or_unconfirmed_free_acid` | 6 | N 端肉豆蔻酸/月桂酸脂肪酰化修饰，或缺少游离酸证明 |
| `rejected_study_overlap_and_non_human_rbc` | 1 | 文献与开发集引文库重叠，且测定靶标为羊红细胞 (Sheep RBC) |
| `rejected_nanoparticle_conjugation_or_unquantified_hemo` | 4 | 偶联纳米银颗粒，或仅有单一低浓度溶血百分比 |
| `rejected_or_unverified_primary_conditions` | 8 | 其他测定条件不符 |

## 三、已确证唯一黄金候选档案 (Verified Golden Candidate Dossier)

- **候选标识**：`DRAMP20968`
- **多肽名称**：`Catesbeianin-1`
- **多肽序列**：`MMRVMRRKTKVIWEKKDFIGLYSID` (25 aa)
- **天然来源**：北美牛蛙 (*Lithobates catesbeianus*) 皮肤分泌物克隆
- **化学末端**：未修饰游离羧酸 (`-COOH`, modifications=none)
- **分子量闭环验证**：
  - 质谱/ESI 实测平均分子量：`3144.8 Da` (专利 CN101724632A / 论文 Table 1)
  - 理论未修饰游离酸分子量：`3144.85 Da` (误差 0.05 Da，完全吻合)
  - 理论 C 端酰胺化分子量：`3142.86 Da` (排除酰胺化假说)
- **全员同源隔离**：
  - 对 417 条开发集记录最大全局 Needleman-Wunsch 一致性：**0.3333** (严格 $< 0.40$)
  - 最接近开发集记录：`DBAASP:25512`
- **双任务实测活性**：
  - *E. coli* 抗菌活性：标准菌株 *E. coli* ATCC 25922 微量肉汤稀释法实测 `MIC = 3.1 μg/mL` (判定：`amp = 1`)
  - 人红细胞溶血活性：人红细胞 (hRBC) 梯度溶血实测 `50% hemolysis at 300 μg/mL`，即 $	ext{HC}_{50} = 300\ \mu	ext{g/mL} \ge 250\ \mu	ext{g/mL}$ (判定：`hemo = 0`)
- **原始研究文献**：Xu et al., *Biotechnol Lett.* (2017) 39(6):897-903, PMID `28258530`, DOI `10.1007/s10529-017-2312-7`
- **发明专利**：韩文瑜、冯新 等 (吉林大学), 中国发明专利 `CN101724632A/B`
