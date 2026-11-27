"""Reproduce selected audit findings offline at the stated production revision.

Run from a checkout whose production code matches 24ff1ec90. This script
prints observations rather than requiring defects to survive future repairs.
All calls to the radar producer use injected inputs and a mocked writer.
"""
import csv
import datetime as dt
import io
import json
import statistics
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = "24ff1ec90"
sys.path[:0] = [str(ROOT / "forecast"), str(ROOT / "bin")]
import flood_forecast_daily as ff
import nowcast
import public_health_watchdog as watchdog


def blob(revision, path):
    return subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT, text=True
    )


def records(revision, path):
    return list(csv.DictReader(io.StringIO(blob(revision, path))))


def model_checks():
    cutoff = dt.datetime.fromisoformat("2026-11-27T13:08:00+00:00")
    repeated_hour = dt.datetime.fromisoformat("2026-11-01T06:30:00+00:00")
    local = ff._station_local_now(repeated_hour)
    point = {"time": "2026-11-27 09:00-05:00", "water_navd88": 5.8, "tide_navd88": 1.0}
    with patch.object(ff, "_radar_live_state", return_value=None):
        display = ff.compute_day_worst([], [point], {}, [], ["2026-11-27"], cutoff)
        alert = ff.compute_alert_level({"water_series": [point], "all_tides": [], "pluvial_risk": {}})
    frames = [(cutoff.replace(tzinfo=None) - dt.timedelta(minutes=m), "frame")
              for m in (18, 12, 6, 0)]
    with (patch.object(nowcast, "latest_frames", return_value=frames),
          patch.object(nowcast, "current_bay", return_value=(1.0, "observed")),
          patch.object(nowcast, "box_rate", return_value=0.0),
          patch.object(nowcast, "_write") as write):
        nowcast.run(cutoff)
    payload = write.call_args.args[0]
    stamp = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    issues = watchdog.assess(
        {"generated_utc": stamp},
        {"active": False, "generated_utc": stamp, "radar_quality": "unavailable",
         "error": "all downloads failed"},
        {"workflow_runs": [{"status": "completed", "conclusion": "success", "updated_at": stamp}]},
        now=cutoff,
    )
    tails = {}
    for count in (5, 6):
        readings = [(i, 4.0 if i < 30 - count else 7.0) for i in range(30)]
        tails[count] = ff._despike_gauge(readings)[-1]
    return {
        "rain_only": {"display": display[0], "alert": alert},
        "live_clock": {"utc_input": repeated_hour.isoformat(), "local_fold": local.fold,
                       "query_gmt": ff.station_local_to_noaa_gmt(local)},
        "radar": {k: payload[k] for k in ("frames_succeeded", "coverage_minutes", "radar_quality")},
        "failed_inactive_watchdog_issues": issues,
        "retained_gauge_tail_by_elevated_sample_count": tails,
    }


def numeric(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def scoring_checks():
    rows = records(SNAPSHOT, "data/labeled_observations.csv")
    predictions = [numeric(r["model_predicted_depth_in"]) for r in rows]
    pairs = [(p, numeric(r["observed_depth_in"])) for p, r in zip(predictions, rows)
             if p is not None and numeric(r["observed_depth_in"]) is not None]
    omitted = [r for r in rows if r["observation_time_local"].startswith("2026-07-06")
               and r["model_predicted_depth_in"].startswith("0 (")
               and numeric(r["observed_depth_in"]) is not None]
    old_new = {}
    for rev in ("da16cd11c^", "da16cd11c"):
        cohort = records(rev, "data/forecast_accuracy.csv")[-30:]
        old_new[rev] = statistics.mean(float(r["mllw_error_ft"]) for r in cohort)
    tide_errors = {}
    outlook = records(SNAPSHOT, "data/outlook_log.csv")
    for target, observed in (("2026-11-26 08:28", 8.267), ("2026-11-26 21:07", 9.211)):
        cohort = [r for r in outlook if r["target_tide_time"].startswith(target)
                  and 12 <= float(r["lead_h"]) < 24]
        keys = ("nws_product_mllw", "persist_flat_mllw", "persist_decay_mllw")
        tide_errors[target] = {"n_issuances": len(cohort), **{
            k: statistics.mean(float(r[k]) - observed for r in cohort if r[k]) for k in keys
        }}
    return {
        "numeric_predictions": sum(p is not None for p in predictions),
        "paired_depths": len(pairs),
        "positive_paired_errors": sum(p > o for p, o in pairs),
        "omitted_july_6_text_zero_pairs": len(omitted),
        "last_30_signed_error_ft_at_rescore": old_new,
        "november_26_signed_errors_12_to_24_hours_ft": tide_errors,
    }


if __name__ == "__main__":
    print(json.dumps({"runtime": model_checks(), "records": scoring_checks()}, indent=2))
