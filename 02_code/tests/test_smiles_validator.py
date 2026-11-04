import pytest
import json
from pathlib import Path
from smiles_validator import validate_smiles


def test_smiles_validator_invalid_cases():
    invalid_cases = [
        "",
        "   ",
        "invalid_smiles",
        "CC=",
        "=CC",
        "CC()",
        "C(=)C",
        "CC.invalid_smiles",
        "CC.",
        ".CC",
        "CC..CC",
        "[Qq]C",
        "C(C)(C)(C)(C)C",
        "c1ccccc",  # unclosed ring
        "CC(C",     # unclosed paren
        "CC[C",     # unclosed bracket
        "CO(C)C",   # neutral oxygen valence exceeded (3 bonds > 2)
        "CFC",      # fluorine valence exceeded (2 bonds > 1)
        "CN(C)(C)C", # neutral nitrogen 4 single bonds
        "CN(C)(C)(C)C", # neutral nitrogen 5 single bonds / coordination 5 > 4
        "C11",      # self-loop ring closure
        "C1C1",     # duplicate bond / 2-cycle ring closure
        "[CH5]",    # explicit hydrogen overflow (5 H on carbon)
        "C=(C)C",   # bond symbol immediately preceding opening parenthesis
        "ccc",      # acyclic lowercase aromatic chain not in cycle
        "C=1CCCCC-1", # conflicting explicit ring closure bonds (= vs -)
        "C[N+2](C)(C)(C)(C)C", # [N+2] coordination/valence exceeded (6 bonds)
        "c1ccccc1cc2ccccc2",   # two rings connected by lowercase aromatic c
        "c1ccccc1ccc2ccccc2",  # two rings connected by 2 lowercase aromatic c's
        "c1ccccc1cccc2ccccc2", # two rings connected by 3 lowercase aromatic c's
    ]
    for case in invalid_cases:
        with pytest.raises(ValueError):
            validate_smiles(case)


def test_smiles_validator_valid_cases():
    valid_cases = [
        "CCO",
        "c1ccccc1",
        "C[C@@H](O)N",
        "c1cc[nH]c1",
        "C[O-]",
        "CC(=O)O",
        "C#N",
        "C1CC1",
        "CC.CC",
        "CCN(CC)CC",
        "C[N+](C)(C)C",  # quaternary ammonium cation (valence 4 allowed for [N+])
        "c1ccoc1",       # furan
        "c1ccsc1",       # thiophene
        "c1ncccc1",      # pyridine
        "C=1CCCCC=1",    # matching explicit double bond ring closure
        # Connected rings with valid aliphatic bridge(s)
        "c1ccccc1Cc2ccccc2",    # single C bridge
        "c1ccccc1CCc2ccccc2",   # two C bridge
        "c1ccccc1CCCc2ccccc2",  # three C bridge
        # Fused rings (稠环)
        "c1ccc2ccccc2c1",       # naphthalene
        "c1ccc2ncccc2c1",       # quinoline
        "c1cc2ccccc2[nH]1",     # indole
        # Spiro rings (螺环)
        "C1CCCC12CCCC2",        # spiro[4.4]nonane
        "C1CCC2(CC1)CCCCC2",    # spiro[5.5]undecane
        "c1ccc2c(c1)CC1(CCCC1)C2", # fused indane + spirocyclopentane
    ]
    for case in valid_cases:
        validate_smiles(case)


def test_smiles_validator_davis_drugs():
    davis_file = Path(__file__).resolve().parents[2] / "03_experiments/audits/dti_davis_field_review_20261006_v1/drugs.json"
    drugs = json.loads(davis_file.read_text(encoding="utf-8"))
    assert len(drugs) == 68
    for d in drugs.values():
        validate_smiles(d["smiles"])
