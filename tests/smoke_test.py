"""Quick smoke test for OptiCore engine"""
import sys
sys.path.insert(0, ".")

from engine.lens_loader import load_lens
from engine.ray_generator import generate_rays, get_ray_count_summary
from engine.paraxial import compute_paraxial
from engine.aberration import compute_76_items
from engine.file_manager import export_to_csv

lens = load_lens("lens.json")
print("=== Lens Loaded ===")
print(f"Surfaces: {lens.num_surfaces}, Field height: {lens.field_height}mm")

# Ray generation
bundles = generate_rays(lens)
summary = get_ray_count_summary(bundles)
print(f"\n=== Ray Generation ===")
print(f"Total rays: {summary['total_rays']}")
print(f"By wavelength: {summary['by_wavelength']}")

# Paraxial
print(f"\n=== Paraxial Calculation ===")
p = compute_paraxial(lens)
for k, v in p.items():
    if isinstance(v, float):
        print(f"  {k}: {v:.4f}")
    else:
        print(f"  {k}: {v}")

# Full 76 items
print(f"\n=== Full Aberration ===")
all_results = compute_76_items(lens)
s = all_results["summary"]
print(f"Infinite: {s['infinite_count']} items")
print(f"Finite:  {s['finite_count']} items")
print(f"Total:   {s['total']} items")

expected = 78  # 39 项/物距（含 y_full_prime）
if s["total"] >= 76:
    print(f">>> ITEM COUNT: {s['total']} (>= 76 baseline) <<<")
else:
    print(f">>> MISMATCH: expected >= 76, got {s['total']} <<<")

# List all keys
print("\n--- Infinite keys ---")
for k in sorted(all_results["infinite"].keys()):
    v = all_results["infinite"][k]
    if isinstance(v, float):
        print(f"  {k}: {v:.6g}")
    else:
        print(f"  {k}: {v}")
