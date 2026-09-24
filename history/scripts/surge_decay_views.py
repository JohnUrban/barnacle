"""Surge decay toward a recent average: choose tau and the averaging window,
scored in three views (all hours; high-tide hours; hours with the bay near
the 3.0-3.52 ft NAVD88 plug band), plus a first test of John's hypothesis
that surge which has ALREADY persisted keeps persisting (2026-09-23).

Forecast of surge at t+k from the reading at t:
    mean_t + (s_t - mean_t) * exp(-k / tau)
mean_t is computed only from data before t (no look-ahead).
Read-only; pandas + pyarrow. Run: python3 history/scripts/surge_decay_views.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MLLW_TO_NAVD88 = -2.82
df = pd.read_parquet(ROOT / "history/data/sandy_hook_hourly_history.parquet",
                     columns=["timestamp", "surge_ft", "predicted_mllw", "observed_mllw"])
df = df[df.timestamp >= "2005-01-01"].set_index("timestamp").asfreq("h")
s = df.surge_ft
means = {
    "zero": pd.Series(0.0, index=s.index),
    "trailing 30 d": s.rolling(24 * 30, min_periods=24 * 20).mean().shift(1),
    "trailing 365 d": s.rolling(24 * 365, min_periods=24 * 300).mean().shift(1),
}
keep = s.index >= "2006-01-01"
S = s.values
pred = df.predicted_mllw.values
obs_navd = df.observed_mllw.values + MLLW_TO_NAVD88
# high tides: local maxima of the astronomical prediction
hi = np.zeros(len(pred), bool)
hi[1:-1] = (pred[1:-1] > pred[:-2]) & (pred[1:-1] >= pred[2:])
lo = np.zeros(len(pred), bool)            # astronomical low tides (review 2026-09-24-a1 R6)
lo[1:-1] = (pred[1:-1] < pred[:-2]) & (pred[1:-1] <= pred[2:])
LAGS = [3, 6, 12, 24, 30, 48]
TAUS = [12, 24, 36, 48, 72, 96, 1e9]      # 1e9 = constant (no decay)


def score(target_mask, start_mask=None, label=""):
    print(f"\n== {label}")
    for mname, mser in means.items():
        M = mser.values
        line = []
        for k in LAGS:
            a, b, m = S[:-k], S[k:], M[:-k]
            ok = np.isfinite(a) & np.isfinite(b) & np.isfinite(m) & keep[:-k] & target_mask[k:]
            if start_mask is not None:
                ok &= start_mask[:-k]
            errs = {t: np.abs(b[ok] - (m[ok] + (a[ok] - m[ok]) * np.exp(-k / t))).mean() for t in TAUS}
            best = min(errs, key=errs.get)
            line.append(f"{k}h: best tau {'const' if best > 1e8 else int(best)} {errs[best]:.3f} (const {errs[1e9]:.3f}, tau48 {errs[48]:.3f})")
        print(f"  toward {mname:15s} " + " | ".join(line))


allmask = np.ones(len(S), bool)
plug = (obs_navd >= 2.5) & (obs_navd <= 3.8)    # the bay near the plug band (margin 0.5 ft)
storm = S >= 1.0
score(allmask, None, "VIEW 1 all hours (curve + rain tank)")
score(hi, None, "VIEW 2 high-tide hours (per-tide peaks)")
score(plug, None, "VIEW 3 target hours with the bay near the plug band (2.5-3.8 ft NAVD88)")
score(lo, None, "VIEW 4 low-tide hours (astronomical lows)")
score(allmask, storm, "storm starts (reading >= +1 ft), all target hours")
# John's hypothesis: surge that has already persisted keeps persisting
roll_min = pd.Series(S).rolling(24, min_periods=20).min().values     # lowest surge over the prior 24 h
fresh_spike = storm & (roll_min < 0.5)          # elevated now, was not elevated within the last day
persisting = storm & (roll_min >= 1.0)           # elevated for at least the whole last day
score(allmask, fresh_spike, "storm starts that ROSE within the last 24 h")
score(allmask, persisting, "storm starts ALREADY elevated >= +1 ft for 24 h")
