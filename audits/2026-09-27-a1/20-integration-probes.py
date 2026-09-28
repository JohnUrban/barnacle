"""Offline round20 integration verification on an isolated candidate archive.

Usage: python 20-integration-probes.py /path/to/candidate
Does not send alerts. External input fetches are mocked for whole-build
health checks; renderers use an existing snapshot with a disputed-band case.
"""
import contextlib
import copy
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT))
from forecast import flood_forecast_daily as ff, nws_surge_parser, rendering

result = {}
now = ff.parse_station_local_time("2026-09-27T23:45:00-04:00")
empty = {"fetch_recent_history": [], "fetch_high_tides_lookahead": [],
         "fetch_observed_recent": [], "build_water_series": [],
         "build_seasonal_context": {}, "build_outlook_7d_field": (None, {}),
         "fetch_nws_qpf": None, "fetch_current_surge": None,
         "fetch_nws_flood_alerts": None, "fetch_surge_swing_6h": None,
         "_load_surge_state": None, "_fetch_actual_peak_around": (None, None),
         "fetch_tides_24h": {"high": [("2026-09-28 09:15", 5.8)], "low": []}}
with tempfile.TemporaryDirectory() as td, contextlib.ExitStack() as stack:
    for name, value in empty.items():
        stack.enter_context(mock.patch.object(ff, name, return_value=value))
    for name in ["fetch_temperature_72h_mean", "fetch_nws_hourly_forecast"]:
        stack.enter_context(mock.patch.object(ff, name, side_effect=OSError("offline probe")))
    stack.enter_context(mock.patch.object(ff._surge_mean, "load", return_value=None))
    stack.enter_context(mock.patch.object(ff, "_station_local_now", return_value=now))
    stack.enter_context(mock.patch.object(nws_surge_parser, "get_surge_forecast",
                                         return_value=(False, [], None, "No active Coastal Flood event")))
    missing = Path(td) / "missing.jsonl"
    with mock.patch.object(ff, "OBSERVATION_BOUNDS_PATH", str(missing)), \
            contextlib.redirect_stdout(io.StringIO()):
        bad = ff.build_forecast()
    result["missing_file_whole_build"] = {
        "health": bad["input_health"].get("observation_bounds"),
        "listed_degraded": "observation_bounds" in bad["degraded_inputs"],
        "empirical_fallback": bad["today_lookback"]["evidence"],
    }
    assert result["missing_file_whole_build"]["listed_degraded"]
    assert result["missing_file_whole_build"]["health"]["status"] == "degraded"
    with contextlib.redirect_stdout(io.StringIO()):
        clean = ff.build_forecast()
    result["subsequent_clean_whole_build"] = {
        "health": clean["input_health"].get("observation_bounds"),
        "listed_degraded": "observation_bounds" in clean["degraded_inputs"],
    }
    assert not result["subsequent_clean_whole_build"]["listed_degraded"]

# All real rows and the committed bounds, with only the model maximum synthetic.
from tests.test_bounds_round18 import repo, run
from tests.test_bounds_round16 import ROWS, model, widget
tmp = repo([dict(r) for r in ROWS if r["observation_time_local"].startswith("2026-09-26T21:30")],
           (ROOT / "data/observation_bounds.jsonl").read_text())
lb, _ = run(tmp, model(9.0, "2026-09-27T01:30:00Z", "2026-09-26"),
            now=ff.parse_station_local_time("2026-09-26T23:45:00-04:00"))
snapshot = json.loads((ROOT / "docs/forecast.json").read_text())
snapshot["today_lookback"] = lb
with contextlib.redirect_stdout(io.StringIO()):
    page = rendering.render_html_page(copy.deepcopy(snapshot))
    subject, plain, html = rendering.render_email(copy.deepcopy(snapshot))
texts = {"landing": page, "email_subject": subject, "email_text": plain,
         "email_html": html, "widget": widget(lb)}
result["rendered_disputed_band"] = {}
for name, text in texts.items():
    result["rendered_disputed_band"][name] = {
        "labels_dispute": ("cap?" if name == "widget" else "cap disputed") in text,
        "retains_model_9": ("model +9″" if name == "widget" else "model claims +9.0") in text,
    }
    assert all(result["rendered_disputed_band"][name].values()), name
result["rendered_disputed_band"]["subject_text"] = subject
result["rendered_disputed_band"]["widget_text"] = texts["widget"]
print(json.dumps(result, ensure_ascii=False, indent=2))
