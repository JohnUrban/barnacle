#!/usr/bin/env python3
"""Read-only quantitative checks for the model-v0.11 assessment.

This is an assessment harness, not a fitter.  It keeps the most consequential
comparisons in ``history/reports/model-v0.11-assessment-2026-09-18.md``
rerunnable from repository evidence without changing production constants,
goldens, ledgers, caches, or generated site artifacts.

Run from any directory:

    python3 history/scripts/assess_model_v0_11.py
    python3 history/scripts/assess_model_v0_11.py --json
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from forecast import flood_forecast_daily as ff  # noqa: E402
from history.scripts import reproduce_v0_10_1 as reproduction  # noqa: E402


MRMS_PATH = REPO_ROOT / "history" / "data" / "mrms" / "mrms_extracted.csv"
PREDICTIONS_PATH = REPO_ROOT / "data" / "predictions_log.csv"
OBSERVED_PEAKS_PATH = REPO_ROOT / "data" / "observed_peaks_cache.csv"
LEGACY_ACCURACY_PATH = REPO_ROOT / "data" / "forecast_accuracy.csv"
HEAD_REPLAY_PATH = (
    REPO_ROOT / "history" / "data" / "noaa_head_replay_fixture.json"
)

MRMS_EVENTS = {
    "event7": {
        "date": "2026-08-07", "start_utc": "21:50", "end_utc": "23:20",
        "bay_navd88": 0.9, "observed_peak_in": 15.4,
        "observed_peak_utc": "2026-08-07T22:40:00+00:00",
    },
    "event8": {
        "date": "2026-09-01", "start_utc": "23:00", "end_utc": "23:56",
        "bay_navd88": -0.7, "observed_peak_in": 13.9,
        "observed_peak_utc": "2026-09-01T23:25:00+00:00",
        "observations": "assets/observations/2026-09-01/observed_points.json",
    },
    "event9_round1": {
        "date": "2026-09-13", "start_utc": "10:16", "end_utc": "11:42",
        "bay_navd88": 0.8, "observed_peak_in": 13.7,
        "observed_peak_utc": "2026-09-13T11:01:23+00:00",
        "observations": "assets/observations/2026-09-13/observed_points.json",
    },
}

LAG_CANDIDATES_MIN = (0, 3, 5, 7, 10, 12, 15)
LEAD_BUCKETS = (
    (0, 3, "0-3 h"), (3, 6, "3-6 h"), (6, 12, "6-12 h"),
    (12, 24, "12-24 h"), (24, 48, "24-48 h"),
    (48, 120, "48-120 h"),
)


def corrected_pluvial_fill(curve, base_stage, budget):
    """Candidate inversion that starts the first bin at ``base_stage``."""
    stage = base_stage
    for index in range(1, len(curve)):
        previous_stage = curve[index - 1][0]
        upper_stage, area = curve[index]
        if upper_stage <= base_stage:
            continue
        lower_stage = max(base_stage, previous_stage)
        step_volume = area * (upper_stage - lower_stage)
        if budget < step_volume:
            return lower_stage + budget / area if area > 0 else upper_stage
        budget -= step_volume
        stage = upper_stage
    if budget > 0 and curve[-1][1] > 0:
        stage += budget / curve[-1][1]
    return stage


def _summary(values):
    values = list(values)
    return {
        "n": len(values),
        "mean_bias": sum(values) / len(values),
        "mae": sum(abs(value) for value in values) / len(values),
        "rmse": math.sqrt(sum(value * value for value in values) / len(values)),
    }


def assess_fill():
    curve = ff._load_stage_curve()
    worst = None
    for hundredth in range(1, 2400):
        base = hundredth / 100.0
        for budget in (1e-6, 0.001, 0.01, 0.1, 1, 10, 100, 1_000,
                       10_000, 100_000, 500_000, 2_000_000):
            current = ff._pluvial_fill(curve, base, budget)
            candidate = corrected_pluvial_fill(curve, base, budget)
            row = {
                "delta_in": candidate - current,
                "base_stage_in": base,
                "budget_cell_in": budget,
                "current_stage_in": current,
                "candidate_stage_in": candidate,
            }
            if worst is None or row["delta_in"] > worst["delta_in"]:
                worst = row

    fixture = reproduction.load_fixture()
    current_metrics = reproduction.hindcast_metrics(fixture)
    original = ff._pluvial_fill
    try:
        ff._pluvial_fill = corrected_pluvial_fill
        candidate_metrics = reproduction.hindcast_metrics(fixture)
    finally:
        ff._pluvial_fill = original
    events = {}
    for event_id, current in current_metrics.items():
        candidate = candidate_metrics[event_id]
        events[event_id] = {
            "peak_delta_in": (
                candidate["peak_stage_in"] - current["peak_stage_in"]
            ),
            "peak_time_changed": (
                candidate["peak_local"] != current["peak_local"]
            ),
        }
        if "stage_at_observation_in" in current:
            events[event_id]["observation_delta_in"] = (
                candidate["stage_at_observation_in"]
                - current["stage_at_observation_in"]
            )
    return {"worst_sampled_case": worst, "frozen_hindcasts": events}


def _load_mrms_rows():
    with MRMS_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _event_frames(rows, event, field):
    start = dt.datetime.fromisoformat(
        f"{event['date']}T{event['start_utc']}:00+00:00"
    )
    end = dt.datetime.fromisoformat(
        f"{event['date']}T{event['end_utc']}:00+00:00"
    )
    frames = []
    for row in rows:
        if row["product"] != "PrecipRate":
            continue
        stamp = dt.datetime.fromisoformat(row["utc"].replace("Z", "+00:00"))
        if start <= stamp <= end:
            frames.append((stamp, float(row[field]) / 25.4))
    if not frames:
        raise ValueError(f"no {field} MRMS frames for {event['date']}")
    return sorted(frames)


def _simulate_mrms(frames, event, lag_minutes):
    curve = ff._load_stage_curve()
    bay = event["bay_navd88"]
    drain_span = ff.PLUVIAL_STREET_BASE - ff.PLUVIAL_DRAIN_FULL_BELOW
    drain_fraction = min(
        1.0, max(0.0, (ff.PLUVIAL_STREET_BASE - bay) / drain_span)
    )
    drain = ff.PLUVIAL_DRAIN_RATE * drain_fraction
    base_stage = max(0.0, (bay - ff.PLUVIAL_STREET_BASE) * 12.0)
    lag = dt.timedelta(minutes=lag_minutes)
    volume = 0.0
    current = frames[0][0]
    end = frames[-1][0] + dt.timedelta(minutes=50)
    step_minutes = 2.0
    output = []
    while current <= end:
        lagged = current - lag
        rate = 0.0
        for stamp, frame_rate in frames:
            if stamp > lagged:
                break
            rate = frame_rate
        if lagged < frames[0][0]:
            rate = 0.0
        net = max(0.0, rate - drain)
        volume = max(
            0.0,
            volume + (
                ff.TANK_K * net ** ff.TANK_GAMMA - ff.TANK_KOUT * volume
            ) * (step_minutes / 60.0),
        )
        stage = (
            ff._pluvial_fill(curve, base_stage, volume)
            if volume > 0 else base_stage
        )
        output.append((current, stage))
        current += dt.timedelta(minutes=step_minutes)
    return output


def _load_event_observations(event):
    path = REPO_ROOT / event["observations"]
    with path.open(encoding="utf-8") as handle:
        rows = json.load(handle)
    station_zone = dt.timezone(dt.timedelta(hours=-4))
    return [
        (
            dt.datetime.fromisoformat(row["t"]).replace(
                tzinfo=station_zone
            ).astimezone(dt.timezone.utc),
            float(row["in"]),
        )
        for row in rows
    ]


def _trajectory_score(trajectory, observations):
    errors = []
    for stamp, observed in observations:
        nearest = min(
            trajectory,
            key=lambda point: abs((point[0] - stamp).total_seconds()),
        )
        errors.append(nearest[1] - observed)
    return _summary(errors)


def assess_lag_and_forcing():
    rows = _load_mrms_rows()
    lag_results = {}
    for event_id in ("event8", "event9_round1"):
        event = MRMS_EVENTS[event_id]
        frames = _event_frames(rows, event, "box_mean")
        observations = _load_event_observations(event)
        candidates = {}
        for lag in LAG_CANDIDATES_MIN:
            trajectory = _simulate_mrms(frames, event, lag)
            score = _trajectory_score(trajectory, observations)
            peak_time, peak = max(trajectory, key=lambda point: point[1])
            score.update({
                "peak_in": peak,
                "peak_error_in": peak - event["observed_peak_in"],
                "peak_time_error_min": (
                    peak_time
                    - dt.datetime.fromisoformat(event["observed_peak_utc"])
                ).total_seconds() / 60.0,
            })
            candidates[str(lag)] = score
        best = min(candidates, key=lambda key: candidates[key]["rmse"])
        lag_results[event_id] = {
            "best_sampled_lag_min": int(best),
            "candidates": candidates,
        }

    forcing_results = {}
    for event_id, event in MRMS_EVENTS.items():
        forcing_results[event_id] = {}
        for field in ("box_mean", "point", "box_max"):
            trajectory = _simulate_mrms(
                _event_frames(rows, event, field), event, ff.TANK_LAG_MIN
            )
            peak_time, peak = max(trajectory, key=lambda point: point[1])
            forcing_results[event_id][field] = {
                "peak_in": peak,
                "peak_error_in": peak - event["observed_peak_in"],
                "peak_time_error_min": (
                    peak_time
                    - dt.datetime.fromisoformat(event["observed_peak_utc"])
                ).total_seconds() / 60.0,
            }
    return {"lag_sensitivity": lag_results, "forcing": forcing_results}


def assess_state_and_tide_head():
    step_fraction = 1.0 - ff.TANK_KOUT * (2.0 / 60.0)
    remaining_60_min = step_fraction ** 30

    with HEAD_REPLAY_PATH.open(encoding="utf-8") as handle:
        head_fixture = json.load(handle)
    series = sorted(
        (
            dt.datetime.fromisoformat(row["utc"].replace("Z", "+00:00")),
            float(row["astronomical_mllw_ft"]),
        )
        for row in head_fixture["astronomical_sample"]["rows"]
    )

    def interpolate(target):
        for (left_time, left), (right_time, right) in zip(series, series[1:]):
            if left_time <= target <= right_time:
                fraction = (
                    (target - left_time).total_seconds()
                    / (right_time - left_time).total_seconds()
                )
                return left + fraction * (right - left)
        raise ValueError("target outside tide series")

    largest = None
    for start, start_level in series:
        end = start + dt.timedelta(minutes=45)
        if end > series[-1][0]:
            continue
        end_level = interpolate(end)
        candidate = {
            "start": start.isoformat(), "end": end.isoformat(),
            "start_mllw_ft": start_level, "end_mllw_ft": end_level,
            "change_ft": end_level - start_level,
        }
        if largest is None or abs(candidate["change_ft"]) > abs(largest["change_ft"]):
            largest = candidate
    return {
        "stateless_storage": {
            "two_minute_decay_factor": step_fraction,
            "fraction_remaining_after_60_dry_minutes": remaining_60_min,
        },
        "tide_head_sample": {
            "points": len(series),
            "first": series[0][0].isoformat(),
            "last": series[-1][0].isoformat(),
            "largest_45_minute_change": largest,
        },
    }


def _interpolate_points(points, target):
    """Linearly interpolate sorted ``(datetime, value)`` points."""
    for (left_time, left), (right_time, right) in zip(points, points[1:]):
        if left_time <= target <= right_time:
            fraction = (
                (target - left_time).total_seconds()
                / (right_time - left_time).total_seconds()
            )
            return left + fraction * (right - left)
    raise ValueError("target outside series")


def _head_forecast_errors(rows):
    astronomical = [
        (dt.datetime.fromisoformat(row["utc"].replace("Z", "+00:00")),
         float(row["astronomical_mllw_ft"]))
        for row in rows
    ]
    observed = [
        (dt.datetime.fromisoformat(row["utc"].replace("Z", "+00:00")),
         float(row["observed_mllw_ft"]))
        for row in rows
    ]
    fixed_errors = []
    moving_errors = []
    fixed_endpoint_errors = []
    moving_endpoint_errors = []
    surge_changes = []
    issue_rows = []
    final_time = observed[-1][0]
    for issue_time, issue_observed in observed:
        endpoint = issue_time + dt.timedelta(minutes=45)
        if endpoint > final_time:
            continue
        issue_astronomical = _interpolate_points(astronomical, issue_time)
        issue_surge = issue_observed - issue_astronomical
        local_fixed = []
        local_moving = []
        for minute in (6, 12, 18, 24, 30, 36, 42, 45):
            target = issue_time + dt.timedelta(minutes=minute)
            truth = _interpolate_points(observed, target)
            future_astronomical = _interpolate_points(astronomical, target)
            local_fixed.append(issue_observed - truth)
            local_moving.append(future_astronomical + issue_surge - truth)
        fixed_errors.extend(local_fixed)
        moving_errors.extend(local_moving)
        fixed_endpoint_errors.append(local_fixed[-1])
        moving_endpoint_errors.append(local_moving[-1])
        endpoint_surge = (
            _interpolate_points(observed, endpoint)
            - _interpolate_points(astronomical, endpoint)
        )
        surge_changes.append(endpoint_surge - issue_surge)
        issue_rows.append({
            "issue_utc": issue_time.isoformat(),
            "astronomical_change_ft": (
                _interpolate_points(astronomical, endpoint)
                - issue_astronomical
            ),
            "observed_change_ft": (
                _interpolate_points(observed, endpoint) - issue_observed
            ),
            "surge_change_ft": endpoint_surge - issue_surge,
            "fixed_endpoint_error_ft": local_fixed[-1],
            "moving_endpoint_error_ft": local_moving[-1],
        })
    most_helpful = max(
        issue_rows,
        key=lambda row: (
            abs(row["fixed_endpoint_error_ft"])
            - abs(row["moving_endpoint_error_ft"])
        ),
    )
    most_harmful = min(
        issue_rows,
        key=lambda row: (
            abs(row["fixed_endpoint_error_ft"])
            - abs(row["moving_endpoint_error_ft"])
        ),
    )
    return {
        "issue_windows": len(issue_rows),
        "forecast_points": len(fixed_errors),
        "fixed_head": _summary(fixed_errors),
        "moving_astronomy_constant_surge": _summary(moving_errors),
        "fixed_head_endpoint": _summary(fixed_endpoint_errors),
        "moving_astronomy_constant_surge_endpoint": _summary(
            moving_endpoint_errors
        ),
        "surge_change_over_45_minutes": _summary(surge_changes),
        "most_helpful_endpoint": most_helpful,
        "most_harmful_endpoint": most_harmful,
    }


def _standardized_head_response(series, start, start_level, rain_rate):
    start_astronomical = _interpolate_points(series, start)
    curve = ff._load_stage_curve()
    results = {}
    for label, moving in (("fixed", False), ("moving", True)):
        volume = 0.0
        trajectory = []
        drains = []
        for minute in range(0, 45, 2):
            stamp = start + dt.timedelta(minutes=minute)
            bay = start_level
            if moving:
                bay += _interpolate_points(series, stamp) - start_astronomical
            drain_span = ff.PLUVIAL_STREET_BASE - ff.PLUVIAL_DRAIN_FULL_BELOW
            drain_fraction = min(
                1.0,
                max(0.0, (ff.PLUVIAL_STREET_BASE - bay) / drain_span),
            )
            drain = ff.PLUVIAL_DRAIN_RATE * drain_fraction
            net = max(0.0, rain_rate - drain)
            volume = max(
                0.0,
                volume + (
                    ff.TANK_K * net ** ff.TANK_GAMMA
                    - ff.TANK_KOUT * volume
                ) * (2.0 / 60.0),
            )
            base_stage = max(0.0, (bay - ff.PLUVIAL_STREET_BASE) * 12.0)
            stage = (
                ff._pluvial_fill(curve, base_stage, volume)
                if volume > 0 else base_stage
            )
            trajectory.append(stage)
            drains.append(drain)
        results[label] = {
            "peak_stage_in": max(trajectory),
            "endpoint_stage_in": trajectory[-1],
            "mean_drain_in_hr": sum(drains) / len(drains),
        }
    results["peak_delta_in"] = (
        results["moving"]["peak_stage_in"]
        - results["fixed"]["peak_stage_in"]
    )
    results["endpoint_delta_in"] = (
        results["moving"]["endpoint_stage_in"]
        - results["fixed"]["endpoint_stage_in"]
    )
    return results


def assess_time_varying_head_candidate():
    """Evaluate moving astronomy + issue-time surge without fitting."""
    with HEAD_REPLAY_PATH.open(encoding="utf-8") as handle:
        fixture = json.load(handle)
    replays = {
        event_date: _head_forecast_errors(event["rows"])
        for event_date, event in fixture["events"].items()
    }

    sample = fixture["astronomical_sample"]["rows"]
    series = sorted(
        (
            dt.datetime.fromisoformat(row["utc"].replace("Z", "+00:00")),
            float(row["astronomical_mllw_ft"]) + ff.MLLW_TO_NAVD88_OFFSET,
        )
        for row in sample
    )
    windows = []
    for start, level in series:
        endpoint = start + dt.timedelta(minutes=45)
        if endpoint > series[-1][0]:
            continue
        windows.append((
            _interpolate_points(series, endpoint) - level,
            start,
        ))
    standardized = {}
    for label, (_change, start) in (
        ("largest_rise", max(windows)),
        ("largest_fall", min(windows)),
    ):
        response = _standardized_head_response(
            series, start, start_level=3.26, rain_rate=1.0
        )
        response.update({
            "start": start.isoformat(),
            "astronomical_change_ft": _change,
            "start_bay_navd88_ft": 3.26,
            "rain_rate_in_hr": 1.0,
        })
        standardized[label] = response

    return {
        "fixture": {
            "path": str(HEAD_REPLAY_PATH.relative_to(REPO_ROOT)),
            "station": fixture["station"],
            "retrieved_utc_date": fixture["retrieved_utc_date"],
            "rows": sum(
                len(event["rows"]) for event in fixture["events"].values()
            ),
            "astronomical_sample_rows": len(sample),
        },
        "historical_head_replay": replays,
        "standardized_tank_response": standardized,
        "age_boundary": {
            "head_observation_max_age_min": ff.GAUGE_HEAD_MAX_AGE_MIN,
            "surge_observation_max_age_min": ff.SURGE_OBS_MAX_AGE_MIN,
            "projection_horizon_min": 45,
            "max_initial_age_for_full_horizon_surge_validity_min": (
                ff.SURGE_OBS_MAX_AGE_MIN - 45
            ),
        },
    }


def _group_stats(rows, key_function):
    groups = defaultdict(list)
    targets = defaultdict(set)
    for row in rows:
        key = key_function(row)
        groups[key].append(row["error"])
        targets[key].add(row["target"])
    return {
        str(key): {**_summary(values), "n_targets": len(targets[key])}
        for key, values in sorted(groups.items(), key=lambda item: str(item[0]))
    }


def assess_tide_accuracy():
    with LEGACY_ACCURACY_PATH.open(newline="", encoding="utf-8") as handle:
        legacy_errors = [
            float(row["mllw_error_ft"]) for row in csv.DictReader(handle)
        ]

    with OBSERVED_PEAKS_PATH.open(newline="", encoding="utf-8") as handle:
        observed = {
            ff.station_time_storage_key(row["target_tide_time"]):
                float(row["observed_peak_mllw"])
            for row in csv.DictReader(handle)
        }
    joined = []
    with PREDICTIONS_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            target = ff.station_time_storage_key(row["target_tide_time"])
            if target not in observed:
                continue
            try:
                predicted = float(row["sh_peak_mllw_predicted"])
                lead = float(row["hours_until_peak"])
            except (KeyError, TypeError, ValueError):
                continue
            joined.append({
                "target": target,
                "error": predicted - observed[target],
                "lead": lead,
                "model_version": row["model_version"],
                "surge_source": row["surge_source"],
                "regime": row["regime_predicted"],
            })

    def lead_bucket(row):
        for low, high, label in LEAD_BUCKETS:
            if low <= row["lead"] < high:
                return label
        return "outside"

    return {
        "legacy_daily": _summary(legacy_errors),
        "hourly_join": {
            **_summary(row["error"] for row in joined),
            "n_targets": len({row["target"] for row in joined}),
            "by_model_version": _group_stats(joined, lambda row: row["model_version"]),
            "by_lead_time": _group_stats(joined, lead_bucket),
            "by_surge_source": _group_stats(joined, lambda row: row["surge_source"]),
            "by_regime": _group_stats(joined, lambda row: row["regime"]),
        },
    }


def assess():
    lag_forcing = assess_lag_and_forcing()
    return {
        "pluvial_fill": assess_fill(),
        **lag_forcing,
        **assess_state_and_tide_head(),
        "time_varying_head_candidate": assess_time_varying_head_candidate(),
        "tide_accuracy": assess_tide_accuracy(),
    }


def _print_compact(result):
    fill = result["pluvial_fill"]
    print("_pluvial_fill")
    print(
        "  worst sampled correction: "
        f"{fill['worst_sampled_case']['delta_in']:+.3f} in"
    )
    for event_id, row in fill["frozen_hindcasts"].items():
        print(
            f"  {event_id}: peak {row['peak_delta_in']:+.3f} in; "
            f"time changed={row['peak_time_changed']}"
        )
    print("lag sensitivity (catchment mean)")
    for event_id, row in result["lag_sensitivity"].items():
        best = row["best_sampled_lag_min"]
        current = row["candidates"][str(ff.TANK_LAG_MIN)]
        selected = row["candidates"][str(best)]
        print(
            f"  {event_id}: best sampled={best} min "
            f"(RMSE {selected['rmse']:.2f} in); "
            f"current 15 min RMSE {current['rmse']:.2f} in"
        )
    print("forcing at current 15-minute lag")
    for event_id, fields in result["forcing"].items():
        bits = [
            f"{field} {row['peak_error_in']:+.2f} in"
            for field, row in fields.items()
        ]
        print(f"  {event_id}: " + "; ".join(bits))
    state = result["stateless_storage"]
    print(
        "stateless window\n"
        f"  current tank retains {state['fraction_remaining_after_60_dry_minutes']:.1%} "
        "after 60 dry minutes"
    )
    tide = result["tide_head_sample"]["largest_45_minute_change"]
    print(
        "tide head\n"
        f"  largest frozen-sample 45-minute astronomical change: "
        f"{tide['change_ft']:+.3f} ft"
    )
    candidate = result["time_varying_head_candidate"]
    for event_date, row in candidate["historical_head_replay"].items():
        fixed = row["fixed_head"]["rmse"]
        moving = row["moving_astronomy_constant_surge"]["rmse"]
        print(
            f"  {event_date}: head RMSE fixed {fixed:.3f} ft; "
            f"moving astronomy + constant surge {moving:.3f} ft"
        )
    accuracy = result["tide_accuracy"]
    print(
        "tide accuracy\n"
        f"  legacy daily bias: {accuracy['legacy_daily']['mean_bias']:+.3f} ft "
        f"(n={accuracy['legacy_daily']['n']})\n"
        f"  hourly joined bias: {accuracy['hourly_join']['mean_bias']:+.3f} ft "
        f"(n={accuracy['hourly_join']['n']}, "
        f"targets={accuracy['hourly_join']['n_targets']})"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print full JSON")
    args = parser.parse_args()
    result = assess()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_compact(result)


if __name__ == "__main__":
    main()
