"""Debug marginal ray trace"""
import sys, math
sys.path.insert(0, ".")
from engine.lens_loader import load_lens
from engine.ray_tracer import trace_single_ray
from engine.data_model import Ray

lens = load_lens("lens.json")
r = Ray(L=10.0, U=0.0, wavelength="d")
res = trace_single_ray(lens, r)

if res:
    print(f"L_last={res['L_last']:.4f}")
    print(f"U_last={res['U_last']:.6f} rad = {math.degrees(res['U_last']):.2f} deg")
    print(f"d_cross={res['d_cross']:.4f}")
    print(f"Expected U_last = {-10/45.2089:.4f} rad")
    print("Path:")
    for p in res["path"]:
        print(f"  Surf {p['surface_index']}: zh={p['z_hit']:.4f}, L={p['L']:.4f}, U={p['U']:.6f}")
else:
    print("FAILED")
