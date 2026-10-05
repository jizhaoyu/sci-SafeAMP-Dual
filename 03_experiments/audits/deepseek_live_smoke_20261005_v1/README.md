# DeepSeek 真实 API 测试验收

实际执行：2026-10-05T06:47:58.703514+00:00 至 06:48:00.238529+00:00，即北京时间 2026-10-05 14:47:58–14:48:00。状态 `passed`。

## 两次实际调用

| 测试 | HTTP | 配置请求模型 | 响应模型 | 完整耗时（秒） | 输入 tokens | 输出 tokens | 总 tokens | 完成原因 |
|---|---:|---|---|---:|---:|---:|---:|---|
| 普通连通性固定文本 | 200 | deepseek-chat | deepseek-flash | 0.8402 | 33 | 8 | 41 | stop |
| 虚构工程报告 JSON 格式 | 200 | deepseek-chat | deepseek-flash | 0.6928 | 177 | 91 | 268 | stop |

合计 2 次真实请求、309 tokens。耗时从发起请求到完整读完并解析响应，不沿用旧脚本只计响应头的口径。没有自动重试。响应 ID、usage、请求 payload、输出原文和 SHA256 均保存；认证头和密钥没有进入产物。

请求地址为 `https://api.deepseek.com/v1/chat/completions`，凭据来自本次明确选择的项目 `.env`。这里没有读取用户浏览器配置中心的 localStorage，也没有声称网页所保存的另一个配置已经测试。请求/响应格式按 [DeepSeek Chat Completions API 文档](https://api-docs.deepseek.com/api/create-chat-completion/) 实现。返回模型名称按实际 API 响应记录，不据历史脚本标题将其声明为 V3，也不推测其参数规模或训练版本。

## 通过的范围

- 官方主机的认证及当前配置可完成真实 Chat Completions 请求。
- 固定连通性标记精确一致，响应结构与 token 用量有效。
- JSON 报告严格保留虚构的 12 条工程记录、artifact_verified=true、正式状态 blocked、外部记录 0、publication_ready=false。
- 模型按要求保留固定的虚构数据声明及研究限制，没有加入未知字段。
- 32 项离线回归通过：端点白名单、缺配置、环境覆盖、报告状态/计数、响应截断、usage、重定向、脱敏及拒绝覆盖。

报告 fixture 为封闭的格式测试，指定了摘要及限制文本。它不能证明模型科学推理、自由撰写、事实核验或真实研究报告质量，也不能代替人工审评。

## 网页功能与科研门禁

当前 `05_web_server/research_api.py` 的 `/api/ai_report` 返回本地证据报告，不向外部发送序列；本轮没有改动这条链路、没有验证网页调用 DeepSeek。独立入口通过与网页集成是分别记录的状态。

本轮未上传真实研究数据、序列、原论文或报告；没有 fit。正式研究状态文件、MIC ZIP 与 manifest 摘要不变。原报告附件的无 fit 一致性核查亦通过，见 [validation_v3.json](D:/桌面文件/sci/04_paper/reports/mic_baseline_report_20261005_v1/validation_v3.json)。原双任务仍为 blocked；原训练成果继续按 protocol-mic-13 小样本探索边界交付。

## 密钥处理

旧 `02_code/deepseek_real_evaluation.py` 的硬编码密钥已移除，改为新测试入口的兼容启动器。新代码只从选定环境文件或进程环境读取凭据，不输出其前后缀。

项目 `.env` 仍配置旧脚本使用过的同一把密钥，轮换未执行。需要账户所有者在 DeepSeek 控制台创建新密钥、替换本地配置并撤销旧密钥；删除代码中的明文不能撤销已经泄露的凭据。本轮没有修改账户、环境文件或声称完成轮换。

## 证据入口

- [实际调用摘要](D:/桌面文件/sci/03_experiments/audits/deepseek_live_smoke_20261005_v1/summary.json)
- [连通性请求](D:/桌面文件/sci/03_experiments/audits/deepseek_live_smoke_20261005_v1/connectivity/request.json)、[脱敏响应](D:/桌面文件/sci/03_experiments/audits/deepseek_live_smoke_20261005_v1/connectivity/response.json)、[逐项验收](D:/桌面文件/sci/03_experiments/audits/deepseek_live_smoke_20261005_v1/connectivity/audit.json)
- [虚构报告请求](D:/桌面文件/sci/03_experiments/audits/deepseek_live_smoke_20261005_v1/synthetic_report/request.json)、[脱敏响应](D:/桌面文件/sci/03_experiments/audits/deepseek_live_smoke_20261005_v1/synthetic_report/response.json)、[逐项验收](D:/桌面文件/sci/03_experiments/audits/deepseek_live_smoke_20261005_v1/synthetic_report/audit.json)
- [真实调用产物摘要](D:/桌面文件/sci/03_experiments/audits/deepseek_live_smoke_20261005_v1/manifest.json)
- [离线回归记录](D:/桌面文件/sci/03_experiments/audits/deepseek_live_smoke_20261005_v1/offline_regressions.xml)

## 复跑命令

以下 v2 输出目录必须不存在；每次将产生最多两次计费 API 请求，凭据只通过环境文件/进程环境读取。

```powershell
Set-Location 'D:\桌面文件\sci'
python -B 02_code/deepseek_live_smoke.py --env-file .env --output 03_experiments/audits/deepseek_live_smoke_20261005_v2
```

离线回归不调用 API：

```powershell
python -B -m pytest -q 02_code/tests/test_deepseek_live_smoke.py -p no:cacheprovider
```

历史 `output/verification/deepseek_full_audit.json`、基准摘要与历史说明保留；本轮不依据这些旧资料宣称当前网页端到端可用。
