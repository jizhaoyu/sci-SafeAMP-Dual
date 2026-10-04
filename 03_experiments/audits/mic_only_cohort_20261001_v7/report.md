# MIC-only 五折可行性审计

**状态：** `blocked`  
**生成时间：** 2026-10-01T12:30:08.805620+00:00  
**协议：** `protocol-mic-01`，SHA-256 `d54227ebb5380039cd07f6ddc979561ef6f99efaecdb7644267e6c7d00dffb97`  
**现有记录：** 417；**DRAMP 补充记录：** 4  
**模型训练：** 未开始；**模型结果：** 未生成

## 证据与队列

- 合并证据门禁：passed — 421 provenance records passed raw-assay validation and label re-derivation.
- 菌株／分离株标识门禁：failed；73 条测定、71 条记录待原文核对。逐条见 `target_identifier_audit.csv`。
- 可判标签记录（合并精确序列前）：395
- 唯一有标签序列：395
- MIC 标签计数（0=阴性、1=阳性）：`{'0': 138, '1': 257}`
- 原始研究标识数：296
- 同源组件：90；最大组件：293；`>=0.40` 成员对：1182

## 五折类别及隔离

| 折 | 训练分子 | 训练阳性 | 训练阴性 | 验证分子 | 验证阳性 | 验证阴性 | 跨折共享组件 | 通过 |
|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 0 | 102 | 47 | 55 | 293 | 210 | 83 | 0 | True |
| 1 | 370 | 245 | 125 | 25 | 12 | 13 | 0 | True |
| 2 | 370 | 246 | 124 | 25 | 11 | 14 | 0 | True |
| 3 | 369 | 245 | 124 | 26 | 12 | 14 | 0 | True |
| 4 | 369 | 245 | 124 | 26 | 12 | 14 | 0 | True |

## 阻断项

- 73 MIC observations across 71 records lack an identified E. coli strain or isolate under protocol-mic-01; review primary papers before release.

## 警示

- Severe fold-size imbalance from an indivisible homology component: largest component=293 of 395 molecules (74.2%); validation fold sizes=[293, 25, 25, 26, 26]. Preserve all-member isolation and review the estimand before model training.

完整记录见同目录 `evidence_inventory.csv`、`exclusions.csv`、`molecule_components.csv`、`all_member_similarity.csv`、`fold_assignments.csv` 和 `manifest.json`。
