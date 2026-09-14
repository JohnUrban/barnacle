#!/usr/bin/env python3
"""GitHub-independent Barnacle freshness check (stdlib only).

Run this from infrastructure outside GitHub Actions and GitHub Pages. It
checks the public forecast, public nowcast, and the GitHub workflow API;
optionally it also checks scheduler-arm rows from the raw heartbeat CSV.
Exit 0 is healthy, 2 is unhealthy, 3 is an indeterminate fetch failure.
Set WATCHDOG_NTFY_TOPIC and pass --notify for bounded ntfy notification.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import tempfile
import urllib.request


UTC = dt.timezone.utc
FORECAST_URL = "https://johnurban.github.io/barnacle/forecast.json"
NOWCAST_URL = "https://johnurban.github.io/barnacle/nowcast.json"
RUNS_URL = ("https://api.github.com/repos/JohnUrban/barnacle/actions/"
            "workflows/nowcast.yml/runs?per_page=20")
HEARTBEAT_URL = ("https://raw.githubusercontent.com/JohnUrban/barnacle/"
                 "main/data/nowcast_heartbeats.csv")
UA = "barnacle-external-watchdog/1.0"


def _utc(value):
    return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=UTC)


def _age_minutes(value, now):
    return (now - _utc(value)).total_seconds() / 60.0


def assess(forecast, nowcast, runs, heartbeat_text="", now=None,
           required_arms=()):
    """Return a list of actionable health failures from fetched payloads."""
    now = now or dt.datetime.now(UTC)
    issues = []
    try:
        age = _age_minutes(forecast["generated_utc"], now)
        if age < -2 or age > 100:
            issues.append(f"forecast artifact is {age:.0f} minutes old")
    except (KeyError, TypeError, ValueError):
        issues.append("forecast artifact has no valid generated_utc")

    try:
        generated_age = _age_minutes(nowcast["generated_utc"], now)
        limit = 25 if nowcast.get("active") else 90
        if generated_age < -2 or generated_age > limit:
            issues.append(
                f"nowcast artifact is {generated_age:.0f} minutes old")
        if nowcast.get("active"):
            source_age = _age_minutes(nowcast["source_latest_utc"], now)
            if source_age < -2 or source_age > 20:
                issues.append(
                    f"active nowcast source is {source_age:.0f} minutes old")
            if nowcast.get("radar_quality") != "ok":
                issues.append("active nowcast radar_quality is not ok")
    except (KeyError, TypeError, ValueError):
        issues.append("nowcast artifact has invalid freshness metadata")

    completed = []
    for run in runs.get("workflow_runs", []):
        if run.get("status") == "completed" and run.get("conclusion") == "success":
            try:
                completed.append(_utc(run["updated_at"]))
            except (KeyError, TypeError, ValueError):
                pass
    if not completed:
        issues.append("nowcast workflow has no recent successful run")
    else:
        run_age = (now - max(completed)).total_seconds() / 60.0
        if run_age > 35:
            issues.append(
                f"last successful nowcast workflow is {run_age:.0f} minutes old")

    if required_arms:
        latest = {}
        try:
            for row in csv.DictReader(io.StringIO(heartbeat_text)):
                arm = row.get("arm") or "legacy-unknown"
                stamp = _utc(row["generated_utc"])
                latest[arm] = max(stamp, latest.get(arm, stamp))
        except (KeyError, TypeError, ValueError, csv.Error):
            issues.append("heartbeat ledger is unreadable")
        for arm in required_arms:
            if arm not in latest:
                issues.append(f"scheduler arm {arm} has no heartbeat")
            else:
                age = (now - latest[arm]).total_seconds() / 60.0
                if age > 90:
                    issues.append(
                        f"scheduler arm {arm} is {age:.0f} minutes stale")
    return issues


def _get(url, as_json=True):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    raw = urllib.request.urlopen(request, timeout=20).read().decode()
    return json.loads(raw) if as_json else raw


def _notify(issues, state_path, now):
    topic = os.environ.get("WATCHDOG_NTFY_TOPIC", "").strip()
    if not topic:
        return
    signature = hashlib.sha256("\n".join(sorted(issues)).encode()).hexdigest()
    state = {}
    try:
        with open(state_path) as source:
            state = json.load(source)
    except (OSError, ValueError):
        pass
    last = None
    try:
        last = _utc(state.get("sent_at", ""))
    except (TypeError, ValueError):
        pass
    if state.get("signature") == signature and last and now - last < dt.timedelta(hours=6):
        return
    body = "Barnacle watchdog: " + "; ".join(issues)
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}", data=body.encode(), method="POST",
        headers={"User-Agent": UA, "Title": "Barnacle health failure",
                 "Priority": "urgent", "Tags": "warning"})
    urllib.request.urlopen(req, timeout=20).read()
    os.makedirs(os.path.dirname(os.path.abspath(state_path)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="watchdog-", dir=os.path.dirname(
        os.path.abspath(state_path)))
    try:
        with os.fdopen(fd, "w") as dest:
            json.dump({"signature": signature,
                       "sent_at": now.strftime("%Y-%m-%dT%H:%M:%SZ")}, dest)
        os.replace(tmp, state_path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--notify", action="store_true")
    parser.add_argument("--require-arm", action="append", default=[])
    parser.add_argument("--state", default=os.environ.get(
        "WATCHDOG_STATE_PATH", "/tmp/barnacle-watchdog-state.json"))
    args = parser.parse_args()
    now = dt.datetime.now(UTC)
    try:
        forecast = _get(FORECAST_URL)
        nowcast = _get(NOWCAST_URL)
        runs = _get(RUNS_URL)
        heartbeats = _get(HEARTBEAT_URL, as_json=False) if args.require_arm else ""
    except Exception as exc:
        issues = [f"watchdog fetch failed: {exc}"]
        print(f"INDETERMINATE: {issues[0]}")
        if args.notify:
            try:
                _notify(issues, args.state, now)
            except Exception as notify_exc:
                print("INDETERMINATE: notification failed:", notify_exc)
        return 3
    issues = assess(forecast, nowcast, runs, heartbeats, now,
                    args.require_arm)
    if not issues:
        print("HEALTHY: forecast, nowcast, and scheduler execution are fresh")
        return 0
    for issue in issues:
        print("UNHEALTHY:", issue)
    if args.notify:
        try:
            _notify(issues, args.state, now)
        except Exception as exc:
            print("UNHEALTHY: notification failed:", exc)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
