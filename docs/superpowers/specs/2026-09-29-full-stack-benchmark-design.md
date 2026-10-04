# SafeAMP-Dual 五维穿透式全栈基准评测工程设计方案 (Full-Stack Benchmark Design)

**文档编号**：SPEC-2026-BENCHMARK-01  
**生效日期**：2026-09-29  
**制定主体**：计算生物学专家、软件架构师、QA 测试工程师与产品经理联合制定  
**执行目标**：实现对 SafeAMP-Dual 平台的跨环境（本地与腾讯云 `62.234.141.184`）、全场景（并发吞吐、真实 DeepSeek 质检、破坏性注入、审计追踪、Fail-Closed 门禁）自动化深度基准测试。

---

## 一、 评测工程架构与五维测试矩阵

评测工程采用独立的自动化基准测试套件（`02_code/benchmark_full_stack.py`），设计为五大严格递进的测试阶段：

```
[阶段 1: 本地核心基线与门禁]
              │
              ▼
[阶段 2: 云端高并发吞吐压测]
              │
              ▼
[阶段 3: 真实 DeepSeek 质检]
              │
              ▼
[阶段 4: 破坏性注入与 Fuzzing]
              │
              ▼
[阶段 5: 结构化审计与追踪对账]
              │
              ▼
[生成最终基准评测验收报告]
```

### 量化合格基准矩阵

| 测试阶段 | 测试对象与手段 | 考核指标与合格基准 | 容错阈值 |
| :--- | :--- | :--- | :---: |
| **阶段 1：本地核心基线与门禁** | 自动化全量回归 132 项测试；模拟无参数运行时检验 Fail-Closed | 1. 132 项测试 100% 通过（0 告警、0 失败）；<br>2. 门禁准确抛出 `ModelUnavailable`，返回 503 | 0 容忍 |
| **阶段 2：云端高并发吞吐压测** | 面向云主机 `http://62.234.141.184:8090`，10 线程并发执行 50 次跨端点请求 | 1. 请求成功率 100%（50/50 响应成功）；<br>2. 计算 Min/P50/P90/P99 延迟及 QPS | 0 崩溃 |
| **阶段 3：真实 DeepSeek 质检验收** | 真实调用云端 `/api/ai_report`（由服务端环境变量读取 Key），获取报告 | 1. 完整包含 SEP-2026 五大规程全部章节；<br>2. 生信指标（电荷 +5.0、疏水度 0.27）吻合；<br>3. 包含科研免责声明 | 0 格式缺漏 |
| **阶段 4：破坏性 Fuzzing 与注入** | 构造 20+ 组变异 Payload（超短、超长 5000 AA、非天然字符、SQL/脚本注入） | 1. 100% 在验证层拦截并返回 HTTP 422；<br>2. 错误信息明确指出异常原因；<br>3. 杜绝 500 异常 | 0 漏检 |
| **阶段 5：全链路审计对账** | 读取云端及本地 `output/audit/api_audit.jsonl` | 1. 所有压测请求 100% 留痕；<br>2. `X-Request-ID` 全局唯一且微秒时间戳格式正确 | 0 遗漏 |

---

## 二、 阶段详细技术规格与实现设计

### 1. 阶段 1：本地核心基线与门禁验证
* **测试用例**：
  * 调用 Python `pytest` 运行 `02_code/tests` 与 `02_code/test_helical_wheel.py`；
  * 调用 `ResearchRuntime(None).load()`，验证 `ModelUnavailable` 异常机制；
* **预期产出**：通过 132 项测试日志与断言。

### 2. 阶段 2：云端高并发与吞吐性能测试
* **端点覆盖**：
  * `GET /api/system_status`（轻量级探针）
  * `POST /api/helical_wheel`（纯理化特征计算）
  * `POST /api/predict_batch`（门禁拦截行为）
* **并发执行器**：
  * `concurrent.futures.ThreadPoolExecutor(max_workers=10)`
  * 统计样本量：50 次混合请求
  * 延迟计算：使用 `time.perf_counter()` 高精度计时器，按升序排列计算百分位数。

### 3. 阶段 3：真实 DeepSeek 生产质检验收
* **输入多肽**：蜂毒素 Melittin (`GIGAVLKVLTTGLPALISWIKRKRQQ`, 26 AA)
* **调用链条**：客户端 -> 云端 API (`/api/ai_report`) -> 腾讯云读取 `/home/ubuntu/safeamp-server/.env` -> DeepSeek 官方 API (`https://api.deepseek.com/v1/chat/completions`)
* **自动化断言检查清单**：
  * [x] 返回结构含 `custom_llm_analysis` 字段，且字符数 $> 500$；
  * [x] `llm_source` 标明 `deepseek-chat`；
  * [x] 正则匹配五大章节标题：
    1. `### 【规程 1】分子理化质量核验与基线参数`
    2. `### 【规程 2】膜孔道形成生物物理机制分类`
    3. `### 【规程 3】溶血毒性决定簇与两亲界面热力学剖析`
    4. `### 【规程 4】AI 定向进化分子工程降毒方案`
    5. `### 【规程 5】CLSI/ISO 标准化湿实验验证操作规程`
  * [x] 理化参数与底层物理计算自洽。

### 4. 阶段 4：破坏性 Fuzzing 与安全注入测试
* **测试用例集**：
  1. 空字符串：`""`
  2. 纯空白字符：`"   \t\n  "`
  3. 单残基：`"A"`
  4. 双残基：`"AK"`
  5. 临界残基：`"KRR"`（3 残基，螺旋轮允许，模型拒绝）
  6. 超长序列：51 残基、100 残基、5000 残基
  7. 非天然残基：`"GIGAULKVLTTGLP"` (含 U)、`"GIGAXLKVLTTGLP"` (含 X)、`"GIGAZLKVLTTGLP"` (含 Z)
  8. 特殊字符与标点：`"GIGA123LKV"`, `"GIGA@#$LKV"`
  9. 安全探测 Payload：
     - SQL 注入：`"GIGAV' OR '1'='1"`
     - XSS 探测：`"<script>alert(1)</script>"`
     - 命令执行注入：`"GIGAV; $(reboot)"`
* **断言**：所有非法请求必须返回 HTTP 422 Unprocessable Entity，错误信息可解析。

### 5. 阶段 5：全链路审计追踪对账
* **对账机制**：
  * 客户端请求记录每一笔分配的 `client_request_id`；
  * 请求发出后检查响应头中的 `X-Request-ID`；
  * 通过 SSH 远端或者本地拉取 `api_audit.jsonl` 最后的日志记录；
  * 核验 `request_id` 匹配率、状态码匹配率、耗时记录合理性。

---

## 三、 执行计划与交付清单

1. **实现测试脚本**：编写 [`02_code/benchmark_full_stack.py`](file:///D:/桌面文件/sci/02_code/benchmark_full_stack.py)；
2. **运行全量测试**：执行脚本并采集各阶段详尽结果（含真实 DeepSeek 报告文本及压测图表）；
3. **输出总结报告**：生成标准化评估报告 [`docs/FULL_STACK_BENCHMARK_REPORT.md`](file:///D:/桌面文件/sci/docs/FULL_STACK_BENCHMARK_REPORT.md)；
4. **CodeGraph 知识图谱同步**：执行 `codegraph sync`，保持图谱 100% 最优健康状态。
