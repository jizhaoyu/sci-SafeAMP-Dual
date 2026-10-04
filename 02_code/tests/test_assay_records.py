"""Unit tests for assay_records.py according to Section 4.5 test scenarios."""
import sys
from pathlib import Path
import math
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assay_records import (
    parse_measurement_bounds,
    normalize_concentration_to_ug_ml,
    calculate_mw,
    SingleAssayObservation,
    StandardizedMoleculeRecord,
    process_molecule_record,
    evaluate_assay_for_amp,
    evaluate_assay_for_hemo,
)


def test_parse_measurement_bounds_operators_and_intervals():
    assert parse_measurement_bounds("16") == (16.0, 16.0, 'exact')
    assert parse_measurement_bounds("<= 32") == (0.0, 32.0, 'less_equal')
    assert parse_measurement_bounds("< 10") == (0.0, 10.0, 'less_equal')
    assert parse_measurement_bounds(">= 250") == (250.0, math.inf, 'greater_equal')
    assert parse_measurement_bounds("> 100") == (100.0, math.inf, 'greater_equal')
    assert parse_measurement_bounds("16 - 32") == (16.0, 32.0, 'interval')
    assert parse_measurement_bounds("1.5e1") == (15.0, 15.0, 'exact')
    assert parse_measurement_bounds("<= 2.5e-1") == (0.0, 0.25, 'less_equal')
    assert parse_measurement_bounds("1e2 - 2.5e2") == (100.0, 250.0, 'interval')
    assert parse_measurement_bounds("invalid text") is None
    assert parse_measurement_bounds("-5") is None
    assert parse_measurement_bounds("0") is None
    assert parse_measurement_bounds(None) is None


def test_mic_intermediate_range_no_label():
    obs = SingleAssayObservation(
        endpoint='amp',
        target_organism_or_cell='Escherichia coli ATCC 25922',
        metric_name='MIC',
        raw_value='64',  # between 32 and 128
        raw_unit='ug/ml'
    )
    evaluate_assay_for_amp(obs, "GIGAVLKVLTTGLPALISWIKRKRQQ")
    assert obs.eligible is True
    assert obs.derived_label is None
    assert obs.ineligibility_reason == 'intermediate_range'


def test_hemo_censored_greater_than_100_not_negative():
    obs = SingleAssayObservation(
        endpoint='hemo',
        target_organism_or_cell='Human erythrocytes',
        metric_name='HC50',
        raw_value='> 100',
        raw_unit='ug/ml'
    )
    evaluate_assay_for_hemo(obs, "GIGAVLKVLTTGLPALISWIKRKRQQ")
    assert obs.eligible is True
    # > 100 has low=100, high=inf. It does not satisfy low >= 250, so derived_label must be None!
    assert obs.derived_label is None
    assert obs.ineligibility_reason == 'intermediate_range'


def test_hemo_clear_negative_greater_equal_250():
    obs = SingleAssayObservation(
        endpoint='hemo',
        target_organism_or_cell='Human red blood cells',
        metric_name='HC50',
        raw_value='>= 250',
        raw_unit='ug/ml'
    )
    evaluate_assay_for_hemo(obs, "GIGAVLKVLTTGLPALISWIKRKRQQ")
    assert obs.eligible is True
    assert obs.derived_label == 0


def test_incompatible_target_rabbit_rbc():
    obs = SingleAssayObservation(
        endpoint='hemo',
        target_organism_or_cell='Rabbit erythrocytes',
        metric_name='HC50',
        raw_value='10',
        raw_unit='ug/ml'
    )
    evaluate_assay_for_hemo(obs, "GIGAVLKVLTTGLPALISWIKRKRQQ")
    assert obs.eligible is False
    assert obs.ineligibility_reason == 'incompatible_target'
    assert obs.derived_label is None


def test_incompatible_metric_hemolysis_percentage():
    obs = SingleAssayObservation(
        endpoint='hemo',
        target_organism_or_cell='Human erythrocytes',
        metric_name='Hemolysis % at 100 uM',
        raw_value='5%',
        raw_unit='%'
    )
    evaluate_assay_for_hemo(obs, "GIGAVLKVLTTGLPALISWIKRKRQQ")
    assert obs.eligible is False
    assert obs.ineligibility_reason == 'incompatible_endpoint'


def test_unit_micromolar_conversion_consistency():
    seq = "GIGAVLKVLTTGLPALISWIKRKRQQ"
    mw = calculate_mw(seq)  # approx 2846.5 Da
    # 10 uM in ug/ml = 10 * 2.8465 = 28.465 ug/ml <= 32 -> positive for AMP
    obs = SingleAssayObservation(
        endpoint='amp',
        target_organism_or_cell='Escherichia coli',
        metric_name='MIC',
        raw_value='10',
        raw_unit='uM'
    )
    evaluate_assay_for_amp(obs, seq)
    assert obs.eligible is True
    assert obs.derived_label == 1
    assert pytest.approx(obs.normalized_low_ug_ml, 0.1) == 28.46


def test_unsupported_unit_yields_unknown():
    obs = SingleAssayObservation(
        endpoint='amp',
        target_organism_or_cell='Escherichia coli',
        metric_name='MIC',
        raw_value='10',
        raw_unit='ppm'
    )
    evaluate_assay_for_amp(obs, "GIGAVLKVLTTGLPALISWIKRKRQQ")
    assert obs.eligible is False
    assert obs.ineligibility_reason == 'unsupported_unit'


def test_conflicting_measurements_yield_unknown_without_voting():
    obs1 = SingleAssayObservation(
        endpoint='amp',
        target_organism_or_cell='Escherichia coli',
        metric_name='MIC',
        raw_value='4',
        raw_unit='ug/ml'
    )  # label 1
    obs2 = SingleAssayObservation(
        endpoint='amp',
        target_organism_or_cell='Escherichia coli',
        metric_name='MIC',
        raw_value='256',
        raw_unit='ug/ml'
    )  # label 0

    record = StandardizedMoleculeRecord(
        record_id='TEST:1',
        sequence='GIGAVLKVLTTGLPALISWIKRKRQQ',
        source_dataset='TEST',
        source_accession='1',
        source_url='http://example.com/1',
        observations=[obs1, obs2]
    )

    row, reason = process_molecule_record(record)
    # Both endpoints are unknown (amp conflicting, hemo not measured), so should be excluded from supervised training
    assert row is None
    assert reason == 'missing_or_conflicting_endpoints'
    assert 'conflicting_measurements' in record.amp_unknown_reasons
