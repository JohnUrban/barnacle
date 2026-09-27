#!/usr/bin/env python3
"""Offline review probes for dc4637d3c; run with Python in Barnacle's venv.
Usage: python 05-review-probes.py /path/to/isolated/candidate
No messages sent; synthetic addresses only; writes temporary files only.
"""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import smtplib
import subprocess
import sys
import tempfile

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT))
from forecast import flood_forecast_daily as ff

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

helper = module('review_lookback', ROOT / 'tests/test_today_lookback.py')
res = {'candidate': 'dc4637d3c9ae0d6c6c53192d4d8e0cb5bbbe300e',
       'reviewed_utc': dt.datetime.now(dt.timezone.utc).isoformat()}
res['dry_same_window_model'] = helper.lookback('2026-09-27T02:50,grate_SW,0\n', helper.MODEL_39)
res['dry_with_bay'] = helper.lookback('2026-09-27T09:44,grate_SW,0\n', None,
                                    gauge=(7.57, '2026-09-27 09:44'))
with tempfile.TemporaryDirectory() as tmp:
    recipient = '15555550123@sms.example.invalid'
    err = str(smtplib.SMTPRecipientsRefused({recipient: (550, b'recipient refused')}))
    path = str(Path(tmp) / 'delivery.json')
    health = ff.record_delivery_health(
        {'attempted':['sms'], 'succeeded':[], 'failed':[{'channel':'sms','error':err}]},
        {'sig':'synthetic-review', 'rank':1}, ['sms'], path=path)
    res['delivery_privacy'] = {'synthetic_recipient_in_persisted_file': recipient in Path(path).read_text(),
                               'persisted_error':health['failed'][0]['error']}
run = subprocess.run([sys.executable, str(ROOT/'forecast/flood_forecast_daily.py'),
                      '--invalid-review-flag'], capture_output=True, text=True, cwd=ROOT)
res['invalid_cli'] = {'returncode':run.returncode, 'stderr_tail':run.stderr.splitlines()[-1]}
rain = json.loads((ROOT/'assets/observations/2026-09-27/analysis/rain_scenarios.json').read_text())
res['rain_peak_field'] = {}
for eid, window in rain['windows'].items():
    for name, scenario in window['scenarios'].items():
        peak = max(scenario['series_10min'], key=lambda s:s[1])
        if peak[1] > scenario['peak_water_in_vs_sw']:
            res['rain_peak_field'][eid+'/'+name] = {
                'reported_peak_water':scenario['peak_water_in_vs_sw'],
                'larger_water_in_own_series':peak[1], 'time_utc':peak[0]}
interval = module('review_intervals', ROOT/'history/scripts/build_observation_intervals.py')
res['interval_overrides_requiring_assumption_labels'] = {str(i):interval.OVERRIDES[i] for i in [187,191,221,238]}
widget = (ROOT/'docs/barnacle-widget.js').read_text()
start = widget.index('    const lb = forecast.today_lookback;')
end = widget.index('\n    // Flood window',start)
res['widget_lookback_code'] = widget[start:end]
print(json.dumps(res,indent=2))
