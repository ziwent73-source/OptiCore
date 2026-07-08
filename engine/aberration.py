"""
AberrationCalculator — 像差计算

基于光线追迹结果，计算全部 38 项数据（单个物距）。

分组：
  A. 近轴参数（11项）：f', l', lH', lp', y'₀, y'₀.₇, x_t', x_s', Δx'_ts, l'_F, l'_C
  B. 轴上像差（11项）：6实际像点 + 2球差 + 3位置色差
  C. 视场像差（16项）：4子午彗差 + 6实际像高 + 2绝对畸变 + 2相对畸变 + 2倍率色差
"""

import math
from typing import Dict, List, Optional
from .data_model import Lens
from .ray_generator import RayBundle, generate_rays
from .ray_tracer import trace_with_image
from .paraxial import compute_paraxial


def _find_trace(traces: List[dict], field: str, aperture: str, wavelength: str) -> Optional[dict]:
    """从追迹结果中查找"""
    for t in traces:
        if (t["field"] == field and t["aperture"] == aperture
                and t["wavelength"] == wavelength):
            return t
    return None


def compute_all_aberrations(lens: Lens, object_distance: float = float("inf")) -> Dict:
    """
    计算单个物距下的全部 38 项数据。

    返回字典，key 为参数名，value 为数值（或 None）。
    """
    # ── 1. 近轴计算 ──
    p = compute_paraxial(lens, object_distance)
    f_prime = p["f_prime"]
    l_prime = p["l_prime"]

    # ── 2. 生成光线（传入精确焦距，避免二次近轴计算）──
    bundles = generate_rays(lens, object_distance, focal_length=f_prime)

    # ── 3. 逐条追迹 ──
    traces: List[dict] = []
    for b in bundles:
        result = trace_with_image(lens, b.ray, l_prime, object_distance)
        if result is not None:
            traces.append({
                "field": b.field_label,
                "aperture": b.aperture_label,
                "wavelength": b.ray.wavelength,
                "field_height": b.field_height,
                "L_image": result["L_at_image"],
                "d_cross": result["d_cross"],
                "U_last": result["U_last"],
                "L_last": result["L_last"],
            })

    results = {}

    # ═══════════════════════════════════════════════
    # 通用辅助：从 pupil_fractions / field_fractions 动态生成迭代列表
    # ═══════════════════════════════════════════════
    _pup_fracs = getattr(lens, "pupil_fractions", [0.0, 0.7, 1.0])
    _fld_fracs = getattr(lens, "field_fractions", [0.0, 0.7, 1.0])
    is_inf = math.isinf(object_distance)

    # 非零孔径 → [(trace_key, result_label), ...]
    _apt_nonzero = []
    for frac in sorted(set(_pup_fracs), key=abs):
        if abs(frac) < 1e-9:
            continue
        lbl = "full" if abs(frac - 1.0) < 1e-3 else str(frac)
        _apt_nonzero.append((f"{lbl}_plus", lbl))

    # 所有孔径（含主光线）
    _apt_all = list(_apt_nonzero) + [("chief", "0")]

    # 孔径对 → [((plus_key, minus_key), result_suffix), ...]
    _apt_pairs = []
    for frac in sorted(set(_pup_fracs), key=abs):
        if abs(frac) < 1e-9:
            continue
        lbl = "full" if abs(frac - 1.0) < 1e-3 else str(frac)
        _apt_pairs.append(((f"{lbl}_plus", f"{lbl}_minus"), f"{lbl}_apt"))

    # 非零视场 → [(trace_key, result_label, field_height), ...]
    _fld_configs = []
    if is_inf:
        W_full = math.atan(lens.field_height / f_prime) if abs(f_prime) > 1e-15 else 0.0
        for frac in sorted(_fld_fracs):
            if abs(frac) < 1e-9:
                continue
            lbl = "full_field" if abs(frac - 1.0) < 1e-3 else f"{frac}_field"
            fh = f_prime * math.tan(frac * W_full)
            _fld_configs.append((lbl, lbl, fh))
    else:
        for frac in sorted(_fld_fracs):
            if abs(frac) < 1e-9:
                continue
            lbl = "full_field" if abs(frac - 1.0) < 1e-3 else f"{frac}_field"
            fh = frac * lens.field_height
            _fld_configs.append((lbl, lbl, fh))

    # 各视场理想像高（用于畸变）
    _ideal_heights = {}
    if is_inf:
        W_full = math.atan(lens.field_height / f_prime) if abs(f_prime) > 1e-15 else 0.0
        for frac in _fld_fracs:
            if abs(frac) < 1e-9:
                continue
            lbl = "full_field" if abs(frac - 1.0) < 1e-3 else f"{frac}_field"
            _ideal_heights[lbl] = f_prime * math.tan(frac * W_full)
    else:
        y_full = p.get("y_full_prime", lens.field_height)
        for frac in _fld_fracs:
            if abs(frac) < 1e-9:
                continue
            lbl = "full_field" if abs(frac - 1.0) < 1e-3 else f"{frac}_field"
            _ideal_heights[lbl] = frac * y_full  # 线性缩放近轴像高

    # ═══════════════════════════════════════════════
    # B. 轴上像差（动态孔径）
    # ═══════════════════════════════════════════════

    # ── B1. 实际像点位置 ──
    for apt_key, apt_label in _apt_nonzero:
        for wl in lens.wavelengths:
            t = _find_trace(traces, "on_axis", apt_key, wl)
            results[f"axial_image_{apt_label}_{wl}"] = t["d_cross"] if t else None

    # ── B2. 球差 ──
    for apt_key, apt_label in _apt_nonzero:
        t = _find_trace(traces, "on_axis", apt_key, "d")
        results[f"spherical_aberration_{apt_label}"] = (t["d_cross"] - l_prime) if t else None

    # ── B3. 位置色差 ──
    for apt_key, apt_label in _apt_all:
        t_F = _find_trace(traces, "on_axis", apt_key, "F")
        t_C = _find_trace(traces, "on_axis", apt_key, "C")
        if t_F and t_C and abs(t_F["d_cross"]) < 1e10 and abs(t_C["d_cross"]) < 1e10:
            results[f"axial_chromatic_{apt_label}"] = t_F["d_cross"] - t_C["d_cross"]
        else:
            results[f"axial_chromatic_{apt_label}"] = p.get("lF_prime", 0) - p.get("lC_prime", 0)

    # ═══════════════════════════════════════════════
    # C. 视场像差（动态视场 + 动态孔径）
    # ═══════════════════════════════════════════════

    # ── C1. 子午彗差 ──
    for field_key, field_name, fh in _fld_configs:
        for (apt_p, apt_m), apt_label in _apt_pairs:
            t_plus = _find_trace(traces, field_key, apt_p, "d")
            t_minus = _find_trace(traces, field_key, apt_m, "d")
            t_chief = _find_trace(traces, field_key, "chief", "d")
            if t_plus and t_minus and t_chief:
                coma = (t_plus["L_image"] + t_minus["L_image"]) / 2.0 - t_chief["L_image"]
                results[f"meridional_coma_{field_name}_{apt_label}"] = coma
            else:
                results[f"meridional_coma_{field_name}_{apt_label}"] = None

    # ── C2. 实际像高 ──
    for field_key, field_name, fh in _fld_configs:
        for wl in lens.wavelengths:
            t = _find_trace(traces, field_key, "chief", wl)
            results[f"image_height_{field_name}_{wl}"] = abs(t["L_image"]) if t else None

    # ── C3. 畸变 ──
    for field_key, field_name, fh in _fld_configs:
        t = _find_trace(traces, field_key, "chief", "d")
        ideal_h = _ideal_heights.get(field_name, fh)
        if t:
            actual_abs = abs(t["L_image"])
            ideal_abs = abs(ideal_h)
            abs_dist = actual_abs - ideal_abs
            results[f"absolute_distortion_{field_name}"] = abs_dist
            results[f"relative_distortion_{field_name}"] = (abs_dist / ideal_abs * 100.0) if ideal_abs > 1e-12 else 0.0
        else:
            results[f"absolute_distortion_{field_name}"] = None
            results[f"relative_distortion_{field_name}"] = None

    # ── C4. 倍率色差 ──
    for field_key, field_name, fh in _fld_configs:
        t_F = _find_trace(traces, field_key, "chief", "F")
        t_C = _find_trace(traces, field_key, "chief", "C")
        if t_F and t_C:
            results[f"lateral_chromatic_{field_name}"] = abs(t_F["L_image"]) - abs(t_C["L_image"])
        else:
            results[f"lateral_chromatic_{field_name}"] = None

    # ── 合并近轴参数 ──
    results.update(p)

    return results


def compute_system(lens: Lens) -> Dict:
    """
    计算单个物距下的像差数据（v2.0 — 单物距、动态参数）。

    处理 field_mode="angle" 的情况（视场角度 → 像高）。
    只计算 wavelengths_selected 中选中的波长。
    使用 pupil_fractions 确定孔径采样。
    """
    import math as _math
    from dataclasses import replace as _replace

    obj_dist = lens.object_distance
    is_inf = _math.isinf(obj_dist) or obj_dist == 0.0

    # ── 处理 field_mode="angle"：视场角度 → 像高 ──
    if lens.field_mode == "angle" and lens.field_height == 0.0:
        # 需要先算 f' 才能换算
        from .paraxial import compute_paraxial as _cp
        _p = _cp(lens, obj_dist)
        f_temp = _p.get("f_prime", 45.0)
        angle_rad = _math.radians(lens.field_value)
        fh = f_temp * _math.tan(angle_rad)
        lens = _replace(lens, field_height=fh)

    # 建立计算用的 lens（限制波长）
    wl_list = getattr(lens, "wavelengths_selected", lens.wavelengths)
    lens_calc = _replace(lens, wavelengths=list(wl_list))

    return compute_all_aberrations(lens_calc, object_distance=obj_dist)


def compute_76_items(lens: Lens) -> Dict:
    """
    兼容旧接口。v2.0 请使用 compute_system()。
    """
    inf = compute_all_aberrations(lens, object_distance=float("inf"))
    fin_obj_dist = getattr(lens, "finite_object_distance", 1000.0)
    fin_field_h = getattr(lens, "get_finite_field_height", lambda: lens.field_height)()
    from dataclasses import replace
    lens_fin = replace(lens, field_height=fin_field_h, object_distance=fin_obj_dist)
    fin = compute_all_aberrations(lens_fin, object_distance=fin_obj_dist)
    return {
        "infinite": inf, "finite": fin,
        "summary": {"infinite_count": len(inf), "finite_count": len(fin), "total": len(inf)+len(fin)},
    }
