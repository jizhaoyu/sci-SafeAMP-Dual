"""Tobit Censored Likelihood & Differentiable Pairwise Ranking Model for DTI.

Designed to resolve the Negative Shrinkage Bias caused by 71.17% censored
unbound pairs (Kd >= 10,000 nM, pKd = 5.0) in the DAVIS benchmark.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import scipy.stats
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset


class TobitLoss(nn.Module):
    """Left-censored Tobit likelihood loss (Type I Tobit).

    For pKd in DAVIS:
    - Uncensored (y > 5.0): Gaussian log-likelihood with active_weight to counteract 71.17% censoring bias
    - Censored (y <= 5.0): Gaussian CDF survival prob Phi((5.0 - y_hat) / sigma)
    """

    def __init__(
        self,
        censoring_threshold: float = 5.0,
        active_weight: float = 2.8,
        strong_binder_boost: float = 1.5,
        eps: float = 1e-7,
    ):
        super().__init__()
        self.censoring_threshold = float(censoring_threshold)
        self.active_weight = float(active_weight)
        self.strong_binder_boost = float(strong_binder_boost)
        self.eps = float(eps)

    def forward(
        self,
        y_pred: torch.Tensor,
        y_true: torch.Tensor,
        log_sigma: torch.Tensor,
        censored_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Compute Tobit negative log-likelihood."""
        y_pred = y_pred.view(-1)
        y_true = y_true.view(-1)
        sigma = torch.exp(log_sigma).clamp(min=1e-3, max=5.0)

        if censored_mask is None:
            censored_mask = y_true <= self.censoring_threshold

        uncensored_mask = ~censored_mask
        total_loss = torch.tensor(0.0, device=y_pred.device, dtype=y_pred.dtype)

        # Uncensored: Gaussian NLL with active reweighting and strong binder boost
        if uncensored_mask.any():
            y_act_true = y_true[uncensored_mask]
            y_act_pred = y_pred[uncensored_mask]
            diff = y_act_true - y_act_pred

            # Sample weight: boost strong binders (pKd >= 7.0) to counteract negative shrinkage bias
            sample_weight = torch.ones_like(diff)
            sample_weight[y_act_true >= 7.0] = self.strong_binder_boost

            gauss_nll = (
                log_sigma
                + 0.5 * math.log(2.0 * math.pi)
                + (diff**2) / (2.0 * (sigma**2))
            ) * sample_weight

            mean_act_loss = gauss_nll.sum() / max(uncensored_mask.sum().item(), 1)
            total_loss = total_loss + self.active_weight * mean_act_loss

        # Censored: -log(Phi((y_0 - y_hat) / sigma))
        if censored_mask.any():
            z = (self.censoring_threshold - y_pred[censored_mask]) / (
                sigma * math.sqrt(2.0)
            )
            cdf = 0.5 * (1.0 + torch.erf(z))
            cdf = cdf.clamp(min=self.eps, max=1.0)
            cens_nll = -torch.log(cdf)
            mean_cens_loss = cens_nll.sum() / max(censored_mask.sum().item(), 1)
            total_loss = total_loss + mean_cens_loss

        return total_loss


class PairwiseRankingLoss(nn.Module):
    """Differentiable Concordance Index surrogate loss via pairwise Sigmoid margins."""

    def __init__(self, tau: float = 0.5, delta: float = 0.4):
        super().__init__()
        self.tau = float(tau)
        self.delta = float(delta)

    def forward(self, y_pred: torch.Tensor, y_true: torch.Tensor) -> torch.Tensor:
        """Compute pairwise ranking loss on candidate pairs."""
        y_pred = y_pred.view(-1)
        y_true = y_true.view(-1)
        n = y_pred.size(0)
        if n < 2:
            return torch.tensor(0.0, device=y_pred.device, dtype=y_pred.dtype)

        # Broadcast differences: row i, col j represents (item i - item j)
        diff_true = y_true.unsqueeze(1) - y_true.unsqueeze(0)  # (N, N)
        diff_pred = y_pred.unsqueeze(1) - y_pred.unsqueeze(0)  # (N, N)

        # Only evaluate pairs where true difference exceeds separation margin delta
        mask = diff_true > self.delta
        if not mask.any():
            return torch.tensor(0.0, device=y_pred.device, dtype=y_pred.dtype)

        # Softplus(-diff_pred / tau) = log(1 + exp(-(y_pred_i - y_pred_j) / tau))
        pair_losses = F.softplus(-diff_pred[mask] / self.tau)
        return pair_losses.mean()


class TobitRankingNet(nn.Module):
    """Neural architecture supporting linear or residual MLP backbone with uncertainty head."""

    def __init__(
        self,
        in_features: int = 2156,
        architecture: str = "residual_mlp",
        hidden_dim: int = 256,
        dropout: float = 0.15,
    ):
        super().__init__()
        self.in_features = in_features
        self.architecture = architecture

        # Learnable log-scale noise parameter for Tobit likelihood
        self.log_sigma = nn.Parameter(torch.tensor(0.0))

        if architecture == "linear":
            self.backbone = nn.Identity()
            self.head = nn.Linear(in_features, 1)
        elif architecture == "residual_mlp":
            self.proj_in = nn.Linear(in_features, hidden_dim)
            self.norm1 = nn.LayerNorm(hidden_dim)
            self.act1 = nn.SiLU()
            self.drop1 = nn.Dropout(dropout)

            self.block = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.SiLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, hidden_dim),
            )
            self.norm2 = nn.LayerNorm(hidden_dim)
            self.act2 = nn.SiLU()

            # Skip connection from input features
            self.skip = nn.Linear(in_features, hidden_dim)
            self.head = nn.Linear(hidden_dim, 1)
        else:
            raise ValueError(f"Unknown architecture: {architecture}")

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        if self.architecture == "linear":
            out = self.head(x)
        else:
            h0 = self.drop1(self.act1(self.norm1(self.proj_in(x))))
            res = self.block(h0)
            h = self.act2(self.norm2(h0 + res + self.skip(x)))
            out = self.head(h)
        return out.squeeze(-1), self.log_sigma


class TobitRankingRegressor:
    """Scikit-Learn compatible Tobit & Pairwise Ranking Regressor."""

    def __init__(
        self,
        in_features: int = 2156,
        architecture: str = "residual_mlp",
        censoring_threshold: float = 5.0,
        active_weight: float = 2.8,
        strong_binder_boost: float = 1.5,
        ranking_weight: float = 0.40,
        l2_reg: float = 1e-4,
        lr: float = 1e-3,
        batch_size: int = 256,
        max_epochs: int = 40,
        early_stopping_patience: int = 8,
        device: Optional[str] = None,
        random_state: int = 42,
        verbose: bool = True,
    ):
        self.in_features = in_features
        self.architecture = architecture
        self.censoring_threshold = censoring_threshold
        self.active_weight = active_weight
        self.strong_binder_boost = strong_binder_boost
        self.ranking_weight = ranking_weight
        self.l2_reg = l2_reg
        self.lr = lr
        self.batch_size = batch_size
        self.max_epochs = max_epochs
        self.early_stopping_patience = early_stopping_patience
        self.random_state = random_state
        self.verbose = verbose

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.model: Optional[TobitRankingNet] = None
        self.tobit_loss = TobitLoss(
            censoring_threshold=censoring_threshold,
            active_weight=active_weight,
            strong_binder_boost=strong_binder_boost,
        )
        self.ranking_loss = PairwiseRankingLoss(tau=0.5, delta=0.4)
        self.history_: list[dict[str, float]] = []

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        verbose: Optional[bool] = None,
    ) -> "TobitRankingRegressor":
        if verbose is None:
            verbose = self.verbose
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        self.model = TobitRankingNet(
            in_features=self.in_features,
            architecture=self.architecture,
        ).to(self.device)

        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.lr,
            weight_decay=self.l2_reg,
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=self.max_epochs, eta_min=1e-5
        )

        dataset = TensorDataset(
            torch.from_numpy(X_train).float(),
            torch.from_numpy(y_train).float(),
        )
        loader = DataLoader(
            dataset, batch_size=self.batch_size, shuffle=True, drop_last=False
        )

        best_val_score = float("inf")
        patience_counter = 0
        best_state = None

        for epoch in range(1, self.max_epochs + 1):
            self.model.train()
            epoch_tobit = 0.0
            epoch_rank = 0.0
            epoch_total = 0.0
            batches = 0

            for bx, by in loader:
                bx, by = bx.to(self.device), by.to(self.device)
                optimizer.zero_grad()

                pred, log_sigma = self.model(bx)
                l_tobit = self.tobit_loss(pred, by, log_sigma)
                l_rank = self.ranking_loss(pred, by)

                total_loss = l_tobit + self.ranking_weight * l_rank
                total_loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=2.0)
                optimizer.step()

                epoch_tobit += l_tobit.item()
                epoch_rank += l_rank.item()
                epoch_total += total_loss.item()
                batches += 1

            scheduler.step()

            train_metrics = {
                "epoch": epoch,
                "tobit_loss": epoch_tobit / max(batches, 1),
                "rank_loss": epoch_rank / max(batches, 1),
                "total_loss": epoch_total / max(batches, 1),
            }

            if X_val is not None and y_val is not None:
                val_eval = self.evaluate(X_val, y_val)
                # Validation monitor: balanced RMSE + (1 - CI) on validation set
                val_score = val_eval["all"]["rmse"] + (1.0 - val_eval["all"]["concordance_index"])
                train_metrics["val_rmse"] = val_eval["all"]["rmse"]
                train_metrics["val_ci"] = val_eval["all"]["concordance_index"]
                train_metrics["val_strong_bias"] = val_eval["strong_binders"]["mean_bias"]

                if val_score < best_val_score:
                    best_val_score = val_score
                    patience_counter = 0
                    best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                else:
                    patience_counter += 1
                    if patience_counter >= self.early_stopping_patience:
                        if verbose:
                            print(f"[EarlyStop] Epoch {epoch}: stopping early, restored best checkpoint.")
                        break

            self.history_.append(train_metrics)
            if verbose and (epoch % 5 == 0 or epoch == 1):
                msg = f"Epoch {epoch:2d}/{self.max_epochs} | Loss: {train_metrics['total_loss']:.4f} (Tobit: {train_metrics['tobit_loss']:.4f}, Rank: {train_metrics['rank_loss']:.4f})"
                if "val_rmse" in train_metrics:
                    msg += f" | Val RMSE: {train_metrics['val_rmse']:.4f}, CI: {train_metrics['val_ci']:.4f}, Strong Bias: {train_metrics['val_strong_bias']:.3f}"
                print(msg)

        if best_state is not None:
            self.model.load_state_dict(best_state)

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model is not fitted.")
        self.model.eval()
        with torch.no_grad():
            bx = torch.from_numpy(X).float().to(self.device)
            pred, _ = self.model(bx)
            return pred.cpu().numpy()

    def predict_with_uncertainty(self, X: np.ndarray) -> Tuple[np.ndarray, float]:
        if self.model is None:
            raise RuntimeError("Model is not fitted.")
        self.model.eval()
        with torch.no_grad():
            bx = torch.from_numpy(X).float().to(self.device)
            pred, log_sigma = self.model(bx)
            sigma = torch.exp(log_sigma).item()
            return pred.cpu().numpy(), float(sigma)

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> dict[str, Any]:
        """Stratified audit across all, censored, active, and strong-binding subsets."""
        y_pred = self.predict(X)
        y_true = np.asarray(y, dtype=np.float32)

        def _subset_metrics(t: np.ndarray, p: np.ndarray) -> dict[str, float]:
            if len(t) == 0:
                return {
                    "count": 0,
                    "rmse": 0.0,
                    "mae": 0.0,
                    "mean_bias": 0.0,
                    "concordance_index": 0.5,
                    "spearman_rho": 0.0,
                }
            diff = p - t
            rmse = float(np.sqrt(np.mean(diff**2)))
            mae = float(np.mean(np.abs(diff)))
            mean_bias = float(np.mean(diff))

            # CI computation
            ci = self.compute_ci_fast(t, p)

            # Spearman
            if len(t) > 2 and np.std(p) > 1e-6 and np.std(t) > 1e-6:
                rho, _ = scipy.stats.spearmanr(t, p)
                spearman_rho = float(rho) if not np.isnan(rho) else 0.0
            else:
                spearman_rho = 0.0

            return {
                "count": int(len(t)),
                "rmse": rmse,
                "mae": mae,
                "mean_bias": mean_bias,
                "concordance_index": ci,
                "spearman_rho": spearman_rho,
            }

        # Subsets
        cens_mask = y_true <= self.censoring_threshold
        active_mask = y_true > self.censoring_threshold
        strong_mask = y_true >= 7.0

        return {
            "all": _subset_metrics(y_true, y_pred),
            "censored_pairs": _subset_metrics(y_true[cens_mask], y_pred[cens_mask]),
            "active_pairs": _subset_metrics(y_true[active_mask], y_pred[active_mask]),
            "strong_binders": _subset_metrics(y_true[strong_mask], y_pred[strong_mask]),
        }

    @staticmethod
    def compute_ci_fast(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Vectorized O(N^2) Concordance Index calculation for numpy arrays."""
        n = len(y_true)
        if n < 2:
            return 0.5
        # For very large arrays (> 8000), sample to prevent OOM
        if n > 6000:
            idx = np.random.choice(n, size=6000, replace=False)
            y_true, y_pred = y_true[idx], y_pred[idx]
            n = 6000

        t_diff = y_true[:, None] - y_true[None, :]
        p_diff = y_pred[:, None] - y_pred[None, :]

        valid = t_diff > 0
        denom = np.sum(valid)
        if denom == 0:
            return 0.5

        concordant = np.sum((p_diff > 0) & valid)
        ties = np.sum((p_diff == 0) & valid) * 0.5
        return float((concordant + ties) / denom)

    def save_checkpoint(self, path: Union[str, Path]):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_state_dict": self.model.state_dict() if self.model else None,
                "in_features": self.in_features,
                "architecture": self.architecture,
                "censoring_threshold": self.censoring_threshold,
                "ranking_weight": self.ranking_weight,
                "history": self.history_,
            },
            path,
        )

    def load_checkpoint(self, path: Union[str, Path]):
        ckpt = torch.load(path, map_location=self.device)
        self.in_features = ckpt["in_features"]
        self.architecture = ckpt["architecture"]
        self.censoring_threshold = ckpt["censoring_threshold"]
        self.ranking_weight = ckpt["ranking_weight"]
        self.history_ = ckpt.get("history", [])

        self.model = TobitRankingNet(
            in_features=self.in_features,
            architecture=self.architecture,
        ).to(self.device)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.eval()
        return self
