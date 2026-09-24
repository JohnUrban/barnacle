import sys,json,datetime as dt,hashlib,collections
from pathlib import Path
ROOT=Path(sys.argv[1]).resolve()
sys.path[:0]=[str(ROOT),str(ROOT/'history/scripts')]
from as_issued import archive as A,street as S,advisory as AD,fidelity as F,cli,normalization as N,report as R,noaa
out={}
canon=lambda x:json.loads(json.dumps(x,sort_keys=True,default=str))
reports=ROOT/'history/reports/as_issued'
inv=A.inventory(); saved=json.loads((reports/'readiness-inventory-r5.json').read_text())
out['inventory']={'count':len(inv['rows']),'rows_match':canon(inv['rows'])==saved['rows']};print('inventory',out['inventory'],flush=True)
fr=F.run(inv['rows']);fs=json.loads((reports/'readiness-fidelity-r5.json').read_text());out['fidelity']={'rows':len(fr),'rows_match':canon(fr)==fs['rows'],'summary_match':canon(F.summarize(fr))==fs['summary']};print('fidelity',out['fidelity'],flush=True)
man,sha=cli.load_normalized();out['normalization']={'entries':len(man['entries']),'primary_entries':sum(x['primary'] for x in man['entries']),'rebuild_match':man==N.build(),'ledger_sha256':sha}
ctx=S.Context(inv_rows=inv['rows']);rep,pairs=S.evaluate(ctx,man['entries']);saved=json.loads((reports/'study-b-street-r5.json').read_text())
out['street']={'pairs':len(pairs),'primary_pairs':sum(p['primary'] for p in pairs),'class_counts':rep['class_counts'],'primary_class_counts':dict(collections.Counter(p['class'] for p in pairs if p['primary'])),'pairs_match':canon(pairs)==saved['pairs'],'report_core_match':all(canon(v)==saved['report'][k] for k,v in rep.items()),'verdicts':rep['verdicts']}
ev=R.per_event(pairs,man['event_peaks']);saved_ev=json.loads((reports/'study-b-events-r5.json').read_text())
out['street']['event_tables_match']=canon(ev)==saved_ev['per_event_published_line'];out['street']['scenario_tables_match']=canon(R.conditional_scenarios(ctx,ev))==saved_ev['conditional_burst_scenarios'];print('street',out['street'],flush=True)
raw=A.replay_records(); bygen={x['generated_utc']:x for x in inv['rows']}; ps,sk=AD.build_pairs(raw,lambda g:A.load_forecast(bygen[g]['blob']) if g in bygen else None,ctx.hilo)
saved_a=json.loads((reports/'study-a-advisory-r5.json').read_text());ar=saved_a['report'];levels=noaa.water_levels(noaa.load_bodies(str(ROOT/ar['outcome_manifest'])));AD.attach_outcomes(ps,levels,dt.datetime.fromisoformat(ar['evaluated_utc']));from forecast import flood_forecast_daily as ff
arep=AD.evaluate(ps,{k:e for k,l,e,s in ff.LANDMARKS});out['advisory']={'pairs':len(ps),'pairs_match':canon(ps)==saved_a['pairs'],'report_core_match':all(canon(v)==ar[k] for k,v in arep.items()),'skips_match':sk==ar['skipped'],'replay_records':len(raw),'cohorts':arep['cohorts']};print('advisory',out['advisory'],flush=True)
# Independent point errors and interval distances from saved pair facts, without score/summarize helpers.
pairs=saved['pairs'];diag=[p for p in pairs if p['primary'] and p['class']=='APPROX-TIDE']
metrics={}
for arm in ['D','K']:
    events={};iv=[];lb=[]
    for p in diag:
        val=p.get(arm)
        if val is None:continue
        if p['level_type']=='POINT':events.setdefault(p['obs_time'][:10],[]).append(abs(val-p['point']))
        rng=p.get(arm+'_range') or [val,val]
        if p['level_type'] in ['POINT','INTERVAL'] and p['lo'] is not None and p['hi'] is not None:iv.append(max(p['lo']-rng[1],rng[0]-p['hi'],0))
        if p['level_type']=='LOWER':lb.append(max(p['lo']-rng[1],0))
    metrics[arm]={'point_events':len(events),'event_mae':{k:sum(v)/len(v) for k,v in events.items()},'interval_n':len(iv),'interval_mean':sum(iv)/len(iv),'lower_bound_n':len(lb),'lower_misses':sum(x>0 for x in lb)}
out['independent_diagnostic']=metrics
Path('/tmp/heron-r9-reproduction.json').write_text(json.dumps(out,indent=2,default=str));print('done',json.dumps(metrics),flush=True)

# Additional independent combined-control check (same receipt).
import subprocess, math
rows=[x for x in fr if x["F2"].get("status")=="replayed"]; bad=[]; count=0
for row in rows:
    f=A.load_forecast(row["blob"])
    for p in f["water_series"]:
        b,pv,w=p.get("tide_navd88"),p.get("pluvial_navd88"),p.get("water_navd88")
        if b is None: continue
        count+=1; expected=b if pv is None else max(b,pv)
        if w is None or not math.isfinite(w) or abs(w-expected)>.002: bad.append({"blob":row["blob"],"time":p["time"],"published":w,"expected":expected})
out["real_combined_control"]={"issuances":len(rows),"points":count,"mismatches":bad}
Path("/tmp/heron-r9-reproduction.json").write_text(json.dumps(out,indent=2,default=str))
