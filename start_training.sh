#!/usr/bin/env bash
# 后台启动 DTA v5 训练,用 setsid 放入独立会话以规避会话超时导致的 SIGTERM
set -e
cd /workspace/sci

# 防重复启动
if pgrep -f "run_experiments_v5.py" >/dev/null 2>&1; then
  echo "训练已在运行,跳过。当前进程:"
  pgrep -af "run_experiments_v5.py"
  exit 0
fi

if [ -d .venv-cloud ]; then VENV=.venv-cloud; elif [ -d .venv ]; then VENV=.venv; else echo "未找到 venv (.venv-cloud/.venv)"; exit 1; fi
source "$VENV/bin/activate"

if [ ! -f output/dta-paper-run-v5-20261009/scripts/run_experiments_v5.py ]; then echo "未找到训练脚本"; exit 1; fi

echo "使用 venv: $VENV"
# 独立会话后台运行,输出追加到日志;exec 减少一层 shell
setsid bash -c 'set -o pipefail; exec python -u output/dta-paper-run-v5-20261009/scripts/run_experiments_v5.py' > cloud-training.log 2>&1 < /dev/null &
disown

echo "训练已在后台启动,日志: /workspace/sci/cloud-training.log"
sleep 4
echo "=== 进程 ==="
pgrep -af "run_experiments_v5.py" || echo "未检测到进程(可能瞬间退出,请查看日志)"
echo "=== 日志尾部 ==="
tail -n 15 cloud-training.log
