"""FROZEN rain-tank reference for the wind-shadow trial (candidate c2; audit
2026-09-24-a3 round 03, R6.3). A verbatim copy of production's v0.10.1 tank
(forecast/flood_forecast_daily.py: simulate_pluvial_series, _pluvial_fill,
the tank/drain constants), the stage-storage curve (a copy of
history/data/stage_storage_curve.csv) and the flood-window landmark heights,
as they were when c2 was frozen. The evaluator imports THIS module, so a
later production change cannot alter the frozen rain comparison; this file
and the curve copy are hash-bound in models/wind_shadow/FREEZE.md.
Equivalence with production at freeze time: audits/2026-09-24-a3 (reply 04).
"""
import csv
import datetime as dt
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE_CURVE_PATH = os.path.join(HERE, "stage_storage_curve.csv")

PLUVIAL_STREET_BASE = 3.52
PLUVIAL_DRAIN_FULL_BELOW = 3.0
PLUVIAL_DRAIN_RATE = 0.25
TANK_K = 1.296e6
TANK_GAMMA = 0.78
TANK_KOUT = 3.50
TANK_LAG_MIN = 15

# production FLOOD_WINDOW_KEYS with their NAVD88 elevations (ft)
LANDMARKS_NAVD88 = {
    "grate_SW": 3.52, "grate_SE": 3.60, "corner_SE": 3.64, "corner_SW": 3.64,
    "grate_bay_ave_upstream": 3.64, "gutter_walkway": 3.78, "grate_NE": 3.80, "grate_NW": 3.80,
    "corner_NE": 3.91, "corner_NW": 3.91, "curb": 4.16, "sidewalk_under_walkway_lawn_step": 4.33,
    "road_middle": 4.36, "intersection_highpoint": 4.54, "lawn_step": 4.66, "porch_step_base": 4.68,
}

_CURVE = None


def load_stage_curve(path=STAGE_CURVE_PATH):
    global _CURVE
    if _CURVE is None or path != STAGE_CURVE_PATH:
        curve = []
        with open(path) as f:
            for r in csv.DictReader(f):
                curve.append((float(r["stage_in_vs_sw_grate"]), float(r["wet_area_cells"])))
        if path != STAGE_CURVE_PATH:
            return curve
        _CURVE = curve
    return _CURVE


def pluvial_fill(curve, base_stage, budget):
    stage = base_stage
    for i in range(1, len(curve)):
        prior_stage = curve[i - 1][0]
        upper_stage, area = curve[i]
        if upper_stage <= base_stage:
            continue
        lower_stage = max(base_stage, prior_stage)
        step_v = area * (upper_stage - lower_stage)
        if budget < step_v:
            stage = (lower_stage + budget / area if area > 0 else upper_stage)
            budget = 0
            break
        budget -= step_v
        stage = upper_stage
    if budget > 0:
        last_area = curve[-1][1]
        if last_area > 0:
            stage += budget / last_area
    return stage


def simulate_pluvial_series(times, tide_waters, rates, dt_min=5.0):
    """Production's tank, frozen: pluvial water NAVD88 per point (None where the
    tank holds no water above the base). Storage is empty at times[0]."""
    curve = load_stage_curve()
    if not curve or len(times) < 2:
        return [None] * len(times)

    def rate_at(t):
        t = t - dt.timedelta(minutes=TANK_LAG_MIN)
        if t <= times[0]:
            return rates[0]
        for i in range(1, len(times)):
            if t <= times[i]:
                return rates[i - 1]
        return rates[-1]

    def bay_at(t):
        for i in range(1, len(times)):
            if t <= times[i]:
                return tide_waters[i - 1]
        return tide_waters[-1]

    out = []
    V = 0.0
    t = times[0]
    idx = 0
    step = dt.timedelta(minutes=dt_min)
    while idx < len(times):
        while t < times[idx]:
            bay = bay_at(t)
            span = PLUVIAL_STREET_BASE - PLUVIAL_DRAIN_FULL_BELOW
            frac = min(1.0, max(0.0, (PLUVIAL_STREET_BASE - bay) / span))
            net = max(0.0, rate_at(t) - PLUVIAL_DRAIN_RATE * frac)
            dV = (TANK_K * net ** TANK_GAMMA - TANK_KOUT * V) * (dt_min / 60.0)
            V = max(0.0, V + dV)
            t = t + step
        bay = tide_waters[idx]
        base = max(bay, PLUVIAL_STREET_BASE)
        base_stage = max(0.0, (base - PLUVIAL_STREET_BASE) * 12)
        if V > 0:
            stage = pluvial_fill(curve, base_stage, V)
            w = PLUVIAL_STREET_BASE + stage / 12.0
            out.append(w if (w - base) * 12 > 0.25 else None)
        else:
            out.append(None)
        idx += 1
    return out
