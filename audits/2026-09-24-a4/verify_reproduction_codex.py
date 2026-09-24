# Codex independent review probes, audit 2026-09-24-a4.
# Run with the candidate worktree, e.g. --repo ../barnacle-asissued.
import argparse
from pathlib import Path as ReviewPath
_parser = argparse.ArgumentParser()
_parser.add_argument('--repo', type=ReviewPath, required=True)
_parser.add_argument('--out', type=ReviewPath, default=ReviewPath(__file__).resolve().parent)
_args = _parser.parse_args()
_args.out.mkdir(parents=True, exist_ok=True)
import sys,json,datetime as dt,pathlib,hashlib,collections,copy
root=_args.repo.resolve();sys.path.insert(0,str(root));sys.path.insert(0,str(root/'history/scripts'))
from as_issued import archive as A,fidelity as F,advisory as AD,obs as O,street as S,noaa,report as R
out=_args.out;out.mkdir(exist_ok=True)
inv=A.inventory();saved=json.loads((root/'history/reports/as_issued/readiness-inventory.json').read_text());print('inventory',len(inv['rows']),inv['rows']==saved['rows'],flush=True)
fidelity=F.run(inv['rows']);fs=F.summarize(fidelity);savedf=json.loads((root/'history/reports/as_issued/readiness-fidelity.json').read_text());print('fidelity',fidelity==savedf['rows'],flush=True)
ctx=S.Context(copy.deepcopy(inv['rows']));obs,sha=O.load();rep,pairs=S.evaluate(ctx,obs);saveds=json.loads((root/'history/reports/as_issued/study-b-street.json').read_text());norm=lambda o:json.loads(json.dumps(o,default=str));print('street_pairs_identical',norm(pairs)==saveds['pairs'],rep['class_counts'],flush=True)
bygen={r['generated_utc']:r for r in inv['rows']};rp=A.replay_records();p30,p6,hilo=F.load_astronomy();ap,sk=AD.build_pairs(rp,lambda g:A.load_forecast(bygen[g]['blob']) if g in bygen else None,hilo)
saveda=json.loads((root/'history/reports/as_issued/study-a-advisory.json').read_text());ma=saveda['report']['outcome_manifest'];lv=noaa.water_levels(noaa.load_bodies(root/ma));AD.attach_outcomes(ap,lv,dt.datetime.fromisoformat(saveda['report']['evaluated_utc']));from forecast import flood_forecast_daily as ff
ar=AD.evaluate(ap,{k:e for k,l,e,s in ff.LANDMARKS});print('advisory_pairs_identical',norm(ap)==saveda['pairs'],ar['pairs'],ar['cohorts'],flush=True)
# Independently calculate saved paired event MAEs without evaluator helpers.
ps=saveds['pairs']; times=sorted(set(dt.datetime.fromisoformat(p['obs_time']) for p in ps)); evmap={};last=None;ev=-1
for t in times:
 if last is None or (t-last).total_seconds()>43200:ev+=1
 evmap[str(t)]=ev;last=t
errs=collections.defaultdict(lambda:collections.defaultdict(list))
for p in ps:
 if p['class']=='APPROX-TIDE' and p['level_type']=='POINT' and p['evidence']!='RECONSTRUCTION':
  for arm in ['D','K']:
   if p[arm] is not None:errs[arm][evmap[p['obs_time']]].append(abs(p[arm]-p['level']))
maes={a:sum(sum(v)/len(v) for v in es.values())/len(es) for a,es in errs.items()}
res={'head':A._git('rev-parse','HEAD').decode().strip(),'inventory_equal':inv['rows']==saved['rows'],'fidelity_equal':norm(fidelity)==savedf['rows'],'street_pairs_equal':norm(pairs)==saveds['pairs'],'advisory_pairs_equal':norm(ap)==saveda['pairs'],'ledger_hash_equal':sha==saveds['report']['ledger_sha256'],'independent_approx_tide_event_mae_ft':maes,'reproduced_class_counts':rep['class_counts'],'advisory_cohorts':ar['cohorts'],'readiness_summary':fs,'study_b_verdicts':rep['verdicts']}
(out/'reproduction.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2),flush=True)
