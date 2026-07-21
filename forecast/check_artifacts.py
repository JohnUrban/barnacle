#!/usr/bin/env python3
"""Publish gate (2026-07-18): refuse to ship corrupted artifacts.

Born from two incidents where git merge artifacts (autostash /
stash-pop conflicts) shipped conflict markers inside forecast.json —
iOS's strict JSON parser broke the widget both times while Python's
lenient one hid it. Run before ANY commit of docs/ or data/:
  1. no conflict markers anywhere in docs/ or data/
  2. every .json in docs/ parses under STRICT rules (json.loads
     forbidding NaN/Infinity — matches JSON.parse on iOS)
  3. canonical CSV ledgers have exact headers and row widths
  4. forecast.json carries valid provenance and input-health metadata
Exit 1 = do not commit.
"""
import json
import os
import sys
import csv
import datetime as dt
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# Canonical, actively consumed ledgers. Raw vendor downloads and archived
# research CSVs intentionally remain outside this shape gate.
CSV_SCHEMAS = {
    "data/forecast_accuracy.csv": [
        "forecast_run_date", "forecast_peak_predicted_mllw",
        "forecast_peak_predicted_time", "forecast_regime",
        "actual_peak_observed_mllw", "actual_peak_observed_time",
        "mllw_error_ft", "confidence_level",
    ],
    "data/labeled_observations.csv": [
        "observation_time_local", "landmark_key", "landmark_label",
        "observed_depth_in", "observed_qualitative", "sh_obs_mllw_actual",
        "model_predicted_depth_in", "weather_in_window", "observer", "notes",
    ],
    "data/predictions_log.csv": [
        "prediction_made_at", "target_tide_time", "hours_until_peak",
        "predicted_mllw_astronomical", "surge_ft_predicted", "surge_source",
        "sh_peak_mllw_predicted", "peak_rain_in_hr_predicted",
        "water_navd88_predicted", "regime_predicted", "cold_lockout",
        "confidence_level", "model_version",
    ],
    "data/labeled_events.csv": [
        "start", "end", "duration_h", "total_in", "peak_hr_in",
        "peak_hr_time", "label", "notes",
    ],
    "data/observed_peaks_cache.csv": [
        "target_tide_time", "observed_peak_mllw",
    ],
}


def validate_csv_ledger(path, expected_fields):
    """Return shape/schema failures for one canonical CSV ledger."""
    failures = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f, strict=True)
            try:
                header = next(reader)
            except StopIteration:
                return ["empty file"]
            if header != expected_fields:
                failures.append(
                    f"header mismatch: expected {expected_fields!r}, got {header!r}"
                )
            width = len(expected_fields)
            for logical_row, row in enumerate(reader, 2):
                if len(row) != width:
                    failures.append(
                        f"logical row {logical_row} (through physical line "
                        f"{reader.line_num}) has {len(row)} fields; expected {width}"
                    )
    except (OSError, UnicodeError, csv.Error) as e:
        failures.append(f"strict CSV parse: {e}")
    return failures


def source_model_version(root=ROOT):
    """Read the production model stamp without importing the forecast app."""
    path = os.path.join(root, "forecast", "flood_forecast_daily.py")
    try:
        with open(path, encoding="utf-8") as f:
            match = re.search(
                r'^CURRENT_MODEL_VERSION\s*=\s*["\']([^"\']+)["\']',
                f.read(), re.MULTILINE,
            )
    except OSError:
        return None
    return match.group(1) if match else None


def validate_forecast_metadata(path, expected_model_version=None):
    """Require provenance and internally consistent input-health metadata."""
    failures = []
    try:
        with open(path, encoding="utf-8") as f:
            forecast = json.load(f)
    except (OSError, UnicodeError, ValueError) as e:
        return [f"metadata read: {e}"]
    for key in ("generated_utc", "forecast_schema_version", "model_version",
                "input_health", "degraded_inputs"):
        if key not in forecast:
            failures.append(f"missing provenance field {key!r}")
    generated = forecast.get("generated_utc")
    try:
        parsed = dt.datetime.fromisoformat(str(generated).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone required")
    except (TypeError, ValueError):
        failures.append(f"generated_utc is not timezone-aware ISO-8601: {generated!r}")
    if forecast.get("forecast_schema_version") != "1.0":
        failures.append("forecast_schema_version must be '1.0'")
    if not isinstance(forecast.get("model_version"), str) or not forecast.get(
        "model_version"
    ):
        failures.append("model_version must be a non-empty string")
    elif (expected_model_version is not None
          and forecast.get("model_version") != expected_model_version):
        failures.append(
            f"model_version mismatch: source is {expected_model_version!r}, "
            f"forecast is {forecast.get('model_version')!r}"
        )
    health = forecast.get("input_health")
    degraded = forecast.get("degraded_inputs")
    if not isinstance(health, dict):
        failures.append("input_health must be an object")
    if not isinstance(degraded, list):
        failures.append("degraded_inputs must be an array")
    if isinstance(health, dict) and isinstance(degraded, list):
        allowed = {"ok", "degraded", "unavailable"}
        expected = []
        for name, item in health.items():
            status = item.get("status") if isinstance(item, dict) else None
            if status not in allowed:
                failures.append(f"input_health.{name} has invalid status {status!r}")
            elif status != "ok":
                expected.append(name)
        if sorted(degraded) != sorted(expected):
            failures.append(
                f"degraded_inputs mismatch: expected {sorted(expected)!r}, "
                f"got {sorted(degraded)!r}"
            )
    return failures


def check_artifacts(root=ROOT):
    bad = []
    for top in ("docs", "data"):
        for dirpath, _dirs, files in os.walk(os.path.join(root, top)):
            for fn in files:
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "rb") as f:
                        blob = f.read()
                except OSError:
                    continue
                if b"<<<<<<< " in blob or b">>>>>>> " in blob:
                    bad.append((path, "conflict markers"))
                    continue
                if fn.endswith(".json"):
                    try:
                        json.loads(
                            blob.decode("utf-8"),
                            parse_constant=lambda c: (_ for _ in ()).throw(
                                ValueError(f"non-strict constant {c}")),
                        )
                    except Exception as e:
                        bad.append((path, f"strict-parse: {e}"))
    for relpath, fields in CSV_SCHEMAS.items():
        path = os.path.join(root, relpath)
        for why in validate_csv_ledger(path, fields):
            bad.append((path, why))
    forecast_path = os.path.join(root, "docs", "forecast.json")
    expected_model = source_model_version(root)
    if expected_model is None:
        bad.append((os.path.join(root, "forecast", "flood_forecast_daily.py"),
                    "CURRENT_MODEL_VERSION not found"))
    for why in validate_forecast_metadata(forecast_path, expected_model):
        bad.append((forecast_path, why))
    return bad


def main():
    bad = check_artifacts()
    for path, why in bad:
        print(f"PUBLISH GATE FAIL: {os.path.relpath(path, ROOT)} — {why}")
    if bad:
        return 1
    print("publish gate: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
