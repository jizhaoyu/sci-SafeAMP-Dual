# MIC 探索研究报告交付

本目录为 `protocol-mic-13`、MIC v26 的本地报告初稿，关联数据版本 `mic_goat_followup_release_20261004_v1`。不改变原双任务 `blocked`、`publication_ready=false`，不重启已关闭的外部证据搜索。

## 阅读顺序

1. [报告正文](D:/桌面文件/sci/04_paper/reports/mic_baseline_report_20261005_v1/report.md)：摘要、问题、证据、固定方法、全部模型/逐折结果、局限、交付入口与待确认声明。
2. [本地演示步骤](D:/桌面文件/sci/04_paper/reports/mic_baseline_report_20261005_v1/demo.md)：包验证、已准入 ID 重放、原文证据追溯。
3. [来源摘要索引](D:/桌面文件/sci/04_paper/reports/mic_baseline_report_20261005_v1/source_manifest.json)、[声明对应表](D:/桌面文件/sci/04_paper/reports/mic_baseline_report_20261005_v1/claims.csv)、[完整数值快照](D:/桌面文件/sci/04_paper/reports/mic_baseline_report_20261005_v1/facts.json)。
4. [报告输入与输出摘要](D:/桌面文件/sci/04_paper/reports/mic_baseline_report_20261005_v1/report_manifest.json)、[初次核查](D:/桌面文件/sci/04_paper/reports/mic_baseline_report_20261005_v1/validation_v1.json)。

## 本地一致性复核

在项目根目录运行，输出名称必须不存在：

```powershell
Set-Location 'D:\桌面文件\sci'
python -I -B '04_paper/reports/mic_baseline_report_20261005_v1/check_report.py' verify --output '04_paper/reports/mic_baseline_report_20261005_v1/validation_v2.json'
```

再次复核应指定新的输出名称，例如 `validation_v3.json`。`build` 用于第一次生成当前目录的固定产物，已构建目录会拒绝再次生成。

核查范围：394 份冻结包文件和原 ZIP 摘要、10 项原始来源文件绑定、正式/MIC 状态摘要、16 项本地证据索引、33 个声明锚点、三个模型的合并指标、九个折模型的完整指标、各折类别数量及本地链接。全过程不导入训练模块、不加载或拟合模型；已有模型运行验收的时间保留在报告内，没有重新标记为本阶段执行。未运行 pytest。

## 交付与人工审核边界

可复核的报告初稿和演示材料已经形成，原训练包继续使用 [现有 ZIP](D:/桌面文件/sci/03_experiments/deliveries/mic_baseline_20261004_v1.zip) 与 [交接指南](D:/桌面文件/sci/docs/handoff/PROJECT_CLOSEOUT_20261005.md)。报告附件单独存放，避免修改已冻结、含许可限制的训练包。

`passed_local_consistency` 仅表示本文数值、链接及摘要的一致性，不表示独立人工证据审查、稿件获批或原研究目标完成。原文定位复核、作者与贡献、经费/利益冲突、伦理及许可适用性仍待责任人确认。写作工具方法来源已按 scientific-writing 技能要求列于报告第 8 节，其公开书目信息在本阶段核对。
