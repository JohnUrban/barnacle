import builtins, io, os, sys, socket, traceback, json, collections, unittest
ROOT='.'
LOG=collections.defaultdict(set); NET=collections.defaultdict(set); WR=collections.defaultdict(set)
def who():
    for fs in reversed(traceback.extract_stack()):
        if '/tests/' in fs.filename and fs.filename.startswith(ROOT):
            return f"{os.path.basename(fs.filename)}::{fs.name}"
    return '(import/other)'
_open=io.open
def popen(file, mode='r', *a, **k):
    try:
        p=os.path.realpath(os.fspath(file)) if not isinstance(file,int) else None
    except Exception: p=None
    if p and p.startswith(ROOT+'/') and not p.endswith(('.py','.pyc')):
        rel=p[len(ROOT)+1:]
        if any(c in str(mode) for c in 'wax+'):
            WR[rel].add(who())
        elif rel.startswith(('data/','docs/','assets/','history/','model/')) or rel.endswith('.md'):
            LOG[rel].add(who())
    return _open(file, mode, *a, **k)
builtins.open=popen; io.open=popen
_conn=socket.socket.connect
def pconn(self, addr, *a, **k):
    NET[str(addr)].add(who()); raise OSError('network blocked by audit probe')
socket.socket.connect=pconn
_gai=socket.getaddrinfo
def pgai(host,*a,**k):
    NET['dns:'+str(host)].add(who()); raise OSError('dns blocked by audit probe')
socket.getaddrinfo=pgai
os.environ['BARNACLE_REQUIRE_GRIB']='1'
os.chdir(ROOT); sys.path.insert(0,ROOT)
suite=unittest.defaultTestLoader.discover('tests')
res=unittest.TextTestRunner(verbosity=0,stream=_open(sys.argv[1]+'/probe_unittest.txt','w')).run(suite)
out={'ran':res.testsRun,'failures':[str(t[0]) for t in res.failures],'errors':[str(t[0]) for t in res.errors],'skipped':[(str(t[0]),t[1]) for t in res.skipped],
     'net':{k:sorted(v) for k,v in NET.items()},'writes_in_repo':{k:sorted(v) for k,v in WR.items()},'reads':{k:sorted(v) for k,v in LOG.items()}}
_open(sys.argv[1]+'/probe.json','w').write(json.dumps(out,indent=1))
