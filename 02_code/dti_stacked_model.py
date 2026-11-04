"""Independent module defining StackedDTIPredictor to ensure clean pickle serialization across all entry points."""
import numpy as np


class StackedDTIPredictor:
    """Self-contained stacked ensemble predictor for inference runtime."""
    def __init__(self, base_models: dict, meta_model, model_names: list[str]):
        self.base_models = base_models
        self.meta_model = meta_model
        self.model_names = model_names

    def predict(self, X: np.ndarray) -> np.ndarray:
        meta_features = np.zeros((X.shape[0], len(self.model_names)), dtype=np.float32)
        for i, m_name in enumerate(self.model_names):
            meta_features[:, i] = self.base_models[m_name].predict(X)
        return self.meta_model.predict(meta_features)
