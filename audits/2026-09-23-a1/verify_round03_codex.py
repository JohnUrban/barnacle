"""Offline adversarial review of bf2e601b4. Assertions record remaining bugs.
No network, notifications, or canonical data writes. Synthetic data is not evidence
of measured flooding. Run: python3 audits/2026-09-23-a1/verify_round03_codex.py
"""
import datetime as dt
import json
import re
import sys
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from forecast import flood_forecast_daily as ff
from forecast import outlook as ol, outlook_sources as src, outlook_page as page
from test_outlook import _build, _fixture_data, NOW
out={}
# Distinct-tide gating is fixed, but absolute error must be taken BEFORE
# averaging issuances. A +/-1 ft candidate should lose to a +0.2 baseline.
rows=[];observed={}
for i in range(28):
    t=(dt.datetime(2026,8,1,12,tzinfo=dt.timezone.utc)+dt.timedelta(hours=12*i)).isoformat()
    observed[t]=5.0
    for pred in (4.0,6.0):
        rows.append(dict(target_tide_time=t,lead_h='12',nwps_mllw=str(pred),persist_flat_mllw='5.2'))
score=ol.score_shadow(rows,observed)['readiness']['nwps_vs_persistence_le72h']
out['S1_cancellation']=score
assert score['mae_candidate']==0.0 and score['verdict'].startswith('READY')
# Same tide but no issuance with both sources is still considered a pair.
x=[dict(target_tide_time='t',lead_h='1',nwps_mllw='5'),
   dict(target_tide_time='t',lead_h='23',persist_flat_mllw='6')]
out['S1_disjoint_issuances']=ol.score_shadow(x,{'t':5})['readiness']['nwps_vs_persistence_le72h']
assert out['S1_disjoint_issuances']['n']==1
# Missing rain indicator is not present in the actual landing-map payload.
data=_fixture_data();data['nbm']=None;data['wpc']=None
built=_build(data=data)
fc={'generated_utc':NOW.isoformat(),'outlook_7d':built}
pts,*_=ff._map_time_series(fc)
unknown=next(p for p in built['series'] if p['rain_unknown'] and p['lead_h']>80)
mappt=next(p for p in pts if p['t']==unknown['time'])
out['S2_missing_rain_map']={'raw_rain_unknown':unknown['rain_unknown'],'map_point':mappt}
assert 'rain_unknown' not in mappt and 'w' in mappt
# Known grid reach with explicitly missing values is falsely declared complete dry.
grid={'series':{'qpf_in':[{'start':'2026-09-23T04:00:00Z','hours':24,'value':None}]},
      'reach':{'qpf_in':'2026-09-30T12:00:00Z'}}
d=ol.build_days(NOW,[],{'grid':grid})[0]
out['S2_null_grid']={k:d[k] for k in ('qpf_in','qpf_source','qpf_covered_h')}
assert d['qpf_in']==0 and d['qpf_covered_h']==24
# Continuous horizon still conflicts with table and fixed 168-hour field.
f=json.loads((ROOT/'docs/forecast.json').read_text());o=f['outlook_7d']
out['S3_published_horizon']={'generated':f['generated_utc'],'declared_h':o['horizon_hours'],
 'series_last_lead':o['series'][-1]['lead_h'],'series_last':o['series'][-1]['time'],
 'table_last':o['tides'][-1]['time']}
assert o['series'][-1]['lead_h']<168
# New day_worst regresses the established future-only headline.
series=[dict(time='2026-09-23 06:00-04:00',water_navd88=6,tide_navd88=2),
        dict(time='2026-09-23 16:00-04:00',water_navd88=2,tide_navd88=2)]
dw=ff.compute_day_worst([],series,{},[],['2026-09-23'])
out['S4_past_flood_headline']=dw[0]
assert dw[0]['regime']=='severe'
# Render only: no delivery. Preserve ordinary required fields from the artifact.
from forecast.rendering import render_email
f['depths_in']['regime']='dry'; f['today_regime']='dry'; f['today_lookback']=None
f['day_worst']=[{'day':'2026-09-23','rank':0,'regime':'dry','pathway':'tide'},
 {'day':'2026-09-24','rank':4,'regime':'severe','pathway':'rain (tank line)','water_navd88':6}]
subject,body,email_html=render_email(f)
panel=email_html.split('WORST 72 H</div>',1)[1].split('</b>',1)[0]
out['S4_email']={'subject':subject,'html_worst_panel':panel}
assert 'WORST 72H SEVERE (RAIN)' in subject and 'NO FLOODING' in panel
# New compound display is not what the continuous burst chart plots.
series=[dict(time='2026-09-23 12:00-04:00',lead_h=5,tide_navd88=4.5,water_navd88=4.5,
             pluvial_navd88=None,rain_in_hr=0.5,rain_unknown=False,burst_risk=True,surge_source='nwps'),
        dict(time='2026-09-23 18:00-04:00',lead_h=11,tide_navd88=5,water_navd88=5,
             pluvial_navd88=None,rain_in_hr=0,rain_unknown=False,burst_risk=False,surge_source='nwps')]
days=[{'date':'2026-09-23','regime_max':'severe'}]
ol.add_rain_pathway(days,series,[],ff.estimate_pluvial_water_models,ff.classify_regime_from_water)
w=ol.worst_points(series,days)
html=page._chart({'series':series,'days':days,'worst':w})
chart=json.loads(re.search(r'var D = (\{.*?\});',html,re.S).group(1))
p=series[0]
out['S5_compound_chart']={'per_point_potential_navd88':p['burst_potential_navd88'],
 'chart_potential_navd88':round(chart['burst'][0]/12+3.52,3),
 'card_high_tide_potential_navd88':days[0]['rain_pathway']['burst_at_high_tide_navd88'],
 'worst_selected_navd88':w['flood_chance']['navd88']}
assert abs(out['S5_compound_chart']['per_point_potential_navd88']-out['S5_compound_chart']['chart_potential_navd88'])>0.1
# R4's "malformed buckets dropped" claim omits required duration.
bad={'nbm':{'cycle':NOW.isoformat(),'buckets':[{'end_utc':(NOW+dt.timedelta(hours=6)).isoformat(),'qpf_in':1}]}}
admitted,health=src.admit_guidance(bad,'nbm',NOW)
try: ol._bucket_containing(admitted['buckets'],NOW)
except KeyError as e: out['S6_bad_bucket']={'status':health['status'],'consumer_exception':str(e)}
assert out['S6_bad_bucket']['status']=='ok'
# Real two-request adapter with fake elapsed time: each response arrives within
# its assigned socket timeout, yet the total exceeds the remaining budget.
clock=[0.0];deadline=src.Deadline(60,clock=lambda:clock[0]);clock[0]=50.0
timeouts=[]
def fake_json(url,timeout):
    timeouts.append(timeout);clock[0]+=9
    return {'properties':{'forecastGridData':'synthetic-grid'}}
with patch.object(src,'_get_json',side_effect=fake_json), patch.object(src,'parse_nws_grid',return_value={'summary':'synthetic'}):
    _,health=src.refresh({},'grid',lambda timeout:src.fetch_nws_grid(timeout=timeout),NOW,deadline=deadline)
out['S7_deadline']={'elapsed':clock[0],'budget':60,'request_timeouts':timeouts,'status':health['status']}
assert clock[0]>60 and timeouts==[10,10] and health['status']=='ok'
print(json.dumps(out,indent=2,sort_keys=True))
