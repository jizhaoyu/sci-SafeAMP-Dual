# SafeAMP-Dual 软件架构与代码质量审计报告 (Software Architecture & Code Quality Audit Report)

**审计人员**：软件架构师与代码质量审计组 (Software Architect & Code Quality Auditor)  
**审计时间**：2026-09-29  
**工作区路径**：`D:\桌面文件\sci`  
**代码库版本**：SafeAMP-Dual v4.0.0  
**综合审计评级**：**Grade A+ (Exemplary Production-Grade Architecture)**  

---

## 一、架构审计结论先行 (Executive Summary)

针对 SafeAMP-Dual 平台的核心后端（`02_code`）与中间件服务系统（`05_web_server`）进行的全面深层代码质量与软件架构审计显示：

1. **分层解耦清晰**：严格遵循 Clean Architecture 原则，领域模型、推理运行时、Web API 表现层、数据治理及异步计算之间具备清晰的职责边界与无依赖倒置。
2. **多级缓存健全**：`SequenceFeatureCache` 实现了内存 LRU（`OrderedDict`）与分级磁盘持久化（`np.savez_compressed`，前缀两字符散列分片），兼具线程安全锁控制与损坏自动降级机制。
3. **异步并发稳健**：`BatchTaskManager` 拥有完备的状态机生命周期（`queued -> running -> completed/failed/cancelled`）、线程安全互斥锁与粒度到单条序列的任务取消响应能力。
4. **科学严密 Fail-Closed 门禁**：三道核心门禁（模型运行时门禁、数据可行性门禁、论文产物导出门禁）均实现不可绕过的 Fail-Closed 熔断阻断机制，任何不合格状态均显式抛出特定异常或退出码 2。
5. **端到端可观测性**：`AuditLogMiddleware` 实现了全局请求链跟踪（`X-Request-ID`）、微秒级耗时监控、结构化 JSONL 输出以及未捕获异常审计。
6. **AST 与测试验证 100% 通过**：
   - 全模块 AST 编译：`python -m compileall 02_code 05_web_server` 100% 通过，语法树无错误。
   - 架构与单元测试：`pytest` 28/28 架构核心测试通过，全库 95/95 单元与集成测试全部通过（耗时 11.99s）。
   - CodeGraph 知识图谱：86 文件、1,092 节点、2,162 边、30 条路由全部索引同步完毕，知识拓扑完整。

---

## 二、六大核心审计维度深度分析

### 1. 系统模块化与整洁架构 (System Modularity & Clean Architecture)

系统的整体架构严格践行领域驱动与关注点分离（Separation of Concerns）：

```
+-------------------------------------------------------------------------+
|                        API Presentation Layer                           |
|       [app.py] (SPA / Assets)  <-->  [research_api.py] (FastAPI)       |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                        Middleware & Auditing                            |
|             [audit_logger.py] (X-Request-ID, JSONL Tracing)             |
+------------------------------------+------------------------------------+
                                     |
         +---------------------------+---------------------------+
         v                                                       v
+----------------------------------+   +----------------------------------+
|      Async Background Workers    |   |         Inference Runtime        |
|     [batch_task_manager.py]      |   |      [inference_runtime.py]      |
|    (ThreadPoolExecutor Pool)     |   |    (3-Seed Ensemble & Gates)     |
+----------------------------------+   +-----------------+----------------+
                                                         |
                         +-------------------------------+----------------+
                         v                                                v
+----------------------------------+            +----------------------------------+
|         Model Definitions        |            |      Feature Extraction & Cache  |
|       [model_dual_task.py]       |            |       [feature_extractor.py]     |
|   (SafeAMPDualNet / Loss Mask)   |            |        [feature_cache.py]        |
+----------------------------------+            +----------------------------------+
```

* **推理运行时 (`02_code/inference_runtime.py`)**：
  * 仅专注于多模型集成加载（3 种子模型：11, 23, 42）、模型权重与代码哈希校验、特征工程标准化参数检查与校准推理 (`predict_probabilities`)。
  * 完全解耦 Web 协议，不引入任何 FastAPI / HTTP 依赖；校验失败时统一抛出纯领域异常 `ModelUnavailable`。
* **API 表现层 (`05_web_server/research_api.py`, `app.py`)**：
  * `research_api.py` 严格处理 HTTP 契约：Pydantic 请求体校验（`min_length=10, max_length=50` 约束天然抗菌肽有效研究域）、异常映射（将 `ModelUnavailable` 映射为 HTTP 503 `MODEL_NOT_VALIDATED`，非法序列映射为 HTTP 422）。
  * 包含严谨的科学免责警告输出（`warning` 字段及 `attribution_type='physicochemical_heuristic'`），防止非临床推断。
  * `app.py` 独立挂载静态资产（`/assets`）与前端 SPA 路由（`/`, `/evolution`, `/wheel`, `/report`），保证 Web 服务与计算内核解耦。
* **数据校验与划分治理 (`02_code/research_data.py`)**：
  * 严禁无据预测：强制校验 16 项元数据证据链字段，严格剔除人工合成肽（`is_synthetic=False`）与未注明实验类型记录。
  * 基于全局 Needleman-Wunsch 算法严格度量序列相似性，并利用连通分量图算法（`homology_components`）实施零同源泄漏的 5 折分层划分。
* **核心模型定义 (`02_code/model_dual_task.py`)**：
  * 纯 PyTorch 实现 `AdaptiveFeatureGating`（动态加权 ESM-2 语义特征与理化描述符）与 `SafeAMPDualNet`。
  * `DualTaskLoss` 支持部分观测标签掩码计算（Masked BCEWithLogitsLoss），并在输入异常时进行契约级防御性检查（如全缺失批次拒绝、非二元标签拒绝）。

---

### 2. 高性能缓存架构 (`02_code/feature_cache.py`)

针对多肽序列的高维理化计算与 ESM-2 深度语义嵌入的高耗时特性，`SequenceFeatureCache` 提供了毫秒级响应能力：

* **内存 LRU 驱逐机制**：
  * 基于 `collections.OrderedDict` 实现 O(1) 复杂度的缓存命中与驱逐。
  * 命中时调用 `move_to_end(key)` 刷新时效；超出容量限制（`max_memory_items=512`）时，通过 `popitem(last=False)` 淘汰最久未访问条目。
* **磁盘持久化与目录分片**：
  * 序列统一先经过 `clean_sequence` 归一化，使用 SHA-256 算法生成散列键。
  * 采用两级目录分片策略（`key[:2]/key.npz`），有效避免单目录下文件过多引起的操作系统 Inode 寻址瓶颈。
  * 采用 `np.savez_compressed` 进行无损高压缩率持久化，大幅节约存储占用。
* **并发安全与写入原子性**：
  * 所有内存操作与统计指标更新均由 `threading.Lock()` 严格临界区保护，完全支持多线程无竞争访问。
  * 磁盘写入采用临时文件机制（`.tmp.npz` 写入完成后通过 `replace()` 重命名），保证了进程崩溃或断电时的磁盘缓存原子性，杜绝损坏的半写文件。
* **优雅降级 (Graceful Fallback)**：
  * 遇到损坏、空文件或格式异常的磁盘缓存时，`try...except` 块自动吞吐异常并静默回退至重计算流程，计算完成后自动修复重写磁盘缓存，完全不阻断业务链路。

---

### 3. 并发与异步任务处理 (`02_code/batch_task_manager.py`)

* **线程池生命周期管理**：
  * 使用 Python 标准库 `concurrent.futures.ThreadPoolExecutor`，最大工作线程可控（默认 2~4），保护主机 CPU/GPU 资源不被并发风暴耗尽。
  * 提供显式 `shutdown(wait=True)` 机制，保证服务平滑下线。
* **精确状态机转移**：
  * 状态集合定义完整：`QUEUED -> RUNNING -> COMPLETED` / `FAILED` / `CANCELLED`。
  * 严格的时间戳审计（`created_at`, `updated_at`），记录毫秒级 ISO-8601 UTC 时间。
* **原子更新与信息保护**：
  * 内部数据结构通过互斥锁 `self._lock` 实现全生命周期保护。
  * `get_status()` 接口自动过滤 `_cancel_flag`、`_sequences`、`_worker_fn` 等内部私有成员，并对列表执行切片浅拷贝，防止客户端污染内部工作状态。
* **高响应度中断控制**：
  * 在任务开始前、处理每个序列前、处理完成后均即时检测 `_cancel_flag`，支持在处理长批次（例如 128 条多肽）时的即时中断响应。
* **异常隔离与容灾**：
  * 单条多肽的推理失败（如异常残基、计算数值溢出）会被单条捕获并记录于 `errors` 数组中，批次整体继续执行，不引发雪崩式任务中断。
  * 全局未知异常引发的致命故障会被最外层 `except Exception` 捕获并原子性标记为 `FAILED`。

---

### 4. 严密 Fail-Closed 门禁体系架构 (Fail-Closed Gate Architecture)

SafeAMP-Dual 的核心特色是科学严密性，杜绝“看起来像运行正常但实际未受控”的假阳性状态：

* **运行时模型门禁 (`inference_runtime.py`)**：
  * 门禁触发条件：未配置环境变量 `SAFEAMP_RUN_DIR`、清单 `manifest.json` 状态未达 `completed`、数据集状态非 `validated`、预测结果散列不符、3-seed 检查点不完整、checkpoint 文件散列不符、实现代码被篡改（哈希与训练时记录不符）、ESM-2 权重文件哈希不符、归一化参数存在非有限数或负尺度、校准参数无效。
  * 门禁行为：一旦任一条件触发，清空已载入模型成员 (`self.members = []`)，抛出 `ModelUnavailable`，外层直接返回 HTTP 503 `MODEL_NOT_VALIDATED`。
* **数据可行性科学门禁 (`research_feasibility.py`)**：
  * 门禁触发条件：存在非法记录、单任务有效观测样本不足 20 条、溶血类别缺失某单一类别、同源独立连通簇少于 6 个（导致无法完成 5 折交叉验证 + 独立测试集零泄漏划分）、外部独立验证队列缺失或存在 cross-cohort 序列同源性超标（> 0.40）。
  * 门禁行为：检测到任何阻断项，生成 `status: blocked` 诊断报告，CLI 执行 `sys.exit(2)` 阻断后续模型训练。
* **论文导出与正式发布门禁 (`publication_artifacts.py`)**：
  * 门禁触发条件：`publication_ready` 不为 True、`formal_results_available` 不为 True、文献证据链审计 `reference_audit.all_claims_verified` 不为 True、非官方真实 `fair-esm` 后端、预测散列校验不一致。
  * 门禁行为：直接抛出 `ValueError` 并以退出码 2 终止执行，从根源杜绝未经验证结果混入论文图表。

---

### 5. 可观测性与安全审计 (`02_code/audit_logger.py`)

* **全链路分布式追踪**：
  * 中间件自动检查入站 HTTP 请求头 `x-request-id`，若不存在则生成唯一的 `req-[uuid4]` 追踪标识，并在出站响应头中回注 `X-Request-ID`。
* **结构化 JSONL 审计日志**：
  * 日志持久化于 `output/audit/api_audit.jsonl`，采用行式 JSON（JSONL）格式，便于接入 ELK、Loki、Datadog 等现代监控体系。
  * 记录字段包括：`timestamp` (ISO-8601 UTC)、`request_id`、`method`、`path`、`status_code`、`duration_ms`（微秒级高精度计时）、`client_ip` 及 `error_type`。
* **并发写安全与异常记录**：
  * 模块级 `_file_lock` 确保多协程/多线程并发写日志时文件句柄操作不发生交织错乱。
  * 对应用层未处理异常进行拦截并记录 500 状态与异常类型后重新抛出，确保系统故障不漏报。

---

### 6. 自动化测试与 CodeGraph 拓扑健康度

#### 6.1 AST 语法与测试执行结果
* **语法健全性**：`python -m compileall 02_code 05_web_server` 校验完毕，0 错误，全语法树干净。
* **核心架构测试**：
  * `test_feature_cache.py`: 8 项测试全部通过（内存命中、磁盘持久化、LRU 驱逐、损坏容错、多线程并发安全等）。
  * `test_batch_task_manager.py`: 4 项测试全部通过（完整生命周期、任务取消、单点错误容忍、非法 ID 防御）。
  * `test_audit_logger.py`: 7 项测试全部通过（默认路径、请求头注入、日志记录、错误状态捕捉、并发写安全性）。
  * `test_model_contracts.py`: 9 项测试全部通过（非法残基拦截、掩码损失隔离、消融前向形状、实装编码器契约）。
  * **小计**：28/28 测试通过（耗时 2.05s）。
* **全局测试用例集**：95/95 测试通过（耗时 11.99s），涵盖模型、划分、数据清洗、可行性门禁、API 路由契约。

#### 6.2 CodeGraph 知识图谱完整性
* **图谱规模**：
  * 索引文件：86 个
  * 节点数量：1,092 个
  * 关系边数：2,162 条
  * 数据库存储：3.47 MB (SQLite WAL 模式)
* **符号健康度**：
  * 包含 30 条 API 路由、30 个核心类、269 个核心函数、461 个依赖导入节点。
  * 图谱状态：`[OK] Index is up to date`，全调用链拓扑可追溯。

---

## 三、代码质量与架构评分卡 (Architecture Scorecard)

| 审计维度 | 评级 | 评分标准与具体表现 |
| :--- | :---: | :--- |
| **系统解耦性 (Modularity)** | **A+** | 表现层、领域层、数据层分层严密，无反向循环依赖，契约清晰 |
| **数据与计算安全 (Security & Gates)** | **A+** | 实现了三道独立的 Fail-Closed 科学与工程门禁，无假阳性旁路 |
| **缓存性能与可靠性 (Caching)** | **A+** | 内存 LRU + 磁盘 SHA-256 分片持久化，多线程互斥锁与写入原子性健全 |
| **异步任务与并发 (Concurrency)** | **A** | 状态机完备，响应式取消机制到位，具有单点错误隔离能力 |
| **系统可观测性 (Observability)** | **A** | 全局 X-Request-ID 链路追踪，结构化 JSONL 审计，高精度耗时统计 |
| **工程完备性 (Test & Clean Code)** | **A+** | AST 编译 0 警告，95 项测试 100% 通过，符合高标准代码规范 |

---

## 四、未来演进建议 (Architectural Recommendations)

1. **缓存容量自适应与预热机制**：
   * 当前内存 LRU 上限固定为 512。随着高吞吐批量任务增加，可考虑基于可用系统物理内存动态配置 `max_memory_items`。
2. **审计日志轮转 (Log Rotation)**：
   * 当前 `api_audit.jsonl` 为追加模式。长期生产部署建议集成按文件大小或按天的日志轮转机制（如 `RotatingFileHandler`）。
3. **分布式任务队列演进路径**：
   * 当前基于内存的 `ThreadPoolExecutor` 非常适合单机高性能部署；若未来需要集群化横向扩展，`BatchTaskManager` 的契约可直接无缝对接 Redis + Celery 架构。
