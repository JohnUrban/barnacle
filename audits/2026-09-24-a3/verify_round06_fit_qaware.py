"""Codex round-05 fit reproduction (audits/2026-09-24-a3/verify_round05_fit_codex.py, main 73a9517ed)
with ONE change by Claude for round 06: the outcome QC line is quality-aware (q=p: [O,F,R,L], F=R=L=0;
q=v: [I,F,R,T], all 0). Everything else is Codex's independent construction, unchanged."""
"""Independent round-05 refit of the reviewed construction; reproduces its QC,
which does not imply acceptance of its preliminary/verified flag semantics.
Adapted from Codex round-03 fit verifier; saved datasets only, no manifest writes.
"""
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
pressure=pd.read_parquet(FT/'pressure_hourly_flags.parquet').set_index('timestamp').sort_index()
validflags=pressure.f.astype(str).str.fullmatch(r'0,0,0')
p=pd.to_numeric(pressure.v,errors='coerce').where(validflags).reindex(s.index)
p=p.where(np.isfinite(p));pan=p-p.rolling(720,min_periods=480).mean().shift(1)
verified=pd.read_parquet(D/'sandy_hook_hourly_utc.parquet').set_index('timestamp_utc').surge_ft.sort_index()
# Independent prefix-window calculation over verified hourly values, last 364
# calendar days; 24-day availability approximation declared by the candidate.
cs=np.r_[0,verified.fillna(0).to_numpy().cumsum()]
cn=np.r_[0,verified.notna().astype(int).to_numpy().cumsum()]
lo=verified.index.searchsorted((s.index-pd.Timedelta(days=364)).normalize())
hi=verified.index.searchsorted(s.index-pd.Timedelta(days=24))
n=cn[hi]-cn[lo]
mp=pd.Series(np.divide(cs[hi]-cs[lo],n,out=np.full(len(n),np.nan),where=n>=7200),index=s.index)

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
wf=pd.read_parquet(FT/'water_level_flags.parquet').set_index('timestamp').sort_index()
flags=wf.f.astype(str).str.split(',',expand=True)
# Independently mirror the reviewed construction, without endorsing its q handling.
qc=flags.shape[1]==4
ok=((wf.q=='p') & wf.f.astype(str).str.fullmatch(r'\d+,0,0,0') | (wf.q=='v') & wf.f.astype(str).str.fullmatch(r'0,0,0,0')) & np.isfinite(pd.to_numeric(wf.v,errors='coerce'))
X=np.array(X);valid=pd.DatetimeIndex(valid);out={'n_nominal_issuances':len(issuances),'fit':{},'equivalence':{},
 'quality_counts':wf.q.value_counts().to_dict(),
 'verified_nonzero_first_admitted':int(((wf.q=='v') & (flags[0]!='0') & ok).sum())}
maxdelta=0
for h in range(1,49):
 base=mp.reindex(valid).to_numpy()+(s.surge_ft.reindex(valid).to_numpy()-mp.reindex(valid).to_numpy())*np.exp(-h/36)
 target=s.surge_ft.reindex(valid+pd.Timedelta(hours=h)).to_numpy();y=target-base
 mask=np.isfinite(X[:,h-1,:]).all(axis=1)&np.isfinite(y)&ok.reindex(valid+pd.Timedelta(hours=h)).fillna(False).to_numpy(dtype=bool)
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
out['dataset_hashes']={}
for k,rel in {'gfs_single_runs':'gfs_single_runs/runs.parquet','surge_6min_on_hour':'forecast_test/surge_hourly.parquet','verified_hourly_utc':'sandy_hook_hourly_utc.parquet','pressure_hourly_flags':'forecast_test/pressure_hourly_flags.parquet','previous_runs_gfs':'forecast_test/fcst_gfs_seamless.parquet','water_level_flags':'forecast_test/water_level_flags.parquet'}.items():
 actual=hashlib.sha256((D/rel).read_bytes()).hexdigest()
 out['dataset_hashes'][k]={'sha256':actual,'matches':actual==manifest['dataset_sha256'][k]}
out['all_sample_counts_match']=all(out['fit'][h]['n']==manifest['fit_info'][str(h)]['n'] for h in range(1,49))
out['all_rounded_maes_match']=all(round(out['fit'][h]['mae_baseline'],4)==manifest['fit_info'][str(h)]['in_sample_mae_baseline_ft'] and round(out['fit'][h]['mae_candidate'],4)==manifest['fit_info'][str(h)]['in_sample_mae_candidate_ft'] for h in range(1,49))
Path(_args.out).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='fit'},indent=2))
