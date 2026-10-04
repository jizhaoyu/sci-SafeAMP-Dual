"""
test_helical_wheel.py
螺旋轮数学投影与物理化学算法模块单元测试
"""

import os
import sys
import pytest

# 确保能正确引用当前目录下的 helical_wheel 模块
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

from helical_wheel import compute_helical_wheel_data, get_residue_category


def test_helical_wheel_melittin():
    """测试典型两亲性抗菌肽蜂毒素 Melittin"""
    seq = "GIGAVLKVLTTGLPALISWIKRKRQQ"
    data = compute_helical_wheel_data(seq)
    
    assert data["sequence"] == seq
    assert data["length"] == 26
    assert len(data["residues"]) == 26
    
    # 验证第一个残基角度与坐标 (0 度, 12点钟方向)
    first_res = data["residues"][0]
    assert first_res["pos"] == 1
    assert first_res["aa"] == "G"
    assert first_res["angle_deg"] == 0.0
    assert first_res["x"] == 160.0
    assert first_res["y"] == 40.0  # 160 - 120
    
    # 验证第二个残基角度 (100 度)
    second_res = data["residues"][1]
    assert second_res["pos"] == 2
    assert second_res["aa"] == "I"
    assert second_res["angle_deg"] == 100.0
    
    # 验证第三个残基角度 (200 度)
    assert data["residues"][2]["angle_deg"] == 200.0
    # 验证第四个残基角度 (300 度)
    assert data["residues"][3]["angle_deg"] == 300.0
    # 验证第五个残基角度 ((4 * 100) % 360 = 40 度)
    assert data["residues"][4]["angle_deg"] == 40.0
    
    # 验证残基分类与色彩
    k_res = [r for r in data["residues"] if r["aa"] == "K"][0]
    assert k_res["category"] == "basic"
    assert k_res["color"] == "#38bdf8"
    assert k_res["charge"] == 1.0
    
    i_res = [r for r in data["residues"] if r["aa"] == "I"][0]
    assert i_res["category"] == "hydrophobic"
    assert i_res["color"] == "#f59e0b"
    assert i_res["hydrophobicity"] == 4.5
    
    # 验证两亲疏水力矩 (Melittin 为强两亲性螺旋，疏水力矩显著大于 0.1)
    assert data["hydrophobic_moment"] > 0.1
    assert 0.0 <= data["moment_angle_deg"] < 360.0
    assert "hydrophobic_angle_span" in data
    
    # 验证电荷与平均疏水性
    # Melittin 包含 K7, K21, R22, K23, R24，净电荷为 +5.0
    assert data["net_charge"] == pytest.approx(5.0, abs=0.1)
    assert "mean_hydrophobicity" in data
    assert isinstance(data["mean_hydrophobicity"], float)


def test_helical_wheel_short():
    """测试短肽 ADAD"""
    seq = "ADAD"
    data = compute_helical_wheel_data(seq)
    
    assert data["length"] == 4
    assert len(data["residues"]) == 4
    
    # 验证两性交替残基分类
    assert data["residues"][0]["aa"] == "A"
    assert data["residues"][0]["category"] == "hydrophobic"  # KD: 1.8 >= 1.8
    assert data["residues"][1]["aa"] == "D"
    assert data["residues"][1]["category"] == "acidic"       # KD: -3.5, charge: -1.0
    assert data["residues"][1]["color"] == "#f43f5e"
    
    assert data["hydrophobic_moment"] >= 0.0
    # ADAD 净电荷为 -2.0 (两个 D 残基)
    assert data["net_charge"] == pytest.approx(-2.0, abs=0.01)


def test_custom_radius():
    """测试自定义投影半径"""
    seq = "AAAA"
    data = compute_helical_wheel_data(seq, radius=80.0)
    # 第一个残基应该在 (160, 160 - 80) = (160, 80)
    assert data["residues"][0]["x"] == 160.0
    assert data["residues"][0]["y"] == 80.0


def test_residue_category_scale():
    """测试氨基酸生信色彩标度函数的各种类型"""
    assert get_residue_category("K") == ("basic", "#38bdf8")
    assert get_residue_category("R") == ("basic", "#38bdf8")
    assert get_residue_category("D") == ("acidic", "#f43f5e")
    assert get_residue_category("E") == ("acidic", "#f43f5e")
    assert get_residue_category("L") == ("hydrophobic", "#f59e0b")
    assert get_residue_category("A") == ("hydrophobic", "#f59e0b")
    assert get_residue_category("C") == ("hydrophobic", "#f59e0b")
    assert get_residue_category("S") == ("polar", "#10b981")


def test_sequence_cleaning():
    """测试序列大小写与空格清理"""
    raw_seq = "  gigavlkvlttglpaliswikrkrqq \n\t"
    data = compute_helical_wheel_data(raw_seq)
    assert data["sequence"] == "GIGAVLKVLTTGLPALISWIKRKRQQ"
    assert data["length"] == 26


def test_invalid_short_sequence():
    """测试少于 3 个残基的非法序列触发 ValueError"""
    with pytest.raises(ValueError):
        compute_helical_wheel_data("A")
    with pytest.raises(ValueError):
        compute_helical_wheel_data("123")
