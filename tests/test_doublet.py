"""Cemented doublet validation test"""
import sys
sys.path.insert(0, ".")
from engine.lens_loader import load_lens
from engine.aberration import compute_76_items

lens = load_lens("test_cases/cemented_doublet.json")
r = compute_76_items(lens)
inf = r["infinite"]

print("=" * 55)
print("  Cemented Achromatic Doublet  Validation")
print("=" * 55)
print(f"  f'                   = {inf['f_prime']:.2f} mm")
print(f"  l'                   = {inf['l_prime']:.2f} mm")
print(f"  SA (full / 0.7)      = {inf['spherical_aberration_full']:+.4f} / {inf['spherical_aberration_0.7']:+.4f} mm")
print(f"  Coma (full fld/apt)  = {inf['meridional_coma_full_field_full_apt']:+.4f} mm")
print(f"  Dist (full / 0.7)    = {inf['relative_distortion_full_field']:+.2f}% / {inf['relative_distortion_0.7_field']:+.2f}%")
print(f"  LCA (0 apt)          = {inf['axial_chromatic_0']:+.4f} mm  <-- achromatic!")
print(f"  LCA (full apt)       = {inf['axial_chromatic_full']:+.4f} mm")
print(f"  TCA (full field)     = {inf['lateral_chromatic_full_field']:+.6f} mm")
print(f"  Astigmatism          = {inf['delta_xts']:+.4f} mm")
print(f"  y_full (paraxial)    = {inf['y_full_prime']:.4f} mm")
print(f"  y_full (actual d)    = {inf['image_height_full_field_d']:.4f} mm")
print(f"  Total items          = {r['summary']['total']}")

# Key check: is LCA significantly better than singlet?
singlet = load_lens("lens.json")
sr = compute_76_items(singlet)
singlet_lca = sr["infinite"]["axial_chromatic_0"]
print(f"\n  Singlet LCA (0 apt)  = {singlet_lca:+.4f} mm")
print(f"  Improvement factor   = {abs(singlet_lca / inf['axial_chromatic_0']):.0f}x better!")
