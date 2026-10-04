"""Tests for external evidence validation, measurement re-derivation, and provenance gates."""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from evidence_validation import validate_source_evidence
from research_data import ResearchDataError, validate_records, REQUIRED
from research_utils import ROOT, sha256, write_json
from assay_records import SingleAssayObservation, evaluate_assay_for_amp, evaluate_assay_for_hemo


def make_record(tmp_path, **kwargs):
    raw_file = tmp_path / "raw_source.json"
    raw_data = kwargs.pop("raw_data", [{"id": "TEST_1", "seq": "GIGAVLKVLTTGLPALISWIKRKRQQ", "amp": 1, "hemo": 0}])
    write_json(raw_file, raw_data)
    h = sha256(raw_file)
    raw_path_str = str(raw_file).replace("\\", "/")
    
    base = {
        "record_id": "TEST_1",
        "seq": "GIGAVLKVLTTGLPALISWIKRKRQQ",
        "amp": 1.0,
        "hemo": 0.0,
        "source_dataset": "TestDB",
        "source_accession": "ACC_1",
        "source_url": "https://doi.org/10.1000/182",
        "evidence_reference": json.dumps([{"pmid": "12345678", "doi": "10.1000/182"}]),
        "label_basis": "measured",
        "assay_conditions": "standard",
        "modifications": "none",
        "evidence_type": "experimental",
        "is_synthetic": False,
        "source_role": "external",
        "raw_path": raw_path_str,
        "raw_sha256": h,
    }
    base.update(kwargs)
    return pd.DataFrame([base])


def test_handwritten_binary_labels_rejected(tmp_path):
    # Fixture 1: Hand-typed amp/hemo without raw assay measurements
    df = make_record(tmp_path, raw_data=[{"id": "TEST_1", "seq": "GIGAVLKVLTTGLPALISWIKRKRQQ", "amp": 1, "hemo": 0}])
    with pytest.raises(ResearchDataError) as exc_info:
        validate_records(df, verify_raw=True)
    assert exc_info.value.evidence_audit is not None
    assert exc_info.value.evidence_audit["status"] == "blocked"
    assert any("handwritten" in issue.lower() or "no raw assay" in issue.lower() 
               for f in exc_info.value.evidence_audit["failures"] for issue in f["issues"])


def test_raw_hash_correct_but_csv_label_altered_rejected(tmp_path):
    # Fixture 2: Raw assay specifies MIC=8 (amp=1), but CSV claims amp=0
    raw_entry = {
        "id": "TEST_1",
        "seq": "GIGAVLKVLTTGLPALISWIKRKRQQ",
        "assays": [
            {
                "endpoint": "amp",
                "target_organism_or_cell": "Escherichia coli ATCC 25922",
                "metric_name": "MIC",
                "raw_value": "8",
                "raw_unit": "ug/ml"
            }
        ]
    }
    df = make_record(tmp_path, raw_data=[raw_entry], amp=0.0, hemo=np.nan)
    with pytest.raises(ResearchDataError) as exc_info:
        validate_records(df, verify_raw=True)
    assert any("differs from re-derived" in issue for f in exc_info.value.evidence_audit["failures"] for issue in f["issues"])


def test_structured_assay_conditions_must_match_raw_observation(tmp_path):
    raw_entry = {
        "id": "TEST_1", "seq": "GIGAVLKVLTTGLPALISWIKRKRQQ", "doi": "10.1000/182",
        "assays": [{"endpoint": "amp", "target_organism_or_cell": "Escherichia coli NBRC 14237",
                    "metric_name": "MIC", "raw_value": "<6.2", "raw_unit": "uM",
                    "assay_method": "MIC assay", "medium": "not stated"}],
    }
    conditions = {"amp": [{"target": "Escherichia coli ATCC 25922", "raw_value": "<6.2",
                           "raw_unit": "uM", "method": "radial diffusion assay", "medium": "trypticase soy broth"}]}
    df = make_record(tmp_path, raw_data=[raw_entry], amp=1.0, hemo=np.nan,
                     assay_conditions=json.dumps(conditions))
    with pytest.raises(ResearchDataError) as exc_info:
        validate_records(df, verify_raw=True)
    assert any("differs from raw target" in issue
               for failure in exc_info.value.evidence_audit["failures"] for issue in failure["issues"])

    conditions["amp"][0].update(target="Escherichia coli NBRC 14237", method="radial diffusion assay")
    df.loc[0, "assay_conditions"] = json.dumps(conditions)
    with pytest.raises(ResearchDataError) as exc_info:
        validate_records(df, verify_raw=True)
    assert any("assay method" in issue for failure in exc_info.value.evidence_audit["failures"] for issue in failure["issues"])

    conditions["amp"][0].update(method="MIC assay", medium="not stated")
    df.loc[0, "assay_conditions"] = json.dumps(conditions)
    validate_records(df, verify_raw=True)


def test_benchmark_prefix_cannot_bypass_validation(tmp_path):
    # Fixture 3: Renaming source_dataset to Benchmark_* does not bypass re-derivation
    df = make_record(
        tmp_path,
        source_dataset="Benchmark_CustomDB",
        raw_data=[{"id": "TEST_1", "seq": "GIGAVLKVLTTGLPALISWIKRKRQQ", "amp": 1, "hemo": 0}]
    )
    with pytest.raises(ResearchDataError) as exc_info:
        validate_records(df, verify_raw=True)
    assert exc_info.value.evidence_audit["status"] == "blocked"


def test_protein_fragment_unannotated_negative_rejected(tmp_path):
    # Fixture 4: Protein fragment (e.g. Ubiquitin) assigned 0/0 without experimental assay evidence
    raw_entry = {
        "id": "TEST_1",
        "seq": "GIGAVLKVLTTGLPALISWIKRKRQQ",
        "description": "Natural protein fragment without antimicrobial assay",
        "assays": []  # No raw assays
    }
    df = make_record(tmp_path, raw_data=[raw_entry], amp=0.0, hemo=0.0)
    with pytest.raises(ResearchDataError) as exc_info:
        validate_records(df, verify_raw=True)
    assert exc_info.value.evidence_audit["status"] == "blocked"


def test_non_human_rbc_or_non_hc50_or_unknown_unit_yields_unknown(tmp_path):
    # Fixture 5: Rabbit RBC or percentage lysis or unknown unit cannot substantiate HC50 label
    obs_rabbit = SingleAssayObservation(
        endpoint="hemo",
        target_organism_or_cell="Rabbit erythrocytes",
        metric_name="HC50",
        raw_value="10",
        raw_unit="ug/ml"
    )
    evaluate_assay_for_hemo(obs_rabbit, "GIGAVLKVLTTGLPALISWIKRKRQQ")
    assert obs_rabbit.eligible is False
    assert obs_rabbit.ineligibility_reason == "incompatible_target"
    assert obs_rabbit.derived_label is None

    obs_mhc = SingleAssayObservation(
        endpoint="hemo",
        target_organism_or_cell="Human erythrocytes",
        metric_name="MHC",
        raw_value="10",
        raw_unit="ug/ml"
    )
    evaluate_assay_for_hemo(obs_mhc, "GIGAVLKVLTTGLPALISWIKRKRQQ")
    assert obs_mhc.eligible is False
    assert obs_mhc.ineligibility_reason == "incompatible_endpoint"
    assert obs_mhc.derived_label is None

    obs_unit = SingleAssayObservation(
        endpoint="amp",
        target_organism_or_cell="Escherichia coli",
        metric_name="MIC",
        raw_value="10",
        raw_unit="unknown_ppm"
    )
    evaluate_assay_for_amp(obs_unit, "GIGAVLKVLTTGLPALISWIKRKRQQ")
    assert obs_unit.eligible is False
    assert obs_unit.ineligibility_reason == "unsupported_unit"
    assert obs_unit.derived_label is None


def test_intermediate_range_or_conflicts_produce_no_label(tmp_path):
    # Fixture 6: MIC 16-64 ug/ml or HC50 > 100 ug/ml does not produce definitive binary label
    obs_mic = SingleAssayObservation(
        endpoint="amp",
        target_organism_or_cell="Escherichia coli",
        metric_name="MIC",
        raw_value="16 - 64",
        raw_unit="ug/ml"
    )
    evaluate_assay_for_amp(obs_mic, "GIGAVLKVLTTGLPALISWIKRKRQQ")
    assert obs_mic.eligible is True
    assert obs_mic.derived_label is None
    assert obs_mic.ineligibility_reason == "intermediate_range"

    obs_hc = SingleAssayObservation(
        endpoint="hemo",
        target_organism_or_cell="Human red blood cells",
        metric_name="HC50",
        raw_value="> 100",
        raw_unit="ug/ml"
    )
    evaluate_assay_for_hemo(obs_hc, "GIGAVLKVLTTGLPALISWIKRKRQQ")
    assert obs_hc.eligible is True
    assert obs_hc.derived_label is None
    assert obs_hc.ineligibility_reason == "intermediate_range"
