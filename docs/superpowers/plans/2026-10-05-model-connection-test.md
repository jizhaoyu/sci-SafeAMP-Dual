# 配置中心真实连接测试 Implementation Plan

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用网页当前草稿配置完成一次中性 API 测试，显示真实模型、完整响应耗时和明确错误。

**Architecture:** 新增独立连接测试模块和 `/api/llm/test_connection`；前端复用 API 客户端，不读取活动序列。关闭弹窗或修改配置时取消等待并清除旧结果；服务端只转发固定文本，不存凭证。

**Tech Stack:** Python 标准库、FastAPI、现有 React、Zustand、Axios；不新增依赖。

## Global Constraints

- 仅支持 DeepSeek/OpenAI 官方 HTTPS 主机；不跟随重定向，不允许任意代理或内网地址。
- 固定 temperature=0、stream=false、max_tokens=32；不自动重试。
- 每客户端每分钟最多 6 次测试，服务端最多 2 个并发请求。
- 不发送序列、论文或研究结果；不改研究状态、冻结文件及模型产物。
- 密钥不写入 localStorage、错误文本或审计产物；清除旧缓存中的凭证。
- 连接成功仅表示中性响应验证通过，不表示科研模型就绪或投稿批准。

### Task 1: 独立后端入口

Files: `05_web_server/llm_connection.py`、`05_web_server/research_api.py`、`05_web_server/rate_limiter.py`。

- [x] 定义 `check_connection(data: dict) -> dict`，严格校验 provider、api_key、base_url、model_name。固定输出标记 `API_CONNECTION_OK`。
- [x] 返回 requested_model、returned_model、duration_seconds_full_response、usage；上游鉴权/余额/限流/超时/响应不合格分别返回固定错误，不回传上游错误正文。
- [x] 路由限制请求大小，在线程池调用中性测试，与 `engine()` 和 `/api/ready` 分离。

### Task 2: 配置中心交互

Files: `frontend/src/components/SettingsModal.tsx`、新建 `frontend/src/components/ModelConnectionTest.tsx`、`frontend/src/store/useAppStore.ts`。

- [x] 使用当前草稿字段测试；显示支持范围、测试耗时、模型和 token 用量；使用 AbortController 消除旧响应。
- [x] 每次打开重新初始化草稿；取消不保存，恢复默认只修改草稿。
- [x] 将 store 持久版本升为 5，partialize 不含 apiKey，迁移和合并都清除缓存凭证；修正科研流程和凭证文案。

### Task 3: 验收

- [x] 运行聚焦后端回归、`npm run build`、`npm run lint`，记录实际失败及范围。
- [x] 在浏览器验证缺少密钥、非官方地址、错误凭证、取消/重开、修改配置清除结果。真实 DeepSeek 中性调用由明确配置提供凭证，不保存浏览器请求轨迹。
- [x] 保存脱敏验收报告；复核受保护科研状态和交付文件摘要，保留所有历史产物。

验收记录：`03_experiments/audits/model_connection_ui_20261005_v1/README.md`。36 项后端回归、构建、lint、隔离存储迁移检查通过；浏览器真实 DeepSeek 返回 `deepseek-flash`，用量 21 tokens。

本轮在当前会话直接实施；远程推送与云端部署需另有用户指令。
