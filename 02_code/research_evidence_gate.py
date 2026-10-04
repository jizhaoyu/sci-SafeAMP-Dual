"""Fail closed on missing primary evidence; never manufacture a release decision."""
from pathlib import Path

import pandas as pd

from public_data import measurement_label
from research_utils import ROOT, read_json, sha256


def workspace_path(name: str) -> Path:
    path = (ROOT / name).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("Evidence path is outside the workspace")
    return path


def verify_manifest(directory: Path) -> dict:
    manifest = read_json(directory / "manifest.json")
    for name, expected in manifest.get("inputs", {}).items():
        if sha256(workspace_path(name)) != expected:
            raise ValueError(f"Primary evidence input changed: {name}")
    for name, expected in manifest.get("outputs", {}).items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory.resolve()) or sha256(path) != expected:
            raise ValueError(f"Primary evidence output changed: {name}")
    return manifest


def require_primary_release(protocol: dict, freeze_path: Path, entry_path: Path) -> dict:
    if not freeze_path.is_file():
        raise ValueError("Training blocked: mandatory protocol freeze is missing")
    if not all(protocol.get(k) for k in ("evidence_release_manifest", "evidence_release_manifest_sha256")):
        raise ValueError("Training blocked: frozen protocol does not bind a complete primary evidence release")
    freeze = read_json(freeze_path)
    protocol_path = workspace_path(f"03_experiments/protocols/{protocol['protocol_id']}.json")
    if freeze.get("protocol_file_sha256") != sha256(protocol_path):
        raise ValueError("Training blocked: protocol freeze checksum differs")
    if freeze.get("training_entry_sha256") != sha256(entry_path):
        raise ValueError("Training blocked: entry changed; a new prospective freeze is required")
    if freeze.get("model_training_started") is not False:
        raise ValueError("Training blocked: missing pre-training freeze declaration")

    path = workspace_path(protocol["evidence_release_manifest"])
    if sha256(path) != protocol["evidence_release_manifest_sha256"]:
        raise ValueError("Training blocked: evidence release checksum differs")
    release = verify_manifest(path.parent)
    if (release.get("status") != "passed_for_local_exploratory_training_protocol_review"
            or release.get("full_release_review_complete") is not True
            or release.get("cohort_manifest_sha256") != protocol["cohort_manifest_sha256"]):
        raise ValueError("Training blocked: primary evidence release is incomplete or for another cohort")

    molecules = pd.read_csv(workspace_path(protocol["molecules"]), keep_default_na=False)
    observations_path = protocol.get("observations")
    if observations_path is None:
        observations_path = str(Path(protocol["cohort_manifest"]).parent / "candidate_observations.csv")
    observations = pd.read_csv(workspace_path(observations_path), keep_default_na=False)
    approved = pd.read_csv(path.parent / "molecule_evidence_review.csv", keep_default_na=False)
    assays = pd.read_csv(path.parent / "assay_evidence_review.csv", keep_default_na=False)
    sources = pd.read_csv(path.parent / "source_review.csv", keep_default_na=False)
    if (not molecules.sample_id.is_unique or not approved.sample_id.is_unique
            or set(approved.sample_id) != set(molecules.sample_id)
            or len(assays) != len(observations)
            or release.get("molecules_evidence_approved") != len(molecules)
            or release.get("observations_evidence_approved") != len(observations)):
        raise ValueError("Training blocked: complete molecule/observation coverage is missing")
    if not all(table.decision.eq("passed_primary_evidence").all() for table in (approved, assays)):
        raise ValueError("Training blocked: an evidence row is withheld or rejected")
    if not set(approved.source_id).issubset(set(sources.source_id)):
        raise ValueError("Training blocked: original study review is missing")

    seq_for = molecules.set_index("sample_id").seq.to_dict()
    labels = molecules.set_index("sample_id").amp.astype(int).to_dict()
    for row in approved.itertuples(index=False):
        if row.sequence != seq_for[row.sample_id] or int(row.derived_label) != labels[row.sample_id]:
            raise ValueError("Training blocked: approved molecular identity or label differs")
    for table in (approved, assays):
        for row in table.itertuples(index=False):
            if (not row.primary_locations or not row.primary_file
                    or sha256(workspace_path(row.primary_file)) != row.primary_file_sha256):
                raise ValueError("Training blocked: original measurement file/locator is missing or changed")
    keys = ["sample_id", "record_id", "assay_index", "target", "raw_mic", "raw_unit"]
    def normalized_rows(table):
        return sorted(tuple(str(row[k]) for k in keys) for row in table.to_dict("records"))
    if normalized_rows(assays) != normalized_rows(observations):
        raise ValueError("Training blocked: original measured values, units or targets differ")
    for row in assays.to_dict("records"):
        label = measurement_label({"concentration": row["raw_mic"], "unit": {"name": row["raw_unit"]}},
                                  seq_for[row["sample_id"]], 32, 128)
        if label is None or label != int(row["derived_label"]) or label != labels[row["sample_id"]]:
            raise ValueError("Training blocked: primary measurement cannot reproduce its label")
    return release


def require_esm_provenance(protocol: dict) -> dict:
    spec = protocol["representations"]["esm2_only"]
    for path_key, hash_key in (("feature_meta_path", "feature_meta_sha256"),
                               ("extractor", "extractor_sha256")):
        if not spec.get(path_key) or sha256(workspace_path(spec[path_key])) != spec.get(hash_key):
            raise ValueError(f"Training blocked: ESM provenance differs: {path_key}")
    meta = read_json(workspace_path(spec["feature_meta_path"]))
    if meta.get("cohort_csv_sha256") != protocol["molecules_sha256"]:
        raise ValueError("Training blocked: ESM sequence inventory differs")
    if not meta.get("checkpoint_sha256") or not meta.get("environment") or not meta.get("sample_ids"):
        raise ValueError("Training blocked: ESM checkpoint/environment/order are not frozen")
    import importlib.metadata
    import torch
    checkpoint = Path(torch.hub.get_dir()) / "checkpoints" / f"{spec['model_name']}.pt"
    if not checkpoint.is_file() or sha256(checkpoint) != meta["checkpoint_sha256"]:
        raise ValueError("Training blocked: pretrained checkpoint is missing or changed")
    expected = {"torch": torch.__version__, "fair_esm": importlib.metadata.version("fair-esm")}
    if any(meta["environment"].get(k) != v for k, v in expected.items()):
        raise ValueError("Training blocked: ESM extraction environment differs")
    return meta
