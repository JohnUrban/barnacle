"""Round 1 of the surge-forcing research, CORRECTED (r2) per audit
2026-09-24-a2 (Codex). Differences from the original surge_forcing_research.py
(kept unchanged for reproducibility):
  R1  water from the canonical UTC table (sandy_hook_hourly_utc.parquet, pulled
      with time_zone=gmt) joined to the UTC meteorology; the original joined
      naive station-local water to UTC weather (4-5 h misalignment).
  R3  a training row needs BOTH its issuance and its target before the split.
  Views are at the TARGET hour (as before) plus low tides; row counts printed.
Deviations from the written plan (history/plans/2026-09-23-surge-forcing-research.md),
stated rather than hidden: M2 uses wind terciles only (the planned pressure
classes were not implemented); M3 adds a pressure-anomaly term and an intercept
to the planned wind stress + pressure change. The plan's predeclaration
timing is UNVERIFIED (see the plan's erratum); treat this as exploratory.
Fit issuances 2006-2015 with targets < 2016-01-01; score issuances 2016-01-01
.. 2026-05-17. Read-only. Run: python3 history/scripts/surge_forcing_research_r2.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MLLW_TO_NAVD88 = -2.82
TAU0 = 36.0
LEADS = [6, 12, 24, 30, 48]
TAU_GRID = [6, 12, 18, 24, 36, 48, 72, 96, 144, 1e9]

h = pd.read_parquet(ROOT / "history/data/sandy_hook_hourly_utc.parquet",
                    columns=["timestamp_utc", "surge_ft", "predicted_mllw", "observed_mllw"])
h = h.set_index("timestamp_utc").sort_index()
assert str(h.index.tz) == "UTC"
h = h[h.index >= pd.Timestamp("2005-01-01", tz="UTC")].asfreq("h")
met = pd.read_parquet(ROOT / "history/data/sandy_hook_met_hourly.parquet").set_index("timestamp").sort_index()
met.index = met.index.tz_localize("UTC")          # pulled with time_zone=gmt: naive UTC labels
met = met[~met.index.duplicated()].reindex(h.index)
df = h.join(met)
s = df.surge_ft
m = s.rolling(24 * 365, min_periods=24 * 300).mean().shift(1)          # no look-ahead
spd = df.wind_speed_kn
dirn = np.deg2rad(df.wind_dir_deg)
p = df.pressure_mb
idx = df.index
SPLIT = pd.Timestamp("2016-01-01", tz="UTC")
train = (idx >= pd.Timestamp("2006-01-01", tz="UTC")) & (idx < SPLIT)
test = idx >= SPLIT
pred = df.predicted_mllw.values
hi = np.zeros(len(pred), bool)
hi[1:-1] = (pred[1:-1] > pred[:-2]) & (pred[1:-1] >= pred[2:])
lo_t = np.zeros(len(pred), bool)
lo_t[1:-1] = (pred[1:-1] < pred[:-2]) & (pred[1:-1] <= pred[2:])
obs_navd = df.observed_mllw.values + MLLW_TO_NAVD88
plug = (obs_navd >= 2.5) & (obs_navd <= 3.8)

print(f"hours {len(df)}; wind valid {spd.notna().mean():.1%}; pressure valid {p.notna().mean():.1%}; "
      f"test-decade wind valid {spd[test].notna().mean():.1%}, pressure {p[test].notna().mean():.1%}")


def stress(theta_deg):
    """Wind-stress proxy along the direction the wind comes FROM = theta."""
    return spd * spd.abs() * np.cos(dirn - np.deg2rad(theta_deg))


# theta*: direction whose past-12-h stress best correlates with surge (training decade only)
cors = {}
for th in range(0, 360, 10):
    w = stress(th).rolling(12, min_periods=9).mean()
    ok = train & w.notna().values & s.notna().values
    cors[th] = np.corrcoef(w[ok], s[ok])[0, 1]
theta = max(cors, key=cors.get)
print(f"theta* (training decade) = {theta} deg FROM (corr {cors[theta]:.3f}); "
      f"prior NE-E 45-90; corr at 45: {cors[40]:.3f}/{cors[50]:.3f}, at 90: {cors[90]:.3f}, at 225: {cors[220]:.3f}")
W = stress(theta)
W_past = W.rolling(12, min_periods=9).mean()
dP_past = p - p.shift(12)
P_anom = p - p.rolling(24 * 30, min_periods=24 * 20).mean().shift(1)

S = s.values
M = m.values


def m1(k, tau=TAU0):
    a = S[:-k]; mm = M[:-k]
    return mm + (a - mm) * np.exp(-k / tau)


views = {"all hours": np.ones(len(S), bool), "high tides": hi, "low tides": lo_t, "plug band": plug}
results = []


def score(name, k, fcst, fallback):
    """MAE on the TEST decade; rows without the model's features use M1."""
    b = S[k:]
    f = np.where(np.isfinite(fcst), fcst, fallback)
    base_ok = np.isfinite(b) & np.isfinite(fallback) & test[:-k]
    row = {"model": name, "lead": k, "features_missing": float(np.mean(~np.isfinite(fcst[base_ok])))}
    for vname, vmask in views.items():
        ok = base_ok & vmask[k:]                     # views at the TARGET hour
        row[vname] = np.abs(b[ok] - f[ok]).mean()
    ok = base_ok & (S[:-k] >= 1.0)                   # storm starts at ISSUANCE
    row["storm starts"] = np.abs(b[ok] - f[ok]).mean()
    row["n all"] = int(base_ok.sum()); row["n storm"] = int(ok.sum())
    results.append(row)


for k in LEADS:
    tr_k = train[:-k] & (idx[k:] < SPLIT)           # R3: issuance AND target before the split
    base = m1(k)
    a = S[:-k]; mm = M[:-k]
    score("M0 constant", k, a.copy(), base)
    score("M1 decay tau36 (baseline)", k, base, base)
    W_fut = W.rolling(k, min_periods=int(0.75 * k)).mean().shift(-k).values[:-k]
    dP_fut = (p.shift(-k) - p).values[:-k]
    for label, feat in (("A past wind", W_past.values[:-k]), ("B future wind", W_fut)):
        # M2: tau per wind tercile, fitted on the training decade
        q = np.nanquantile(feat[tr_k], [1 / 3, 2 / 3])
        cls = np.where(np.isfinite(feat), np.digitize(feat, q), -1)
        f = np.full(len(a), np.nan)
        taus = []
        for c in (0, 1, 2):
            sel_tr = (cls == c) & tr_k & np.isfinite(a) & np.isfinite(mm) & np.isfinite(S[k:])
            best = min(TAU_GRID, key=lambda t: np.abs(S[k:][sel_tr] - (mm[sel_tr] + (a[sel_tr] - mm[sel_tr]) * np.exp(-k / t))).mean())
            taus.append("const" if best > 1e8 else int(best))
            sel = cls == c
            f[sel] = mm[sel] + (a[sel] - mm[sel]) * np.exp(-k / best)
        score(f"M2 {label}: tau by tercile {taus}", k, f, base)
    # M3: additive forcing on M1's residual (least squares, training decade)
    for label, X in (("A past wind+pressure", np.column_stack([W_past.values[:-k], dP_past.values[:-k], P_anom.values[:-k]])),
                     ("B future wind+pressure", np.column_stack([W_fut, dP_fut, P_anom.values[:-k]]))):
        r = S[k:] - base
        ok = tr_k & np.isfinite(r) & np.all(np.isfinite(X), axis=1)
        Xd = np.column_stack([X, np.ones(len(X))])
        beta, *_ = np.linalg.lstsq(Xd[ok], r[ok], rcond=None)
        f = base + Xd @ beta
        score(f"M3 {label}: coef {np.round(beta[:-1], 4).tolist()}", k, f, base)

out = pd.DataFrame(results)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 70)
for k in LEADS:
    print(f"\n=== lead {k} h (MAE ft, held-out 2016-2026) ===")
    print(out[out.lead == k].drop(columns="lead").round(3).to_string(index=False))
