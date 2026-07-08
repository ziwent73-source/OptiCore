"""
RayTracer — 实际光线追迹（Snell 折射，全局坐标精确求解）

全局坐标系：z 轴沿光轴（向右为正），L 为光线高度。
第一面顶点在 z=0。

对每个面，直接从当前光线位置求与球面的交点，无需先传到顶点平面。
"""

import math
from typing import List, Optional
from .data_model import Lens, Ray, GLASS_CATALOG


def _get_n(glass_name: str, wavelength: str) -> float:
    if glass_name in GLASS_CATALOG:
        return GLASS_CATALOG[glass_name].get_n(wavelength)
    return 1.0


def trace_single_ray(
    lens: Lens,
    ray: Ray,
    object_distance: float = float("inf"),
) -> Optional[dict]:
    """
    追迹一条光线穿过全部光学面。

    参数:
        lens: 光学系统
        ray: 初始光线 (L, U) 在入瞳平面
        object_distance: 物距（inf = 无限远）

    返回:
        {"L_last", "U_last", "d_cross", "path": [...]} 或 None
    """
    wl = ray.wavelength

    # ── 初始状态 ──
    # 入瞳平面位置（在全局 z 坐标中，第一面顶点为 z=0）
    pupil_z = lens.entrance_pupil_position  # 通常 = 0 (入瞳在第一面)

    # 光线在入瞳平面上
    L_cur = ray.L
    U_cur = ray.U
    z_cur = pupil_z

    # 当前介质
    n_cur = _get_n("Air", wl)

    # 各面顶点在全局 z 坐标系中的位置
    vertex_z = 0.0  # 第一面顶点
    path = []

    for i, surface in enumerate(lens.surfaces):
        n_next = _get_n(surface.glass, wl)
        R = surface.radius

        # ═══════════════════════════════════════════
        # 求光线与当前球面的交点
        # 球面中心：(zc, yc) = (vertex_z + R, 0)
        # 球面方程：(z - zc)² + (L - 0)² = R²
        #
        # 光线：(z, L) = (z_cur + p·cosU, L_cur + p·sinU), p≥0 为传播距离
        # 代入：
        #   (z_cur + p·cosU - vertex_z - R)² + (L_cur + p·sinU)² = R²
        # 令 Δz = z_cur - vertex_z - R
        #   (Δz + p·cosU)² + (L_cur + p·sinU)² = R²
        #   Δz² + 2Δz·p·cosU + p²cos²U + L_cur² + 2L_cur·p·sinU + p²sin²U = R²
        #   p² + 2p(Δz·cosU + L_cur·sinU) + (Δz² + L_cur² - R²) = 0
        # ═══════════════════════════════════════════

        if math.isinf(R):
            # 平面：交点在光线与顶点平面的交点
            # 光线传播到 z = vertex_z
            dz = vertex_z - z_cur
            if abs(math.cos(U_cur)) > 1e-15:
                p = dz / math.cos(U_cur)
            else:
                p = 0.0
            if p < 0:
                p = 0.0  # 已经在平面后面？取 0

            # 交点
            z_hit = z_cur + p * math.cos(U_cur)
            L_hit = L_cur + p * math.sin(U_cur)

            # 平面折射（Snell 定律近似）
            sinU_old = math.sin(U_cur)
            sinU_new = n_cur * sinU_old / n_next
            if abs(sinU_new) >= 1.0:
                return None  # TIR
            U_new = math.asin(sinU_new)
            L_new = L_hit
        else:
            cosU = math.cos(U_cur)
            sinU = math.sin(U_cur)

            dz = z_cur - vertex_z - R

            A = 1.0
            B = 2.0 * (dz * cosU + L_cur * sinU)
            C = dz * dz + L_cur * L_cur - R * R

            disc = B * B - 4.0 * A * C
            if disc < 0:
                return None  # 无交点

            sqrt_disc = math.sqrt(disc)
            p1 = (-B - sqrt_disc) / (2.0 * A)
            p2 = (-B + sqrt_disc) / (2.0 * A)

            # 选择较小的正 p（光线向前传播）
            p = None
            for cp in sorted([p1, p2]):
                if cp > -1e-9:
                    p = cp
                    break
            if p is None:
                return None  # 无正向交点

            # 交点坐标
            z_hit = z_cur + p * cosU
            L_hit = L_cur + p * sinU

            # ── 表面法线（从交点指向球心） ──
            # 球心：(vertex_z + R, 0)，直接用向量差然后归一化
            cz = vertex_z + R
            nx = cz - z_hit    # 指向球心（未经 R 缩放）
            ny = -L_hit
            nm = math.sqrt(nx * nx + ny * ny)
            if nm < 1e-15:
                # 交点在球心（不可能），回退
                return None
            nx /= nm
            ny /= nm

            # ── 向量 Snell 折射（处理所有角度，包括 cosI < 0 的斜入射）──
            # 入射方向向量
            sx = math.cos(U_cur)
            sy = math.sin(U_cur)

            # cosI = ŝ · N̂（有符号），N̂ 指向入射介质
            cosI = sx * nx + sy * ny
            cosI = max(-1.0, min(1.0, cosI))

            # sin²I' = (n/n')² · (1 - cos²I)
            sin2_I = 1.0 - cosI * cosI
            sin2_Ip = (n_cur / n_next) * (n_cur / n_next) * sin2_I
            if sin2_Ip >= 1.0:
                return None  # 全内反射

            # cosI' 与 cosI 同号（折射光线在法线同侧）
            sign_cosI = 1.0 if cosI >= 0 else -1.0
            cosIp = sign_cosI * math.sqrt(1.0 - sin2_Ip)

            # Γ = n'·cosI' - n·cosI
            Gamma = n_next * cosIp - n_cur * cosI

            # 向量 Snell: n'·ŝ' = n·ŝ + Γ·N̂
            sp_x = (n_cur * sx + Gamma * nx) / n_next
            sp_y = (n_cur * sy + Gamma * ny) / n_next

            # 归一化（防止积累误差）
            sp_norm = math.sqrt(sp_x * sp_x + sp_y * sp_y)
            sp_x /= sp_norm
            sp_y /= sp_norm

            U_new = math.atan2(sp_y, sp_x)
            L_new = L_hit

        # ── 记录 ──
        path.append({
            "surface_index": i,
            "z_hit": z_hit,
            "L": L_new,
            "U": U_new,
            "n_before": n_cur,
            "n_after": n_next,
            "radius": R,
        })

        # ── 准备下一个面 ──
        z_cur = z_hit
        L_cur = L_new
        U_cur = U_new
        n_cur = n_next
        vertex_z += surface.thickness  # 下一个面顶点 z

    # ── 最终状态（最后一面出射后）──
    # 计算光线与光轴交点到最后一面的距离（沿 z 轴）
    if abs(math.tan(U_cur)) > 1e-15:
        # 从当前位置 z_cur 到光轴交点的 z 距离
        dz_to_axis = -L_cur / math.tan(U_cur)
        # 光轴交点的全局 z 坐标
        z_axis_cross = z_cur + dz_to_axis
        # 最后一面顶点的 z 坐标
        last_vertex_z = vertex_z - lens.surfaces[-1].thickness
        # 从最后一面顶点到光轴交点的距离
        d_cross_from_last = z_axis_cross - last_vertex_z
    else:
        d_cross_from_last = float("inf")

    return {
        "L_last": L_cur,
        "U_last": U_cur,
        "d_cross": d_cross_from_last,
        "wavelength": wl,
        "path": path,
        "L_at_image": None,
    }


def trace_with_image(
    lens: Lens, ray: Ray, image_distance: float,
    object_distance: float = float("inf"),
) -> Optional[dict]:
    """追迹光线，并计算在近轴像面上的落点高度"""
    result = trace_single_ray(lens, ray, object_distance)
    if result is None:
        return None

    L_last = result["L_last"]
    U_last = result["U_last"]

    # 从最后一面交点（非顶点）到像面的实际距离
    # 像面 z = 最后一面顶点 + image_distance
    last_vertex_z = sum(s.thickness for s in lens.surfaces[:-1])
    last_hit_z = result["path"][-1]["z_hit"] if result["path"] else last_vertex_z
    dz_to_image = last_vertex_z + image_distance - last_hit_z

    L_at_image = L_last + dz_to_image * math.tan(U_last)
    result["L_at_image"] = L_at_image
    result["image_distance"] = image_distance

    return result
