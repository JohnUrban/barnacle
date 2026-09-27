#!/usr/bin/env python3
"""Rain forcing and explicit scenario comparison for the 2026-09-25..27 storm
(audit 2026-09-27-a1 R2). Offline: reads the committed MRMS extraction
(history/data/mrms/mrms_extracted.csv, catchment box mean, 6-min stride),
the archived gauge series (gauge-sources/) and the ledger. Writes
rain_scenarios.json. Nothing here fits a coefficient or a gate formula.

Per tide window it reports:
  coverage       frames present / expected on the 6-min grid, missing stamps
  totals         rectangular 6-min sum (in), peak 6-min rate, burst intervals
  scenarios      the production tank (TANK_K/GAMMA/KOUT, TANK_LAG_MIN,
                 _pluvial_fill on the stage-storage curve) driven by the
                 box-mean rate under EXPLICIT, labeled assumptions:
     A  fixed-base, zero-drain SENSITIVITY: base stage held at the tide's
        crest bay level, drain = 0 all window (the HANDOFF "~2.4 in" number;
        reproduces the audit probe within rounding)
     B  bay-tracking base, zero drain: base = archived despiked bay level at
        each step, drain = 0 (bay above grates most of the window)
     C  bay-tracking base, production head-dependent drain
        (PLUVIAL_DRAIN_RATE * clamp((3.52 - bay)/0.52)), i.e. what the live
        nowcast tank does with a real bay
     D  fixed LOW base 2.50 ft (drains fully open): the rain alone
  Every scenario is a model sensitivity, not measured attribution. The
  street tape series is listed beside them for comparison only.
Run: ~/.barnacle/venv/bin/python event10_rain_scenarios.py
"""
import csv
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
from forecast import flood_forecast_daily as ff  # noqa: E402

MRMS = REPO / "history/data/mrms/mrms_extracted.csv"
LEDGER = REPO / "data/labeled_observations.csv"
UTC = dt.timezone.utc
STEP = dt.timedelta(minutes=2)
WINDOWS = [  # episode, rain window UTC [start, end], crest bay for scenario A
    ("2026-09-25-e01", "2026-09-25T21:00:00Z", "2026-09-26T04:30:00Z"),
    ("2026-09-26-e01", "2026-09-26T08:00:00Z", "2026-09-26T17:00:00Z"),
    ("2026-09-26-e02", "2026-09-26T21:00:00Z", "2026-09-27T04:00:00Z"),
    ("2026-09-27-e01", "2026-09-27T08:00:00Z", "2026-09-27T17:00:00Z"),
]


def load_rain(a, b):
    rows = [r for r in csv.DictReader(MRMS.open())
            if r["product"] == "PrecipRate" and a <= r["utc"] <= b]
    frames = sorted((dt.datetime.fromisoformat(r["utc"].replace("Z", "+00:00")),
                     float(r["box_mean"]) / 25.4, float(r["box_max"]) / 25.4) for r in rows)
    t0 = dt.datetime.fromisoformat(a.replace("Z", "+00:00"))
    t1 = dt.datetime.fromisoformat(b.replace("Z", "+00:00"))
    expected, t = [], t0
    while t <= t1:
        expected.append(t)
        t += dt.timedelta(minutes=6)
    have = {f[0] for f in frames}
    return frames, expected, [t.isoformat() for t in expected if t not in have]


def load_bay():
    files = sorted((HERE / "gauge-sources").glob("sandy-hook-*Z.json"))
    rows = json.loads(files[-1].read_text())["data"]
    pairs = [(dt.datetime.strptime(r["t"], "%Y-%m-%d %H:%M").replace(tzinfo=UTC),
              float(r["v"]) + ff.MLLW_TO_NAVD88_OFFSET) for r in rows if r["v"]]
    desp = ff._despike_gauge([(t.isoformat(), v) for t, v in pairs])
    return [(dt.datetime.fromisoformat(t), v) for t, v in desp], files[-1].name


def bay_at(bay, t):
    prev = bay[0][1]
    for bt, v in bay:
        if bt > t:
            break
        prev = v
    return prev


def tank(frames, t0, t1, base_fn, drain_fn):
    """Production tank stepped at 2 min with the 15-min lagged 6-min box rate."""
    lag = dt.timedelta(minutes=ff.TANK_LAG_MIN)
    curve = ff._load_stage_curve()
    V, t, out = 0.0, t0, []
    while t <= t1:
        cands = [r for ft, r, _ in frames if ft <= t - lag]
        rate = cands[-1] if cands else 0.0
        base = base_fn(t)
        drain = drain_fn(t)
        net = max(0.0, rate - drain)
        V = max(0.0, V + (ff.TANK_K * net ** ff.TANK_GAMMA - ff.TANK_KOUT * V) * (2.0 / 60.0))
        stage = max(0.0, (base - ff.GRATE_SW) * 12)
        water = ff._pluvial_fill(curve, stage, V) if V > 0 else stage
        out.append((t, round(water, 2), round(water - stage, 2)))
        t += STEP
    return out


def street_series(a, b):
    elev = {k: e for k, _l, e, _s in ff.LANDMARKS}
    ta, tb = (dt.datetime.fromisoformat(x.replace("Z", "+00:00")) for x in (a, b))
    out = []
    for r in csv.DictReader(LEDGER.open()):
        try:
            t = ff.parse_station_local_time(r["observation_time_local"]).astimezone(UTC)
            w = elev[r["landmark_key"]] + float(r["observed_depth_in"]) / 12
        except (KeyError, ValueError, TypeError):
            continue
        if ta <= t <= tb and r.get("observer") == "john":
            out.append({"utc": t.isoformat(), "navd88": round(w, 3),
                        "in_vs_sw": round((w - ff.GRATE_SW) * 12, 2)})
    return sorted(out, key=lambda x: x["utc"])


def main():
    bay, bay_file = load_bay()
    result = {"prepared_utc": dt.datetime.now(UTC).isoformat(timespec="seconds"),
              "inputs": {"mrms": str(MRMS.relative_to(REPO)), "gauge": bay_file,
                         "tank_constants": {"TANK_K": ff.TANK_K, "TANK_GAMMA": ff.TANK_GAMMA,
                                            "TANK_KOUT": ff.TANK_KOUT, "TANK_LAG_MIN": ff.TANK_LAG_MIN,
                                            "PLUVIAL_DRAIN_RATE": ff.PLUVIAL_DRAIN_RATE},
                         "model_version": ff.CURRENT_MODEL_VERSION},
              "caveat": ("Every scenario is a sensitivity of the production tank under a stated "
                         "base/drain assumption. None is a measured rain/tide partition of the "
                         "street crest; the tank was calibrated on low-bay rain events and a "
                         "closed tide gate is not represented. No gate formula is fitted."),
              "windows": {}}
    for eid, a, b in WINDOWS:
        frames, expected, missing = load_rain(a, b)
        t0 = dt.datetime.fromisoformat(a.replace("Z", "+00:00"))
        t1 = dt.datetime.fromisoformat(b.replace("Z", "+00:00"))
        w = {"rain_window_utc": [a, b],
             "coverage": {"frames": len(frames), "expected": len(expected),
                          "missing_utc": missing,
                          "integration": "rectangular 6-min sum of catchment box-mean rate"},
             "scenarios": {}, "street_tape": street_series(a, b)}
        if not frames:
            w["status"] = "no rain frames cached for this window"
            result["windows"][eid] = w
            continue
        total = sum(r * 0.1 for _, r, _ in frames)
        peak = max(frames, key=lambda f: f[1])
        bursts = [(t.isoformat(), round(r, 2), round(mx, 2)) for t, r, mx in frames if r >= 0.5]
        w["totals"] = {"box_mean_sum_in": round(total, 3),
                       "peak_6min_box_mean_in_hr": round(peak[1], 2), "peak_utc": peak[0].isoformat(),
                       "frames_at_or_above_0p5_in_hr": bursts}
        crest_bay = max(bay_at(bay, t) for t in expected)
        scen = {
            "A_fixed_crest_base_zero_drain": (lambda t: crest_bay, lambda t: 0.0),
            "B_bay_tracking_base_zero_drain": (lambda t: bay_at(bay, t), lambda t: 0.0),
            "C_bay_tracking_base_head_drain": (
                lambda t: bay_at(bay, t),
                lambda t: ff.PLUVIAL_DRAIN_RATE * min(1, max(0, (ff.GRATE_SW - bay_at(bay, t)) / 0.52))),
            "D_fixed_low_base_2p50_full_drain": (lambda t: 2.50, lambda t: ff.PLUVIAL_DRAIN_RATE),
        }
        for name, (bfn, dfn) in scen.items():
            series = tank(frames, t0, t1, bfn, dfn)
            pk = max(series, key=lambda s: s[2])
            w["scenarios"][name] = {
                "assumption": {"A_fixed_crest_base_zero_drain": f"base held at crest bay {crest_bay:.3f} ft NAVD88; drain 0",
                               "B_bay_tracking_base_zero_drain": "base = despiked archived bay each step; drain 0",
                               "C_bay_tracking_base_head_drain": "base = despiked archived bay; production head-dependent drain",
                               "D_fixed_low_base_2p50_full_drain": "base 2.50 ft (drains open); full drain rate"}[name],
                "peak_rain_lift_in": pk[2], "peak_lift_utc": pk[0].isoformat(),
                "peak_water_in_vs_sw": pk[1],
                "series_10min": [(s[0].strftime("%H:%MZ"), s[1], s[2]) for s in series[::5]],
            }
        result["windows"][eid] = w
    (HERE / "rain_scenarios.json").write_text(json.dumps(result, indent=1))
    for eid, w in result["windows"].items():
        print(eid, w.get("status", ""), json.dumps(w.get("coverage")), json.dumps(w.get("totals", {}).get("box_mean_sum_in")),
              {k: (v["peak_rain_lift_in"], v["peak_lift_utc"]) for k, v in w["scenarios"].items()})


if __name__ == "__main__":
    main()
