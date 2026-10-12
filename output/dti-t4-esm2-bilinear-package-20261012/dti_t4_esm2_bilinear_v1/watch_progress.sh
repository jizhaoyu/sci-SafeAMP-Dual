#!/usr/bin/env bash
# Follow live training logs
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$ROOT_DIR/t4_training.log"
PID_FILE="$ROOT_DIR/train.pid"

if [ -f "$PID_FILE" ]; then
    TRAIN_PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$TRAIN_PID" ] && kill -0 "$TRAIN_PID" 2>/dev/null; then
        echo "Training is ACTIVE (PID: $TRAIN_PID)."
    else
        echo "Training process is NOT running (either completed or stopped)."
    fi
else
    echo "No train.pid file found."
fi

if [ ! -f "$LOG_FILE" ]; then
    echo "Log file $LOG_FILE does not exist yet. Please start training first."
    exit 1
fi

echo "Displaying latest logs (Press Ctrl+C to exit viewing; training continues in background):"
echo "----------------------------------------------------------------------"
tail -n 35 -f "$LOG_FILE"
