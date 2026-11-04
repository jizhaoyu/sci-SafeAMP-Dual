# MIC 训练工程交付计划

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 protocol-mic-13 的已准入探索性训练交付为可复跑、可离线复核的模型与证据包。

**Architecture:** 复用冻结训练入口，交付构建前重新执行独立复核；导出九个折模型、固定特征、分区、证据、结果、协议和文件摘要。独立运行时验证交付摘要后只重放准入样本的留出折预测；验收命令验证本地复跑及移动目录后的离线复核。

**Tech Stack:** Python 3.11、现有 numpy/pandas/scikit-learn/joblib/pytest，标准库；不新增依赖。

## 全局约束

- 既有脏文件、冻结入口、协议、状态 v26 及其全部受保护依赖保持原样。
- 科学条件不变：真实原始证据、全员 identity >=0.40 与原测量研究联合分组、固定三折 seed=42、每个分区两类。
- 17 个分子、42 条测定表述、44 维固定特征；LR/RF/Dummy 全部报告，不选优，不新增全量拟合模型。
- 原双任务仍 blocked；不提供 HC50、临床安全或投稿准入结论。
- 交付运行时只提供已准入样本的 OOF 重放，不加入任意新肽设计或优化功能。现有双任务服务不接入 MIC 折模型。
- 输出目录存在即拒绝覆盖；交付与复核均记录真实时间。来自可信渠道的 manifest SHA256 是模型反序列化前的摘要锚点。
- 离线交付验证不依赖原工作区；完整训练重跑依赖保留的研究工作区及冻结环境，说明两者要求。

## Task 1：训练与交付构建

**Files:** 新建 `02_code/mic_delivery.py`、`02_code/tests/test_mic_delivery.py`。

**Interfaces:** `build_delivery(run, protocol, freeze, output)`；CLI `build` 和 `retrain`。交付 `manifest.json` 使用 schema_version=1、files 相对路径摘要、artifacts 路径索引、environment、protocol_id、sample_ids、model_names 和 scope 字段。

- [x] 构建前调用冻结入口的独立 validate，不接受未复核结果。
- [x] 完整导出 run/、cohort/、evidence/、protocol.json、freeze.json、validation.json、runtime.py、requirements-lock.txt、MODEL_CARD.md、README.md；保留证据来源的许可与引用。
- [x] 摘要先绑定所有文件，再生成 manifest；返回 manifest 摘要供验收和交接。
- [x] `retrain` 显式接收原协议、冻结与新的 run/output 路径，复用原训练门禁，再复核和打包。
- [x] 验证缺失冻结、摘要变化、不完整运行、覆盖不足与已有输出均拒绝。

## Task 2：离线加载与 OOF 重放

**Files:** 新建 `02_code/mic_delivery_runtime.py`、`02_code/tests/test_mic_delivery_runtime.py`。

**Interfaces:** `DeliveryRuntime(bundle, manifest_sha256)`；`verify()`；`replay(sample_id=None, model=None)`；CLI `verify`/`replay --bundle --manifest-sha256`。只使用标准库和既有 numpy/pandas/scikit-learn/joblib。

- [x] 在 joblib.load 之前验证独立摘要锚点、全部文件、相对路径、环境、九模型完整性、特征和样本顺序。
- [x] 验证协议模型参数、标签/折覆盖、LR 缩放器训练范围、RF/Dummy 参数和预测概率。
- [x] 重算 51 条 OOF、九折与三模型汇总指标；禁止任何 fit。
- [x] 未知样本、未知模型、路径逃逸、修改模型/特征/参数/预测均失败。
- [x] 在工作区之外移动复制包，用包内 runtime.py 完成离线复核。

## Task 3：验收与说明

**Files:** 新建 `02_code/accept_mic_delivery.py`、`02_code/tests/test_mic_delivery_acceptance.py`、`docs/handoff/MIC_TRAINING_DELIVERY_20261004.md`。

**Interfaces:** 验收 CLI 显式接收 bundle、manifest-sha256、output；输出 exclusive JSON 证据，不以工程成功修改科学状态。

- [x] 检查工作区原始科学状态 v26 与交付包的 protocol/data 绑定。
- [x] 复核五份科学文档仍一致；记录历史固定库存测试不适用于扩充队列的具体原因。
- [x] 验证当前 frozen dependency/受保护 history 摘要保持不变；未验证的旧引用单列缺口。
- [x] 独立验收完整交付包、错误路径和篡改拒绝；保存复跑结果比较。
- [x] 说明一条构建/复跑命令、一条离线验证命令、一条 OOF 重放命令，以及环境、来源许可和研究限制。

## Task 4：集成与两阶段评审

- [x] 各实施任务完成后由主代理做规格评审与代码质量检查；目录写入保护修复后重新验收。交叉智能体评审因额度限制未完成，未声称第二名独立审阅通过。
- [x] 根代理运行新测试和现有相关回归，记录完整通过/失败/不适用项，不修改历史冻结测试掩盖失败。
- [x] 执行一次固定方案工程重跑，确认三模型全部 OOF 与已复核运行一致；该重跑不构成新的科学实验。
- [x] 生成不可覆盖的交付目录和摘要锚点；离线迁移验收；保存验收 JSON 与交付报告。
- [x] 更新本计划复选框；交付具体目录和使用命令。

## 执行结果

- 交付：`03_experiments/deliveries/mic_baseline_20261004_v1.zip`；manifest SHA256 `f8b8606dc807279cc78c6728260f6d3d7da463f2416bf47e8d3bafbdf1789ed3`。
- 工程重跑 14 结果文件逐字节一致；九模型、51 OOF、零 fit 独立复核；最终验收检查 95 受保护文件和五份文档。
- 新交付测试 58 passed；历史相关检查 60 passed、1 failed（旧发布器固定 16/23 库存，与当前 17/42 不兼容）。
- 包记录 1 个旧生产代码快照缺口、10 个历史证书未验证引用；原始测定和当前冻结绑定均严格核验，未把缺口当作已通过。
- 详细命令和实际验收证书见 `docs/handoff/MIC_TRAINING_DELIVERY_20261004.md`。
