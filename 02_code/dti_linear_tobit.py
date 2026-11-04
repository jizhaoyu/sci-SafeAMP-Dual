"""Equal-observation left-censored Gaussian linear baseline, without ranking weights.

This models a processed benchmark endpoint. A shared boundary of 5 is a
statistical assumption; heterogeneous source blanks are not verified assay bounds.
"""
import math

import numpy as np
from scipy.optimize import minimize
from scipy.special import log_ndtr
from sklearn.preprocessing import StandardScaler


def validate_data(x, y):
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    if (x.ndim != 2 or y.ndim != 1 or len(x) != len(y) or not len(y)
            or not x.shape[1] or not np.isfinite(x).all()
            or not np.isfinite(y).all() or np.any(y < 5)):
        raise ValueError('expected finite aligned nonempty X,y with encoded pKd >= 5')
    return x, y


def nll_gradient(theta, x, y, l2):
    """Mean per-observation NLL + L2/2, and analytic coefficient/log-sigma gradient."""
    w, intercept, log_sigma = theta[:-2], theta[-2], theta[-1]
    sigma = math.exp(log_sigma)
    mu = x @ w + intercept
    active = y > 5
    difference = mu[active] - y[active]
    nll = np.empty(len(y))
    dmu = np.empty(len(y))
    dscale = np.empty(len(y))
    nll[active] = log_sigma + .5*math.log(2*math.pi) + .5*(difference/sigma)**2
    dmu[active] = difference/sigma**2
    dscale[active] = 1 - (difference/sigma)**2
    z = (5-mu[~active])/sigma
    log_cdf = log_ndtr(z)
    mills = np.exp(-.5*z*z - .5*math.log(2*math.pi) - log_cdf)
    nll[~active] = -log_cdf
    dmu[~active] = mills/sigma
    dscale[~active] = mills*z
    gradient = np.concatenate([x.T @ dmu/len(y) + l2*w,
                               [dmu.mean(), dscale.mean()]])
    value = float(nll.mean() + .5*l2*np.dot(w, w))
    if not np.isfinite(value) or not np.isfinite(gradient).all():
        raise FloatingPointError('nonfinite Tobit objective/gradient')
    return value, gradient


class LinearTobit:
    """Deterministic regularized location model with one jointly estimated scale."""

    def __init__(self, l2=.01, max_iter=2000, ftol=1e-10, gtol=1e-5, maxls=50):
        self.l2 = l2
        self.max_iter = max_iter
        self.ftol = ftol
        self.gtol = gtol
        self.maxls = maxls

    def fit(self, x, y):
        x, y = validate_data(x, y)
        if self.l2 < 0 or not np.isfinite(self.l2):
            raise ValueError('l2 must be finite and nonnegative')
        # Keep state local until convergence; failed optimization never publishes a model.
        scaler = StandardScaler()
        scaled = scaler.fit_transform(x)
        initial = np.zeros(x.shape[1]+2)
        initial[-2] = y.mean()
        initial[-1] = math.log(float(np.clip(y.std(), .1, 10)))
        result = minimize(nll_gradient, initial, args=(scaled, y, self.l2), jac=True,
                          method='L-BFGS-B', bounds=[(None, None)]*(len(initial)-1)
                          + [(math.log(.1), math.log(10))],
                          options=dict(maxiter=self.max_iter, ftol=self.ftol,
                                       gtol=self.gtol, maxls=self.maxls))
        self.optimization_ = dict(success=bool(result.success), message=str(result.message),
                                  iterations=int(result.nit), evaluations=int(result.nfev),
                                  objective=float(result.fun),
                                  max_abs_gradient=float(np.max(np.abs(result.jac))))
        if not result.success or not np.isfinite(result.x).all():
            raise RuntimeError('Tobit optimizer did not converge: '+str(result.message))
        self.scaler_ = scaler
        self.coef_ = result.x[:-2].copy()
        self.intercept_ = float(result.x[-2])
        self.sigma_ = math.exp(float(result.x[-1]))
        self.fit_rows_ = len(y)
        return self

    def predict(self, x):
        if not hasattr(self, 'coef_'):
            raise ValueError('model is not fitted')
        x = np.asarray(x, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != len(self.coef_) or not np.isfinite(x).all():
            raise ValueError('invalid prediction features')
        return self.scaler_.transform(x) @ self.coef_ + self.intercept_
