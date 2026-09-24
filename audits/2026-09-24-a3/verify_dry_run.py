import contextlib,copy,importlib.util,io,json,pathlib,sys,tempfile
from unittest.mock import patch
import argparse
_parser=argparse.ArgumentParser()
_parser.add_argument('--repo',required=True)
_parser.add_argument('--out',required=True)
_args=_parser.parse_args()
ROOT=pathlib.Path(_args.repo).resolve();sys.path.insert(0,str(ROOT))
from forecast import flood_forecast_daily as ff,wind_shadow as ws
spec=importlib.util.spec_from_file_location('fixture',ROOT/'tests/test_wind_shadow.py');fx=importlib.util.module_from_spec(spec);spec.loader.exec_module(fx)
results={}
for flag in ('--no-send','--dry-run'):
 with tempfile.TemporaryDirectory() as td, contextlib.ExitStack() as stack:
  f=fx._forecast()
  stack.enter_context(patch.object(sys,'argv',['forecast',flag,'--write-json',str(pathlib.Path(td)/'forecast.json')]))
  stack.enter_context(patch.object(ff,'build_forecast',return_value=f))
  for name in ('_attach_summary_and_confidence','_save_surge_state','append_predictions_log','append_day_risk_log'):
   stack.enter_context(patch.object(ff,name))
  stack.enter_context(patch.object(ff._replay_archive,'append'))
  stack.enter_context(patch.object(ff._outlook,'append_outlook_log'))
  stack.enter_context(patch.object(ff._outlook,'outlook_log_rows',return_value=[]))
  stack.enter_context(patch.object(ff,'render_email',return_value=('fixture','body','html')))
  stack.enter_context(patch.object(ff,'evaluate_alert',return_value={'send':False,'reason':'fixture'}))
  stack.enter_context(patch.object(ff,'evaluate_sms_gate',return_value={'send':False,'reason':'fixture'}))
  mocked=stack.enter_context(patch.object(ws,'run',return_value='shadow invocation intercepted; no record'))
  buf=stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
  ff.main()
  results[flag]={'shadow_invocations':mocked.call_count,'forecast_json_written':(pathlib.Path(td)/'forecast.json').exists(),'log':buf.getvalue()}
p=pathlib.Path(_args.out);p.write_text(json.dumps(results,indent=2)+'\n');print(p.read_text())
