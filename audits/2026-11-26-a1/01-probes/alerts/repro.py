"""READ-ONLY reproductions. Every call passes state explicitly, mocks the radar
reader, and writes only to a temp dir outside the repo."""
import datetime as dt, json, sys, tempfile, os
from unittest import mock
sys.path.insert(0, ".")
from forecast import flood_forecast_daily as ff
from forecast import nowcast
UTC = dt.timezone.utc
TMP = tempfile.mkdtemp(prefix="alrepro_")
def tide(when, regime, hfn, peak=7.0):
    return {"time": when, "hours_from_now": hfn, "forecast_peak_mllw": peak,
            "depths_in": {"regime": regime}}
def fc(tides, pluv=None):
    return {"all_tides": tides, "pluvial_risk": pluv or {}, "today_regime": "dry"}
def ev(forecast, state, now, nc=None):
    with mock.patch.object(ff, "_radar_live_state", return_value=nc):
        return ff.evaluate_alert(forecast, state=state, now_utc=now)
def persist(decision, delivered=None):
    return ff.persist_alert_state(decision, delivered, path=os.path.join(TMP, "st.json"))
def show(tag, d):
    print(f"  {tag}: send={d['send']} rank={d['rank']} sig={d['sig']!r} reason={d['reason']}")

PROD = {"rank": 1, "sig": "tide:2026-12-05 08:00-05:00", "last_sent_rank": 4,
        "last_sent_sig": "tide:2026-12-05 08:00-05:00", "last_sent_ts": "2026-12-03T14:00:00Z",
        "last_sent_channels": ["email", "ntfy"],
        "base_sends_today": {"date": "2026-12-03", "count": 1}}

print("R1 same tide upgraded street->severe, production-shaped state (last_sent_rank=4)")
now = dt.datetime(2026, 12, 4, 18, 0, tzinfo=UTC)  # 13:00 EST, daytime
d = ev(fc([tide("2026-12-05 08:00-05:00", "severe", 19.0, 8.6)]), PROD, now); show("ratcheted", d)
st2 = dict(PROD, last_sent_rank=1)
d = ev(fc([tide("2026-12-05 08:00-05:00", "severe", 19.0, 8.6)]), st2, now); show("if last_sent_rank were the last-sent rank (1)", d)

print("R2 two severe tides: signature names only the first")
with mock.patch.object(ff, "_radar_live_state", return_value=None):
    print("  ", ff.compute_alert_level(fc([tide("2026-11-26 08:28-05:00", "severe", 3.0, 8.3), tide("2026-11-26 21:07-05:00", "severe", 16.0, 8.6)])))

print("R3 PAST tide (hours_from_now=-0.78) reclassified to street raises an alert")
st = {"rank": 1, "sig": "tide:2026-10-26 08:09-04:00", "last_sent_rank": 4, "last_sent_sig": "tide:2026-10-26 08:09-04:00",
      "last_sent_ts": "2026-10-25T11:09:48Z", "base_sends_today": {"date": "2026-10-25", "count": 1}}
f = fc([tide("2026-10-25 07:29-04:00", "street", -0.78, 6.3744), tide("2026-10-26 08:09-04:00", "street", 23.89, 6.63)])
now = dt.datetime(2026, 10, 25, 12, 15, 45, tzinfo=UTC)
d = ev(f, st, now); show("08:15 EDT", d)
with mock.patch.object(ff, "_radar_live_state", return_value=None), mock.patch.object(ff, "headline_for", return_value=("x", "")):
    print("   ntfy/base text:", ff.build_sms_text(f))

print("R4 composition-only change: pluv bit drops, same tide, same rank")
st = {"rank": 1, "sig": "tide:2026-11-07 06:00-05:00|pluv", "last_sent_rank": 4, "last_sent_sig": "tide:2026-11-07 06:00-05:00|pluv",
      "last_sent_ts": "2026-11-06T13:07:55Z", "base_sends_today": {"date": "2026-11-06", "count": 2}}
f = fc([tide("2026-11-07 06:00-05:00", "street", 5.9, 6.5)])
show("2026-11-06 23:08 EST (cap 2/2)", ev(f, st, dt.datetime(2026, 11, 7, 4, 8, tzinfo=UTC)))
show("2026-11-07 00:07 EST (cap reset)", ev(f, st, dt.datetime(2026, 11, 7, 5, 7, tzinfo=UTC)))

print("R5 radar signature carries the calendar day: local midnight makes a 'new event'")
nc = {"nowcast_schema_version": ff.NOWCAST_SCHEMA_VERSION, "active": True, "radar_quality": "ok", "trend": "falling",
      "street_now_in": 5.2, "peak_proj_in": 7.2, "day_local": "2026-09-21", "source_latest_utc": "2026-09-21T04:10:00Z"}
st = {"rank": 1, "sig": "radar:2026-09-20:street", "last_sent_rank": 3, "last_sent_sig": "radar:2026-09-20:street",
      "last_sent_ts": "2026-09-21T03:16:11Z", "base_sends_today": {"date": "2026-09-20", "count": 2}}
show("00:15 EDT", ev(fc([]), st, dt.datetime(2026, 9, 21, 4, 15, tzinfo=UTC), nc))

print("R6 quiet hours vs a SEVERE tide tomorrow 09:23, first seen 22:00")
st0 = {"rank": 4, "sig": "tide:2026-11-26 21:07-05:00", "last_sent_rank": 4, "last_sent_sig": "tide:2026-11-26 21:07-05:00",
       "last_sent_ts": "2026-11-26T16:09:13Z", "base_sends_today": {"date": "2026-11-26", "count": 1}}
for label, when, hfn in (("tide 09:23", "2026-11-27 09:23-05:00", 11.4), ("tide 07:10", "2026-11-27 07:10-05:00", 9.2), ("tide 06:50", "2026-11-27 06:50-05:00", 8.8)):
    f = fc([tide(when, "severe", hfn, 8.6)])
    for hh, mm, day in ((3, 0, 27), (11, 59, 27), (12, 8, 27)):
        now = dt.datetime(2026, 11, day, hh, mm, tzinfo=UTC)
        d = ev(f, st0, now); show(f"{label} @ {now.astimezone(ff.STATION_TZ):%H:%M} EST", d)

print("R7 quiet-hours hold consumes the appearance edge; identical signature is never delivered")
st = {"rank": 0, "sig": "", "last_sent_rank": 4, "last_sent_sig": "pluv", "last_sent_ts": "2026-11-11T23:07:09Z",
      "base_sends_today": {"date": "2026-11-11", "count": 1}}
f = fc([], {"level": "elevated"})
d1 = ev(f, st, dt.datetime(2026, 11, 15, 3, 0, tzinfo=UTC)); show("22:00 EST first sight", d1)
held = persist(d1)            # what _main_core does on a no-send run
d2 = ev(f, held, dt.datetime(2026, 11, 15, 12, 10, tzinfo=UTC)); show("07:10 EST next morning", d2)
d3 = ev(f, persist(d2), dt.datetime(2026, 11, 15, 18, 10, tzinfo=UTC)); show("13:10 EST", d3)

print("R8 pathway masking: Flash Flood Warning under a severe tide never enters the signature")
f = fc([tide("2026-11-26 21:07-05:00", "severe", 2.0, 8.8)], {"level": "elevated", "nws_flood_alerts": [{"event": "Flash Flood Warning", "onset": "2026-11-26T19:30:00-05:00"}]})
st = {"rank": 4, "sig": "tide:2026-11-26 21:07-05:00", "last_sent_rank": 4, "last_sent_sig": "tide:2026-11-26 21:07-05:00",
      "last_sent_ts": "2026-11-26T16:09:13Z", "base_sends_today": {"date": "2026-11-26", "count": 1}}
d = ev(f, st, dt.datetime(2026, 11, 27, 0, 40, tzinfo=UTC)); show("19:40 EST", d)
st_path = os.path.join(TMP, "alert_state.json"); json.dump(persist(d), open(st_path, "w"))
real_join = nowcast.os.path.join
def fake_join(*parts):
    return st_path if parts[-1] == "alert_state.json" else real_join(*parts)
with mock.patch.object(ff, "fetch_nws_flood_alerts", return_value=f["pluvial_risk"]["nws_flood_alerts"]), mock.patch.object(nowcast.os.path, "join", fake_join):
    print("   alert_dispatch_check exit codes on three consecutive nowcast runs:", [nowcast.alert_dispatch_check() for _ in range(3)])

print("R10 label prints a projection that the policy itself rejects (falling trend)")
nc = {"nowcast_schema_version": ff.NOWCAST_SCHEMA_VERSION, "active": True, "radar_quality": "ok", "trend": "falling",
      "street_now_in": 5.0, "peak_proj_in": 17.1, "day_local": "2026-08-07", "source_latest_utc": "2026-08-07T22:32:00Z"}
with mock.patch.object(ff, "_radar_live_state", return_value=nc):
    print("  ", ff.compute_alert_level(fc([])))
    with mock.patch.object(ff, "headline_for", return_value=("x", "")):
        print("   base ntfy text:", ff.build_sms_text(fc([])))

print("R13 base radar pathway has no curb floor: +0.1 in over the grate ranks 1 and bypasses quiet hours")
nc = dict(nc, street_now_in=0.1, peak_proj_in=0.4, day_local="2026-12-01", source_latest_utc="2026-12-01T07:55:00Z")
st = {"rank": 0, "sig": "", "last_sent_rank": 4, "last_sent_sig": "tide:x", "last_sent_ts": "2026-11-20T00:00:00Z"}
d = ev(fc([]), st, dt.datetime(2026, 12, 1, 8, 0, tzinfo=UTC), nc); show("03:00 EST", d)
g = ff.evaluate_sms_gate({}, state=st, now_utc=dt.datetime(2026, 12, 1, 8, 0, tzinfo=UTC), nowcast=nc)
print("   imminent gate for the same payload:", g["send"], g["reason"])

print("R14 radar bit drop-out after a radar-tagged send = 'new event' (daytime, cap not reached)")
st = {"rank": 4, "sig": "tide:2026-12-05 14:00-05:00|radar:2026-12-05:severe", "last_sent_rank": 4,
      "last_sent_sig": "tide:2026-12-05 14:00-05:00|radar:2026-12-05:severe", "last_sent_ts": "2026-12-05T18:00:00Z",
      "base_sends_today": {"date": "2026-12-05", "count": 1}}
f = fc([tide("2026-12-05 14:00-05:00", "severe", -0.5, 8.6)])
show("14:30 EST radar inactive/stale", ev(f, st, dt.datetime(2026, 12, 5, 19, 30, tzinfo=UTC), None))
