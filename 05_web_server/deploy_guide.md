# DTI 部署与启动指南

1. 在 Python 环境中安装根目录依赖：`pip install -r requirements.txt`
2. 进入前端目录并完成打包构建：
   ```powershell
   cd frontend
   npm ci
   npm run build
   cd ..
   ```
3. 在项目根目录下启动 FastAPI 服务：
   ```powershell
   python 05_web_server/app.py
   ```
4. 打开浏览器访问 `http://127.0.0.1:8000` 即可使用药物靶点预测平台。
