import sys,json,hashlib,datetime as dt,re
from pathlib import Path
import numpy as np,pandas as pd
import argparse
_parser=argparse.ArgumentParser()
_parser.add_argument('--repo',required=True)
_parser.add_argument('--out',required=True)
_args=_parser.parse_args()
ROOT=Path(_args.repo).resolve()
sys.path.insert(0,str(ROOT))
from forecast import wind_shadow as ws
D=ROOT/'history/data'; FT=D/'forecast_test'; manifest=json.loads((ROOT/'models/wind_shadow/manifest.json').read_text())
s=pd.read_parquet(FT/'surge_hourly.parquet').set_index('timestamp').asfreq('h');s.index=s.index.tz_localize('UTC')
m=pd.read_parquet(FT/'met_obs.parquet').set_index('timestamp'); m.index=m.index.tz_localize('UTC');m=m[~m.index.duplicated()].reindex(s.index)
p=m.pressure_mb;pan=p-p.rolling(720,min_periods=480).mean().shift(1)
mp=s.surge_ft.rolling(364*24,min_periods=300*24).mean().shift(21*24)
g=pd.read_parquet(D/'gfs_single_runs/runs.parquet'); gs={pd.Timestamp(k):v.set_index('valid_utc') for k,v in g.groupby('run_init_utc')}
fc=pd.read_parquet(FT/'fcst_gfs_seamless.parquet').set_index('timestamp');fc.index=fc.index.tz_localize('UTC')
start=g.run_init_utc.min()+pd.Timedelta(hours=6); end=s.index.max()-pd.Timedelta(hours=48)
issuances=s.index[(s.index>=start)&(s.index<=end)]
X=[];valid=[]; oldW={12:[],24:[],30:[]};newW={12:[],24:[],30:[]}
for t in issuances:
 init=(t-pd.Timedelta(hours=6)).floor('6h'); times=pd.date_range(t+pd.Timedelta(hours=1),periods=48,freq='h');run=gs.get(init)
 if run is None: continue
 w=run.reindex(times)[['wind_kn','wind_dir','pressure_hpa']].to_numpy(float)
 stress=w[:,0]**2*np.cos(np.deg2rad(w[:,1]-70))
 complete=np.isfinite(w).all(axis=1).astype(int).cumprod().astype(bool)
 mat=np.column_stack([stress.cumsum()/np.arange(1,49),w[:,2]-p.get(t),np.repeat(pan.get(t),48),np.ones(48)])
 mat[~complete]=np.nan
 X.append(mat);valid.append(t)
 for h in [12,24,30]:
  if np.isfinite(mat[h-1]).all():
   d=1 if h<=24 else 2; a=fc.reindex(times[:h]); sp=a[f'wind_speed_10m_previous_day{d}'].to_numpy();dr=a[f'wind_direction_10m_previous_day{d}'].to_numpy()
   # same overlap definition as source; compare wind only after pressure eligibility
   if t<=min(g.run_init_utc.max(),fc.index.max())-pd.Timedelta(hours=48) and np.isfinite(sp).all() and np.isfinite(dr).all() and np.isfinite(a[f'pressure_msl_previous_day{d}'].iloc[-1]):
    oldW[h].append(np.mean(sp**2*np.cos(np.deg2rad(dr-70))));newW[h].append(mat[h-1,0])
X=np.array(X);valid=pd.DatetimeIndex(valid);out={'n_nominal_issuances':len(issuances),'fit':{},'equivalence':{}}
maxdelta=0
for h in range(1,49):
 base=mp.reindex(valid).to_numpy()+(s.surge_ft.reindex(valid).to_numpy()-mp.reindex(valid).to_numpy())*np.exp(-h/36)
 target=s.surge_ft.reindex(valid+pd.Timedelta(hours=h)).to_numpy();y=target-base
 mask=np.isfinite(X[:,h-1,:]).all(axis=1)&np.isfinite(y)
 A=X[mask,h-1,:];yy=y[mask];coef=np.linalg.lstsq(A,yy,rcond=None)[0];pred=np.clip(A@coef,-3,3)
 maxdelta=max(maxdelta,float(np.max(np.abs(coef-manifest['coefficients'][str(h)]))))
 out['fit'][h]={'n':int(mask.sum()),'mae_baseline':float(np.abs(yy).mean()),'mae_candidate':float(np.abs(yy-pred).mean()),'coef':coef.tolist()}
for h in [12,24,30]:
 a=np.array(oldW[h]);b=np.array(newW[h]);out['equivalence'][h]={'n':len(a),'r':float(np.corrcoef(a,b)[0,1]),'slope':float(a@b/(a@a))}
out['max_coefficient_difference_vs_8decimal_manifest']=maxdelta
# Verify every single-run raw hash, units and numerical parquet provenance
hashfail=[];metas=set();parsed=0;mismatch=0
for f in sorted((D/'gfs_single_runs/raw').glob('*.json')):
 r=json.loads(f.read_text());raw=r['body']; obj=json.loads(raw)
 if hashlib.sha256(raw.encode()).hexdigest()!=r['sha256']:hashfail.append(f.name)
 if obj.get('error'):continue
 parsed+=1;metas.add((obj['latitude'],obj['longitude'],str(obj['hourly_units'])))
 arr=gs[pd.Timestamp(r['run_init_utc'])]
 for i,t in enumerate(obj['hourly']['time']):
  a=np.array([obj['hourly'][v][i] for v in ['wind_speed_10m','wind_direction_10m','pressure_msl']],dtype=float)
  b=arr.loc[pd.Timestamp(t,tz='UTC'),['wind_kn','wind_dir','pressure_hpa']].to_numpy(dtype=float)
  if not np.array_equal(a,b,equal_nan=True):mismatch+=1
out['raw']={'n_successful':parsed,'hash_failures':hashfail,'parquet_mismatches':mismatch,'grid_and_units':list(metas)}
# Window-only difference, still same unflagged hourly surrogate in both paths.
correctwin=s.surge_ft.rolling((364-21)*24,min_periods=300*24).mean().shift(21*24)
diff=(mp-correctwin).reindex(valid).dropna()
out['mean_window_mismatch_only']={'mean_signed_ft':float(diff.mean()),'max_abs_ft':float(diff.abs().max()),'n':len(diff)}
Path(_args.out).write_text(json.dumps(out,indent=2))
print(json.dumps({k:v for k,v in out.items() if k!='fit'},indent=2));print('selected fit',json.dumps({h:out['fit'][h] for h in [6,12,24,30,48]},indent=2))
