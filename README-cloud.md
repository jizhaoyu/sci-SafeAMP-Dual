# DTA v5 云端迁移包

包含训练必需的输入、划分、脚本，以及现有模型和断点。
完整断点：SET-D-S123, SET-D-S42, SET-D-S456, SET-D-S789（16 个实验）。
未完成设置中的模型也保留，但没有逐折续跑功能，该设置会重新训练。
仅包内 Python 脚本的 ROOT 改为根据文件位置定位 sci，原本地文件未修改。
本地 Python 3.11；依赖版本见 requirements-cloud.txt。

上传 ZIP 到 /workspace 后：

```bash
cd /workspace
unzip -n sci-training-cloud-20261009.zip
cd /workspace/sci
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-cloud.txt
python check_cloud_bundle.py
```

检查 PASS 后，准备开始云端训练时才执行：

```bash
cd /workspace/sci
source .venv/bin/activate
set -o pipefail
python -u output/dta-paper-run-v5-20261009/scripts/run_experiments_v5.py 2>&1 | tee cloud-training.log
```

训练时保留 IDE 标签页；后台工具不能保证平台不会回收工作空间。
定期下载 checkpoints/ 和 models/；结束后下载整个运行目录及日志。
剩余机时耗尽可能转为按量付费，需自行查看平台额度并及时停止。
