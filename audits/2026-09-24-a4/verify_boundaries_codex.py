# Codex independent review probes, audit 2026-09-24-a4.
# Run with the candidate worktree, e.g. --repo ../barnacle-asissued.
import argparse
from pathlib import Path as ReviewPath
_parser = argparse.ArgumentParser()
_parser.add_argument('--repo', type=ReviewPath, required=True)
_parser.add_argument('--out', type=ReviewPath, default=ReviewPath(__file__).resolve().parent)
_args = _parser.parse_args()
_args.out.mkdir(parents=True, exist_ok=True)
import sys,copy,datetime as dt,json,importlib.util,pathlib
root=_args.repo.resolve();sys.path.insert(0,str(root));sys.path.insert(0,str(root/'history/scripts'))
from as_issued import advisory as A,street as S,obs as O,fidelity as F
spec=importlib.util.spec_from_file_location('fx',root/'tests/test_as_issued_validation.py');fx=importlib.util.module_from_spec(spec);spec.loader.exec_module(fx)
res={}
# Real point exactly at its reference: protocol 4.6 calls it dry; code drops the cell.
p={'elevation':4.16,'level_type':'POINT','level':4.16,'D':4.5};res['point_at_reference']=S.score(p,'D')
# A rain replay can disagree greatly with published street water and still enter EXACT.
f,replay,p30=fx._v106(rain=[1.0]*40);ctx=fx.FakeCtx({'f':f},replay,p30);o=O.classify(fx._row('2026-09-24T12:00','curb','1',weather='rain'),fx.EL);o['row']=2
p=S.build_pairs(ctx,[o])[0];res['replay_mismatch_admitted']={k:p[k] for k in ['class','P','D','class_note']};res['replay_mismatch_admitted']['max_tank_difference']=F.f2_tank(f,'HEAD',replay[f['generated_utc']],ctx.tank)
# Mismatched correction metadata is ignored rather than rejected.
rows,fc,levels,hilo=fx._advisory_fixture({'HIGH':.3,'MID':.3,'LOW':.3},6,'corrected')
for rec,_ in rows:rec['advisory_corrections']=[{'utc':rec['generated_utc'],'ft':0.0}]
pairs,sk=A.build_pairs(rows,fc.get,hilo);A.attach_outcomes(pairs,levels,dt.datetime(2026,12,1,tzinfo=dt.timezone.utc));ar=A.evaluate(pairs,{})
res['wrong_correction_metadata']={'pairs_admitted':len(pairs),'declared_nonzero_anchors':sum(p['recorded_nonzero_corrections'] for p in pairs),'cohorts':ar['cohorts'],'verdicts':{k:v['verdict'] for k,v in ar['phases'].items()}}
# Gaps in hourly outcomes/phase coverage are not labeled unavailable.
res['absent_phase_coverage']=A.phase_of(dt.datetime(2026,12,1,tzinfo=dt.timezone.utc),[])
# Direct check on published point-score omissions.
saved=json.loads((root/'history/reports/as_issued/study-b-street.json').read_text());ps=saved['pairs'];exact=[p for p in ps if p['level_type']=='POINT' and abs(p['level']-p['elevation'])<1e-9]
res['real_point_threshold_omissions']={'pairs':len(exact),'observation_rows':sorted(set(p['obs_row'] for p in exact)),'published_predicted_wet':sum(p['P'] is not None and p['P']>p['elevation'] for p in exact),'published_predicted_dry':sum(p['P'] is not None and p['P']<=p['elevation'] for p in exact)}
# Keep source brackets and supersession visible in the evidence receipt.
import csv
ledger=list(csv.DictReader((root/'data/labeled_observations.csv').open()))
res['observation_source_examples']=[{'row':n,'stored_classification':next(o for o in saved['observations'] if o['row']==n),'source':ledger[n-2]} for n in [153,159,161,166,168,173,178,181]]
res['linear_interpolation_across_missing_halfhours']=S.interp([dt.datetime(2026,9,24,10,tzinfo=dt.timezone.utc),dt.datetime(2026,9,24,13,tzinfo=dt.timezone.utc)],[1.0,4.0],dt.datetime(2026,9,24,11,tzinfo=dt.timezone.utc))
(_args.out/'boundary-probes.json').write_text(json.dumps(res,indent=2,default=str)+'\n');print(json.dumps(res,indent=2,default=str))
