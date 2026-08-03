#!/usr/bin/env python3
"""Deterministically replay the frozen v0.10.1 fit score and hindcasts.

This command is deliberately read-only: it loads repository-versioned inputs,
uses the production constants and stage curve, and exits nonzero if the frozen
RMS, event goldens, or model-version cutover no longer reproduce.  It does not
search for new parameters or write production artifacts.

Run from any directory:

    python history/scripts/reproduce_v0_10_1.py
    python history/scripts/reproduce_v0_10_1.py --json
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "model" / "data" / "v0.10.1-reproduction.json"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from forecast import flood_forecast_daily as ff  # noqa: E402


def load_fixture(path: Path = FIXTURE_PATH) -> dict:
    with path.open(encoding="utf-8") as handle:
        fixture = json.load(handle)
    if fixture.get("schema_version") != 1:
        raise ValueError("unsupported v0.10.1 reproduction fixture schema")
    return fixture


def _minutes(hhmm: str) -> int:
    hour, minute = (int(value) for value in hhmm.split(":"))
    return hour * 60 + minute


def _local_time(day: str, hhmm: str) -> dt.datetime:
    return dt.datetime.fromisoformat(f"{day}T{hhmm}:00")


def _drain_rate(bay_navd88_ft: float) -> float:
    span = ff.PLUVIAL_STREET_BASE - ff.PLUVIAL_DRAIN_FULL_BELOW
    open_fraction = min(
        1.0,
        max(0.0, (ff.PLUVIAL_STREET_BASE - bay_navd88_ft) / span),
    )
    return ff.PLUVIAL_DRAIN_RATE * open_fraction


def _volume_at_stage(curve: list[tuple[float, float]], stage: float) -> float:
    volume = 0.0
    for index in range(1, len(curve)):
        lower_stage = curve[index - 1][0]
        upper_stage, upper_area = curve[index]
        if upper_stage > stage:
            volume += upper_area * max(0.0, stage - lower_stage)
            return volume
        volume += upper_area * (upper_stage - lower_stage)
    if curve and stage > curve[-1][0]:
        volume += curve[-1][1] * (stage - curve[-1][0])
    return volume


def _stage_at_volume(curve: list[tuple[float, float]], volume: float) -> float:
    accumulated = 0.0
    for index in range(1, len(curve)):
        lower_stage = curve[index - 1][0]
        upper_stage, upper_area = curve[index]
        step_volume = upper_area * (upper_stage - lower_stage)
        if accumulated + step_volume >= volume:
            return lower_stage + (volume - accumulated) / upper_area
        accumulated += step_volume
    return curve[-1][0] + (volume - accumulated) / curve[-1][1]


def production_parameters(fixture: dict) -> tuple[float, float, float, int]:
    params = fixture["parameters"]
    return (
        float(params["tank_k"]),
        float(params["tank_gamma"]),
        float(params["tank_kout_per_hour"]),
        int(params["tank_lag_minutes"]),
    )


def simulate_fit_event(
    event: dict,
    parameters: tuple[float, float, float, int],
    step_minutes: float,
) -> dict[float, float]:
    """Replay the retained linear-interpolation fit recipe."""
    curve = ff._load_stage_curve()
    if not curve:
        raise RuntimeError("stage-storage curve is unavailable")
    tank_k, gamma, tank_kout, lag_minutes = parameters
    rain = [(_minutes(when), float(rate)) for when, rate in event["rain_in_hr"]]

    def rain_at(minute: float) -> float:
        minute -= lag_minutes
        if minute <= rain[0][0]:
            return rain[0][1]
        for index in range(1, len(rain)):
            if minute <= rain[index][0]:
                prior_time, prior_rate = rain[index - 1]
                next_time, next_rate = rain[index]
                fraction = (minute - prior_time) / (next_time - prior_time)
                return prior_rate + fraction * (next_rate - prior_rate)
        return rain[-1][1]

    bay = float(event["bay_navd88_ft"])
    drain = _drain_rate(bay)
    base_stage = max(0.0, (bay - ff.PLUVIAL_STREET_BASE) * 12.0)
    base_volume = _volume_at_stage(curve, base_stage)
    storage = 0.0
    output = {}
    minute = float(_minutes(event["run_from"]))
    end = float(_minutes(event["run_to"]))
    while minute <= end:
        net_rate = max(0.0, rain_at(minute) - drain)
        storage = max(
            0.0,
            storage
            + (tank_k * net_rate**gamma - tank_kout * storage)
            * (step_minutes / 60.0),
        )
        output[minute] = (
            _stage_at_volume(curve, base_volume + storage)
            if storage > 0
            else base_stage
        )
        minute += step_minutes
    return output


def fit_metrics(fixture: dict) -> dict:
    fit = fixture["fit"]
    parameters = production_parameters(fixture)
    squared_error = 0.0
    points = 0
    event_metrics = {}
    for event in fit["events"]:
        simulation = simulate_fit_event(
            event, parameters, float(fit["integration_step_minutes"])
        )
        for when, measured_stage in event["measured_stage_in"]:
            target = _minutes(when)
            nearest = min(simulation, key=lambda minute: abs(minute - target))
            squared_error += (simulation[nearest] - float(measured_stage)) ** 2
            points += 1
        peak_minute = max(simulation, key=simulation.get)
        event_metrics[event["id"]] = {
            "peak_stage_in": simulation[peak_minute],
            "peak_local_hhmm": f"{int(peak_minute) // 60:02d}:{int(peak_minute) % 60:02d}",
        }
    return {
        "points": points,
        "rms_inches": math.sqrt(squared_error / points),
        "events": event_metrics,
    }


def simulate_hindcast_event(event: dict, fixture: dict) -> list[tuple[dt.datetime, float]]:
    """Replay the retained step-held MRMS all-anchor recipe."""
    curve = ff._load_stage_curve()
    if not curve:
        raise RuntimeError("stage-storage curve is unavailable")
    tank_k, gamma, tank_kout, lag_minutes = production_parameters(fixture)
    step_minutes = float(fixture["hindcast"]["integration_step_minutes"])
    day = event["date"]
    rain_times = [_local_time(day, when) for when, _ in event["rain_in_hr"]]
    rain_values = {
        _local_time(day, when): float(rate) for when, rate in event["rain_in_hr"]
    }
    cutoff = rain_times[-1] + dt.timedelta(minutes=float(event["frame_minutes"]))
    lag = dt.timedelta(minutes=lag_minutes)
    bay = float(event["bay_navd88_ft"])
    drain = _drain_rate(bay)
    base_stage = max(0.0, (bay - ff.PLUVIAL_STREET_BASE) * 12.0)
    storage = 0.0
    output = []
    current = _local_time(day, event["run_from"])
    end = _local_time(day, event["run_to"])
    step = dt.timedelta(minutes=step_minutes)
    while current <= end:
        lagged = current - lag
        rain_rate = 0.0
        if lagged <= cutoff:
            for frame_time in rain_times:
                if frame_time <= lagged:
                    rain_rate = rain_values[frame_time]
                else:
                    break
        net_rate = max(0.0, rain_rate - drain)
        storage = max(
            0.0,
            storage
            + (tank_k * net_rate**gamma - tank_kout * storage)
            * (step_minutes / 60.0),
        )
        stage = (
            ff._pluvial_fill(curve, base_stage, storage)
            if storage > 0
            else base_stage
        )
        output.append((current, stage))
        current += step
    return output


def hindcast_metrics(fixture: dict) -> dict[str, dict]:
    metrics = {}
    for event in fixture["hindcast"]["events"]:
        simulation = simulate_hindcast_event(event, fixture)
        peak_time, peak_stage = max(simulation, key=lambda point: point[1])
        result = {
            "peak_stage_in": peak_stage,
            "peak_local": peak_time.isoformat(),
        }
        observation_time = event.get("observation_local")
        if observation_time:
            target = dt.datetime.fromisoformat(observation_time)
            nearest_time, nearest_stage = min(
                simulation, key=lambda point: abs((point[0] - target).total_seconds())
            )
            result["stage_at_observation_in"] = nearest_stage
            result["observation_local"] = nearest_time.isoformat()
        metrics[event["id"]] = result
    return metrics


def _verify_cutover(fixture: dict) -> dict:
    log_path = REPO_ROOT / "data" / "predictions_log.csv"
    with log_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    first = next(row for row in rows if row["model_version"] == "v0.10.1")
    expected = fixture["production_cutover_utc"]
    if first["prediction_made_at"] != expected:
        raise AssertionError(
            f"v0.10.1 log cutover changed: {first['prediction_made_at']} != {expected}"
        )
    return {
        "first_v0.10.1_prediction_utc": first["prediction_made_at"],
        "target_tide_time": first["target_tide_time"],
    }


def verify_reproduction(fixture: dict | None = None) -> dict:
    fixture = fixture or load_fixture()
    expected_parameters = production_parameters(fixture)
    actual_parameters = (
        ff.TANK_K,
        ff.TANK_GAMMA,
        ff.TANK_KOUT,
        ff.TANK_LAG_MIN,
    )
    if ff.CURRENT_MODEL_VERSION != fixture["model_version"]:
        raise AssertionError("production model version differs from fixture")
    if actual_parameters != expected_parameters:
        raise AssertionError(
            f"production parameters differ: {actual_parameters} != {expected_parameters}"
        )

    fit = fit_metrics(fixture)
    expected_rms = float(fixture["fit"]["expected_rms_inches"])
    if not math.isclose(fit["rms_inches"], expected_rms, rel_tol=0.0, abs_tol=1e-10):
        raise AssertionError(
            f"fit RMS changed: {fit['rms_inches']:.12f} != {expected_rms:.12f}"
        )
    reported_rms = float(fixture["fit"]["reported_rms_inches"])
    if round(fit["rms_inches"], 2) != reported_rms:
        raise AssertionError("fit RMS no longer rounds to the documented value")

    hindcasts = hindcast_metrics(fixture)
    for event in fixture["hindcast"]["events"]:
        actual = hindcasts[event["id"]]
        if not math.isclose(
            actual["peak_stage_in"],
            float(event["expected_peak_stage_in"]),
            rel_tol=0.0,
            abs_tol=1e-10,
        ):
            raise AssertionError(f"{event['id']} hindcast peak changed")
        if actual["peak_local"] != event["expected_peak_local"]:
            raise AssertionError(f"{event['id']} hindcast peak time changed")
        if "expected_stage_at_observation_in" in event and not math.isclose(
            actual["stage_at_observation_in"],
            float(event["expected_stage_at_observation_in"]),
            rel_tol=0.0,
            abs_tol=1e-10,
        ):
            raise AssertionError(f"{event['id']} observation-time hindcast changed")

    return {
        "model_version": ff.CURRENT_MODEL_VERSION,
        "parameters": {
            "tank_k": ff.TANK_K,
            "tank_gamma": ff.TANK_GAMMA,
            "tank_kout_per_hour": ff.TANK_KOUT,
            "tank_lag_minutes": ff.TANK_LAG_MIN,
        },
        "fit": fit,
        "hindcasts": hindcasts,
        "cutover": _verify_cutover(fixture),
        "evidence": fixture["evidence"],
    }


def _print_report(result: dict) -> None:
    params = result["parameters"]
    print(
        f"{result['model_version']} frozen production vector: "
        f"K={params['tank_k']:.0f}, gamma={params['tank_gamma']:.2f}, "
        f"k_out={params['tank_kout_per_hour']:.2f}/h, "
        f"lag={params['tank_lag_minutes']} min"
    )
    print(
        f"fit replay: RMS {result['fit']['rms_inches']:.6f} in over "
        f"{result['fit']['points']} points (reported 1.32 in)"
    )
    for event_id, event in result["hindcasts"].items():
        line = (
            f"{event_id:6s}: peak +{event['peak_stage_in']:.1f} in "
            f"at {event['peak_local'][11:16]} local"
        )
        if "stage_at_observation_in" in event:
            line += f"; observation-time +{event['stage_at_observation_in']:.1f} in"
        print(line)
    print(
        "model-version log cutover: "
        f"{result['cutover']['first_v0.10.1_prediction_utc']}"
    )
    print("verification: PASS (read-only; no production files written)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)
    result = verify_reproduction()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_report(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
