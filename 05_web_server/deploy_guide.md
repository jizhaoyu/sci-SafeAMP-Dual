# 本地研究服务运行指南

本轮不执行远程部署。原部署说明保存在 legacy/，不代表修订版已上线。

1. 在独立 Python 环境安装根目录 requirements.txt。
2. 在 frontend 运行 npm ci 和 npm run build。
3. 从项目根目录运行 python -m uvicorn app:app --app-dir 05_web_server --host 127.0.0.1 --port 8000。
4. 打开 http://127.0.0.1:8000。开发模式可运行 frontend 的 npm run dev，API 代理到本机 8000。

SAFEAMP_RUN_DIR 必须指向 completed 运行目录，其数据清单 validated、真实 ESM 哈希与三种子模型完整匹配。旧 safeamp_dual_best.pt 文件不会被接受。当前数据门禁失败，正确状态应为 unavailable，正式预测 HTTP 503。

/api/system_status 返回实际加载状态；无效序列返回 422；/api/helical_wheel 提供独立理化投影。不存在临床安全评级、真实结构推断或经验证降毒承诺。报告是本地生成，不接入外部 LLM。

开始任何公共部署前，须另行确认公开数据许可、已完成的模型证据、API 资源限制和真实服务地址；本说明不构成部署或发表完成声明。
