"""
ParaxialCalculator — ABCD 矩阵近轴光学计算

输出 11 项近轴参数：
  f', l', lH', lp', y'₀, y'₀.₇, x_t', x_s', Δx'_ts, l'_F, l'_C

方法：近轴光线追迹（L-U 坐标）
  折射：n' u' = n u - h (n'-n)/R
  传播：h_new = h + d·u（小角度近似 tan u ≈ u）
"""

import math
from typing import Dict, Tuple
from .data_model import Lens, GLASS_CATALOG


def _get_n(glass_name: str, wavelength: str) -> float:
    if glass_name in GLASS_CATALOG:
        return GLASS_CATALOG[glass_name].get_n(wavelength)
    return 1.0


def _paraxial_trace(
    lens: Lens,
    L0: float,
    U0: float,
    wavelength: str,
) -> Tuple[float, float]:
    """
    追迹一条近轴光线穿过系统。

    参数:
        L0: 第一面上的初始高度
        U0: 初始角度
        wavelength: 波长标识

    返回:
        (L_last, U_last) — 最后一面出射后的高度和角度
    """
    L = L0
    U = U0

    for i, surface in enumerate(lens.surfaces):
        n_prev = _get_n("Air", wavelength) if i == 0 else _get_n(lens.surfaces[i - 1].glass, wavelength)
        n_cur = _get_n(surface.glass, wavelength)
        R = surface.radius

        # 折射
        if math.isinf(R):
            # 平面
            U_new = n_prev * U / n_cur
            L_new = L
        else:
            # 球面：n' u' = n u - L*(n'-n)/R
            nU_new = n_prev * U - L * (n_cur - n_prev) / R
            U_new = nU_new / n_cur
            L_new = L  # 面上的高度不变

        L = L_new
        U = U_new

        # 传播到下一面
        if i < len(lens.surfaces) - 1:
            d = surface.thickness
            L = L + d * U

    return (L, U)


def compute_paraxial(lens: Lens, object_distance: float = float("inf")) -> Dict:
    """
    计算全部 11 项近轴参数。
    """
    results = {}
    is_infinite = math.isinf(object_distance)

    # ── 焦距 f' ──
    # 追迹平行于光轴（U=0）的近轴光线，从入瞳高度 h 入射
    h = lens.entrance_pupil_radius
    _, U_out_d = _paraxial_trace(lens, L0=h, U0=0.0, wavelength="d")
    f_prime = -h / U_out_d if abs(U_out_d) > 1e-15 else float("inf")
    results["f_prime"] = f_prime

    # ── 各波长像方截距 l' ──
    # 无限远：追迹平行光（U₀=0）
    # 有限物距：追迹从轴上物点发出的光线（U₀ = atan(h/物距)）
    for wl_key, wl_name in [("d", "l_prime"), ("F", "lF_prime"), ("C", "lC_prime")]:
        if is_infinite:
            U0 = 0.0
        else:
            # paraxial 内部用 tanU≈U 近似，这里保持一致用 h/obj 而非 atan(h/obj)
            U0 = h / object_distance if abs(object_distance) > 1e-15 else 0.0
        L_last, U_last = _paraxial_trace(lens, L0=h, U0=U0, wavelength=wl_key)
        if abs(U_last) > 1e-15:
            l_p = -L_last / U_last
        else:
            l_p = float("inf")
        results[wl_name] = l_p

    l_prime = results["l_prime"]

    # ── 后主面位置 lH' ──
    # lH' 是镜头固有属性，始终从无限远平行光追迹计算
    L_inf, U_inf = _paraxial_trace(lens, L0=h, U0=0.0, wavelength="d")
    l_inf = -L_inf / U_inf if abs(U_inf) > 1e-15 else float("inf")
    results["lH_prime"] = f_prime - l_inf

    # ── 出瞳位置 lp'（光阑对其后方系统成像）──
    results["lp_prime"] = _exit_pupil_location(lens)

    # ── 近轴像高 ──
    results["y0_prime"] = 0.0  # 轴上视场，像高为 0

    # 辅助：追迹近轴主光线，获取该视场下的近轴像高（取绝对值）
    def _chief_image_height(y_field: float) -> float:
        """追迹近轴主光线（L0=0 过瞳孔中心），返回近轴像高（正值）"""
        if is_infinite:
            # 与 paraxial 内部 tanU≈U 近似一致，用比值而非 atan
            U_in = y_field / f_prime if abs(f_prime) > 1e-15 else 0.0
        else:
            # 主光线从物点经入瞳中心：用 -y/obj
            U_in = -y_field / object_distance if abs(object_distance) > 1e-15 else 0.0
        L_img, U_img = _paraxial_trace(lens, L0=0.0, U0=U_in, wavelength="d")
        if abs(U_img) > 1e-15:
            return abs(L_img + l_prime * U_img)  # 取绝对值，与 Zemax 参考一致
        return abs(L_img)

    if is_infinite:
        # 无限远：0.7 视场 = 0.7×视场角
        W_full = math.atan(lens.field_height / f_prime) if abs(f_prime) > 1e-15 else 0.0
        y_07 = f_prime * math.tan(0.7 * W_full)
        y_full = lens.field_height
    else:
        y_07 = 0.7 * lens.field_height
        y_full = lens.field_height
    results["y07_prime"] = _chief_image_height(y_07)
    results["y_full_prime"] = _chief_image_height(y_full)

    # ── 场曲 & 像散（Coddington 细光束追迹）──
    y_image = results.get("y_full_prime", lens.field_height)
    xt, xs = _coddington_field_curvature(lens, f_prime, y_image, object_distance)
    results["xt_prime"] = xt
    results["xs_prime"] = xs
    results["delta_xts"] = xt - xs

    return results


def _exit_pupil_location(lens: Lens) -> float:
    """出瞳位置：过光阑中心的光线在像方与光轴的交点"""
    stop_idx = lens.aperture_stop_index
    # 从光阑中心出发，小角度
    L0 = 0.0
    U0 = 0.05  # 小角度

    L = L0
    U = U0

    for i in range(stop_idx, len(lens.surfaces)):
        surface = lens.surfaces[i]
        n_prev = _get_n("Air", "d") if i == 0 else _get_n(lens.surfaces[i - 1].glass, "d")
        n_cur = _get_n(surface.glass, "d")
        R = surface.radius

        if math.isinf(R):
            U_new = n_prev * U / n_cur
            L_new = L
        else:
            nU_new = n_prev * U - L * (n_cur - n_prev) / R
            U_new = nU_new / n_cur
            L_new = L

        L = L_new
        U = U_new

        if i < len(lens.surfaces) - 1:
            L = L + surface.thickness * U

    if abs(U) > 1e-15:
        return -L / U
    return float("inf")


def _coddington_field_curvature(
    lens: Lens, f_prime: float, image_height: float,
    object_distance: float,
) -> Tuple[float, float]:
    """
    Coddington 细光束追迹计算场曲和像散。
    沿主光线逐面计算子午/弧矢焦点位置。
    """
    from .ray_tracer import trace_single_ray
    from .data_model import Ray

    is_inf = math.isinf(object_distance)

    # ── 主光线初始角（精确 atan2，与 ray_generator 一致）──
    if is_inf:
        U_chief = math.atan(image_height / f_prime) if abs(f_prime) > 1e-15 else 0.0
    else:
        obj_height = lens.get_finite_field_height() if hasattr(lens, 'get_finite_field_height') else lens.field_height
        pupil_z = lens.entrance_pupil_position
        U_chief = math.atan2(-obj_height, pupil_z + object_distance) if abs(object_distance) > 1e-15 else 0.0

    # 追迹主光线（精确 Snell 折射）
    chief_ray = Ray(L=0.0, U=U_chief, wavelength="d")
    chief_result = trace_single_ray(lens, chief_ray, object_distance)
    if chief_result is None or not chief_result["path"]:
        return 0.0, 0.0

    # ── Coddington 追迹：初始波前曲率 ──
    if is_inf:
        t = float("inf")
        s = float("inf")
    else:
        obj_height = lens.get_finite_field_height() if hasattr(lens, 'get_finite_field_height') else lens.field_height
        pupil_z = lens.entrance_pupil_position
        dz_obj = pupil_z + object_distance
        dy_obj = 0.0 - obj_height
        D_obj = math.sqrt(dz_obj * dz_obj + dy_obj * dy_obj)
        t = -D_obj   # 发散光束，负值
        s = -D_obj

    for i, pd in enumerate(chief_result["path"]):
        n_in = pd["n_before"]
        n_out = pd["n_after"]
        R = pd["radius"]
        L_hit = pd["L"]
        U_before = U_chief if i == 0 else chief_result["path"][i - 1]["U"]
        U_after = pd["U"]

        # 法线角度（从顶点指向球心）
        if abs(R) > 1e-10:
            alpha = math.atan2(-L_hit, R)
        else:
            alpha = 0.0

        # 入射角 / 折射角余弦（锐角，取绝对值）
        cosI_in = abs(math.cos(U_before - alpha))
        cosI_out = abs(math.cos(U_after - alpha))

        # Coddington Δ = n' cosI' − n cosI
        delta = n_out * cosI_out - n_in * cosI_in

        if math.isinf(R):
            t_prime = t
            s_prime = s
        else:
            term_t = n_in * cosI_in * cosI_in / t if (math.isfinite(t) and abs(t) > 1e-10) else 0.0
            term_s = n_in / s if (math.isfinite(s) and abs(s) > 1e-10) else 0.0

            denom_t = delta / R + term_t
            denom_s = delta / R + term_s

            t_prime = n_out * cosI_out * cosI_out / denom_t if abs(denom_t) > 1e-15 else float("inf")
            s_prime = n_out / denom_s if abs(denom_s) > 1e-15 else float("inf")

        # 转移到下一面（沿主光线的空间距离）
        if i < len(chief_result["path"]) - 1:
            next_pd = chief_result["path"][i + 1]
            dz = next_pd["z_hit"] - pd["z_hit"]
            dL = next_pd["L"] - L_hit
            D = math.sqrt(dz * dz + dL * dL)
        else:
            D = 0.0

        t = t_prime - D if math.isfinite(t_prime) else float("inf")
        s = s_prime - D if math.isfinite(s_prime) else float("inf")

    # ── 转换为相对于近轴像面的轴向距离 ──
    U_last = chief_result["U_last"]
    cosU_last = abs(math.cos(U_last))
    last_surf_z = chief_result["path"][-1]["z_hit"]
    last_vz = sum(s.thickness for s in lens.surfaces[:-1])

    # 近轴像面位置（与 compute_paraxial 保持一致：有限物距用斜率 h/obj）
    h = lens.entrance_pupil_radius
    if is_inf:
        U0 = 0.0
    else:
        U0 = h / object_distance if abs(object_distance) > 1e-15 else 0.0
    L_obj, U_obj = _paraxial_trace(lens, L0=h, U0=U0, wavelength="d")
    l_p = -L_obj / U_obj if abs(U_obj) > 1e-15 else float("inf")

    img_z = last_vz + l_p
    z_t = last_surf_z + t * cosU_last if math.isfinite(t) else float("inf")
    z_s = last_surf_z + s * cosU_last if math.isfinite(s) else float("inf")

    xt = z_t - img_z if math.isfinite(z_t) else 0.0
    xs = z_s - img_z if math.isfinite(z_s) else 0.0

    return xt, xs
