# 4核4G 云服务器极简部署与常驻运行指南 (Cloud Deployment Guide)

本指南针对你的 **4核 4G 内存云服务器**（Linux CentOS / Ubuntu / Debian 等均适用），将 `SafeAMP-Dual` 在线筛选平台以最低资源消耗部署并设置为 7x24 小时后台守护运行，对外提供公共 Web 界面与 RESTful API。

---

## 一、 服务器环境极简准备（仅需 2 分钟）

在你的云服务器终端（SSH 登录后）执行以下指令：

```bash
# 1. 更新系统包并安装基础 Python 环境
sudo apt-get update -y && sudo apt-get install -y python3 python3-pip git

# 2. 安装运行所需轻量核心依赖 (整体占用内存 < 300MB)
pip3 install fastapi uvicorn torch scikit-learn numpy pandas pydantic
```

---

## 二、 上传代码与权重文件

将本地 `D:\桌面文件\sci\` 下的代码与训练好的权重打包上传至云服务器：
```bash
# 在云服务器创建项目目录
mkdir -p /opt/safeamp_dual

# 将本地如下文件上传至 /opt/safeamp_dual/ 目录:
# - 02_code/feature_extractor.py
# - 02_code/model_dual_task.py
# - 02_code/weights/safeamp_dual_best.pt
# - 05_web_server/app.py
```

---

## 三、 配置 Systemd 后台系统守护服务（开机自启、崩溃自动重启）

创建系统服务配置文件：
```bash
sudo bash -c 'cat <<EOF > /etc/systemd/system/safeamp.service
[Unit]
Description=SafeAMP-Dual 2.0 AI Screening & Engineering Platform
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/safeamp-server
ExecStart=/home/ubuntu/safeamp-server/run_server.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF'
```

启动并设置开机自启：
```bash
# 重载系统服务
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start safeamp

# 开启开机自启
sudo systemctl enable safeamp

# 查看运行状态 (显示 active (running) 即代表成功)
sudo systemctl status safeamp
```

---

## 四、 开放防火墙与安全组端口

在你的腾讯云轻量控制台：
* 进入【安全组 (Security Group)】或【防火墙 (Firewall)】设置。
* 添加一条入方向规则：**放行 TCP 8090 端口**，授权对象设置为 `0.0.0.0/0`。

---

## 五、 验收与论文写作引用

1. **浏览器直接访问**：
   在任何电脑或手机浏览器输入：`http://62.234.141.184:8090/`，即可体验最新 2.0 版本的彩色残基热力图、双任务预测与一键 AI 智能突变降毒改造功能！
2. **在论文中写入网址（顶刊极大加分项）**：
   在论文的 `Abstract` 与 `Data and Code Availability` 章节中写道：
   > *"To assist experimental biologists in de-risking peptide leads, an online web server and AI mutation design suite has been deployed at http://62.234.141.184:8090, with open RESTful APIs."*
3. **API 供程序自动化调用**：
   同行也可以直接向 `http://<你的公网IP>/api/predict` 发送 POST 请求批量获取预测结果。
