"""Verified F1 Ridge inference with training-identical 2156D features; no fitting."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import threading

import joblib
import numpy as np
import sklearn

from extract_dti_davis_enhanced_features import extract_enhanced_drug_features, extract_enhanced_kinase_features
from research_utils import sha256
from smiles_validator import validate_smiles

MODEL_ID = "f1_ridge"
STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")


class F1RidgePredictor:
    def __init__(self, bundle: Path):
        self.bundle = Path(bundle).resolve()
        self.loaded = False
        self._lock = threading.Lock()

    def load(self):
        if self.loaded:
            return self
        with self._lock:
            if self.loaded:
                return self
            manifest = json.loads((self.bundle / "manifest.json").read_text(encoding="utf-8"))
            if manifest["model_id"] != MODEL_ID or manifest["feature_dimension"] != 2156:
                raise ValueError("F1 model identity/dimension mismatch")
            if manifest["sklearn_version"] != sklearn.__version__:
                raise ValueError("F1 model sklearn version mismatch")
            for relative, expected in manifest["files"].items():
                path = (self.bundle / relative).resolve()
                if not path.is_relative_to(self.bundle) or sha256(path) != expected:
                    raise ValueError(f"F1 artifact identity mismatch: {relative}")
            for name, expected in manifest["feature_code_sha256"].items():
                path = Path(__file__).resolve().parent / name
                if sha256(path) != expected:
                    raise ValueError(f"F1 feature implementation identity mismatch: {name}")
            catalog = json.loads((self.bundle / "catalog.json").read_text(encoding="utf-8"))
            d_ids = json.loads((self.bundle / "drug_ids.json").read_text(encoding="utf-8"))
            t_ids = json.loads((self.bundle / "target_ids.json").read_text(encoding="utf-8"))
            drug = np.load(self.bundle / "drug_features.npy", allow_pickle=False)
            target = np.load(self.bundle / "target_features.npy", allow_pickle=False)
            if drug.shape != (68, 2056) or target.shape != (379, 100):
                raise ValueError("F1 frozen feature dimensions changed")
            if not np.isfinite(drug).all() or not np.isfinite(target).all():
                raise ValueError("F1 frozen features contain nonfinite values")
            model = joblib.load(self.bundle / "model.joblib")
            if model.n_features_in_ != 2156 or model.alpha != 50.0 or not model.fit_intercept:
                raise ValueError("F1 fitted model contract mismatch")
            self.manifest = manifest
            self.model = model
            self.drug_smiles = catalog["drug_smiles"]
            self.target_sequences = catalog["target_sequences"]
            self.drug_features = {str(identity): drug[i] for i, identity in enumerate(d_ids)}
            self.target_features = {str(identity): target[i] for i, identity in enumerate(t_ids)}
            self._drug_by_smiles = {smiles: identity for identity, smiles in self.drug_smiles.items()}
            self._target_by_seq = {seq: identity for identity, seq in self.target_sequences.items()}
            self.train_drugs = set(catalog["train_drug_ids"])
            self.train_targets = set(catalog["train_target_ids"])
            # These matrices use the new model's bound feature space, not the older Web cache.
            self._train_drug_fps = np.stack([self.drug_features[i][:2048] for i in sorted(self.train_drugs)]) > 0
            self._train_targets = np.stack([self.target_features[i] for i in sorted(self.train_targets)])
            self._target_norms = np.linalg.norm(self._train_targets, axis=1)
            self.loaded = True
        return self

    @lru_cache(maxsize=256)
    def _drug(self, smiles: str):
        identity = self._drug_by_smiles.get(smiles)
        return self.drug_features[identity] if identity else extract_enhanced_drug_features(smiles)

    @lru_cache(maxsize=128)
    def _target(self, sequence: str):
        identity = self._target_by_seq.get(sequence)
        return self.target_features[identity] if identity else extract_enhanced_kinase_features(sequence)

    def pair_features(self, smiles: str, sequence: str):
        self.load()
        if not isinstance(smiles, str) or not smiles.strip():
            raise ValueError("SMILES must be a nonempty string")
        if not isinstance(sequence, str):
            raise ValueError("Target sequence must be a string")
        smiles = smiles.strip()
        sequence = "".join(sequence.split()).upper()
        validate_smiles(smiles)
        if not 10 <= len(sequence) <= 4096 or set(sequence) - STANDARD_AA:
            raise ValueError("Target sequence must contain 10–4096 supported amino acids")
        features = np.concatenate([self._drug(smiles), self._target(sequence)]).astype(np.float32)
        if features.shape != (2156,) or not np.isfinite(features).all():
            raise ValueError("F1 live feature contract mismatch")
        return features

    def predict_many(self, pairs):
        self.load()
        if not pairs:
            return np.empty(0, dtype=float)
        features = np.stack([self.pair_features(smiles, seq) for smiles, seq in pairs])
        prediction = self.model.predict(features)
        if not np.isfinite(prediction).all():
            raise ValueError("F1 predictions contain nonfinite values")
        return prediction

    def predict(self, smiles: str, sequence: str):
        return float(self.predict_many([(smiles, sequence)])[0])

    def diagnose_domain(self, smiles: str, sequence: str, threshold: float = .4):
        self.load()
        smiles = smiles.strip()
        sequence = "".join(sequence.split()).upper()
        fp = self._drug(smiles)[:2048] > 0
        intersection = np.sum(self._train_drug_fps & fp, axis=1)
        union = np.sum(self._train_drug_fps | fp, axis=1)
        drug_similarity = float(np.max(np.divide(intersection, union, out=np.zeros_like(intersection, dtype=float), where=union != 0)))
        target = self._target(sequence)
        norm = np.linalg.norm(target)
        denominator = self._target_norms * norm
        similarity = np.divide(self._train_targets @ target, denominator,
                               out=np.zeros(len(denominator), dtype=float), where=denominator != 0)
        target_similarity = float(np.clip(np.max(similarity), -1, 1))
        drug_id = self._drug_by_smiles.get(smiles)
        target_id = self._target_by_seq.get(sequence)
        seen_drug = drug_id in self.train_drugs if drug_id else drug_similarity >= threshold
        seen_target = target_id in self.train_targets if target_id else target_similarity >= threshold
        domain = {(True, True): "train_block", (False, False): "strict_dual_cold_test",
                  (True, False): "cold_target_test", (False, True): "cold_drug_test"}[(seen_drug, seen_target)]
        scope = "benchmark_identity" if drug_id and target_id else "similarity_heuristic"
        return domain, drug_similarity, target_similarity, scope

    def model_metadata(self):
        self.load()
        evaluation = self.manifest["metrics"]["eval_overall"]
        return {
            "id": MODEL_ID, "name": "F1 Ridge α=50（已核验基线）",
            "badge": f"双冷 CI {evaluation['ci']:.4f} · F1 2156维",
            "badge_color": "emerald", "is_recommended": True,
            "desc": "自定义确定性WL指纹＋SMILES文本描述符＋序列描述符；双冷975对，探索性结果。",
            "benchmark_version": self.manifest["version"], "model_version": self.manifest["version"],
            "seed": self.manifest["seed"], "feature_dimension": 2156,
            "model_sha256": self.manifest["files"]["model.joblib"],
            "train_ci": None, "dual_cold_ci": evaluation["ci"],
            "dual_cold_rmse": evaluation["rmse"], "cold_target_ci": None, "cold_drug_ci": None,
            "five_seed_ci_mean": self.manifest["five_seed_summary"]["ci_mean"],
            "evaluation_scope": "同一双冷基准域的探索性比较；新输入未直接验证。",
            "metrics_by_domain": {"strict_dual_cold_test": {**evaluation, "concordance_index": evaluation["ci"]}},
        }
