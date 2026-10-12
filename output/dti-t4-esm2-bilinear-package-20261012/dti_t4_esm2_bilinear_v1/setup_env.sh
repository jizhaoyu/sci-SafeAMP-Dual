#!/usr/bin/env bash
# Environment setup for Cloud T4 GPU instance
set -euo pipefail

echo "======================================================================"
echo "[1/3] Checking Python & System Environment"
echo "======================================================================"
python3 --version
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi
else
    echo "Notice: nvidia-smi not found. If running on GPU instance, ensure CUDA drivers are installed."
fi

echo "======================================================================"
echo "[2/3] Installing / Verifying Dependencies (Tsinghua Mirror)"
echo "======================================================================"
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple || pip install -r requirements.txt

echo "======================================================================"
echo "[3/3] Running Pre-flight Integrity Check"
echo "======================================================================"
python3 check_bundle.py

echo "======================================================================"
echo "Setup Finished Successfully!"
echo "Next step: Start training with:  bash start_training.sh"
echo "======================================================================"
