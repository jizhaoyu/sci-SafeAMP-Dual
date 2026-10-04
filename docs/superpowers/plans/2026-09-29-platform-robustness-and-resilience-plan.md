# SafeAMP-Dual 平台鲁棒性、高弹性与工程健壮性实施计划书 (Platform Robustness & Resilience Implementation Plan)

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建高并发、强容错、持久化缓存与端到端可观测的 SafeAMP-Dual 计算生物学科研工程平台，解决多肽重复提取计算开销大、超长批处理连接超时、大矩阵全对齐内存风险以及缺乏请求审计链路的问题。

**Architecture:** 采用“分层多级缓存 + 异步任务流水线 + 稀疏分块拓扑流 + 统一请求审计追踪”架构。在特征层建立基于序列规范化哈希的内存+磁盘二级 LRU 缓存；在服务端建立基于异步任务池与 SSE 流式推送的批量高通量预测引擎；在算法层将 $O(N^2)$ 全矩阵对齐改造为分块稀疏流式并查集；在网关层建立全链路 `request_id` 结构化审计日志；在前端提供作业管理与进度监视，并在每次开发收尾强制执行 `codegraph sync` 保持代码知识图谱实时同步。

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, PyTorch, fair-esm, NumPy, Pandas, SQLite/DiskCache, React 18, TypeScript, Tailwind CSS, Lucide Icons, Vite, pytest, CodeGraph CLI.

## Global Constraints

- **语言与编码**：代码注释与文档默认采用中文，涉及文件读写强制使用 UTF-8 编码。
- **数学与公式**：严禁裸露多行 LaTeX 环境（严禁 `\begin{aligned}` 等），推导过程采用 Markdown 列表与单行标准等式。
- **运行环境**：终端必须遵循 Windows PowerShell (pwsh) 语法，路径必须使用双引号包裹，严禁使用 Linux/Bash 专有指令。
- **存储边界**：所有临时缓存、产物日志必须存放在当前工作区 `D:\桌面文件\sci\` 内，严禁未经许可在 C 盘根目录写大文件。
- **学术诚信与门禁**：所有优化必须保持既定生物物理计算逻辑与 Needleman-Wunsch 严格数学一致性，严禁绕过 `research_feasibility` 科学门禁。
- **CodeGraph 强制规则**：**每次按照文档任务开发完成后，必须执行 `codegraph sync` 更新图谱**。

---

## 模块结构与文件权责映射 (File Structure & Responsibilities)

| 文件路径 | 职责与归属 |
| :--- | :--- |
| `02_code/feature_cache.py` (新增) | 序列特征多级缓存：内存 LRU + SQLite 磁盘持久化，支持线程安全与指标统计 |
| `02_code/batch_task_manager.py` (新增) | 异步批量作业管理器：管理大批量预测任务队列、生命周期、状态轮询与流式事件生成 |
| `02_code/isolation_diagnostics.py` (修改) | 增加大序列集合分块计算 (Chunked Pair Processing) 与稀疏流式并查集支持 |
| `02_code/audit_logger.py` (新增) | 结构化请求审计日志中间件：全局 `request_id` 生成、耗时分析与安全日志记录 |
| `05_web_server/research_api.py` (修改) | 挂载审计日志中间件、异步作业 API 路由 (`/api/batch_jobs`) 与 SSE 流式接口 |
| `02_code/tests/test_robustness_features.py` (新增) | 针对缓存、异步作业管理器、异常输入的针对性健壮性自动化测试集 |
| `frontend/src/pages/ScreeningStudio.tsx` (修改) | 增强高通量大批量任务提交、异步轮询与实时进度展示 |
| `docs/handoff/TASK_STATE.md` (修改) | 任务状态与 CodeGraph 知识图谱同步记录 |

---

## 阶段任务详细拆解 (Tasks)

### Task 1: 序列理化与 ESM-2 嵌入多级缓存引擎 (`feature_cache.py`)

**Files:**
- Create: `02_code/feature_cache.py`
- Test: `02_code/tests/test_feature_cache.py`

**Interfaces:**
- Consumes: `feature_extractor.clean_sequence`, `feature_extractor.extract_handcrafted_features`, `feature_extractor.ESMFeatureExtractor`
- Produces: `SequenceFeatureCache` (方法: `get_or_compute(seq: str, extractor: ESMFeatureExtractor) -> Tuple[np.ndarray, np.ndarray, np.ndarray]`, `get_stats() -> dict`)

- [ ] **Step 1: 编写多级缓存引擎的单元失败测试**

在 `02_code/tests/test_feature_cache.py` 中编写测试：

```python
import pytest
import numpy as np
from pathlib import Path
import tempfile
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '02_code'))
from feature_cache import SequenceFeatureCache

def test_cache_miss_and_hit(tmp_path):
    cache = SequenceFeatureCache(cache_dir=tmp_path / 'cache', max_memory_items=5)
    seq = "GIGAVLKVLTTGLPALISWIKRKRQQ"
    
    # 模拟计算函数
    call_count = 0
    def mock_compute(s):
        nonlocal call_count
        call_count += 1
        return np.ones(320, dtype=np.float32), np.ones((len(s), 320), dtype=np.float32), np.zeros(44, dtype=np.float32)
    
    # 第一次查询：Cache Miss
    p1, r1, h1 = cache.get_or_compute(seq, compute_fn=mock_compute)
    assert call_count == 1
    assert p1.shape == (320,)
    assert h1.shape == (44,)
    
    # 第二次查询：Cache Hit (内存命中)
    p2, r2, h2 = cache.get_or_compute(seq, compute_fn=mock_compute)
    assert call_count == 1  # 不应触发重新计算
    np.testing.assert_array_equal(p1, p2)
    
    # 统计数据校验
    stats = cache.get_stats()
    assert stats['hits'] == 1
    assert stats['misses'] == 1
```

- [ ] **Step 2: 运行测试验证失败**

运行指令：
```powershell
python -B -m pytest 02_code/tests/test_feature_cache.py -v
```
预期结果：FAIL（`ModuleNotFoundError: No module named 'feature_cache'`）。

- [ ] **Step 3: 编写多级缓存引擎实现代码**

创建 `02_code/feature_cache.py`：

```python
"""
feature_cache.py
多肽序列特征的多级缓存体系 (内存 OrderedDict LRU + 本地 SQLite/文件持久化)
保证相同分子的 ESM-2 嵌入与理化特征毫秒级命中，避免重复计算耗竭 CPU/显存。
"""
from collections import OrderedDict
import hashlib
import json
from pathlib import Path
import threading
from typing import Callable, Dict, Optional, Tuple
import numpy as np
from feature_extractor import clean_sequence, extract_handcrafted_features
from research_utils import ROOT

class SequenceFeatureCache:
    def __init__(self, cache_dir: Optional[Path] = None, max_memory_items: int = 512):
        self.cache_dir = Path(cache_dir or (ROOT / 'output' / 'cache' / 'features'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_memory_items = max_memory_items
        self._lock = threading.Lock()
        self._memory_cache: OrderedDict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _hash_key(self, seq: str) -> str:
        cleaned = clean_sequence(seq)
        return hashlib.sha256(cleaned.encode('utf-8')).hexdigest()

    def get_or_compute(
        self,
        seq: str,
        compute_fn: Optional[Callable[[str], Tuple[np.ndarray, np.ndarray, np.ndarray]]] = None,
        extractor = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        cleaned = clean_sequence(seq)
        key = self._hash_key(cleaned)
        
        # 1. 尝试从内存缓存中读取
        with self._lock:
            if key in self._memory_cache:
                self._hits += 1
                self._memory_cache.move_to_end(key)
                return self._memory_cache[key]
                
        # 2. 尝试从磁盘持久化缓存读取 (.npz)
        disk_file = self.cache_dir / f"{key[:2]}/{key}.npz"
        if disk_file.is_file():
            try:
                data = np.load(disk_file)
                pooled = data['pooled']
                residue = data['residue']
                phys = data['phys']
                with self._lock:
                    self._hits += 1
                    self._put_memory(key, (pooled, residue, phys))
                return pooled, residue, phys
            except Exception:
                pass  # 若文件损坏则重新计算
                
        # 3. Cache Miss: 执行计算
        with self._lock:
            self._misses += 1
            
        if compute_fn is not None:
            pooled, residue, phys = compute_fn(cleaned)
        else:
            if extractor is None:
                raise ValueError("Either compute_fn or extractor must be provided.")
            pooled, residue = extractor.extract_sequence_embedding(cleaned)
            phys = extract_handcrafted_features(cleaned)
            
        # 4. 回写内存与磁盘
        with self._lock:
            self._put_memory(key, (pooled, residue, phys))
            
        try:
            disk_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = disk_file.with_suffix('.tmp.npz')
            np.savez_compressed(temp_file, pooled=pooled, residue=residue, phys=phys)
            temp_file.replace(disk_file)
        except Exception:
            pass  # 磁盘写入失败不阻断业务
            
        return pooled, residue, phys

    def _put_memory(self, key: str, value: Tuple[np.ndarray, np.ndarray, np.ndarray]):
        if key in self._memory_cache:
            self._memory_cache.move_to_end(key)
        else:
            self._memory_cache[key] = value
            if len(self._memory_cache) > self.max_memory_items:
                self._memory_cache.popitem(last=False)

    def get_stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                'hits': self._hits,
                'misses': self._misses,
                'memory_items': len(self._memory_cache),
                'total_queries': self._hits + self._misses
            }
```

- [ ] **Step 4: 运行测试并验证通过**

运行指令：
```powershell
python -B -m pytest 02_code/tests/test_feature_cache.py -v
```
预期结果：PASS。

- [ ] **Step 5: 更新 CodeGraph 索引**

运行指令：
```powershell
codegraph sync
```
预期输出：`[OK] Index is up to date`。

---

### Task 2: 异步大批量任务流水线与 SSE 流式推送 (`batch_task_manager.py`)

**Files:**
- Create: `02_code/batch_task_manager.py`
- Modify: `05_web_server/research_api.py`
- Test: `02_code/tests/test_batch_task_manager.py`

**Interfaces:**
- Consumes: `feature_cache.SequenceFeatureCache`, `research_api.validate_sequence`, `inference_runtime.ResearchRuntime`
- Produces: `BatchTaskManager` (方法: `submit_batch(sequences: List[str]) -> str`, `get_job_status(job_id: str) -> dict`, `stream_job_events(job_id: str) -> AsyncGenerator`), 挂载 `/api/batch_jobs` 路由

- [ ] **Step 1: 编写批量异步管理器的失败单元测试**

在 `02_code/tests/test_batch_task_manager.py` 中编写测试：

```python
import pytest
import time
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '02_code'))
from batch_task_manager import BatchTaskManager, BatchJobStatus

def test_batch_job_lifecycle():
    mgr = BatchTaskManager(max_workers=2)
    seqs = ["GIGAVLKVLTTGLPALISWIKRKRQQ", "ACDEFGHIKLMNPQRSTVWY"]
    
    # 提交作业
    job_id = mgr.submit_job(seqs, worker_fn=lambda s: {"seq": s, "score": 0.85})
    assert job_id is not None
    
    # 轮询直至完成
    for _ in range(50):
        status = mgr.get_status(job_id)
        if status['status'] in (BatchJobStatus.COMPLETED, BatchJobStatus.FAILED):
            break
        time.sleep(0.05)
        
    assert status['status'] == BatchJobStatus.COMPLETED
    assert status['total'] == 2
    assert status['completed'] == 2
    assert len(status['results']) == 2
```

- [ ] **Step 2: 运行测试验证失败**

运行指令：
```powershell
python -B -m pytest 02_code/tests/test_batch_task_manager.py -v
```
预期结果：FAIL（`ModuleNotFoundError: No module named 'batch_task_manager'`）。

- [ ] **Step 3: 实现批量作业管理器 `batch_task_manager.py`**

创建 `02_code/batch_task_manager.py`：

```python
"""
batch_task_manager.py
大批量多肽预测异步队列与状态跟踪器。
支持解耦长耗时 HTTP 请求、作业进度实时流式推送与取消机制。
"""
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

class BatchJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class BatchTaskManager:
    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="SafeAMP-Worker")
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def submit_job(self, sequences: List[str], worker_fn: Callable[[str], Any]) -> str:
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        now = time.time()
        job_data = {
            "job_id": job_id,
            "status": BatchJobStatus.QUEUED,
            "created_at": now,
            "updated_at": now,
            "total": len(sequences),
            "completed": 0,
            "failed_count": 0,
            "results": [],
            "errors": [],
            "_cancel_flag": False
        }
        with self._lock:
            self._jobs[job_id] = job_data
            
        self._executor.submit(self._execute_job, job_id, sequences, worker_fn)
        return job_id

    def _execute_job(self, job_id: str, sequences: List[str], worker_fn: Callable[[str], Any]):
        with self._lock:
            if job_id not in self._jobs or self._jobs[job_id]["_cancel_flag"]:
                return
            self._jobs[job_id]["status"] = BatchJobStatus.RUNNING
            self._jobs[job_id]["updated_at"] = time.time()

        for idx, seq in enumerate(sequences):
            with self._lock:
                if self._jobs[job_id]["_cancel_flag"]:
                    self._jobs[job_id]["status"] = BatchJobStatus.CANCELLED
                    return
                    
            try:
                item_result = worker_fn(seq)
                with self._lock:
                    self._jobs[job_id]["results"].append(item_result)
                    self._jobs[job_id]["completed"] += 1
                    self._jobs[job_id]["updated_at"] = time.time()
            except Exception as exc:
                with self._lock:
                    self._jobs[job_id]["failed_count"] += 1
                    self._jobs[job_id]["errors"].append({
                        "index": idx,
                        "sequence": seq[:15] + "...",
                        "error": str(exc)
                    })
                    self._jobs[job_id]["completed"] += 1
                    self._jobs[job_id]["updated_at"] = time.time()

        with self._lock:
            if not self._jobs[job_id]["_cancel_flag"]:
                self._jobs[job_id]["status"] = BatchJobStatus.COMPLETED
                self._jobs[job_id]["updated_at"] = time.time()

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if job_id not in self._jobs:
                return None
            job = self._jobs[job_id]
            return {k: v for k, v in job.items() if not k.startswith('_')}

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs and self._jobs[job_id]["status"] in (BatchJobStatus.QUEUED, BatchJobStatus.RUNNING):
                self._jobs[job_id]["_cancel_flag"] = True
                self._jobs[job_id]["status"] = BatchJobStatus.CANCELLED
                return True
        return False
```

- [ ] **Step 4: 将异步作业路由挂载至 `05_web_server/research_api.py`**

在 `research_api.py` 中引入 `batch_task_manager`，挂载端点：
- `POST /api/batch_jobs`（提交超过 128 条或需长程计算的批量任务）
- `GET /api/batch_jobs/{job_id}`（查询作业进度与已解析结果）
- `DELETE /api/batch_jobs/{job_id}`（取消任务）

- [ ] **Step 5: 运行全套单元测试并验证通过**

运行指令：
```powershell
python -B -m pytest 02_code/tests/test_batch_task_manager.py 02_code/tests/test_runtime_api.py -v
```
预期结果：PASS。

- [ ] **Step 6: 同步更新 CodeGraph 知识图谱**

运行指令：
```powershell
codegraph sync
```
预期输出：`[OK] Index is up to date`。

---

### Task 3: 超大序列全矩阵拓扑分块与流式并查集 (`isolation_diagnostics.py`)

**Files:**
- Modify: `02_code/isolation_diagnostics.py:120-220`
- Test: `02_code/tests/test_isolation_diagnostics.py`

**Interfaces:**
- Consumes: `isolation_diagnostics.production_needleman_wunsch`, `isolation_diagnostics.can_exceed_cutoff`
- Produces: `chunked_all_pairs_diagnostics(sequences: List[str], cutoff: float, chunk_size: int = 5000) -> Iterator[Tuple[int, int, float]]`, 流式连通分量更新

- [ ] **Step 1: 编写分块诊断与流式并查集的回归测试**

在 `02_code/tests/test_isolation_diagnostics.py` 增补测试：

```python
def test_chunked_all_pairs_consistency():
    seqs = ["GIGAVLKVLTTGLPALISWIKRKRQQ", "KKLRLKIAFK", "ADAD", "KKAKRRLLKK"]
    # 验证常规计算与分块计算边数与连通分量完全一致
    regular = compute_all_pair_metrics(seqs, cutoff=0.40)
    chunked = list(chunked_all_pairs_diagnostics(seqs, cutoff=0.40, chunk_size=2))
    assert len(regular['edges']) == len(chunked)
```

- [ ] **Step 2: 运行测试验证失败**

运行指令：
```powershell
python -B -m pytest 02_code/tests/test_isolation_diagnostics.py -v
```
预期结果：FAIL（`NameError: name 'chunked_all_pairs_diagnostics' is not defined`）。

- [ ] **Step 3: 在 `isolation_diagnostics.py` 中实现分块生成器**

编写分块生成器，当对齐对数极大时不一次性在内存中堆叠全部字典，而是按生成器流式产出高于 cutoff 的边，直接喂给并查集 `DisjointSet` 更新分组，将内存占用从 $O(N^2)$ 压降至 $O(N + E)$。

- [ ] **Step 4: 运行测试并验证通过**

运行指令：
```powershell
python -B -m pytest 02_code/tests/test_isolation_diagnostics.py -v
```
预期结果：PASS。

- [ ] **Step 5: 同步更新 CodeGraph 知识图谱**

运行指令：
```powershell
codegraph sync
```
预期输出：`[OK] Index is up to date`。

---

### Task 4: 请求追踪中间件与结构化审计日志 (`audit_logger.py`)

**Files:**
- Create: `02_code/audit_logger.py`
- Modify: `05_web_server/research_api.py`
- Test: `02_code/tests/test_audit_logger.py`

**Interfaces:**
- Consumes: FastAPI Request/Response lifecycle
- Produces: `AuditLogMiddleware` (注入 `X-Request-ID` 响应头，流式写入 `output/audit/api_audit.jsonl`)

- [ ] **Step 1: 编写结构化审计日志测试**

在 `02_code/tests/test_audit_logger.py` 中编写测试：

```python
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '02_code'))
sys.path.insert(0, str(ROOT / '05_web_server'))
import research_api

def test_request_id_and_audit_log(tmp_path, monkeypatch):
    audit_file = tmp_path / 'audit.jsonl'
    monkeypatch.setattr('audit_logger.AUDIT_LOG_FILE', audit_file)
    client = TestClient(research_api.app)
    
    resp = client.get('/api/system_status')
    assert 'X-Request-ID' in resp.headers
    request_id = resp.headers['X-Request-ID']
    assert len(request_id) >= 8
    
    # 验证日志记录完整性
    assert audit_file.exists()
    lines = audit_file.read_text(encoding='utf-8').strip().split('\n')
    last_log = json.loads(lines[-1])
    assert last_log['request_id'] == request_id
    assert last_log['method'] == 'GET'
    assert last_log['path'] == '/api/system_status'
    assert last_log['status_code'] == 200
```

- [ ] **Step 2: 运行测试验证失败**

运行指令：
```powershell
python -B -m pytest 02_code/tests/test_audit_logger.py -v
```
预期结果：FAIL（`ModuleNotFoundError: No module named 'audit_logger'`）。

- [ ] **Step 3: 实现 `02_code/audit_logger.py` 并装载至 FastAPI**

创建 `audit_logger.py`：
- 生成标准 UUID4 作为 `request_id`；
- 记录请求方法、URL、客户端 IP、处理耗时（毫秒）、HTTP 状态码；
- 异常时记录异常类型与概要；
- 在 `research_api.py` 中添加 `app.add_middleware(AuditLogMiddleware)`。

- [ ] **Step 4: 运行测试并验证通过**

运行指令：
```powershell
python -B -m pytest 02_code/tests/test_audit_logger.py 02_code/tests/test_runtime_api.py -v
```
预期结果：PASS。

- [ ] **Step 5: 同步更新 CodeGraph 知识图谱**

运行指令：
```powershell
codegraph sync
```
预期输出：`[OK] Index is up to date`。

---

### Task 5: 前端大批量任务异步监视与导出增强

**Files:**
- Modify: `frontend/src/pages/ScreeningStudio.tsx`
- Modify: `frontend/src/components/ResearchStudio.tsx`
- Test: `frontend/src/api/client.ts`

**Interfaces:**
- Consumes: 后端 `/api/batch_jobs` 接口
- Produces: 前端批量进度条组件、分片提交与失效应急导出功能

- [ ] **Step 1: 前端增补批量作业状态查询 API**

在 `frontend/src/api/client.ts` 中增加 `submitBatchJob(sequences: string[])` 与 `getBatchJob(jobId: string)` 请求函数。

- [ ] **Step 2: 在 `ResearchStudio.tsx` 中增加异步进度条与状态展示**

当提交序列数量超过 30 条时，自动切换为异步作业模式，展示动效进度条（`completed / total`）、耗时统计及异常项单独展开查看。

- [ ] **Step 3: 运行前端构建校验**

运行指令：
```powershell
cd frontend
npm run build
npm run lint
```
预期结果：0 errors, production bundle 构建成功。

- [ ] **Step 4: 同步更新 CodeGraph 知识图谱**

运行指令：
```powershell
codegraph sync
```
预期输出：`[OK] Index is up to date`。

---

### Task 6: 终期全系统回归审计与看板更新

**Files:**
- Modify: `docs/handoff/TASK_STATE.md`
- Output: `output/verification/pytest.txt`

**Interfaces:**
- Consumes: 全部测试套件
- Produces: 全系统验证报告、更新后的 CodeGraph 数据库与状态看板

- [ ] **Step 1: 执行全量测试套件**

运行指令：
```powershell
python -B -m pytest 02_code/tests 02_code/test_helical_wheel.py -p no:cacheprovider -v
```
预期结果：全量测试 100% 通过（0 失败）。

- [ ] **Step 2: 重新编译并检查字节码**

运行指令：
```powershell
python -m compileall 02_code 05_web_server
```
预期结果：全部通过，0 语法错误。

- [ ] **Step 3: 落实 CodeGraph 铁律同步**

运行指令：
```powershell
codegraph sync
codegraph status
```
预期结果：`[OK] Index is up to date`。

- [ ] **Step 4: 更新交接看板 `docs/handoff/TASK_STATE.md`**

将健壮性加固指标（缓存命中率、异步任务吞吐量、测试覆盖数）同步写入看板。
