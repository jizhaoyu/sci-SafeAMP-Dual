# SafeAMP-Dual Phase D 实施交付日志 (Implementation Log)

> 本文记录 2026-09-30 的工程交付。2026-10-01 新增 `protocol-amd-02` 全员隔离协议并排除 13 条无测定依据的外部记录；当前数据仍因缺独立外部队列而 `blocked`。最新四轴状态以 `04_paper/research_status.json` 为准。

**文档时间**: 2026-09-30 (Asia/Shanghai)  
**工作目录**: `D:/桌面文件/sci`  
**执行角色**: Antigravity / Gemini Phase D 执行代理  
**当前状态**: **Phase D 核心工程实施全部完成 (Task 0 至 Task 7 软件交付完毕，科学门禁严格阻断虚假实验)**

---

## 一、四轴状态事实汇总 (Four-Axis State)

| 状态轴 | 当前取值 | 依据与事实说明 |
|---|---|---|
| **数据准备 (Preparation)** | `blocked` | 真实源数据 `combined_v2` 包含 13 条缺少真实 assay 测定依据的外部序列，被 `evidence_validation` 拦截；且 `protocol-amd-01` 存在科学争议被标记为 `protocol_conflict`。真实数据下 preparation status 为 `blocked`。 |
| **实验运行 (Run)** | `none` | 在数据准备通过且科学门禁放行前，严禁伪造数据启动模型训练。当前无任何假冒 formal run。 |
| **研究结果 (Formal Results)** | `formal_results_available=false` | 无 completed 真实正式运行及全产物校验，严禁宣称已有正式结果。 |
| **投稿审批 (Publication Ready)** | `publication_ready=false` | 投稿导出强制需要独立人工审核回执（`--approval`）且绑定 SHA-256。无人工签字回执，严禁置 true。 |

---

## 二、测试与验证产物总览

- **基线测试 (Task 0)**: `144 passed in 13.09s`
- **终期全量回归 (Task 7)**: **`177 passed in 15.42s`** (新增 33 个单元测试用例，全绿通过，0 错误，0 忽略)
- **测试报告存档**: [`output/verification/phase_d_final_20260930/pytest_full.txt`](file:///D:/桌面文件/sci/output/verification/phase_d_final_20260930/pytest_full.txt)
- **科学门禁阻断证据归档**:
  - [`output/verification/phase_d_final_20260930/audit_real_combined_v2.txt`](file:///D:/桌面文件/sci/output/verification/phase_d_final_20260930/audit_real_combined_v2.txt): 记录 13 条外部记录缺实测证据被拦截
  - [`output/verification/phase_d_final_20260930/audit_real_protocol_amd01.txt`](file:///D:/桌面文件/sci/output/verification/phase_d_final_20260930/audit_real_protocol_amd01.txt): 记录 `protocol-amd-01` 科学争议阻断拦截

---

## 三、分任务实施明细 (Task 0 - Task 7)

### Task 0: 固定可复核基线与变更范围
- 检查工作区及子目录：非 Git 仓库，无擅自 `git init`，无未记录外部修改。
- CodeGraph 图谱状态：98 files, 1313 nodes, 2580 edges, 35 routes。
- 基线测试 144 项全量通过，保存快照于 `output/verification/phase_d_baseline_20260930/`。

### Task 1: 恢复外部标签实测证据链 (P0)
- **新增模块**: [`02_code/evidence_validation.py`](file:///D:/桌面文件/sci/02_code/evidence_validation.py)
  - 实现 `validate_source_evidence(records: pd.DataFrame)`，全量重推导 E. coli MIC 与 Human HC50。
  - 拦截规则：拒绝手写标签、默认 APD3 DOI、MHC 伪造为 HC50、非人红细胞等无证据数据。
- **修改模块**:
  - [`02_code/assay_records.py`](file:///D:/桌面文件/sci/02_code/assay_records.py): 移除 `MHC` 别名，仅允许 `('HC50', '50%HEMOLYSIS', '50%HAEMOLYSIS')`。
  - [`02_code/research_data.py`](file:///D:/桌面文件/sci/02_code/research_data.py): 集成 `validate_source_evidence`。
  - [`02_code/build_cohorts.py`](file:///D:/桌面文件/sci/02_code/build_cohorts.py) & [`02_code/external_curator.py`](file:///D:/桌面文件/sci/02_code/external_curator.py): 移除硬编码默认外部序列，强制真实 `--external` 输入。
- **测试覆盖**: [`02_code/tests/test_external_evidence.py`](file:///D:/桌面文件/sci/02_code/tests/test_external_evidence.py) (6 种失败夹具测试全通)。

### Task 2: 统一协议和确定性相似度实现 (P0/P1)
- **新增模块**: [`02_code/research_protocol_config.py`](file:///D:/桌面文件/sci/02_code/research_protocol_config.py)
  - 定义不可变 `ProtocolSpec` (`legacy-v1`, `protocol-amd-01`)。
  - 实现 `check_protocol_conflicts`：将 `protocol-amd-01` 显式判定为 `protocol_conflict`，阻止未经正式科学决议的放行。
- **修改模块**:
  - [`02_code/cdhit_cluster.py`](file:///D:/桌面文件/sci/02_code/cdhit_cluster.py): 规范聚类排序权重为 `(-len(seq), seq)`（长度降序、同长字典序升序）。
  - [`02_code/research_data.py`](file:///D:/桌面文件/sci/02_code/research_data.py): `sequence_identity` 支持 `identity_mode='min'|'max'`；新增对称 `sequence_length_ratio`；`assert_cross_isolation` 支持 protocol 配置和代表集对比。
- **测试覆盖**: [`02_code/tests/test_protocol_contract.py`](file:///D:/桌面文件/sci/02_code/tests/test_protocol_contract.py) (7 项全通)。

### Task 3: 共用准备引擎与真实可行性判断 (P0)
- **修改模块**:
  - [`02_code/research_data.py`](file:///D:/桌面文件/sci/02_code/research_data.py): 实现统一 `prepare_frame`，构建 `partition_audit.json`，CLI 支持 `--protocol-id`，持久化 7 个产物文件 (`manifest.json` schema_version=2, `records.csv`, `dataset.csv`, `cluster_membership.csv`, `partition_audit.json`, `evidence_audit.json`, `exclusions.json`)。
  - [`02_code/research_feasibility.py`](file:///D:/桌面文件/sci/02_code/research_feasibility.py): 新增 `audit_prepared_feasibility`，CLI 切换为 `--prepared` 与 `--records` 互斥，支持 `--protocol-id`。
- **测试覆盖**: [`02_code/tests/test_preparation_pipeline.py`](file:///D:/桌面文件/sci/02_code/tests/test_preparation_pipeline.py) 与 [`02_code/tests/test_feasibility_gates.py`](file:///D:/桌面文件/sci/02_code/tests/test_feasibility_gates.py) (共 11 项全通)。

### Task 4: 训练清单生命周期与完整产物校验 (P1)
- **新增模块**: [`02_code/run_artifacts.py`](file:///D:/桌面文件/sci/02_code/run_artifacts.py)
  - 实现公开门禁 `validate_run_artifacts` 与 `validate_artifact_payloads`。
  - 严格校验 21 个 model joblib、3 个 PyTorch checkpoints、`features.npz`、逐样本 `predictions.csv` 以及 evaluation 产物 SHA-256。
- **修改模块**:
  - [`02_code/experiment_runner.py`](file:///D:/桌面文件/sci/02_code/experiment_runner.py): `load_dataset` 明确拒绝 CSV 文件与 `cohorts_built` 目录；初始化 `formal_results_available=False`；写 `completed` 前执行 `validate_artifact_payloads`，校验失败保持 `failed`。
- **测试覆盖**: [`02_code/tests/test_run_lifecycle.py`](file:///D:/桌面文件/sci/02_code/tests/test_run_lifecycle.py) (5 项全通)。

### Task 5: 研究草稿与投稿导出闭环 (P1)
- **修改模块**: [`02_code/publication_artifacts.py`](file:///D:/桌面文件/sci/02_code/publication_artifacts.py)
  - 新增 `load_research_predictions(run_dir)`。
  - `export` 支持 `mode='research'`（生成草稿，`publication_ready=False`）与 `mode='publication'`（强制要求 `--approval` 人工审核回执并校验哈希绑定）。
- **测试覆盖**: [`02_code/tests/test_publication_approval.py`](file:///D:/桌面文件/sci/02_code/tests/test_publication_approval.py) 与 [`02_code/tests/test_publication_artifacts.py`](file:///D:/桌面文件/sci/02_code/tests/test_publication_artifacts.py) (共 9 项全通)。

### Task 6: 状态文档与 API 事实一致 (P1/P2)
- **修改模块**:
  - [`02_code/research_readiness.py`](file:///D:/桌面文件/sci/02_code/research_readiness.py): 实现 `generate_current_status(prepared_dir, run_dir=None) -> dict`，CLI 支持 `--prepared` 与 `--run`。
  - [`05_web_server/research_api.py`](file:///D:/桌面文件/sci/05_web_server/research_api.py): `/api/health` 纯存活探针（200）；新增 `/api/ready` 模型就绪探针（未就绪 503，就绪 200）；`/api/metrics` 显式标注缓存 `status: 'not_integrated'`。
  - [`README.md`](file:///D:/桌面文件/sci/README.md) & [`docs/handoff/TASK_STATE.md`](file:///D:/桌面文件/sci/docs/handoff/TASK_STATE.md): 同步数据流规范、不可变目录要求与四轴状态声明。
  - [`04_paper/research_status.json`](file:///D:/桌面文件/sci/04_paper/research_status.json): 生成当前真实状态。
- **测试覆盖**: [`02_code/tests/test_research_status.py`](file:///D:/桌面文件/sci/02_code/tests/test_research_status.py) 与 [`02_code/tests/test_health_and_metrics.py`](file:///D:/桌面文件/sci/02_code/tests/test_health_and_metrics.py) (共 9 项全通)。

### Task 7: 集成验收与科学门禁交付
- 全量 pytest：**177 passed in 15.42s**，退出码 0。
- 真实科学重放测试：
  - 运行 `python -B 02_code/research_data.py --records 02_code/data/sources/combined_v2/records.csv --output 03_experiments/prepared/phase_d_blocked_combined_v2 --protocol-id protocol-amd-01`
  - 结果：退出码 1，拦截报错 `Source evidence validation failed for 13 records; missing or conflicted experimental assays.`。
  - 运行 `python -B 02_code/research_data.py --records 02_code/data/sources/dbaasp_v1/records.csv --output 03_experiments/prepared/phase_d_blocked_amd01 --protocol-id protocol-amd-01`
  - 结果：退出码 1，拦截报错 `protocol_conflict: cross_scope 'members_to_representatives' vs all-member zero leakage claim and min/max denominator ambiguity require formal scientific protocol sign-off.`。
- 门禁结论：软件修复与工程架构 100% 达成，科学保护门禁严格 Fail-Closed，未放行虚假实验。

---

## 四、文件变更与源码清单

| 文件路径 | 变更类型 | 说明 |
|---|---|---|
| `02_code/evidence_validation.py` | 新增 | 实测标签证据审计引擎 |
| `02_code/research_protocol_config.py` | 新增 | 不可变科研协议规范配置 |
| `02_code/run_artifacts.py` | 新增 | 训练运行全量产物校验门禁 |
| `02_code/tests/test_external_evidence.py` | 新增 | 外部证据链单元测试 |
| `02_code/tests/test_protocol_contract.py` | 新增 | 科学协议契约单元测试 |
| `02_code/tests/test_preparation_pipeline.py` | 新增 | 数据准备管线单元测试 |
| `02_code/tests/test_feasibility_gates.py` | 新增 | 可行性门禁单元测试 |
| `02_code/tests/test_run_lifecycle.py` | 新增 | 运行生命周期单元测试 |
| `02_code/tests/test_publication_approval.py` | 新增 | 投稿审核与哈希绑定单元测试 |
| `02_code/tests/test_research_status.py` | 新增 | 研究状态生成单元测试 |
| `02_code/assay_records.py` | 修改 | 规范溶血测定字段，移除 MHC 别名 |
| `02_code/cdhit_cluster.py` | 修改 | 规范聚类排序确定性权重 |
| `02_code/research_data.py` | 修改 | 支持证据校验、准备管线输出 7 文件与 protocol-id |
| `02_code/research_feasibility.py` | 修改 | 支持 `--prepared` 与协议冲突判定 |
| `02_code/experiment_runner.py` | 修改 | 拒绝 CSV/cohorts_built，集成产物完整性校验 |
| `02_code/publication_artifacts.py` | 修改 | 支持 `--mode research/publication` 与人工审核回执校验 |
| `02_code/research_readiness.py` | 修改 | 实现 `generate_current_status` 与对应 CLI |
| `02_code/build_cohorts.py` | 修改 | 移除硬编码外部默认序列 |
| `02_code/external_curator.py` | 修改 | 移除硬编码外部默认序列 |
| `05_web_server/research_api.py` | 修改 | 分离 `/api/health` 与 `/api/ready`，标注缓存未集成 |
| `02_code/tests/test_health_and_metrics.py` | 修改 | 补充 ready 探针与缓存状态测试 |
| `README.md` | 修改 | 规范标准数据流与不可变目录要求 |
| `docs/handoff/TASK_STATE.md` | 修改 | 记录 Phase D 四轴状态与历史口径声明 |
| `04_paper/research_status.json` | 修改 | 记录当前推导的最新项目状态 JSON |
