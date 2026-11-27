import datetime as dt, json, sys, os
from unittest import mock
sys.path.insert(0, ".")
from forecast import flood_forecast_daily as ff
from forecast import nowcast
UTC = dt.timezone.utc
S = os.path.dirname(os.path.abspath(__file__))
L = lambda n: json.load(open(os.path.join(S, n)))

print("R9 nowcast.run() with synthetic radar, bay held at 6.3 ft NAVD88 (no network, _write captured)")
def run_with(bay, rate):
    now = dt.datetime(2026, 11, 27, 1, 47, tzinfo=UTC)
    frames = [(dt.datetime(2026, 11, 27, 0, 44) + dt.timedelta(minutes=6 * i), f"s{i}") for i in range(11)]
    cap = {}
    with mock.patch.object(nowcast, "current_bay", return_value=(bay, "observed")), \
         mock.patch.object(nowcast, "latest_frames", return_value=frames), \
         mock.patch.object(nowcast, "box_rate", return_value=rate), \
         mock.patch.object(nowcast, "_write", side_effect=lambda p, n=None: cap.update(p)):
        nowcast.run(now)
    return cap
for bay, rate in ((6.3, 0.0), (6.3, 0.27), (6.3, 0.30), (6.3, 0.31), (5.43, 0.07), (2.9, 0.31), (2.9, 0.26)):
    p = run_with(bay, rate)
    print(f"  bay {bay} ft, rain {rate} in/hr -> active={p.get('active')} drain={p.get('drain_in_hr')} street_now_in={p.get('street_now_in')} peak_proj_in={p.get('peak_proj_in')} trend={p.get('trend')} regime={p.get('regime_display')} keys_has_street={'street_now_in' in p}")

print("R11 the two real payloads either side of the first value (git 1232d2ad6 01:47Z, d46b9c1d0 01:55Z)")
st = L("state_0108.json")
for name, now in (("nc_1414.json", dt.datetime(2026, 11, 26, 14, 15, tzinfo=UTC)), ("nc_0147.json", dt.datetime(2026, 11, 27, 1, 48, tzinfo=UTC)), ("nc_0155.json", dt.datetime(2026, 11, 27, 1, 56, 36, tzinfo=UTC))):
    nc = L(name)
    print(f"  {name}: active={nc.get('active')} bay={nc.get('bay_navd88')} recent_max={nc.get('recent_max_in_hr')} street_now_in={nc.get('street_now_in')}")
    print("    contract:", repr(ff._nowcast_contract_reason(nc, now)))
    g = ff.evaluate_sms_gate({}, state=st, now_utc=now, nowcast=nc, channel="ntfy")
    print("    imminent gate:", g["send"], "|", g["reason"], "| class", g["class"], g["phrase"])
    if g["send"]:
        print("    ntfy body:", ff.build_sms_imminent(g))
        with mock.patch.object(ff, "_radar_live_state", return_value=nc):
            rank, label, sig = ff.compute_alert_level({"all_tides": [{"time": "2026-11-26 21:07-05:00", "hours_from_now": 0.2, "forecast_peak_mllw": 8.8, "depths_in": {"regime": "severe"}}], "pluvial_risk": {}})
        print("    base label:", label, "| sig:", sig, "| ntfy title:", ff._ntfy_header_text(f"Barnacle flood alert ({label})"))
        print("    of the +%.1f in 'radar' street stage, bay head alone = %.1f in" % (nc["street_now_in"], (nc["bay_navd88"] - 3.52) * 12))

print("R12 a third base alert on 2026-11-26 with the committed state (5857208e4, base count 2/2)")
st = L("state_0156.json")
f = {"all_tides": [{"time": "2026-11-26 21:07-05:00", "hours_from_now": -1.0, "forecast_peak_mllw": 8.8, "depths_in": {"regime": "severe"}},
                   {"time": "2026-11-27 09:23-05:00", "hours_from_now": 11.3, "forecast_peak_mllw": 8.4, "depths_in": {"regime": "severe"}}],
     "pluvial_risk": {"level": "elevated", "nws_flood_alerts": [{"event": "Flash Flood Warning", "onset": "2026-11-26T21:40:00-05:00"}]}}
def ev(forecast, state, now, nc=None):
    with mock.patch.object(ff, "_radar_live_state", return_value=nc):
        return ff.evaluate_alert(forecast, state=state, now_utc=now)
d = ev(f, st, dt.datetime(2026, 11, 27, 3, 8, tzinfo=UTC)); print("  22:08 EST, both tides severe + new FFW:", d["send"], "|", d["sig"], "|", d["reason"])
f2 = {"all_tides": f["all_tides"][1:], "pluvial_risk": {}}
for now in (dt.datetime(2026, 11, 27, 4, 8, tzinfo=UTC), dt.datetime(2026, 11, 27, 5, 8, tzinfo=UTC), dt.datetime(2026, 11, 27, 12, 8, tzinfo=UTC)):
    d = ev(f2, st, now); print(f"  {now.astimezone(ff.STATION_TZ):%m-%d %H:%M} EST, evening tide gone, severe 09:23 tide tops the table:", d["send"], "|", d["reason"])
f3 = {"all_tides": [], "pluvial_risk": {"level": "elevated", "nws_flood_alerts": [{"event": "Flash Flood Warning", "onset": "2026-11-26T21:40:00-05:00"}]}}
for now in (dt.datetime(2026, 11, 27, 3, 8, tzinfo=UTC), dt.datetime(2026, 11, 27, 5, 8, tzinfo=UTC)):
    d = ev(f3, st, now); print(f"  {now.astimezone(ff.STATION_TZ):%m-%d %H:%M} EST, only a Flash Flood Warning (rank 3 < last tide gone):", d["send"], "|", d["reason"])
