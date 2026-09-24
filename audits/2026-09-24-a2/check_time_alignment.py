"""Diagnose legacy local/UTC join and rerun round1 with UTC-aligned water.
Read-only sensitivity run of the original study, NOT an independent model
implementation or new holdout. The naive legacy archive cannot recover both
fall-back folds. Use the project's explicit fold=0 convention; discard
nonexistent local rows and retain resulting missing UTC hours.
"""
from pathlib import Path
import json
import sys
import datetime as dt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from forecast.station_time import parse_station_local_time
h = pd.read_parquet(ROOT/'history/data/sandy_hook_hourly_history.parquet').set_index('timestamp')
f = pd.read_parquet(ROOT/'history/data/forecast_test/surge_hourly.parquet').set_index('timestamp')
for hours in (0,4,5):
    shifted=h[['predicted_mllw']].copy()
    shifted.index += pd.Timedelta(hours=hours)
    j=shifted.join(f[['predicted_mllw']],lsuffix='_old',rsuffix='_utc').dropna()
    error=(j.predicted_mllw_old-j.predicted_mllw_utc).abs()
    print(json.dumps({'shift_hours':hours,'january_mae_ft':error[j.index.month==1].mean(),
                      'july_mae_ft':error[j.index.month==7].mean()}))
script=ROOT/'history/scripts/surge_forcing_research.py'
source=script.read_text()
anchor='h = h[h.timestamp >= "2005-01-01"].set_index("timestamp").asfreq("h")'
assert source.count(anchor)==1
replace='''h = h[h.timestamp >= "2005-01-01"].copy()
from forecast.station_time import parse_station_local_time
import datetime as dt
def legacy_utc(value):
    local = parse_station_local_time(value.to_pydatetime())
    utc = local.astimezone(dt.timezone.utc)
    if utc.astimezone(local.tzinfo).replace(tzinfo=None) != value.to_pydatetime():
        return pd.NaT
    return utc.replace(tzinfo=None)
h["timestamp"] = h.timestamp.map(legacy_utc)
h = h.dropna(subset=["timestamp"]).set_index("timestamp").sort_index().asfreq("h")'''
source=source.replace(anchor,replace)
# Purge cross-boundary outcomes for each lead without changing the split dates.
for old,new in [
 ('feat[train[:-k]]','feat[train[:-k] & (idx[k:] < "2016-01-01")]'),
 ('(cls == c) & train[:-k] &','(cls == c) & train[:-k] & (idx[k:] < "2016-01-01") &'),
 ('ok = train[:-k] & np.isfinite(r)','ok = train[:-k] & (idx[k:] < "2016-01-01") & np.isfinite(r)')]:
    assert source.count(old)==1,old
    source=source.replace(old,new)
exec(compile(source,str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
