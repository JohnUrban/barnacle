#!/usr/bin/env python3
"""Round09 review probes. Run: python 09-review-probes.py /isolated/candidate.
Only synthetic model inputs and temporary files; no network or message sends.
"""
import csv,datetime as dt,importlib.util,io,json,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root))
from forecast import flood_forecast_daily as ff,rendering
spec=importlib.util.spec_from_file_location('review_helpers',root/'tests/test_today_lookback.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
rows=list(csv.DictReader((root/'data/labeled_observations.csv').open()))
def pack(row):
 b=io.StringIO();csv.writer(b).writerow([row.get(k,'') for k in ['observation_time_local','landmark_key','observed_depth_in','observed_qualitative']]);return b.getvalue()
def render(lb):
 src=(root/'docs/barnacle-widget.js').read_text();script=src[src.index('// SOFAR-BEGIN'):src.index('// SOFAR-END')]
 script+='\nconsole.log(soFarText(JSON.parse(process.argv[1])));'
 w=subprocess.run(['node','-e',script,json.dumps(lb)],capture_output=True,text=True,check=True).stdout.strip()
 return {'payload':lb,'short':rendering._lookback_phrase(lb,short=True),'widget':w}
r={'candidate':'96afc191d','reviewed_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
row=rows[238-2];lb=h.lookback(pack(row),now=dt.datetime(2026,9,27,8,13))
r['actual_row238_wrong_landmark']={'source_row':238,'landmark_key':row['landmark_key'],'source_text':row['observed_qualitative'],**render(lb)}
wet='2026-09-27T02:50,grate_SW,,Not dry; water above the SW grate\n'
neg=h.lookback(wet,h.MODEL_39)
r['negation_becomes_dry_and_suppresses_model']={'source':wet.strip(),**render(neg)}
row=rows[191-2];model={'generated_utc':'2026-09-26T01:10:00Z','day_local':'2026-09-25','day_max_street_in':26,'day_max_utc':'2026-09-26T00:06:00Z'}
r['prior_surrogate_case_fixed']=h.lookback(pack(row),model,now=dt.datetime(2026,9,25,22))
r['prior_unknown_depth_case_fixed']=h.lookback('2026-09-27T02:50,grate_SW,,Water seen above SW grate; depth not measured\n',h.MODEL_39)
r['prior_html_case_fixed']=rendering._lookback_phrase({'evidence':'reported','time_local':'20:06','report':'<b>dry</b> & water <curb>','report_summary':'water <curb> & more'},html=True)
print(json.dumps(r,indent=2))
