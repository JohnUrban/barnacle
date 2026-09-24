"""How long does a stale Sandy Hook surge reading stay useful? (2026-09-23)

For each lag k hours after the last reading, MAE (ft) of predicting the
surge (observed minus NOAA astronomical) at t+k from the reading at t:
zero, constant, exponential decay toward zero, decay toward the recent
mean surge. All hours and storm cases (last reading >= +1 / +2 ft), 2006+.
Read-only; needs pandas + pyarrow. Run: python3 history/scripts/surge_persistence_decay.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
df = pd.read_parquet(ROOT / "history/data/sandy_hook_hourly_history.parquet", columns=["timestamp", "surge_ft"])
df = df[df.timestamp >= "2006-01-01"].set_index("timestamp").asfreq("h")
s = df.surge_ft.values
m = float(np.nanmean(s))
print(f"hours {len(s)}, mean surge since 2006 {m:.3f} ft")
LAGS = [1, 2, 3, 6, 9, 12, 18, 24, 36, 48, 72]
TAUS = [12, 24, 48, 96]
for name, cond in (("all hours", lambda a: np.ones_like(a, bool)),
                   ("last reading >= +1.0 ft", lambda a: a >= 1.0),
                   ("last reading >= +2.0 ft", lambda a: a >= 2.0)):
    print(f"\n== {name}\nlag n zero constant " + " ".join(f"decay0_tau{t}" for t in TAUS) + " decayMean_tau24 decayMean_tau48")
    for k in LAGS:
        a, b = s[:-k], s[k:]
        ok = np.isfinite(a) & np.isfinite(b) & cond(a)
        a, b = a[ok], b[ok]
        row = [np.abs(b).mean(), np.abs(b - a).mean()]
        row += [np.abs(b - a * np.exp(-k / t)).mean() for t in TAUS]
        row += [np.abs(b - (m + (a - m) * np.exp(-k / t))).mean() for t in (24, 48)]
        print(f"{k} {ok.sum()} " + " ".join(f"{v:.3f}" for v in row))
