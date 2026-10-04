# Gemini Phase D 开发启动提示

配套计划：[SafeAMP-Dual Phase D — Gemini 开发实施计划](../superpowers/plans/2026-09-30-gemini-phase-d-implementation.md)。

把下面代码块中的内容直接发给能访问该工作区的 Gemini。用户仅阅读此文档不会启动训练；由 Gemini 接收执行任务后按门禁推进。

```text
你现在负责 SafeAMP-Dual 的下一阶段本地开发实施。
工作目录：D:/桌面文件/sci

首先完整阅读：
1. 工作区及相关目录的 AGENTS.md（若没有文件，遵循本会话工作约定）。
2. docs/superpowers/plans/2026-09-30-gemini-phase-d-implementation.md
3. docs/research_protocol.md
4. docs/amendments/PROTOCOL_AMENDMENT_01_CDHIT.md

按实施计划 Task 0→7 执行，交付代码、必要测试、实际输出与交接日志。
不要只复述计划或停留在建议；对明确的本地修复直接执行。
定位代码先使用现有 CodeGraph，再按具体符号读取源码。
当前目录此前非 Git 仓库；先检测，不擅自 git init，不覆盖他人改动。

已核实的重点问题：
- README把records.csv当作--dataset；实际入口要求validated准备目录。
- feasibility未实际验证五折/留出，prepare仍走旧传递闭包规则。
- 代表聚类、min/max分母、长度比和跨集合定义尚不一致。
- 13条外部记录来自手写二元标签，当前缺逐条原始assay依据。
- run完成、研究结果可用、投稿授权没有完整一致的状态闭环。
这些事实优先于旧状态文档中的全完成或ready宣称。

禁止通过关闭校验、放宽阈值、随机拆分、搜索seed、补负类、伪造assay、
或直接把publication_ready/all_claims_verified改true来取得通过。
保持7模型、3种子、五折、固定端点和真实fair-esm；不新增依赖。
不读取或输出.env、密钥；不部署、不推送、不调用付费服务、不投稿。

先完成证据校验、协议衔接、共享准备引擎、运行产物校验和研究草稿导出。
真实数据与协议均合格、prepared实际validated后再运行正式实验。
若资料不足或科学定义冲突，记录具体blockers，继续不依赖该决定的软件任务。
涉及必须由研究负责人决定的口径，集中给出确切待决定字段与影响，不能代签。
代码测试通过不代表真实科研门禁已通过，不把软件fixture当正式结果。

每个任务执行必要验证，记录命令、退出码、真实测试数量、证据路径。
保留既有数据及历史run，新产物采用新版本目录；源码改动用小范围补丁。
最后更新CodeGraph和当前状态文档，提交：
docs/handoff/PHASE_D_IMPLEMENTATION_LOG.md

最终答复分清：软件已修复项、实际执行实验、仍被阻断项、投稿审批状态。
列出修改文件、验证输出、数据/协议/run哈希和下一步缺少的具体证据。
```

完成边界以主计划第7节为准。现有144项通过是2026-09-29的历史基线，不能代替本轮修改后的实际测试结果。
