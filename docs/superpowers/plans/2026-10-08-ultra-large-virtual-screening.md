# Ultra-Large Virtual Screening Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建针对人类激酶组及耐药突变体的超大规模虚拟筛选引擎，支持商业现货分子库的高通量矢量化初筛、物理-AI 双核重排精筛、Butina 化学多样性骨架聚类以及前端交互式 Hits 发现看板与一键湿法投产闭环。

**Architecture:** 采用三级递进式漏斗架构 (Hierarchical Cascade Funnel)：第一级基于 2048-bit 摩根指纹位运算与轻量模型进行极速粗筛（>10,000 cpd/s）；第二级通过第二代世界模型 (Stacked Ensemble) 与 MM-GBSA 物理能深度精评亲和力与成药性；第三级通过 Butina 聚类算法剔除同质化骨架并保留多样性代表物。前后端打通 REST API 与交互式工作台。

**Tech Stack:** Python 3.11, FastAPI, NumPy, Scikit-learn, RDKit/Morgan Fingerprints, PyTest, React, TypeScript, Tailwind CSS, Lucide Icons, Playwright.

**Spec:** [docs/superpowers/plans/2026-10-08-ultra-large-virtual-screening.md](file:///d:/桌面文件/sci/docs/superpowers/plans/2026-10-08-ultra-large-virtual-screening.md)

## Global Constraints

- 严禁裸露多行 LaTeX 复杂环境；公式统一使用行内单美元符号或清晰 Markdown 原生等式列表。
- 加粗符号 `**` 必须置于数学符号外部。
- 采用 Windows PowerShell (pwsh) 规范语法，所有路径使用双引号包裹，严禁直接写入 C 盘根目录。
- 保证测试门禁 `python 02_code/check_mic_project.py --scope current` 维持 Exit 0。
- 保证 Vite 生产构建与 Playwright E2E UI 测试（Exit 0）无未捕获控制台错误。

## Review Focus

1. **大规模分子库吞吐量与内存占用**：避免在 Python 循环中反复构造对象，采用 NumPy 稀疏/密集矩阵批处理广播计算。
2. **极端非活性/弱亲和力分子下潜**：对低活性分子正确截断，防止无效计算消耗服务器资源。
3. **聚类代表物多样性保证**：Butina 聚类应有效聚出至少 3~8 个不同化学母核，防止单一先导化合物占据所有 Hits。
4. **耐药突变靶点敏感性**：面对 ABL1-T315I 或 EGFR-T790M 时，筛选引擎能够优先选出能穿透门控残基的刚性分子（如炔基/刚性骨架化合物）。
5. **端到端一键流转可用性**：筛选出的 Top Hits 能够一键跳转至 3D 口袋视窗、AI 逆合成规划或 96 孔板点样。

---

### Task 1: 商业化合物库资产与虚拟筛选核心算法引擎 (Virtual Screening Engine)

**Files:**
- Create: `02_code/virtual_screening_engine.py`
- Test: `02_code/tests/test_virtual_screening.py`

- [ ] **Step 1.1**: 编写单元测试 `test_virtual_screening.py`，覆盖：
  - 内置商业分子库（Enamine HTS 多样性库、Kinase-Privileged 特权骨架库、FDA 衍生库）读取与元数据校验；
  - 矢量化极速粗筛阶段的吞吐与候选截断；
  - 双核深度精筛阶段的 pKd/Kd、MM-GBSA 物理能与 SA 分值计算；
  - Butina 拓扑多样性聚类算法及簇代表物选择；
  - 针对 ABL1-T315I 耐药靶点的敏感性筛选测试。
- [ ] **Step 1.2**: 运行测试确保初始状态测试未就绪或报错。
- [ ] **Step 1.3**: 编写 `02_code/virtual_screening_engine.py`：
  - 构建预置商业分子库字典 `PRESET_SCREENING_LIBRARIES`，内置 Enamine、Kinase-Privileged 等高品质现货分子及 CAS 编号；
  - 实现 `ScreeningEngine` 类与 `screen_virtual_library` 函数；
  - 实现矢量化摩根指纹批量生成与矩阵乘法快速打分；
  - 实现双核精筛过滤（结合 `DTIInferenceRuntime` 与 `thermodynamic_physics_engine`）；
  - 实现基于 Tanimoto 距离矩阵的 Butina 骨架聚类算法，输出聚类簇 ID、母核骨架代表物与 Hits 排名；
  - 提供亲和力分布与多样性统计指标。
- [ ] **Step 1.4**: 运行 `pytest 02_code/tests/test_virtual_screening.py -v` 验证全部测试通过。
- [ ] **Step 1.5**: 暂存并提交代码：`git commit -m "feat(screening): 实现超大规模虚拟筛选引擎与Butina多样性聚类"`。

---

### Task 2: REST API 端点扩展与接口联调

**Files:**
- Modify: `05_web_server/dti_endpoints.py`
- Modify: `02_code/tests/test_virtual_screening.py`

- [ ] **Step 2.1**: 在 `test_virtual_screening.py` 中添加 TestClient API 接口集成测试用例：
  - `GET /api/dti/screening_libraries`；
  - `POST /api/dti/virtual_screen`。
- [ ] **Step 2.2**: 在 `05_web_server/dti_endpoints.py` 中引入 `ScreeningEngine`：
  - 定义 Pydantic 请求模型 `VirtualScreeningRequest`；
  - 添加 `GET /api/dti/screening_libraries` 路由；
  - 添加 `POST /api/dti/virtual_screen` 路由，支持流式或异步高通量调用。
- [ ] **Step 2.3**: 运行 pytest 验证 API 端点测试通过。
- [ ] **Step 2.4**: 暂存并提交代码：`git commit -m "feat(api): 接入虚拟筛选与分子库查询路由端点"`。

---

### Task 3: 前端客户端接口与虚拟筛选交互工作台组件

**Files:**
- Modify: `frontend/src/api/dtiClient.ts`
- Create: `frontend/src/components/VirtualScreeningModal.tsx`
- Modify: `frontend/src/components/DTIStudio.tsx`
- Modify: `frontend/src/components/LeadOptimizerStudio.tsx`

- [ ] **Step 3.1**: 在 `frontend/src/api/dtiClient.ts` 中导出 `ScreeningLibraryMeta`、`VirtualScreeningHit`、`VirtualScreeningResult` 接口，并导出 `fetchScreeningLibraries` 与 `runVirtualScreening` 方法。
- [ ] **Step 3.2**: 开发 `frontend/src/components/VirtualScreeningModal.tsx`：
  - 参数面板：靶点选择、分子库切换、亲和力截断阈值（$K_d \le 100\text{ nM}$）、输出 Hits 数；
  - 计算状态：动态进度条、扫描速率（cpd/s）、命中率指示；
  - 数据可视化：散点图（亲和力 vs 分子量 / cLogP）、簇分类比例条；
  - Top Hits 列表：展示 2D 结构式、SMILES 复制、pKd/Kd、MM-GBSA 能动、SA 评分、所属多样性簇；
  - 联动操作：支持「查看 3D 口袋构象」、「AI 逆合成规划」、「载入 96 孔板点样」。
- [ ] **Step 3.3**: 在 `DTIStudio.tsx` 与 `LeadOptimizerStudio.tsx` 的工具栏挂载「🚀 超大规模虚拟筛选」入口与流转逻辑。
- [ ] **Step 3.4**: 运行 `npm run build`，确保 TypeScript 严格模式 0 报错，Vite 编译通过。
- [ ] **Step 3.5**: 暂存并提交代码：`git commit -m "feat(ui): 交付虚拟筛选与Hits发现交互工作台"`。

---

### Task 4: Playwright E2E UI 自动化测试、科研门禁与交付归档

**Files:**
- Modify: `frontend/scripts/run_e2e_ui_test.mjs`
- Modify: `C:\Users\888\.gemini\antigravity\brain\b13186b1-cf67-48df-823a-3edc35a099cb\three_phase_evolution_development_plan.md`

- [ ] **Step 4.1**: 在 `frontend/scripts/run_e2e_ui_test.mjs` 中添加超大规模虚拟筛选自动化测试步骤：
  - 点击「超大规模虚拟筛选」按钮呼出模态框；
  - 选择分子库并启动筛选计算；
  - 等待进度完成并验证 Top Hits 卡片与聚类分布渲染；
  - 截取快照 `20_ultra_large_virtual_screening.png` 与 `21_virtual_screening_hits_explorer.png`。
- [ ] **Step 4.2**: 运行全套 Playwright E2E 自动化测试，验证 0 控制台未捕获异常并生成快照。
- [ ] **Step 4.3**: 运行科研门禁脚本 `python 02_code/check_mic_project.py --scope current` 确保 Exit 0。
- [ ] **Step 4.4**: 更新全景交付计划文档 `three_phase_evolution_development_plan.md`。
- [ ] **Step 4.5**: 执行 Git Commit 归档第三阶段全部交付物。
