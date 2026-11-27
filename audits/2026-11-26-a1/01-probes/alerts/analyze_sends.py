import json, sys, re, datetime as dt
from zoneinfo import ZoneInfo
TZ=ZoneInfo("America/New_York")
rows = json.load(open(sys.argv[1]))
norm=lambda s: re.sub(r"^\d+\|","",s or "")
sends=[]
prev=None
for h,ts,d in rows:
    if prev is not None and d.get("last_sent_ts") and d.get("last_sent_ts")!=prev.get("last_sent_ts"):
        sends.append((h,d,prev))
    prev=d
print("total base sends recorded:", len(sends))
since=[s for s in sends if s[1]["last_sent_ts"]>="2026-09-25T11:11:00Z"]
print("since ratchet locked (2026-09-25T11:11Z):", len(since))
from collections import Counter
c=Counter(s[1].get("rank") for s in since); print("by rank at send:", dict(c))
past=[];night=[];comp=[]
for h,d,p in since:
    t=dt.datetime.strptime(d["last_sent_ts"],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    loc=t.astimezone(TZ)
    sig=norm(d.get("last_sent_sig")); old=norm(p.get("last_sent_sig"))
    m=re.search(r"tide:(\d{4}-\d\d-\d\d \d\d:\d\d)([-+]\d\d:\d\d)?",sig)
    lead=None
    if m:
        tt=dt.datetime.fromisoformat(m.group(1).replace(" ","T")+(m.group(2) or "")).astimezone(TZ) if m.group(2) else dt.datetime.fromisoformat(m.group(1).replace(" ","T")).replace(tzinfo=TZ)
        lead=(tt-loc).total_seconds()/3600
        only_tide = sig.startswith("tide:") and "|" not in sig
        if lead<0 and only_tide: past.append((h,loc.strftime("%Y-%m-%d %H:%M %Z"),sig,round(lead,2),d.get("rank")))
    if loc.hour>=20 or loc.hour<7: night.append((h,loc.strftime("%Y-%m-%d %H:%M %Z"),sig,d.get("rank"),None if lead is None else round(lead,1)))
    ob=set(old.split("|")); nb=set(sig.split("|"))
    tb_old={b for b in ob if b.startswith("tide:")}; tb_new={b for b in nb if b.startswith("tide:")}
    if (ob<nb or nb<ob) and d.get("rank",0)<=p.get("rank",0):
        comp.append((h,loc.strftime("%Y-%m-%d %H:%M %Z"),"rank %s->%s"%(p.get("rank"),d.get("rank")),old,"=>",sig))
print("\nPAST-TIDE sends (tide-only sig, tide time before send):")
for x in past: print("  ",x)
print("\nNIGHT sends (20:00-07:00 local):")
for x in night: print("  ",x)
print("\nCOMPOSITION-ONLY 'new event' sends (new sig is strict subset/superset of last-sent sig, rank not higher):")
for x in comp: print("  ",x)
# rank-1 tide spam
r1=[s for s in since if s[1].get("rank")==1]
print("\nrank-1 sends since ratchet:", len(r1), "of", len(since))
days=Counter()
for h,d,p in since:
    t=dt.datetime.strptime(d["last_sent_ts"],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).astimezone(TZ)
    days[t.date().isoformat()]+=1
print("days with >=2 base sends:", sum(1 for v in days.values() if v>=2), "of", len(days), "send-days")
# flip-backs: sig returns to one previously sent within 48h
seen={}
flips=[]
for h,d,p in since:
    sig=norm(d.get("last_sent_sig")); ts=d["last_sent_ts"]
    if sig in seen: flips.append((h,ts,sig,"previously sent",seen[sig]))
    seen[sig]=ts
print("\nRE-SENDS of an identical signature already alerted earlier:")
for x in flips: print("  ",x)
