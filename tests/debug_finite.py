"""验证有限物距(500mm)的计算也正确"""
import sys
sys.path.insert(0, ".")

from engine.lens_loader import load_lens_from_dict
from engine.aberration import compute_system
import math

# 有限物距 500mm，物高 26mm（textbook_ch4 原始设计）
DEMO_FIN = {
    "name": "教材第四章 双胶合物镜 - 有限物距500mm",
    "system_parameters": {
        "object_distance": 500.0,
        "entrance_pupil_radius": 10.0,
        "aperture_stop_index": 0,
        "max_field_height": 26.0,
    },
    "calculation_settings": {
        "field_mode": "object_height",
        "field_value": 26.0,
        "aperture_angle_deg": 5.0,
        "field_fractions": [0.7],
        "pupil_fractions": [0.7],
    },
    "surfaces": [
        {"radius": 62.5,   "thickness": 4.0,  "glass": "H-K9L", "diameter": 25.0},
        {"radius": -43.65, "thickness": 2.5,  "glass": "H-ZF2", "diameter": 25.0},
        {"radius": -124.35,"thickness": 96.0, "glass": "Air",   "diameter": 25.0},
    ],
    "glass_library": "CDGM-ZEMAX202111.AGF",
}

lens = load_lens_from_dict(DEMO_FIN)
lens.wavelengths = ["d", "F", "C"]
results = compute_system(lens)

# Zemax 参考值（有限物距 500mm，第三列）
REF_FIN = {
    "f_prime": 99.718291,
    "l_prime": 121.593774,
    "lF_prime": 121.6220946,
    "lC_prime": 121.6910446,
    "lH_prime": 2.886118,
    "lp_prime": -4.200427,
    "y07_prime": 4.51934287,
    "y_full_prime": 6.4562041,
    # 球差
    "spherical_aberration_0.7": -0.161809,
    "spherical_aberration_full": -0.276609,
    # 位置色差
    "axial_chromatic_0.7": 0.003620,
    "axial_chromatic_full": 0.085400,
    "axial_chromatic_0": -0.068950,
    # 场曲
    "xt_prime": -0.74808913,
    "xs_prime": -0.35080441,
    "delta_xts": -0.39728472,
    # 畸变 etc
    "meridional_coma_0.7_field_0.7_apt": 0.01503556,
    "meridional_coma_0.7_field_full_apt": 0.03272088,
    "meridional_coma_full_field_0.7_apt": 0.02143336,
    "meridional_coma_full_field_full_apt": 0.04665836,
    "absolute_distortion_0.7_field": -0.00017404,
    "absolute_distortion_full_field": -0.00050737,
    "relative_distortion_0.7_field": -0.00385091,
    "relative_distortion_full_field": -0.00785864,
    "lateral_chromatic_0.7_field": -0.00025808,
    "lateral_chromatic_full_field": -0.00036631,
}

print("=" * 80)
print("有限物距 500mm, 物高 26mm — 对比 Zemax 参考值")
print("=" * 80)
all_ok = True
for key in sorted(REF_FIN.keys()):
    val = results.get(key, "MISSING")
    ref = REF_FIN[key]
    if isinstance(val, (int, float)):
        err = val - ref
        err_pct = abs(err / ref) * 100 if abs(ref) > 1e-10 else 0
        flag = " !!!" if err_pct > 1.0 else ""
        if err_pct > 1.0:
            all_ok = False
        print(f"  {key:35s}: {val:14.8f}  ref={ref:14.8f}  err_pct={err_pct:9.4f}%{flag}")
    else:
        print(f"  {key:35s}: {val}")

if all_ok:
    print("\n*** 有限物距计算全部正确！ ***")
else:
    print("\n*** 有误差超1%的项，需排查 ***")
