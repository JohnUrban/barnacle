import json,sys,datetime as dt,collections,statistics as st
S=sys.argv[1]
def p(t): return dt.datetime.strptime(t,'%Y-%m-%dT%H:%M:%SZ')
d=json.load(open(f'{S}/runs_pages.json')); d.sort(key=lambda r:r['createdAt'])
perhour=collections.Counter(p(r['createdAt']).replace(minute=0,second=0) for r in d)
v=sorted(perhour.values())
print('pages builds per clock hour: n_hours',len(v),'median',st.median(v),'p90',v[int(.9*len(v))],'max',v[-1], 'hours>10:',sum(1 for x in v if x>10))
for h,c in sorted(perhour.items(), key=lambda x:-x[1])[:8]: print('  ',h,c)
# rolling 60-min max
ts=[p(r['createdAt']) for r in d]
mx=0
j=0
for i,t in enumerate(ts):
    while ts[j] < t-dt.timedelta(minutes=60): j+=1
    mx=max(mx,i-j+1)
print('max builds in any rolling 60 min:',mx)
# time from build created to completion for success
ok=[r for r in d if r['conclusion']=='success']
lat=[(p(r['updatedAt'])-p(r['createdAt'])).total_seconds() for r in ok]
lat.sort()
print('create->done s median',st.median(lat),'p90',lat[int(.9*len(lat))],'p99',lat[int(.99*len(lat))],'max',lat[-1])
# gaps between successful deploy completions
done=sorted(p(r['updatedAt']) for r in ok)
g=[(b-a).total_seconds()/60 for a,b in zip(done,done[1:])]
print('gap between successful deploys min: median',st.median(g),'max',max(g))
for x,a,b in sorted(zip(g,done,done[1:]),reverse=True)[:5]: print('   %.0f'%x,a,b)
for r in d:
    if r['conclusion']=='failure': print('FAIL',r['createdAt'],r['updatedAt'],r['databaseId'],r['headSha'][:9])
long=[r for r in ok if (p(r['updatedAt'])-p(r['createdAt'])).total_seconds()>150]
for r in long[-10:]: print('SLOW',r['createdAt'],(p(r['updatedAt'])-p(r['createdAt'])).total_seconds())
