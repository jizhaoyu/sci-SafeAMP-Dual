自动续跑工具：仅在训练进程 SIGTERM（-15 或 143）退出后等待15秒再恢复，最多10次。
不会阻止平台终止；平台停止整个工作空间时，本工具也无法继续。
代码报错或 SIGKILL 不自动重试，正常完成后停止。Ctrl+C 会停止监督和子训练进程。
启动前必须停止旧 watch_training.sh/start_training.sh 和手动训练进程。
运行：cd /workspace/sci；.venv-cloud/bin/python -u supervise_training.py 2>&1 | tee -a cloud-training.log
固定线程环境8以匹配现有逐折断点；模型参数不改变。
纯模拟检查6项通过，未启动本地训练；Linux云端整体运行待验证。
