"""Benchmark script for T4 GPU runtime and memory allocation.

Evaluates batch throughput, parameter count, and estimated peak VRAM
to verify that model complexity stays well within NVIDIA T4 16GB VRAM.
"""
import json
import time
from pathlib import Path
import numpy as np
import torch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cloud_t4_pilot.bilinear_interaction_model import BilinearInteractionDTI

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/dti-phase3-candidate-screening-20261012'


def run_benchmark():
    OUT.mkdir(parents=True, exist_ok=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    d_drug = 2048
    d_target = 1280
    hidden_dim = 128
    
    model = BilinearInteractionDTI(d_drug=d_drug, d_target=d_target, hidden_dim=hidden_dim).to(device)
    
    n_params = sum(p.numel() for p in model.parameters())
    param_size_mb = sum(p.numel() * p.element_size() for p in model.parameters()) / (1024 * 1024)
    
    batch_sizes = [64, 256, 1024]
    throughput_records = {}
    
    for bs in batch_sizes:
        drug_x = torch.randn(bs, d_drug, device=device)
        target_x = torch.randn(bs, d_target, device=device)
        
        # Warmup
        for _ in range(5):
            _ = model(drug_x, target_x)
            
        # Timed loop
        t0 = time.monotonic()
        for _ in range(20):
            out = model(drug_x, target_x)
            loss = out.sum()
            loss.backward()
            model.zero_grad()
        elapsed = time.monotonic() - t0
        
        samples_per_sec = (bs * 20) / elapsed
        throughput_records[f'bs_{bs}'] = {
            'batch_size': bs,
            'samples_per_sec': float(samples_per_sec),
            'ms_per_batch': float((elapsed / 20) * 1000)
        }
        
    vram_peak_mb = (
        torch.cuda.max_memory_allocated() / (1024 * 1024)
        if torch.cuda.is_available()
        else param_size_mb * 4  # estimated upper bound for activations
    )
    
    report = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'device': str(device),
        'device_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU (Smoke)',
        'parameter_count': int(n_params),
        'model_size_mb': float(param_size_mb),
        'vram_peak_mb': float(vram_peak_mb),
        't4_limit_mb': 16384.0,
        'vram_safe': bool(vram_peak_mb < 16384.0),
        'throughputs': throughput_records
    }
    
    out_file = OUT / 't4_pilot_benchmark.json'
    with out_file.open('w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    print(f"T4 pilot benchmark complete. Peak VRAM estimate: {vram_peak_mb:.2f} MB (T4 limit: 16,384 MB). Report saved to {out_file}")
    return report


if __name__ == '__main__':
    run_benchmark()
