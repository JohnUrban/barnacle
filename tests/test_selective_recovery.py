"""Whole-build frozen-input contracts for the September 23 recovery.
No transport, delivery, canonical ledger or cache writes.
"""
import datetime as dt
import json
import unittest
import tempfile
from types import SimpleNamespace
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from forecast import flood_forecast_daily as ff
from forecast import check_artifacts, outlook_sources, rendering


# v0.10.6: whole-build tests never read the repo's live surge state or the
# warm job's trailing mean (they are data files the bots rewrite).
_isolation = [patch.object(ff, "_load_surge_state", return_value=None),
              patch.object(ff._surge_mean, "load", return_value=None)]


def setUpModule():
    for p in _isolation:
        p.start()


def tearDownModule():
    for p in _isolation:
        p.stop()

NOW = ff.parse_station_local_time('2026-09-23 16:13-04:00')
class FrozenDateTime(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)


def build(surge=1.424, product_surge=2.5, outlook_failure=False, rain=0):
    tide_times = [NOW + dt.timedelta(hours=h) for h in (2, 26, 50)]
    highs = [(ff.station_time_storage_key(t), 5.1) for t in tide_times]
    products = [dict(when=t.replace(tzinfo=None, second=0, microsecond=0),
                     total_mllw_ft=5.1+product_surge, departure_ft=product_surge,
                     cat='Minor', raw='synthetic') for t in tide_times]
    astro = [{'t':(NOW.astimezone(dt.timezone.utc).replace(minute=0)+dt.timedelta(minutes=30*i)).strftime('%Y-%m-%d %H:%M'),
              'v':'1.0'} for i in range(-12,61)]
    qpf = [(NOW.astimezone(dt.timezone.utc).replace(minute=0)+dt.timedelta(hours=i), rain) for i in range(-6,31)]
    def observed_surge():
        ff._LAST_SURGE_OBSERVATION_META.update(
            status='ok' if surge is not None else 'degraded',
            detail='fixture observation' if surge is not None else 'observation too old',
            observation_time=ff.station_time_storage_key(NOW-dt.timedelta(minutes=6)),
            age_min=6 if surge is not None else 90)
        return surge
    fixed = {
        '_station_local_now':NOW, '_station_local_today':NOW.date(),
        'fetch_tides_24h':{'high':highs,'low':[]},
        'fetch_temperature_72h_mean':60., 'fetch_nws_hourly_forecast':[],
        'fetch_nws_qpf':qpf, 'fetch_nws_flood_alerts':[],
        'fetch_surge_swing_6h':None, 'fetch_recent_history':[],
        'fetch_high_tides_lookahead':[], 'fetch_observed_recent':[],
        'build_seasonal_context':{}, '_today_lookback':None,
        '_get':{'predictions':astro}, '_tide_cache_save':None,
        '_tide_cache_load':{},
    }
    from forecast import nws_surge_parser
    with ExitStack() as stack:
        for name,value in fixed.items():stack.enter_context(patch.object(ff,name,return_value=value))
        stack.enter_context(patch.object(ff,'dt', SimpleNamespace(datetime=FrozenDateTime, timezone=dt.timezone, timedelta=dt.timedelta, date=dt.date)))
        stack.enter_context(patch.object(ff,'fetch_current_surge',side_effect=observed_surge))
        stack.enter_context(patch.object(nws_surge_parser,'get_surge_forecast',return_value=(True,products,None,'fixture')))
        if outlook_failure:
            stack.enter_context(patch.object(ff,'build_outlook_7d_field',side_effect=OSError('outlook offline')))
        else:
            stack.enter_context(patch.object(ff,'build_outlook_7d_field',return_value=(None,{'outlook_petss':{'status':'degraded','detail':'fixture old cycle'}})))
        return ff.build_forecast()


def validate(f):
    with tempfile.TemporaryDirectory() as folder:
        p=Path(folder)/'forecast.json'
        p.write_text(json.dumps(f,default=str))
        return check_artifacts.validate_forecast_metadata(p,now_utc=NOW.astimezone(dt.timezone.utc))


class SelectiveRecoveryTests(unittest.TestCase):
    def test_product_surge_changes_only_its_tides_not_the_curve_or_tank(self):
        for rain in (0, 2):
            a=build(product_surge=1.8,rain=rain)
            b=build(product_surge=3.0,rain=rain)
            self.assertEqual(a['water_series'],b['water_series'])
            self.assertEqual(a['water_series_input'],b['water_series_input'])
            self.assertAlmostEqual(b['all_tides'][-1]['forecast_peak_mllw']-a['all_tides'][-1]['forecast_peak_mllw'],1.2)
            self.assertEqual(b['current_surge_ft'],3.0) # legacy worst-tide meaning
            # v0.10.6: the reading is 1.424; the curve's surge decays from its time
            self.assertEqual(b['water_series_input']['decay']['surge_obs_ft'],1.424)
            self.assertAlmostEqual(b['water_series_input']['surge_ft'],1.424,delta=0.01)
        self.assertGreater(max(p['water_navd88'] for p in b['water_series']),b['water_series'][0]['tide_navd88'])

    def test_negative_zero_and_missing_surge(self):
        for surge in (-.4,0.,1.424):
            f=build(surge=surge)
            self.assertAlmostEqual(f['water_series'][0]['tide_navd88'],round(1+surge+ff.LOCAL_ENHANCEMENT_FT+ff.MLLW_TO_NAVD88_OFFSET,3))
            self.assertEqual(f['water_series_input']['observation_time'],'2026-09-23 16:07-04:00')
        # v0.10.6 (owner decision missing-surge-ladder): no reading -> the
        # curve and tank run on astronomy + the typical offset, labeled.
        f=build(surge=None,rain=2)
        self.assertTrue(f['water_series'])
        self.assertIn('surge_observation',f['degraded_inputs'])
        self.assertEqual(f['water_series_input']['source'],'typical-offset')
        self.assertAlmostEqual(f['water_series'][0]['tide_navd88'],
                               round(1+0.54+ff.LOCAL_ENHANCEMENT_FT+ff.MLLW_TO_NAVD88_OFFSET,3))
        self.assertIn('typical offset',ff._render_water_series_section(f))
        self.assertEqual(f['all_tides'][0]['forecast_peak_mllw'],7.6)
        with patch.object(ff,'_get') as transport, patch.object(ff,'simulate_pluvial_series') as tank:
            self.assertEqual(ff.build_water_series(None,[]),[])
            transport.assert_not_called();tank.assert_not_called()

    def test_outlook_failure_cannot_change_core_or_alerts(self):
        a=build();b=build(outlook_failure=True)
        for field in ('water_series','water_series_input','all_tides','day_worst','today_regime','pluvial_risk','degraded_inputs'):
            self.assertEqual(a[field],b[field],field)
        with patch.object(ff,'_radar_live_state',return_value=None):
            self.assertEqual(ff.compute_alert_level(a),ff.compute_alert_level(b))
        with patch.object(rendering,'_station_local_now',return_value=NOW):
            self.assertEqual(rendering.render_email(a),rendering.render_email(b))
        self.assertEqual(a['outlook_degraded_inputs'],['outlook_petss'])
        self.assertEqual(b['outlook_degraded_inputs'],['outlook_7d'])
        self.assertNotIn('outlook',rendering._render_input_health_html(a))
        self.assertIn('fixture old cycle',rendering._render_input_health_html(a,scope='outlook'))
        self.assertIn('fixture old cycle',ff.render_outlook_page(a))
        self.assertEqual(len(ff._alert_window_tides(a)),2)
        pts,*_=ff._map_time_series(a)
        self.assertEqual(pts[0]['w'],a['water_series'][0]['water_navd88'])

    def test_gate_checks_split_and_missing_series(self):
        f=build()
        self.assertEqual(validate(f),[])
        f['degraded_inputs'].append('outlook_petss')
        self.assertTrue(any('degraded_inputs mismatch' in x for x in validate(f)))
        # legacy 'unavailable' payloads keep their rule
        f=build(surge=None);f['water_series_input']={'source':'unavailable','surge_ft':None}
        f['water_series']=[{'time':'invalid','water_navd88':0}]
        self.assertTrue(any('unavailable series input' in x for x in validate(f)))
        f=build(surge=None);f['water_series_input']['surge_ft']=float('nan')
        self.assertTrue(any('finite surge' in x for x in validate(f)))

    def test_crossed_percentiles_are_counted_and_degraded(self):
        now=NOW.astimezone(dt.timezone.utc)
        stamps=[(now+dt.timedelta(hours=h)).isoformat() for h in (1,2)]
        g={'petss':{'cycle':now.isoformat(),'p10':[{'utc':t,'surge_ft':1} for t in stamps],
                    'p90':[{'utc':stamps[0],'surge_ft':.98},{'utc':stamps[1],'surge_ft':2}]}}
        data,health=outlook_sources.admit_guidance(g,'petss',now)
        self.assertEqual(len(data['p90']),1)
        self.assertEqual(health['status'],'degraded')
        self.assertIn('1 malformed dropped',health['detail'])
