# MIC-only 证据筛选与状态同步验证

验证时间：2026-10-02 16:01:27（Asia/Shanghai）。实际机器结果见 [validation v3](mic_training_progress_validation_20261002_v3.json)。本记录覆盖筛查报告尾部旧放行措辞更正后的五份活动文档；较早的 v2 验证文件保持原样，保留当时的文档哈希。

## 实际执行与输出

| 检查 | 实际结果 |
| --- | --- |
| 筛选审计生成 | 11 条分子、16 条测定；4 个不可拆分组件，含阳性 2、含阴性 4；`blocked` |
| 独立全局比对 | 用独立全矩阵和显式回溯重算 55 对；全部与生产比对一致，11 条同源边 |
| 逐测定标签复核 | 16 条原始 µg/mL 测定重新按 32/128 阈值及删失符号推导，均与候选标签一致 |
| 独立分组复核 | 同源边加分子/测定研究标识，独立图遍历所得成员集合与组件表一致 |
| 冻结证据校验 | 当前来源/产物哈希、5 个历史来源目录及两个新增生成脚本摘要通过 |
| 活动文档一致性 | README、整改状态、文档索引、任务看板、数据库筛查报告共 5 份，当前状态路径、生成时间、候选版本及协议 ID 一致 |
| Python 编译 | 3 个本轮新增脚本 `py_compile`，实际退出码 0 |
| 不可覆盖行为 | 对已存在审计目录和状态文件再次运行，两个生成入口均以 `FileExistsError: Refusing to overwrite` 拒绝 |
| 正式研究与训练 | 正式状态文件原哈希不变；无训练命令、训练释放 0、未启动训练 |

## 复跑命令

```powershell
# 每次改为全新的输出目录或文件名。
python 02_code/audit_mic_confirmed_acid_subset.py --output 03_experiments/audits/mic_confirmed_acid_subset_my_run
python 02_code/mic_training_readiness_v8.py --output 03_experiments/audits/mic_training_readiness_my_run.json
python 02_code/validate_mic_acid_progress.py --output 03_experiments/audits/mic_training_progress_validation_my_run.json
python -m py_compile 02_code/audit_mic_confirmed_acid_subset.py 02_code/mic_training_readiness_v8.py 02_code/validate_mic_acid_progress.py
```

状态生成与验证入口校验本轮冻结的 `mic_confirmed_acid_subset_20261002_v1`，不会将任意新输出自动替换成训练输入。

## 结论与限制

软件审计计算和状态同步验证通过；科学训练门禁仍为 `blocked`。当前 11 条只是末端及 MIC 字段局部确认的候选，尚未完成完整独立来源/释放审查。没有满足五折必要条件，因此未生成折表，跨折同源及论文审计为 `null`。未运行模型性能验证，也没有正式结果。

固定 0.40 阈值、五折、seed 42 和测定标签规则均保持原样。至少新增 3 个含阳性、1 个含阴性的独立组件是下一轮的必要条件；是否真正通过固定五折仍需在完整证据筛选后重算。
