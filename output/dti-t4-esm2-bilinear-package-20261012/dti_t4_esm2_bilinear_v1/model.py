"""Bilinear and cross-interaction DTI architecture for NVIDIA T4 GPU."""
import torch
import torch.nn as nn


class BilinearInteractionDTI(nn.Module):
    """Cross-interaction DTI neural model for candidate screening.

    Combines non-linear latent projections with a bilinear interaction head
    and additive skip connections to break the identical ranking degeneracy.
    """

    def __init__(
        self,
        d_drug: int = 2048,
        d_target: int = 480,
        hidden_dim: int = 128,
        dropout: float = 0.1
    ):
        super().__init__()
        self.d_drug = d_drug
        self.d_target = d_target
        self.hidden_dim = hidden_dim

        self.proj_drug = nn.Sequential(
            nn.Linear(d_drug, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        self.proj_target = nn.Sequential(
            nn.Linear(d_target, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )

        self.interaction_head = nn.Linear(hidden_dim, 1)

        self.linear_drug = nn.Linear(d_drug, 1, bias=False)
        self.linear_target = nn.Linear(d_target, 1, bias=False)
        self.bias = nn.Parameter(torch.zeros(1))

    def forward(self, drug_x: torch.Tensor, target_x: torch.Tensor) -> torch.Tensor:
        hd = self.proj_drug(drug_x)
        ht = self.proj_target(target_x)

        interaction = hd * ht
        interaction_score = self.interaction_head(interaction)

        additive_score = self.linear_drug(drug_x) + self.linear_target(target_x) + self.bias

        return interaction_score + additive_score
