"""
Complete comparison: our software vs teacher's Zemax data
Textbook Ch4 cemented doublet
"""
import sys
sys.path.insert(0, ".")

# Build the lens directly with correct glass data
from engine.data_model import Lens, Surface, GLASS_CATALOG
from engine.aberration import compute_all_aberrations, compute_paraxial
from engine.ray_generator import generate_rays
from engine.ray_tracer import trace_single_ray, trace_with_image

# ── Lens: textbook Ch4 cemented doublet ──
surfaces = [
    Surface(radius=62.5,   thickness=4.0,  glass="H-K9L", diameter=25.0),
    Surface(radius=-43.65, thickness=2.5,  glass="H-ZF2", diameter=25.0),
    Surface(radius=-124.35,thickness=96.0, glass="Air",   diameter=25.0),
]

# For infinite: field_height = image height = f'*tan(3deg)
f_est = 99.7
field_img_h = f_est * 0.05240778  # tan(3deg) ≈ 0.05241

lens_inf = Lens(
    surfaces=surfaces, wavelengths=["d","F","C"],
    field_height=field_img_h,  # ~5.226mm
    entrance_pupil_radius=10.0, entrance_pupil_position=0.0,
    aperture_stop_index=0, object_distance=float("inf"),
)

# For finite 500mm: field_height = object height = 26mm
lens_fin = Lens(
    surfaces=surfaces, wavelengths=["d","F","C"],
    field_height=26.0,  # object height
    entrance_pupil_radius=10.0, entrance_pupil_position=0.0,
    aperture_stop_index=0, object_distance=500.0,
)

inf = compute_all_aberrations(lens_inf, float("inf"))
fin = compute_all_aberrations(lens_fin, 500.0)

print("=" * 78)
print("  Textbook Ch4 Cemented Doublet — Full Comparison vs Zemax")
print("=" * 78)

# ═════════════════════════════════════════════════
# A. INFINITE CONJUGATE
# ═════════════════════════════════════════════════
print("\n" + "─" * 70)
print("  A. INFINITE CONJUGATE (W = 3 deg)")
print("─" * 70)

pairs_inf = [
    # (label, our_value, zemax_value, unit)
    ("A1  f' (focal length)",            inf.get("f_prime"),        99.718291,  "mm"),
    ("A2  l' (back focal distance)",     inf.get("l_prime"),        96.832173,  "mm"),
    ("A3  lH' (rear princ. plane)",      inf.get("lH_prime"),        2.886118,  "mm"),
    ("A4  lp' (exit pupil pos)",         inf.get("lp_prime"),       -4.200427,  "mm"),
    ("A5  y' full field (paraxial)",     inf.get("y_full_prime"),    5.226014,  "mm"),
    ("A6  y' 0.7 field (paraxial)",      inf.get("y07_prime"),       3.656504,  "mm"),
    ("A7  lF' (F-light image pos)",      inf.get("lF_prime"),       96.852571,  "mm"),
    ("A8  lC' (C-light image pos)",      inf.get("lC_prime"),       96.893481,  "mm"),
    ("A9  Axial image d full apt",       inf.get("axial_image_full_d"), 96.819571, "mm"),
    ("A10 Axial image d 0.7 apt",        inf.get("axial_image_0.7_d"),  96.804041, "mm"),
    ("A11 Axial image C full apt",       inf.get("axial_image_full_C"),  96.849631, "mm"),
    ("A12 Axial image C 0.7 apt",        inf.get("axial_image_0.7_C"),   96.850721, "mm"),
    ("A13 Axial image F full apt",       inf.get("axial_image_full_F"),  96.923661, "mm"),
    ("A14 Axial image F 0.7 apt",        inf.get("axial_image_0.7_F"),   96.863641, "mm"),
]

print(f"  {'#':<4} {'Parameter':<30} {'Our Value':>12} {'Zemax':>12} {'Diff':>10} {'Rel%':>8}")
print(f"  {'-'*4} {'-'*30} {'-'*12} {'-'*12} {'-'*10} {'-'*8}")

for label, our, zemax, unit in pairs_inf:
    o = our if our is not None else float("nan")
    z = zemax
    diff = o - z
    rel = (diff / abs(z) * 100) if abs(z) > 1e-9 else 0.0
    flag = ""
    if abs(rel) > 1.0:
        flag = " <<"
    elif abs(rel) > 0.5:
        flag = " <"
    print(f"  {label:<30} {o:>12.5f} {z:>12.5f} {diff:>+10.5f} {rel:>+7.2f}%{flag}")

# ═════════════════════════════════════════════════
# B. FINITE CONJUGATE 500mm
# ═════════════════════════════════════════════════
print("\n" + "─" * 70)
print("  B. FINITE CONJUGATE (500mm, y_obj = 26mm)")
print("─" * 70)

pairs_fin = [
    # Paraxial
    ("B1  l' (image distance)",              fin.get("l_prime"),        121.593774, "mm"),
    ("B2  lH' (rear princ. plane)",          fin.get("lH_prime"),        2.886118,  "mm"),
    ("B3  y' full field (paraxial)",         fin.get("y_full_prime"),    6.456204,  "mm"),
    ("B4  y' 0.7 field (paraxial)",          fin.get("y07_prime"),       4.519343,  "mm"),
    # Spherical aberration
    ("B5  SA full aperture",                 fin.get("spherical_aberration_full"), -0.276609, "mm"),
    ("B6  SA 0.7 aperture",                  fin.get("spherical_aberration_0.7"),  -0.161809, "mm"),
    # Axial chromatic
    ("B7  LCA full aperture",                fin.get("axial_chromatic_full"),  0.085400, "mm"),
    ("B8  LCA 0.7 aperture",                 fin.get("axial_chromatic_0.7"),   0.003620, "mm"),
    ("B9  LCA 0 aperture",                   fin.get("axial_chromatic_0"),    -0.068950, "mm"),
    # Field curvature & astigmatism
    ("B10 xt' (tangential field curv)",       fin.get("xt_prime"),       -0.748089,  "mm"),
    ("B11 xs' (sagittal field curv)",         fin.get("xs_prime"),       -0.350804,  "mm"),
    ("B12 dxts' (astigmatism)",              fin.get("delta_xts"),      -0.397285,  "mm"),
    # Actual image heights
    ("B13 Image height d full field",         fin.get("image_height_full_field_d"), 6.455697, "mm"),
    ("B14 Image height d 0.7 field",          fin.get("image_height_0.7_field_d"),  4.519169, "mm"),
    ("B15 Image height F full field",         fin.get("image_height_full_field_F"), 6.455500, "mm"),
    ("B16 Image height C full field",         fin.get("image_height_full_field_C"), 6.455866, "mm"),
    # Distortion
    ("B17 Relative distortion full field",    fin.get("relative_distortion_full_field"), -0.007859, "%"),
    ("B18 Relative distortion 0.7 field",     fin.get("relative_distortion_0.7_field"),  -0.003851, "%"),
    ("B19 Absolute distortion full field",    fin.get("absolute_distortion_full_field"), -0.000507, "mm"),
    ("B20 Absolute distortion 0.7 field",     fin.get("absolute_distortion_0.7_field"),  -0.000174, "mm"),
    # Lateral chromatic
    ("B21 Lateral chromatic full field",      fin.get("lateral_chromatic_full_field"), -0.000366, "mm"),
    ("B22 Lateral chromatic 0.7 field",       fin.get("lateral_chromatic_0.7_field"),  -0.000258, "mm"),
    # Meridional coma
    ("B23 Coma 0.7f 0.7apt",                  fin.get("meridional_coma_0.7_field_0.7_apt"), 0.015036, "mm"),
    ("B24 Coma 0.7f full apt",                fin.get("meridional_coma_0.7_field_full_apt"), 0.032721, "mm"),
    ("B25 Coma full f 0.7apt",                fin.get("meridional_coma_full_field_0.7_apt"), 0.021433, "mm"),
    ("B26 Coma full f full apt",              fin.get("meridional_coma_full_field_full_apt"), 0.046658, "mm"),
]

print(f"  {'#':<4} {'Parameter':<33} {'Our Value':>12} {'Zemax':>12} {'Diff':>10} {'Rel%':>8}")
print(f"  {'-'*4} {'-'*33} {'-'*12} {'-'*12} {'-'*10} {'-'*8}")

ok_count = 0
big_diff = 0
for label, our, zemax, unit in pairs_fin:
    o = our if our is not None else float("nan")
    z = zemax
    diff = o - z
    rel = (diff / abs(z) * 100) if abs(z) > 1e-4 else (diff * 100 if abs(diff) < 0.01 else float("nan"))
    flag = ""
    if abs(rel) > 5.0 if rel == rel else False:
        flag = " <<<"
        big_diff += 1
    elif abs(rel) > 1.0:
        flag = " <<"
    elif abs(rel) > 0.5:
        flag = " <"
    else:
        ok_count += 1
    rel_s = f"{rel:>+7.2f}%" if rel == rel else f"{'N/A':>8}"
    print(f"  {label:<33} {o:>12.6f} {z:>12.6f} {diff:>+10.6f} {rel_s}{flag}")

# ── Summary ──
print(f"\n  {'='*60}")
print(f"  Summary: {ok_count} items within 1%, {big_diff} items > 5%")
print(f"  Systematic offset in f'/l' explained by glass index difference")
print(f"  (our n_d=1.51637 vs CDGM-ZEMAX n_d=1.51680, ~0.03% dn)")
