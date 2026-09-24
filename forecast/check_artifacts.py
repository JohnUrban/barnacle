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
import math
import re
from zoneinfo import ZoneInfo

try:
    from .html_contract import validate_current_surfaces
except ImportError:  # direct `python forecast/check_artifacts.py` execution
    from html_contract import validate_current_surfaces

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
STATION_TZ = ZoneInfo("America/New_York")
FUTURE_TOLERANCE = dt.timedelta(minutes=5)

# Canonical, actively consumed ledgers. Raw vendor downloads and archived
# research CSVs intentionally remain outside this shape gate.
CSV_SCHEMAS = {
    "data/outlook_log.csv": [
        "generated_utc", "target_tide_time", "lead_h", "astro_mllw",
        "nws_product_mllw", "nwps_mllw", "petss_p10_mllw", "petss_p90_mllw",
        "persist_flat_mllw", "persist_decay_mllw", "production_mllw",
        "production_source", "outlook_mllw", "outlook_source", "qpf6_in",
        "qpf6_source", "pop_pct", "gust_mph", "xcheck_p_half_inch_pct",
        "model_version",
    ],
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
    "data/day_risk_log.csv": [
        "generated_utc", "local_day", "pluvial_level", "burst_est_in_hr",
        "potential_navd88", "model_version",
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


def _station_time(value):
    """Parse offset-bearing current or legacy naive station timestamps."""
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=STATION_TZ, fold=0)
    return parsed.astimezone(STATION_TZ)


def _station_stamp(value):
    """Parse a persisted station-local stamp in either accepted form.

    Legacy rows: naive ``YYYY-MM-DD HH:MM`` (fold=0). Rows written after
    the 2026-09-18 GMT migration: offset-bearing ``YYYY-MM-DD HH:MM-04:00``.
    Anything else is rejected. (2026-09-19→20 outage: the accuracy writer
    began emitting offset-bearing observed times while this validator
    still demanded the naive form — 42 hourly publishes failed the gate.)
    """
    text = str(value).strip()
    try:
        return dt.datetime.strptime(text, "%Y-%m-%d %H:%M").replace(
            tzinfo=STATION_TZ)
    except ValueError:
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            raise ValueError(f"station stamp must be naive HH:MM or "
                             f"offset-bearing: {text!r}")
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
        allowed_confidence = {"low", "medium", "high", ""}   # labels retired 2026-09-23
        allowed_regimes = {"", "dry", "street", "light", "moderate",
                           "severe", "cold_lockout"}
        for logical_row, row in enumerate(rows, 2):
            key = (row.get("prediction_made_at"), row.get("target_tide_time"))
            if key in seen:
                failures.append(f"row {logical_row}: duplicate prediction key {key!r}")
            seen.add(key)
            try:
                made = _aware_time(row.get("prediction_made_at"))
                target = _station_time(row.get("target_tide_time", ""))
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
        allowed_regimes = {"dry", "street", "light", "moderate", "severe",
                           "cold_lockout"}
        allowed_confidence = {"low", "medium", "high", ""}   # labels retired 2026-09-23
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
                if not all(map(math.isfinite, (predicted, actual, error))):
                    raise ValueError("nonfinite number")
                if abs((predicted - actual) - error) > 1e-9:
                    failures.append(f"row {logical_row}: mllw_error_ft arithmetic mismatch")
                for field in ("forecast_peak_predicted_time",
                              "actual_peak_observed_time"):
                    _station_stamp(row[field])
            except (KeyError, TypeError, ValueError) as exc:
                failures.append(f"row {logical_row}: invalid accuracy row: {exc}")
            if row.get("forecast_regime") not in allowed_regimes:
                failures.append(f"row {logical_row}: invalid forecast_regime")
            if row.get("confidence_level") not in allowed_confidence:
                failures.append(f"row {logical_row}: invalid confidence_level")

    elif relpath == "data/outlook_log.csv":
        allowed_sources = {"nws_product", "nwps", "petss_mid", "guidance_decay", "persist_decay", "astro"}
        allowed_prod = {"", "nws-coastal-flood-product", "surge-persistence",
                        "astronomical-only-degraded", "typical-offset-degraded"}
        allowed_rain = {"", "nws_grid", "nbm", "wpc_24h"}
        for logical_row, row in enumerate(rows, 2):
            try:
                made = _aware_time(row.get("generated_utc"))
                if made > now + FUTURE_TOLERANCE:
                    failures.append(f"row {logical_row}: generated_utc is future")
                _station_stamp(row.get("target_tide_time", ""))
                lead = float(row.get("lead_h", ""))
                if not math.isfinite(lead) or lead < 0 or lead > 200:
                    failures.append(f"row {logical_row}: lead_h out of range")
                for field in ("astro_mllw", "outlook_mllw"):
                    v = float(row.get(field, ""))
                    if not math.isfinite(v) or not (-5 < v < 25):
                        failures.append(f"row {logical_row}: {field} out of range")
                for field in ("nws_product_mllw", "nwps_mllw", "petss_p10_mllw", "petss_p90_mllw",
                              "persist_flat_mllw", "persist_decay_mllw", "production_mllw",
                              "qpf6_in", "pop_pct", "gust_mph", "xcheck_p_half_inch_pct"):
                    text = row.get(field, "")
                    if text != "" and not math.isfinite(float(text)):
                        failures.append(f"row {logical_row}: {field} non-finite")
            except (TypeError, ValueError) as exc:
                failures.append(f"row {logical_row}: invalid outlook row: {exc}")
            if row.get("outlook_source") not in allowed_sources:
                failures.append(f"row {logical_row}: invalid outlook_source")
            if row.get("production_source") not in allowed_prod:
                failures.append(f"row {logical_row}: invalid production_source")
            if row.get("qpf6_source") not in allowed_rain:
                failures.append(f"row {logical_row}: invalid qpf6_source")

    elif relpath == "data/labeled_events.csv":
        allowed_labels = {"flood", "noflood", "noflood_at_342", "unlabeled"}
        for logical_row, row in enumerate(rows, 2):
            try:
                start = dt.datetime.strptime(row["start"], "%Y-%m-%d %H:%M:%S")
                end = dt.datetime.strptime(row["end"], "%Y-%m-%d %H:%M:%S")
                peak = dt.datetime.strptime(
                    row["peak_hr_time"], "%Y-%m-%d %H:%M:%S")
                duration = float(row["duration_h"])
                total = float(row["total_in"])
                rate = float(row["peak_hr_in"])
                if not all(map(math.isfinite, (duration, total, rate))):
                    raise ValueError("nonfinite number")
                if end < start or not start <= peak <= end:
                    raise ValueError("event times are not ordered")
                if duration < 0 or total < 0 or rate < 0:
                    raise ValueError("negative duration or rainfall")
                actual_h = (end - start).total_seconds() / 3600.0
                if abs(actual_h - duration) > 1.01:
                    raise ValueError("duration disagrees with timestamps")
            except (KeyError, TypeError, ValueError) as exc:
                failures.append(f"row {logical_row}: invalid labeled event: {exc}")
            if row.get("label") not in allowed_labels:
                failures.append(f"row {logical_row}: invalid event label")

    elif relpath == "data/observed_peaks_cache.csv":
        seen = set()
        for logical_row, row in enumerate(rows, 2):
            target = row.get("target_tide_time")
            if target in seen:
                failures.append(f"row {logical_row}: duplicate target_tide_time {target}")
            seen.add(target)
            try:
                _station_time(target)
                float(row.get("observed_peak_mllw", ""))
            except (TypeError, ValueError) as exc:
                failures.append(f"row {logical_row}: invalid observed peak: {exc}")
    elif relpath == "data/day_risk_log.csv":
        seen = set()
        for logical_row, row in enumerate(rows, 2):
            try:
                stamp = _aware_time(row.get("generated_utc"))
                local_day = dt.date.fromisoformat(row.get("local_day", ""))
                if stamp.astimezone(STATION_TZ).date() != local_day:
                    raise ValueError("local_day disagrees with generated_utc")
                if row.get("pluvial_level") not in {"", "possible", "elevated"}:
                    raise ValueError("invalid pluvial_level")
                for field in ("burst_est_in_hr", "potential_navd88"):
                    if row.get(field):
                        value = float(row[field])
                        if not math.isfinite(value) or value < 0:
                            raise ValueError(f"invalid {field}")
                if not (row.get("model_version") or "").startswith("v"):
                    raise ValueError("invalid model_version")
                key = row.get("generated_utc")
                if key in seen:
                    raise ValueError("duplicate generated_utc")
                seen.add(key)
            except (TypeError, ValueError) as exc:
                failures.append(f"row {logical_row}: invalid day-risk row: {exc}")
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
                if "outlook_degraded_inputs" not in forecast or not name.startswith("outlook_"):
                    expected.append(name)
        if sorted(degraded) != sorted(expected):
            failures.append(
                f"degraded_inputs mismatch: expected {sorted(expected)!r}, "
                f"got {sorted(degraded)!r}"
            )
    if isinstance(health, dict) and "outlook_degraded_inputs" in forecast:
        expected_outlook = sorted(name for name, item in health.items()
                                  if isinstance(item, dict) and item.get("status") != "ok"
                                  and name.startswith("outlook_"))
        if forecast["outlook_degraded_inputs"] != expected_outlook:
            failures.append("outlook_degraded_inputs mismatch")
    si = forecast.get("water_series_input")
    if si is not None:
        if not isinstance(si, dict) or si.get("source") not in {"surge-persistence", "typical-offset", "unavailable"}:
            failures.append("invalid water_series_input")
        elif si["source"] == "unavailable":
            if si.get("surge_ft") is not None or forecast.get("water_series"):
                failures.append("unavailable series input must not produce a numeric curve")
        elif not isinstance(si.get("surge_ft"), (int, float)) or not math.isfinite(si["surge_ft"]):
            failures.append("series persistence requires finite surge")
    failures.extend(validate_outlook_field(forecast))
    return failures


def validate_outlook_field(forecast):
    """Scientific-contract checks on `outlook_7d` (audit R10): horizon,
    model stamp, ordered finite series, seven consecutive day cards, source
    statuses, and a future worst point."""
    ol = forecast.get("outlook_7d")
    if ol is None:
        return []
    failures = []
    if not isinstance(ol, dict):
        return ["outlook_7d must be an object or null"]
    if ol.get("horizon_hours") != 168:
        failures.append("outlook_7d.horizon_hours must be 168")
    if ol.get("model_version") != forecast.get("model_version"):
        failures.append("outlook_7d.model_version must match the forecast stamp")
    series = ol.get("series")
    if not isinstance(series, list):
        failures.append("outlook_7d.series must be an array")
    else:
        last = None
        for i, p in enumerate(series):
            try:
                t = _station_stamp(p["time"])
                for k in ("tide_navd88", "water_navd88"):
                    v = float(p[k])
                    if not math.isfinite(v) or not (-10 < v < 30):
                        raise ValueError(f"{k} out of range")
                if p.get("pluvial_navd88") is not None and not math.isfinite(float(p["pluvial_navd88"])):
                    raise ValueError("pluvial_navd88 non-finite")
                if last is not None and t <= last:
                    raise ValueError("series times not strictly ascending")
                last = t
            except (KeyError, TypeError, ValueError) as exc:
                failures.append(f"outlook_7d.series[{i}]: {exc}")
                break
    days = ol.get("days")
    if not isinstance(days, list) or len(days) not in (7, 8):
        failures.append("outlook_7d.days must hold the 7 or 8 calendar dates the 168-h horizon touches")
    else:
        try:
            dates = [dt.date.fromisoformat(d["date"]) for d in days]
            if any((b - a).days != 1 for a, b in zip(dates, dates[1:])):
                failures.append("outlook_7d.days must be consecutive dates")
        except (KeyError, TypeError, ValueError):
            failures.append("outlook_7d.days dates unparseable")
    sources = ol.get("sources")
    if not isinstance(sources, dict):
        failures.append("outlook_7d.sources must be an object")
    else:
        for name, h in sources.items():
            if not isinstance(h, dict) or h.get("status") not in ("ok", "degraded", "unavailable"):
                failures.append(f"outlook_7d.sources.{name} has an invalid status")
    worst = (ol.get("worst") or {}).get("flood_chance")
    if worst:
        try:
            if _station_stamp(worst["time"]) < _aware_time(forecast.get("generated_utc")) - dt.timedelta(hours=1):
                failures.append("outlook_7d.worst.flood_chance is in the past")
        except (KeyError, TypeError, ValueError):
            failures.append("outlook_7d.worst.flood_chance unparseable")
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
    if nowcast.get("nowcast_schema_version") != "1.0":
        failures.append("nowcast_schema_version must be '1.0'")
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
    prior_stamp = None
    for index, frame in enumerate(frames):
        try:
            stamp = _aware_time(frame.get("utc"))
            rate = float(frame.get("in_hr"))
            if not math.isfinite(rate) or rate < 0:
                raise ValueError("rain rate must be finite and nonnegative")
            if prior_stamp is not None and stamp <= prior_stamp:
                raise ValueError("frames must be strictly time-sorted")
            prior_stamp = stamp
        except (AttributeError, TypeError, ValueError) as exc:
            failures.append(f"frame {index}: invalid provenance/rate: {exc}")
    if nowcast.get("active"):
        for key in ("street_now_in", "peak_proj_in", "trend"):
            if key not in nowcast:
                failures.append(f"active nowcast missing {key!r}")
        if nowcast.get("trend") not in {"rising", "falling"}:
            failures.append("active nowcast trend must be rising/falling")
        for key in ("street_now_in", "peak_proj_in"):
            try:
                if not math.isfinite(float(nowcast[key])):
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                failures.append(f"active nowcast {key} must be finite")
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
    elif not set(state["last_sent_channels"]) <= {"ntfy", "email", "sms"}:
        failures.append("last_sent_channels contains an unknown rail")
    for key in ("rank", "last_sent_rank"):
        if not isinstance(state.get(key), int) or not 0 <= state[key] <= 4:
            failures.append(f"{key} must be an integer from 0 through 4")
    for key in ("sig", "last_sent_sig"):
        if not isinstance(state.get(key), str):
            failures.append(f"{key} must be a string")
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
    for name, event in (("sms_event", state.get("sms_event")),
                        *((f"imminent_channels.{channel}", event)
                          for channel, event in
                          (state.get("imminent_channels") or {}).items())):
        if event is None:
            continue
        try:
            _aware_time(event["ts"])
            if not isinstance(event["class"], int) or not 1 <= event["class"] <= 3:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            failures.append(f"{name} must contain UTC ts and class 1-3")
    return failures


def validate_surface_stamps(root=ROOT):
    """Require every current display arm to describe one forecast build."""
    failures = []
    forecast_path = os.path.join(root, "docs", "forecast.json")
    try:
        with open(forecast_path, encoding="utf-8") as source:
            forecast = json.load(source)
    except (OSError, ValueError) as exc:
        return [(forecast_path, f"surface stamp source unreadable: {exc}")]
    expected = {
        "barnacle-generated-utc": str(forecast.get("generated_utc", "")),
        "barnacle-schema-version": str(
            forecast.get("forecast_schema_version", "")),
        "barnacle-model-version": str(forecast.get("model_version", "")),
    }

    def check_html(path):
        try:
            with open(path, encoding="utf-8") as source:
                text = source.read()
        except OSError as exc:
            failures.append((path, f"surface unreadable: {exc}"))
            return
        for name, value in expected.items():
            marker = f'<meta name="{name}" content="{value}">'
            if marker not in text:
                failures.append((path, f"missing/mismatched {name} stamp"))

    check_html(os.path.join(root, "docs", "index.html"))
    check_html(os.path.join(root, "docs", "details.html"))
    check_html(os.path.join(root, "docs", "outlook.html"))
    for tide in forecast.get("all_tides") or []:
        stamp = str(tide.get("time", ""))[:16]
        if " " not in stamp:
            continue
        day, clock = stamp.split(" ", 1)
        slug = f"{day}T{clock.replace(':', '-')}"
        tide_dir = os.path.join(root, "docs", "tides", slug)
        check_html(os.path.join(tide_dir, "index.html"))
        tide_json = os.path.join(tide_dir, "forecast.json")
        try:
            with open(tide_json, encoding="utf-8") as source:
                payload = json.load(source)
        except (OSError, ValueError) as exc:
            failures.append((tide_json, f"surface unreadable: {exc}"))
            continue
        for key in ("generated_utc", "forecast_schema_version", "model_version"):
            if payload.get(key) != forecast.get(key):
                failures.append((tide_json, f"mismatched {key} stamp"))
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
    bad.extend(validate_surface_stamps(root))
    bad.extend(validate_current_surfaces(root))
    for relpath in ("docs/index.html", "docs/details.html", "docs/outlook.html",
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
