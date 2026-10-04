# SafeAMP-Dual 交付物与当前研究状态

**更新时间**：2026-10-01  
**权威状态**：`04_paper/research_status.json`（`generated_at` 为精确生成时间）  
**当前协议**：`protocol-amd-02`  
**当前数据版本**：`combined_v3_evidence_clean_20261001`；准备目录 `amd02_evidence_clean_20261001`。

## 四轴状态

| 项目 | 当前值 | 说明 |
| --- | --- | --- |
| 数据准备 | `blocked` | 缺少独立、端点兼容且通过全员隔离审计的外部队列 |
| 正式实验运行 | `none` | 未启动通过科学门禁的七模型三种子比较 |
| 正式研究结果 | `false` | 没有完成且通过产物校验的运行 |
| 投稿审批 | `false` | 无正式结果和人工审核回执 |

## 已交付的工程与证据

- 数据与标签管线：`assay_records.py`、`evidence_validation.py`、`research_data.py` 和 `research_feasibility.py` 负责原始测定重推导、来源哈希、分区及失败即阻断的审计。
- 冻结协议：`research_protocol_config.py` 保留 `legacy-v1`、`protocol-amd-01`，新增采用全局比对列数作分母、0.40 阈值、全员连通分组的 `protocol-amd-02`；参数摘要写入准备清单。
- 历史 `combined_v2` 的 13 条外部记录均缺少底层实验观察；新候选源保留 417 条证据通过的开发记录，并在 `exclusions.json` 逐条记录排除原因。
- 新协议对开发集 86,736 对序列完成审计，得到 89 个连通簇，最大簇 318 条。DRAMP 的 10 条本地候选与开发集 4,170 对比较全部保存，10 条候选均存在达到阈值的配对。
- 七模型三种子训练、推理服务、研究产物导出及人工投稿审批门禁已有软件实现。工程完成不能替代数据可行性或模型效果证明。
- 2026-10-01 本地全量 Python 回归：`182 passed`。

## 当前交付位置

| 交付物 | 位置 |
| --- | --- |
| 机器状态 | `04_paper/research_status.json` |
| 当前准备清单和全员分组 | `03_experiments/prepared/amd02_evidence_clean_20261001/` |
| 证据清理候选源 | `02_code/data/sources/combined_v3_evidence_clean_20261001/` |
| DRAMP 全员候选筛查 | `03_experiments/audits/dramp_amd02_20261001/` |
| 严格协议说明 | `docs/amendments/PROTOCOL_AMENDMENT_02_ALL_MEMBER.md` |
| 历史工程交付和测试记录 | `docs/handoff/PHASE_D_IMPLEMENTATION_LOG.md` |

历史 `protocol-amd-01` 的代表聚类数和旧版“已放行”报告仅保留作过程记录。正式训练的前提是新数据通过原始测定、来源独立性、全员同源隔离和各分区标签门禁；若失败，项目继续保持 `blocked`。
