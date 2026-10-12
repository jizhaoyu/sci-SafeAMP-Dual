#!/usr/bin/env bash
# Safely terminate training
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT_DIR/train.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No running training process PID file found."
    exit 0
fi

TRAIN_PID=$(cat "$PID_FILE")
if [ -n "$TRAIN_PID" ] && kill -0 "$TRAIN_PID" 2>/dev/null; then
    echo "Stopping training process (PID: $TRAIN_PID)..."
    kill -15 "$TRAIN_PID" || true
    sleep 2
    if kill -0 "$TRAIN_PID" 2>/dev/null; then
        echo "Process did not terminate immediately, sending SIGKILL..."
        kill -9 "$TRAIN_PID" || true
    fi
    echo "Training process stopped."
else
    echo "Process $TRAIN_PID is not running."
fi

rm -f "$PID_FILE"
echo "Completed folds are preserved in checkpoints/. Run 'bash continue_training.sh' to resume."
