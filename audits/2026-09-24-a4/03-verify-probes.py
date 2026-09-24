import sys,json,datetime as dt,importlib.util,math,copy
from pathlib import Path
ROOT=Path(sys.argv[1]).resolve()
sys.path[:0]=[str(ROOT),str(ROOT/'history/scripts')]
from as_issued import street as S,advisory as AD
spec=importlib.util.spec_from_file_location('test_asissued',ROOT/'tests/test_as_issued_validation.py'); T=importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
results={}
o=T._entry('2026-09-24T08:00','curb','POINT',point=4.24)
for case in ['baseline','combined_plus_5','published_combined_nan','rain_nan','rain_negative','rain_null','tank_nan','tau_other','bay_constant_002']:
    rain=[1.0]*40 if case=='tank_nan' else None
    f,r,a=T._v106(rain=rain,pluvial='consistent' if rain else None)
    if case=='combined_plus_5':
        for p in f['water_series']:p['water_navd88']+=5
    if case=='published_combined_nan':
        for p in f['water_series']:p['water_navd88']=float('nan')
    if case in ['rain_nan','rain_negative','rain_null']:
        rr=next(iter(r.values()))['qpf_hourly'];rr['in_hr']=[float('nan') if case=='rain_nan' else None if case=='rain_null' else -1.0]*len(rr['in_hr'])
    if case=='tank_nan':
        for p in f['water_series']:
            if 'pluvial_navd88' in p:p['pluvial_navd88']=float('nan')
    if case=='tau_other':
        dec=f['water_series_input']['decay'];dec['tau_h']=18
        for p in f['water_series']:
            t=dt.datetime.fromisoformat(p['time']); p['tide_navd88']=round(a[t]-2.82+S.decay(dec['surge_obs_ft'],dt.datetime.fromisoformat(dec['observation_utc'].replace('Z','+00:00')),dec['mean_ft'],t,18),3);p['water_navd88']=p['tide_navd88']
    if case=='bay_constant_002':
        dec=f['water_series_input'].pop('decay'); f['water_series_input'].update(surge_ft=dec['surge_obs_ft'],observation_time=dec['observation_utc']);f['model_version']='v0.10.5'
        for p in f['water_series']:
            t=dt.datetime.fromisoformat(p['time']);p['tide_navd88']=round(a[t]-2.82+dec['surge_obs_ft']+.002,3);p['water_navd88']=p['tide_navd88']
    try:
        ctx=T.FakeCtx({'b':f},r,a); pairs=S.build_pairs(ctx,[o]);res=S.arms(ctx,ctx.issuances[0])
        results[case]={'pairs':[{k:p[k] for k in ['class','class_note','P','D','K']} for p in pairs], 'gates':res.get('gates'),'facts':res['facts']}
    except Exception as e:results[case]={'error':repr(e)}
rows,fc,levels,hilo=T._advisory_fixture(.3,1,'corrected')
for f in fc.values():
    for p in f['outlook_7d']['series']:p['tide_navd88']=float('nan')
ps,sk=AD.build_pairs(rows,fc.get,hilo)
results['advisory_nan']={'admitted':len(ps),'skipped':sk,'first':ps[:1]}
def json_safe(x):
    if isinstance(x,float) and not math.isfinite(x): return str(x)
    if isinstance(x,dict): return {k:json_safe(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [json_safe(v) for v in x]
    return x
Path('/tmp/heron-r3-probes.json').write_text(json.dumps(json_safe(results),indent=2,default=str,allow_nan=False))
for k,v in results.items():print(k, json.dumps({x:y for x,y in v.items() if x!='facts'},default=str)[:550])
