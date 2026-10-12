import pytest
import numpy as np

from dti_candidate_classifiers import (
    HGBContinuousBaseline,
    LogRegCandidateClassifier,
    HGBBinaryClassifier,
)


def test_classifier_interfaces_and_scores():
    rng = np.random.RandomState(42)
    n_samples, n_features = 100, 20
    X = rng.randn(n_samples, n_features)
    
    # y continuous between 5.0 and 9.0
    y_cont = rng.uniform(5.0, 9.0, size=n_samples)
    y_bin = (y_cont >= 7.0).astype(int)
    
    # 1. HGBContinuousBaseline
    m1 = HGBContinuousBaseline(max_iter=10, random_state=42)
    m1.fit(X, y_cont)
    s1 = m1.predict_score(X)
    assert isinstance(s1, np.ndarray)
    assert s1.shape == (n_samples,)
    assert np.isfinite(s1).all()
    
    # 2. LogRegCandidateClassifier
    m2 = LogRegCandidateClassifier(max_iter=100, random_state=42)
    m2.fit(X, y_bin)
    s2 = m2.predict_score(X)
    assert isinstance(s2, np.ndarray)
    assert s2.shape == (n_samples,)
    assert np.isfinite(s2).all()
    assert (s2 >= 0.0).all() and (s2 <= 1.0).all()  # Probabilities
    
    # 3. HGBBinaryClassifier
    m3 = HGBBinaryClassifier(max_iter=10, random_state=42)
    m3.fit(X, y_bin)
    s3 = m3.predict_score(X)
    assert isinstance(s3, np.ndarray)
    assert s3.shape == (n_samples,)
    assert np.isfinite(s3).all()
    assert (s3 >= 0.0).all() and (s3 <= 1.0).all()  # Probabilities


def test_single_class_edge_case():
    # If a training subset only has negative samples, must not crash
    X = np.ones((20, 5))
    y_bin = np.zeros(20, dtype=int)
    
    m_lr = LogRegCandidateClassifier(random_state=42)
    m_lr.fit(X, y_bin)
    s_lr = m_lr.predict_score(X)
    assert (s_lr == 0.0).all()
