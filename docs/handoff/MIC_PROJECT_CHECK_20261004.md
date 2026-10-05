# MIC 当前版本工程检查

## 本轮改动

新增 `02_code/check_mic_project.py`，复用现有独立验收流程，实时核对当前 v26 状态、冻结依赖、原始证据绑定、五份文档、九个模型/51 条 OOF 以及原结果的特征和指标顺序。不以保存的旧证书替代本次复核，不执行 fit。

修复 `02_code/accept_mic_delivery.py` 的 CLI 输出：诊断提示写入 stderr，stdout 只输出一个 JSON。机器输出使用标准 JSON 的 ASCII 转义，在 Windows GBK 控制台下仍能由 UTF-8 消费程序读取；保存的报告文件保持 UTF-8。

## 命令与退出码

在 `D:\桌面文件\sci` 执行：

```powershell
# 当前 MIC 交付检查；实际结果退出码 0
python 02_code/check_mic_project.py --scope current

# 当前交付加历史发布器兼容检查；当前实际结果退出码 1
python 02_code/check_mic_project.py
```

两个范围都会输出历史兼容问题和原双任务的实际状态。`current` 仅表示当前 MIC 交付门禁通过，不表示完整 pytest 套件、正式双任务或投稿通过。默认 `all` 也不运行完整 pytest，而是在当前交付之外执行冻结历史发布器的文档检查。

可用 `--output 03_experiments/audits/<新的报告文件>.json` 保存新报告，已有文件即拒绝覆盖。工作区内的报告只允许直接保存到 audits 根目录，不能写入模型、协议、数据或交付包；stdout 也可由 CI 收集。替换交付包时必须同时显式提供来自可信交接渠道的 `--manifest-sha256`。

## 实际执行记录

| 范围 | 机器结果 | 退出码 | 报告 |
|---|---|---:|---|
| current | passed；九模型/51 OOF、零 fit；95 项保护绑定、五份文档通过 | 0 | `03_experiments/audits/mic_project_check_current_20261004_v2.json` |
| all | failed；当前交付通过，旧发布器库存不兼容 | 1 | `03_experiments/audits/mic_project_check_all_20261004_v1.json` |

执行记录：`03_experiments/audits/mic_project_check_execution_20261004_v1.json`，实际用子进程调用两个 CLI，确认 stdout 可解析、与保存的报告一致，退出码符合上述范围，并确认原 ZIP 摘要未改变。

首次 current v1 报告在控制台 GBK 编码导致消费端 UTF-8 解码失败时已经生成，因此保留。修复后使用新的 v2 路径；未覆盖该中间产物。

## 仍未解决的事项

`test_evidence_gate_repair.py::test_all_current_documents_agree` 调用冻结旧发布器，要求 16 分子、23 观察；当前 v26 已准入 17 分子、42 条测定表述，故旧检查失败。该不兼容由本轮状态升级触发，不能称为原基线已有失败。旧测试和发布器受历史摘要保护，未修改、跳过或重写摘要来取得绿色结果。

原正式 MIC/HC50 双任务仍 `blocked`，正式结果和投稿就绪仍为 false。本轮推进的是工程可调用性与验收清晰度，不新增原始测量数据或模型泛化证据。

本轮选定的 11 个相关测试文件实际结果：**130 passed、1 failed**。其中当前交付与检查的五组检查为 70 项，全部通过；唯一失败仍为上述旧库存断言。两个跨编码用例实际将子进程的 `PYTHONIOENCODING` 设置为 GBK，再由 UTF-8 解码程序解析 stdout，均通过。

JUnit 记录：`03_experiments/audits/mic_project_regressions_20261004_v2.xml`。没有跳过旧断言，也未声称完整项目 pytest 套件通过。
