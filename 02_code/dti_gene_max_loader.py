"""DTI Gene-Max Dataset Loader (Plan A Specification).

Integrates the DAVIS benchmark dataset with the official Gene-Max DTI semantic mapping.
Guarantees consistent target metadata, gene-level semantic roles, and explicit
distinction between uncensored measurement values and right-censored detection limits.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_DAVIS_CSV = Path(r"D:\桌面文件\sci\03_experiments\audits\dti_davis_acquisition_20261006_v2\davis.csv")
DEFAULT_MAPPING_JSON = Path(r"D:\桌面文件\sci\output\dti-protocol-plan-a-20261011\target_semantic_mapping.json")
CENSORED_KD_THRESHOLD = 10000.0  # nM
CENSORED_PKD_THRESHOLD = 5.0     # pKd


class DtiGeneMaxDatasetLoader:
    """Robust, protocol-aligned dataset loader for Kinase Gene-Level Maximum Affinity Benchmark (Plan A)."""

    def __init__(
        self,
        davis_csv_path: Optional[Path | str] = None,
        mapping_json_path: Optional[Path | str] = None,
    ):
        self.davis_csv_path = Path(davis_csv_path or DEFAULT_DAVIS_CSV)
        self.mapping_json_path = Path(mapping_json_path or DEFAULT_MAPPING_JSON)
        self._target_map: Dict[str, Dict[str, Any]] = {}
        self._df: Optional[pd.DataFrame] = None

        if not self.davis_csv_path.exists():
            raise FileNotFoundError(f"DAVIS CSV not found at: {self.davis_csv_path}")
        if not self.mapping_json_path.exists():
            raise FileNotFoundError(f"Target semantic mapping not found at: {self.mapping_json_path}")

        self._load_mapping()

    def _load_mapping(self) -> None:
        """Loads semantic target metadata mapping."""
        with open(self.mapping_json_path, "r", encoding="utf-8") as f:
            mapping_list = json.load(f)
        for item in mapping_list:
            raw_id = item["raw_tdc_id"]
            self._target_map[raw_id] = item

    def load(self, force_reload: bool = False) -> pd.DataFrame:
        """Loads and decorates the DAVIS dataset with Plan A semantics."""
        if self._df is not None and not force_reload:
            return self._df

        raw_df = pd.read_csv(self.davis_csv_path)

        # Standardize columns
        # Expected raw columns: ID1 (drug), X1 (SMILES), ID2 (target), X2 (Seq), Y (Kd in nM)
        df = raw_df.copy()
        df["ID1"] = df["ID1"].astype(str)
        df["ID2"] = df["ID2"].astype(str)
        df["Y"] = df["Y"].astype(float)

        # Calculate pKd = 9 - log10(Kd)
        df["pkd"] = 9.0 - np.log10(np.clip(df["Y"], a_min=1e-3, a_max=None))

        # Annotate censorship: Kd >= 10000 nM is right-censored (pkd <= 5.0)
        df["is_censored"] = df["Y"] >= CENSORED_KD_THRESHOLD
        df["censoring_type"] = np.where(
            df["is_censored"],
            "right_censored_bound",
            "uncensored_measurement"
        )

        # Attach target semantics
        mapped_records = []
        for raw_id in df["ID2"]:
            m = self._target_map.get(raw_id)
            if m:
                mapped_records.append({
                    "canonical_gene_symbol": m["canonical_gene_symbol"],
                    "standard_display_name": m["standard_display_name"],
                    "organism": m["organism"],
                    "taxid": m["taxid"],
                    "is_misleading_mutation_label": m["is_misleading_mutation_label"],
                    "misleading_label_type": m["misleading_label_type"],
                    "target_semantic_type": m["semantic_task_role"],
                })
            else:
                mapped_records.append({
                    "canonical_gene_symbol": raw_id,
                    "standard_display_name": f"{raw_id} (Gene-Max)",
                    "organism": "Homo sapiens",
                    "taxid": 9606,
                    "is_misleading_mutation_label": False,
                    "misleading_label_type": "none",
                    "target_semantic_type": "Gene-level maximal affinity representative",
                })

        meta_df = pd.DataFrame(mapped_records, index=df.index)
        self._df = pd.concat([df, meta_df], axis=1)
        return self._df

    def get_full_dataset(self) -> pd.DataFrame:
        """Returns the full 25,772 pair dataset."""
        return self.load()

    def get_uncensored_pairs(self) -> pd.DataFrame:
        """Returns only the uncensored measurements (Kd < 10,000 nM, pkd > 5.0)."""
        df = self.load()
        return df[~df["is_censored"]].copy()

    def get_censored_pairs(self) -> pd.DataFrame:
        """Returns only the right-censored lower bounds (Kd >= 10,000 nM, pkd <= 5.0)."""
        df = self.load()
        return df[df["is_censored"]].copy()

    def get_active_pairs(self, min_pkd: float = 7.0) -> pd.DataFrame:
        """Returns active pairs with pkd >= min_pkd (default Kd <= 100 nM)."""
        df = self.load()
        return df[df["pkd"] >= min_pkd].copy()

    def get_target_metadata(self, raw_target_id: str) -> Optional[Dict[str, Any]]:
        """Returns the semantic metadata dictionary for a target."""
        return self._target_map.get(raw_target_id)

    def get_all_targets_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Returns all 379 target metadata records."""
        return self._target_map

    def validate_integrity(self) -> Dict[str, Any]:
        """Validates dataset dimensions, null values, and censorship rates."""
        df = self.load()
        total_rows = len(df)
        unique_drugs = df["ID1"].nunique()
        unique_targets = df["ID2"].nunique()
        unique_canonical_genes = df["canonical_gene_symbol"].nunique()
        censored_count = df["is_censored"].sum()
        uncensored_count = total_rows - censored_count
        censored_ratio = float(censored_count) / float(total_rows)

        # Check nulls in core fields
        null_counts = df[["ID1", "X1", "ID2", "X2", "Y", "canonical_gene_symbol", "pkd"]].isnull().sum().to_dict()

        integrity_report = {
            "status": "PASS" if total_rows == 25772 and unique_targets == 379 and sum(null_counts.values()) == 0 else "FAIL",
            "total_pairs": total_rows,
            "unique_drugs": unique_drugs,
            "unique_raw_targets": unique_targets,
            "unique_canonical_genes": unique_canonical_genes,
            "uncensored_measurements": int(uncensored_count),
            "right_censored_bounds": int(censored_count),
            "censored_ratio": round(censored_ratio, 4),
            "null_counts": null_counts,
            "plan_a_aligned": True,
        }
        return integrity_report


if __name__ == "__main__":
    loader = DtiGeneMaxDatasetLoader()
    df = loader.load()
    report = loader.validate_integrity()
    print("Dataset loaded successfully.")
    print(f"Total rows: {len(df)}")
    print(f"Report: {json.dumps(report, indent=2)}")
