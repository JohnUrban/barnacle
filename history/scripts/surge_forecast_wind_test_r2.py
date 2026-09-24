"""Round 2 of the surge-forcing research, CORRECTED (r2) per audit
2026-09-24-a2 (Codex). The original surge_forecast_wind_test.py is kept.
  R1  the transferred coefficients are refit on the canonical UTC water table
      (the original used naive station-local water against UTC weather).
  R2  high-tide, LOW-tide and plug-band views are evaluated at the TARGET hour
      t+k (the original masked the issuance hour t); storm starts stay at t.
  R3  a fitting row needs both issuance and target before the split, for the
      refit and the transfer fit.
  R4  wording: previous_day1/2 values are chosen by VALID time; for a 24-h
      window starting at issuance t their nominal ages at t run from ~23 h to
      ~0 h (day1), for 24-48 h windows ~47 h to ~18 h (day2); cached values do
      not prove publication/retrieval availability at t. "M3-obs" is an ORACLE
      benchmark (observed future forcing), not an upper bound on forecast skill.
Scored period = ISSUANCES 2025-05-01 up to (not including) 2026-09-21; targets
may fall after that. Exploratory (predeclaration timing unverified; see the
plan's erratum). Run: python3 history/scripts/surge_forecast_wind_test_r2.py
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
h = pd.read_parquet(ROOT / "history/data/sandy_hook_hourly_utc.parquet", columns=["timestamp_utc", "surge_ft"])
h = h.set_index("timestamp_utc").sort_index()
assert str(h.index.tz) == "UTC"
h = h[h.index >= pd.Timestamp("2005-01-01", tz="UTC")].asfreq("h")
met = pd.read_parquet(ROOT / "history/data/sandy_hook_met_hourly.parquet").set_index("timestamp").sort_index()
met.index = met.index.tz_localize("UTC")
met = met[~met.index.duplicated()].reindex(h.index)
s1 = h.surge_ft; m1 = s1.rolling(24 * 365, min_periods=24 * 300).mean().shift(1)
W1 = stress(met.wind_speed_kn, met.wind_dir_deg); p1 = met.pressure_mb
SPLIT1 = pd.Timestamp("2016-01-01", tz="UTC")
tr1 = (h.index >= pd.Timestamp("2006-01-01", tz="UTC")) & (h.index < SPLIT1)
transfer = {}
for k in LEADS:
    base = (m1 + (s1 - m1) * np.exp(-k / TAU0)).values
    X = features(s1, p1, W1, W1, p1, k)
    r = s1.shift(-k).values - base
    tgt_before = np.zeros(len(r), bool); tgt_before[:-k] = h.index[k:] < SPLIT1      # R3 purge
    ok = tr1 & tgt_before & np.isfinite(r) & np.all(np.isfinite(X), axis=1)
    Xd = np.column_stack([X, np.ones(len(X))])
    transfer[k] = np.linalg.lstsq(Xd[ok], r[ok], rcond=None)[0]

# ---- the forecast-era data
sv = pd.read_parquet(FT / "surge_hourly.parquet").set_index("timestamp").asfreq("h")
sv.index = sv.index.tz_localize("UTC")                                 # pulled with time_zone=gmt
mo = pd.read_parquet(FT / "met_obs.parquet").set_index("timestamp").sort_index()
mo.index = mo.index.tz_localize("UTC")
mo = mo[~mo.index.duplicated()].reindex(sv.index)
s = sv.surge_ft
m = s.rolling(24 * 365, min_periods=24 * 300).mean().shift(1)
W_obs = stress(mo.wind_speed_kn, mo.wind_dir_deg); p_obs = mo.pressure_mb
idx = sv.index
FIT_END = pd.Timestamp(FIT[1], tz="UTC")
fit = (idx >= pd.Timestamp(FIT[0], tz="UTC")) & (idx < FIT_END)
score = (idx >= pd.Timestamp(SCORE[0], tz="UTC")) & (idx < pd.Timestamp(SCORE[1], tz="UTC"))
pred = sv.predicted_mllw.values
hi = np.zeros(len(pred), bool); hi[1:-1] = (pred[1:-1] > pred[:-2]) & (pred[1:-1] >= pred[2:])
lo_t = np.zeros(len(pred), bool); lo_t[1:-1] = (pred[1:-1] < pred[:-2]) & (pred[1:-1] <= pred[2:])


def at_target(mask, k):
    """R2: the mask evaluated at t+k, aligned to issuance rows t."""
    out = np.zeros(len(mask), bool); out[:-k] = mask[k:]
    return out
obs_navd = sv.observed_mllw.values + MLLW_TO_NAVD88
plug = (obs_navd >= 2.5) & (obs_navd <= 3.8)
print(f"surge hours {s.notna().sum()} ({idx.min().date()}..{idx.max().date()}); "
      f"obs wind valid in scored period {mo.wind_speed_kn[score].notna().mean():.1%}, pressure {p_obs[score].notna().mean():.1%}")

rows = []
for model in ("gfs_seamless", "ecmwf_ifs025"):
    fc = pd.read_parquet(FT / f"fcst_{model}.parquet").set_index("timestamp").sort_index()
    fc.index = fc.index.tz_localize("UTC") if fc.index.tz is None else fc.index
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
        for name, X in (("M3-obs (oracle: observed future forcing)", Xo), ("M3-fcst-refit", Xf)):
            r = target - base
            tgt_ok = np.zeros(len(r), bool); tgt_ok[:-k] = idx[k:] < FIT_END              # R3 purge
            ok = fit & tgt_ok & np.isfinite(r) & np.isfinite(base) & np.all(np.isfinite(X), axis=1)
            Xd = np.column_stack([X, np.ones(len(X))])
            beta = np.linalg.lstsq(Xd[ok], r[ok], rcond=None)[0]
            cands[name] = base + Xd @ beta
        Xd = np.column_stack([Xf, np.ones(len(Xf))])
        cands["M3-fcst-transfer"] = base + Xd @ transfer[k]
        valid = score & np.isfinite(target) & np.isfinite(base)
        for name, f in cands.items():
            f = np.where(np.isfinite(f), f, base)          # missing features -> M1
            row = {"source": model, "lead": k, "model": name}
            for vname, vm in (("all hours", np.ones(len(S), bool)), ("high tide @target", at_target(hi, k)),
                              ("low tide @target", at_target(lo_t, k)), ("plug band @target", at_target(plug, k)),
                              ("storm starts @issuance", S >= 1.0)):
                sel = valid & vm
                row[vname] = np.abs(target[sel] - f[sel]).mean()
            row["n all"] = int(valid.sum()); row["n storm"] = int((valid & (S >= 1.0)).sum())
            row["n plug@t+k"] = int((valid & at_target(plug, k)).sum())
            row["fcst features missing"] = float(np.mean(~np.all(np.isfinite(Xf[valid]), axis=1)))
            rows.append(row)

out = pd.DataFrame(rows)
pd.set_option("display.width", 220)
for model in ("gfs_seamless", "ecmwf_ifs025"):
    for k in LEADS:
        sub = out[(out.source == model) & (out.lead == k)].drop(columns=["source", "lead"])
        print(f"\n=== {model}, lead {k} h (MAE ft, issuances {SCORE[0]} up to, not incl., {SCORE[1]}) ===")
        print(sub.round(3).to_string(index=False))
