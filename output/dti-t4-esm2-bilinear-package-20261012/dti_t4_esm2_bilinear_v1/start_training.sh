#!/usr/bin/env bash
# One-click launch script for BilinearInteractionDTI on Cloud T4 GPU
set -euo pipefail

echo "=== [1/3] Environment & GPU Preflight Check ==="
python3 -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
nvidia-smi || true

echo "=== [2/3] Installing Dependencies ==="
pip install -r requirements.txt || true

echo "=== [3/3] Launching 4-Fold Training on T4 ==="
python3 train_t4.py --epochs 25 --batch_size 256 --lr 0.001 2>&1 | tee t4_training.log

echo "Training complete! Results saved to t4_results.json"
