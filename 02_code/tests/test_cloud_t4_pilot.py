import pytest
import numpy as np
import torch

from cloud_t4_pilot.bilinear_interaction_model import BilinearInteractionDTI
from cloud_t4_pilot.esm2_embedding_loader import load_or_mock_esm2_embeddings


def test_bilinear_interaction_model():
    batch_size = 32
    d_drug = 2048
    d_target = 1280  # ESM-2 embedding dimension
    
    model = BilinearInteractionDTI(d_drug=d_drug, d_target=d_target, hidden_dim=128)
    
    drug_x = torch.randn(batch_size, d_drug)
    target_x = torch.randn(batch_size, d_target)
    
    # Forward pass
    output = model(drug_x, target_x)
    assert output.shape == (batch_size, 1)
    assert torch.isfinite(output).all()
    
    # Backward pass
    loss = output.sum()
    loss.backward()
    for param in model.parameters():
        assert param.grad is not None
        assert torch.isfinite(param.grad).all()


def test_ranking_diversity():
    # Crucial property: Bilinear interaction MUST NOT have identical target ranking for different drugs!
    d_drug = 2048
    d_target = 1280
    model = BilinearInteractionDTI(d_drug=d_drug, d_target=d_target, hidden_dim=64)
    model.eval()
    
    # 2 different drugs
    d1 = torch.randn(1, d_drug)
    d2 = torch.randn(1, d_drug)
    
    # 10 candidate targets
    targets = torch.randn(10, d_target)
    
    # Repeat drugs for 10 targets
    d1_rep = d1.repeat(10, 1)
    d2_rep = d2.repeat(10, 1)
    
    with torch.no_grad():
        scores1 = model(d1_rep, targets).squeeze().numpy()
        scores2 = model(d2_rep, targets).squeeze().numpy()
        
    rank1 = np.argsort(scores1)
    rank2 = np.argsort(scores2)
    
    # With non-zero interaction, ranks should NOT be identical
    assert not np.array_equal(rank1, rank2), "Model must break additive identical ranking degeneracy"


def test_esm2_loader():
    target_ids = ['T1', 'T2', 'T3']
    emb = load_or_mock_esm2_embeddings(target_ids, dim=1280)
    assert emb.shape == (3, 1280)
    assert np.isfinite(emb).all()
