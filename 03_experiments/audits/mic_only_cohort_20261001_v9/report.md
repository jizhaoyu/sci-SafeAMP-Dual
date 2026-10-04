# MIC-only 五折可行性审计

**状态：** `feasible_for_training_review`  
**生成时间：** 2026-10-01T12:42:39.989771+00:00  
**协议：** `protocol-mic-01`，SHA-256 `d54227ebb5380039cd07f6ddc979561ef6f99efaecdb7644267e6c7d00dffb97`  
**现有记录：** 320；**DRAMP 补充记录：** 4  
**模型训练：** 未开始；**模型结果：** 未生成

## 证据与队列

- 合并证据门禁：passed — 324 provenance records passed raw-assay validation and label re-derivation.
- 菌株／分离株标识门禁：passed；0 条测定、0 条记录待原文核对。逐条见 `target_identifier_audit.csv`。
- 可判标签记录（合并精确序列前）：324
- 唯一有标签序列：324
- MIC 标签计数（0=阴性、1=阳性）：`{'0': 107, '1': 217}`
- 原始研究标识数：252
- 同源组件：84；最大组件：225；`>=0.40` 成员对：828

## 五折类别及隔离

| 折 | 训练分子 | 训练阳性 | 训练阴性 | 验证分子 | 验证阳性 | 验证阴性 | 跨折共享组件 | 通过 |
|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 0 | 99 | 50 | 49 | 225 | 167 | 58 | 0 | True |
| 1 | 298 | 204 | 94 | 26 | 13 | 13 | 0 | True |
| 2 | 300 | 205 | 95 | 24 | 12 | 12 | 0 | True |
| 3 | 300 | 205 | 95 | 24 | 12 | 12 | 0 | True |
| 4 | 299 | 204 | 95 | 25 | 13 | 12 | 0 | True |

## 阻断项

- 无

## 警示

- Severe fold-size imbalance from an indivisible homology component: largest component=225 of 324 molecules (69.4%); validation fold sizes=[225, 26, 24, 24, 25]. Preserve all-member isolation and review the estimand before model training.

完整记录见同目录 `evidence_inventory.csv`、`exclusions.csv`、`molecule_components.csv`、`all_member_similarity.csv`、`fold_assignments.csv` 和 `manifest.json`。
