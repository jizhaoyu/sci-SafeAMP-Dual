"""Unit tests for Tobit Censored Likelihood & Pairwise Ranking Engine."""
from __future__ import annotations

import numpy as np
import pytest
import torch

from dti_tobit_ranking_model import (
    PairwiseRankingLoss,
    TobitLoss,
    TobitRankingNet,
    TobitRankingRegressor,
)


def test_tobit_loss_censoring_properties():
    loss_fn = TobitLoss(censoring_threshold=5.0)
    log_sigma = torch.tensor(0.0)  # sigma = 1.0

    # 1. Censored pair with true y = 5.0
    y_true_cens = torch.tensor([5.0])
    
    # Model predicts sub-threshold (3.0, 4.0): valid unbound territory, loss should be small
    pred_low = torch.tensor([3.0])
    loss_low = loss_fn(pred_low, y_true_cens, log_sigma)

    # Model incorrectly predicts high affinity (7.0): false positive, should incur heavy penalty
    pred_high = torch.tensor([7.0])
    loss_high = loss_fn(pred_high, y_true_cens, log_sigma)

    assert loss_low.item() < loss_high.item(), (
        f"Tobit loss should heavily penalize over-predicting censored points: {loss_low} vs {loss_high}"
    )
    # The penalty ratio should be substantial
    assert loss_high.item() > loss_low.item() + 1.5


def test_pairwise_ranking_loss_directionality():
    rank_loss = PairwiseRankingLoss(tau=0.5, delta=0.5)

    y_true = torch.tensor([8.5, 5.0, 7.0])

    # Case A: Correct rank order (8.5 > 7.0 > 5.0)
    y_pred_correct = torch.tensor([8.8, 4.8, 6.9])
    loss_correct = rank_loss(y_pred_correct, y_true)

    # Case B: Inverted rank order
    y_pred_inverted = torch.tensor([4.5, 9.0, 6.0])
    loss_inverted = rank_loss(y_pred_inverted, y_true)

    assert loss_correct.item() < loss_inverted.item(), (
        f"Inverted ranking must yield higher loss: {loss_correct} vs {loss_inverted}"
    )


def test_tobit_net_forward_shapes():
    net_linear = TobitRankingNet(in_features=64, architecture="linear")
    x = torch.randn(10, 64)
    pred_lin, log_sigma_lin = net_linear(x)
    assert pred_lin.shape == (10,)
    assert log_sigma_lin.shape == ()

    net_mlp = TobitRankingNet(in_features=64, architecture="residual_mlp", hidden_dim=32)
    pred_mlp, log_sigma_mlp = net_mlp(x)
    assert pred_mlp.shape == (10,)
    assert log_sigma_mlp.shape == ()


def test_regressor_training_and_bias_audit():
    np.random.seed(42)
    torch.manual_seed(42)

    n_samples = 300
    n_features = 32

    # Synthetic features & true latent affinity
    X = np.random.randn(n_samples, n_features).astype(np.float32)
    true_w = np.random.randn(n_features).astype(np.float32) * 0.5
    y_latent = X @ true_w + 5.5 + np.random.randn(n_samples).astype(np.float32) * 0.3

    # Apply 5.0 censoring threshold (simulating DAVIS distribution)
    y_obs = np.maximum(y_latent, 5.0)

    regressor = TobitRankingRegressor(
        in_features=n_features,
        architecture="linear",
        max_epochs=15,
        batch_size=64,
        lr=0.01,
        verbose=False,
    )
    regressor.fit(X, y_obs)

    preds = regressor.predict(X)
    assert preds.shape == (n_samples,)
    assert np.isfinite(preds).all()

    eval_results = regressor.evaluate(X, y_obs)
    assert "all" in eval_results
    assert "censored_pairs" in eval_results
    assert "strong_binders" in eval_results
    assert eval_results["all"]["concordance_index"] > 0.65
