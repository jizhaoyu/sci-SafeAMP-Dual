# Gemini 审计修复与复跑说明

> 本页保留的是审计修复阶段快照。后续山羊肽证据释放、训练和复核已完成，当前以 `mic_training_readiness_20261004_v26.json` 和 [后续交付](MIC_GOAT_FOLLOWUP_20261004.md) 为准。

## 范围与当前状态

修复范围为第二轮来源审计的转录、标签推导、准入解释、报告声明与覆盖保护。冻结训练入口、协议、数据和模型保留原样。

当前纠正报告：[v3 报告](../../03_experiments/audits/alternative_primary_search_20261004_v3/report.md)。当前来源审计状态以该目录的 `handoff_status.json` 为准。MIC 训练机器状态仍是 v22，原双任务仍为 `blocked`。

历史 v2 的表格、状态和报告不是证据释放。`process_v2_audit.py` 已停用；旧提取器拒绝覆盖已有提取结果。旧交付报告已标记需要纠正，并撤回超出审计范围的结论。

## 已完成

- [x] 从原 XML Table 1 重读序列和分子量，修正三处转录错误。
- [x] 从 Table 3 重读 MHA、MHB 两种条件的全部 10 条 E. coli 测定，逐行保留原值、来源位置和删失边界。
- [x] 使用既有标签工具及协议阈值推导标签，不输入手写标签；换算前后不以舍入结果判定。
- [x] 重算 5,629 对本批输入比较，用独立全局比对实现逐对复算通过。
- [x] 将尚未完成原始身份及测定复核的其他记录置为待核实，清空旧转录表中的未经复核标签。
- [x] 将 MIC 同源边解释为需合并组件；未完成证据释放时不执行新队列折划分，也不预判组件合并将通过或失败。
- [x] 生成绑定输入、依赖、输出以及 45 项受保护文件的 SHA256 清单；输出目录已存在时拒绝执行。
- [x] 核验边界值 32、32.000001、128，开放上界，覆盖拒绝、旧入口拒绝和输出篡改拒绝。

## 复跑

使用项目已有 Python 3.11 环境，该环境已安装 scikit-learn；不新增依赖。

```powershell
python 02_code/repair_alternative_primary_audit.py validate --output 03_experiments/audits/alternative_primary_search_20261004_v3
```

生成另一份审计时，必须指定尚不存在的目录：

```powershell
python 02_code/repair_alternative_primary_audit.py repair --output 03_experiments/audits/alternative_primary_search_20261004_v4
```

本轮实际验证输出：`passed`，`comparison_rows=5629`，`original_measurements_checked=10`，`protected_bindings=45`，`model_fit_calls=0`。未重跑完整历史测试套件，也未重新训练模型。

## 未完成的研究工作

其他候选仍需完整原始身份、末端形式、单独测定与来源复核。新审计目录不是正式释放队列，不能直接进入训练。后续扩充须先完成证据释放，再按既定同源与研究关系合并，检查唯一固定三折及全部跨折成员；任何门禁失败保持阻断。
