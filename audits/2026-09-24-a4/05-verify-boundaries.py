import sys,importlib.util,datetime as dt,json,math
from pathlib import Path
ROOT=Path(sys.argv[1]).resolve();sys.path[:0]=[str(ROOT),str(ROOT/'history/scripts')]
from as_issued import street as S, report as R
spec=importlib.util.spec_from_file_location('T',ROOT/'tests/test_as_issued_validation.py');T=importlib.util.module_from_spec(spec);spec.loader.exec_module(T)
out={}
for case in ['baseline','bay_string','mean_string','combined_nan','combined_string','tau_string','reading_bad_time']:
 f,r,a=T._v106();o=T._entry('2026-09-24T08:00','curb','POINT',point=4.24)
 if case=='bay_string':f['water_series'][10]['tide_navd88']='bad'
 if case=='mean_string':f['water_series_input']['decay']['mean_ft']='bad'
 if case=='combined_nan':
  for p in f['water_series']:p['water_navd88']=float('nan')
 if case=='combined_string':
  for p in f['water_series']:p['water_navd88']='bad'
 if case=='tau_string':f['water_series_input']['decay']['tau_h']='bad'
 if case=='reading_bad_time':f['water_series_input']['decay']['observation_utc']='bad'
 try:
  rep,ps=S.evaluate(T.FakeCtx({'b':f},r,a),[o]);b0=rep['B0_published_by_version'];out[case]={'classes':rep['class_counts'],'B0':b0,'verdicts':rep['verdicts']}
  events=R.per_event(ps,{})
  try:
   json.dumps({'report':rep,'events':events},allow_nan=False,default=str)
   out[case]['strict_json']='passed'
  except ValueError as e:
   out[case]['strict_json']='failed: '+str(e)
 except Exception as e:out[case]={'error':str(e),'type':type(e).__name__}
def clean(x):
 if isinstance(x,float) and not math.isfinite(x):return str(x)
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
 if isinstance(x,list):return [clean(v) for v in x]
 return x
Path('/tmp/heron-r5-extra-probes.json').write_text(json.dumps(clean(out),indent=2,allow_nan=False))
print(json.dumps(clean(out),indent=2,allow_nan=False))
