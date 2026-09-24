"""Read-only verification of Claude 142907573 and round03 doc clarifications.
Run from any directory with numpy/pandas/pyarrow. Outputs JSON to stdout.
Original report headers are provenance, not part of their scripts' output.
"""
import contextlib, io, runpy, json, hashlib, subprocess, os
from pathlib import Path
import pandas as pd
import numpy as np
root=Path(__file__).resolve().parents[2]; os.chdir(root); out={"reviewed_commit":"1429075730f68d4de8ad2c48fafdbfa6a1a66c3c"}
for script,report in [
 ('surge_forcing_research_r2.py','2026-09-24-surge-forcing-r2-results.txt'),
 ('surge_forecast_wind_test_r2.py','2026-09-24-surge-forecast-wind-r2-results.txt'),
 ('surge_decay_views_utc.py','2026-09-24-surge-decay-views-utc.txt')]:
 buf=io.StringIO()
 with contextlib.redirect_stdout(buf): ns=runpy.run_path(str(root/'history/scripts'/script))
 expected=(root/'history/reports'/report).read_text()
 body=expected[expected.index('\n\n')+2:] if expected.startswith('# Generated') else expected
 assert body==buf.getvalue(),report
 out[script]={'report_body_exact_match':True}
 if script=='surge_forecast_wind_test_r2.py': r2=ns
h=pd.read_parquet('history/data/sandy_hook_hourly_utc.parquet').set_index('timestamp_utc')
assert str(h.index.tz)=='UTC' and h.index.is_unique
assert (h.index.to_series().diff().dropna()==pd.Timedelta(hours=1)).all()
f=pd.read_parquet('history/data/forecast_test/surge_hourly.parquet').set_index('timestamp')
f.index=f.index.tz_localize('UTC')
j=h[['predicted_mllw']].join(f[['predicted_mllw']],lsuffix='_h',rsuffix='_f').dropna()
assert (j.predicted_mllw_h-j.predicted_mllw_f).abs().max()==0
out['utc_water']={'rows':len(h),'valid_surge':int(h.surge_ft.notna().sum()),'timezone':str(h.index.tz),'unique_regular_hourly':True,'paired_forecast_era_predictions':len(j),'prediction_max_difference_ft':0.0,'flag_values':h.obs_flags.value_counts(dropna=False).astype(int).to_dict()}
# Compare author results against the previously independent forward-window implementation.
prior=json.loads(Path('audits/2026-09-24-a2/recomputed.json').read_text())
diffs=[]
for row in prior['results']:
 o=r2['out'];o=o[(o.source==row['source'])&(o.lead==row['lead'])&(o.model=='M3-fcst-refit')].iloc[0]
 for ours,theirs in [('all','all hours'),('high_target','high tide @target'),('low_target','low tide @target'),('plug_target','plug band @target'),('storm_start','storm starts @issuance')]:
  diffs.append(abs(row['views'][ours]['purged_mae']-o[theirs]))
assert max(diffs)<1e-10
out['independent_refit_comparison']={'values':len(diffs),'max_abs_difference_ft':max(diffs)}
out['training_boundaries']={'source_review':'All M2/M3, transfer and forecast-refit selections require target before split; theta uses only training-period observations.'}
paths=['history/data/sandy_hook_hourly_utc.parquet','history/scripts/surge_forcing_research_r2.py','history/scripts/surge_forecast_wind_test_r2.py','history/scripts/surge_decay_views_utc.py','history/scripts/pull_sandy_hook_history_utc.py']
out['sha256']={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
for p in ['history/scripts/surge_forcing_research.py','history/scripts/surge_forecast_wind_test.py','history/reports/2026-09-23-surge-forcing-results.txt','history/reports/2026-09-23-surge-forecast-wind-results.txt']:
 assert Path(p).read_bytes()==subprocess.check_output(['git','show',f'2e609b47f:{p}'])
out['original_studies_unchanged']=True
print(json.dumps(out,indent=2,default=str))
