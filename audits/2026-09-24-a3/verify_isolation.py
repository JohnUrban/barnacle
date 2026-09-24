import ast, datetime as dt, hashlib, importlib.util, json, os, pathlib, subprocess, sys, tempfile, time
from unittest.mock import patch
import argparse
_parser=argparse.ArgumentParser()
_parser.add_argument('--repo',required=True)
_parser.add_argument('--out',required=True)
_args=_parser.parse_args()
ROOT=pathlib.Path(_args.repo).resolve()
sys.path.insert(0,str(ROOT))
from forecast import wind_shadow as ws
from forecast import flood_forecast_daily as ff
from forecast import check_artifacts as gate
spec=importlib.util.spec_from_file_location('fixture',ROOT/'tests/test_wind_shadow.py')
fx=importlib.util.module_from_spec(spec);spec.loader.exec_module(fx)
spec=importlib.util.spec_from_file_location('ev',ROOT/'history/scripts/evaluate_wind_shadow.py')
ev=importlib.util.module_from_spec(spec);spec.loader.exec_module(ev)
result={}
with tempfile.TemporaryDirectory() as td:
 p=pathlib.Path(td);m=p/'manifest.json';m.write_text(json.dumps(fx.MANIFEST))
 def slow(url,params,timeout):
  time.sleep(.05);raise OSError('simulated slow service')
 result['timeout_status']=ws.run(fx._forecast(),now_utc=fx.T,manifest_path=str(m),directory=td,get=slow,wall_clock_s=.01)
 r=json.loads((p/'2026-09.jsonl').read_text())
 result['timeout_record']={k:r[k] for k in ('status','candidate_id','fallback_reason','baseline_surge_ft','candidate_surge_ft','leads')}
 result['timeout_primary_pairs']=len(ev.pairs({ev.hour(fx.T):r},{},fx.T+dt.timedelta(days=5),24,'primary'))
 result['timeout_record_validator']=ws.validate_file(p/'2026-09.jsonl')
 time.sleep(.3)
# Freshness claim depends on rung rather than independently checking stated reading age.
f=fx._forecast();f['water_series_input']['decay']['observation_utc']='2026-09-24T04:00:00Z';f['water_series_input']['decay']['age_h']=6.5
result['stale_fresh_label_status']=ws.build_record(f,fx.MANIFEST,fx._inputs(),fx.T)['status']
# If metadata is >one cycle late, selected run still exceeds documented availability.
old=fx.T-dt.timedelta(days=2)
selected,note=ws.select_run(fx.T,6,old)
result['meta_lag']={'meta_init':old.isoformat(),'selected_init':selected.isoformat(),'selected_after_known_available':selected>old,'note':note}
# Corrupt or malformed shadow record in isolated copy is fatal to shared production gate.
with tempfile.TemporaryDirectory() as td:
 p=pathlib.Path(td)
 for x in ROOT.iterdir():
  if x.name in ('.git','data'):continue
  (p/x.name).symlink_to(x,target_is_directory=x.is_dir())
 (p/'data').mkdir()
 for x in (ROOT/'data').iterdir():
  (p/'data'/x.name).symlink_to(x,target_is_directory=x.is_dir())
 result['gate_before_bad_shadow']=gate.check_artifacts(str(p))
 (p/'data/wind_shadow').mkdir()
 (p/'data/wind_shadow/2026-09.jsonl').write_text('{"v":1}\n')
 bad=gate.check_artifacts(str(p))
 result['gate_after_bad_shadow']=[(str(path).replace(td,'SCRATCH'),why) for path,why in bad]
# Manifest hash table validation; does not execute live collection.
import re
result['freeze_hashes']={}
for path,expected in re.findall(r'\| `([^`]+)` \| `([a-f0-9]{64})` \|',(ROOT/'models/wind_shadow/FREEZE.md').read_text()):
 actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
 result['freeze_hashes'][path]={'matches':actual==expected,'sha256':actual}
# Prove original production core is unchanged apart from holder export.
oldsrc=subprocess.check_output(['git','show','e640f0a27:forecast/flood_forecast_daily.py'],cwd=ROOT,text=True)
newsrc=(ROOT/'forecast/flood_forecast_daily.py').read_text()
a=next(n for n in ast.parse(oldsrc).body if isinstance(n,ast.FunctionDef) and n.name=='main')
b=next(n for n in ast.parse(newsrc).body if isinstance(n,ast.FunctionDef) and n.name=='_main_core')
class RemoveHolder(ast.NodeTransformer):
 def visit_Assign(self,node):
  return None if any(isinstance(x,ast.Name) and x.id=='holder' for x in ast.walk(node)) else node
b=RemoveHolder().visit(b);b.name=a.name;b.args=a.args
result['production_core_ast_equal_except_holder']=ast.dump(a)==ast.dump(b)
path=pathlib.Path(_args.out);path.write_text(json.dumps(result,indent=2,default=str)+'\n')
print(path.read_text())
