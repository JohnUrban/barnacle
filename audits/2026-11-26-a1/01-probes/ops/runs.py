import json,sys,datetime as dt,collections,statistics as st
S=sys.argv[1]
def p(t): return dt.datetime.strptime(t,'%Y-%m-%dT%H:%M:%SZ')
def pct(v,q):
    v=sorted(v); return v[min(len(v)-1,int(q*len(v)))]
for w in ['nowcast.yml','daily_forecast.yml','nbm_qmd.yml','ci.yml','pages']:
    d=json.load(open(f'{S}/runs_{w}.json'))
    d.sort(key=lambda r:r['createdAt'])
    print('==',w,len(d),d[0]['createdAt'],'->',d[-1]['createdAt'])
    print('  conclusions',collections.Counter((r['event'],r['conclusion']) for r in d))
    dur=[(p(r['updatedAt'])-p(r['startedAt'])).total_seconds() for r in d if r['conclusion']=='success']
    print(f'  success duration s: median={st.median(dur):.0f} p90={pct(dur,.9):.0f} p99={pct(dur,.99):.0f} max={max(dur):.0f}')
    sched=[p(r['createdAt']) for r in d if r['event']=='schedule']
    if len(sched)>2:
        g=[(b-a).total_seconds()/60 for a,b in zip(sched,sched[1:])]
        print(f'  schedule start gaps min: n={len(g)} median={st.median(g):.1f} p90={pct(g,.9):.1f} p99={pct(g,.99):.1f} max={max(g):.1f}')
        big=sorted(zip(g,sched,sched[1:]),reverse=True)[:6]
        for x,a,b in big: print(f'     {x:.0f} min {a} -> {b}')
    bad=[r for r in d if r['conclusion'] not in('success',)]
    for r in bad[-25:]: print('  NONSUCCESS',r['createdAt'],r['event'],r['conclusion'],r['databaseId'])
