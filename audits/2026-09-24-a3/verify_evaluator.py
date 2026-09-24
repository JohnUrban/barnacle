import argparse, datetime as dt, importlib.util, io, json, math, pathlib, tempfile
from unittest.mock import patch
from urllib.parse import urlparse,parse_qs
ap=argparse.ArgumentParser()
ap.add_argument('--repo',type=pathlib.Path,required=True)
ap.add_argument('--out',type=pathlib.Path,default=pathlib.Path(__file__).with_name('results.json'))
a=ap.parse_args()
ROOT=a.repo.resolve()
spec=importlib.util.spec_from_file_location('ev',ROOT/'history/scripts/evaluate_wind_shadow.py')
ev=importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
T=dt.datetime(2026,10,1,tzinfo=dt.timezone.utc)
def stamp(h): return T+dt.timedelta(hours=h)
def o(high=False):
 s=1.5 if high else 0.0
 return (s,6.0,6.0-s,True)
res={}
# 5 high + missing + 1 high is NOT 6 consecutive valid observations.
obs={stamp(h):o(h in [0,1,2,3,4,6]) for h in range(55) if h !=5}
res['discontinuous_six_hour_episode']={'expected_episode_count':0,'actual':ev.episodes(obs,T,stamp(54))}
# 24 low + missing +24 low does not complete the 48-consecutive-valid tail.
obs={stamp(h):o(h<6) for h in range(55) if h!=30}
res['discontinuous_quiet_tail']={'expected_completed':False,'actual':ev.episodes(obs,T,stamp(54))}
# Fifth episode after the 60-day minimum. Gap in tail makes actual completion
# day76 23:00, but endpoint reconstructs last high+48 -> day68.
obs={stamp(h):o(any(d*24<=h<d*24+6 for d in (1,10,20,30,65))) for h in range(80*24)}
for h in range(65*24+6,75*24): obs.pop(stamp(h))
recs={T:{'status':'error'}}
rep=ev.evaluate(recs,obs,stamp(80*24))
res['backdated_endpoint']={'expected_endpoint':stamp(77*24).isoformat(),'actual_endpoint':rep['endpoint'],'completed':rep['episodes_completed']}
# Every present hour through current hour has a record; count excludes current
# opportunity but includes its record.
obs={stamp(h):o() for h in range(4)}
recs={stamp(h):{'status':'fallback'} for h in range(4)}
rep=ev.evaluate(recs,obs,stamp(3)+dt.timedelta(minutes=30))
res['negative_missing_count']={k:rep[k] for k in ['opportunities','records','missing_or_error']}
# Missing/malformed QC data are treated as valid; nonfinite values too.
rows=[{'t':'2026-10-01 00:00','v':'6.0'}, {'t':'2026-10-01 01:00','v':'6.0','f':'garbage'}, {'t':'2026-10-01 02:00','v':'NaN','f':'0,0,0,0'}, {'t':'2026-10-01 03:00','v':'6.0','f':'-1,0,0,0'}]
def fake(req,timeout):
 product=parse_qs(urlparse(req.full_url).query)['product'][0]
 body={'data':rows} if product=='water_level' else {'predictions':[{'t':r['t'],'v':'4.5'} for r in rows]}
 return io.BytesIO(json.dumps(body).encode())
with patch.object(ev.urllib.request,'urlopen',fake): got=ev.fetch_observations(T,stamp(4))
res['invalid_qc_accepted']={t.isoformat():{'valid':v[3],'surge_finite':math.isfinite(v[0])} for t,v in got.items()}
# Frozen manifest identity isn't validated by loader.
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp)/'sample.jsonl'
 p.write_text('\n'.join(json.dumps({'candidate_id':'wind-shadow-c1','manifest_sha256':sha,'issuance_utc':stamp(i).isoformat()}) for i,sha in enumerate(['reviewed-hash','different-hash'])))
 res['mixed_manifest_hashes']={'loaded_count':len(ev.load_records(tmp,'wind-shadow-c1'))}
# A single scored episode and 30 records can PASS, although 5 real episodes
# have occurred and only one has any scored candidate predictions.
obs={stamp(h):o(h<72 or any(d*24<=h<d*24+6 for d in (12,24,36,48))) for h in range(70*24)}
recs={}
for h in range(30):
 t=stamp(h); truth=[obs[stamp(h+k)][0] for k in range(1,49)]
 recs[t]={'status':'candidate','leads':{'start':stamp(h+1).isoformat()},'candidate_surge_ft':truth,'baseline_surge_ft':[v+0.5 for v in truth], 'production_model_version':'future-version','nws_outlook_surge':[[0.0,'nwps']]*48}
# The statistical bootstrap is immaterial to Boolean pass checks; preserve it
# but reduce iterations to 10 to make the reproduction quick.
orig=ev.block_ci
ev.block_ci=lambda ps:orig(ps,n=10)
rep=ev.evaluate(recs,obs,stamp(70*24))
res['insufficient_scored_episode_pass']={k:rep[k] for k in ['status','verdict','opportunities','records','missing_or_error','episodes_completed']}
res['insufficient_scored_episode_pass']['scored_episodes_24h']=rep['leads'][24]['primary']['episodes']
res['report_omits_comparators']={'24h_report_keys':list(rep['leads'][24]),'view_keys':list(rep['leads'][24]['primary']),'top_keys':list(rep)}
p=a.out
p.write_text(json.dumps(res,indent=2,default=str)+'\n')
print(p.read_text())
