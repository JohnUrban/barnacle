"""Read-only review probes. Usage: python verify_candidate.py CANDIDATE_ROOT.
Run against the ba57f53d5 snapshot; comparisons are synthetic unless noted.
No transport, notifications, state, ledger, or candidate writes.
"""
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from forecast import flood_forecast_daily as ff, outlook
import test_outlook as to
import test_selective_recovery as rec

out = {'candidate': 'ba57f53d5', 'outlook_fallback_comparisons': []}
data = to._fixture_data()
data['nwps'] = None
data['petss'] = None
for name, fresh, reading in [
    ('missing', None, None),
    ('stale-state', None, (2.5, to.NOW - dt.timedelta(hours=10))),
    ('fresh-50-min-old', 2.5, (2.5, to.NOW - dt.timedelta(minutes=50))),
]:
    ol = outlook.build_outlook_7d(
        to.NOW, data, to._health(data), [], fresh, None,
        ff.classify_regime_from_water,
        lambda p: ff.predict_landmark_depths(p, 0, False),
        ff.MLLW_TO_NAVD88_OFFSET, 'v0.10.6', surge_mean_ft=.54,
        obs_reading=reading)
    tide = next(t for t in ol['tides'] if t['lead_h'] > 0)
    est = outlook.hourly_surge_estimator(to.NOW, data, [], .54, reading)
    surge, source = est(outlook._utc(tide['utc']))
    out['outlook_fallback_comparisons'].append({
        'case': name, 'time': tide['time'],
        'table_mllw': tide['outlook_mllw'], 'table_source': tide['outlook_source'],
        'estimator_at_same_tide_mllw': round(tide['astro_mllw'] + surge, 3),
        'estimator_source': source,
        'difference_ft': round(tide['astro_mllw'] + surge - tide['outlook_mllw'], 3)})

bad_mean = {'mean_ft': .54, 'n_hours': 8000, 'computed_utc': '2026-09-23T00:00:00'}
with patch.object(ff._surge_mean, 'load', return_value=bad_mean):
    try:
        rec.build()
        out['malformed_mean_whole_build'] = 'unexpected success'
    except Exception as e:
        out['malformed_mean_whole_build'] = f'{type(e).__name__}: {e}'

state = (1.8, rec.NOW.astimezone(dt.timezone.utc) - dt.timedelta(hours=10))
with patch.object(ff, '_load_surge_state', return_value=state), \
     patch.object(ff._surge_mean, 'load', return_value=None), \
     patch.dict(ff._LAST_SURGE_READING, {'reading': None}):
    built = rec.build(surge=None)
out['selected_state_provenance'] = built['water_series_input']
out['surge_health_keys'] = [k for k in built['input_health'] if 'surge' in k]

rows, observations = [], {}
for i in range(28):
    tide = f'tide-{i}'
    observations[tide] = 1.
    rows.append({'target_tide_time': tide, 'lead_h': '12',
                 'persist_decay_mllw': '1', 'persist_flat_mllw': '2',
                 'model_version': 'v0.10.5'})
rows.append({'target_tide_time': 'tide-0', 'lead_h': '12',
             'persist_decay_mllw': '5', 'persist_flat_mllw': '2',
             'model_version': 'v0.10.6'})
out['synthetic_mixed_version_score'] = outlook.score_shadow(rows, observations)[
    'readiness']['decay_vs_flat_persistence_le168h']

# Mechanism check, NOT historical or forecast skill: same rain, differing bay.
out['synthetic_tank_sensitivity'] = []
times = [to.NOW + dt.timedelta(minutes=5*i) for i in range(37)]
for bay in (2.7, 3.1, 3.5, 3.9):
    series = ff.simulate_pluvial_series(times, [bay]*len(times), [.3]*len(times))
    peak = max(x for x in series if x is not None)
    out['synthetic_tank_sensitivity'].append({
        'constant_bay_navd88': bay, 'rain_in_hr': .3, 'duration_h': 3,
        'peak_water_navd88': round(peak, 6), 'peak_inches_over_grate': round((peak-3.52)*12, 3)})

# Primary historical input excerpt, from the real repo holding this script.
repo = Path(__file__).resolve().parents[2]
sha = '3a6c96faf7ebbf98c3e69322948aa5c1ddbbcedc'
raw = subprocess.check_output(['git', 'show', f'{sha}:docs/forecast.json'], cwd=repo, text=True)
old = json.loads(raw)
out['archived_issuance_rain'] = {'commit': sha, 'generated_utc': old['generated_utc'], 'windows': []}
for tide in old['all_tides']:
    if tide['time'].startswith('2026-09-13'):
        instant = ff.parse_station_local_time(tide['time'])
        out['archived_issuance_rain']['windows'].append({
            'tide': tide['time'],
            'hourly_rates': [{'time': (instant+dt.timedelta(hours=h)).isoformat(), 'in_hr': rate}
                             for h, rate in tide['rain_window_3h']]})
print(json.dumps(out, indent=2))
