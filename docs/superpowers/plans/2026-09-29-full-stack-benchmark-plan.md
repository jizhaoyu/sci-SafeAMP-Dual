# SafeAMP-Dual 五维穿透式全栈基准评测实施计划 (Full-Stack Benchmark Implementation Plan)

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建并执行 SafeAMP-Dual 跨本地与腾讯云主机（`62.234.141.184`）的五阶段自动化基准评测套件，全面量化系统并发吞吐、真实 DeepSeek 报告质检、破坏性注入防御与全链路审计留痕，并生成权威总结报告。

**Architecture:** 编写独立的自动化基准测试套件 `02_code/benchmark_full_stack.py`，编排执行 5 大独立测试阶段（本地回归与 Fail-Closed、云端 10 线程并发压测、真实 DeepSeek 质检、破坏性变异 Payload Fuzzing、审计日志对账），并将结果聚合输出至 `docs/FULL_STACK_BENCHMARK_REPORT.md`。

**Tech Stack:** Python 3.11, `pytest`, `concurrent.futures`, `urllib.request`, `httpx`, `paramiko`/SSH, DeepSeek-V3 API, CodeGraph.

## Global Constraints

- 严禁使用多行 LaTeX 环境（如 `\begin{aligned}`），公式统一使用纯文本或行内单美元符号。
- 命令必须兼容 Windows PowerShell (pwsh)，所有路径使用双引号包裹。
- 严禁向系统盘 C:\ 随意写入大型文件，所有交付物必须保存在 `D:\桌面文件\sci`。
- 每次按照文档开发/修改完成之后必须执行 `codegraph sync`。
- 坚持 Fail-Closed 门禁原则，未验证模型坚决拒绝出具正式推断。

---

### Task 1: 编写自动化全栈基准评测主脚本 (`02_code/benchmark_full_stack.py`)

**Files:**
- Create: `02_code/benchmark_full_stack.py`

**Interfaces:**
- Consumes: `05_web_server/research_api.py`, `02_code/inference_runtime.py`, cloud server `http://62.234.141.184:8090`
- Produces: `benchmark_results` dictionary, stdout execution logs, JSON evaluation dump

- [ ] **Step 1: 创建评测主脚本骨架与五阶段流程**
  在 `02_code/benchmark_full_stack.py` 中实现：
  1. `run_phase1_local_baseline()`：运行 pytest 自动化测试（132 项）并校验 `ResearchRuntime(None).load()` 抛出 `ModelUnavailable`；
  2. `run_phase2_remote_concurrency()`：使用 `ThreadPoolExecutor(max_workers=10)` 向云端 `http://62.234.141.184:8090` 发送 50 次跨端点请求，统计 P50/P90/P99 延迟及 QPS；
  3. `run_phase3_deepseek_quality()`：向云端 `/api/ai_report` 传入 Melittin，校验 DeepSeek 返回的五章节完整度与指标吻合度；
  4. `run_phase4_destructive_fuzzing()`：构造 10+ 组变异 Payload（超短、超长、非法残基、SQL/XSS/Command 注入），断言 100% 拦截返回 422；
  5. `run_phase5_audit_trail()`：拉取并核验本地与云端 `output/audit/api_audit.jsonl`，比对 `X-Request-ID`。

- [ ] **Step 2: 语法检查与 AST 编译验证**
  Run: `python -m py_compile 02_code/benchmark_full_stack.py`
  Expected: 无语法错误，退出码 0

---

### Task 2: 执行基准评测并采集五阶段实测数据

**Files:**
- Modify: `02_code/benchmark_full_stack.py` (如需微调参数)

**Interfaces:**
- Consumes: `02_code/benchmark_full_stack.py`, 云端 `62.234.141.184`
- Produces: `output/verification/benchmark_summary.json`

- [ ] **Step 1: 运行全栈基准评测套件**
  Run: `python 02_code/benchmark_full_stack.py`
  Expected: 五个阶段全部执行完成并输出 PASS，输出各阶段量化指标

- [ ] **Step 2: 验证阶段 1 至 5 关键指标**
  - Phase 1: 132 tests PASS, Fail-Closed 503 verified
  - Phase 2: 50 requests 100% success rate, latency statistics calculated
  - Phase 3: DeepSeek report contains 5 SEP-2026 sections, net charge +5.0, KD 0.27
  - Phase 4: 100% fuzzing payloads intercepted with 422, zero 500 errors
  - Phase 5: X-Request-ID audit log verified

---

### Task 3: 编写终审全栈基准评测与验收报告

**Files:**
- Create: `docs/FULL_STACK_BENCHMARK_REPORT.md`

**Interfaces:**
- Consumes: `benchmark_results` 实测数据
- Produces: 详尽的 Markdown 评测报告，含指标对比表、延迟分布、DeepSeek 报告全文节选、Fuzzing 拦截明细

- [ ] **Step 1: 撰写全栈基准报告**
  落地 `docs/FULL_STACK_BENCHMARK_REPORT.md`，按“结论先行”原则呈现所有实测结果与质量评级。

- [ ] **Step 2: 更新任务执行看板与总结数据**
  更新 `docs/handoff/TASK_STATE.md` 与 `output/verification/summary.json`。

---

### Task 4: CodeGraph 知识图谱全量同步与健康度验证

**Files:**
- Sync: `.codegraph`

- [ ] **Step 1: 执行 CodeGraph 同步**
  Run: `codegraph sync`
  Expected: 同步新增文件，索引更新完毕

- [ ] **Step 2: 校验 CodeGraph 状态**
  Run: `codegraph status`
  Expected: `[OK] Index is up to date`
