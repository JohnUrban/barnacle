import ast,copy,datetime as dt,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path(sys.argv[1]).resolve();sys.path.insert(0,str(ROOT));from forecast import flood_forecast_daily as ff
base=subprocess.check_output(['git','show','224c14dcd^:forecast/flood_forecast_daily.py'],cwd=ROOT,text=True)
node=next(n for n in ast.parse(base).body if isinstance(n,ast.FunctionDef) and n.name=='fetch_nws_qpf'); module=ast.Module(body=[node],type_ignores=[]);ns=vars(ff).copy();exec(compile(module,'base-qpf','exec'),ns);old=ns['fetch_nws_qpf']
start='2026-09-24T12:00:00+00:00/'
cases={'six_hour':[{'validTime':start+'PT6H','value':3}], 'null':[{'validTime':start+'PT1H','value':None}], 'empty':[], 'bad_interval':[{'validTime':'bad','value':3}], 'overlap':[{'validTime':start+'PT6H','value':3},{'validTime':start+'PT1H','value':2}], 'fractional':[{'validTime':start+'PT30M','value':2}], 'bad_amount':[{'validTime':start+'PT1H','value':'bad'}]}
rows=[]
for name,values in cases.items():
    def fake(url):return {'properties':{'forecastGridData':'https://grid'}} if 'points/' in url else {'properties':{'updateTime':'2026-09-24T11:00:00Z','quantitativePrecipitation':{'uom':'wmoUnit:mm','values':values}}}
    ff._get=fake;ns['_get']=fake
    a,b=old(),ff.fetch_nws_qpf();rows.append({'case':name,'identical':a==b,'buckets':len(a) if a is not None else None})
expected=json.loads(Path(__file__).with_name('frozen-files.json').read_text());frozen=[]
for root in [ROOT,Path(sys.argv[2]).resolve()]:
    for e in expected:frozen.append({'branch_root':root.name,'path':e['path'],'matches':hashlib.sha256((root/e['path']).read_bytes()).hexdigest()==e['sha256']})
syntax=[]
research=Path(sys.argv[2]).resolve()
for p in list((research/'history/scripts/as_issued').glob('*.py'))+[research/'forecast/replay_archive.py',research/'tests/test_as_issued_validation.py',research/'tests/test_replay_archive_provenance.py',ROOT/'forecast/flood_forecast_daily.py']:
    ast.parse(p.read_text(),feature_version=(3,11));syntax.append(str(p.relative_to(p.parents[2])) if p.is_relative_to(research/'history') else p.name)
out={'qpf_differential':rows,'frozen_files':frozen,'syntax_311_files':len(syntax),'logging_changed_paths':subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r','224c14dcd'],cwd=ROOT,text=True).splitlines()}
Path('/tmp/heron-r3-isolation.json').write_text(json.dumps(out,indent=2));print('QPF cases',len(rows),'all identical',all(x['identical'] for x in rows),'frozen files',len(frozen),'all match',all(x['matches'] for x in frozen),'syntax files',len(syntax))
