"""
LensLoader — 从 JSON 文件加载光学系统配置
支持 v2.0 新格式（system_parameters + calculation_settings）和旧格式。
"""

import json
import math
from pathlib import Path
from .data_model import Lens, Surface
from .glass_loader import load_glass_catalog


def _parse_object_distance(val) -> float:
    """解析物距：inf / null / 0 → float('inf')，数字 → 取绝对值"""
    if val is None:
        return float("inf")
    if isinstance(val, str) and val.strip().lower() == "inf":
        return float("inf")
    if isinstance(val, (int, float)):
        if val == 0 or math.isinf(val):
            return float("inf")
        return abs(float(val))  # 实物在左侧为负，取绝对值作为物距大小
    return float("inf")


def _merge_with_defaults(user_fracs: list[float]) -> list[float]:
    """视场/孔径分数始终包含 0 和 1.0，去重排序"""
    merged = set(user_fracs or [])
    merged.add(0.0)
    merged.add(1.0)
    return sorted(merged)


def load_lens_from_dict(data: dict) -> Lens:
    """
    从 Python 字典构建 Lens 对象。
    支持 v2.0 格式（system_parameters + calculation_settings）和旧格式。
    自动尝试加载 AGF 玻璃库。
    """
    # ── 解析 surfaces（两种格式共用）──
    surfaces = [
        Surface(
            radius=s.get("radius", float("inf")),
            thickness=s.get("thickness", 0.0),
            glass=s.get("glass", "Air"),
            diameter=s.get("diameter", 25.0),
        )
        for s in data["surfaces"]
    ]

    # ── 判断格式 ──
    if "system_parameters" in data:
        # === v2.0 新格式 ===
        sp = data["system_parameters"]
        cs = data.get("calculation_settings", {})

        obj_dist = _parse_object_distance(sp.get("object_distance"))
        entrance_pupil_radius = float(sp.get("entrance_pupil_radius", 10.0))
        aperture_stop_index = int(sp.get("aperture_stop_index", 0))
        max_field_height = float(sp.get("max_field_height", 18.0))

        wavelengths_selected = cs.get("wavelengths_selected", ["d", "F", "C"])
        field_mode = cs.get("field_mode", "image_height")
        field_value = float(cs.get("field_value", 18.0))
        aperture_angle_deg = float(cs.get("aperture_angle_deg", 5.0))

        # 视场分数：用户只写中间值，0 和 1.0 自动补全
        raw_field_fracs = [float(f) for f in cs.get("field_fractions", [0.7])]
        field_fractions = _merge_with_defaults(raw_field_fracs)

        # 孔径分数：用户只写中间值，0 和 1.0 自动补全
        raw_pupil_fracs = [float(f) for f in cs.get("pupil_fractions", [0.7])]
        pupil_fractions = _merge_with_defaults(raw_pupil_fracs)

        glass_library = data.get("glass_library", "")

        # 根据 field_mode 设置 field_height
        if field_mode == "angle":
            # 视场角（度）→ 需要 f' 才能换算像高，暂时存 0 后面再算
            field_height = 0.0
        else:
            # object_height 或 image_height：直接使用
            field_height = field_value

        return Lens(
            name=data.get("name", ""),
            surfaces=surfaces,
            wavelengths=wavelengths_selected,
            field_height=field_height,
            entrance_pupil_radius=entrance_pupil_radius,
            entrance_pupil_position=float(sp.get("entrance_pupil_position", 0.0)),
            aperture_stop_index=aperture_stop_index,
            object_distance=obj_dist,
            max_field_height=max_field_height,
            field_mode=field_mode,
            field_value=field_value,
            wavelengths_selected=wavelengths_selected,
            aperture_angle_deg=aperture_angle_deg,
            pupil_fractions=pupil_fractions,
            field_fractions=field_fractions,
            glass_library=glass_library,
            finite_object_distance=1000.0,
            finite_field_height=None,
        )
    else:
        # === 旧格式（向后兼容）===
        obj_dist = _parse_object_distance(data.get("object_distance"))
        wl = data.get("wavelengths", ["d", "F", "C"])
        fh = float(data.get("field_height", 18.0))
        return Lens(
            name=data.get("name", ""),
            surfaces=surfaces,
            wavelengths=wl,
            field_height=fh,
            entrance_pupil_radius=float(data.get("entrance_pupil_radius", 10.0)),
            entrance_pupil_position=float(data.get("entrance_pupil_position", 0.0)),
            aperture_stop_index=int(data.get("aperture_stop_index", 0)),
            object_distance=obj_dist,
            max_field_height=fh,
            field_mode="image_height",
            field_value=fh,
            wavelengths_selected=wl,
            aperture_angle_deg=5.0,
            pupil_fractions=[0.0, 0.7, 1.0],
            field_fractions=[0.0, 0.7, 1.0],
            glass_library=data.get("glass_library", ""),
            finite_object_distance=float(data.get("finite_object_distance", 1000.0)),
            finite_field_height=data.get("finite_field_height"),
        )


def load_lens(filepath: str) -> Lens:
    """从 JSON 文件加载 Lens 对象。支持新旧两种格式。自动加载 AGF 玻璃库。"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    lens = load_lens_from_dict(data)
    # 尝试加载 AGF 玻璃库
    if lens.glass_library:
        load_glass_catalog(lens)
    return lens
