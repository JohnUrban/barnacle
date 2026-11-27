import csv, re, sys, collections, json
R='./'
rows=list(csv.DictReader(open(R+'data/labeled_observations.csv',newline='')))
print('rows',len(rows))
keys=collections.Counter(r['landmark_key'] for r in rows)
defined={"grate_SW","grate_SE","corner_SE","corner_SW","grate_bay_ave_upstream","gutter_walkway","grate_NE","grate_NW","corner_NE","corner_NW","curb","sidewalk_under_walkway_lawn_step","road_middle","intersection_highpoint","lawn_step","porch_step_base","porch_step1_top","porch_deck"}
print('KEYS not in LANDMARKS:')
for k,c in keys.most_common():
    if k not in defined:
        idx=[i+2 for i,r in enumerate(rows) if r['landmark_key']==k]
        print('  ',repr(k),c,idx[:30])
# timestamps
naive=[];off=[];bad=[]
for i,r in enumerate(rows):
    t=r['observation_time_local']
    if re.search(r'[+-]\d\d:\d\d$',t): off.append(i+2)
    elif re.match(r'^\d{4}-\d\d-\d\dT\d\d:\d\d(:\d\d)?$',t): naive.append(i+2)
    else: bad.append((i+2,t))
print('naive',len(naive),'first',naive[:3],'last',naive[-5:]); print('offset',len(off),'first',off[:5]); print('bad',bad)
# naive after first offset
fo=min(off) if off else None
print('naive rows after first offset row:',[n for n in naive if n>fo])
# order
import datetime
def p(t):
    try: return datetime.datetime.fromisoformat(t)
    except Exception: return None
# observers
print('observer',collections.Counter(r['observer'] for r in rows))
# dup exact time+key
d=collections.defaultdict(list)
for i,r in enumerate(rows): d[(r['observation_time_local'],r['landmark_key'])].append(i+2)
print('DUP time+key:')
for k,v in d.items():
    if len(v)>1:
        deps=[rows[x-2]['observed_depth_in'] for x in v]
        print('  ',k,v,deps)
# full dup
d2=collections.defaultdict(list)
for i,r in enumerate(rows): d2[tuple(r.values())].append(i+2)
print('exact dup rows',[v for v in d2.values() if len(v)>1])
# keyword rows
kw=re.compile(r'supersed|correction|erratum|retract|corrects|withdrawn|replaces',re.I)
print('KEYWORD rows:')
for i,r in enumerate(rows):
    s=' '.join(r.values())
    m=kw.findall(s)
    if m: print('  ',i+2,r['observation_time_local'],r['landmark_key'],r['observer'],sorted(set(x.lower() for x in m)),'|',(r['observed_qualitative'][:90]),'|',r['notes'][:110])
