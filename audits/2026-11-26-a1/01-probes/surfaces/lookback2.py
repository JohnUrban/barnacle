import sys, json, datetime as dt, csv, io
sys.path.insert(0, '.'); sys.dont_write_bytecode=True
from unittest import mock
from forecast import flood_forecast_daily as ff
from forecast import rendering
import tempfile, pathlib, shutil, os
ROOT='.'
lines=open(ROOT+'/data/labeled_observations.csv').read().split('\n')
def run(label, keep, now_s, nowcast=None):
    now=dt.datetime.fromisoformat(now_s)
    tmp=pathlib.Path(tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__))))
    (tmp/'data').mkdir(); (tmp/'docs').mkdir()
    (tmp/'data'/'labeled_observations.csv').write_text('\n'.join([lines[0]]+[lines[i-1] for i in keep])+'\n')
    shutil.copy(ROOT+'/data/observation_bounds.jsonl', tmp/'data'/'observation_bounds.jsonl')
    if nowcast: (tmp/'docs'/'nowcast.json').write_text(json.dumps(nowcast))
    with mock.patch.object(ff,'_REPO_ROOT',str(tmp)), mock.patch.object(ff,'OBSERVATION_BOUNDS_PATH',str(tmp/'data'/'observation_bounds.jsonl')), \
         mock.patch.object(ff,'DAYMAX_REJECTIONS_PATH',str(tmp/'none.json')), \
         mock.patch.object(ff,'_station_local_now',return_value=now), \
         mock.patch.object(ff,'_fetch_actual_peak_around',mock.Mock(return_value=(None,None))):
        lb=ff._today_lookback()
    shutil.rmtree(tmp)
    print('---',label); print('   dict:',json.dumps(lb,ensure_ascii=False)[:900])
    if lb:
        print('   site :',rendering._lookback_phrase(lb)); print('   short:',rendering._lookback_phrase(lb,short=True))
# file line numbers (1-based, header = line 1) as printed by grep -n
run('morning rows 279-282 only, 10:08', [279,280,281,282], '2026-11-26T10:08:00-05:00')
run('morning rows + retrospective row 296 (surrogate 09:48, written 21:57), no evening rows', [279,280,281,282,296], '2026-11-26T22:00:00-05:00')
run('only negative report row 279 + a model day max +23 at 09:00 (retracted negative still caps the claim?)', [279,280], '2026-11-26T10:08:00-05:00',
    {"generated_utc":"2026-11-26T15:00:00Z","day_local":"2026-11-26","day_max_street_in":23.0,"day_max_utc":"2026-11-26T14:00:00Z"})
run('rows 283,284 (bounded) only at 20:00', [283,284], '2026-11-26T20:00:00-05:00')
run('rows 283-284 at 20:00 + nowcast daymax 35.2@20:54 (future-dated relative to now is impossible; use 19:50)', [283,284], '2026-11-26T20:00:00-05:00',
    {"generated_utc":"2026-11-27T00:55:00Z","day_local":"2026-11-26","day_max_street_in":27.0,"day_max_utc":"2026-11-27T00:50:00Z"})
