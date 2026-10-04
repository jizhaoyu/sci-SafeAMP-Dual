"""Unit tests for DRAMP source importer and overlap auditing."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dramp_importer import (
    parse_dramp_hemolysis,
    extract_pmids_and_dois_from_dev,
)
from research_utils import ROOT


def test_parse_dramp_hemolysis_valid():
    text = "Human erythrocytes (50% Hemolysis=86 µM; 10% Hemolysis=6.0 µm) ; Sheep erythrocytes (3% Hemolysis=80 µM)"
    res = parse_dramp_hemolysis(text)
    assert res is not None
    val, unit, snippet = res
    assert val == '86'
    assert unit in ('µM', 'uM')


def test_parse_dramp_hemolysis_no_human():
    text = "Rabbit erythrocytes (50% Hemolysis=20 µM)"
    assert parse_dramp_hemolysis(text) is None


def test_parse_dramp_hemolysis_fixed_percent_only():
    text = "Human erythrocytes: Hemolysis 0% (100 μM)"
    # Has 0% hemolysis at 100 uM, but no 50% Hemolysis or HC50
    assert parse_dramp_hemolysis(text) is None


def test_extract_pmids_from_dev():
    dev_path = ROOT / '02_code/data/sources/dbaasp_v1/records.csv'
    pmids, dois = extract_pmids_and_dois_from_dev(dev_path)
    assert len(pmids) > 100
    assert '18586467' in pmids
