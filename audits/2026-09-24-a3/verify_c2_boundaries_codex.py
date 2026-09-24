"""Independent round-03 c2 boundary probes. Synthetic providers only, no live collection.
Run with --repo /path/to/wind-shadow --out /tmp/results.json.
"""
import argparse,shutil,ast,contextlib,copy,datetime as dt,hashlib,importlib.util,io,json,os,pathlib,subprocess,sys,tempfile
from unittest.mock import patch
ap=argparse.ArgumentParser(description='Read-only candidate review; all mutations occur in a temporary mirror.')
ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
source=pathlib.Path(args.repo).resolve()
mirror=tempfile.TemporaryDirectory(prefix='barnacle-c2-review-');R=pathlib.Path(mirror.name)
for name in ('forecast','tests','models','model','bin','.github','docs','data'):
 shutil.copytree(source/name,R/name,ignore=shutil.ignore_patterns('__pycache__'))
(R/'history').mkdir();shutil.copytree(source/'history/scripts',R/'history/scripts')
for name in ('assets','analysis'): (R/name).symlink_to(source/name,target_is_directory=True)
for p in source.iterdir():
 if p.is_file():shutil.copy2(p,R/p.name)
for p in (source/'history').iterdir():
 if not (R/'history'/p.name).exists():(R/'history'/p.name).symlink_to(p,target_is_directory=p.is_dir())
sys.path.insert(0,str(R));sys.path.insert(0,str(R/'tests'))
from forecast import wind_shadow as w, check_artifacts as g, flood_forecast_daily as ff, replay_archive as ra
import test_wind_shadow as fx
spec=importlib.util.spec_from_file_location('ev',R/'history/scripts/evaluate_wind_shadow.py');ev=importlib.util.module_from_spec(spec);spec.loader.exec_module(ev)
out={}
wd=R/'data/wind_shadow'; wd.mkdir(exist_ok=True)
p=wd/'zz-independent-probe.jsonl'
try:
 for label,body in [('truncated','{"v":2\n'),('array','[]\n'),('null','null\n')]:
  p.write_text(body)
  z=subprocess.run([sys.executable,str(R/'forecast/check_artifacts.py')],cwd=R,capture_output=True,text=True)
  out['gate_'+label]={'exit':z.returncode,'stdout':z.stdout[-1500:],'stderr':z.stderr[-1500:]}
finally:
 p.unlink()
 if not list(wd.iterdir()):wd.rmdir()
# Function-isolated adverse pressure data: mock all provider responses.
def futurepressure(url,params,timeout):
 if url==w.META_URL: return json.dumps({'last_run_initialisation_time':int((fx.T0-dt.timedelta(hours=10)).timestamp()),'last_run_availability_time':int((fx.T0-dt.timedelta(hours=5)).timestamp())}).encode()
 if url==w.SINGLE_RUNS_URL:return b'{"error":true,"reason":"probe"}'
 if params.get('interval')=='h':
  rows=[{'t':(fx.T0-dt.timedelta(hours=k)).strftime('%Y-%m-%d %H:%M'),'v':'1000','f':'0,0,0'} for k in range(720,0,-1)]
 else:rows=[{'t':(fx.T+dt.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'),'v':'1001','f':'0,0,0'}]
 return json.dumps({'data':rows}).encode()
i=w.fetch_inputs(fx.T,fx.MANIFEST,get=futurepressure)
out['future_pressure']={'time':i['pressure']['time_utc'],'issuance':fx.T.isoformat(),'pressure_errors':[e for e in i['errors'] if 'pressure' in e],'retained_hourly_raw_body':'body' in i['pressure']['responses'][1]}
selected,why=w.select_run(fx.T,6,w.cycle_for(fx.T,6)+dt.timedelta(hours=6),fx.T+dt.timedelta(minutes=1))
out['newer_metadata_available_after_issuance']={'selected':selected.isoformat() if selected else None,'reason':why,'metadata_availability':(fx.T+dt.timedelta(minutes=1)).isoformat(),'issuance':fx.T.isoformat()}
# Data actual forecast: captured outlook source is Barnacle processed guidance, not raw NWS.
f=json.load(open(R/'docs/forecast.json'));m=w.load_manifest()
r=w.pre_network_part(f,m,'preview',fx.T)
out['actual_outlook_comparator_sources']=sorted({x[1] for x in r['nws_outlook_surge'] if x})
# Rain code provenance and initialization are not consumed/bound by evaluator.
t=fx.T0;rr=fx._rec(t,1.0,.5)
times=[t+dt.timedelta(hours=h) for h in range(-6,49)]
rp={rr['issuance_utc']:{'qpf_hourly':ra.columnar(times,in_hr=[1.0 if z<=t else 0 for z in times]),'outlook_hourly':ra.columnar(times,astro_mllw=[6.0]*len(times)),'tank_init':{'series_start':times[0].isoformat(),'storage':'empty at series start'}}}
seen=[]
def tank(ts,bay,rain):
 seen.append({'start':ts[0].isoformat(),'rates':rain,'hours':len(ts)})
 return [None]*len(ts)
with patch.object(ff,'simulate_pluvial_series',side_effect=tank): rain=ev.rain_tank_sensitivity({t:rr},rp)
out['rain_prior_event']={'archived_start':times[0].isoformat(),'actual_call':seen[0],'report':rain}
# Rain initialization changes the physical state: compare with the same full history.
basebay=[6.0+.5-2.82]*len(times); rates=[1.0 if z<=t else 0 for z in times]
full=ff.simulate_pluvial_series(times,basebay,rates)
forwardtimes=[z for z in times if z>t]; forward=ff.simulate_pluvial_series(forwardtimes,[3.68]*len(forwardtimes),[0]*len(forwardtimes))
out['rain_initialization_numeric']={'first_target':forwardtimes[0].isoformat(),'with_archived_prior_rain_navd88':full[times.index(forwardtimes[0])],'empty_restart_navd88':forward[0]}
# A Barnacle-only fallback is currently counted as NWS/P-ETSS coverage.
ob=fx._obs(200,lambda k: .2);ot=min(ob);sr=fx._rec(ot,.3,.4);sr['nws_outlook_surge']=[[.4,'observed_decay']]*48
with patch.object(ev,'block_ci',return_value=None):
 cmp=ev.evaluate({ot:sr},ob,ot+dt.timedelta(hours=199))['leads'][24]
out['non_guidance_counted_as_nws']={k:cmp[k] for k in ['vs_nws_petss_guidance','nws_petss_coverage']}
# Hash binding before official writes: real function with modified manifest, network mocked.
with tempfile.TemporaryDirectory() as d:
 mod=json.loads((R/'models/wind_shadow/manifest.json').read_text());mod['tau_h']=999
 mp=pathlib.Path(d)/'manifest.json';mp.write_text(json.dumps(mod))
 with patch.object(w,'fetch_inputs',return_value=fx._inputs()):
  status=w.run(fx._forecast(),manifest_path=str(mp),collection='official',directory=d,now_utc=fx.T)
 row=json.loads((pathlib.Path(d)/'2026-09.jsonl').read_text())
 out['unfrozen_manifest_official_write']={'status':status,'collection':row['collection'],'matches_freeze':row['manifest_sha256']==ev.freeze_table()['models/wind_shadow/manifest.json'],'n_values':len(row['baseline_surge_ft'])}
# Offline cli emits score even though evaluator bytes no longer equal freeze.
with tempfile.TemporaryDirectory() as d:
 td=pathlib.Path(d); record=dict(fx._rec(fx.T0,0.2,.3),candidate_id=m['candidate_id'],manifest_sha256=m['_sha256'],runtime_sha256=w.runtime_sha256(),written_utc=fx.T.isoformat())
 (td/'records').mkdir();(td/'records/2026-09.jsonl').write_text(json.dumps(record)+'\n')
 (td/'obs.json').write_text(json.dumps({'water_level':{'data':[]},'predictions':{'predictions':[]}}))
 path=R/'history/scripts/evaluate_wind_shadow.py';src=path.read_text();path.write_text(src+'\n# reviewer test of mismatch rejection\n')
 try:
  z=subprocess.run([sys.executable,str(path),'--dir',str(td/'records'),'--obs-json',str(td/'obs.json'),'--now','2026-10-01T00:00:00Z'],capture_output=True,text=True)
  j=json.loads(z.stdout);out['evaluator_hash_mismatch']={'exit':z.returncode,'hashes_equal':j['evaluator_sha256']==j['freeze_evaluator_sha256'],'verdict':j['verdict']}
 finally:path.write_text(src)
# Main-flow no-send with opt-in inherited (actual workflow sets this variable).
probe=pathlib.Path(__file__).with_name('verify_dry_run.py')
for mode in ['default','opt_in']:
 with tempfile.NamedTemporaryFile(suffix='.json') as ftmp:
  env={k:v for k,v in os.environ.items() if not k.startswith('BARNACLE_WIND_SHADOW')}
  if mode=='opt_in': env['BARNACLE_WIND_SHADOW_TRIAL']='1'
  env['PYTHONDONTWRITEBYTECODE']='1'
  z=subprocess.run([sys.executable,str(probe),'--repo',str(R),'--out',ftmp.name],env=env,capture_output=True,text=True)
  out['main_dry_run_'+mode]={'exit':z.returncode,'result':json.load(open(ftmp.name)) if z.returncode==0 else z.stderr[-1500:]}
pathlib.Path(args.out).write_text((json.dumps(out,indent=2,default=str)+'\n').replace(str(R),'SCRATCH_MIRROR'))
print(args.out)
mirror.cleanup()
