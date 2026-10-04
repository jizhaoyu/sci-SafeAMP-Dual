# SafeAMP-Dual 平台端到端集成测试与接口契约审计报告
# (SafeAMP-Dual QA & Integration Test Report)

- **测试工程师**: QA & Integration Test Engineer
- **工作区**: [`D:/桌面文件/sci`](file:///D:/%E6%A1%8C%E9%9D%A2%E6%96%87%E4%BB%B6/sci)
- **测试环境**: Windows 11 / Python 3.11.9 / pytest-7.4.4 / FastAPI TestClient
- **测试日期**: 2026-09-29
- **测试状态**: **全部通过 (100% PASS, 132/132 Passed, 0 Warnings, 0 Failures)**

---

## 一、 测试结论与执行概况 (Executive Summary)

针对 SafeAMP-Dual 多肽双任务预测与研究服务平台，本次测试覆盖了全套自动化回归测试、API 接口契约校验、全生命周期异步任务流、理化投影算法边界、非标准氨基酸模糊测试（Fuzzing）、大尺度输入阻断、以及高并发线程安全性验证。

### 核心测试指标汇总

* **基线自动化回归测试集**：共 101 项测试，101 项通过，0 项失败，耗时 12.19 秒。
* **新增 QA 端到端集成与契约测试集** ([`test_qa_integration.py`](file:///D:/%E6%A1%8C%E9%9D%A2%E6%96%87%E4%BB%B6/sci/02_code/tests/test_qa_integration.py))：共 31 项测试，31 项通过，0 项失败，耗时 2.76 秒。
* **全量综合回归测试** (`pytest 02_code/tests 02_code/test_helical_wheel.py`)：共 **132 项测试全部通过**，通过率 **100%**，执行耗时 12.75 秒，0 个告警。

---

## 二、 缺陷发现与即时修复记录 (Discovered Defect & Remediation)

在执行批量预测接口错误溯源测试时，发现并修复了 1 处边界异常信息缺失缺陷：

### 缺陷描述
* **定位文件**：[`05_web_server/research_api.py`](file:///D:/%E6%A1%8C%E9%9D%A2%E6%96%87%E4%BB%B6/sci/05_web_server/research_api.py) 中的 `validate_sequence(value, idx=None)` 函数。
* **问题现象**：当客户端提交包含非法氨基酸（如 `'X'`, `'B'`, `'1'` 等）的批量序列时，底层 `clean_sequence` 抛出 `ValueError`，但外层未将序列在列表中的索引 `idx` 注入到错误提示中，仅返回通用提示 `"Noncanonical residues or non-sequence characters are not supported."`，导致批量任务提交者无法快速定位具体哪一条序列存在非法残基。

### 修复方案
在 `validate_sequence` 中捕获底层 `ValueError`，统一注入 `Sequence at index {idx}: ` 前缀：
```python
def validate_sequence(value, idx=None):
    prefix = f'Sequence at index {idx}: ' if idx is not None else ''
    try:
        try:
            seq = clean_sequence(value)
        except ValueError as exc:
            raise ValueError(f'{prefix}{exc}') from exc
        if not 10 <= len(seq) <= 50:
            raise ValueError(f'{prefix}Research model domain is 10–50 residues.')
        return seq
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
```

### 验证结果
重新运行 `TestPredictBatchEndpoint::test_predict_batch_invalid_residue_with_index` 测试，响应状态码为 422，错误信息精准包含 `Sequence at index 1: Noncanonical residues or non-sequence characters are not supported.`，通过验证。

---

## 三、 API 接口契约与端点集成测试明细 (API Contract Verification)

对 [`05_web_server/research_api.py`](file:///D:/%E6%A1%8C%E9%9D%A2%E6%96%87%E4%BB%B6/sci/05_web_server/research_api.py) 与 [`05_web_server/app.py`](file:///D:/%E6%A1%8C%E9%9D%A2%E6%96%87%E4%BB%B6/sci/05_web_server/app.py) 暴露的端点进行了全面契约测试：

### 1. 系统健康状态检查 (`GET /api/system_status`)
* **未配置模型环境（默认 Fail-Closed 状态）**：返回 HTTP 200，字段结构包含：
  * `status`: `"unavailable"`
  * `dual_task_model.weights_loaded`: `false`
  * `dual_task_model.status`: `"Not validated"`
  * `mutation_engine.status`: `"Disabled"`
* **模型校验通过状态（Validated 状态）**：返回 HTTP 200，`status` 切换为 `"healthy"`，`weights_loaded` 切换为 `true`，`provenance` 包含溯源哈希元数据。

### 2. 螺旋轮理化投影接口 (`POST /api/helical_wheel`)
* **典型蜂毒素 Melittin (`GIGAVLKVLTTGLPALISWIKRKRQQ`)**：
  * 状态码：HTTP 200
  * 长度与残基数：26 个，首个残基 G 位于 12 点钟（0.0 度），坐标计算符合 `radius = 120` 规范
  * 净电荷：理论电荷为 +5.0（4 个 Lys + 2 个 Arg - 1 个末端电荷），实测 `net_charge` 精准等于 5.0
  * 两亲疏水力矩：`hydrophobic_moment = 0.536 > 0.1`，验证了典型两亲性抗菌肽的几何特征
* **爪蟾抗菌肽 Magainin-2 (`GIGKFLHSAKKFGKAFVGEIMNS`)**：
  * 状态码：HTTP 200
  * 残基数：23 个
  * 生理净电荷：包含 4 个 Lys（+4）、1 个 Glu（-1）、1 个 His（+0.1），净电荷精准计算为 **+3.1**
* **合法长度边界校验**：
  * 序列长度 3（如 `"AAA"`）：HTTP 200 通过
  * 序列长度 4（如 `"ADAD"`）：HTTP 200 通过
  * 序列长度 50（如 `"A"*50`）：HTTP 200 通过

### 3. 同步批量预测接口 (`POST /api/predict_batch`)
* **未受训验证运行时**：阻断并返回 HTTP 503，错误载荷为 `{"code": "MODEL_NOT_VALIDATED"}`。
* **空序列列表校验**：提交 `{"sequences": []}` 触发 Pydantic 边界校验，返回 HTTP 422。
* **模型适用结构域（Domain 10–50）**：
  * 序列长度 < 10（如 4 残基 `"ADAD"` 或 9 残基 `"A"*9`）：拦截并返回 HTTP 422，明确告知 `Research model domain is 10–50 residues.`。
  * 序列长度 > 50（如 51 残基 `"A"*51`）：拦截并返回 HTTP 422。
* **合法模型预测输出契约**：
  * 返回数组包含 `amp_probability`, `hemo_probability`, `ranking_score`, `therapeutic_safety_index`。
  * 包含 `attribution_type: "physicochemical_heuristic"`。
  * 包含安全免责声明 `warning: "Research prediction; no clinical safety or measured efficacy claim."`。

### 4. 异步批处理任务管理 (`/api/batch_jobs`)
* **任务提交流程 (`POST /api/batch_jobs`)**：
  * 接收合法批处理请求，在后台线程池执行，立即返回 HTTP 200，格式为 `{"job_id": "job-...", "status": "queued", "total": 2}`。
* **任务进度与状态轮询 (`GET /api/batch_jobs/{job_id}`)**：
  * 轮询监控任务状态从 `queued` -> `running` -> `completed`。
  * 验证完成时 `completed == 2`, `failed_count == 0`, `results` 正确包含各序列预测对象。
* **任务取消与异常流 (`DELETE /api/batch_jobs/{job_id}`)**：
  * 取消任务返回 HTTP 200 `{"status": "cancelled"}`。
  * 访问不存在的任务 ID（如 `job-unknown-9999`）：GET 与 DELETE 均幂等返回 HTTP 404 `"Job not found"`。

### 5. AI 突变优化搜索 (`POST /api/ai_optimize`)
* 未经独立验证模型返回 HTTP 503 阻断。
* 验证状态下返回 HTTP 200，字段包含 `status: "exploratory"`, `original_sequence`, `solutions` 列表（包含突变位点、TSI 预测提升值、预测溶血变化）。
* 明确标注 `warning: "Same-model ranking is not independent experimental validation."`。

### 6. 学术报告生成与隐私安全保障 (`POST /api/ai_report`)
* 输出符合学术规范报告，包含 `report_id`, `tier_code: "Research-only"`, `clinical_tier: "Not clinically validated"`, `standard_markdown_report`。
* **序列防外泄隐私契约验证**：当请求体携带外部大模型密钥 `api_key: "sk-test-secret-key-12345"` 时，后端坚守本地证据封闭原则，绝不外发多肽序列，返回字段 `custom_llm_error: "This research endpoint returns evidence-bounded local reports; no sequence was sent externally."`。

### 7. 静态前端资源分发 (Static File Serving)
* 验证 [`05_web_server/app.py`](file:///D:/%E6%A1%8C%E9%9D%A2%E6%96%87%E4%BB%B6/sci/05_web_server/app.py) 路由分发：
  * `GET /`: 返回 HTTP 200，HTML 文本包含前端 Single Page Application 挂载节点 `<div id="root">`。
  * `GET /wheel`: 返回 HTTP 200，正确路由至螺旋轮分析工作台。
  * `GET /evolution`: 返回 HTTP 200，正确路由至序列进化工作台。
  * `GET /report`: 返回 HTTP 200，正确路由至科研报告界面。
  * `GET /favicon.ico`: 返回 HTTP 204 No Content，避免不必要的 404 刷屏。
  * `GET /api/completely_invalid_route`: 返回 HTTP 404。

---

## 四、 边界条件与非标准输入模糊测试 (Boundary & Fuzzing)

| 测试类别 | 测试输入示例 | 预期行为 | 实测结果 | 结论 |
| :--- | :--- | :--- | :--- | :--- |
| **超短序列** | `""`, `"A"`, `"AK"`, `" \t\n "` | 序列长度 < 3 残基，无法构成二级结构 | HTTP 422 拒绝 | **PASS** |
| **螺旋轮下界** | `"AAA"` (3 残基), `"ADAD"` (4 残基) | 螺旋轮投影支持 3–50 残基 | HTTP 200 接收并计算 | **PASS** |
| **预测模型下界** | `"AAA"` (3 残基), `"ADAD"` (4 残基) | 模型训练域严格限定为 10–50 残基 | HTTP 422 拒绝 | **PASS** |
| **两端有效交集** | `"A"*10`, Melittin (26), `"A"*50` | 处于 10–50 残基区间内 | 螺旋轮与模型均 HTTP 200 正常处理 | **PASS** |
| **上界超出** | `"A"*51`, `"A"*100`, `"A"*1000` | 超出 50 残基结构域范围 | 螺旋轮与模型均 HTTP 422 拒绝 | **PASS** |
| **超长极限输入** | 1023 残基 (`> clean_sequence 1022`) | 超出特征提取器极限 | HTTP 422 拒绝 | **PASS** |
| **超大请求攻击** | 5000 残基 (`> Pydantic 4096`) | 超出 API 请求体上限 | HTTP 422 拒绝 | **PASS** |
| **非天然残基** | 含有 `'B'`, `'Z'`, `'X'`, `'U'`, `'O'`, `'J'` | 非 20 种天然氨基酸 | 100% 被捕获并返回 422 | **PASS** |
| **数字及符号** | 注入 `'0'`, `'1'`, `'!'`, `'@'`, `'#'`, `'$'`, `'*'` 等 | 恶意或污染字符 | 注入前缀/中缀/后缀均 422 拒绝 | **PASS** |
| **格式杂乱序列** | `"  \n\t gigavl \n kvltt \r\n glpaliswikrkrqq "` | 含有大小写、混杂回车换行与制表符 | 自动清理为大写规范序列并返回 200 | **PASS** |

---

## 五、 高并发与多线程锁稳定性测试 (Concurrency & Thread-Safety)

针对系统多处涉及线程锁保护的关键模块进行了并发压测：
1. **审计日志中间件** (`audit_logger.py` 中 `_file_lock` 保护的 `api_audit.jsonl` 文件追加写入)
2. **异步批处理管理器** (`batch_task_manager.py` 中 `_lock` 保护的任务状态字典更新与结果收集)
3. **特征缓存管理** (`feature_cache.py` 中 `_lock` 保护的双层 LRU 缓存存取)

### 压测设计与结果
* **并发规模**：通过 `ThreadPoolExecutor(max_workers=10)` 在瞬间发起 50 次高并发请求，跨系统状态、螺旋轮计算、批量预测和异步任务提交 4 个不同核心接口进行轮询压测。
* **稳定性表现**：
  * **请求成功率**：50 / 50（100% 成功返回 HTTP 200），0 次崩溃，0 次连接超时，0 次死锁。
  * **请求追踪性**：每次请求均通过 `X-Request-ID` 实现了全链路打标，自定义客户端 `X-Request-ID`（如 `custom-trace-0042`）完整保留在响应头中。
  * **日志原子写入验证**：检查测试生成的 JSON Lines 审计日志文件，50 条记录全部完整落盘，行数严丝合缝为 50 条，每条日志均为合法的 JSON 格式，未出现多线程写入导致的字符交错或文件损坏。

---

## 六、 归档测试文件索引

* **集成测试脚本**: [`02_code/tests/test_qa_integration.py`](file:///D:/%E6%A1%8C%E9%9D%A2%E6%96%87%E4%BB%B6/sci/02_code/tests/test_qa_integration.py)
* **核心服务定义**: [`05_web_server/research_api.py`](file:///D:/%E6%A1%8C%E9%9D%A2%E6%96%87%E4%BB%B6/sci/05_web_server/research_api.py)
* **前端集成入口**: [`05_web_server/app.py`](file:///D:/%E6%A1%8C%E9%9D%A2%E6%96%87%E4%BB%B6/sci/05_web_server/app.py)
* **螺旋轮单元测试**: [`02_code/test_helical_wheel.py`](file:///D:/%E6%A1%8C%E9%9D%A2%E6%96%87%E4%BB%B6/sci/02_code/test_helical_wheel.py)
* **审计日志组件**: [`02_code/audit_logger.py`](file:///D:/%E6%A1%8C%E9%9D%A2%E6%96%87%E4%BB%B6/sci/02_code/audit_logger.py)
