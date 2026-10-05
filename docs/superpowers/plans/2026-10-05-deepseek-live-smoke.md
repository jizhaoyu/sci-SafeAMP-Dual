# DeepSeek 真实调用验收 Implementation Plan

> **For agentic workers:** 按当前工作区约定实施，以下复选框记录实际执行；本轮直接本地执行。

**Goal:** 用当前 DeepSeek 配置完成真实 API 连通性与虚构报告辅助输出验收，保存脱敏记录，区分 API、输出契约和原研究状态。

**Architecture:** 独立测试入口读取现有环境配置，执行两次有界请求；输出不可覆盖的请求、响应、检查和摘要。保留当前科研 API 门禁及 MIC 冻结包。旧测试入口改为新的兼容启动器，去掉硬编码密钥及不可靠的诊断/同行评审模板。

**Tech Stack:** Python 标准库，复用已安装 python-dotenv；不新增依赖。

## Global Constraints

- 不上传序列、论文、未公开报告或实际科研测定；报告用固定虚构工程数据。
- 不训练、不修改正式状态，不把 LLM 输出当实验证据或人工独立评审。
- 密钥只在进程内使用，不写请求文件、响应、摘要或终端；不输出 key 前后缀。
- 只允许配置指向 `https://api.deepseek.com` 的无 userinfo/query/fragment URL；不随重定向发送认证。
- 两次真实请求，timeout=45 秒，temperature=0，stream=false，不自动重试；完整读完响应后计时。
- 输出目录必须不存在；异常以 HTTP 状态或异常类型记录，不能打印未脱敏异常正文。
- 用户已要求测试；执行有界实时请求及针对性本地回归，不执行全项目历史套件。

## Task 1：配置与安全入口

Files：新增 `02_code/deepseek_live_smoke.py`，修改 `02_code/deepseek_real_evaluation.py`。

- [x] 阅读调用链、配置中心与真实历史测试代码；确认现有科研 `/api/ai_report` 不调用第三方。
- [x] 只输出配置字段存在性及安全 host/model，不打印配置原文。
- [x] 实现配置加载、端点验证、完整请求计时、错误脱敏和不可覆盖输出。

调用方式：

```powershell
python -B 02_code/deepseek_live_smoke.py --env-file .env --output 03_experiments/audits/deepseek_live_smoke_20261005_v1
```

环境优先于所选 `.env`；优先 `DEEPSEEK_API_KEY/DEEPSEEK_BASE_URL/DEEPSEEK_MODEL`，兼容既有 `OPENAI_API_KEY/OPENAI_API_BASE`；默认 DeepSeek 官方 base 与 `deepseek-chat`。

## Task 2：两次真实请求及逐项判断

- [x] 连通性请求只要求返回固定字符串 `DEEPSEEK_CONNECTION_OK`，max_tokens=32。
- [x] 报告辅助请求使用 JSON output、max_tokens=512，虚构字段为 engineering_records=12、artifact_verified=true、formal_research_status=blocked、eligible_external_records=0、publication_ready=false。
- [x] 校验结构、数字与状态精确一致；限制和 summary 使用明确标注虚构和禁止研究放行的固定值；未知字段、非 stop 完成状态或缺失 usage 不记完整通过。
- [x] 保存每次无认证请求 payload、脱敏响应、HTTP/响应 ID、usage、完整耗时、检查结果和 SHA256。
- [x] 原生研究报告端点仍按既有门禁执行；独立入口通过不代表网页已接入第三方。

## Task 3：回归、保护与说明

- [x] 针对配置缺失、非法端点、重定向、报告篡改、缺少 usage、截断和响应脱敏运行离线回归（零真实网络）：32 passed。
- [x] 确认 MIC ZIP/manifest 与正式状态摘要不变，旧代码密钥已移除。密钥轮换尚未执行，账户所有者需在控制台完成。
- [x] 新版说明列出实际返回模型、调用耗时、token 与失败项；历史 9 月记录保留。

## 实际结果

2026-10-05 14:47:58–14:48:00（Asia/Shanghai）两次真实调用 HTTP 200、finish_reason=stop，完整耗时 0.8402 秒及 0.6928 秒；共 309 tokens。配置请求 deepseek-chat，实际返回 deepseek-flash。完整产物位于 `03_experiments/audits/deepseek_live_smoke_20261005_v1`，README 列出逐项记录与范围限制。

验收允许通过或真实失败；不能因 401/402/429/超时而改科学门禁、换隐藏凭据、伪造成功或替换成模拟返回。
