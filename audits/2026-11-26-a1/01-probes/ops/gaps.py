import sys, datetime as dt, statistics as st, collections
rows=[]
for line in open(sys.argv[1]):
    h,t,a,s=line.rstrip('\n').split('|',3)
    rows.append((dt.datetime.strptime(t,'%Y-%m-%dT%H:%M:%SZ'),h,a,s))
rows.sort()
end=rows[-1][0]
def pct(v,p):
    v=sorted(v); 
    return v[min(len(v)-1,int(p*len(v)))]
def report(name, sel, days, thresholds):
    start=end-dt.timedelta(days=days)
    ts=[r[0] for r in rows if sel(r) and r[0]>=start]
    g=[(b-a).total_seconds()/60 for a,b in zip(ts,ts[1:])]
    print(f"== {name}: last {days}d n={len(ts)} median={st.median(g):.1f} p90={pct(g,.9):.1f} p99={pct(g,.99):.1f} max={max(g):.1f}")
    for th in thresholds:
        print(f"   gaps > {th} min: {sum(1 for x in g if x>th)}")
    big=sorted(zip(g,ts,ts[1:]),reverse=True)[:8]
    for x,a,b in big: print(f"   {x:.0f} min  {a} -> {b}")
    return ts
hourly=lambda r: r[2]=='github-actions[bot]' and (r[3].startswith('hourly update') or r[3].startswith('daily forecast'))
ts=report('hourly forecast commits', hourly, 14, [75,90,120,180])
# start delay: commit minute past the labelled hour
d=[]
start=end-dt.timedelta(days=14)
for r in rows:
    if r[2]=='github-actions[bot]' and r[3].startswith('hourly update') and r[0]>=start:
        lab=dt.datetime.strptime(r[3][len('hourly update '):len('hourly update ')+16].replace(' UTC',''),'%Y-%m-%d %H:%M')
        d.append((r[0]-lab).total_seconds()/60)
print(f"   commit lateness vs labelled hour: n={len(d)} median={st.median(d):.1f} p90={pct(d,.9):.1f} max={max(d):.1f} min={min(d):.1f}")
# hours with no hourly commit in 14 d
hrs=collections.Counter()
for r in rows:
    if hourly(r) and r[0]>=start: hrs[r[0].replace(minute=0,second=0)]+=1
tot=14*24
print("   distinct clock-hours with >=1 hourly commit:",len(hrs),"of",tot)
# labelled hours
labs=set()
for r in rows:
    if r[2]=='github-actions[bot]' and r[3].startswith('hourly update') and r[0]>=start: labs.add(r[3][14:30])
print("   distinct labelled hours:",len(labs))
report('outlook guidance', lambda r: r[3].startswith('outlook guidance'), 14, [200,400])
report('nowcast GH arm (all)', lambda r: r[2]=='barnacle-nowcast', 14, [70,90,120])
report('nowcast local arm (all)', lambda r: r[2]=='barnacle-local', 14, [70,90,120,480])
report('nowcast either arm', lambda r: r[2] in('barnacle-nowcast','barnacle-local'), 14, [70,90,120])
report('ANY commit', lambda r: True, 14, [60,90])
# per day counts
c=collections.Counter()
for r in rows:
    c[(r[0].date(),r[2])]+=1
days=sorted({k[0] for k in c})[-16:]
for dday in days:
    print(dday, {a:c[(dday,a)] for a in ['github-actions[bot]','barnacle-nowcast','barnacle-local','JohnUrban'] })
