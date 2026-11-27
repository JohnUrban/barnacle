import datetime as dt, json, sys, os, tempfile
from unittest import mock
sys.path.insert(0, ".")
from forecast import flood_forecast_daily as ff
UTC = dt.timezone.utc
TMP = tempfile.mkdtemp(prefix="alrepro_")
P = os.path.join(TMP, "st.json")
f = {"all_tides": [{"time": "2026-12-06 15:00-05:00", "hours_from_now": 20.0, "forecast_peak_mllw": 7.2, "depths_in": {"regime": "light"}}], "pluvial_risk": {}}
st = {"rank": 0, "sig": "", "last_sent_rank": 4, "last_sent_sig": "tide:old", "last_sent_ts": "2026-11-30T00:00:00Z"}
def ev(state, now):
    with mock.patch.object(ff, "_radar_live_state", return_value=None):
        return ff.evaluate_alert(f, state=state, now_utc=now)
print("R15 total delivery failure at 19:10 EST, then quiet hours")
d = ev(st, dt.datetime(2026, 12, 6, 0, 10, tzinfo=UTC)); print("  19:10 EST:", d["send"], d["reason"])
s1 = ff.persist_alert_state(d, path=P, requested_base_channels=ff._base_channels_to_attempt(d))   # what _settle_delivery does on total failure
print("  state after failure: pending_base =", s1.get("pending_base"), "| base count =", s1.get("base_sends_today"))
for hh in (1, 8):   # 20:10 EST, 03:10 EST
    now = dt.datetime(2026, 12, 6, hh, 10, tzinfo=UTC)
    d = ev(s1, now)
    print(f"  {now.astimezone(ff.STATION_TZ):%H:%M} EST: decision.send={d['send']} ({d['reason'][:60]}...) -> channels still attempted: {sorted(ff._base_channels_to_attempt(d))}")
    s2 = ff.persist_alert_state(d, ["ntfy", "email"], path=P, requested_base_channels=ff._base_channels_to_attempt(d))
    print("     after a successful retry: base_sends_today =", s2.get("base_sends_today"), "| sends_today =", s2.get("sends_today"), "| pending =", s2.get("pending_base"))
print("R16 cooldown text vs ratchet: same signature reappears at a HIGHER rank inside 24 h")
st = {"rank": 0, "sig": "", "last_sent_rank": 4, "last_sent_sig": "pluv", "last_sent_ts": "2026-12-05T15:00:00Z"}
f = {"all_tides": [], "pluvial_risk": {"level": "elevated"}}
d = ev(st, dt.datetime(2026, 12, 5, 19, 0, tzinfo=UTC)); print("  (sent at rank 1 four hours ago; now rank 3):", d["send"], "|", d["reason"])
