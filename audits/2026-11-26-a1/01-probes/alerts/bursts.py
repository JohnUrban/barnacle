import json, sys, re, datetime as dt
from collections import defaultdict
rows = json.load(open(sys.argv[1]))
# group state commits by 'updated' hour (UTC)
byhour=defaultdict(list)
for h,ts,d in rows:
    u=d.get("updated") or ""
    if u: byhour[u[:13]].append((h,u,d))
runs=[]
for hr in sorted(byhour):
    if len(byhour[hr])>=4:
        ds=byhour[hr]
        runs.append((hr,len(ds),ds[0][2].get("rank"),ds[0][2].get("sig"), ds[0][2].get("label")))
print("hours with >=4 forecast runs (state commits):", len(runs))
for r in runs: print(r)
