import subprocess, json, sys
repo = "."
hs = subprocess.run(["git","log","--reverse","--format=%H %cI","--","data/alert_state.json"],cwd=repo,capture_output=True,text=True).stdout.split("\n")
hs = [h.split() for h in hs if h.strip()]
p = subprocess.Popen(["git","cat-file","--batch"],cwd=repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
rows=[]
for h,ts in hs:
    p.stdin.write(f"{h}:data/alert_state.json\n".encode()); p.stdin.flush()
    hdr = p.stdout.readline().split()
    if len(hdr)<3 or hdr[1]!=b"blob":
        continue
    n=int(hdr[2]); body=p.stdout.read(n); p.stdout.read(1)
    try: d=json.loads(body)
    except Exception: continue
    rows.append((h[:9],ts,d))
json.dump(rows, open(sys.argv[1],"w"))
print(len(rows))
