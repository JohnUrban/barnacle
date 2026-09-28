#!/usr/bin/env python3
"""Decide whether the hourly workflow may publish after the forecast step
(audit 2026-09-27-a1 round 05 R4).

Exit status of flood_forecast_daily.py alone does not prove what happened:
Python's argument parser and a missing script also exit 2, so the delivery-
only failure status is DELIVERY_FAILED_EXIT (75) AND this script demands a
fresh completion receipt before allowing the publish-then-fail path.

    python3 forecast/publish_decision.py --rc <code> --started-utc <ISO Z>
        [--forecast-json docs/forecast.json] [--health data/alert_delivery_health.json]

Prints one word and exits 0 for the two publishable outcomes:
  publish            rc == 0
  publish-then-fail  rc == 75 and the receipt proves THIS invocation generated
                     the artifacts: health file written after --started-utc,
                     status "failed", run.forecast_generated_utc equal to the
                     forecast.json generation stamp, which is itself not older
                     than --started-utc.
Anything else prints a reason to stderr and exits 1 (do not publish).
"""
import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DELIVERY_FAILED_EXIT = 75


def _utc(value):
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must carry an offset")
    return parsed.astimezone(dt.timezone.utc)


def decide(rc, started_utc, forecast_json, health_path):
    """Return ("publish" | "publish-then-fail", None) or (None, reason)."""
    if rc == 0:
        return "publish", None
    if rc != DELIVERY_FAILED_EXIT:
        return None, f"forecast step exited {rc}: not a delivery-only failure; nothing publishes"
    try:
        started = _utc(started_utc)
    except (TypeError, ValueError) as exc:
        return None, f"invalid --started-utc: {exc}"
    try:
        with open(health_path) as f:
            health = json.load(f)
        with open(forecast_json) as f:
            forecast = json.load(f)
    except (OSError, ValueError) as exc:
        return None, f"exit {rc} without readable receipt/artifact: {exc}"
    try:
        updated = _utc(health.get("updated_utc"))
        generated = _utc(forecast.get("generated_utc"))
    except (TypeError, ValueError) as exc:
        return None, f"receipt/artifact stamps unreadable: {exc}"
    if health.get("status") != "failed":
        return None, f"exit {rc} but delivery health is {health.get('status')!r}, not 'failed'"
    if updated < started:
        return None, f"delivery receipt {health.get('updated_utc')} predates this run ({started_utc})"
    if generated < started - dt.timedelta(seconds=5):
        return None, f"forecast.json {forecast.get('generated_utc')} predates this run ({started_utc})"
    receipt_gen = (health.get("run") or {}).get("forecast_generated_utc")
    if not receipt_gen or _utc(receipt_gen) != generated:
        return None, (f"receipt forecast_generated_utc {receipt_gen!r} does not match "
                      f"forecast.json {forecast.get('generated_utc')!r}")
    return "publish-then-fail", None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rc", type=int, required=True)
    ap.add_argument("--started-utc", required=True)
    ap.add_argument("--forecast-json", default=os.path.join(ROOT, "docs", "forecast.json"))
    ap.add_argument("--health", default=os.path.join(ROOT, "data", "alert_delivery_health.json"))
    args = ap.parse_args(argv)
    outcome, reason = decide(args.rc, args.started_utc, args.forecast_json, args.health)
    if outcome is None:
        print(f"publish_decision: DO NOT PUBLISH — {reason}", file=sys.stderr)
        return 1
    print(outcome)
    return 0


if __name__ == "__main__":
    sys.exit(main())
