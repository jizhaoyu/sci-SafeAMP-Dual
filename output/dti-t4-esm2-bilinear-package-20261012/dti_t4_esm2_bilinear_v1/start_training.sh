#!/usr/bin/env bash
# One-click background launch script for BilinearInteractionDTI on Cloud T4 GPU
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PID_FILE="$ROOT_DIR/train.pid"
LOG_FILE="$ROOT_DIR/t4_training.log"

# Check if training process is already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[ERROR] Training job is already running with PID $OLD_PID!"
        echo "Use 'bash watch_progress.sh' to view progress, or 'bash stop_training.sh' to stop."
        exit 1
    fi
    rm -f "$PID_FILE"
fi

echo "======================================================================"
echo "[1/2] Pre-flight Verification..."
echo "======================================================================"
python3 check_bundle.py

echo "======================================================================"
echo "[2/2] Launching Background Training on T4..."
echo "======================================================================"

# Detach from interactive terminal with nohup and unbuffered Python
nohup python3 -u train_t4.py --epochs 25 --batch_size 256 --lr 0.001 "$@" >> "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

echo "Background job launched successfully!"
echo "PID: $NEW_PID"
echo "Log file: $LOG_FILE"
echo "======================================================================"
echo "SAFE TO DISCONNECT: You can now safely close this web terminal or SSH."
echo "The training will continue in the background."
echo ""
echo "Useful commands:"
echo "  - Track progress:  bash watch_progress.sh"
echo "  - Stop training:   bash stop_training.sh"
echo "  - Resume training: bash continue_training.sh"
echo "======================================================================"
