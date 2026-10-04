"""
model_dual_task.py
SafeAMP-Dual: 融合 ESM-2 深度语义嵌入与理化先验的双任务协同神经网络。
支持缺失标签掩码、多任务训练、特征融合消融及计算排序分数；不推断临床安全性。
"""

import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

# 确保 UTF-8 打印
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class AdaptiveFeatureGating(nn.Module):
    """
    自适应双模态门控融合层 (Cross-Feature Fusion Gate):
    根据多肽的电荷与疏水先验，动态加权 ESM-2 语义表征与物理化学特征。
    """
    def __init__(self, esm_dim: int = 320, phys_dim: int = 44, hidden_dim: int = 128):
        super().__init__()
        self.esm_proj = nn.Sequential(
            nn.Linear(esm_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU()
        )
        self.phys_proj = nn.Sequential(
            nn.Linear(phys_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU()
        )
        # 门控向量计算
        self.gate_net = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.Sigmoid()
        )
        self.out_norm = nn.LayerNorm(hidden_dim)

    def forward(self, x_esm: torch.Tensor, x_phys: torch.Tensor) -> torch.Tensor:
        h_esm = self.esm_proj(x_esm)
        h_phys = self.phys_proj(x_phys)
        
        # 门控权重 g (0~1 之间)
        combined = torch.cat([h_esm, h_phys], dim=-1)
        gate = self.gate_net(combined)
        
        # 自适应加权融合
        fused = gate * h_esm + (1.0 - gate) * h_phys
        return self.out_norm(fused)


class SafeAMPDualNet(nn.Module):
    """
    SafeAMP-Dual 核心双任务网络:
    - 共享特征骨干 (Shared Feature Encoder)
    - 抗菌活性专用分支 (AMP Task Head)
    - 溶血毒性专用分支 (Hemolytic Task Head)
    - 共享表示、独立任务输出头
    """
    def __init__(self, esm_dim: int = 320, phys_dim: int = 44, hidden_dim: int = 128, dropout_rate: float = 0.25, fusion: str = 'gated'):
        super().__init__()
        self.hidden_dim = hidden_dim
        
        # 1. 自适应特征门控
        self.fusion = fusion
        if fusion == 'gated':
            self.fusion_gate = AdaptiveFeatureGating(esm_dim, phys_dim, hidden_dim)
        elif fusion in {'concat', 'esm_only', 'phys_only'}:
            dim = {'concat': esm_dim + phys_dim, 'esm_only': esm_dim, 'phys_only': phys_dim}[fusion]
            self.fusion_gate = nn.Sequential(nn.Linear(dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU())
        else:
            raise ValueError(f'Unknown fusion variant: {fusion}')
        
        # 2. 共享特征表示骨干
        self.shared_encoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU()
        )
        
        # 3. 抗菌任务分支 (AMP Head)
        self.amp_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(64, 1)
        )
        
        # 4. 溶血毒性任务分支 (Hemolysis Head)
        self.hemo_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(64, 1)
        )

    def forward(self, x_esm: torch.Tensor, x_phys: torch.Tensor):
        """
        前向传播:
        返回:
        - amp_logits: 抗菌对数几率 (未经过 Sigmoid)
        - hemo_logits: 溶血对数几率 (未经过 Sigmoid)
        - h_shared: 共享特征表示 (用于 t-SNE 与表征分析)
        """
        if self.fusion == 'gated':
            fused = self.fusion_gate(x_esm, x_phys)
        else:
            inputs = {'concat': lambda: torch.cat([x_esm, x_phys], dim=-1),
                      'esm_only': lambda: x_esm, 'phys_only': lambda: x_phys}
            fused = self.fusion_gate(inputs[self.fusion]())
        h_shared = self.shared_encoder(fused)
        
        amp_logits = self.amp_head(h_shared).squeeze(-1)
        hemo_logits = self.hemo_head(h_shared).squeeze(-1)
        
        return amp_logits, hemo_logits, h_shared

    @torch.no_grad()
    def predict_probabilities(self, x_esm: torch.Tensor, x_phys: torch.Tensor):
        """
        输出分类概率及探索性排序分数（不等同于治疗指数）:
        TSI = P_AMP * (1 - P_Hemo)
        """
        self.eval()
        amp_logits, hemo_logits, _ = self.forward(x_esm, x_phys)
        p_amp = torch.sigmoid(amp_logits).cpu().numpy()
        p_hemo = torch.sigmoid(hemo_logits).cpu().numpy()
        
        # Legacy TSI field: unvalidated computational ranking score only.
        tsi = p_amp * (1.0 - p_hemo)
        return p_amp, p_hemo, tsi


class DualTaskLoss(nn.Module):
    """
    带缺失标签掩码的固定权重双任务损失函数:
    L_total = alpha * L_AMP + beta * L_Hemo
    """
    def __init__(self, alpha: float = 1.0, beta: float = 1.0):
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        self.bce = nn.BCEWithLogitsLoss()

    def masked_loss(self, logits, targets):
        targets = targets.float()
        if torch.isinf(targets).any():
            raise ValueError('Targets must be binary or NaN.')
        mask = ~torch.isnan(targets)
        if not torch.all((targets[mask] == 0) | (targets[mask] == 1)):
            raise ValueError('Observed labels must be binary.')
        if not mask.any():
            return logits.sum() * 0.0
        return self.bce(logits[mask], targets[mask])

    def forward(self, amp_logits: torch.Tensor, hemo_logits: torch.Tensor,
                amp_targets: torch.Tensor, hemo_targets: torch.Tensor) -> torch.Tensor:
        if not (torch.isfinite(amp_targets).any() or torch.isfinite(hemo_targets).any()):
            raise ValueError('Batch must contain at least one observed label.')
        loss_amp = self.masked_loss(amp_logits, amp_targets)
        loss_hemo = self.masked_loss(hemo_logits, hemo_targets)
        return self.alpha * loss_amp + self.beta * loss_hemo, loss_amp, loss_hemo


if __name__ == "__main__":
    # 单元测试
    B = 8
    x_esm = torch.randn(B, 320)
    x_phys = torch.randn(B, 44)
    y_amp = torch.randint(0, 2, (B,)).float()
    y_hemo = torch.randint(0, 2, (B,)).float()
    
    model = SafeAMPDualNet()
    criterion = DualTaskLoss()
    
    amp_l, hemo_l, feat = model(x_esm, x_phys)
    loss, l_amp, l_hemo = criterion(amp_l, hemo_l, y_amp, y_hemo)
    
    p_amp, p_hemo, tsi = model.predict_probabilities(x_esm, x_phys)
    print(f"SafeAMPDualNet 模型前向测试成功:")
    print(f"  - 输出维度: amp_logits={amp_l.shape}, hemo_logits={hemo_l.shape}, shared_feat={feat.shape}")
    print(f"  - 损失值: Total={loss.item():.4f} (AMP={l_amp.item():.4f}, Hemo={l_hemo.item():.4f})")
    print(f"  - 样本0 预测概率: P_AMP={p_amp[0]:.3f}, P_Hemo={p_hemo[0]:.3f}, TSI={tsi[0]:.3f}")
