"""Independent round-07 checks; scratch-only outputs, no live network."""
import argparse,ast,copy,datetime as dt,hashlib,importlib.util,json,random,subprocess,sys,tempfile
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
r=Path(a.repo).resolve();sys.path.insert(0,str(r));sys.path.insert(0,str(r/'tests'))
from forecast import wind_shadow as ws,flood_forecast_daily as ff
import test_wind_shadow as fx
spec=importlib.util.spec_from_file_location('eval_review',r/'history/scripts/evaluate_wind_shadow.py');ev=importlib.util.module_from_spec(spec);spec.loader.exec_module(ev)
out={};b=ws.check_bundle(str(r));assert b['ok'];out['bundle']=b
# q changes the first flag's meaning: verify repaired outcomes.
rows=[]
for i,q in enumerate(['p','v',None,'unknown']):
 row={'t':f'2026-09-01 {i:02}:00','v':'5.5','f':'1,0,0,0'}
 if q is not None:row['q']=q
 rows.append(row)
obs=ev.parse_observations({'data':rows},{'predictions':[{'t':row['t'],'v':'4'} for row in rows]})
out['quality_semantics']=[{'input':row,'output':obs[ev._utc(row['t'].replace(' ','T')+'Z')]} for row in rows]
assert [x['output']['valid'] for x in out['quality_semantics']]==[True,False,False,False]
assert out['quality_semantics'][0]['output']['outlier_samples']==1
assert out['quality_semantics'][1]['output']['inferred_obs']==5.5
assert 'outlier_samples' not in out['quality_semantics'][1]['output']
assert all(x['output']['f']=='1,0,0,0' for x in out['quality_semantics'])
# Frozen rain reference agrees numerically with production, including varying bay/rain.
rr=ev.rain_ref();rng=random.Random(20260924);errors=[];mismatches=0;n=0
for j in range(200):
 times=[fx.T0+dt.timedelta(minutes=30*i) for i in range(73)]
 bay=[rng.uniform(1.5,5.0) for _ in times]; rain=[rng.choice([0.,.1,.4,1.]) for _ in times]
 x=ff.simulate_pluvial_series(times,bay,rain);y=rr.simulate_pluvial_series(times,bay,rain)
 for u,v in zip(x,y):
  n+=1;mismatches+=((u is None)!=(v is None))
  if u is not None and v is not None:errors.append(abs(u-v))
assert max(errors)==0 and mismatches==0
assert rr.LANDMARKS_NAVD88=={k:v for k,_,v,_ in ff.LANDMARKS if k in ff.FLOOD_WINDOW_KEYS}
out['frozen_rain']={'points':n,'max_difference_ft':max(errors),'presence_mismatches':mismatches,'landmarks':len(rr.LANDMARKS_NAVD88)}
# Raw external guidance and inherited bay are not altered to manufacture better comparisons.
f=fx._forecast(); context=fx._context(); rec=ws.pre_network_part(f,ws.load_manifest(), 'preview',fx.T,context=context,bundle=b)
assert rec['guidance']['nwps_raw']['surge_ft'][0]==1.0
assert rec['guidance']['petss_mid']['surge_ft'][0]==.6
assert rec['guidance']['nwps_raw']['surge_ft'][-1] is None
ri=rec['rain_inputs'];assert all(v is None for t,v in zip(ws.rain_times(ri),ri['baseline_surge_ft']) if t<=fx.T)
out['raw_guidance']={'nwps_first':rec['guidance']['nwps_raw']['surge_ft'][0],'petss_first':rec['guidance']['petss_mid']['surge_ft'][0],'nwps_beyond_coverage':rec['guidance']['nwps_raw']['surge_ft'][-1],'shared_preissuance_bay':True}
# Outcome replay reconstructs bytes rather than trusting edited merged rows; hash tampering fails.
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp); wl=json.dumps({'data':[{'t':'2026-09-01 00:00','v':'5.5','f':'0,0,0,0','q':'p'}]}).encode();pr=json.dumps({'predictions':[{'t':'2026-09-01 00:00','v':'4'}]}).encode()
 responses=[]
 for prod,body in [('water_level',wl),('predictions',pr)]:
  fn=prod+'.json';(p/fn).write_bytes(body);responses.append({'product':prod,'file':fn,'sha256':hashlib.sha256(body).hexdigest()})
 (p/'bundle.json').write_text(json.dumps({'responses':responses,'water_level':{'data':[]},'predictions':{'predictions':[]}}))
 z=ev.load_observation_bundle(str(p/'bundle.json'));assert z['water_level']['data'][0]['v']=='5.5'
 (p/'water_level.json').write_bytes(wl+b' ')
 try:ev.load_observation_bundle(str(p/'bundle.json'))
 except ValueError:out['outcome_provenance']={'raw_reparsed':True,'tampered_body_rejected':True}
 else:raise AssertionError('tampered raw body admitted')
# Preserve first disabled opportunity even when a later valid record exists.
with tempfile.TemporaryDirectory() as tmp:
 g=fx._rec(fx.T0,.2,.3);g.update(candidate_id=ws.CANDIDATE_ID,bundle_sha256=b['bundle_sha256'],manifest_sha256=b['table'][ws.MANIFEST_REL],runtime_sha256=b['table'][ws.RUNTIME_REL])
 early=copy.deepcopy(g);t=fx.T0-dt.timedelta(hours=1);early.update(issuance_utc=ws._stamp(t),nominal_issuance_hour_utc=ws._stamp(t),status='disabled',baseline_surge_ft=None,candidate_surge_ft=None,fallback_reason='injected')
 (Path(tmp)/'2026-09.jsonl').write_text(json.dumps(early)+'\n'+json.dumps(g)+'\n')
 slots,attempts,excluded,trial=ev.load_records(tmp,ws.CANDIDATE_ID,b['bundle_sha256'],g['manifest_sha256'],g['runtime_sha256'])
 assert trial['start']==t and t in attempts and len(slots)==1
 out['disabled_start']={'trial':trial,'attempts':{str(k):v for k,v in attempts.items()},'evaluable_slots':len(slots)}
# Existing production entry-point statements unchanged except read-only holder exports.
base=subprocess.check_output(['git','show','e640f0a27:forecast/flood_forecast_daily.py'],cwd=r,text=True)
old=next(n for n in ast.parse(base).body if isinstance(n,ast.FunctionDef) and n.name=='main')
new=next(n for n in ast.parse((r/'forecast/flood_forecast_daily.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='_main_core')
class RemoveHolder(ast.NodeTransformer):
 def visit_Assign(self,n):return None if any(isinstance(t,ast.Name) and t.id=='holder' for target in n.targets for t in ast.walk(target)) else n
new=RemoveHolder().visit(new);new.name='main';new.args=copy.deepcopy(old.args)
assert ast.dump(new,include_attributes=False)==ast.dump(old,include_attributes=False)
out['production_main_ast_unchanged_except_holder']=True
Path(a.out).write_text(json.dumps(out,indent=2,default=str)+'\n');print(a.out)
