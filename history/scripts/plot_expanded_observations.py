#!/usr/bin/env python3
"""Offline, reproducible figures from committed evidence snapshots. No downloads.

Run with the project's matplotlib/numpy environment. Does not touch all_anchors.
"""
from pathlib import Path
import json,sys,datetime as dt
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from forecast.station_time import parse_station_local_time,utc_to_station_local,STATION_TZ
A=ROOT/'assets/observations/2026-09-27/analysis'
NAVY='#234e70'; TEAL='#278579'; ORANGE='#bc6515'; GRAY='#747982'
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})

def expanded():
 d=json.loads((A/'expanded_events_data.json').read_text());events=d['events']
 fig,ax=plt.subplots(figsize=(16,15));fig.subplots_adjust(left=.17,right=.68,top=.87,bottom=.12)
 levels=[(7.68,'Marked curb'),(13.68,'Lawn step'),(13.92,'Porch base'),(22.68,'First step top')]
 # Adjacent lawn/porch lines deliberately share a single label.
 for x,label in levels:ax.axvline(x,color='#d2d8dd',lw=1,zorder=0)
 for x,label in [(7.68,'Curb'),(13.8,'Lawn step / porch base'),(22.68,'First step top')]:ax.text(x,1.01,label,transform=ax.get_xaxis_transform(),ha='center',fontsize=9,color=GRAY)
 labels=[]
 for y,e in enumerate(events):
  labels.append(e['episode_id'].replace('-e01',' e01').replace('-e02',' e02'))
  if y%2==0:ax.axhspan(y-.5,y+.5,color='#f4f6f8',zorder=0)
  x=e['level_in_vs_sw'];kind=e['evidence_kind'];lo=e.get('range_low_in');hi=e.get('range_high_in')
  if x is not None:
   inferred=kind in ('reconstruction','inferred_peak','inferred_lower_bound','historical_bound')
   color=GRAY if inferred else (TEAL if kind in ('photo','lower_bound') else NAVY)
   if lo is not None and hi is not None:ax.plot([lo,hi],[y,y],color=color,lw=2)
   marker='^' if 'lower_bound' in kind else ('s' if kind=='photo' else 'o')
   ax.plot(x,y,marker=marker,color=color,mfc='white' if inferred else color,ms=6,zorder=3)
   if 'lower_bound' in kind:ax.annotate('',(x+1.4,y),(x+.15,y),arrowprops=dict(arrowstyle='->',color=color,lw=1))
   ax.text(x,y-.22,f'{x:.1f}',ha='center',fontsize=8,color=color)
  if e.get('model_hindcast_in') is not None:ax.plot(e['model_hindcast_in'],y,'D',color=ORANGE,ms=5)
  # Full method notes remain in JSON/Markdown; concise row annotations fit the figure.
  notes={
   '2025-08-21-e01':'August flood; Aug21 date tentative; local height unknown',
   '2025-10-30-e01':'20.8 reconstruction; post-peak photo floor ~13.5',
   '2025-12-19-e01':'08:12 landmark bracket; not a measured crest',
   '2026-04-17-e01':'Light / ~2-inch memory; height reference unknown',
   '2026-04-18-e01':'Likely lawn-step level; recollection + gauge; may be higher',
   '2026-05-18-e01':'SE/SW overflowed; no standardized crest point',
   '2026-05-30-e01':'Dry check', '2026-05-30-e02':'SE grate overtopped; post-peak report',
   '2026-05-31-e01':'Below-grate readings; dry roadway',
   '2026-06-13-e01':'Post-peak NE-grate residue; lower bound',
   '2026-06-14-e01':'20:07–20:14 corner-tape mean + sample spread',
   '2026-06-15-e01':'21:08–21:14 corner-tape mean + sample spread',
   '2026-07-06-e01':'Accepted reference window; not an exact tape crest',
   '2026-07-09-e01':'Tape-derived level; alternate reference differs 0.55 in',
   '2026-07-13-e01':'19:48–19:49 corner tapes; small flood',
   '2026-07-18-e01':'Tape-derived level', '2026-08-03-e01':'Reported bracket',
   '2026-08-07-e01':'Missed crest reconstructed from recession',
   '2026-08-10-e01':'Photo estimate at NE/NW pavement',
   '2026-08-11-e01':'Photo bracket; upper endpoint less certain',
   '2026-08-12-e01':'NE/NW pavement wet; lower bound',
   '2026-08-13-e01':'NE/NW pavement wet; lower bound',
   '2026-08-27-e01':'Driveway proxy ~13.8; missed crest; hindcast 16.4',
   '2026-09-01-e01':'Photo/landmark bracket',
   '2026-09-13-e01':'Dawn: lawn-step level', '2026-09-13-e02':'Later: near-curb bracket',
   '2026-09-25-e01':'Reported dry window; gate context',
   '2026-09-26-e01':'Morning: tape peak; entire garage flooded',
   '2026-09-26-e02':'Evening: explicit curb +0.5–1-inch bracket',
   '2026-09-27-e01':'Morning: tape peak; ~90% garage flooded'}
  ax.text(1.02,y,notes[e['episode_id']],transform=ax.get_yaxis_transform(),va='center',fontsize=9,color='#333d47')
 ax.set_yticks(range(len(events)),labels);ax.set_ylim(len(events)-.4,-.7);ax.set_xlim(-.6,28)
 ax.set_xticks(range(0,29,2));ax.set_xlabel('Water level in inches above the SW grate (3.52 ft NAVD88)');ax.grid(axis='x',alpha=.18)
 fig.suptitle('More floods belong in the record than in the original anchor comparison',x=.07,y=.98,ha='left',fontsize=19,fontweight='bold')
 fig.text(.07,.943,'30 registered episodes and observation windows • chronological order • evidence types kept distinct',fontsize=12)
 fig.text(.07,.922,'Blank position means the local height is not established. It does not mean no flooding.',fontsize=11,color=GRAY)
 handles=[Line2D([],[],marker='o',ls='',color=NAVY,label='Tape / reported landmark or bracket'),Line2D([],[],marker='s',ls='',color=TEAL,label='Photo interpretation'),Line2D([],[],marker='o',mfc='white',ls='',color=GRAY,label='Historical / inferred reference'),Line2D([],[],marker='^',ls='',color=TEAL,label='Lower bound (arrow extends right)'),Line2D([],[],marker='D',ls='',color=ORANGE,label='Historical model hindcast')]
 fig.legend(handles=handles,loc='lower left',bbox_to_anchor=(.07,.035),ncol=3,frameon=False,fontsize=10)
 fig.text(.07,.018,'Whiskers are evidence ranges, not confidence intervals. August27 proxy is not a surveyed bound. Hindcasts are mixed vintages, not as-issued skill.',fontsize=9,color=GRAY)
 for ext in ('png','pdf'):fig.savefig(A/f'expanded_events.{ext}',dpi=180)
 plt.close(fig)

def gauge(name):
 d=json.loads((A/'historical-gauge-sources'/f'{name}.json').read_text())
 return [(utc_to_station_local(r['t']+'+00:00'),float(r['v']),r.get('q'),r.get('f')) for r in d['data'] if r['v']]

def june(date):
 folder=ROOT/f'assets/observations/{date}/analysis';d=json.loads((folder/'observations.json').read_text());obs=d['observations']
 t=[parse_station_local_time(o['time_local']) for o in obs]
 lower=min(t)-dt.timedelta(minutes=50);upper=max(t)+dt.timedelta(minutes=50)
 sh=[r for r in gauge('june-sandy-hook') if lower<=r[0]<=upper];ba=[r for r in gauge('june-battery') if lower<=r[0]<=upper]
 # Sandy Hook datum conversion is repo's 2.82 ft MLLW–NAVD88 offset; never apply it to Battery.
 st=np.array([r[0].timestamp() for r in sh]);sv=np.array([r[1]-2.82 for r in sh])
 fig,(ax,rx)=plt.subplots(2,1,figsize=(12,8),sharex=True,gridspec_kw={'height_ratios':[2.2,1]});fig.subplots_adjust(top=.80,bottom=.16,hspace=.16,right=.97,left=.1)
 ax.plot([r[0] for r in sh],sv,color=GRAY,label='Sandy Hook gauge − 2.82 ft (bay reference)',lw=2)
 colors={'grate_NE':'#286090','grate_NW':'#3d9693','grate_SE':'#b16427','grate_SW':'#973b70','grate_bay_ave_upstream':'#aaaaaa','sidewalk_under_walkway_lawn_step':'#697834'}
 residual=[]
 for key,color in colors.items():
  selected=[o for o in obs if o['landmark']==key]
  if not selected:continue
  tt=[parse_station_local_time(o['time_local']) for o in selected];vv=[o['level_navd88'] for o in selected];marker='x' if 'upstream' in key else 'o'
  ax.scatter(tt,vv,label=key.replace('grate_','').replace('sidewalk_under_walkway_lawn_step','Sidewalk under lawn step'),s=33,color=color,marker=marker,zorder=5)
  res=(np.array(vv)-np.interp([x.timestamp() for x in tt],st,sv))*12
  rx.scatter(tt,res,color=color,marker=marker,s=26)
  residual.extend(dict(csv_row=o['csv_row'],street_minus_interpolated_sh_in=float(v)) for o,v in zip(selected,res))
 for val,name in [(3.80,'NE/NW grate'),(4.16,'Curb'),(4.33,'Sidewalk below lawn step'),(4.54,'Intersection crown')]:
  ax.axhline(val,lw=.6,color='#b9c0c5',ls=':');ax.text(lower,val+.006,name,fontsize=8,color=GRAY)
 ax.set_ylim(3.65,4.66);ax.set_ylabel('Water level (ft NAVD88)');ax.legend(loc='lower left',bbox_to_anchor=(0,1.015),ncol=3,fontsize=8,frameon=False)
 rx.axhline(0,color=GRAY,lw=1);rx.set_ylabel('Street − bay\n(inches)');rx.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M',tz=STATION_TZ));rx.set_xlabel(f'{date} • America/New_York (EDT)');rx.grid(alpha=.2)
 fig.suptitle(f'{date}: measured street water through the evening high tide',fontsize=17,fontweight='bold',y=.97)
 fig.text(.1,.913,'Tape points retain their actual observation times; the gray line is bay water, not a street observation.',fontsize=10)
 fig.text(.1,.886,'No rain, wind or surge correction is added to the tape readings. Upstream grate is uneven and shown separately.',fontsize=10)
 fig.text(.1,.045,'Residuals use linear interpolation between 6-minute Sandy Hook readings. They do not isolate wind, rain, gate effects or measurement error.\nNOAA later-retrieved verified data; not an as-issued forecast test. Full methods and Battery timing check: README.md.',fontsize=9,color=GRAY)
 for ext in ('png','pdf'):fig.savefig(folder/f'field_hydrograph.{ext}',dpi=180)
 plt.close(fig)
 stats={}
 for name in ('june-sandy-hook','june-battery'):
  rr=[r for r in gauge(name) if str(r[0].date())==date];peak=max(rr,key=lambda r:r[1]);stats[name]=dict(peak_mllw=peak[1],time_local=peak[0].isoformat(),samples=len(rr),quality_codes=sorted({r[2] for r in rr}),max_adjacent_change_ft=max(abs(b[1]-a[1]) for a,b in zip(rr,rr[1:])),flags=sorted({r[3] for r in rr}))
 result=dict(gauges=stats,peak_cluster=d['peak_cluster'],residuals=residual,qualification='Different stations have different MLLW datums. Battery is a timing/shape cross-check only here; no datum-unaware height subtraction or automatic gauge replacement.')
 (folder/'results.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
 expanded()
 for date in ('2026-06-14','2026-06-15'):june(date)
