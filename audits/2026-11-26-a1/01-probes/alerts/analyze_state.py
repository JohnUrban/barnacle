import json, sys
rows = json.load(open(sys.argv[1]))
print("first", rows[0][1], "last", rows[-1][1])
# 1. rank increased, sig same, no new send
print("\n== rank UP with same sig and NO send (missed escalation candidates) ==")
prev=None
for h,ts,d in rows:
    if prev:
        ph,pts,pd = prev
        if (d.get("rank",0) > pd.get("rank",0) and pd.get("rank",0)>0 and d.get("last_sent_ts")==pd.get("last_sent_ts")):
            print(h, ts, "rank", pd.get("rank"),"->",d.get("rank"), "| sig", pd.get("sig"),"->",d.get("sig"), "| lsr", d.get("last_sent_rank"), "| lss", d.get("last_sent_sig"), "| base", d.get("base_sends_today"), "| label", d.get("label"))
    prev=(h,ts,d)
print("\n== last_sent_rank trajectory ==")
prev=None
for h,ts,d in rows:
    v=d.get("last_sent_rank")
    if v!=prev:
        print(h,ts,"last_sent_rank",prev,"->",v, "| rank", d.get("rank"), d.get("sig"))
        prev=v
print("\n== sig != last_sent_sig while rank>0 (held / capped / unsent periods): first and last of each run ==")
run=None
for h,ts,d in rows:
    from re import sub
    lss = sub(r"^\d+\|","",d.get("last_sent_sig") or "")
    sg = sub(r"^\d+\|","",d.get("sig") or "")
    key=(sg,lss)
    cond = d.get("rank",0)>0 and "last_sent_sig" in d and sg!=lss
    if cond:
        if run and run["key"]==key:
            run["last"]=(h,ts); run["n"]+=1
        else:
            if run: print(run["first"],"..",run["last"][1],"n",run["n"],"rank",run["rank"],"| sig",run["key"][0],"| last_sent",run["key"][1],"| base",run["base"])
            run={"key":key,"first":(h,ts),"last":(h,ts),"n":1,"rank":d.get("rank"),"base":d.get("base_sends_today") or d.get("sends_today")}
    else:
        if run: print(run["first"],"..",run["last"][1],"n",run["n"],"rank",run["rank"],"| sig",run["key"][0],"| last_sent",run["key"][1],"| base",run["base"])
        run=None
