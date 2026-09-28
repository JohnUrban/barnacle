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
  street reading series is listed beside them for comparison only.
  Per scenario (round 05 R7): `max_increment_in` and its time, the water at
  THAT instant (`water_at_max_increment_in_vs_sw`), the separate
  `max_water_in_vs_sw` and its time (base + increment can peak at a
  different time when the bay is moving), and the increment over the
  observed corner-crest window where one exists.
  Missing-frame handling: the tank steps every 2 min; the rate applied at
  step t is the LAST cached 6-min frame at or before t − TANK_LAG_MIN (a
  missing frame is bridged by the previous frame, never zero-filled).
  Storage starts empty (V = 0) at the window start; a window that opens
  during rain understates early storage.
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
WINDOWS = [  # episode, rain window UTC [start, end]
    ("2026-09-25-e01", "2026-09-25T21:00:00Z", "2026-09-26T04:30:00Z"),
    ("2026-09-26-e01", "2026-09-26T08:00:00Z", "2026-09-26T17:00:00Z"),
    ("2026-09-26-e02", "2026-09-26T21:00:00Z", "2026-09-27T04:00:00Z"),
    ("2026-09-27-e01", "2026-09-27T08:00:00Z", "2026-09-27T17:00:00Z"),
]
# observed corner-crest windows (measured plateau, station-local → UTC)
CREST = {"2026-09-26-e01": ("2026-09-26T13:06:00Z", "2026-09-26T13:13:00Z"),
         "2026-09-26-e02": ("2026-09-27T02:11:00Z", "2026-09-27T02:29:00Z"),
         "2026-09-27-e01": ("2026-09-27T13:44:00Z", "2026-09-27T14:06:00Z")}


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
             "scenarios": {}, "street_readings": street_series(a, b)}
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
        crest = CREST.get(eid)
        for name, (bfn, dfn) in scen.items():
            series = tank(frames, t0, t1, bfn, dfn)
            pk_inc = max(series, key=lambda s: s[2])       # largest rain INCREMENT
            pk_wat = max(series, key=lambda s: s[1])       # largest TOTAL water
            entry = {
                "assumption": {"A_fixed_crest_base_zero_drain": f"base held at crest bay {crest_bay:.3f} ft NAVD88; drain 0",
                               "B_bay_tracking_base_zero_drain": "base = despiked archived bay each step; drain 0",
                               "C_bay_tracking_base_head_drain": "base = despiked archived bay; production head-dependent drain",
                               "D_fixed_low_base_2p50_full_drain": "base 2.50 ft (drains open); full drain rate"}[name],
                "max_increment_in": pk_inc[2], "max_increment_utc": pk_inc[0].isoformat(),
                "water_at_max_increment_in_vs_sw": pk_inc[1],
                "max_water_in_vs_sw": pk_wat[1], "max_water_utc": pk_wat[0].isoformat(),
                "series_10min": [(s[0].strftime("%H:%MZ"), s[1], s[2]) for s in series[::5]],
            }
            if crest:
                c0 = dt.datetime.fromisoformat(crest[0].replace("Z", "+00:00"))
                c1 = dt.datetime.fromisoformat(crest[1].replace("Z", "+00:00"))
                inside = [x for x in series if c0 <= x[0] <= c1]
                if inside:
                    entry["increment_at_corner_crest_in"] = {
                        "window_utc": list(crest),
                        "min": min(x[2] for x in inside), "max": max(x[2] for x in inside)}
            w["scenarios"][name] = entry
        result["windows"][eid] = w
    (HERE / "rain_scenarios.json").write_text(json.dumps(result, indent=1))
    for eid, w in result["windows"].items():
        print(eid, w.get("status", ""), "total_in", json.dumps(w.get("totals", {}).get("box_mean_sum_in")))
        for k, v in w["scenarios"].items():
            print("   ", k, "max_inc", v["max_increment_in"], v["max_increment_utc"][11:16],
                  "max_water", v["max_water_in_vs_sw"], v["max_water_utc"][11:16],
                  "crest_inc", v.get("increment_at_corner_crest_in", {}).get("min"), v.get("increment_at_corner_crest_in", {}).get("max"))


if __name__ == "__main__":
    main()
