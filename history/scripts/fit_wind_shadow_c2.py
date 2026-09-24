#!/usr/bin/env python3
"""Fit wind-shadow candidate c2 (repairs per audit 2026-09-24-a3; c1's fit script is kept
unchanged as history) and write models/wind_shadow/manifest.json.
c2 changes (R4, R5): the PRODUCTION mean policy is replayed (verified hourly
surge from the calendar day 364 days back up to the verified-data end, which is
LAG_VERIFIED_D before issuance; measured 24 d on 2026-09-24, an assumption for
history); observed pressure uses the hourly product WITH quality flags (all 0
required), the window [t0 - 30 d, t0) and >= 480 of its 720 hours; dataset
identities (SHA-256) are bound into the manifest; nominal targets t0 + h from
the issuance hour t0; the reading is the 6-min value at t0.
Round 03/05 (a3 R5, R5-Q1): the training OUTCOME (target) must pass the
evaluator's own water-level classifier (classify_water_level, imported):
preliminary [O,F,R,L] valid iff F=R=L=0 (O is a count); verified [I,F,R,T]
valid iff all 0 (I = inferred); missing/unknown q invalid. From a re-pull of the
6-min water_level WITH flags (history/data/forecast_test/water_level_flags.parquet).
The READING mirrors production, which applies no flag QC (it despikes); the
mean replays production's policy, which also applies no flag QC.
Construction and the coefficient-route rule: models/wind_shadow/DESIGN.md
(committed before this comparison). Features are built with the SAME code the
live shadow uses (forecast/wind_shadow.py: select_run, features), so training
and live construction match by construction for route A; route B's features
come from the previous-runs archive and are used only if the predeclared
equivalence test passes.
Inputs (git-ignored, regeneratable): history/data/gfs_single_runs/runs.parquet
(pull_gfs_single_runs.py), history/data/forecast_test/{surge_hourly,met_obs,
fcst_gfs_seamless}.parquet (pull_surge_forecast_test_data.py).
Run: python3 history/scripts/fit_wind_shadow_c2.py
"""
import datetime as dt, hashlib, json, math, sys, time, urllib.parse, urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from forecast import wind_shadow as ws  # noqa: E402

UTC = dt.timezone.utc
THETA, LATENCY_H, TAU, CAP = 70.0, 6, 36.0, 3.0
LAG_VERIFIED_D = 24          # verified hourly_height end lags issuance (measured 2026-09-24: Aug 31)
MIN_PRESSURE_HOURS = 480
FT = ROOT / "history/data/forecast_test"

sv = pd.read_parquet(FT / "surge_hourly.parquet").set_index("timestamp").asfreq("h")
sv.index = sv.index.tz_localize("UTC")
s = sv.surge_ft                                        # 6-min on the hour: what live readings and outcomes use

# ---- production mean policy (forecast/surge_mean.py): verified hourly_height minus
# predictions, request window = the last 364 calendar days, data present up to the
# verified end; replayed with a fixed LAG_VERIFIED_D for history (assumption).
ver = pd.read_parquet(ROOT / "history/data/sandy_hook_hourly_utc.parquet").set_index("timestamp_utc").sort_index()
vs = ver.surge_ft
csum = vs.fillna(0).cumsum(); ccount = vs.notna().astype(int).cumsum()


def m_prod_at(t):
    start = pd.Timestamp((t - dt.timedelta(days=364)).date(), tz="UTC")
    end = t - dt.timedelta(days=LAG_VERIFIED_D)                      # exclusive
    a = csum.index.searchsorted(start) - 1; b = csum.index.searchsorted(end) - 1
    if b <= a:
        return None
    n = ccount.iloc[b] - (ccount.iloc[a] if a >= 0 else 0)
    if n < 24 * 300:
        return None
    return float((csum.iloc[b] - (csum.iloc[a] if a >= 0 else 0)) / n)

# ---- observed pressure WITH quality flags (hourly product), cached
PF = FT / "pressure_hourly_flags.parquet"
if not PF.exists():
    rows = []
    a = dt.datetime(2026, 2, 1, tzinfo=UTC)
    while a < dt.datetime(2026, 9, 24, tzinfo=UTC):
        b = min(a + dt.timedelta(days=30), dt.datetime(2026, 9, 24, tzinfo=UTC))
        q = {"product": "air_pressure", "station": "8531680", "begin_date": a.strftime("%Y%m%d %H:%M"),
             "end_date": b.strftime("%Y%m%d %H:%M"), "time_zone": "gmt", "units": "metric", "interval": "h",
             "format": "json", "application": "barnacle-research"}
        req = urllib.request.Request("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" + urllib.parse.urlencode(q),
                                     headers={"User-Agent": "barnacle-research (dr.john.urban@gmail.com)"})
        for r in json.load(urllib.request.urlopen(req, timeout=60)).get("data") or []:
            rows.append({"timestamp": pd.Timestamp(r["t"], tz="UTC"), "v": r.get("v"), "f": r.get("f")})
        a = b; time.sleep(0.3)
    pd.DataFrame(rows).drop_duplicates("timestamp").to_parquet(PF, index=False)
pf = pd.read_parquet(PF).set_index("timestamp").sort_index()

# ---- 6-min water level on the hour WITH flags (outcome QC), cached
WF = FT / "water_level_flags.parquet"
if not WF.exists():
    rows = []
    a = dt.datetime(2026, 3, 25, tzinfo=UTC)
    while a < dt.datetime(2026, 9, 24, tzinfo=UTC):
        b = min(a + dt.timedelta(days=30), dt.datetime(2026, 9, 24, tzinfo=UTC))
        q = {"product": "water_level", "station": "8531680", "begin_date": a.strftime("%Y%m%d %H:%M"),
             "end_date": b.strftime("%Y%m%d %H:%M"), "datum": "MLLW", "time_zone": "gmt", "units": "english",
             "format": "json", "application": "barnacle-research"}
        req = urllib.request.Request("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" + urllib.parse.urlencode(q),
                                     headers={"User-Agent": "barnacle-research (dr.john.urban@gmail.com)"})
        for r in json.load(urllib.request.urlopen(req, timeout=90)).get("data") or []:
            if r["t"].endswith(":00"):
                rows.append({"timestamp": pd.Timestamp(r["t"], tz="UTC"), "v": r.get("v"), "f": r.get("f"), "q": r.get("q")})
        a = b; time.sleep(0.3)
    pd.DataFrame(rows).drop_duplicates("timestamp").to_parquet(WF, index=False)
wf = pd.read_parquet(WF).set_index("timestamp").sort_index()


# outcome QC = the evaluator's own classifier (one rule for training and scoring)
import importlib.util as _ilu  # noqa: E402
_spec = _ilu.spec_from_file_location("evaluate_wind_shadow", ROOT / "history/scripts/evaluate_wind_shadow.py")
_evm = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_evm)
_cls = [_evm.classify_water_level({"v": v, "f": f, "q": q}) for v, f, q in zip(wf.v, wf.f, wf.q)]
_ok_rows = pd.Series([c[0] for c in _cls], index=wf.index)
wl_ok = _ok_rows.reindex(sv.index).fillna(False).astype(bool)
wl_v = pd.to_numeric(wf.v, errors="coerce").reindex(sv.index)
_both = wl_v.notna() & sv.observed_mllw.notna()
_reasons = pd.Series([c[1] or "valid" for c in _cls]).str.replace(r" \d+,\d+,\d+,\d+$", "", regex=True)
wl_qc = {"rows_repulled": int(len(wf)), "rows_valid": int(_ok_rows.sum()),
         "invalid_by_reason": {str(k): int(v) for k, v in _reasons[_reasons != "valid"].value_counts().items()},
         "preliminary_valid_with_outlier_count": int(sum(bool(c[0] and c[2].get("outlier_samples")) for c in _cls)),
         "verified_inferred_excluded": int(sum(bool(c[2].get("inferred")) for c in _cls)),
         "value_mismatch_vs_table_gt_0p001ft": int(((wl_v - sv.observed_mllw).abs() > 0.001)[_both].sum()),
         "rows_compared": int(_both.sum()),
         "quality_codes": {str(k): int(v) for k, v in wf["q"].value_counts(dropna=False).items()}}
print("water-level QC re-pull:", json.dumps(wl_qc))


def _ok(v, f):
    try:
        fl = [int(x) for x in str(f).split(",")]
        return len(fl) == 3 and not any(fl) and math.isfinite(float(v))
    except (TypeError, ValueError):
        return False
pvalid = pd.Series([float(v) if _ok(v, f) else np.nan for v, f in zip(pf.v, pf.f)], index=pf.index).reindex(sv.index)
p = pvalid
p_prior_mean = p.rolling(24 * 30, min_periods=MIN_PRESSURE_HOURS).mean().shift(1)     # [t0 - 30 d, t0)
p_anom = p - p_prior_mean

runs = pd.read_parquet(ROOT / "history/data/gfs_single_runs/runs.parquet")
runs["run_init_utc"] = pd.to_datetime(runs.run_init_utc, utc=True); runs["valid_utc"] = pd.to_datetime(runs.valid_utc, utc=True)
by_run = {k: {v.to_pydatetime(): (a, b, c) for v, a, b, c in zip(g.valid_utc, g.wind_kn, g.wind_dir, g.pressure_hpa)}
          for k, g in runs.groupby("run_init_utc")}
by_run = {k.to_pydatetime(): v for k, v in by_run.items()}
fc = pd.read_parquet(FT / "fcst_gfs_seamless.parquet").set_index("timestamp").sort_index()
fc.index = fc.index.tz_localize("UTC") if fc.index.tz is None else fc.index


def feats_single(t, h):
    init = ws.cycle_for(t, LATENCY_H)          # training: 6-h rule (historical availability assumed)
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
m_prod_cache = {t: m_prod_at(t) for t in issuances}
mp_vals = [v for v in m_prod_cache.values() if v is not None]
old_mp = s.rolling(24 * 364, min_periods=24 * 300).mean().shift(24 * 21)                # c1's construction
d_mp = [abs(m_prod_cache[t] - float(old_mp.get(t))) for t in issuances
        if m_prod_cache[t] is not None and old_mp.get(t) is not None and math.isfinite(old_mp.get(t))]
print(f"production-mean replay: n={len(mp_vals)}, range {min(mp_vals):.4f}..{max(mp_vals):.4f} ft; "
      f"vs c1 construction mean |diff| {np.mean(d_mp):.4f}, max {np.max(d_mp):.4f} ft")
coefs, fitinfo, qc_dropped = {}, {}, {}
for h in range(1, 49):
    X, y, base_err, cand_rows = [], [], [], []
    for t in issuances:
        s0, mp, s1 = s.get(t), m_prod_cache.get(t), s.get(t + dt.timedelta(hours=h))
        if s0 is None or mp is None or s1 is None or not all(map(math.isfinite, (s0, mp, s1))):
            continue
        if not bool(wl_ok.get(t + dt.timedelta(hours=h), False)):      # outcome QC (evaluator's rule)
            qc_dropped[h] = qc_dropped.get(h, 0) + 1
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
    fitinfo[str(h)] = {"n": int(len(y)), "outcomes_dropped_by_qc": int(qc_dropped.get(h, 0)), "in_sample_mae_baseline_ft": round(float(np.abs(y).mean()), 4),
                       "in_sample_mae_candidate_ft": round(float(np.abs(y - pred).mean()), 4)}
    if h in (6, 12, 24, 30, 48):
        print(f"lead {h:2d} h: n={len(y)} in-sample MAE baseline {np.abs(y).mean():.3f} -> candidate {np.abs(y - pred).mean():.3f} ft; coef {coefs[str(h)]}")

manifest = {
    "candidate_id": "wind-shadow-c2",
    "supersedes": "wind-shadow-c1 (retired before any official record; see models/wind_shadow/SMOKE_TESTS.md)",
    "created_utc": dt.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "status": "FROZEN for the prospective shadow trial; do not refit; a changed model gets a new id",
    "plan": "history/plans/2026-09-24-wind-term-candidate-plan.md", "design": "models/wind_shadow/DESIGN.md",
    "fit_script": "history/scripts/fit_wind_shadow_c2.py",
    "feed": "Open-Meteo Single Runs API", "model": "gfs_seamless", "resolves_to": "ncep_gfs013",
    "latitude": 40.4669, "longitude": -74.0094, "forecast_hours": 61, "latency_h": LATENCY_H,
    "units": {"wind_speed_10m": "kn", "wind_direction_10m": "deg FROM", "pressure_msl": "hPa",
              "observed_pressure": "hPa (CO-OPS air_pressure, metric)", "surge": "ft"},
    "theta_deg": THETA, "tau_h": TAU, "correction_cap_ft": CAP, "leads_h": [1, 48],
    "beyond_48h": "no correction (baseline)", "requires": "fresh surge reading (<= 60 min) and complete inputs",
    "mean_policy": ("production (forecast/surge_mean.py): verified hourly_height minus predictions over the last 364 "
                    "calendar days as returned (verified data end); training replays it with a fixed verified lag of "
                    f"{LAG_VERIFIED_D} d (measured once, 2026-09-24): an assumption for history"),
    "pressure_policy": ("CO-OPS air_pressure: value at the issuance hour t0 (live: else latest 6-min <= 60 min old, "
                        "labeled); anomaly = value minus the mean of QC-passing hourly values in [t0 - 30 d, t0), "
                        f">= {MIN_PRESSURE_HOURS} of 720 required; QC = all three flags 0 and finite"),
    "targets": "nominal UTC hours t0 + h, t0 = the issuance hour; reading = 6-min value at t0 (live: <= 60 min old)",
    "water_level_qc": ("training outcome must pass the evaluator's classify_water_level (q-aware: preliminary O is a count, verified I=1 is inferred and excluded) from a flagged "
                       "re-pull; the reading mirrors production (no flag QC; production despikes); the mean replays "
                       "production (no flag QC)"),
    "water_level_qc_repull": wl_qc,
    "historical_availability": ("training assumes every cycle was available 6 h after init (one metadata observation: "
                                "5.6 h); live requires confirmation by provider metadata, else fallback"),
    "dataset_sha256": {k: hashlib.sha256((ROOT / v).read_bytes()).hexdigest() for k, v in {
        "gfs_single_runs": "history/data/gfs_single_runs/runs.parquet",
        "surge_6min_on_hour": "history/data/forecast_test/surge_hourly.parquet",
        "verified_hourly_utc": "history/data/sandy_hook_hourly_utc.parquet",
        "pressure_hourly_flags": "history/data/forecast_test/pressure_hourly_flags.parquet",
        "water_level_flags": "history/data/forecast_test/water_level_flags.parquet",
        "previous_runs_gfs": "history/data/forecast_test/fcst_gfs_seamless.parquet"}.items()},
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
