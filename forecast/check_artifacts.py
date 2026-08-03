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
from zoneinfo import ZoneInfo

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
STATION_TZ = ZoneInfo("America/New_York")
FUTURE_TOLERANCE = dt.timedelta(minutes=5)

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


def _aware_time(value):
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed


def validate_csv_semantics(path, relpath, now_utc=None):
    """Validate domain invariants that a shape-only CSV gate cannot catch."""
    failures = []
    now = now_utc or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f, strict=True))
    except (OSError, UnicodeError, csv.Error) as exc:
        return [f"semantic parse: {exc}"]

    if relpath == "data/labeled_observations.csv":
        now_local = now.astimezone(STATION_TZ).replace(tzinfo=None)
        for logical_row, row in enumerate(rows, 2):
            stamp = row.get("observation_time_local", "")
            try:
                observed = dt.datetime.fromisoformat(stamp)
                if observed.tzinfo is not None:
                    observed = observed.astimezone(STATION_TZ).replace(tzinfo=None)
            except (TypeError, ValueError):
                failures.append(f"row {logical_row}: invalid local observation time {stamp!r}")
                continue
            if observed > now_local + FUTURE_TOLERANCE:
                failures.append(
                    f"row {logical_row}: observation time {stamp!r} is in the future"
                )
            if not (row.get("landmark_key") or "").strip():
                failures.append(f"row {logical_row}: landmark_key is empty")
            if not ((row.get("observed_depth_in") or "").strip()
                    or (row.get("observed_qualitative") or "").strip()):
                failures.append(f"row {logical_row}: no numeric or qualitative outcome")

    elif relpath == "data/predictions_log.csv":
        seen = set()
        allowed_confidence = {"low", "medium", "high"}
        allowed_regimes = {"", "dry", "street", "light", "moderate",
                           "severe", "cold_lockout"}
        for logical_row, row in enumerate(rows, 2):
            key = (row.get("prediction_made_at"), row.get("target_tide_time"))
            if key in seen:
                failures.append(f"row {logical_row}: duplicate prediction key {key!r}")
            seen.add(key)
            try:
                made = _aware_time(row.get("prediction_made_at"))
                target = dt.datetime.strptime(
                    row.get("target_tide_time", ""), "%Y-%m-%d %H:%M"
                ).replace(tzinfo=STATION_TZ)
                recorded = float(row.get("hours_until_peak", ""))
                actual = (target.astimezone(dt.timezone.utc)
                          - made.astimezone(dt.timezone.utc)).total_seconds() / 3600
                if abs(recorded - actual) > 0.02:
                    failures.append(
                        f"row {logical_row}: hours_until_peak differs by "
                        f"{recorded - actual:+.3f} h"
                    )
                if made > now + FUTURE_TOLERANCE:
                    failures.append(f"row {logical_row}: prediction_made_at is future")
            except (TypeError, ValueError) as exc:
                failures.append(f"row {logical_row}: invalid prediction timing: {exc}")
            if row.get("confidence_level") not in allowed_confidence:
                failures.append(f"row {logical_row}: invalid confidence_level")
            if row.get("regime_predicted") not in allowed_regimes:
                failures.append(f"row {logical_row}: invalid regime_predicted")
            if row.get("cold_lockout") not in {"true", "false"}:
                failures.append(f"row {logical_row}: cold_lockout must be true/false")
            if not (row.get("model_version") or "").strip():
                failures.append(f"row {logical_row}: model_version is empty")

    elif relpath == "data/forecast_accuracy.csv":
        seen = set()
        for logical_row, row in enumerate(rows, 2):
            day = row.get("forecast_run_date")
            if day in seen:
                failures.append(f"row {logical_row}: duplicate forecast_run_date {day}")
            seen.add(day)
            try:
                dt.date.fromisoformat(day)
                predicted = float(row["forecast_peak_predicted_mllw"])
                actual = float(row["actual_peak_observed_mllw"])
                error = float(row["mllw_error_ft"])
                if abs((predicted - actual) - error) > 1e-9:
                    failures.append(f"row {logical_row}: mllw_error_ft arithmetic mismatch")
            except (KeyError, TypeError, ValueError) as exc:
                failures.append(f"row {logical_row}: invalid accuracy row: {exc}")

    elif relpath == "data/observed_peaks_cache.csv":
        seen = set()
        for logical_row, row in enumerate(rows, 2):
            target = row.get("target_tide_time")
            if target in seen:
                failures.append(f"row {logical_row}: duplicate target_tide_time {target}")
            seen.add(target)
            try:
                dt.datetime.strptime(target, "%Y-%m-%d %H:%M")
                float(row.get("observed_peak_mllw", ""))
            except (TypeError, ValueError) as exc:
                failures.append(f"row {logical_row}: invalid observed peak: {exc}")
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


def validate_forecast_metadata(path, expected_model_version=None, now_utc=None):
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
        parsed = _aware_time(generated)
        now = now_utc or dt.datetime.now(dt.timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=dt.timezone.utc)
        if parsed.astimezone(dt.timezone.utc) > now + FUTURE_TOLERANCE:
            failures.append("generated_utc is in the future")
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


def validate_nowcast_metadata(path):
    failures = []
    try:
        with open(path, encoding="utf-8") as f:
            nowcast = json.load(f)
    except (OSError, UnicodeError, ValueError) as exc:
        return [f"metadata read: {exc}"]
    required = {
        "active", "generated_utc", "day_local", "radar_quality",
        "source_latest_utc", "source_age_min", "frames_expected",
        "frames_succeeded", "coverage_minutes", "projection_assumption",
    }
    for key in sorted(required - set(nowcast)):
        failures.append(f"missing nowcast provenance field {key!r}")
    if not isinstance(nowcast.get("active"), bool):
        failures.append("active must be boolean")
    try:
        generated = _aware_time(nowcast.get("generated_utc"))
    except (TypeError, ValueError) as exc:
        generated = None
        failures.append(f"invalid nowcast generation time: {exc}")
    try:
        dt.date.fromisoformat(nowcast.get("day_local", ""))
    except (TypeError, ValueError):
        failures.append("day_local is not an ISO date")
    quality = nowcast.get("radar_quality")
    if quality not in {"ok", "degraded", "unavailable"}:
        failures.append(f"invalid radar_quality {quality!r}")
    if nowcast.get("active") and quality != "ok":
        failures.append("active nowcast must have radar_quality='ok'")
    if quality in {"ok", "degraded"}:
        try:
            source = _aware_time(nowcast.get("source_latest_utc"))
            recorded_age = float(nowcast.get("source_age_min"))
            actual_age = (generated.astimezone(dt.timezone.utc)
                          - source.astimezone(dt.timezone.utc)).total_seconds() / 60
            if actual_age < -2 or abs(recorded_age - max(0, actual_age)) > 0.2:
                failures.append(
                    "source_age_min disagrees with source/generated timestamps"
                )
            if nowcast.get("active") and recorded_age > 10:
                failures.append("active nowcast source is older than 10 minutes")
        except (AttributeError, TypeError, ValueError) as exc:
            failures.append(f"invalid nowcast source timing: {exc}")
    elif (nowcast.get("source_latest_utc") is not None
          or nowcast.get("source_age_min") is not None):
        failures.append("unavailable radar must use null source time/age")
    frames = nowcast.get("frames") or []
    try:
        expected = int(nowcast.get("frames_expected"))
        succeeded = int(nowcast.get("frames_succeeded"))
        if succeeded != len(frames):
            failures.append("frames_succeeded does not match frames array")
        if succeeded > expected or expected < 0:
            failures.append("invalid expected/succeeded frame counts")
        if quality == "ok" and expected < 1:
            failures.append("ok radar requires at least one expected frame")
    except (TypeError, ValueError):
        failures.append("frame counts must be integers")
    for index, frame in enumerate(frames):
        try:
            _aware_time(frame.get("utc"))
            float(frame.get("in_hr"))
        except (AttributeError, TypeError, ValueError) as exc:
            failures.append(f"frame {index}: invalid provenance/rate: {exc}")
    return failures


def validate_alert_state(path):
    failures = []
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, UnicodeError, ValueError) as exc:
        return [f"state read: {exc}"]
    if not isinstance(state, dict):
        return ["alert state must be an object"]
    for key in ("rank", "sig", "updated", "last_sent_rank",
                "last_sent_sig", "last_sent_ts", "last_sent_channels",
                "sends_today"):
        if key not in state:
            failures.append(f"missing alert-state field {key!r}")
    for key in ("updated", "last_sent_ts"):
        if state.get(key):
            try:
                _aware_time(state[key])
            except (TypeError, ValueError):
                failures.append(f"{key} must be timezone-aware ISO-8601")
    if not isinstance(state.get("last_sent_channels"), list):
        failures.append("last_sent_channels must be an array")
    sends = state.get("sends_today")
    if not isinstance(sends, dict):
        failures.append("sends_today must be an object")
    elif sends:
        try:
            dt.date.fromisoformat(sends["date"])
            if int(sends["count"]) < 0:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            failures.append("sends_today must contain ISO date and nonnegative count")
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
        for why in validate_csv_semantics(path, relpath):
            bad.append((path, why))
    forecast_path = os.path.join(root, "docs", "forecast.json")
    expected_model = source_model_version(root)
    if expected_model is None:
        bad.append((os.path.join(root, "forecast", "flood_forecast_daily.py"),
                    "CURRENT_MODEL_VERSION not found"))
    for why in validate_forecast_metadata(forecast_path, expected_model):
        bad.append((forecast_path, why))
    nowcast_path = os.path.join(root, "docs", "nowcast.json")
    for why in validate_nowcast_metadata(nowcast_path):
        bad.append((nowcast_path, why))
    alert_path = os.path.join(root, "data", "alert_state.json")
    for why in validate_alert_state(alert_path):
        bad.append((alert_path, why))
    for relpath in ("docs/index.html", "docs/details.html",
                    "docs/forecast.json", "docs/nowcast.json",
                    "docs/barnacle-widget.js"):
        path = os.path.join(root, relpath)
        if not os.path.isfile(path):
            bad.append((path, "required publish artifact is missing"))
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
