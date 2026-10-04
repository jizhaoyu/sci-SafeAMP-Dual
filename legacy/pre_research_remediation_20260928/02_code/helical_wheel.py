"""
helical_wheel.py
计算基于 Schiffer-Edmundson 100° 投影模型的 α-螺旋轮构象数据与 Eisenberg 疏水力矩。
为 SafeAMP-Dual 3.0 工作站提供高精度物理化学与几何投影支持。
"""

import os
import sys
import math
from typing import Dict, List, Tuple, Any
import numpy as np

# 确保能正确引用当前目录下的 feature_extractor 模块
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

from feature_extractor import clean_sequence, KYTE_DOOLITTLE, CHARGE_ESTIMATE


def get_residue_category(aa: str) -> Tuple[str, str]:
    """
    根据 Kyte-Doolittle 疏水性与电荷倾向返回氨基酸生信色彩分类:
    - basic: 碱性阳离子 (天蓝 #38bdf8)
    - acidic: 酸性阴离子 (玫红 #f43f5e)
    - hydrophobic: 强疏水 (橙黄 #f59e0b)
    - moderate: 中度疏水 (淡黄 #fbbf24)
    - polar: 极性中性 (草绿 #10b981)

    Returns:
        (category_name, hex_color)
    """
    charge = CHARGE_ESTIMATE.get(aa, 0.0)
    hydro = KYTE_DOOLITTLE.get(aa, 0.0)

    if charge > 0:
        return "basic", "#38bdf8"
    elif charge < 0:
        return "acidic", "#f43f5e"
    elif hydro >= 1.8:
        return "hydrophobic", "#f59e0b"
    elif hydro > 0:
        return "moderate", "#fbbf24"
    else:
        return "polar", "#10b981"


def compute_helical_wheel_data(seq: str, radius: float = 120.0) -> Dict[str, Any]:
    """
    计算基于 Schiffer-Edmundson 100 度投影模型的螺旋轮构象数据及 Eisenberg 两亲疏水力矩。

    Args:
        seq: 多肽单字母序列
        radius: 螺旋轮投影半径 (默认 120.0，中心坐标为 (160.0, 160.0))

    Returns:
        Dict 包含:
            - sequence: 清理后的大写序列
            - length: 序列长度
            - residues: 残基投影列表 (pos, aa, angle_deg, x, y, category, color, hydrophobicity, charge)
            - hydrophobic_moment: Eisenberg 疏水力矩模长 (μH)
            - moment_angle_deg: 疏水力矩指向角度 (0~360°, 12点钟为 0°, 顺时针)
            - hydrophobic_angle_span: 疏水面跨度角度
            - net_charge: pH 7.4 净电荷估计
            - mean_hydrophobicity: 平均 Kyte-Doolittle 疏水性
    """
    cleaned = clean_sequence(seq)
    L = len(cleaned)
    residues: List[Dict[str, Any]] = []

    sum_x = 0.0
    sum_y = 0.0

    hydro_angles = []

    for idx, aa in enumerate(cleaned):
        # Schiffer-Edmundson 投影：每个残基在圆周上顺时针步进 100°
        angle_deg = (idx * 100.0) % 360.0
        angle_rad = math.radians(angle_deg)

        # 极坐标转换为笛卡尔坐标 (以 (160.0, 160.0) 为圆心，12点钟方向为 0°)
        cx = 160.0 + radius * math.sin(angle_rad)
        cy = 160.0 - radius * math.cos(angle_rad)

        category, color = get_residue_category(aa)
        hydro = KYTE_DOOLITTLE.get(aa, 0.0)
        charge = CHARGE_ESTIMATE.get(aa, 0.0)

        # 归一化疏水性贡献向量 (KD 标度从 -4.5 到 4.5 归一化至 0.0 ~ 1.0)
        h_norm = (hydro + 4.5) / 9.0
        sum_x += h_norm * math.sin(angle_rad)
        sum_y += -h_norm * math.cos(angle_rad)

        if hydro > 0:
            hydro_angles.append(angle_deg)

        residues.append({
            "pos": idx + 1,
            "aa": aa,
            "angle_deg": round(angle_deg, 1),
            "x": round(cx, 1),
            "y": round(cy, 1),
            "category": category,
            "color_category": category,
            "color": color,
            "hydrophobicity": float(hydro),
            "charge": float(charge)
        })

    # Eisenberg 疏水力矩模长
    moment_mag = math.sqrt(sum_x ** 2 + sum_y ** 2) / (L + 1e-6)
    # 疏水力矩方向 (以 12点钟为 0°，顺时针 0~360°)
    moment_angle_deg = (math.degrees(math.atan2(sum_x, -sum_y)) + 360.0) % 360.0

    # 计算疏水面角度跨度 (Hydrophobic arc span)
    if len(hydro_angles) >= 2:
        # 计算所有疏水残基相对于力矩矢量的角偏离
        diffs = [abs((a - moment_angle_deg + 180.0) % 360.0 - 180.0) for a in hydro_angles]
        hydro_span = min(360.0, 2.0 * max(diffs))
    elif len(hydro_angles) == 1:
        hydro_span = 20.0
    else:
        hydro_span = 0.0

    net_charge = sum(CHARGE_ESTIMATE.get(aa, 0.0) for aa in cleaned)
    mean_hydro = float(np.mean([KYTE_DOOLITTLE.get(aa, 0.0) for aa in cleaned]))

    return {
        "sequence": cleaned,
        "length": L,
        "residues": residues,
        "hydrophobic_moment": round(moment_mag, 4),
        "moment_angle_deg": round(moment_angle_deg, 1),
        "hydrophobic_angle_span": round(hydro_span, 1),
        "net_charge": round(net_charge, 2),
        "mean_hydrophobicity": round(mean_hydro, 2)
    }
