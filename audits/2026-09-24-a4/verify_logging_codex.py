# Codex independent review probes, audit 2026-09-24-a4.
# Run with the candidate worktree, e.g. --repo ../barnacle-asissued.
import argparse
from pathlib import Path as ReviewPath
_parser = argparse.ArgumentParser()
_parser.add_argument('--repo', type=ReviewPath, required=True)
_parser.add_argument('--out', type=ReviewPath, default=ReviewPath(__file__).resolve().parent)
_args = _parser.parse_args()
_args.out.mkdir(parents=True, exist_ok=True)
import sys,ast,subprocess,copy,datetime as dt,json,pathlib,hashlib,re
root=_args.repo.resolve();sys.path.insert(0,str(root))
from forecast import flood_forecast_daily as ff,replay_archive as ra
old=subprocess.check_output(['git','show','292cb3188^:forecast/flood_forecast_daily.py'],cwd=root,text=True);node=next(n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef) and n.name=='fetch_nws_qpf');ns=dict(ff.__dict__);exec(compile(ast.Module(body=[node],type_ignores=[]),'pre-candidate-fetch','exec'),ns);prior=ns['fetch_nws_qpf']
cases=[('six_hour',[{'validTime':'2026-09-24T12:00:00+00:00/PT6H','value':3.0}]),('null',[{'validTime':'2026-09-24T18:00:00+00:00/PT1H','value':None}]),('empty',[]),('bad_interval',[{'validTime':'bad','value':3.0}]),('overlap',[{'validTime':'2026-09-24T12:00:00+00:00/PT6H','value':3.0},{'validTime':'2026-09-24T13:00:00+00:00/PT1H','value':5.0}]),('fractional',[{'validTime':'2026-09-24T12:30:00+00:00/PT30M','value':2.0}]),('bad_amount',[{'validTime':'2026-09-24T12:00:00+00:00/PT6H','value':'bad'}])]
out=[];real_get=ff._get
for name,values in cases:
 grid={'properties':{'updateTime':'2026-09-24T12:01:00+00:00','quantitativePrecipitation':{'uom':'wmoUnit:mm','values':values}}}
 def get(url,*a,**k):return {'properties':{'forecastGridData':'https://grid.invalid'}} if '/points/' in url else copy.deepcopy(grid)
 ns['_get']=get;ff._get=get
 a=prior();b=ff.fetch_nws_qpf();assert a==b,(name,a,b)
 out.append({'case':name,'rate_output_identical':True,'buckets':None if b is None else len(b),'provenance_status':ff._LAST_REPLAY_INPUTS['qpf_meta']['status']})
ff._get=real_get
changed=subprocess.check_output(['git','diff','--name-only','292cb3188^','292cb3188','--','data/*.csv','data/replay_inputs/*.jsonl','models/wind_shadow','forecast/wind_shadow.py'],cwd=root,text=True)
assert not changed,changed
p=(_args.out/'logging-differential.json');p.write_text(json.dumps({'rate_cases':out,'production_ledgers_and_frozen_files_unchanged':True},indent=2)+'\n');print(p.read_text())
