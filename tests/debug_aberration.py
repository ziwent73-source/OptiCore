"""逐个对比像差计算值与Zemax参考值"""
import sys
sys.path.insert(0, ".")

from engine.lens_loader import load_lens_from_dict
from engine.glass_loader import load_glass_catalog
from engine.aberration import compute_system

# 教材第四章 双胶合物镜 — 无穷远，3°半视场角
DEMO = {
    "name": "教材第四章 双胶合物镜 - 无穷远",
    "system_parameters": {
        "object_distance": None,
        "entrance_pupil_radius": 10.0,
        "aperture_stop_index": 0,
        "max_field_height": 18.0,
    },
    "calculation_settings": {
        "field_mode": "angle",
        "field_value": 3.0,
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

lens = load_lens_from_dict(DEMO)
lens.wavelengths = ["d", "F", "C"]
print(f"field_height (computed from 3deg angle): {lens.field_height}")
print(f"field_fractions: {lens.field_fractions}")
print(f"pupil_fractions: {lens.pupil_fractions}")

results = compute_system(lens)

# ---- Zemax 参考值（无穷远）----
REF = {
    "f_prime": 99.718291,
    "l_prime": 96.832173,
    "lF_prime": 96.85257054,
    "lC_prime": 96.89348054,
    "lH_prime": 2.886118,
    "lp_prime": -4.200427,
    "y0_prime": 0.0,
    "y07_prime": 3.65650373,
    "y_full_prime": 5.22601418,
    "xt_prime": -0.48325753,
    "xs_prime": -0.22739103,
    "delta_xts": -0.25586650,
    # 轴上
    "axial_image_0.7_d": 96.80404054,
    "spherical_aberration_0.7": -0.028132,
    "spherical_aberration_full": -0.012602,  # 1.0 aperture
    "axial_chromatic_0.7": 0.012920,   # F-C at 0.7 apt
    "axial_chromatic_full": 0.074030,  # F-C at full apt
    "axial_chromatic_0": -0.040910,    # F-C at chief ray
    # 视场
    "image_height_0.7_field_d": 3.65635003,
    "image_height_0.7_field_F": 3.65607322,
    "image_height_0.7_field_C": 3.65651661,
    "image_height_full_field_d": 5.22556548,
    "image_height_full_field_F": 5.22517126,
    "image_height_full_field_C": 5.22580308,
    "absolute_distortion_0.7_field": -0.0001537,
    "absolute_distortion_full_field": -0.0004487,
    "relative_distortion_0.7_field": -0.00420354,
    "relative_distortion_full_field": -0.00858588,
    "lateral_chromatic_0.7_field": -0.00044339,
    "lateral_chromatic_full_field": -0.00063182,
    "meridional_coma_0.7_field_0.7_apt": 0.001827678,
    "meridional_coma_0.7_field_full_apt": 0.002172625,
    "meridional_coma_full_field_0.7_apt": 0.002668431,
    "meridional_coma_full_field_full_apt": 0.003214342,
}

print("\n" + "=" * 80)
print("A. 近轴参数对比")
print("=" * 80)
for key in ["f_prime", "l_prime", "lF_prime", "lC_prime", "lH_prime", "lp_prime",
            "y0_prime", "y07_prime", "y_full_prime", "xt_prime", "xs_prime", "delta_xts"]:
    val = results.get(key, "MISSING")
    ref = REF.get(key, None)
    if ref is not None and isinstance(val, (int, float)):
        err = val - ref
        err_pct = abs(err / ref) * 100 if abs(ref) > 1e-10 else 0
        flag = " *** LARGE ERROR" if err_pct > 1.0 else ""
        print(f"  {key:30s}: {val:14.8f}  ref={ref:14.8f}  err={err:12.8f}  {err_pct:8.4f}%{flag}")
    else:
        print(f"  {key:30s}: {val}")

print("\n" + "=" * 80)
print("B. 轴上像差对比")
print("=" * 80)
for key in sorted(k for k in results if k.startswith("axial_image_")):
    print(f"  {key}: {results[key]:.8f}")

for key in ["spherical_aberration_0.7", "spherical_aberration_full"]:
    val = results.get(key, "MISSING")
    ref = REF.get(key, None)
    if ref is not None and isinstance(val, (int, float)):
        err = val - ref
        err_pct = abs(err / ref) * 100 if abs(ref) > 1e-10 else 0
        flag = " *** LARGE ERROR" if err_pct > 1.0 else ""
        print(f"  {key:30s}: {val:14.8f}  ref={ref:14.8f}  err={err:12.8f}  {err_pct:8.4f}%{flag}")

for key in ["axial_chromatic_0.7", "axial_chromatic_full", "axial_chromatic_0"]:
    val = results.get(key, "MISSING")
    ref = REF.get(key, None)
    if ref is not None and isinstance(val, (int, float)):
        err = val - ref
        err_pct = abs(err / ref) * 100 if abs(ref) > 1e-10 else 0
        flag = " *** LARGE ERROR" if err_pct > 1.0 else ""
        print(f"  {key:30s}: {val:14.8f}  ref={ref:14.8f}  err={err:12.8f}  {err_pct:8.4f}%{flag}")

print("\n" + "=" * 80)
print("C. 视场像差对比")
print("=" * 80)
for key in sorted(k for k in results if k.startswith("image_height_")):
    print(f"  {key}: {results[key]:.8f}")

for key in ["absolute_distortion_0.7_field", "absolute_distortion_full_field",
            "relative_distortion_0.7_field", "relative_distortion_full_field"]:
    val = results.get(key, "MISSING")
    ref = REF.get(key, None)
    if ref is not None and isinstance(val, (int, float)):
        err = val - ref
        err_pct = abs(err / ref) * 100 if abs(ref) > 1e-10 else 0
        flag = " *** LARGE ERROR" if err_pct > 1.0 else ""
        print(f"  {key:30s}: {val:14.8f}  ref={ref:14.8f}  err={err:12.8f}  {err_pct:8.4f}%{flag}")

for key in ["lateral_chromatic_0.7_field", "lateral_chromatic_full_field"]:
    val = results.get(key, "MISSING")
    ref = REF.get(key, None)
    if ref is not None and isinstance(val, (int, float)):
        err = val - ref
        err_pct = abs(err / ref) * 100 if abs(ref) > 1e-10 else 0
        flag = " *** LARGE ERROR" if err_pct > 1.0 else ""
        print(f"  {key:30s}: {val:14.8f}  ref={ref:14.8f}  err={err:12.8f}  {err_pct:8.4f}%{flag}")

for key in ["meridional_coma_0.7_field_0.7_apt", "meridional_coma_0.7_field_full_apt",
            "meridional_coma_full_field_0.7_apt", "meridional_coma_full_field_full_apt"]:
    val = results.get(key, "MISSING")
    ref = REF.get(key, None)
    if ref is not None and isinstance(val, (int, float)):
        err = val - ref
        err_pct = abs(err / ref) * 100 if abs(ref) > 1e-10 else 0
        flag = " *** LARGE ERROR" if err_pct > 1.0 else ""
        print(f"  {key:30s}: {val:14.8f}  ref={ref:14.8f}  err={err:12.8f}  {err_pct:8.4f}%{flag}")

# Also print all result keys for debugging
print("\n" + "=" * 80)
print("All result keys:")
print("=" * 80)
for k in sorted(results.keys()):
    v = results[k]
    if isinstance(v, (int, float)):
        print(f"  {k}: {v:.10f}")
    else:
        print(f"  {k}: {v}")
