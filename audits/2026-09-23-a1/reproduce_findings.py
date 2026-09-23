"""Offline audit probes, not production regression tests; run from any cwd.
Assertions describe defects at ece4c2314 and should fail when repaired.
No network, canonical ledger writes, alert delivery, or production mutation.
"""
import copy
import datetime as dt
import json
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from forecast import flood_forecast_daily as ff
from forecast import outlook as ol, outlook_sources as src, rendering as render
from test_outlook import _build, _fixture_data, NOW

results = {}
# H1: a slow failed optional source can exceed the entire hourly job budget.
requests = []
def timeout(url, timeout=30):
    requests.append(timeout)
    raise TimeoutError('synthetic timeout; no real wait/network')
with mock.patch.object(src, '_request', side_effect=timeout):
    try:
        src.fetch_nbm_qpf(NOW)
    except RuntimeError:
        pass
results['H1_nbm_discovery_only_timeout_seconds'] = sum(requests)
assert sum(requests) == 420

# H2: repeated forecast issuances of ONE observed tide unlock READY.
target = '2026-09-24 06:47-04:00'
rows = [dict(target_tide_time=target, lead_h=str(40-i), nwps_mllw='6.5',
             persist_flat_mllw='7.5', generated_utc=f'run-{i}') for i in range(28)]
score = ol.score_shadow(rows, {target: 6.5})['readiness']['nwps_vs_persistence_le72h']
results['H2_one_tide_28_issuances'] = score
assert score['verdict'].startswith('READY')

# H3: missing rain is zero in the simulation and becomes a dry rain regime.
data = _fixture_data()
data['grid']['series']['qpf_in'] = []
data['grid']['reach'].pop('qpf_in', None)
data['nbm'] = data['wpc'] = None
out = _build(data=data, hourly_periods=[])
rp = out['days'][-1]['rain_pathway']
results['H3_unavailable_rain'] = {k:rp[k] for k in ('rain_available','peak_rate_in_hr','max_6h_in','tank_regime','burst_regime')}
assert rp['rain_available'] is False and rp['tank_regime'] == 'dry' and rp['peak_rate_in_hr'] == 0
assert all(p['water_navd88'] is not None for p in out['series'])

# H4: default source freshness tests fetched time, not issued time;
# unavailable qmd is merged before the expiry check.
bucket = {'end_utc':'2026-09-26T12:00:00Z','hours':6,'qpf_in':0.1}
nbm = {'buckets':[bucket]}
qmd = {'qmd_cycle':'2026-09-20T00:00:00Z','fetched_at':'2026-09-20T06:00:00Z',
       'buckets':{bucket['end_utc']:{'p90_in':3.0}}}
health = src.merge_nbm_qmd(nbm,qmd,NOW)
results['H4_expired_qmd'] = {'health':health['status'],'p90_still_used':bucket.get('p90_in')}
assert health['status']=='unavailable' and bucket['p90_in']==3.0

# H5: grid accumulation crossing local midnight is counted in BOTH day totals.
grid = {'series':{'qpf_in':[{'start':'2026-09-24T00:00:00Z','hours':6,'value':0.6}]},
        'reach':{'qpf_in':'2026-09-30T12:00:00Z'}}
days = ol.build_days(NOW,[],{'grid':grid})
results['H5_one_0_6in_bucket_day_totals'] = [d['qpf_in'] for d in days[:2]]
assert days[0]['qpf_in']==days[1]['qpf_in']==0.6
# The hourly model steps forward, but bucket_containing is (start,end].
at = ol._hourly_rain_lookup([], [{'end_utc':'2026-09-24T06:00:00Z','hours':6,'qpf_in':6}],[])
results['H5_hourly_bucket_edges'] = {h:at(dt.datetime.fromisoformat('2026-09-24T'+h+':00+00:00'))[0] for h in ('00:00','01:00','06:00')}
assert results['H5_hourly_bucket_edges']['00:00'] is None
assert results['H5_hourly_bucket_edges']['06:00']==1.0

# H6: a station's explicit offset is stripped by both map initializers
# (see companion JS probe in report); past values also win future buttons.
series = [{'time':'2026-09-23 05:00-04:00','lead_h':-2,'tide_navd88':8,'water_navd88':8},
          {'time':'2026-09-23 08:00-04:00','lead_h':1,'tide_navd88':3,'water_navd88':3}]
results['H6_past_wins_next_7_days'] = ol.worst_points(series,[])['flood_chance']
assert results['H6_past_wins_next_7_days']['time']==series[0]['time']

# H7: landing worst ribbon ranks tide first, even against heavy rain and
# an elevated pluvial pathway. The newer outlook data is ignored.
forecast = {'all_tides':[{'time':'2026-09-24 18:00-04:00','forecast_peak_mllw':6.8,
                         'depths_in':{'regime':'street'}}],
            'rain_outlook_72h':[{'day':'2026-09-23','cum_in':3,'max_pop_pct':100,'thunder':True,'peak_in_hr':3}],
            'pluvial_risk':{'level':'elevated','potential_low_tide_navd88':6},
            'outlook_7d':{'days':[{'date':'2026-09-23','regime_max':'severe','worst_pathway':'rain'}]}}
with mock.patch.object(render,'_station_local_now',return_value=ff.parse_station_local_time('2026-09-23 07:00-04:00')):
    html = render._render_day_cards_html(forecast)
sections=html.split('<section')[1:]
results['H7_ribbon_on_tide_day'] = ['WORST OF 72 H' in s for s in sections]
assert results['H7_ribbon_on_tide_day']==[False,True,False]

# H8: per-tide CFW-first but hourly NWPS-first means two central truths.
data = _fixture_data()
for p in data['nwps']['series']:
    p['ft']=4.0
out = _build(data=data,hourly_periods=[])
tide = next(t for t in out['tides'] if t['time']=='2026-09-23 18:19-04:00')
pt = next(p for p in out['series'] if p['time']=='2026-09-23 18:00-04:00')
results['H8_ladders']={'tide_source':tide['outlook_source'],'tide_mllw':tide['outlook_mllw'],
                       'hour_source':pt['surge_source'],'hour_mllw':round(pt['tide_navd88']-ff.MLLW_TO_NAVD88_OFFSET,3)}
assert tide['outlook_source']=='nws_product' and pt['surge_source']=='nwps'

# M1: the published metadata gate does not validate outlook semantics.
from forecast import check_artifacts as gate
import tempfile
forecast=json.loads((ROOT/'docs/forecast.json').read_text())
forecast['outlook_7d']={'model_version':'invented','horizon_hours':-1,'series':'bad'}
with tempfile.TemporaryDirectory() as temp:
    path=Path(temp)/'forecast.json'; path.write_text(json.dumps(forecast))
    errors=gate.validate_forecast_metadata(str(path),ff.CURRENT_MODEL_VERSION)
results['M1_invalid_outlook_gate_errors']=errors
assert errors==[]

# Provenance and existing immutable ledgers verified separately via git blobs.
print(json.dumps(results,indent=2,sort_keys=True))
