#!/usr/bin/env python3
"""Round07 figure order probe. Usage: python 07-figure-probe.py /isolated/candidate
No ledger writes; figure output writes are mocked.
"""
import contextlib,importlib.util,io,json,sys
from pathlib import Path
from unittest import mock
root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root))
p=root/'assets/observations/2026-09-27/analysis/event10_hydrographs.py'
spec=importlib.util.spec_from_file_location('figreview',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from matplotlib.axes import Axes
from matplotlib.figure import Figure
rows=m.ledger_rows(); target=rows[219]
assert target[1]['observed_depth_in']=='-0.4'
original=Axes.plot

def run(seq):
 counts=[]
 def spy(self,*args,**kwargs):
  if kwargs.get('color')=='#b45309' and kwargs.get('lw')==1.6:
   counts.append([str(args[0][0]),list(args[1])])
  return original(self,*args,**kwargs)
 with mock.patch.object(m,'ledger_rows',return_value=seq),mock.patch.object(Axes,'plot',spy),mock.patch.object(Figure,'savefig'):
  with contextlib.redirect_stdout(io.StringIO()):
   m.main()
 return counts
base=run(rows); reordered=run([x for x in rows if x is not target]+[target])
out={'original_order_range_whiskers':base,'same_rows_row221_last_range_whiskers':reordered,'ledger_rows_changed':False}
print(json.dumps(out))
