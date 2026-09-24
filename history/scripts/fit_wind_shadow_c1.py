#!/usr/bin/env python3
"""Fit wind-shadow candidate c1 and write models/wind_shadow/manifest.json.
Construction and the coefficient-route rule: models/wind_shadow/DESIGN.md
(committed before this comparison). Features are built with the SAME code the
live shadow uses (forecast/wind_shadow.py: select_run, features), so training
and live construction match by construction for route A; route B's features
come from the previous-runs archive and are used only if the predeclared
equivalence test passes.
Inputs (git-ignored, regeneratable): history/data/gfs_single_runs/runs.parquet
(pull_gfs_single_runs.py), history/data/forecast_test/{surge_hourly,met_obs,
fcst_gfs_seamless}.parquet (pull_surge_forecast_test_data.py).
Run: python3 history/scripts/fit_wind_shadow_c1.py
"""
import datetime as dt, hashlib, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from forecast import wind_shadow as ws  # noqa: E402

UTC = dt.timezone.utc
THETA, LATENCY_H, TAU, CAP = 70.0, 6, 36.0, 3.0
FT = ROOT / "history/data/forecast_test"

sv = pd.read_parquet(FT / "surge_hourly.parquet").set_index("timestamp").asfreq("h")
sv.index = sv.index.tz_localize("UTC")
mo = pd.read_parquet(FT / "met_obs.parquet").set_index("timestamp").sort_index()
mo.index = mo.index.tz_localize("UTC")
mo = mo[~mo.index.duplicated()].reindex(sv.index)
s = sv.surge_ft
# production mean policy replayed: mean surge over [t - 21 d - 364 d, t - 21 d)
m_prod = s.rolling(24 * 364, min_periods=24 * 300).mean().shift(24 * 21)
p = mo.pressure_mb
p_anom = p - p.rolling(24 * 30, min_periods=24 * 20).mean().shift(1)

runs = pd.read_parquet(ROOT / "history/data/gfs_single_runs/runs.parquet")
runs["run_init_utc"] = pd.to_datetime(runs.run_init_utc, utc=True); runs["valid_utc"] = pd.to_datetime(runs.valid_utc, utc=True)
by_run = {k: {v.to_pydatetime(): (a, b, c) for v, a, b, c in zip(g.valid_utc, g.wind_kn, g.wind_dir, g.pressure_hpa)}
          for k, g in runs.groupby("run_init_utc")}
by_run = {k.to_pydatetime(): v for k, v in by_run.items()}
fc = pd.read_parquet(FT / "fcst_gfs_seamless.parquet").set_index("timestamp").sort_index()
fc.index = fc.index.tz_localize("UTC") if fc.index.tz is None else fc.index


def feats_single(t, h):
    init, _ = ws.select_run(t, LATENCY_H)
    rh = by_run.get(init)
    if rh is None:
        return None
    po, pa = p.get(t), p_anom.get(t)
    if po is None or pa is None or not (math.isfinite(po) and math.isfinite(pa)):
        return None
    f, _why = ws.features(rh, t, float(po), float(pa), h, THETA)
    return f


def feats_prev(t, h):
    d = 1 if h <= 24 else 2
    vals = []
    for k in range(1, h + 1):
        tt = t + dt.timedelta(hours=k)
        if tt not in fc.index:
            return None
        spd, dr = fc.at[tt, f"wind_speed_10m_previous_day{d}"], fc.at[tt, f"wind_direction_10m_previous_day{d}"]
        if not (np.isfinite(spd) and np.isfinite(dr)):
            return None
        vals.append(ws.stress(float(spd), float(dr), THETA))
    po, pa = p.get(t), p_anom.get(t)
    pe = fc.at[t + dt.timedelta(hours=h), f"pressure_msl_previous_day{d}"]
    if po is None or pa is None or not (math.isfinite(po) and math.isfinite(pa) and np.isfinite(pe)):
        return None
    return (sum(vals) / len(vals), float(pe) - float(po), float(pa))


# ---- 1. predeclared equivalence test on the overlap
first_run, last_run = min(by_run), max(by_run)
overlap = [t.to_pydatetime() for t in sv.index if first_run + dt.timedelta(hours=LATENCY_H) <= t.to_pydatetime()
           <= min(last_run, fc.index.max().to_pydatetime()) - dt.timedelta(hours=48)]
eq = {}
for h in (12, 24, 30):
    a, b = [], []
    for t in overlap:
        fs, fp = feats_single(t, h), feats_prev(t, h)
        if fs is not None and fp is not None:
            a.append(fs[0]); b.append(fp[0])
    a, b = np.array(a), np.array(b)
    r = float(np.corrcoef(a, b)[0, 1]); slope = float((a * b).sum() / (b * b).sum())
    eq[h] = {"n": int(len(a)), "pearson_r": round(r, 4), "slope_single_on_prev": round(slope, 4)}
equivalent = all(v["pearson_r"] >= 0.95 and 0.9 <= v["slope_single_on_prev"] <= 1.1 for v in eq.values())
route = "B (previous-runs archive, longer)" if equivalent else "A (single runs only, exact live construction)"
print("equivalence test (W_h, single-run vs previous-runs construction):", json.dumps(eq))
print("route:", route)

# ---- 2. fit every lead 1..48 on the chosen route
feat_fn = feats_prev if equivalent else feats_single
if equivalent:
    t_start = max(fc.index.min().to_pydatetime(), pd.Timestamp("2024-02-01", tz="UTC").to_pydatetime())
else:
    t_start = first_run + dt.timedelta(hours=LATENCY_H)
t_end = sv.index.max().to_pydatetime() - dt.timedelta(hours=48)          # targets must be observed
issuances = [t.to_pydatetime() for t in sv.index if t_start <= t.to_pydatetime() <= t_end]
coefs, fitinfo = {}, {}
for h in range(1, 49):
    X, y, base_err, cand_rows = [], [], [], []
    for t in issuances:
        s0, mp, s1 = s.get(t), m_prod.get(t), s.get(t + dt.timedelta(hours=h))
        if s0 is None or mp is None or s1 is None or not all(map(math.isfinite, (s0, mp, s1))):
            continue
        f = feat_fn(t, h)
        if f is None:
            continue
        base = mp + (s0 - mp) * math.exp(-h / TAU)
        X.append(f); y.append(s1 - base)
    X, y = np.array(X), np.array(y)
    Xd = np.column_stack([X, np.ones(len(X))])
    beta = np.linalg.lstsq(Xd, y, rcond=None)[0]
    pred = np.clip(Xd @ beta, -CAP, CAP)
    coefs[str(h)] = [round(float(b), 8) for b in beta]
    fitinfo[str(h)] = {"n": int(len(y)), "in_sample_mae_baseline_ft": round(float(np.abs(y).mean()), 4),
                       "in_sample_mae_candidate_ft": round(float(np.abs(y - pred).mean()), 4)}
    if h in (6, 12, 24, 30, 48):
        print(f"lead {h:2d} h: n={len(y)} in-sample MAE baseline {np.abs(y).mean():.3f} -> candidate {np.abs(y - pred).mean():.3f} ft; coef {coefs[str(h)]}")

manifest = {
    "candidate_id": "wind-shadow-c1",
    "created_utc": dt.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "status": "FROZEN for the prospective shadow trial; do not refit; a changed model gets a new id",
    "plan": "history/plans/2026-09-24-wind-term-candidate-plan.md", "design": "models/wind_shadow/DESIGN.md",
    "fit_script": "history/scripts/fit_wind_shadow_c1.py",
    "feed": "Open-Meteo Single Runs API", "model": "gfs_seamless", "resolves_to": "ncep_gfs013",
    "latitude": 40.4669, "longitude": -74.0094, "forecast_hours": 61, "latency_h": LATENCY_H,
    "units": {"wind_speed_10m": "kn", "wind_direction_10m": "deg FROM", "pressure_msl": "hPa",
              "observed_pressure": "hPa (CO-OPS air_pressure, metric)", "surge": "ft"},
    "theta_deg": THETA, "tau_h": TAU, "correction_cap_ft": CAP, "leads_h": [1, 48],
    "beyond_48h": "no correction (baseline)", "requires": "fresh surge reading (<= 60 min) and complete inputs",
    "mean_policy": "production: 364-day verified window ending ~21 days back (training replays it)",
    "navd88_offset_ft": -2.82, "local_enhancement_ft": 0.0,
    "coefficient_order": ["b1 wind stress (kn^2)", "b2 dP (hPa)", "b3 P_anom (hPa)", "a intercept (ft)"],
    "route": route, "equivalence_test": eq,
    "fit_span_issuance_utc": [t_start.strftime("%Y-%m-%dT%HZ"), t_end.strftime("%Y-%m-%dT%HZ")],
    "coefficients": coefs, "fit_info": fitinfo,
    "note": "in-sample MAE is descriptive only; the prospective shadow period is the test",
}
out = ROOT / "models/wind_shadow/manifest.json"
out.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
print("wrote", out.relative_to(ROOT), "sha256", hashlib.sha256(out.read_bytes()).hexdigest()[:16])
