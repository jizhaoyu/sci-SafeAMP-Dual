"""Unit tests for Helical Wheel mathematical projection and physicochemical calculations (P5B Milestone)."""
import os
import sys
import pytest

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_CODE_DIR = os.path.abspath(os.path.join(_CURRENT_DIR, ".."))
if _CODE_DIR not in sys.path:
    sys.path.insert(0, _CODE_DIR)

from helical_wheel import compute_helical_wheel_data, get_residue_category


def test_helical_wheel_melittin():
    """Test classic amphipathic peptide Melittin."""
    seq = "GIGAVLKVLTTGLPALISWIKRKRQQ"
    data = compute_helical_wheel_data(seq)
    
    assert data["sequence"] == seq
    assert data["length"] == 26
    assert len(data["residues"]) == 26
    
    # First residue angle and coordinates (0 deg, 12 o'clock)
    first_res = data["residues"][0]
    assert first_res["pos"] == 1
    assert first_res["aa"] == "G"
    assert first_res["angle_deg"] == 0.0
    assert first_res["x"] == 160.0
    assert first_res["y"] == 40.0  # 160 - 120
    
    # Second residue angle (100 deg)
    second_res = data["residues"][1]
    assert second_res["pos"] == 2
    assert second_res["aa"] == "I"
    assert second_res["angle_deg"] == 100.0
    
    # Successive angle steps
    assert data["residues"][2]["angle_deg"] == 200.0
    assert data["residues"][3]["angle_deg"] == 300.0
    assert data["residues"][4]["angle_deg"] == 40.0
    
    # Residue color categories
    k_res = [r for r in data["residues"] if r["aa"] == "K"][0]
    assert k_res["category"] == "basic"
    assert k_res["color"] == "#38bdf8"
    assert k_res["charge"] == 1.0
    
    i_res = [r for r in data["residues"] if r["aa"] == "I"][0]
    assert i_res["category"] == "hydrophobic"
    assert i_res["color"] == "#f59e0b"
    assert i_res["hydrophobicity"] == 4.5
    
    # Hydrophobic moment
    assert data["hydrophobic_moment"] > 0.1
    assert 0.0 <= data["moment_angle_deg"] < 360.0
    assert "hydrophobic_angle_span" in data
    
    # Net charge and mean hydrophobicity
    assert data["net_charge"] == pytest.approx(5.0, abs=0.1)
    assert "mean_hydrophobicity" in data
    assert isinstance(data["mean_hydrophobicity"], float)
    assert "disclaimer" in data


def test_helical_wheel_short():
    """Test short peptide ADAD."""
    seq = "ADAD"
    data = compute_helical_wheel_data(seq)
    
    assert data["length"] == 4
    assert len(data["residues"]) == 4
    
    # Verify categories
    assert data["residues"][0]["aa"] == "A"
    assert data["residues"][0]["category"] == "hydrophobic"
    assert data["residues"][1]["aa"] == "D"
    assert data["residues"][1]["category"] == "acidic"
    assert data["residues"][1]["color"] == "#f43f5e"
    
    assert data["hydrophobic_moment"] >= 0.0
    assert data["net_charge"] == pytest.approx(-2.0, abs=0.01)


def test_custom_radius():
    """Test custom projection radius."""
    seq = "AAAA"
    data = compute_helical_wheel_data(seq, radius=80.0)
    assert data["residues"][0]["x"] == 160.0
    assert data["residues"][0]["y"] == 80.0


def test_residue_category_scale():
    """Test residue category mappings."""
    assert get_residue_category("K") == ("basic", "#38bdf8")
    assert get_residue_category("R") == ("basic", "#38bdf8")
    assert get_residue_category("D") == ("acidic", "#f43f5e")
    assert get_residue_category("E") == ("acidic", "#f43f5e")
    assert get_residue_category("L") == ("hydrophobic", "#f59e0b")
    assert get_residue_category("A") == ("hydrophobic", "#f59e0b")
    assert get_residue_category("C") == ("hydrophobic", "#f59e0b")
    assert get_residue_category("S") == ("polar", "#10b981")


def test_sequence_cleaning():
    """Test sequence case and whitespace cleaning."""
    raw_seq = "  gigavlkvlttglpaliswikrkrqq \n\t"
    data = compute_helical_wheel_data(raw_seq)
    assert data["sequence"] == "GIGAVLKVLTTGLPALISWIKRKRQQ"
    assert data["length"] == 26


def test_invalid_short_sequence():
    """Test invalid sequences raise ValueError."""
    with pytest.raises(ValueError):
        compute_helical_wheel_data("A")
    with pytest.raises(ValueError):
        compute_helical_wheel_data("123")
    with pytest.raises(ValueError):
        compute_helical_wheel_data("GIXY")  # 'X' is invalid
