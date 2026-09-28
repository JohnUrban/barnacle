#!/usr/bin/env python3
"""Read-only round07 probes, using an isolated candidate archive.
Usage: python 07-review-probes.py /path/to/candidate
No network, messages or production writes.
"""
import csv, datetime as dt, importlib.util, io, json, subprocess, sys, tempfile
from pathlib import Path
from unittest import mock
ROOT=Path(sys.argv[1]).resolve();sys.path.insert(0,str(ROOT))
from forecast import flood_forecast_daily as ff, rendering, publish_decision

def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=module('lookback_review',ROOT/'tests/test_today_lookback.py')
r={'candidate':'8da682473','reviewed_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
r['prior_dry_case_fixed']=h.lookback(h.DRY_0250,h.MODEL_39)
rows=list(csv.DictReader((ROOT/'data/labeled_observations.csv').open()))
row=rows[191-2]
assert 'exact observation time unconfirmed' in row['observed_qualitative']
buf=io.StringIO();csv.writer(buf).writerow([row[x] for x in ['observation_time_local','landmark_key','observed_depth_in','observed_qualitative']])
model={'generated_utc':'2026-09-26T01:10:00Z','day_local':'2026-09-25','day_max_street_in':26.0,'day_max_utc':'2026-09-26T00:06:00Z'}
r['surrogate_time_suppresses_claim']=h.lookback(buf.getvalue(),model,now=dt.datetime(2026,9,25,22,0))
r['exact_qualitative_wet_suppresses_higher_model']=h.lookback('2026-09-27T02:50,grate_SW,,Water seen above SW grate; depth not measured\n',h.MODEL_39)
base={'evidence':'reported','rel_grate_in':None,'time_local':'20:06','time_uncertain':True}
payloads=[dict(base,report='No flooding at the intersection'),dict(base,report='Water over the curb at the intersection')]
src=(ROOT/'docs/barnacle-widget.js').read_text();js=src[src.index('// SOFAR-BEGIN'):src.index('// SOFAR-END')]
js+='\nconsole.log(JSON.stringify(JSON.parse(process.argv[1]).map(soFarText)));'
out=subprocess.run(['node','-e',js,json.dumps(payloads)],capture_output=True,text=True,check=True)
r['opposite_reports_widget']=json.loads(out.stdout)
r['opposite_reports_short']=[rendering._lookback_phrase(x,short=True) for x in payloads]
r['opposite_reports_long']=[rendering._lookback_phrase(x) for x in payloads]
r['literal_report_interpreted_as_markup']=rendering._lookback_phrase(dict(base,report='<b>dry</b> & water <curb>'),html=True)
# Public-health regression reproduction uses a synthetic identifier only.
import smtplib
with tempfile.TemporaryDirectory() as tmp:
 err=smtplib.SMTPRecipientsRefused({'15555550123@sms.example.invalid':(550,b'refused')})
 path=str(Path(tmp)/'health.json'); health=ff.record_delivery_health({'succeeded':[], 'attempted':['sms'],'failed':[{'channel':'sms','error':str(err),**ff._delivery_error_facts(err)}]}, {},['sms'],path=path)
 r['private_recipient_removed']='15555550123' not in Path(path).read_text();r['safe_failure_facts']=health['failed']
# Show the figure's leaked loop variable using current records, without drawing.
iv=json.loads((ROOT/'assets/observations/2026-09-27/analysis/observation_intervals.json').read_text())
byhash={x['sha256']:x for x in iv['records']}
figpath=ROOT/'assets/observations/2026-09-27/analysis/event10_hydrographs.py'
figsrc=figpath.read_text()
r['figure_basis_not_carried_in_tape_tuple']=('for t, w, dk, lo, hi, tk, w0, w1 in tape:' in figsrc and 'and basis in ("stated", "stated_landmarks")' in figsrc)
# Eligible stated ranges in Sep26 AM; last record controls their drawing instead.
window=[]
for row in rows:
 try:t=ff.parse_station_local_time(row['observation_time_local'])
 except (ValueError,TypeError):continue
 if row.get('observer')=='john' and t.date()==dt.date(2026,9,26) and 4<=t.hour<=13:
  i=byhash.get(ff._observation_row_hash(row),{})
  window.append((row,i))
r['figure_order_example']={'last_basis':window[-1][1].get('depth_basis','stated'),'stated_range_rows':[i['csv_row'] for _,i in window if i.get('depth_kind')=='range' and i.get('depth_basis') in ('stated','stated_landmarks')], 'move_approximate_row_221_to_end_basis':byhash[ff._observation_row_hash(rows[219])]['depth_basis']}
print(json.dumps(r,indent=2))
