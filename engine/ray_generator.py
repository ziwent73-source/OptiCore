"""
RayGenerator — 在入瞳平面生成计算所需的全部光线

⭐ 这是整个软件最关键、最容易出错的模块。

光线分类（每个视场均生成 d/F/C 三个波长版本）：

  轴上视场（0 视场）：
    - 主光线（0 孔径）
    - ±全孔径（±R）
    - ±0.7孔径（±0.7R）

  0.7 视场 & 全视场：
    - 主光线（0 孔径）
    - ±全孔径（±R）
    - ±0.7孔径（±0.7R）

无限远物距 → U 由视场角决定（所有同视场光线 U 相同）
有限物距   → U 由物距 + 孔径偏移共同决定
"""

import math
from typing import List, Optional
from .data_model import Lens, Ray


# --- 光线元数据（标记每条光线的用途） ---

class RayBundle:
    """带元数据的光线 — 方便像差计算时按条件筛选"""

    def __init__(
        self,
        ray: Ray,
        field_label: str,      # "on_axis" | "0.7_field" | "full_field"
        aperture_label: str,   # "chief" | "full_plus" | "full_minus" | "0.7_plus" | "0.7_minus"
        field_height: float,   # 实际物高（mm）
    ):
        self.ray = ray
        self.field_label = field_label
        self.aperture_label = aperture_label
        self.field_height = field_height

    def __repr__(self):
        return (
            f"RayBundle(field={self.field_label}, apt={self.aperture_label}, "
            f"λ={self.ray.wavelength}, L={self.ray.L:.4f}, U={self.ray.U:.6f})"
        )


def generate_rays(
    lens: Lens,
    object_distance: Optional[float] = None,
    focal_length: Optional[float] = None,
) -> List[RayBundle]:
    """
    在入瞳平面生成完整光线集合。

    参数:
        lens: 光学系统
        object_distance: 物距（None=无限远, 数值=有限物距mm）
        focal_length: 系统焦距（用于无限远视场角计算）。
                      传入 None 则回退到硬编码 45.0。
                      推荐由调用方先运行 compute_paraxial 获取精确 f' 后传入。

    返回:
        所有光线束（带元数据），每条光线有三个波长版本
    """
    if object_distance is None:
        object_distance = lens.object_distance

    is_infinite = math.isinf(object_distance)

    # ── 确定有效焦距 ──
    if focal_length is not None and abs(focal_length) > 1e-15:
        f_actual = focal_length
    else:
        # 回退：做一次快速近轴计算获取精确焦距
        from .paraxial import compute_paraxial as _cp
        _pre = _cp(lens, object_distance)
        f_actual = _pre.get("f_prime", 45.0)
        if not f_actual or abs(f_actual) < 1e-15:
            f_actual = 45.0

    # ── 视场高度：从 lens.field_fractions 动态生成 ──
    # field_fractions 已包含 0.0 和 1.0（lens_loader 自动补全）
    field_fracs = getattr(lens, "field_fractions", [0.0, 0.7, 1.0])
    if is_infinite:
        W_full = math.atan(lens.field_height / f_actual) if abs(f_actual) > 1e-15 else 0.0
        field_heights = {}
        for frac in field_fracs:
            if abs(frac) < 1e-9:
                field_heights["on_axis"] = 0.0
            elif abs(frac - 1.0) < 1e-9:
                field_heights["full_field"] = lens.field_height
            else:
                label = f"{frac}_field"
                W_frac = frac * W_full
                field_heights[label] = f_actual * math.tan(W_frac)
    else:
        field_heights = {}
        for frac in field_fracs:
            if abs(frac) < 1e-9:
                field_heights["on_axis"] = 0.0
            elif abs(frac - 1.0) < 1e-9:
                field_heights["full_field"] = lens.field_height
            else:
                label = f"{frac}_field"
                field_heights[label] = frac * lens.field_height

    # 孔径采样（从 lens.pupil_fractions 动态生成）
    # 1.0 → "full", 其他 → "X.X" （保持向后兼容）
    pup_fracs = getattr(lens, "pupil_fractions", [0.0, 0.7, 1.0])
    aperture_samples: dict[str, float] = {}
    for frac in sorted(set(pup_fracs), key=abs):
        if abs(frac) < 1e-9:
            aperture_samples["chief"] = 0.0
        else:
            label = "full" if abs(frac - 1.0) < 0.001 else str(frac)
            aperture_samples[f"{label}_plus"] = +abs(frac)
            aperture_samples[f"{label}_minus"] = -abs(frac)

    bundles: List[RayBundle] = []

    for field_label, y_field in field_heights.items():
        for apt_label, apt_fraction in aperture_samples.items():
            # --- 计算入瞳平面上的 (L, U) ---
            # L：光线在入瞳平面的高度
            L_at_pupil = apt_fraction * lens.entrance_pupil_radius

            if is_infinite:
                # 无限远物距：同视场所有光线平行入射
                # 轴上 U=0，视场角 ω = atan(y / f')（精确计算）
                U = math.atan(y_field / f_actual) if y_field != 0 else 0.0
            else:
                # 有限物距：先在入瞳上取高度，再从物点算 U 角
                # 光线从物点 (z=-obj_dist, y=y_field) 到入瞳点 (z=pupil_z, y=L_at_pupil)
                pupil_z = lens.entrance_pupil_position
                dz = pupil_z + object_distance       # pupil_z - (-obj_dist)
                dy = L_at_pupil - y_field            # 入瞳高度 - 物高
                U = math.atan2(dy, dz)

            # 入瞳位置偏移（如入瞳不在第一面）
            # 这里 L 是入瞳平面上的高度，传到第一面时需加上 U * d
            # 下面暂简化为入瞳与第一面重合（常见情况）

            # 在每个波长下生成光线
            for wl in lens.wavelengths:
                ray = Ray(L=L_at_pupil, U=U, wavelength=wl)
                bundles.append(RayBundle(
                    ray=ray,
                    field_label=field_label,
                    aperture_label=apt_label,
                    field_height=y_field,
                ))

    return bundles


def get_ray_count_summary(bundles: List[RayBundle]) -> dict:
    """统计光线数量"""
    fields = {}
    for b in bundles:
        key = (b.field_label, b.ray.wavelength)
        fields.setdefault(key, 0)
        fields[key] += 1

    total = len(bundles)
    by_wl = {}
    for b in bundles:
        by_wl[b.ray.wavelength] = by_wl.get(b.ray.wavelength, 0) + 1

    return {
        "total_rays": total,
        "by_wavelength": by_wl,
        "fields": len(set(b.field_label for b in bundles)),
        "apertures_per_field": len(set(b.aperture_label for b in bundles)),
    }
