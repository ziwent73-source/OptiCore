"""用用户当前的textbook_ch4.json配置跑，看误差来源"""
import sys
sys.path.insert(0, ".")

from engine.lens_loader import load_lens_from_dict
from engine.aberration import compute_system
import math
import json

# 直接读取用户当前的JSON
with open("test_cases/textbook_ch4.json", "r", encoding="utf-8") as f:
    data = json.load(f)

lens = load_lens_from_dict(data)
lens.wavelengths = ["d", "F", "C"]

# 检查实际使用的参数
print("=== 当前配置 ===")
print(f"object_distance: {lens.object_distance} (inf={math.isinf(lens.object_distance)})")
print(f"field_mode: {lens.field_mode}")
print(f"field_value: {lens.field_value}")
print(f"field_height (from loader): {lens.field_height}")
print(f"max_field_height: {lens.max_field_height}")

results = compute_system(lens)

print(f"\nf' = {results['f_prime']:.8f}")
print(f"W_full = atan(field_height/f') = {math.degrees(math.atan(lens.field_height/results['f_prime'])):.4f} deg")
print(f"  (应为 3.0 deg)")

# Zemax 参考值
REF = {
    "y07_prime": 3.65650373,
    "y_full_prime": 5.22601418,
    "xt_prime": -0.48325753,
    "xs_prime": -0.22739103,
    "delta_xts": -0.25586650,
    "spherical_aberration_0.7": -0.028132,
    "spherical_aberration_full": -0.012602,
    "axial_chromatic_0.7": 0.012920,
    "axial_chromatic_full": 0.074030,
    "axial_chromatic_0": -0.040910,
    "meridional_coma_0.7_field_0.7_apt": 0.001827678,
    "meridional_coma_0.7_field_full_apt": 0.002172625,
    "meridional_coma_full_field_0.7_apt": 0.002668431,
    "meridional_coma_full_field_full_apt": 0.003214342,
    "absolute_distortion_0.7_field": -0.0001537,
    "absolute_distortion_full_field": -0.0004487,
    "relative_distortion_0.7_field": -0.00420354,
    "relative_distortion_full_field": -0.00858588,
    "lateral_chromatic_0.7_field": -0.00044339,
    "lateral_chromatic_full_field": -0.00063182,
}

print("\n=== 用当前(错误)配置的计算值 vs Zemax参考值 ===")
for key in sorted(REF.keys()):
    val = results.get(key, "MISSING")
    ref = REF[key]
    if isinstance(val, (int, float)):
        err = val - ref
        err_pct = abs(err / ref) * 100 if abs(ref) > 1e-10 else 0
        flag = " !!!" if err_pct > 1.0 else ""
        print(f"  {key:35s}: {val:14.8f}  ref={ref:14.8f}  err_pct={err_pct:9.4f}%{flag}")

# 也看看实际像高对比
print("\n=== 实际像高 ===")
for key in sorted(k for k in results if k.startswith("image_height_")):
    print(f"  {key}: {results[key]:.8f}")
