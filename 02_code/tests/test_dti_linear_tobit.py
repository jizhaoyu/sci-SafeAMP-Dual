"""Acceptance of equal-observation NLL, gradients, censor direction and fit scope."""
import importlib
from pathlib import Path

import numpy as np
import pytest
from scipy.optimize import check_grad


@pytest.fixture
def api():
    path = Path(__file__).parents[1] / 'dti_linear_tobit.py'
    if not path.exists():
        pytest.fail('equal-weight linear Tobit implementation is missing')
    return importlib.import_module('dti_linear_tobit')


def test_equal_observation_mean_not_classwise_mean(api):
    # At mu=5,sigma=1: two censored contributions log(2), one density contribution.
    x = np.zeros((3, 1))
    y = np.array([5., 5., 6.])
    value, _ = api.nll_gradient(np.array([0., 5., 0.]), x, y, 0.)
    assert value == pytest.approx(1.0/3 * (2*np.log(2) + .5*np.log(2*np.pi) + .5))


def test_no_strong_binder_boost(api):
    value, _ = api.nll_gradient(np.array([0., 7., 0.]), np.zeros((2, 1)), np.array([6., 8.]), 0.)
    assert value == pytest.approx(.5*np.log(2*np.pi) + .5)


@pytest.mark.parametrize('labels', [[5., 5., 5.], [6., 7., 8.], [5., 6., 8.]])
def test_analytic_gradient_matches_finite_difference(api, labels):
    x = np.array([[1., -.3], [.4, .7], [-.5, 1.]])
    theta = np.array([.3, -.2, 5.8, .1])
    fn = lambda t: api.nll_gradient(t, x, np.array(labels), .02)
    assert check_grad(lambda t: fn(t)[0], lambda t: fn(t)[1], theta) < 2e-6


def test_censored_prediction_above_boundary_costs_more(api):
    x, y = np.zeros((1, 1)), np.array([5.])
    low, _ = api.nll_gradient(np.array([0., 4., 0.]), x, y, 0.)
    high, gradient = api.nll_gradient(np.array([0., 6., 0.]), x, y, 0.)
    assert low < high
    assert gradient[1] > 0  # Descent reduces mu; reversed censor direction breaks this.


def test_extreme_tail_has_finite_nonzero_gradient(api):
    value, gradient = api.nll_gradient(np.array([0., 105., 0.]), np.zeros((1, 1)), np.array([5.]), 0.)
    assert np.isfinite(value) and np.isfinite(gradient).all()
    assert value > 5000 and gradient[1] > 99


@pytest.mark.parametrize('x,y', [(np.zeros((2, 1)), np.array([5.])),
                               (np.array([[np.nan]]), np.array([5.])),
                               (np.zeros((1, 1)), np.array([4.])),
                               (np.empty((0, 1)), np.array([]))])
def test_reject_invalid_training_input(api, x, y):
    with pytest.raises(ValueError):
        api.LinearTobit().fit(x, y)


def test_fit_scope_and_gaussian_special_case(api):
    x = np.array([[-2.], [-1.], [0.], [1.], [2.]])
    y = np.array([5.8, 6.9, 8., 9.1, 9.8])
    model = api.LinearTobit(l2=0., max_iter=500).fit(x, y)
    # All observations uncensored: mean coefficients reduce to ordinary least squares.
    assert model.predict(np.array([[0.], [1.]])) == pytest.approx([7.92, 8.94], abs=1e-5)
    before = model.scaler_.mean_.copy()
    model.predict(np.array([[1000.]]))
    np.testing.assert_array_equal(model.scaler_.mean_, before)
    assert model.scaler_.n_samples_seen_ == 5
    assert model.optimization_['success']


def test_nonconvergence_does_not_publish_fitted_model(api):
    model = api.LinearTobit(max_iter=1)
    with pytest.raises(RuntimeError, match='converge'):
        model.fit(np.array([[-2.], [-1.], [1.], [2.]]), np.array([5., 5., 7., 9.]))
    with pytest.raises(ValueError, match='fitted'):
        model.predict(np.array([[0.]]))
