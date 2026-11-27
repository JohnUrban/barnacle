import json, subprocess, sys
repo='.'
rows=[l.split(' ',2) for l in open(sys.argv[1]).read().splitlines()]
for h,ci,s in reversed(rows):
    try:
        j=json.loads(subprocess.check_output(['git','-C',repo,'show',f'{h}:docs/forecast.json']))
    except Exception as e:
        print(h[:9],'ERR',e); continue
    ws=j.get('water_series') or []
    mx=max(ws,key=lambda p:p.get('water_navd88',-9)) if ws else {}
    wsi=j.get('water_series_input') or {}
    print(h[:9], j.get('generated_utc'), 'today_peak',j.get('today_peak_water_navd88'),j.get('today_peak_time'), j.get('today_regime'),
          '| series max',mx.get('water_navd88'),mx.get('time'),'tide',mx.get('tide_navd88'),'pluv',mx.get('pluvial_navd88'),
          '| surge',wsi.get('surge_ft'), wsi.get('status'),
          '| worst', j.get('peak_forecast_observed_mllw'), j.get('peak_time_local'), j.get('surge_source'), (j.get('depths_in') or {}).get('regime'),
          '| pluv', (j.get('pluvial_risk') or {}).get('level'), (j.get('pluvial_risk') or {}).get('peak_rain_rate_24h_in_hr'), (j.get('pluvial_risk') or {}).get('cumulative_rain_24h_in'),
          '| degraded', j.get('degraded_inputs'))
