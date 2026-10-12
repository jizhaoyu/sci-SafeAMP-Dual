# SafeAMP-Dual & DTI 全局文档体系总索引与科研知识枢纽
# Master Documentation Catalog & Knowledge Hub

## 2026-10-10 文档归档与当前 DTA 入口

当前文档总入口：[文档导航](../文档导航.md)。完整盘点、当前成果、历史版本快照和项目知识沉淀见 [20261010 归档总览](归档沉淀/20261010/00_归档总览.md)。

本页下方保留既有平台说明和历史状态，不以旧稿中的模型名称、分数或冻结声明替代当前 DTA 验收及论文证据。当前中文全稿仍待作者审阅，交付整改通过不等于投稿或科学确认通过。

> **最后更新时间**: 2026-10-07 17:45 (UTC+8)  
> **代码库根目录**: `D:/桌面文件/sci/`  
> **系统当前状态**: 
> * **DTI 激酶亲和力基准与改构平台**: **正式冻结并已上线运行** (Protocol `protocol-dti-01`, 5折 Stacking 训练完成，5/5 密码学审计 PASS)；
> * **SafeAMP-Dual 历史多肽双任务**: 历史冻结保留状态 (`blocked`，受密码学审计保护，保持 100% 只读不可篡改)。

---

<!-- RESEARCH_STATUS_CURRENT_START -->
## 当前研究状态（机器生成）

状态来源：`03_experiments/audits/mic_training_readiness_20261004_v26.json`。生成时间：2026-10-04T07:17:45.230443+00:00（UTC）。
数据版本：`mic_goat_followup_release_20261004_v1`；数据目录：`03_experiments/audits/mic_goat_followup_release_20261004_v1`；审查协议：`protocol-mic-06`。
训练协议：`protocol-mic-13`；当前状态：`local_exploratory_training_independently_verified`。

| 状态 | 当前结论 |
|---|---|
| 证据准入 | 17 分子、42 条测定表述；6 阳性、11 阴性；ChMAP-28 新增准入，两条 mini-ChBac 因正负标签冲突未释放 |
| 全员及研究隔离 | 136 对、7 组件；固定三折 seed=42；跨折同源 0、跨折测量研究 0；各训练/验证含两类 |
| 训练执行 | 固定 LR/RF/Dummy 三折完成，9 个模型、51 条 OOF；training_blocked=false |
| 独立复核 | passed；禁止 fit，重载 9 模型并复算全部 OOF、指标及缩放器训练范围 |
| 原双任务 | blocked；protocol-amd-02；正式运行 none |
| 正式结果 / 投稿就绪 | false / false |

运行目录：`03_experiments/runs/mic_goat_baseline_20261004_v2`；复核：`03_experiments/audits/mic_goat_run_validation_20261004_v1.json`。
42 条为测定表格提及数，不代表 42 次独立实验。各分子只产生一个训练样本。
protocol-mic-12 首次运行因指标函数绑定缺失中断，失败产物保留；protocol-mic-13 仅修复技术入口，科学定义与参数不变。
原 16 分子已验证基线保留；以下旧正文为历史快照，不能覆盖本状态块或支撑当前证据放行。
本轮是历史性能已知后的小样本探索，没有独立外部验证、临床泛化或投稿批准。
<!-- RESEARCH_STATUS_CURRENT_END -->

<!-- PROJECT_CLOSEOUT_CURRENT_START -->
## 本批结案与交付（机器审计）

状态来源：`03_experiments/audits/project_closeout_20261005_v1/review/project_delivery_status.json`；生成时间：2026-10-05T05:05:20.652390+00:00（UTC）；版本：`project_closeout_20261005_v1`。
证据协议：`protocol-amd-02`；MIC训练协议：`protocol-mic-13`；MIC状态来源仍为`03_experiments/audits/mic_training_readiness_20261004_v26.json`。

- 本批外部证据审查：已结案；30条不准入、11条形式排除、37条缺原文归档；合格外部0，当前检索待办0。
- 跨队列隔离：`not_run_no_evidence_eligible_records`；没有把未执行记为通过。
- MIC探索工程交付：现有17样本/9模型/51OOF冻结包本轮复核通过，零fit，工作区外ZIP运行通过。
- 原双任务：`blocked`；原研究目标未完成；正式结果/投稿就绪：`false`/`false`。

交接入口：[项目收尾与交付指南](D:/桌面文件/sci/docs/handoff/PROJECT_CLOSEOUT_20261005.md)。证据结案表和本轮运行检查见状态来源所列目录；历史MIC机器状态块保留。
<!-- PROJECT_CLOSEOUT_CURRENT_END -->

## 快速导航与最新科研交付中心 (Executive Highlights)

* 📄 **学术论文手稿 (Full Manuscript)**: [MANUSCRIPT_DTI_DAVIS_STACKED_FRAMEWORK.md](file:///d:/桌面文件/sci/04_paper/MANUSCRIPT_DTI_DAVIS_STACKED_FRAMEWORK.md)  
  *《A Cryptographically Audited and Motif-Aware Stacking Framework for Kinase-Target Affinity Prediction and Generative Lead Optimization》*
* 📊 **项目执行与答辩简报 (Executive Brief)**: [EXECUTIVE_RESEARCH_BRIEF_20261007.md](file:///d:/桌面文件/sci/04_paper/EXECUTIVE_RESEARCH_BRIEF_20261007.md)
* 📜 **正式 DTI 基准协议主文**: [PROTOCOL_AMD_04_DTI_DAVIS_BENCHMARK.md](file:///d:/桌面文件/sci/docs/amendments/PROTOCOL_AMD_04_DTI_DAVIS_BENCHMARK.md)
* 🤖 **机器可读协议**: [protocol-dti-01.json](file:///d:/桌面文件/sci/03_experiments/protocols/protocol-dti-01.json)
* 🔬 **全流程有效性验证报告**: 包含密码学哈希、Y-Scrambling 标签置乱阴性对照、生物物理机制对齐、临床已知药靶盲测及 E2E 闭环测试。

---

## 一、文档体系结构全景图 (Documentation Architecture)

```
sci (项目根目录)
├── 04_paper/                          [模块 A: 学术成果、论文手稿与科研交付物]
│   ├── MANUSCRIPT_DTI_DAVIS_STACKED_FRAMEWORK.md   # 完整学术论文手稿 (英文)
│   ├── EXECUTIVE_RESEARCH_BRIEF_20261007.md         # 项目执行与答辩简报 (中英文)
│   ├── research_status.json                         # 历史状态守护文件 (密码学锁死)
│   └── reports/                                     # 历史小样本探索报告归档
│
├── docs/                              [模块 B: 科学协议、修订案与全局索引]
│   ├── DOCUMENTATION_INDEX.md                       # 【当前文件】全局文档总索引
│   ├── amendments/                                  # 前瞻性科学协议修订案
│   │   ├── PROTOCOL_AMD_04_DTI_DAVIS_BENCHMARK.md   # 核心: DTI DAVIS 激酶基准协议
│   │   ├── PROTOCOL_AMENDMENT_01_CDHIT.md           # 历史: CD-HIT 聚类规则
│   │   └── PROTOCOL_AMENDMENT_02_ALL_MEMBER.md      # 历史: 全员隔离协议
│   ├── superpowers/plans/                           # 各阶段实施计划与架构设计方案
│   │   ├── 2026-10-06-dti-kd-feasibility.md         # DTI 实测 Kd 数据可行性审计计划
│   │   ├── 2026-10-05-dual-task-model-readiness.md  # 双任务模型就绪计划
│   │   └── ...                                      # 历史各期整改与探索计划
│   └── handoff/                                     # 各阶段开发与交接指令
│
├── 03_experiments/                    [模块 C: 实验数据、特征矩阵、模型权重与审计]
│   ├── protocols/                                   # 机器可读协议 (JSON)
│   │   └── protocol-dti-01.json                     # 冻结的 DTI 机器可读协议
│   ├── prepared/                                    # 特征工程与预处理固定资产
│   │   ├── dti_davis_enhanced_features_20261007_v1/ # 100维激酶+2056维分子增强特征
│   │   └── dti_davis_features_20261006_v1/          # 28维激酶+2048维分子基准特征
│   ├── runs/                                        # 模型训练 Checkpoints 与预测结果
│   │   ├── dti_davis_stacked_20261007_v1/           # ★ 5折 Stacking 集成模型运行包
│   │   └── dti_davis_baselines_20261006_v1/         # 4大经典基线模型运行包
│   └── audits/                                      # 只追加的加密审计与复核目录
│       ├── dti_davis_stacked_verification_20261007_v2/ # Stacking 独立验证审计
│       ├── dti_davis_baseline_verification_20261006_v1/ # 基线独立验证审计
│       ├── dti_davis_isolation_review_20261006_v1/     # 双图块隔离可行性审计
│       └── dti_davis_acquisition_20261006_v2/          # 官方数据获取与校验
│
├── 02_code/                           [模块 D: 核心算法、特征工程与评估运行时]
│   ├── dti_inference_runtime.py                     # 推理运行时引擎 (双轨维度自适应)
│   ├── dti_stacked_model.py                         # Stacking 集成模型序列化解耦模块
│   ├── extract_dti_davis_enhanced_features.py       # 100维激酶催化口袋特征提取器
│   ├── train_dti_davis_stacked_ensemble.py          # 5折 OOF Stacking 集成训练主程序
│   ├── train_dti_davis_baselines.py                 # 经典四大基线训练程序
│   └── validate_dti_davis_stacked_run.py            # 独立密码学审计脚本
│
├── 05_web_server/                     [模块 E: FastAPI 容器与微服务网关]
│   ├── app.py                                       # 生产级 FastAPI 后端入口与 SPA 回退
│   ├── dti_endpoints.py                             # DTI 预测与 AI 改构 API 路由
│   └── research_api.py                              # 平台状态与系统信息路由
│
└── frontend/                          [模块 F: React 18 + Vite 交互工作台]
    ├── src/components/LeadOptimizerStudio.tsx       # AI 分子改构与进化工作台 (Tab 2)
    ├── src/components/DTIStudio.tsx                 # DTI 激酶亲和力全域推断实验室
    ├── src/components/Molecule2DViewer.tsx          # 纯前端 2D 化学骨架矢量渲染器
    ├── src/components/PeptideCartModal.tsx          # 多态分子暂存库 (支持小分子 CSV 导出)
    └── src/utils/cheminformatics.ts                 # Lipinski Ro5 成药性计算与导出工具
```

---

## 二、核心文档详述与快速跳转

### 1. 学术论文与科研交付物 (`04_paper/`)

| 文档名称 | 语言 | 核心作用与内容 | 链接 |
|---|---|---|---|
| **MANUSCRIPT_DTI_DAVIS_STACKED_FRAMEWORK.md** | 英文 | **学术论文正式手稿**。包含完整 Abstract、严格双盲隔离证明、100 维激酶结构域催化基序特征构建、5 折 OOF Stacking 元回归体系、四大域 Benchmark 对照表、达沙替尼/ABL1 实测案例分析。 | [查看手稿](file:///d:/桌面文件/sci/04_paper/MANUSCRIPT_DTI_DAVIS_STACKED_FRAMEWORK.md) |
| **EXECUTIVE_RESEARCH_BRIEF_20261007.md** | 中文 | **项目执行简报与答辩指南**。提炼全系统突破亮点、四大域全量对照矩阵、全流程代码路径索引及审稿人 3 大高频关切问题 (FAQ) 预案。 | [查看简报](file:///d:/桌面文件/sci/04_paper/EXECUTIVE_RESEARCH_BRIEF_20261007.md) |
| **research_status.json** | 机器 | **历史多肽研究状态守护文件**。哈希受保护核心文件，记录历史 SafeAMP-Dual 门禁状态，严禁人为篡改。 | [查看状态](file:///d:/桌面文件/sci/04_paper/research_status.json) |

### 2. 科学基准协议与技术规范 (`docs/amendments/` & `03_experiments/protocols/`)

| 协议文档 | 状态 | 规范范围与科学定义 | 链接 |
|---|---|---|---|
| **PROTOCOL_AMD_04_DTI_DAVIS_BENCHMARK.md** | **FROZEN (已冻结)** | **DTI 激酶亲和力前瞻性基准协议主文**。规定 25,772 条实测矩阵范围、Tanimoto < 0.40 与 NW < 0.40 双图块互斥聚类划分准则、四大评估域数学定义。 | [查看协议](file:///d:/桌面文件/sci/docs/amendments/PROTOCOL_AMD_04_DTI_DAVIS_BENCHMARK.md) |
| **protocol-dti-01.json** | **FROZEN (已冻结)** | 机器可读协议文件。包含不可变来源路径、哈希签名和四大评估域元数据配置。 | [查看协议](file:///d:/桌面文件/sci/03_experiments/protocols/protocol-dti-01.json) |
| **PROTOCOL_AMENDMENT_01_CDHIT.md** | 历史归档 | 历史多肽 CD-HIT 聚类与同源性分割规范。 | [查看历史协议](file:///d:/桌面文件/sci/docs/amendments/PROTOCOL_AMENDMENT_01_CDHIT.md) |
| **PROTOCOL_AMENDMENT_02_ALL_MEMBER.md** | 历史归档 | 历史多肽全员隔离与研究来源正交性规范。 | [查看历史协议](file:///d:/桌面文件/sci/docs/amendments/PROTOCOL_AMENDMENT_02_ALL_MEMBER.md) |

### 3. 实验审计与密码学复核报告 (`03_experiments/audits/`)

| 审计目录 / 报告 | 结论 | 审计内容与验证项 | 链接 |
|---|---|---|---|
| **dti_davis_stacked_verification_20261007_v2/report.md** | **AUDIT PASSED** | Stacking 集成模型独立密码学审计报告。复算 25,772 对预测值，核验 0 NaN，确认全域指标。 | [查看审计报告](file:///d:/桌面文件/sci/03_experiments/audits/dti_davis_stacked_verification_20261007_v2/report.md) |
| **dti_davis_baseline_verification_20261006_v1/report.md** | **AUDIT PASSED** | 四大经典基线模型独立复算与隔离无泄漏证明。 | [查看基线审计](file:///d:/桌面文件/sci/03_experiments/audits/dti_davis_baseline_verification_20261006_v1/report.md) |
| **dti_davis_isolation_review_20261006_v1/report.md** | **FEASIBLE (通过)** | DAVIS 激酶基准图拓扑聚类与双盲冷启动隔离可行性裁决报告。 | [查看隔离报告](file:///d:/桌面文件/sci/03_experiments/audits/dti_davis_isolation_review_20261006_v1/report.md) |
| **dti_davis_acquisition_20261006_v2/report.md** | **VERIFIED (通过)** | Harvard Dataverse 官方原始数据下载与 MD5/SHA256 官方校验报告。 | [查看数据获取报告](file:///d:/桌面文件/sci/03_experiments/audits/dti_davis_acquisition_20261006_v2/report.md) |

### 4. 实施方案与技术设计文档 (`docs/superpowers/plans/`)

| 设计规划文档 | 实施阶段 | 核心任务与架构规划 | 链接 |
|---|---|---|---|
| **2026-10-06-dti-kd-feasibility.md** | 阶段三 (DTI) | DTI 实测 Kd 数据可行性清点、同源隔离论证与 Task 1–4 全阶段实施计划。 | [查看实施计划](file:///d:/桌面文件/sci/docs/superpowers/plans/2026-10-06-dti-kd-feasibility.md) |
| **2026-10-05-dual-task-model-readiness.md** | 阶段二 (模型准备) | 算法就绪与双任务模型接口契约规范。 | [查看计划](file:///d:/桌面文件/sci/docs/superpowers/plans/2026-10-05-dual-task-model-readiness.md) |
| **2026-09-30-gemini-phase-d-implementation.md** | 阶段一 (平台基础) | Phase D 全栈工程、数据网关与防泄漏保护系统架构。 | [查看计划](file:///d:/桌面文件/sci/docs/superpowers/plans/2026-09-30-gemini-phase-d-implementation.md) |

---

## 三、常用命令与可复现性操作指南 (Runbook)

### 1. 验证 5 大受保护文件密码学哈希（防篡改核验）
```powershell
$files = @(
    "04_paper/research_status.json",
    "docs/amendments/PROTOCOL_AMD_04_DTI_DAVIS_BENCHMARK.md",
    "03_experiments/audits/dti_davis_acquisition_20261006_v2/davis.csv",
    "03_experiments/audits/dti_davis_isolation_review_20261006_v1/fold_memberships.json",
    "03_experiments/audits/dti_davis_isolation_review_20261006_v1/isolation_audit.json"
)
foreach ($f in $files) {
    Write-Host "$f : $((Get-FileHash -Algorithm SHA256 "d:\桌面文件\sci\$f").Hash.ToLower())"
}
```

### 2. 执行独立复算与加密审计脚本
```powershell
python "d:\桌面文件\sci\02_code\validate_dti_davis_stacked_run.py" `
  --protocol "d:\桌面文件\sci\03_experiments\protocols\protocol-dti-01.json" `
  --features-dir "d:\桌面文件\sci\03_experiments\prepared\dti_davis_enhanced_features_20261007_v1" `
  --run-dir "d:\桌面文件\sci\03_experiments\runs\dti_davis_stacked_20261007_v1" `
  --output "d:\桌面文件\sci\03_experiments\audits\dti_davis_stacked_verification_check"
```

### 3. 运行端到端改构与推理测试套件
```powershell
python "C:\Users\888\.gemini\antigravity\brain\31e23736-661c-450a-87fc-1798ec3a4b9f\scratch\test_lead_optimizer_e2e.py"
```

### 4. 前端构建与生产包验证
```powershell
cd "d:\桌面文件\sci\frontend"
npm run build
```

### 5. 启动本地全栈交互平台
* **后端 FastAPI 服务**：
  ```powershell
  python "d:\桌面文件\sci\05_web_server\app.py"
  ```
  *服务地址：http://localhost:8000 (API 文档: http://localhost:8000/docs)*
* **前端 Vite 开发服务**：
  ```powershell
  cd "d:\桌面文件\sci\frontend"
  npm run dev
  ```
  *界面地址：http://localhost:5173*
