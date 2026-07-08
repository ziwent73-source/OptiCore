"""
AGF 玻璃库加载器
从 CDGM-ZEMAX AGF 文件读取玻璃折射率，含 fallback 机制。
"""

import os
import math
from typing import Dict, Optional
from .data_model import Material, GLASS_CATALOG


def load_agf(filepath: str) -> Dict[str, Material]:
    """
    解析 Zemax AGF 格式玻璃库文件。
    返回 {玻璃名: Material} 字典。
    解析失败返回空字典。
    """
    if not os.path.exists(filepath):
        return {}

    materials = {}
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith("NM "):
                    continue
                parts = line.split()
                if len(parts) < 6:
                    continue
                name = parts[1].strip('"')
                # AGF NM 行：NM <名> <公式> <MIL> <nd> <Vd> <nF-nC> ...
                # 不同版本的 AGF 格式略有差异，尝试多种解析方式
                try:
                    formula = int(parts[2])
                    # 尝试提取 n_d, n_F, n_C
                    n_d = None
                    n_F = None
                    n_C = None

                    # Zemax AGF 常见格式：NM name 0 nd Vd nC nF ...
                    # 位置：parts[3]=MIL 或 direct nd
                    # 尝试解析
                    vals = []
                    for p in parts[3:]:
                        try:
                            vals.append(float(p))
                        except ValueError:
                            continue

                    if len(vals) >= 3:
                        # 格式 1: nd, Vd, dn (nF-nC)
                        # 格式 2: nd, Vd, nC, nF
                        n_d = vals[0]
                        if len(vals) >= 4 and abs(vals[1]) > 10:
                            # vals[1] 是阿贝数 (>10)，vals[2], vals[3] 是 nC, nF
                            n_C = vals[2]
                            n_F = vals[3] if len(vals) > 3 else None
                        elif n_d > 1.0:
                            # 从阿贝数推算
                            Vd = vals[1]
                            if Vd > 10 and n_d > 1.0:
                                dn = (n_d - 1.0) / Vd
                                n_F = n_d + dn / 2.0
                                n_C = n_d - dn / 2.0
                    elif len(vals) >= 1:
                        n_d = vals[0]

                    if n_d is not None and n_d > 1.0:
                        n_F_val = n_F if n_F is not None else n_d + 0.006
                        n_C_val = n_C if n_C is not None else n_d - 0.006
                        materials[name] = Material(
                            name=name,
                            n_d=round(n_d, 8),
                            n_F=round(n_F_val, 8),
                            n_C=round(n_C_val, 8),
                        )
                except (ValueError, IndexError):
                    continue
    except Exception:
        pass

    return materials


def load_glass_catalog(lens) -> bool:
    """
    根据 lens.glass_library 加载玻璃库。
    优先级：
      1. 项目目录下的 AGF 文件
      2. 内置 GLASS_CATALOG
    成功返回 True。
    """
    agf_name = getattr(lens, "glass_library", "")
    if not agf_name:
        return True  # 使用内置库

    # 尝试加载
    search_paths = [
        agf_name,                                          # 绝对路径
        os.path.join(os.path.dirname(__file__), "..", agf_name),  # 项目根目录
    ]

    for path in search_paths:
        materials = load_agf(path)
        if materials:
            # 将 AGF 数据写入全局 GLASS_CATALOG
            for name, mat in materials.items():
                if name not in GLASS_CATALOG:
                    GLASS_CATALOG[name] = mat
            return True

    return False  # AGF 加载失败，回退到内置库


def get_refractive_index(glass_name: str, wavelength: str,
                          manual_overrides: Optional[Dict[str, Dict[str, float]]] = None) -> float:
    """
    获取指定玻璃和波长的折射率。
    manual_overrides: {玻璃名: {波长: n}} 手动输入覆盖
    """
    # 手动输入优先
    if manual_overrides and glass_name in manual_overrides:
        override = manual_overrides[glass_name]
        if wavelength in override:
            return override[wavelength]

    # AGF 或内置库
    if glass_name in GLASS_CATALOG:
        return GLASS_CATALOG[glass_name].get_n(wavelength)

    # Air 默认
    if glass_name == "Air":
        return 1.0

    raise KeyError(f"玻璃 '{glass_name}' 未找到。请检查 AGF 文件或手动输入折射率。")
