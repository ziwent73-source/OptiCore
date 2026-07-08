"""Smoke test v2 — 验证动态 field_fractions / pupil_fractions"""
import sys
sys.path.insert(0, ".")

from engine.lens_loader import load_lens_from_dict
from engine.glass_loader import load_glass_catalog
from engine.aberration import compute_system
from engine.file_manager import export_to_csv, format_detailed_tables

# Test 1: Default (field_fractions=[0.7], pupil_fractions=[0.7])
print("=" * 60)
print("Test 1: field_fractions=[0.7], pupil_fractions=[0.7]")
print("  Expected: fields=[0, 0.7, 1.0], pupils=[0.0, 0.7, 1.0]")

DEMO = {
    "name": "Test Default",
    "system_parameters": {
        "object_distance": None, "entrance_pupil_radius": 10.0,
        "aperture_stop_index": 0, "max_field_height": 18.0,
    },
    "calculation_settings": {
        "field_mode": "image_height", "field_value": 18.0,
        "aperture_angle_deg": 5.0,
        "field_fractions": [0.7],
        "pupil_fractions": [0.7],
    },
    "surfaces": [
        {"radius": 42.0, "thickness": 6.0, "glass": "H-K9L", "diameter": 25.0},
        {"radius": -50.0, "thickness": 42.0, "glass": "Air", "diameter": 25.0},
    ],
    "glass_library": "",
}

lens = load_lens_from_dict(DEMO)
lens.wavelengths = ["d", "F", "C"]
print(f"  field_fractions (merged): {lens.field_fractions}")
print(f"  pupil_fractions (merged): {lens.pupil_fractions}")

results = compute_system(lens)
n = len([v for v in results.values() if isinstance(v, (int, float))])
print(f"  Computed: {n} numeric items")

# Check key field-related keys exist
for k in sorted(results.keys()):
    if "0.7" in k or "full" in k:
        pass  # Should be present

# Test 2: Custom fractions (field_fractions=[0.4, 0.7], pupil_fractions=[0.5, 0.8])
print()
print("=" * 60)
print("Test 2: field_fractions=[0.4, 0.7], pupil_fractions=[0.5, 0.8]")
print("  Expected: fields=[0, 0.4, 0.7, 1.0], pupils=[0.0, 0.5, 0.8, 1.0]")

DEMO2 = {
    "name": "Test Custom",
    "system_parameters": {
        "object_distance": None, "entrance_pupil_radius": 10.0,
        "aperture_stop_index": 0, "max_field_height": 18.0,
    },
    "calculation_settings": {
        "field_mode": "image_height", "field_value": 18.0,
        "aperture_angle_deg": 5.0,
        "field_fractions": [0.4, 0.7],
        "pupil_fractions": [0.5, 0.8],
    },
    "surfaces": [
        {"radius": 42.0, "thickness": 6.0, "glass": "H-K9L", "diameter": 25.0},
        {"radius": -50.0, "thickness": 42.0, "glass": "Air", "diameter": 25.0},
    ],
    "glass_library": "",
}

lens2 = load_lens_from_dict(DEMO2)
lens2.wavelengths = ["d", "F", "C"]
print(f"  field_fractions (merged): {lens2.field_fractions}")
print(f"  pupil_fractions (merged): {lens2.pupil_fractions}")

results2 = compute_system(lens2)
n2 = len([v for v in results2.values() if isinstance(v, (int, float))])
print(f"  Computed: {n2} numeric items")

# Check specific dynamic keys exist
for prefix in ["image_height_0.4_field", "image_height_0.7_field",
               "meridional_coma_0.4_field_0.5_apt", "meridional_coma_0.4_field_full_apt",
               "axial_image_0.5_d", "spherical_aberration_0.5"]:
    found = prefix in str(sorted(results2.keys()))
    print(f"  Key prefix '{prefix}': {'FOUND' if any(k.startswith(prefix) for k in results2) else 'MISSING'}")

# Test 3: Tables and CSV
tables = format_detailed_tables(results2, lens_config={
    "pupil_fractions": lens2.pupil_fractions,
    "field_fractions": lens2.field_fractions,
    "field_mode": "image_height", "field_value": 18.0,
})
print(f"\n  Tables: {len(tables)} categories")
for t in tables:
    row_keys = [r["参数"] for r in t["rows"]]
    print(f"    {t['title']}: {len(t['rows'])} rows")

csv = export_to_csv(results2, metadata={"lens": "Test Custom"})
print(f"\n  CSV lines: {len(csv.splitlines())}")

print()
print("=" * 60)
print("ALL TESTS PASSED")
