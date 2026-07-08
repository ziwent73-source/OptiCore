"""
OptiCore 数据结构定义
Lens（光学系统）, Surface（光学面）, Ray（光线）, Material（玻璃）
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Material:
    """玻璃材料 — 存储 d/F/C 三个波长的折射率"""
    name: str
    n_d: float   # 587.56 nm (氦黄线)
    n_F: float   # 486.13 nm (氢蓝线)
    n_C: float   # 656.27 nm (氢红线)

    def get_n(self, wavelength: str) -> float:
        """根据波长标识返回折射率"""
        return {"d": self.n_d, "F": self.n_F, "C": self.n_C}[wavelength]


# 内置玻璃库（来自教材常用材料）
GLASS_CATALOG: dict[str, Material] = {
    "H-K9L":  Material("H-K9L",  n_d=1.51680, n_F=1.52238, n_C=1.51433),
    "H-ZF2":  Material("H-ZF2",  n_d=1.67270, n_F=1.68753, n_C=1.66662),
    "H-ZK7":  Material("H-ZK7",  n_d=1.61300, n_F=1.61999, n_C=1.60949),
    "H-ZK14": Material("H-ZK14", n_d=1.60311, n_F=1.60966, n_C=1.59971),
    "H-LAK7": Material("H-LAK7", n_d=1.71300, n_F=1.72236, n_C=1.70886),
    "H-F4":   Material("H-F4",   n_d=1.62004, n_F=1.63210, n_C=1.61498),
    "H-ZF10": Material("H-ZF10", n_d=1.68893, n_F=1.70461, n_C=1.68193),
    "Air":    Material("Air",    n_d=1.00000, n_F=1.00000, n_C=1.00000),
}


@dataclass
class Surface:
    """单面光学面 — 球面折射面"""
    radius: float       # 曲率半径（mm），平面用 inf
    thickness: float    # 到下一面的距离（mm）
    glass: str          # 材料名称（对应 GLASS_CATALOG）
    diameter: float = 25.0  # 通光口径（mm）


@dataclass
class Ray:
    """光线 — 由 (L, U) 坐标定义"""
    L: float            # 光线高度（mm）
    U: float            # 光线方向角（弧度）
    wavelength: str     # "d", "F", "C"


@dataclass
class Lens:
    """共轴球面光学系统"""
    name: str = ""
    surfaces: List[Surface] = field(default_factory=list)
    wavelengths: List[str] = field(default_factory=lambda: ["d", "F", "C"])
    field_height: float = 18.0          # 视场参数（含义取决于 field_mode）
    entrance_pupil_radius: float = 10.0 # 入瞳半径（mm）
    entrance_pupil_position: float = 0.0  # 入瞳距第一面距离（mm），负值在左侧
    aperture_stop_index: int = 0        # 光阑所在面索引（0=第一面）
    object_distance: float = float("inf")  # 物距（mm），inf/0=无限远，负数/正数=有限距
    # ── 新增字段（v2.0）──
    max_field_height: float = 18.0      # 系统最大视场像高（mm）
    field_mode: str = "image_height"    # angle | object_height | image_height
    field_value: float = 18.0           # 用户输入的视场数值
    wavelengths_selected: List[str] = field(default_factory=lambda: ["d", "F", "C"])
    aperture_angle_deg: float = 5.0     # 孔径角（度）
    pupil_fractions: List[float] = field(default_factory=lambda: [0.0, 0.7, 1.0])  # 全量（已 merge）
    field_fractions: List[float] = field(default_factory=lambda: [0.0, 0.7, 1.0])  # 全量（已 merge）
    glass_library: str = ""             # AGF 玻璃库文件名
    # ── 向后兼容 ──
    finite_object_distance: float = 1000.0
    finite_field_height: float | None = None

    @property
    def num_surfaces(self) -> int:
        return len(self.surfaces)

    def get_finite_field_height(self) -> float:
        """有限物距时使用的 field_height"""
        return self.finite_field_height if self.finite_field_height is not None else self.field_height

    @property
    def is_infinite(self) -> bool:
        """物距是否为无限远"""
        return math.isinf(self.object_distance) or self.object_distance == 0.0
