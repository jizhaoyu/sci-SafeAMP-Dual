import sys
from pathlib import Path
import pytest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from feature_extractor import clean_sequence
from model_dual_task import DualTaskLoss, SafeAMPDualNet

def test_invalid_residues_are_not_silently_removed():
    with pytest.raises(ValueError):
        clean_sequence('AKX123L')
    assert clean_sequence('  a k l \n') == 'AKL'

def test_missing_labels_do_not_contribute_to_loss():
    a = torch.tensor([0.2, -0.1], requires_grad=True)
    h = torch.tensor([0.4, 0.7], requires_grad=True)
    loss, _, _ = DualTaskLoss()(a, h, torch.tensor([1., float('nan')]), torch.tensor([float('nan'), 0.]))
    loss.backward()
    assert torch.isfinite(loss)
    assert a.grad[1] == 0 and h.grad[0] == 0

def test_all_missing_batch_is_rejected():
    x = torch.ones(2, requires_grad=True)
    with pytest.raises(ValueError, match='observed'):
        DualTaskLoss()(x, x, torch.full((2,), float('nan')), torch.full((2,), float('nan')))

def test_nonbinary_observed_label_is_rejected():
    with pytest.raises(ValueError, match='binary'):
        DualTaskLoss()(torch.ones(1), torch.ones(1), torch.tensor([2.]), torch.tensor([0.]))

@pytest.mark.parametrize('fusion', ['gated', 'concat', 'esm_only', 'phys_only'])
def test_ablation_forward_shapes(fusion):
    model = SafeAMPDualNet(fusion=fusion)
    a,h,z = model(torch.zeros(3,320), torch.zeros(3,44))
    assert a.shape == h.shape == (3,) and z.shape == (3,128)


def test_unavailable_real_encoder_never_silently_falls_back(monkeypatch):
    import types
    from feature_extractor import ESMFeatureExtractor
    def unavailable():raise OSError('unit-test unavailable encoder')
    monkeypatch.setitem(sys.modules,'esm',types.SimpleNamespace(pretrained=types.SimpleNamespace(esm2_t6_8M_UR50D=unavailable)))
    with pytest.raises(RuntimeError,match='disabled'):ESMFeatureExtractor()
    explicit=ESMFeatureExtractor(allow_fallback=True)
    assert not explicit.real_esm_available and explicit.backend=='synthetic-test-only'
    assert explicit.extract_sequence_embedding('ACDEFGHIKLMNPQ')[0].shape==(320,)
