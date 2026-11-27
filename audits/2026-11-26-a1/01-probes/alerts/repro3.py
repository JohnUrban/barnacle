import datetime as dt, json, sys, os
from unittest import mock
sys.path.insert(0, ".")
from forecast import flood_forecast_daily as ff
S = os.path.dirname(os.path.abspath(__file__))
for h in ("d174fdd39", "c712c8365", "5857208e4"):
    f = json.load(open(os.path.join(S, f"fc_{h}.json")))
    nc = json.load(open(os.path.join(S, "nc_0155.json"))) if h == "5857208e4" else None
    with mock.patch.object(ff, "_radar_live_state", return_value=nc):
        try:
            rank, label, sig = ff.compute_alert_level(f)
            print(h, f.get("generated_utc"), "| rank", rank, "| label:", label)
            print("    base ntfy text:", ff.build_sms_text(f))
        except Exception as e:
            print(h, "ERR", type(e).__name__, e)
    print("    tides in table:", [(t["time"][5:16], t["depths_in"]["regime"], round(t["hours_from_now"], 1)) for t in f["all_tides"][:4]])
