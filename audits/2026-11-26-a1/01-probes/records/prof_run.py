import os, sys, json, unittest, socket, threading
ROOT='.'
CALLED=set()
def prof(frame, event, arg):
    if event=='call':
        fn=frame.f_code.co_filename
        if fn.startswith(ROOT) and '/tests/' not in fn:
            CALLED.add((fn[len(ROOT)+1:], frame.f_code.co_name, frame.f_code.co_firstlineno))
def blocked(*a, **k): raise OSError('network blocked by audit probe')
socket.socket.connect=blocked; socket.getaddrinfo=blocked
os.environ['BARNACLE_REQUIRE_GRIB']='1'
os.chdir(ROOT); sys.path.insert(0,ROOT)
suite=unittest.defaultTestLoader.discover('tests')
threading.setprofile(prof); sys.setprofile(prof)
res=unittest.TextTestRunner(verbosity=0,stream=open(sys.argv[1]+'/prof_unittest.txt','w')).run(suite)
sys.setprofile(None)
json.dump({'ran':res.testsRun,'fail':len(res.failures),'err':len(res.errors),'called':sorted(CALLED)}, open(sys.argv[1]+'/prof.json','w'))
