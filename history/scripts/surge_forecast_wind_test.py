"""Round 2 of the surge forcing research: archived FORECAST wind at the
matching lead (plan: history/plans/2026-09-23-surge-forcing-research.md,
"Round 2 plan"). Read-only. Needs pull_surge_forecast_test_data.py output
and round 1's data (sandy_hook_hourly_history.parquet, sandy_hook_met_hourly.parquet).
Run: python3 history/scripts/surge_forecast_wind_test.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FT = ROOT / "history/data/forecast_test"
MLLW_TO_NAVD88 = -2.82
TAU0, THETA = 36.0, 70.0
LEADS = [6, 12, 24, 30, 48]
FIT = ("2024-02-01", "2025-05-01")
SCORE = ("2025-05-01", "2026-09-21")


def stress(spd, dir_deg):
    return spd * spd.abs() * np.cos(np.deg2rad(dir_deg) - np.deg2rad(THETA))


def features(s, p_obs, W_obs, Wf, pf, k):
    """Row t: [mean stress over (t, t+k], pressure change to t+k, pressure anomaly at t]."""
    Wm = Wf.rolling(k, min_periods=int(0.75 * k)).mean().shift(-k)
    dP = pf.shift(-k) - p_obs
    Pa = p_obs - p_obs.rolling(24 * 30, min_periods=24 * 20).mean().shift(1)
    return np.column_stack([Wm.values, dP.values, Pa.values])


# ---- round-1 coefficients on 2006-2015 OBSERVED wind (for the transfer model)
h = pd.read_parquet(ROOT / "history/data/sandy_hook_hourly_history.parquet", columns=["timestamp", "surge_ft"])
h = h[h.timestamp >= "2005-01-01"].set_index("timestamp").asfreq("h")
met = pd.read_parquet(ROOT / "history/data/sandy_hook_met_hourly.parquet").set_index("timestamp").sort_index()
met = met[~met.index.duplicated()].reindex(h.index)
s1 = h.surge_ft; m1 = s1.rolling(24 * 365, min_periods=24 * 300).mean().shift(1)
W1 = stress(met.wind_speed_kn, met.wind_dir_deg); p1 = met.pressure_mb
tr1 = (h.index >= "2006-01-01") & (h.index < "2016-01-01")
transfer = {}
for k in LEADS:
    base = (m1 + (s1 - m1) * np.exp(-k / TAU0)).values
    X = features(s1, p1, W1, W1, p1, k)
    r = s1.shift(-k).values - base
    ok = tr1 & np.isfinite(r) & np.all(np.isfinite(X), axis=1)
    Xd = np.column_stack([X, np.ones(len(X))])
    transfer[k] = np.linalg.lstsq(Xd[ok], r[ok], rcond=None)[0]

# ---- the forecast-era data
sv = pd.read_parquet(FT / "surge_hourly.parquet").set_index("timestamp").asfreq("h")
mo = pd.read_parquet(FT / "met_obs.parquet").set_index("timestamp").sort_index()
mo = mo[~mo.index.duplicated()].reindex(sv.index)
s = sv.surge_ft
m = s.rolling(24 * 365, min_periods=24 * 300).mean().shift(1)
W_obs = stress(mo.wind_speed_kn, mo.wind_dir_deg); p_obs = mo.pressure_mb
idx = sv.index
fit = (idx >= FIT[0]) & (idx < FIT[1])
score = (idx >= SCORE[0]) & (idx < SCORE[1])
pred = sv.predicted_mllw.values
hi = np.zeros(len(pred), bool); hi[1:-1] = (pred[1:-1] > pred[:-2]) & (pred[1:-1] >= pred[2:])
obs_navd = sv.observed_mllw.values + MLLW_TO_NAVD88
plug = (obs_navd >= 2.5) & (obs_navd <= 3.8)
print(f"surge hours {s.notna().sum()} ({idx.min().date()}..{idx.max().date()}); "
      f"obs wind valid in scored period {mo.wind_speed_kn[score].notna().mean():.1%}, pressure {p_obs[score].notna().mean():.1%}")

rows = []
for model in ("gfs_seamless", "ecmwf_ifs025"):
    fc = pd.read_parquet(FT / f"fcst_{model}.parquet").set_index("timestamp").sort_index()
    fc = fc[~fc.index.duplicated()].reindex(idx)
    for k in LEADS:
        d = 1 if k <= 24 else 2
        Wf = stress(fc[f"wind_speed_10m_previous_day{d}"], fc[f"wind_direction_10m_previous_day{d}"])
        pf = fc[f"pressure_msl_previous_day{d}"]
        S, M = s.values, m.values
        base = M + (S - M) * np.exp(-k / TAU0)
        target = s.shift(-k).values
        cands = {"M1 decay tau36": base}
        Xo = features(s, p_obs, W_obs, W_obs, p_obs, k)
        Xf = features(s, p_obs, W_obs, Wf, pf, k)
        for name, X in (("M3-obs (upper bound)", Xo), ("M3-fcst-refit", Xf)):
            r = target - base
            ok = fit & np.isfinite(r) & np.isfinite(base) & np.all(np.isfinite(X), axis=1)
            Xd = np.column_stack([X, np.ones(len(X))])
            beta = np.linalg.lstsq(Xd[ok], r[ok], rcond=None)[0]
            cands[name] = base + Xd @ beta
        Xd = np.column_stack([Xf, np.ones(len(Xf))])
        cands["M3-fcst-transfer"] = base + Xd @ transfer[k]
        valid = score & np.isfinite(target) & np.isfinite(base)
        for name, f in cands.items():
            f = np.where(np.isfinite(f), f, base)          # missing features -> M1
            row = {"source": model, "lead": k, "model": name}
            for vname, vm in (("all hours", np.ones(len(S), bool)), ("high tides", hi), ("plug band", plug),
                              ("storm starts", S >= 1.0)):
                sel = valid & vm
                row[vname] = np.abs(target[sel] - f[sel]).mean()
            row["n storm"] = int((valid & (S >= 1.0)).sum())
            row["fcst features missing"] = float(np.mean(~np.all(np.isfinite(Xf[valid]), axis=1)))
            rows.append(row)

out = pd.DataFrame(rows)
pd.set_option("display.width", 220)
for model in ("gfs_seamless", "ecmwf_ifs025"):
    for k in LEADS:
        sub = out[(out.source == model) & (out.lead == k)].drop(columns=["source", "lead"])
        print(f"\n=== {model}, lead {k} h (MAE ft, scored {SCORE[0]}..{SCORE[1]}) ===")
        print(sub.round(3).to_string(index=False))
