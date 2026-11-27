import sys
sys.path.insert(0, ".")
from forecast import flood_forecast_daily as ff
ff._load_stage_curve()
def steady(bay, r, minutes=105):
    drain = ff.PLUVIAL_DRAIN_RATE * min(1, max(0, (3.52 - bay) / 0.52))
    base = max(0.0, (bay - 3.52) * 12)
    V = 0.0
    for _ in range(minutes // 2):
        net = max(0.0, r - drain)
        V = max(0.0, V + (ff.TANK_K * net ** ff.TANK_GAMMA - ff.TANK_KOUT * V) * (2.0 / 60.0))
    stage = ff._pluvial_fill(ff._STAGE_CURVE, base, V) if V > 0 else base
    return drain, base, stage
print("PLUVIAL_DRAIN_RATE =", ff.PLUVIAL_DRAIN_RATE, "-> max(0.3, drain) is always 0.3 (drain never exceeds", ff.PLUVIAL_DRAIN_RATE, ")")
for bay, r in ((3.52, 0.27), (3.52, 0.30), (3.60, 0.25), (4.20, 0.14), (6.29, 0.25), (6.29, 0.0), (2.0, 0.30)):
    d, b, s = steady(bay, r)
    print(f"bay {bay:5.2f} ft, steady rain {r:.2f} in/hr: drain {d:.3f}, bay-head stage {b:5.1f} in, tank stage {s:5.1f} in  | nowcast gate active = {r > max(0.3, d)}")
