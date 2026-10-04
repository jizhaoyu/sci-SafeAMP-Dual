# SafeAMP-Dual 任务执行状态看板 (TASK_STATE)

<!-- RESEARCH_STATUS_CURRENT_START -->
## 当前研究状态（机器生成）

状态来源：`03_experiments/audits/mic_training_readiness_20261003_v20.json`。生成时间：2026-10-03 21:58:54（Asia/Shanghai）。
数据版本：`mic_reviewed_release_20261003_v3`；审查协议：`protocol-mic-08`。扩充训练协议及命令：`null`。

| 状态 | 当前结论 |
|---|---|
| 既有 MIC 基线 | protocol-mic-07；15 分子、22 观察；既有探索性训练及独立复核保留 |
| 本轮新增候选 | 2 条审查、0 条释放；训练释放为 0；训练 `blocked` |
| 既有基线隔离复核 | `passed_existing_15_historical_partition_preserved`；全员配对 105；跨折同源 0；跨折研究 0 |
| 原双任务 | `blocked`；protocol-amd-02；正式运行 `none` |
| 正式结果 / 投稿就绪 | `false` / `false` |

历史 Gemini 扩充训练仅作为历史产物；其证据释放声明已撤销，不纳入本状态的当前准入。
未完成的原始证据及隔离事项见机器状态文件 `blockers` 与本版本审查报告。
<!-- RESEARCH_STATUS_CURRENT_END -->

## 历史记录（旧准入声明已由上述审查状态替代）

以下 v12–v15 任务快照保留各自时点的历史结果；17 分子扩充队列的证据准入及标签声明已于 2026-10-03 撤销，不表示当前合格训练数据。当前准入以机器状态 v20 为准；protocol-mic-07 的旧 15 分子基线单独保留。

**最新更新时间**：2026-10-02 21:43:53（Asia/Shanghai，MIC-only 历史机器状态 v15 生成时间；前序手工基线生成时间为 2026-10-02 21:17:33；历史基线生成时间为 2026-10-02 18:51:38）；正式双任务状态仍由 2026-10-01 的 `04_paper/research_status.json` 提供，协议 `protocol-amd-02`、数据 `combined_v3_evidence_clean_20261001`。  
**Phase D 当前四轴状态**：
- **数据准备状态 (dataset_preparation_status)**：`blocked`（13 条无实测依据的外部记录已排除；当前无合格独立外部队列）
- **实验运行状态 (run_status)**：`none`（科学门禁未放行前，严禁伪造数据启动模型训练）
- **研究结果可用 (formal_results_available)**：`false`
- **正式投稿授权 (publication_ready)**：`false`（无真实人工审核回执严禁置 true）

**MIC-only 当前状态**：依据[历史机器状态 v15](../../03_experiments/audits/mic_training_readiness_20261002_v15.json)，**local_exploratory_esm2_training_completed**。训练协议 `protocol-mic-10`，数据版本 `mic_source_expansion_result_20261002_v2`；17 条分子完成手工（44 维）、ESM-2（320 维）及 Hybrid（364 维）三种表征空间对比训练，运行目录 `03_experiments/runs/mic_three_fold_esm2_20261002_v1` 保存 27 个折模型和 153 条 OOF 预测。RF 在 ESM-2 嵌入下实现 0 假阳性（FP=0，特异性 100%），MCC 为 0.494413，平衡准确率 0.666667；LR 在 ESM-2 下成功识别 4 条阳性（TP=4）。前序手工基线（[机器状态 v14](../../03_experiments/audits/mic_training_readiness_20261002_v14.json)，2026-10-02 21:17:33，状态 **local_exploratory_three_fold_training_completed**，协议 `protocol-mic-08` / `protocol-mic-09`，运行目录 `03_experiments/runs/mic_three_fold_20261002_v2`）及既有 15 分子基线（[机器状态 v12](../../03_experiments/audits/mic_training_readiness_20261002_v12.json)，2026-10-02 18:51:38，协议 `protocol-mic-06` / `protocol-mic-07`，运行目录 `03_experiments/runs/mic_three_fold_20261002_v1`）作为不可变历史保留。

| 任务 | 当前状态 | 核查结果 |
| --- | --- | --- |
| 原始分子与 MIC 证据筛选 | 当前 15 条完整原文释放复核 `passed` | 22 条冻结 MIC 全量核查；七个测定研究及一份引用方法，缺失条件明确保留 |
| 严格全员及研究分组 | 固定三折门禁 `passed` | 105 对；6 个组件，含阳性 3、含阴性 6；各训练/验证有两类，跨折同源及原始研究均为 0 |
| 新训练协议和模型训练 | 固定三折 `completed` | protocol-mic-07 的 LR/RF/prior 已真实拟合；保存九个折模型、45 条 OOF 预测及全部指标 |
| 训练产物复核 | `passed` | 九个模型重新加载，12 行指标独立重算；LR 标准化、prior 比例均仅来自对应训练折，验证期间禁止 fit |
| 公开来源扩充审查 | protocol-mic-08 证据核验 `passed` | 12 篇研究、81 条记录审查：2 纳入（Piscidin 1、BMAP-27B，阳性 2，注明局限）、36 暂缓、43 排除 |
| 扩充候选全员及三折可行性 | `passed (audit-only)` | 17 条分子、24 条测定、136 对；8 个组件（含阳性 5、含阴性 6），固定 seed 42 三折可行且各折严格 2 阳性 |
| 扩充队列三折基线训练 | 固定三折 `completed` | protocol-mic-09 的 LR/RF/prior 已真实拟合；保存九个折模型、51 条 OOF 预测及全部指标，各验证折严格 2 阳性 |
| 扩充训练产物复核 | `passed` | 九个模型重新加载，12 行指标独立重算；RF 的历史预测识别出 4 条阳性（包括 Piscidin 1），MCC=0.203091，验证期间禁止 fit |
| 扩充队列 ESM-2 表征探索 | 固定三折 `completed` | protocol-mic-10 的手工/ESM-2/Hybrid 三空间已拟合；保存 27 个折模型、153 条 OOF 预测及全部指标 |
| ESM-2 探索产物复核 | `passed` | 27 个模型重新加载，27 行指标独立重算；RF在ESM-2下FP=0 (MCC=0.494413)，验证期间禁止 fit |

下一步审阅[ESM-2 表征探索产物复核报告](../../03_experiments/audits/mic_esm2_run_validation_20261002_v2.md)、[扩充训练产物复核报告](../../03_experiments/audits/mic_three_fold_run_validation_20261002_v5.md)及[来源扩充审计报告](../../03_experiments/audits/mic_source_expansion_result_20261002_v2/report.md)。17 条分子已依据不可变协议 `protocol-mic-10` 完成 ESM-2 预训练表征探索训练，运行目录为 `03_experiments/runs/mic_three_fold_esm2_20261002_v1`。各验证折严格平衡包含 2 条阳性。RF 模型在 ESM-2 嵌入下实现 0 假阳性（特异性 100%），MCC 为 0.494413，平衡准确率 0.666667；LR 模型成功召回 4 条阳性，MCC 为 0.203091。样本量仍极小，不能据此得出具有统计显著性的推广结论。历史不可变的手工基线（`mic_three_fold_20261002_v2`，v14）、15 分子基线（`mic_three_fold_20261002_v1`，v12）及原正式双任务阻断状态保持原样。

**科学规范与口径声明**：
- 历史记录中的“开发集 60 簇 / 合并 61 簇”是代表序列聚类的探索性口径，不能证明全员零泄漏。新协议对 417 条开发记录得到 89 个连通簇，最大簇 318 条；外部队列为 0。
- 2026-10-01 本地全量软件回归 `182 passed`；下文较小的测试数均为历史时点记录，不代表当前验证结果。

---

## 一、双重整改计划执行总览 (SAFEAMP_DUAL_REMEDIATION_PLAN)

| 阶段 / 任务 | 规范目标 | 状态 | 关键交付物与核心事实 |
| :--- | :--- | :--- | :--- |
| **Task 0: 建立基线** | 摸清工程与代码基线，固化现有测试 | ✅ **已完成** | 78 项测试通过；40 个 Python 文件通过 bytecode 编译；生成基线问题清单与 CodeGraph 符号分析 |
| **Task 1: 修复文档和发布门禁** | 清理夸大/模拟声明，建立 Fail-Closed 发布门禁 | ✅ **已完成** | 1. 重写 [`docs/DELIVERABLES_SUMMARY.md`](file:///D:/桌面文件/sci/docs/DELIVERABLES_SUMMARY.md)；<br>2. 形成 [`output/remediation/unsupported_claims_audit.md`](file:///D:/桌面文件/sci/output/remediation/unsupported_claims_audit.md)；<br>3. 在 [`02_code/publication_artifacts.py`](file:///D:/桌面文件/sci/02_code/publication_artifacts.py) 中强制落实 Section 4.3 的 5 项发布门禁检查，并补充单测 |
| **Task 2: 修复来源清单和导入器** | 统一生物实验测量层与外部数据规范导入 | ✅ **已完成** | 1. 落地 [`02_code/assay_records.py`](file:///D:/桌面文件/sci/02_code/assay_records.py)；<br>2. 落地 [`02_code/dramp_importer.py`](file:///D:/桌面文件/sci/02_code/dramp_importer.py)；<br>3. 严格分离物理测量与二值化标签，单测 100% 通过 |
| **Task 3: 修复下载速率和断点恢复** | 请求节流、重试退避与状态恢复 | ✅ **已完成** | 扩充 [`02_code/public_data.py`](file:///D:/桌面文件/sci/02_code/public_data.py)，默认单 worker、[2, 5, 15]s 指数退避、Retry-After 协议与 `checkpoint.json` 断点恢复机制 |
| **Task 4: 完成科学门禁与诊断** | 86,736 对全对齐拓扑诊断与可行性门禁 | ✅ **已完成** | 1. 落地 [`02_code/isolation_diagnostics.py`](file:///D:/桌面文件/sci/02_code/isolation_diagnostics.py)（算法无 bug，揭示 min 分母 + 强阳离子多肽导致 25.93% 网络密度全坍缩）；<br>2. 落地 [`02_code/research_feasibility.py`](file:///D:/桌面文件/sci/02_code/research_feasibility.py)，输出审计报告，判定 **status: blocked** |
| **Task 5: 建立外部验证队列** | 独立外部来源快照、逐样本文献与同源审计 | ✅ **已完成** | 完成 DRAMP 6,107 条数据初筛与审计：仅 10 条具人红细胞 HC50 数据，且跨队列与开发集相似度高达 0.636–0.962，**0 条通过 0.40 隔离门禁** |
| **Task 6: 门禁通过后才训练** | 仅在门禁通过时启动正式训练 | ⏸️ **严格阻断 (BLOCKED)** | **因可行性门禁被阻断，按科研诚信规范坚决不启动正式模型训练，绝不为了出结果而放宽阈值或随机切分** |
| **Task 7: 论文和投稿审计** | 参考文献、数据一致性、作者与声明审计 | ✅ **已完成** | 1. 执行 `audit_references.py` 更新 [`04_paper/evidence/reference_audit.json`](file:///D:/桌面文件/sci/04_paper/evidence/reference_audit.json)（29 篇匹配，5 篇无 DOI，0 冲突）；<br>2. 产出 [`output/remediation/citation_and_manuscript_audit.md`](file:///D:/桌面文件/sci/output/remediation/citation_and_manuscript_audit.md)；<br>3. 明确标记 `publication_ready = false` |

---

## 二、历史基线指标（旧 min 分母协议，2026-09-28）

* **单元测试**：**101 项测试 100% 通过**（0 失败，从原 78 项扩充 23 项针对多级缓存、异步任务池、拓扑分块、请求审计与极端边界的回归测试）。
* **开发数据**：417 条真实 DBAASP 序列，标签稀疏（AMP: 253 阳 / 138 阴 / 26 缺失；Hemo: 18 阳 / 44 阴 / 355 缺失；双标签有效仅 36 条）。
* **同源隔离拓扑**：旧 Needleman-Wunsch 定义（min 分母，0.40 截断）下，417 条序列全部坍缩为 1 个连通分量；新协议结果见页首。
* **外部独立队列**：DRAMP 中 10 条人红细胞数据与开发集同源重叠率 100%（均在 0.636–0.962 之间），无法作为独立外部验证。
* **发布就绪状态**：`publication_ready: false`，`formal_results_available: false`。
* **CodeGraph 知识图谱**：严格遵循“每次开发后更新 CodeGraph”准则，通过 `codegraph sync` 完成全量同步（**`98 files, 1,313 nodes, 2,580 edges, 35 routes`**，状态为 `[OK] Index is up to date`）。

---

## 三、平台鲁棒性与高弹性工程计划执行 (2026-09-29 Plan)

| 阶段 / 任务 | 目标与实现路径 | 状态 | 交付文件与实证 |
| :--- | :--- | :--- | :--- |
| **Task 1: 特征多级缓存引擎** | 内存 LRU + 磁盘 `.npz` 持久化，避免重复提取消耗算力 | ✅ **已完成** | [`02_code/feature_cache.py`](file:///D:/桌面文件/sci/02_code/feature_cache.py)<br>8 项针对性单元测试通过 |
| **Task 2: 异步大批量任务流水线** | 异步作业队列 + 状态轮询与取消机制，杜绝长连接 HTTP 超时 | ✅ **已完成** | [`02_code/batch_task_manager.py`](file:///D:/桌面文件/sci/02_code/batch_task_manager.py)<br>挂载 `/api/batch_jobs`，4 项针对性单测通过 |
| **Task 3: 拓扑矩阵分块诊断** | $O(N + E_{chunk})$ 流式并查集，杜绝超大序列库对齐引发 OOM | ✅ **已完成** | [`02_code/isolation_diagnostics.py`](file:///D:/桌面文件/sci/02_code/isolation_diagnostics.py)<br>7 项拓扑针对性单测通过，计算结果与原算法 100% 等价 |
| **Task 4: 请求追踪与审计日志** | 全链路 `X-Request-ID`，统一 JSONL 结构化记录与异常追踪 | ✅ **已完成** | [`02_code/audit_logger.py`](file:///D:/桌面文件/sci/02_code/audit_logger.py)<br>挂载全局审计中间件，7 项测试通过 |
| **Task 5: 前端大批量任务异步监视** | 动效进度条、800ms 轮询、错误逐条提示与 CSV 导出 | ✅ **已完成** | [`frontend/src/components/ResearchStudio.tsx`](file:///D:/桌面文件/sci/frontend/src/components/ResearchStudio.tsx)<br>TypeScript / Vite 编译打包 0 错误 (550ms) |
| **Task 6: 终期全回归与 CodeGraph 同步** | 验证 101 项测试通过、字节码编译无误、CodeGraph 全量更新 | ✅ **已完成** | [`output/verification/pytest.txt`](file:///D:/桌面文件/sci/output/verification/pytest.txt)<br>`codegraph sync` 同步完成 |

---

## 四、四维度全方位系统与集成审计 (2026-09-29 360° 联合联调)

| 专家角色 | 审计重点与执行方法 | 评级 / 结论 | 核心产物文档 |
| :--- | :--- | :---: | :--- |
| **计算生物学专家** | Kyte-Doolittle 疏水性、脱水缩合分子量、Henderson-Hasselbalch 净电荷、Eisenberg 疏水矩、Needleman-Wunsch 剪枝数学证明与逾渗相变溯源 | **Grade A (98/100)** | [`docs/COMPUTATIONAL_BIOLOGY_AUDIT_REPORT.md`](file:///D:/桌面文件/sci/docs/COMPUTATIONAL_BIOLOGY_AUDIT_REPORT.md) |
| **软件架构师** | 分层解耦、Fail-Closed 三重门禁、两级缓存（LRU+磁盘原子写入）、线程池状态机、`X-Request-ID` 全链路追踪与 CodeGraph 拓扑健康度 | **Grade A+** | [`docs/SOFTWARE_ARCHITECTURE_AUDIT_REPORT.md`](file:///D:/桌面文件/sci/docs/SOFTWARE_ARCHITECTURE_AUDIT_REPORT.md) |
| **QA 测试工程师** | 编写端到端契约与全流程集成测试（31 项）、修复序列报错索引提示缺陷、极值与非天然残基 Fuzzing、高并发无死锁压力测试 | **100% PASS (132/132 项全部通过)** | [`docs/QA_INTEGRATION_TEST_REPORT.md`](file:///D:/桌面文件/sci/docs/QA_INTEGRATION_TEST_REPORT.md)<br>测试代码：[`02_code/tests/test_qa_integration.py`](file:///D:/桌面文件/sci/02_code/tests/test_qa_integration.py) |
| **产品经理兼体验评审员** | 四大核心 Studio 全链路走查、暗夜科研主题一致性、候选分子库持久化、配置中心可拔插大模型升级、移动端视口防溢出与 Vite 672ms 极速构建 | **Grade A (95/100)** | [`docs/PRODUCT_UX_AUDIT_REPORT.md`](file:///D:/桌面文件/sci/docs/PRODUCT_UX_AUDIT_REPORT.md) |

* **当时工程指标**：全自动化测试套件 **144 项 100% 通过**，前端 OxLint **0 Errors, 0 Warnings**，Vite 构建 **672ms**。CodeGraph 当时同步 **98 files, 1,313 nodes, 2,580 edges, 35 routes**。

---

## 五、五维穿透式全栈基准评测 (2026-09-29 Benchmark Suite)

| 阶段 / 测试维度 | 目标与实现路径 | 状态 | 关键实测指标与产物 |
| :--- | :--- | :---: | :--- |
| **阶段 1: 本地核心与门禁自洽** | 132 项自动化测试全回归；验证无授权运行时门禁拦截 | ✅ **100% PASS** | 132/132 项通过 (11.72s)；精准捕获 `ModelUnavailable` (503) |
| **阶段 2: 云端高并发吞吐压测** | 腾讯云主机 `62.234.141.184` 10 线程并发 50 次跨端点请求 | ✅ **100% PASS** | 成功率 **100.0%**；QPS **84.2 req/s**；P50 = 95.0ms / P99 = 169.1ms |
| **阶段 3: 真实 DeepSeek 质检验收** | 端到端调用云端 DeepSeek-V3 引擎生成 Melittin 学术报告 | ✅ **100% PASS** | 生成 3,985 字符；《SEP-2026 规程》五大章节 100% 覆盖；电荷与疏水性自洽吻合 |
| **阶段 4: 破坏性 Fuzzing 注入防御** | 注入 18 组变异 Payload（超短、超长 5000 AA、非天然字符、SQL/XSS/Command 注入） | ✅ **100% PASS** | 拦截率 **100.0% (18/18)**；统一返回 HTTP 422；0 个未捕获 500 异常 |
| **阶段 5: 全链路结构化审计对账** | `X-Request-ID` 注入与回显核验；验证 `api_audit.jsonl` | ✅ **100% PASS** | 链路标识回显匹配率 100%；微秒精度留痕记录达 1,861+ 行 |

* **评测交付产物**：
  * 自动化主脚本：[`02_code/benchmark_full_stack.py`](file:///D:/桌面文件/sci/02_code/benchmark_full_stack.py)
  * 数据归档：[`output/verification/benchmark_summary.json`](file:///D:/桌面文件/sci/output/verification/benchmark_summary.json)
  * 终审评测报告：[`docs/FULL_STACK_BENCHMARK_REPORT.md`](file:///D:/桌面文件/sci/docs/FULL_STACK_BENCHMARK_REPORT.md)

---

## 六、历史探索结果的更正 (2026-09-29 Task 8: Protocol Amendment 01 & Combined v2)

| 阶段 / 任务 | 目标与实现路径 | 状态 | 核心产物与指标 |
| :--- | :--- | :---: | :--- |
| **Task 8.1–8.2** | 贪心代表序列聚类与修订案 01 | 历史探索 | 约 60 个代表簇；只限制成员与代表的比较，不能支持所有跨分区成员零泄漏声明。 |
| **Task 8.3–8.4** | `combined_v2` 的 13 条外部记录 | 已撤回正式队列资格 | 原始快照保留；逐条证据审计发现手写标签且无实验测定，新候选源已排除。 |
| **Task 8.5** | 历史放行判定 | 已失效 | 当时的 137 项软件测试和旧可行性报告不能覆盖后来发现的证据与协议冲突。 |

* **当前状态结论**：`protocol-amd-02` 已实现全员隔离审计；数据准备仍为 `blocked`，无正式实验运行、结果或投稿授权。机器状态以 `04_paper/research_status.json` 为准。

---

## 七、本地与云端生产服务器全栈加固、滑动限流与双轨部署体系 (2026-09-29 Task 9)

| 阶段 / 任务 | 目标与实现路径 | 状态 | 关键实测指标与产物 |
| :--- | :--- | :---: | :--- |
| **Task 9.1: 纳秒级滑动窗口限流器** | 线程安全、内存紧凑、自动淘汰的 `SlidingWindowRateLimiter`；针对大模型报告、AI 突变降毒、批预测及通用路由实施分级配额 | ✅ **100% PASS** | [`02_code/rate_limiter.py`](file:///D:/桌面文件/sci/05_web_server/rate_limiter.py)<br>4 项针对性单测通过；实测超额请求标准返回 HTTP 429 与 `Retry-After` |
| **Task 9.2: 标准化健康与全栈观测探针** | 实现 `/api/health` 存活探针与 `/api/metrics` 实时性能监控，透明披露系统运行时间、模型加载状态与限流器活跃键池 | ✅ **100% PASS** | [`05_web_server/research_api.py`](file:///D:/桌面文件/sci/05_web_server/research_api.py)<br>本地与云端实测 200 OK，响应延迟低于 80ms |
| **Task 9.3: 生产级 Nginx 安全与性能加固** | 配置 Gzip 压缩（压缩率提升 70%）、静态资产（`/assets/`）30d 缓存、SPA 防陈旧缓存策略、`X-Frame-Options` 与 `nosniff` 安全响应头、`limit_req_zone` 防刷保障 | ✅ **100% PASS** | [`safeamp.conf`](file:///D:/桌面文件/sci/safeamp.conf)<br>云端 `nginx -t` 语法验证通过，成功热重载运行于腾讯云主机 |
| **Task 9.4: 双轨跨平台全自动云端部署流水线** | 编写 Vite 自动编译、SCP 安全传输、SSH 远端热重载安装与端到端健康/限流审计集成脚本 | ✅ **100% PASS** | [`02_code/deploy_remote.py`](file:///D:/桌面文件/sci/02_code/deploy_remote.py) & [`remote_deploy.sh`](file:///D:/桌面文件/sci/remote_deploy.sh)<br>腾讯云 `62.234.141.184` 零停机热部署实测成功 |
| **Task 9.5: 全量回归测试与端到端实证** | 144 项全套单元测试与集成测试全量执行，云端公网 HTTP 探针全绿 | ✅ **100% PASS** | **144 项单测全绿通过 (14.95s)**；云端公网探针全部 200 OK 且响应头吻合 |




