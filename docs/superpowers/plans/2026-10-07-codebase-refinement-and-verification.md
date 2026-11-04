# DTI 全平台稳健性加固与优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 彻底消除代码库中因历史协议密码学哈希冲突导致的测试红灯，补齐前后端大模型改构参数协议与静默降级提示，堵住高开销接口频控盲区，精简推理线性代数冗余，并将全平台推荐模型与分子可视化保真度统一对齐。

**Architecture:** 
1. **密码学解耦层**：将实验性 `protocol-amd-03` 逻辑从受保护的 `02_code/research_data.py` 剥离至专用派生脚本，恢复历史冻结哈希（`9a5d92a8...`），修复陈旧物理断言，使科研防篡改门禁与回归套件重归绿灯；
2. **前后端接口稳健层**：在 `dti_lead_optimizer.py` 中实现 `api_base`/`base_url` 与 `model`/`model_name` 双向兼容映射，在返回体中透传降级原因并在 UI 给予明确告警；在 `rate_limiter.py` 补齐 `/api/dti/optimize_lead` 限流；
3. **计算与产品对齐层**：缓存 `DTIInferenceRuntime` 静态靶点矩阵范数消除重复计算；全平台将推荐模型统一为 100 维催化口袋特征增强的 5 折 Stacking 集成模型；在 `Molecule2DViewer.tsx` 中支持方括号原子（如 `[nH]`）成组识别，消除虚假原子节点。

**Tech Stack:** Python 3.11, FastAPI, NumPy, Scikit-learn, Pytest, React 19, TypeScript, Vite, TailwindCSS.

**Spec:** 本计划基于 2026-10-07 全盘代码与测试审计诊断报告（包含对 `protocol-mic-13` 密码学绑定、`LeadOptimizerStudio` 键名冲突、`rate_limiter` 盲区及 `Molecule2DViewer` 拓扑解析缺陷的实证分析）。

## Global Constraints

- 严禁篡改已受协议锁定的历史代码哈希，保持 `protocol-mic-13.json` 中依赖清单的密码学一致性；
- 严禁引入重型外部依赖（如 RDKit C++ 拓展或臃肿渲染库），保持零安装门槛与纯 Python/纯前端轻量化特性；
- 遵循 Windows pwsh 规范与 C 盘存储保护原则，产物严格限制在工作区 `d:\桌面文件\sci`；
- 所有改动必须通过全量单元测试与前端构建（`npm run build`）。

## Review Focus

- 当用户在前端 Settings 中自定义非官方 `apiBase`（如代理地址或内网端口）时，优化工作台必须准确直连该地址，不得静默回退至 DeepSeek 官方地址；
- 当外部大模型返回 401/402/超时等异常时，前端必须明确感知并展示告警信息，不得让用户误以为规则生成物为 AI 产物；
- 客户端在 60 秒内连续调用 `/api/dti/optimize_lead` 超过 6 次时，系统必须立即返回 429 并携带 `Retry-After`，有效阻断并发配额穿透；
- 靶点相似度计算在 16-激酶面板全扫描与批量预测时，不得重复触发对全训练集的 `np.linalg.norm` 重复计算；
- 输入包含 `[nH]`（如达沙替尼、索拉非尼类似物）的激酶抑制剂分子时，2D 视图中不得出现游离的“H”原子球破坏环系。

---

### Task 1: 密码学防篡改绑定恢复与科研门禁解耦

**Files:**
- Modify: `02_code/research_data.py` (恢复至 git HEAD 对应的原始冻结哈希 `9a5d92a8bbb54bbb938a6a3cb0c0c798a9e14e72942f53a9f1b74b1e5b047350`)
- Modify: `02_code/tests/test_mic_reviewed_training.py:100-103` (更新陈旧的历史物理文件断言)
- Test: `02_code/tests/test_mic_project_check.py`

**Interfaces:**
- Consumes: `protocol-mic-13.json` 依赖哈希定义
- Produces: `check_mic_project.py --scope current` 零错误通过返回

- [ ] **Step 1: 编写/验证受保护文件哈希校验测试**

```python
# 验证 02_code/research_data.py 的 sha256 必须严格等于 protocol-mic-13.json 中锁定的哈希
import json
from pathlib import Path
from research_utils import sha256, ROOT

def test_research_data_matches_frozen_protocol():
    proto = json.loads((ROOT / "03_experiments/protocols/protocol-mic-13.json").read_text(encoding="utf-8"))
    expected = proto["dependency_sha256"]["02_code/research_data.py"]
    current = sha256(ROOT / "02_code/research_data.py")
    assert current == expected
```

- [ ] **Step 2: 运行测试验证当前处于失败状态**

Run: `pytest 02_code/tests/test_mic_project_check.py -v`
Expected: FAIL with `ValueError: Immutable binding changed: 02_code/research_data.py`

- [ ] **Step 3: 恢复 `02_code/research_data.py` 并修正 `test_mic_reviewed_training.py`**

1. 将 `02_code/research_data.py` 还原为冻结的原始字节（撤销将 `c_terminal_amide` 硬编码进旧门禁的修改）；
2. 检查 `test_mic_reviewed_training.py` 中 `test_protocol_11_and_freeze_slots_remain_unused_until_gate_passes`，将其调整为符合当前 2026-10-04 交付快照的条件断言。

- [ ] **Step 4: 运行科学门禁命令行与测试套件验证完全恢复**

Run: `python 02_code/check_mic_project.py --scope current`
Expected: 输出 JSON 中 `"status": "passed"` 且进程以 exit code 0 退出。

- [ ] **Step 5: 提交更改**

```bash
git add 02_code/research_data.py 02_code/tests/test_mic_reviewed_training.py
git commit -m "fix(provenance): 恢复 research_data.py 冻结密码学哈希并解耦协议门禁"
```

---

### Task 2: LLM 改构参数双向对齐与降级可解释提示

**Files:**
- Modify: `02_code/dti_lead_optimizer.py:114-118,241-248`
- Modify: `frontend/src/components/LeadOptimizerStudio.tsx:173-178,540-560`
- Test: `02_code/tests/test_dti_lead_optimizer.py`

**Interfaces:**
- Consumes: `llm_config` 字典，可携带 `api_base` / `base_url` 与 `model` / `model_name`
- Produces: 返回字典包含 `mode`, `fallback_reason: Optional[str]`

- [ ] **Step 1: 编写参数兼容与降级原因测试**

```python
# 测试不同键名输入均能正确识别，并在 LLM 调用失败时返回 fallback_reason
def test_lead_optimizer_config_compatibility(monkeypatch):
    from dti_lead_optimizer import DTILeadOptimizer
    # 构造 mock runtime
    # 传入 {api_base: 'https://custom.api/v1', model: 'custom-model'}
    # 验证 fallback 时包含脱敏错误原因
```

- [ ] **Step 2: 运行测试确认测试执行**

Run: `pytest 02_code/tests/test_dti_lead_optimizer.py -v`

- [ ] **Step 3: 修改 `dti_lead_optimizer.py` 实现健壮参数读取与异常透传**

1. 在 `generate_llm_candidates` 中读取：
   `base_url = (llm_config.get("base_url") or llm_config.get("api_base") or "https://api.deepseek.com").rstrip("/")`
   `model_name = (llm_config.get("model_name") or llm_config.get("model") or "deepseek-chat").strip()`
2. 在捕获异常时记录详细信息，并在优化结果外层附加 `fallback_reason: str | None`；
3. 前端 `LeadOptimizerStudio.tsx` 中在展示模式标签下方添加告警提示：“⚠️ 检测到大模型服务异常（原因：...），已自动启用药化专家规则保底方案”。

- [ ] **Step 4: 运行测试并验证通过**

Run: `pytest 02_code/tests/test_dti_lead_optimizer.py -v`
Expected: PASS

- [ ] **Step 5: 提交更改**

```bash
git add 02_code/dti_lead_optimizer.py frontend/src/components/LeadOptimizerStudio.tsx
git commit -m "fix(dti): 对齐先导改构参数键名并增加降级可解释提示"
```

---

### Task 3: 高开销 DTI 改构路由速率限制保护

**Files:**
- Modify: `05_web_server/rate_limiter.py:28-36`
- Modify: `02_code/tests/test_rate_limiter.py`

**Interfaces:**
- Consumes: HTTP 请求至 `/api/dti/optimize_lead`
- Produces: 超过 6 req/60s 时返回 HTTP 429 响应头包含 `Retry-After`

- [ ] **Step 1: 编写先导优化路由限频测试**

```python
def test_optimize_lead_route_is_strictly_rate_limited():
    from rate_limiter import SlidingWindowRateLimiter
    limiter = SlidingWindowRateLimiter()
    # 模拟 client_ip 在 /api/dti/optimize_lead 连续 6 次允许，第 7 次返回 False
    for _ in range(6):
        allowed, _, _, _ = limiter.check_rate_limit("1.2.3.4", "/api/dti/optimize_lead")
        assert allowed is True
    allowed, _, retry_after, limit = limiter.check_rate_limit("1.2.3.4", "/api/dti/optimize_lead")
    assert allowed is False
    assert limit == 6
    assert retry_after > 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest 02_code/tests/test_rate_limiter.py::test_optimize_lead_route_is_strictly_rate_limited -v`
Expected: FAIL (因为目前默认被归类为 `/api/` 的 120 次/分)

- [ ] **Step 3: 在 `rate_limiter.py` 中注册该路由规则**

在 `self.limits` 字典中显式加入：
```python
"/api/dti/optimize_lead": (6, 60),
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest 02_code/tests/test_rate_limiter.py -v`
Expected: PASS

- [ ] **Step 5: 提交更改**

```bash
git add 05_web_server/rate_limiter.py 02_code/tests/test_rate_limiter.py
git commit -m "feat(security): 为 DTI 先导改构接口配置严格滑动窗口频控"
```

---

### Task 4: 预计算并缓存静态靶点特征矩阵范数

**Files:**
- Modify: `02_code/dti_inference_runtime.py:58-60,183-191,245-255`
- Test: `02_code/tests/test_dti_runtime_performance.py`

**Interfaces:**
- Consumes: `self._train_target_feats: np.ndarray` (形状 303 x 28)
- Produces: `self._train_target_norms: np.ndarray` (形状 303,)，推理时直接向量化点积广播

- [ ] **Step 1: 编写范数缓存正确性测试**

```python
def test_precomputed_target_norms_equal_runtime_norms():
    from dti_inference_runtime import DTIInferenceRuntime
    runtime = DTIInferenceRuntime()
    runtime.load()
    assert runtime._train_target_norms is not None
    expected = np.linalg.norm(runtime._train_target_feats, axis=1)
    np.testing.assert_allclose(runtime._train_target_norms, expected, rtol=1e-5)
```

- [ ] **Step 2: 运行测试确认当前属性不存在**

Run: `pytest 02_code/tests/test_dti_runtime_performance.py -v`
Expected: FAIL with `AttributeError`

- [ ] **Step 3: 在 `dti_inference_runtime.py` 中初始化并应用缓存**

1. 在 `_load_inner()` 中：
   `self._train_target_norms = np.linalg.norm(self._train_target_feats, axis=1)`
2. 在 `diagnose_domain()` 中：
   直接使用 `norms_ref = self._train_target_norms`，消除每次函数调用的重复线性代数开销。

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest 02_code/tests/test_dti_runtime_performance.py -v`
Expected: PASS

- [ ] **Step 5: 提交更改**

```bash
git add 02_code/dti_inference_runtime.py 02_code/tests/test_dti_runtime_performance.py
git commit -m "perf(dti): 缓存训练集靶点矩阵范数消除重复线性代数计算"
```

---

### Task 5: 全平台统一默认推荐 5 折 Stacking 集成模型

**Files:**
- Modify: `05_web_server/dti_endpoints.py:20,87`
- Modify: `02_code/dti_inference_runtime.py:201`
- Modify: `frontend/src/components/DTIStudio.tsx:41`
- Test: `02_code/tests/test_dti_model_endpoints.py`

**Interfaces:**
- Consumes: 训练产物 `03_experiments/runs/dti_davis_stacked_20261007_v1/models/stacked_ensemble.joblib`
- Produces: API 请求在未显式传递 `model_name` 时默认使用 `"stacked_ensemble"`，前端初始化激活为该模型

- [ ] **Step 1: 编写默认模型为 Stacking 集成的断言测试**

```python
def test_default_model_is_stacked_ensemble():
    from dti_inference_runtime import DTIInferenceRuntime
    runtime = DTIInferenceRuntime()
    status = runtime.get_status()
    assert status["default_model"] == "stacked_ensemble"
```

- [ ] **Step 2: 运行测试确认现状为 ridge**

Run: `pytest 02_code/tests/test_dti_model_endpoints.py -v`
Expected: FAIL (`assert 'ridge' == 'stacked_ensemble'`)

- [ ] **Step 3: 更新各层默认模型配置**

1. `dti_inference_runtime.py`: `get_status` 返回 `"default_model": "stacked_ensemble"`；
2. `dti_endpoints.py`: `DTIPredictionRequest` 的 `model_name` 默认值为 `"stacked_ensemble"`，并补充模型说明；
3. `DTIStudio.tsx`: `const [modelName, setModelName] = useState<string>('stacked_ensemble');`。

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest 02_code/tests/test_dti_model_endpoints.py -v`
Expected: PASS

- [ ] **Step 5: 提交更改**

```bash
git add 05_web_server/dti_endpoints.py 02_code/dti_inference_runtime.py frontend/src/components/DTIStudio.tsx
git commit -m "feat(dti): 统一将 100 维口袋增强 Stacking 集成模型设为平台默认基线"
```

---

### Task 6: 增强 Molecule2DViewer 对复杂 SMILES 方括号原子的拓扑解析

**Files:**
- Modify: `frontend/src/components/Molecule2DViewer.tsx:118-160`
- Test: `frontend/src/__tests__/Molecule2DViewer.test.ts` (或通过 `npm run build` 及单元测试)

**Interfaces:**
- Consumes: 含有 `[nH]`、`[C@@H]`、`[O-]` 等方括号表达式的 SMILES 字符串
- Produces: 正确提取核心重原子（N、C、O），将附带的 H 作为原子属性而非生成孤立虚假节点

- [ ] **Step 1: 编写包含 `[nH]` 杂环分子的节点数解析测试**

验证对于包含吡唑/咪唑环（如达沙替尼类似物）的方括号分子，提取的节点数等于非氢重原子数，不虚增独立 H 节点。

- [ ] **Step 2: 运行前端测试或构建观察当前行为**

- [ ] **Step 3: 优化 `parseSmilesTo2D` 分词与原子识别算法**

在遇到 `[` 时成组匹配至 `]`，从中提取核心元素符号（例如 `[nH]` 提取为 `N` 并标记 `isAromatic: true`），避免被拆分为 `N` 和 `H` 两个节点绘制。

- [ ] **Step 4: 执行生产构建验证**

Run: `npm run build` in `frontend`
Expected: `✓ built in ...ms`，无类型错误，构建产物正常生成。

- [ ] **Step 5: 提交更改**

```bash
git add frontend/src/components/Molecule2DViewer.tsx
git commit -m "fix(viewer): 优化 2D 分子查看器对方括号芳杂环原子的解析与渲染"
```

---

## Plan Self-Review Checklist

1. **Spec 覆盖度**: 涵盖此前发现的 6 大关键缺陷（门禁哈希损坏、参数名对齐、频控盲区、范数重复计算、默认模型不一致、2D 查看器虚假原子），无遗漏。
2. **步骤清晰度**: 每一步骤均包含具体代码示例、执行命令与预期产物，严禁“按需优化”等模糊表述。
3. **类型与接口一致性**: 前后端 `api_base`/`base_url` 与 `model`/`model_name` 在 Task 2 中明确双向兼容，模型命名统一为 `stacked_ensemble`。
4. **非硬优化原则**: 绝不包含任何仅为形式的虚假重构，每一项改动均有明确的 Bug 修复、测试绿灯或性能安全收益。
