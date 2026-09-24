"""Independent round-2 review. No network or production imports/writes.
Run with pandas/numpy/pyarrow; stdout is the review JSON.
Target-time masks, purged training boundary, exploratory low-tide/month views.
The original reports remain immutable. Extra cuts are post-hoc diagnostics.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'history/data/forecast_test'
files = sorted(DATA.glob('*.parquet'))
result = {'inputs': {}, 'results': []}
for p in files:
    d = pd.read_parquet(p)
    result['inputs'][p.name] = dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        rows=len(d), duplicate_times=int(d.timestamp.duplicated().sum()),
        first=str(d.timestamp.min()), last=str(d.timestamp.max()),
        missing={c: int(d[c].isna().sum()) for c in d.columns})
a = pd.read_parquet(DATA/'surge_hourly.parquet').set_index('timestamp').asfreq('h')
p = pd.read_parquet(DATA/'met_obs.parquet').set_index('timestamp').reindex(a.index).pressure_mb
s = a.surge_ft
mean = s.rolling(8760, min_periods=7200).mean().shift(1).to_numpy()
idx = a.index
train = (idx >= '2024-02-01') & (idx < '2025-05-01')
test = (idx >= '2025-05-01') & (idx < '2026-09-21')
astro = a.predicted_mllw
high = (astro > astro.shift(1)) & (astro >= astro.shift(-1))
low = (astro < astro.shift(1)) & (astro <= astro.shift(-1))
plug = (a.observed_mllw - 2.82).between(2.5, 3.8)
pa = p - p.rolling(720, min_periods=480).mean().shift(1)
for source in ('gfs_seamless', 'ecmwf_ifs025'):
    fc = pd.read_parquet(DATA/f'fcst_{source}.parquet').set_index('timestamp').reindex(idx)
    for k in (6, 12, 24, 30, 48):
        day = 1 if k <= 24 else 2
        speed = fc[f'wind_speed_10m_previous_day{day}'].to_numpy()
        direction = fc[f'wind_direction_10m_previous_day{day}'].to_numpy()
        stress = speed**2 * np.cos(np.deg2rad(direction-70))
        # Explicit forward windows, independent of the study's rolling/shift helper.
        w = np.full(len(s), np.nan)
        for i in range(len(s)-k):
            vals = stress[i+1:i+k+1]
            if np.isfinite(vals).sum() >= int(.75*k):
                w[i] = np.nanmean(vals)
        pressure = fc[f'pressure_msl_previous_day{day}'].shift(-k) - p
        X = np.column_stack([w, pressure, pa, np.ones(len(s))])
        base = mean + (s.to_numpy()-mean)*np.exp(-k/36)
        target = s.shift(-k).to_numpy()
        good = np.isfinite(X).all(axis=1) & np.isfinite(target) & np.isfinite(base)
        fit_original = train & good
        fit_purged = fit_original & (idx+pd.Timedelta(hours=k) < pd.Timestamp('2025-05-01'))
        score = test & np.isfinite(target) & np.isfinite(base)
        forecasts = {}
        for name, fit in [('original',fit_original), ('purged',fit_purged)]:
            beta = np.linalg.lstsq(X[fit], (target-base)[fit], rcond=None)[0]
            pred = base + X@beta
            forecasts[name] = np.where(np.isfinite(pred), pred, base)
        masks = {'all': np.ones(len(s),bool), 'storm_start': (s>=1).to_numpy(),
                 'high_issuance': high.to_numpy(), 'plug_issuance': plug.to_numpy(),
                 'high_target': high.shift(-k,fill_value=False).to_numpy(),
                 'low_target': low.shift(-k,fill_value=False).to_numpy(),
                 'plug_target': plug.shift(-k,fill_value=False).to_numpy()}
        row = dict(source=source, lead=k, training_rows=int(fit_original.sum()),
                   purged_rows=int((fit_original & ~fit_purged).sum()),
                   forecast_missing_fraction=float((~np.isfinite(X[score]).all(axis=1)).mean()), views={})
        for name, mask in masks.items():
            take = score & mask
            stats = {'n':int(take.sum()),'baseline_mae':float(np.abs(target[take]-base[take]).mean())}
            for model, pred in forecasts.items():
                stats[model+'_mae'] = float(np.abs(target[take]-pred[take]).mean())
            row['views'][name] = stats
        if k in (24,30):
            error = np.abs(target-base)-np.abs(target-forecasts['purged'])
            scored = pd.DataFrame({'gain':error[score], 'storm':(s.to_numpy()[score]>=1)},index=idx[score])
            row['monthly_gain_ft'] = {str(t.date()):float(g.gain.mean()) for t,g in scored.groupby(pd.Grouper(freq='MS'))}
            # One-week resampling blocks preserves nearby hourly dependence;
            # exploratory uncertainty only, not a count of independent storms.
            block = ((scored.index-scored.index[0]).total_seconds()//(7*86400)).astype(int)
            row['block_bootstrap'] = {}
            for name, sub in [('all',scored),('storm_start',scored[scored.storm])]:
                b = block if name=='all' else block[scored.storm]
                sums = sub.groupby(b).gain.agg(['sum','count']).to_numpy()
                rng = np.random.default_rng(240924)
                samples = rng.integers(0,len(sums),size=(2000,len(sums)))
                gains = sums[samples,0].sum(axis=1)/sums[samples,1].sum(axis=1)
                row['block_bootstrap'][name] = dict(blocks=len(sums), gain_ft=float(sub.gain.mean()),
                    exploratory_95pct=np.quantile(gains,[.025,.975]).tolist())
        result['results'].append(row)
print(json.dumps(result,indent=2,allow_nan=False))
