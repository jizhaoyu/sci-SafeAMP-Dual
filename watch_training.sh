#!/usr/bin/env bash
# 训练守护:周期性检查 DTA v5 训练进程,崩溃/被杀则自动重启,直到训练正常完成才退出。
# 用法: setsid bash /workspace/sci/watch_training.sh > /workspace/sci/watchdog.log 2>&1 &
set -u
cd /workspace/sci
TRAIN_LOG=/workspace/sci/cloud-training.log
WATCHDOG_LOG=/workspace/sci/watchdog.log
CHECK_INTERVAL=30
DONE_MARK="Total pipeline completed in"

echo "$(date '+%F %T') watchdog 启动 (间隔 ${CHECK_INTERVAL}s, 完成标记: ${DONE_MARK})" >> "$WATCHDOG_LOG"

while true; do
  # 1) 训练已正常完成 -> 退出守护
  if grep -q "$DONE_MARK" "$TRAIN_LOG" 2>/dev/null; then
    echo "$(date '+%F %T') 检测到训练已完成, watchdog 退出" >> "$WATCHDOG_LOG"
    break
  fi
  # 2) 进程存活 -> 跳过
  if pgrep -f "run_experiments_v5.py" >/dev/null 2>&1; then
    echo "$(date '+%F %T') 训练进程存活, 跳过" >> "$WATCHDOG_LOG"
  else
    echo "$(date '+%F %T') 训练进程不存在, 触发重启" >> "$WATCHDOG_LOG"
    bash /workspace/sci/start_training.sh >> "$WATCHDOG_LOG" 2>&1
  fi
  sleep "$CHECK_INTERVAL"
done
echo "$(date '+%F %T') watchdog 结束" >> "$WATCHDOG_LOG"
