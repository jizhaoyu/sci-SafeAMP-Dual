#!/usr/bin/env bash
# Resume training from existing checkpoints
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
echo "Resuming training from checkpoints/..."
bash "$ROOT_DIR/start_training.sh" "$@"
