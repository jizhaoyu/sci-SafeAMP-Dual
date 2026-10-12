"""Controlled 3-model candidate screening engine for DTI Phase 3.

Provides three unified models:
1. HGBContinuousBaseline: Continuous regression baseline (HGB iter=50).
2. LogRegCandidateClassifier: Linear regularized logistic regression on pKd >= 7.0.
3. HGBBinaryClassifier: Non-linear gradient boosting classifier on pKd >= 7.0.
"""
from typing import Optional
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class HGBContinuousBaseline:
    """Continuous target regression baseline (comparable to Phase 1 HGB)."""

    def __init__(self, max_iter: int = 50, random_state: int = 42):
        self.max_iter = max_iter
        self.random_state = random_state
        self.model = HistGradientBoostingRegressor(
            max_iter=self.max_iter,
            random_state=self.random_state
        )

    def fit(self, X: np.ndarray, y: np.ndarray):
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        self.model.fit(X, y)
        return self

    def predict_score(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        return self.model.predict(X)


class LogRegCandidateClassifier:
    """Regularized Logistic Regression classifier for pKd >= 7.0 candidates."""

    def __init__(self, C: float = 1.0, max_iter: int = 1000, random_state: int = 42):
        self.C = C
        self.max_iter = max_iter
        self.random_state = random_state
        self.constant_class_: Optional[int] = None
        self.pipeline: Optional[Pipeline] = None

    def fit(self, X: np.ndarray, y: np.ndarray):
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=int)
        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            self.constant_class_ = int(unique_classes[0])
            self.pipeline = None
            return self

        self.constant_class_ = None
        self.pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(
                C=self.C,
                max_iter=self.max_iter,
                random_state=self.random_state,
                solver='lbfgs'
            ))
        ])
        self.pipeline.fit(X, y)
        return self

    def predict_score(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        if self.constant_class_ is not None:
            return np.full(len(X), float(self.constant_class_), dtype=np.float64)
        # Returns probability of class 1
        probs = self.pipeline.predict_proba(X)
        classes = self.pipeline.named_steps['clf'].classes_
        if 1 in classes:
            idx = int(np.where(classes == 1)[0][0])
            return probs[:, idx]
        return probs[:, -1]


class HGBBinaryClassifier:
    """Histogram Gradient Boosting Classifier for pKd >= 7.0 candidates."""

    def __init__(self, max_iter: int = 50, random_state: int = 42):
        self.max_iter = max_iter
        self.random_state = random_state
        self.constant_class_: Optional[int] = None
        self.model: Optional[HistGradientBoostingClassifier] = None

    def fit(self, X: np.ndarray, y: np.ndarray):
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=int)
        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            self.constant_class_ = int(unique_classes[0])
            self.model = None
            return self

        self.constant_class_ = None
        self.model = HistGradientBoostingClassifier(
            loss='log_loss',
            max_iter=self.max_iter,
            random_state=self.random_state
        )
        self.model.fit(X, y)
        return self

    def predict_score(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        if self.constant_class_ is not None:
            return np.full(len(X), float(self.constant_class_), dtype=np.float64)
        probs = self.model.predict_proba(X)
        classes = self.model.classes_
        if 1 in classes:
            idx = int(np.where(classes == 1)[0][0])
            return probs[:, idx]
        return probs[:, -1]
