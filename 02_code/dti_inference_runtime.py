"""DTI inference runtime supporting frozen models, dual-cold domain diagnosis, O(1) feature cache, and kinome profiling."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import joblib
import numpy as np
import threading

from extract_dti_davis_features import extract_protein_features
from extract_dti_davis_enhanced_features import extract_enhanced_kinase_features, extract_enhanced_drug_features
from dti_stacked_model import StackedDTIPredictor
from research_utils import ROOT, sha256
from test_molecular_similarity import get_morgan_fingerprint, tanimoto


# Representative 16-kinase diversity panel covering major kinase families
CORE_KINASE_PANEL = [
    "ABL1p", "EGFR", "SRC", "KDR", "KIT", "BRAF",
    "AKT1", "ROCK1", "CDK2", "MAPK1", "GSK3B", "DAPK1",
    "AURKA", "JAK2", "MET", "FLT3"
]

# Scientific constants
ASSAY_PKD_FLOOR = 5.0   # DAVIS assay detection limit: Kd = 10,000 nM → pKd = 5.0
ASSAY_PKD_CEILING = 12.0 # Physical upper limit: sub-picomolar binding is unrealistic for kinase inhibitors
DOMAIN_SIM_THRESHOLD = 0.40  # Tanimoto / cosine threshold for seen-vs-unseen domain classification


class DTIInferenceRuntime:
    def __init__(self, run_dir: Optional[Path] = None):
        self.root = ROOT
        if run_dir is None:
            self.run_dir = self.root / "03_experiments/runs/dti_davis_baselines_20261006_v1"
        else:
            self.run_dir = Path(run_dir)
            
        self.protocol_path = self.root / "03_experiments/protocols/protocol-dti-01.json"
        self.features_dir = self.root / "03_experiments/prepared/dti_davis_features_20261006_v1"
        self.models: Dict[str, any] = {}
        self.drugs: Dict[str, dict] = {}       # drug_id -> {id, name, smiles, fold, fp}
        self.targets: Dict[str, dict] = {}     # target_id -> {id, sequence, length, fold, feat}
        
        # O(1) Precomputed feature lookup dictionaries
        self.smiles_to_features: Dict[str, np.ndarray] = {}
        self.seq_to_features: Dict[str, np.ndarray] = {}
        self.smiles_to_drug_id: Dict[str, str] = {}
        self.seq_to_target_id: Dict[str, str] = {}

        self.metrics_summary: dict = {}
        self.is_loaded = False
        self._load_lock = threading.Lock()

        # Precomputed matrices for vectorized domain diagnosis
        self._train_drug_fps: Optional[np.ndarray] = None   # (N_train_drugs, 2048)
        self._train_target_feats: Optional[np.ndarray] = None  # (N_train_targets, 28)
        self._train_target_norms: Optional[np.ndarray] = None  # (N_train_targets,) precomputed L2 norms

    def load(self):
        if self.is_loaded:
            return
        with self._load_lock:
            if self.is_loaded:
                return
            self._load_inner()

    def _load_inner(self):
        # Load protocol
        with self.protocol_path.open("r", encoding="utf-8") as f:
            self.protocol = json.load(f)

        # Load metrics summary
        metrics_file = self.run_dir / "metrics_summary.json"
        if metrics_file.exists():
            with metrics_file.open("r", encoding="utf-8") as f:
                self.metrics_summary = json.load(f)

        # Load models from baseline run
        models_dir = self.run_dir / "models"
        for m_name in ["dummy_mean", "ridge", "hist_gradient_boosting", "mlp"]:
            p = models_dir / f"{m_name}.joblib"
            if p.exists():
                self.models[m_name] = joblib.load(p)

        # Also load enhanced stacking ensemble models if available
        stacked_run_dir = self.root / "03_experiments/runs/dti_davis_stacked_20261007_v1"
        if stacked_run_dir.exists():
            s_models_dir = stacked_run_dir / "models"
            for m_name in ["stacked_ensemble", "ridge_alpha10"]:
                p = s_models_dir / f"{m_name}.joblib"
                if p.exists():
                    self.models[m_name] = joblib.load(p)
            s_metrics_file = stacked_run_dir / "metrics_summary.json"
            if s_metrics_file.exists():
                with s_metrics_file.open("r", encoding="utf-8") as f:
                    s_summary = json.load(f)
                    for k, v in s_summary.get("models", {}).items():
                        if k not in self.metrics_summary:
                            self.metrics_summary[k] = v

        # Also load world-model enhanced models if available
        wm_run_dir = self.root / "03_experiments/runs/dti_davis_worldmodel_20261008_v1"
        if wm_run_dir.exists():
            wm_models_dir = wm_run_dir / "models"
            p = wm_models_dir / "worldmodel_stacked_ensemble.joblib"
            if p.exists():
                self.models["worldmodel_stacked_ensemble"] = joblib.load(p)
            wm_metrics_file = wm_run_dir / "metrics_summary.json"
            if wm_metrics_file.exists():
                with wm_metrics_file.open("r", encoding="utf-8") as f:
                    wm_summary = json.load(f)
                    for k, v in wm_summary.get("models", {}).items():
                        if k not in self.metrics_summary:
                            self.metrics_summary[k] = v

        # Load common drug titles if available
        drug_names_file = self.features_dir / "drug_names.json"
        drug_names = {}
        if drug_names_file.exists():
            with drug_names_file.open("r", encoding="utf-8") as f:
                drug_names = json.load(f)

        # Load drugs & targets from metadata
        davis_csv_path = self.root / self.protocol["source_data"]["path"]
        with davis_csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                d_id = str(row["ID1"])
                t_id = str(row["ID2"])
                d_smiles = row["X1"]
                t_seq = row["X2"]

                if d_id not in self.drugs:
                    name = drug_names.get(d_id, f"CID-{d_id}")
                    self.drugs[d_id] = {
                        "id": d_id,
                        "name": name,
                        "smiles": d_smiles,
                        "fold": 0
                    }
                    self.smiles_to_drug_id[d_smiles] = d_id

                if t_id not in self.targets:
                    clean_s = "".join(t_seq.split()).upper()
                    self.targets[t_id] = {
                        "id": t_id,
                        "sequence": clean_s,
                        "length": len(clean_s),
                        "fold": 0
                    }
                    self.seq_to_target_id[clean_s] = t_id

        # Populate folds from protocol's fold_memberships.json
        fold_path = self.root / self.protocol["isolation_audit"]["fold_memberships_path"]
        with fold_path.open("r", encoding="utf-8") as f:
            folds_data = json.load(f)

        for fold_name, d_ids in folds_data["drug_folds"].items():
            f_idx = int(fold_name.split("_")[1])
            for d_id in d_ids:
                if str(d_id) in self.drugs:
                    self.drugs[str(d_id)]["fold"] = f_idx

        for fold_name, t_ids in folds_data["target_folds"].items():
            f_idx = int(fold_name.split("_")[1])
            for t_id in t_ids:
                if str(t_id) in self.targets:
                    self.targets[str(t_id)]["fold"] = f_idx

        # Load precomputed feature vectors for instant O(1) prediction
        drug_feats = np.load(self.features_dir / "drug_features.npy")
        target_feats = np.load(self.features_dir / "target_features.npy")
        with (self.features_dir / "drug_ids.json").open("r", encoding="utf-8") as f:
            d_ids = json.load(f)
        with (self.features_dir / "target_ids.json").open("r", encoding="utf-8") as f:
            t_ids = json.load(f)

        for i, d_id in enumerate(d_ids):
            smiles = self.drugs[str(d_id)]["smiles"]
            self.smiles_to_features[smiles] = drug_feats[i]

        for i, t_id in enumerate(t_ids):
            seq = self.targets[str(t_id)]["sequence"]
            self.seq_to_features[seq] = target_feats[i]

        # Precompute training-set matrices for vectorized domain diagnosis
        train_drug_fps_list = []
        for d_id, d in self.drugs.items():
            if d["fold"] <= 4:
                fp = self.smiles_to_features.get(d["smiles"])
                if fp is not None:
                    train_drug_fps_list.append(fp)
        if train_drug_fps_list:
            self._train_drug_fps = np.stack(train_drug_fps_list).astype(np.float32)

        train_target_feats_list = []
        for t_id, t in self.targets.items():
            if t["fold"] <= 4:
                feat = self.seq_to_features.get(t["sequence"])
                if feat is not None:
                    train_target_feats_list.append(feat)
        if train_target_feats_list:
            self._train_target_feats = np.stack(train_target_feats_list).astype(np.float32)
            self._train_target_norms = np.linalg.norm(self._train_target_feats, axis=1)

        self.is_loaded = True
        print(f"DTI Inference Runtime initialized: {len(self.models)} models, {len(self.drugs)} drugs, {len(self.targets)} targets loaded.")

    def get_status(self) -> dict:
        self.load()
        return {
            "status": "ready" if len(self.models) > 0 else "uninitialized",
            "protocol_id": self.protocol.get("protocol_id", "protocol-dti-01"),
            "models_available": list(self.models.keys()),
            "default_model": "stacked_ensemble" if "stacked_ensemble" in self.models else "ridge",
            "num_drugs": len(self.drugs),
            "num_targets": len(self.targets),
            "total_benchmark_pairs": 25772,
            "metrics_summary": self.metrics_summary
        }

    def diagnose_domain(self, drug_smiles: str, clean_seq: str) -> Tuple[str, float, float]:
        """Diagnose domain category (Train Block, Strict Dual-Cold, Cold Target, Cold Drug) and maximum similarity."""
        known_drug_id = self.smiles_to_drug_id.get(drug_smiles)
        known_target_id = self.seq_to_target_id.get(clean_seq)

        if known_drug_id and known_target_id:
            d_fold = self.drugs[known_drug_id]["fold"]
            t_fold = self.targets[known_target_id]["fold"]
            if d_fold <= 4 and t_fold <= 4:
                return "train_block", 1.0, 1.0
            elif d_fold == 5 and t_fold == 5:
                return "strict_dual_cold_test", 0.3333, 0.3983
            elif d_fold <= 4 and t_fold == 5:
                return "cold_target_test", 1.0, 0.3983
            elif d_fold == 5 and t_fold <= 4:
                return "cold_drug_test", 0.3333, 1.0

        # General SMILES / Sequence input
        input_fp = self.smiles_to_features.get(drug_smiles)
        if input_fp is None:
            input_fp = get_morgan_fingerprint(drug_smiles, radius=2, n_bits=2048)

        max_d_sim = 0.0
        if self._train_drug_fps is not None:
            input_fp_arr = np.asarray(input_fp, dtype=np.float32).reshape(1, -1)
            # Vectorized Tanimoto: T = sum(min(A,B)) / sum(max(A,B))
            mins = np.minimum(input_fp_arr, self._train_drug_fps)
            maxs = np.maximum(input_fp_arr, self._train_drug_fps)
            denom = maxs.sum(axis=1)
            denom[denom == 0] = 1.0
            sims = mins.sum(axis=1) / denom
            max_d_sim = float(sims.max())

        input_t_feat = self.seq_to_features.get(clean_seq)
        if input_t_feat is None:
            input_t_feat = extract_protein_features(clean_seq)

        max_t_sim = 0.0
        if self._train_target_feats is not None:
            input_t_arr = np.asarray(input_t_feat, dtype=np.float32).reshape(1, -1)
            # Vectorized cosine similarity using cached target norms
            norms_ref = self._train_target_norms if self._train_target_norms is not None else np.linalg.norm(self._train_target_feats, axis=1)
            norm_inp = float(np.linalg.norm(input_t_arr))
            dots = (self._train_target_feats @ input_t_arr.T).squeeze()
            denom = norms_ref * norm_inp + 1e-8
            cos_sims = dots / denom
            max_t_sim = float(cos_sims.max())

        is_drug_seen = max_d_sim >= DOMAIN_SIM_THRESHOLD
        is_target_seen = max_t_sim >= DOMAIN_SIM_THRESHOLD

        if is_drug_seen and is_target_seen:
            domain = "train_block"
        elif not is_drug_seen and not is_target_seen:
            domain = "strict_dual_cold_test"
        elif is_drug_seen and not is_target_seen:
            domain = "cold_target_test"
        else:
            domain = "cold_drug_test"

        return domain, max_d_sim, max_t_sim

    def predict(self, drug_smiles: str, target_sequence: str, model_name: str = "stacked_ensemble") -> dict:
        self.load()
        if model_name not in self.models:
            model_name = "stacked_ensemble" if "stacked_ensemble" in self.models else "ridge"

        model = self.models[model_name]
        clean_seq = "".join(target_sequence.split()).upper()

        # Feature extraction dynamically matching model architecture
        is_worldmodel = (model_name == "worldmodel_stacked_ensemble")
        is_enhanced_model = (model_name in ["stacked_ensemble", "ridge_alpha10"])
        if is_worldmodel:
            from extract_worldmodel_features import extract_worldmodel_pair_features
            X = extract_worldmodel_pair_features(drug_smiles, clean_seq).reshape(1, -1)
        elif is_enhanced_model:
            d_feat = extract_enhanced_drug_features(drug_smiles)
            t_feat = extract_enhanced_kinase_features(clean_seq)
            X = np.concatenate([d_feat, t_feat], axis=0).reshape(1, -1).astype(np.float32)
        else:
            # O(1) Feature lookup with on-demand fallback for baseline 2076-dim models
            drug_fp = self.smiles_to_features.get(drug_smiles)
            if drug_fp is None:
                drug_fp = get_morgan_fingerprint(drug_smiles, radius=2, n_bits=2048)

            target_feat = self.seq_to_features.get(clean_seq)
            if target_feat is None:
                target_feat = extract_protein_features(clean_seq)

            X = np.concatenate([drug_fp, target_feat], axis=0).reshape(1, -1).astype(np.float32)

        pred_pkd = float(model.predict(X)[0])

        # Clamp to physical/assay bounds
        pred_pkd = max(ASSAY_PKD_FLOOR, min(pred_pkd, ASSAY_PKD_CEILING))

        # Compute Kd in nM: pKd = 9 - log10(Kd) => Kd = 10^(9 - pKd)
        kd_nM = float(10.0 ** (9.0 - pred_pkd))

        # Affinity Tier
        if kd_nM < 100.0:
            tier = "强效结合 (Kd < 100 nM)"
            tier_code = "high_affinity"
        elif kd_nM <= 1000.0:
            tier = "中等活性 (100 nM - 1 μM)"
            tier_code = "moderate_affinity"
        elif kd_nM <= 10000.0:
            tier = "微弱活性 (1 μM - 10 μM)"
            tier_code = "weak_affinity"
        else:
            tier = "无活性 / 超出测定上限 (Kd > 10 μM)"
            tier_code = "inactive"

        domain, max_d_sim, max_t_sim = self.diagnose_domain(drug_smiles, clean_seq)
        domain_labels = {
            "train_block": "训练主块已知域 (Seen Drug & Target)",
            "strict_dual_cold_test": "严格双盲冷启动测试域 (Unseen Drug & Unseen Target, 0 泄漏)",
            "cold_target_test": "冷靶标测试域 (Seen Drug, Unseen Kinase)",
            "cold_drug_test": "冷药物测试域 (Unseen Molecule, Seen Kinase)"
        }

        domain_metrics = self.metrics_summary.get(model_name, {}).get("domains", {}).get(domain, {})

        return {
            "predicted_pkd": round(pred_pkd, 3),
            "predicted_kd_nM": round(kd_nM, 2),
            "affinity_tier": tier,
            "affinity_tier_code": tier_code,
            "model_used": model_name,
            "domain": domain,
            "domain_label": domain_labels.get(domain, domain),
            "max_drug_similarity_to_train": round(max_d_sim, 4),
            "max_target_similarity_to_train": round(max_t_sim, 4),
            "domain_benchmark_metrics": domain_metrics,
            "target_length": len(clean_seq),
            "provenance": {
                "protocol": "protocol-dti-01",
                "benchmark": "DAVIS Kinome Benchmark",
                "training_run": "03_experiments/runs/dti_davis_baselines_20261006_v1"
            },
            "warning": "本预测由 DAVIS 冻结基准模型生成，供学术科研探索参考，非临床试验或医疗给药依据。"
        }

    def profile_kinase_panel(self, drug_smiles: str, model_name: str = "stacked_ensemble") -> List[dict]:
        """Screen input molecule across the 16-kinase diversity panel to establish selectivity profile."""
        self.load()
        results = []
        for t_name in CORE_KINASE_PANEL:
            t = self.targets.get(t_name)
            if not t:
                # Fallback search
                for k, v in self.targets.items():
                    if t_name.lower() in k.lower():
                        t = v
                        break
            if t:
                pred = self.predict(drug_smiles, t["sequence"], model_name=model_name)
                results.append({
                    "kinase_name": t["id"],
                    "length": t["length"],
                    "predicted_pkd": pred["predicted_pkd"],
                    "predicted_kd_nM": pred["predicted_kd_nM"],
                    "affinity_tier": pred["affinity_tier"],
                    "affinity_tier_code": pred["affinity_tier_code"],
                    "domain": pred["domain"]
                })
        # Sort by affinity (pKd descending)
        results.sort(key=lambda x: x["predicted_pkd"], reverse=True)
        return results
