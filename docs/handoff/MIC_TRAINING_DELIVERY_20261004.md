# MIC 训练工程交付

## 范围与科学状态

这次交付复用 `protocol-mic-13`，队列版本为 `mic_goat_followup_release_20261004_v1`。科学状态继续以 `03_experiments/audits/mic_training_readiness_20261004_v26.json` 为准，生成时间 `2026-10-04T07:17:45.230443+00:00`。

MIC 探索训练已完成并独立复核，`training_blocked=false`。原 MIC/HC50 双任务仍 `blocked`，正式结果与投稿就绪仍为 `false`。工程交付不改变这些结论。

交付对象为九个固定折模型和准入队列的 OOF 结果复现接口。17 个分子、42 条测定表述、44 维特征、固定三折、6 阳性和 11 阴性；42 条表述不等于 42 个独立样本。全部三种模型一同交付，不进行选优、调参或全数据追加拟合。原双任务网页服务需要的 ESM/HC50 模型与本包不同。

## 训练与复现证据

- 工程复跑：`03_experiments/runs/mic_delivery_reproduction_20261004_v1`。
- 冻结入口复核：`03_experiments/audits/mic_delivery_reproduction_validation_20261004_v1.json`，九模型重载、51 条 OOF、零 fit，缩放器训练范围通过。
- 比较与保护检查：`03_experiments/audits/mic_delivery_reproduction_comparison_20261004_v1.json`，14 个结果文件与原已验证运行逐字节一致；32 项当前与历史保护摘要一致。
- 原协议、数据、失败运行与冻结源代码未因本次交付修改。

本次重跑是固定方案的工程复现，不是新增科学证据。小样本的描述性性能不能说明模型已经获得外部泛化能力。各模型的完整指标在包内 `run/pooled_descriptive_metrics.csv`。

## 使用方式

完整训练复跑需要原研究工作区、冻结依赖与原始证据。使用尚不存在的运行和交付路径：

```powershell
Set-Location 'D:\桌面文件\sci'
python 02_code/mic_delivery.py retrain --protocol 03_experiments/protocols/protocol-mic-13.json --freeze 03_experiments/audits/protocol_mic_13_freeze_20261004_v1.json --run 03_experiments/runs/<新运行目录> --output 03_experiments/deliveries/<新交付目录>
```

离线复核与 OOF 重放使用交付目录内 `runtime.py`，不需要原工作区。接收方须从可信交接渠道取得 manifest 摘要，使用包内锁定环境。

```powershell
python runtime.py verify --bundle . --manifest-sha256 <交接摘要>
python runtime.py replay --bundle . --manifest-sha256 <交接摘要> --sample-id <准入sample_id>
```

加载前检查摘要、路径、环境、模型参数、样本顺序和折角色；复核时重算预测与指标，不执行 fit。重放只使用该样本唯一的留出折模型。未知样本被拒绝，不将交叉验证模型包装成未经评估的新肽预测产品。

## 测试说明

本轮运行现有六组相关回归的完整集合，结果 **60 passed、1 failed**。唯一失败为 `test_evidence_gate_repair.py::test_all_current_documents_agree`：历史发布器冻结了 16 分子/23 观察的库存断言，无法处理已准入的 17 分子/42 表述。当前发布器的五份文档一致性检查实际通过。该旧文件受历史冻结摘要保护，未通过修改旧测试或跳过检查来声称历史套件全通过。

新增交付检查最终为 **58 passed**，JUnit 记录为 `03_experiments/audits/mic_delivery_new_regressions_20261004_v2.xml`。现有相关六组检查的完整结果保存于 `mic_delivery_historical_regressions_20261004_v1.xml`，仍为 60 passed、1 failed，没有声称整个项目测试全通过。

实现由三个智能体分别承担。后续交叉评审遇到额度限制，由主代理继续做规格和代码质量检查，增加禁止验收报告写入冻结目录的保护及三项回归。未声称完成第二名独立代理或人工评审。

## 已生成的交付与验收

交付目录：`03_experiments/deliveries/mic_baseline_20261004_v1`。包内 manifest 生成时间：`2026-10-04T10:08:45.778582+00:00`。文件绑定 394 项，包括模型、结果、协议、原始证据、来源说明和运行时。

压缩包：`03_experiments/deliveries/mic_baseline_20261004_v1.zip`，58,090,263 字节。该本地研究交接包包含来源资料，公开再分发条件见包内 `LICENSE_NOTICE.md`。

| 摘要对象 | SHA256 |
|---|---|
| manifest.json | `f8b8606dc807279cc78c6728260f6d3d7da463f2416bf47e8d3bafbdf1789ed3` |
| ZIP | `858f6aa9a09dfc822b6a7c155a629ae13caf0e2c922abe3448d81119e3491b2b` |

工程验收：`03_experiments/audits/mic_delivery_acceptance_20261004_v1.json`，生成于 `2026-10-04T10:09:02.539352+00:00`，`engineering_delivery_accepted=true`。核对 95 个受保护文件、五份一致状态文档、协议及数据摘要，独立重算九模型/51 OOF，并比较原运行的特征、行顺序与指标。

迁移验收：`03_experiments/audits/mic_delivery_portable_validation_20261004_v1.json`。实际解压到系统临时目录，在项目目录外使用 `python -I` 运行包内脚本，完成全部复核和单个准入样本的三模型重放；临时目录已清理。没有依赖原工作区导入路径。

从交付目录直接执行：

```powershell
Set-Location 'D:\桌面文件\sci\03_experiments\deliveries\mic_baseline_20261004_v1'
python runtime.py verify --bundle . --manifest-sha256 f8b8606dc807279cc78c6728260f6d3d7da463f2416bf47e8d3bafbdf1789ed3
python runtime.py replay --bundle . --manifest-sha256 f8b8606dc807279cc78c6728260f6d3d7da463f2416bf47e8d3bafbdf1789ed3 --sample-id 3e656d2ae8d48ae33078fcd4
```

`verify` 输出独立复核 JSON；`replay` 对该准入样本返回三个固定模型在留出折上的结果。输出保存到包外，保持包内文件摘要稳定。若作为 Python 模块导入包内运行时，使用 `python -B` 避免在包中产生未登记字节码缓存。

工程重跑不会更新科学状态 v26。当前 MIC 探索训练已可交付；正式双任务、外部泛化和投稿状态按上文分别记录。

## 来源和许可

包保留原始来源与逐记录证据、冲突和排除理由。许可按每项来源记录；未明确取得公开再分发许可的来源不能因打包就被视为开源材料。该包用于本地研究交接，不提供整体公开再分发授权。

原始证据资料与当前被冻结输入必须与其摘要一致。历史未被当前协议绑定的源代码若已经缺少原快照，会单独记录 expected/actual 摘要；保留这种历史缺口不会生成“旧流水线完整复现”的结论。

实际来源索引保留 345 份来源文件和 10 项原文/方法引用。`evidence/source_index.json` 列明 1 项旧生产 manifest 的代码快照缺口，以及 10 项旧证书未验证引用（7 项文档绑定、3 项代码绑定，部分引用同一文件）。当前释放清单的 45 项 protected 绑定通过。旧证书保留原样，但不声称其历史引用已全部复原。
