import json, sys, os
from unittest import mock
sys.path.insert(0, ".")
from forecast import flood_forecast_daily as ff
S = os.path.dirname(os.path.abspath(__file__))
for h in ("d174fdd39", "c712c8365", "5857208e4"):
    f = json.load(open(os.path.join(S, f"fc_{h}.json")))
    nc = json.load(open(os.path.join(S, "nc_0155.json"))) if h == "5857208e4" else None
    with mock.patch.object(ff, "_radar_live_state", return_value=nc):
        try:
            subject, text, html = ff.render_email(f)
            rank, label, sig = ff.compute_alert_level(f)
            print(h, "\n   EMAIL SUBJECT: [ALERT] " + label + " | " + subject)
            print("   EMAIL TEXT (first 14 lines):")
            for line in ("ALERT: " + label + "\n\n" + text).split("\n")[:14]:
                print("     |", line[:200])
            print("   NTFY TITLE: ", ff._ntfy_header_text(f"Barnacle flood alert ({label})"))
        except Exception as e:
            import traceback; traceback.print_exc()
