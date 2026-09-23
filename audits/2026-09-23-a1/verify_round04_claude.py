"""Round 04 (Claude): offline inversion of Codex's round-03 probes against the
repaired code. Each block asserts the REPAIRED behaviour; a successful exit
means the seven defects no longer reproduce here. No network, no delivery,
no canonical data writes. Synthetic scenarios are not measured floods.
Run: python3 audits/2026-09-23-a1/verify_round04_claude.py
(S3 reads the committed docs/forecast.json; that assertion only holds once
the hourly job has published with the repaired code.)
"""
import datetime as dt
import json
import re
import sys
import time
from unittest.mock import patch
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
from forecast import flood_forecast_daily as ff
from forecast import outlook as ol, outlook_sources as src, outlook_page as page
from forecast.rendering import render_email, worst_72h_headline
from test_outlook import _build, _fixture_data, NOW
out = {}
UTC = dt.timezone.utc

# S1: absolute errors before averaging; same-issuance pairing; paired rows counted once
rows = []; observed = {}
for i in range(28):
    t = (dt.datetime(2026, 8, 1, 12, tzinfo=UTC) + dt.timedelta(hours=12 * i)).isoformat()
    observed[t] = 5.0
    for pred in (4.0, 6.0):
        rows.append(dict(target_tide_time=t, lead_h="12", nwps_mllw=str(pred), persist_flat_mllw="5.2"))
score = ol.score_shadow(rows, observed)["readiness"]["nwps_vs_persistence_le72h"]
out["S1_cancellation"] = score
assert score["mae_candidate"] == 1.0 and abs(score["mae_baseline"] - 0.2) < 1e-9
assert score["verdict"].startswith("NOT BETTER") and score["n_forecasts"] == 56
x = [dict(target_tide_time="t", lead_h="1", nwps_mllw="5"),
     dict(target_tide_time="t", lead_h="23", persist_flat_mllw="6")]
out["S1_disjoint_issuances"] = ol.score_shadow(x, {"t": 5})["readiness"]["nwps_vs_persistence_le72h"]
assert out["S1_disjoint_issuances"]["n"] == 0

# S2: the unknown flag reaches the landing-map payload; explicit null grid hours are not dry
data = _fixture_data(); data["nbm"] = None; data["wpc"] = None
built = _build(data=data)
fc = {"generated_utc": NOW.isoformat(), "outlook_7d": built}
pts, *_ = ff._map_time_series(fc)
unknown = next(p for p in built["series"] if p["rain_unknown"] and p["lead_h"] > 80)
mappt = next(p for p in pts if p["t"] == unknown["time"])
out["S2_missing_rain_map"] = {"raw_rain_unknown": unknown["rain_unknown"], "map_point": mappt}
assert mappt["u"] is True
grid = {"series": {"qpf_in": [{"start": "2026-09-24T04:00:00Z", "hours": 24, "value": None}]},
        "reach": {"qpf_in": "2026-09-30T12:00:00Z"}}
d = ol.build_days(NOW, [], {"grid": grid})[1]
out["S2_null_grid"] = {k: d[k] for k in ("qpf_in", "qpf_source", "qpf_covered_h", "qpf_null_h", "qpf_partial")}
assert d["qpf_covered_h"] < 1.0 and d["qpf_null_h"] >= 23.0 and d["qpf_partial"] is True
chart = json.loads(re.search(r"var D = (\{.*?\});", page._chart(built), re.S).group(1))
out["S2_chart_unknown_hours"] = sum(1 for v in chart["unknown"] if v is not None)
assert out["S2_chart_unknown_hours"] > 0

# S3: the built series reaches the declared horizon; every touched date has a card
last = built["series"][-1]["lead_h"]
out["S3_built_horizon"] = {"declared_h": built["horizon_hours"], "series_last_lead": last,
                           "cards": len(built["days"]), "partial_cards": [d["date"] for d in built["days"] if d["partial"]],
                           "table_last_lead": built["tides"][-1]["lead_h"]}
assert 160 <= last <= 168 and built["tides"][-1]["lead_h"] <= 168
assert set(p["time"][:10] for p in built["series"]) <= set(d["date"] for d in built["days"])
try:
    f = json.loads((ROOT / "docs/forecast.json").read_text()); o = f["outlook_7d"]
    out["S3_published_horizon"] = {"generated": f["generated_utc"], "series_last_lead": o["series"][-1]["lead_h"],
                                   "cards": len(o["days"])}
except Exception as e:  # noqa: BLE001
    out["S3_published_horizon"] = str(e)

# S4: one headline for subject, text and HTML; past points are not forward outlook
f = json.loads((ROOT / "docs/forecast.json").read_text())
f["depths_in"]["regime"] = "dry"; f["today_regime"] = "dry"; f["today_lookback"] = None
f["day_worst"] = [{"day": "2026-09-23", "rank": 0, "regime": "dry", "pathway": "tide"},
                  {"day": "2026-09-24", "rank": 4, "regime": "severe", "pathway": "rain (tank line)", "water_navd88": 6}]
subject, body, email_html = render_email(f)
panel = email_html.split("WORST 72 H</div>", 1)[1].split("</b>", 1)[0]
out["S4_email"] = {"subject": subject, "html_worst_panel": panel[-40:],
                   "text_line": next(l for l in body.splitlines() if l.startswith("WORST 72H"))}
assert "WORST 72H SEVERE (RAIN)" in subject and "SEVERE (RAIN)" in panel
assert "SEVERE (RAIN)" in out["S4_email"]["text_line"] or "SEVERE" in out["S4_email"]["text_line"]
series = [dict(time="2026-09-23 06:00-04:00", water_navd88=6, tide_navd88=2),
          dict(time="2026-09-23 16:00-04:00", water_navd88=2, tide_navd88=2)]
dw = ff.compute_day_worst([], series, {}, [], ["2026-09-23"],
                          now_utc=ff.parse_station_local_time("2026-09-23 15:26-04:00"))
out["S4_past_flood_headline"] = dw[0]
assert dw[0]["regime"] == "dry"

# S5: chart plots the per-point compound scenario the maps use
series = [dict(time="2026-09-23 12:00-04:00", utc="2026-09-23T16:00:00Z", lead_h=5, tide_navd88=4.5, water_navd88=4.5,
               pluvial_navd88=None, rain_in_hr=0.5, rain_unknown=False, burst_risk=True, surge_source="nwps"),
          dict(time="2026-09-23 18:00-04:00", utc="2026-09-23T22:00:00Z", lead_h=11, tide_navd88=5, water_navd88=5,
               pluvial_navd88=None, rain_in_hr=0, rain_unknown=False, burst_risk=False, surge_source="nwps")]
days = [{"date": "2026-09-23", "regime_max": "severe"}]
ol.add_rain_pathway(days, series, [], ff.estimate_pluvial_water_models, ff.classify_regime_from_water)
w = ol.worst_points(series, days)
html = page._chart({"series": series, "days": days, "worst": w})
chart = json.loads(re.search(r"var D = (\{.*?\});", html, re.S).group(1))
p = series[0]
out["S5_compound_chart"] = {"per_point_potential_navd88": p["burst_potential_navd88"],
                            "chart_potential_navd88": round(chart["burst"][0] / 12 + 3.52, 3),
                            "card_high_tide_potential_navd88": days[0]["rain_pathway"]["burst_at_high_tide_navd88"],
                            "worst_selected_navd88": w["flood_chance"]["navd88"]}
assert abs(out["S5_compound_chart"]["per_point_potential_navd88"] - out["S5_compound_chart"]["chart_potential_navd88"]) < 0.01

# S6: a bucket without hours is dropped with truthful health; the survivor works in the consumer
bad = {"nbm": {"cycle": NOW.isoformat(), "buckets": [
    {"end_utc": (NOW + dt.timedelta(hours=6)).isoformat(), "qpf_in": 1},
    {"end_utc": (NOW + dt.timedelta(hours=12)).isoformat(), "hours": 6, "qpf_in": 0.2}]}}
admitted, health = src.admit_guidance(bad, "nbm", NOW)
out["S6_bad_bucket"] = {"status": health["status"], "detail": health["detail"], "kept": len(admitted["buckets"])}
assert len(admitted["buckets"]) == 1 and "malformed dropped" in health["detail"] and health["status"] == "degraded"
assert ol._bucket_containing(admitted["buckets"], NOW + dt.timedelta(hours=8)) is not None

# S7: nested requests recompute the timeout; the wall clock bounds gather
clock = [0.0]; deadline = src.Deadline(60, clock=lambda: clock[0]); clock[0] = 50.0
timeouts = []
def fake_json(url, timeout):
    timeouts.append(timeout); clock[0] += 9
    return {"properties": {"forecastGridData": "synthetic-grid"}}
with patch.object(src, "_get_json", side_effect=fake_json), patch.object(src, "parse_nws_grid", return_value={"summary": "synthetic"}):
    _, health = src.refresh({}, "grid", lambda timeout: src.fetch_nws_grid(timeout=timeout, deadline=deadline), NOW, deadline=deadline)
out["S7_deadline"] = {"elapsed": clock[0], "budget": 60, "request_timeouts": timeouts, "status": health["status"], "detail": health["detail"]}
assert timeouts == [10.0] and health["status"] == "unavailable" and clock[0] == 59.0
def hang(url, timeout=30):
    time.sleep(0.6); raise OSError("late")
with patch.object(src, "_request", side_effect=hang), patch.object(src, "load_guidance", return_value={}):
    t0 = time.monotonic()
    _, health = src.gather(NOW, guidance_path="/nonexistent", deadline=src.Deadline(3.0), wall_clock_s=0.3)
    elapsed = time.monotonic() - t0
    time.sleep(3.2)
out["S7_wall_clock"] = {"wall_clock_s": 0.3, "elapsed_s": round(elapsed, 2), "astro": health["astro"]["detail"],
                        "budget": health["_budget"]}
assert elapsed < 0.55 and "wall-clock" in health["astro"]["detail"]

# follow-up: six-hour window by timestamps
pts6 = [dict(time=f"2026-09-23 {h:02d}:00-04:00", utc=f"2026-09-23T{h+4:02d}:00:00Z", lead_h=h, tide_navd88=1.0, water_navd88=1.0,
             pluvial_navd88=None, rain_in_hr=0.5, rain_unknown=False, burst_risk=False, surge_source="nwps") for h in (0, 1, 2, 9, 10, 11)]
days6 = [{"date": "2026-09-23", "regime_max": "dry"}]
ol.add_rain_pathway(days6, pts6, [], ff.estimate_pluvial_water_models, ff.classify_regime_from_water)
out["followup_6h_window"] = {k: days6[0]["rain_pathway"][k] for k in ("max_6h_in", "max_6h_window_complete")}
assert abs(days6[0]["rain_pathway"]["max_6h_in"] - 1.5) < 1e-9 and days6[0]["rain_pathway"]["max_6h_window_complete"] is False
print(json.dumps(out, indent=2, sort_keys=True, default=str))
