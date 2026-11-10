#!/usr/bin/env python3
"""Re-derive the OBSERVED half of data/forecast_accuracy.csv from NOAA.

Why (2026-11-10 health check): the scorer wrote a row as soon as the
+/-2 h window around a forecast's target tide returned any gauge data.
For a tide a day or two after the run date that was about two hours
before the peak, so the "observed peak" was a reading on the rising limb.
An older variant did the same to same-day evening tides (May to Aug 1).

Owner decision (John, 2026-11-10; BACKLOG DECISION accuracy-ledger-in-place):
this ledger is a DERIVED score, reproducible from the archived forecast
and the gauge, so its wrong rows are corrected IN PLACE. The as-recorded
file is kept under history/data/ and every change is itemised in a report
under history/reports/. The as-issued half of each row (run date,
predicted peak, predicted time, regime, confidence label) is never
touched, and neither are the archives or predictions_log.csv.

What it does, per row:
  * asks NOAA for the full window with the scorer's own function
    (flood_forecast_daily._fetch_actual_peak_around), so a corrected row
    is exactly what the repaired scorer would write today;
  * leaves the row's bytes alone when the observed peak is unchanged;
  * otherwise replaces observed peak, observed time and the error, and
    records why: the recorded reading is still in NOAA's series and a
    higher one came later (scored-early), NOAA's reading for the recorded
    minute has changed (noaa-revised), or both.

All-or-nothing: if any row cannot be fetched, or the corrected file fails
the publish gate's CSV rules, nothing is written. Re-running after a
successful apply changes nothing.

  rescore_forecast_accuracy.py                 dry run, prints a summary
  rescore_forecast_accuracy.py --apply --tag 2026-11-10
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
import shutil
import statistics
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "forecast"))
import check_artifacts  # noqa: E402
import flood_forecast_daily as ff  # noqa: E402

LEDGER = os.path.join(REPO, "data", "forecast_accuracy.csv")
HISTORY = os.path.join(REPO, "history")
RELPATH = "data/forecast_accuracy.csv"
SAME_FT = 0.0005          # NOAA publishes millifeet
FIELDS = check_artifacts.CSV_SCHEMAS[RELPATH]


def _parse(value):
    return ff.parse_station_local_time(value)


def fetch_window(pred_time, retries=6):
    """(peak, peak_time, raw rows) via the scorer's own fetch, capturing
    the NOAA response it used. Returns (None, None, []) when NOAA has
    nothing after every retry."""
    captured = {}
    real_get = ff._get

    def spy(url, params=None, *args, **kwargs):
        data = real_get(url, params, *args, **kwargs)
        if isinstance(params, dict) and params.get("product") == "water_level":
            captured["data"] = data
        return data

    for attempt in range(retries):
        captured.clear()
        ff._get = spy
        try:
            peak, peak_time = ff._fetch_actual_peak_around(
                pred_time, window_hours=ff.ACCURACY_WINDOW_HOURS)
        finally:
            ff._get = real_get
        if peak is not None:
            raw = []
            for row in ff._localize_noaa_gmt_rows(
                    (captured.get("data") or {}).get("data") or []):
                try:
                    raw.append((_parse(row.get("t")), float(row["v"])))
                except (KeyError, TypeError, ValueError):
                    continue
            return peak, peak_time, raw
        time.sleep(1.5 * (attempt + 1))
    return None, None, []


def classify(old_peak, old_time, new_peak, new_time, raw):
    at_old = next((v for t, v in raw if t == old_time), None)
    later = new_time > old_time
    revised = at_old is not None and abs(at_old - old_peak) >= SAME_FT
    if at_old is None:
        return "recorded-reading-absent", at_old
    if later and not revised:
        return "scored-early", at_old
    if later and revised:
        return "scored-early+noaa-revised", at_old
    if revised:
        return "noaa-revised", at_old
    return "other", at_old


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--tag", default=dt.datetime.now(
        dt.timezone.utc).strftime("%Y-%m-%d"))
    parser.add_argument("--pace", type=float, default=0.4,
                        help="seconds between NOAA requests")
    args = parser.parse_args(argv)
    snapshot = os.path.join(HISTORY, "data",
                            f"forecast_accuracy_as_recorded_{args.tag}.csv")
    detail = os.path.join(HISTORY, "reports",
                          f"{args.tag}-forecast-accuracy-rescore.csv")
    summary_path = os.path.join(HISTORY, "reports",
                                f"{args.tag}-forecast-accuracy-rescore.json")

    with open(LEDGER, newline="") as source:
        original = source.read()
    lines = original.split("\n")
    assert lines[-1] == "", "ledger must end with a newline"
    lines = lines[:-1]
    rows = list(csv.DictReader(io.StringIO(original)))
    assert len(rows) == len(lines) - 1, "one physical line per row expected"
    assert list(rows[0].keys()) == list(FIELDS), "unexpected ledger columns"

    now = dt.datetime.now(dt.timezone.utc)
    retrieved = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    out_lines = [lines[0]]
    report = []
    unfetched = []
    for index, row in enumerate(rows, 1):
        raw_line = lines[index]
        pred_time = row["forecast_peak_predicted_time"]
        pred = float(row["forecast_peak_predicted_mllw"])
        old_peak = float(row["actual_peak_observed_mllw"])
        old_time = _parse(row["actual_peak_observed_time"])
        lead_days = (_parse(pred_time).date()
                     - dt.date.fromisoformat(row["forecast_run_date"])).days
        entry = {
            "forecast_run_date": row["forecast_run_date"],
            "forecast_peak_predicted_mllw": row["forecast_peak_predicted_mllw"],
            "forecast_peak_predicted_time": pred_time,
            "lead_days": lead_days,
            "recorded_observed_mllw": row["actual_peak_observed_mllw"],
            "recorded_observed_time": row["actual_peak_observed_time"],
            "recorded_error_ft": f"{float(row['mllw_error_ft']):+.3f}",
        }
        if ff.hours_until_station_time(pred_time, now) > -ff.ACCURACY_WINDOW_HOURS:
            # Its window is still open: leave it for a later run.
            entry.update(outcome="window-open", reason="")
            report.append(entry)
            out_lines.append(raw_line)
            continue
        new_peak, new_time_str, raw = fetch_window(pred_time)
        time.sleep(args.pace)
        if new_peak is None:
            unfetched.append(row["forecast_run_date"])
            continue
        new_time = _parse(new_time_str)
        entry.update(
            rederived_observed_mllw=f"{new_peak:.3f}",
            rederived_observed_time=ff.station_time_storage_key(new_time_str),
            rederived_error_ft=f"{pred - new_peak:+.3f}",
            change_ft=f"{new_peak - old_peak:+.3f}",
            readings_in_window=len(raw),
            noaa_retrieved_utc=retrieved)
        if abs(new_peak - old_peak) < SAME_FT:
            entry.update(outcome="unchanged", reason="")
            out_lines.append(raw_line)
        else:
            reason, at_old = classify(old_peak, old_time, new_peak, new_time, raw)
            entry.update(outcome="corrected", reason=reason,
                         noaa_now_at_recorded_minute=(
                             "" if at_old is None else f"{at_old:.3f}"))
            fixed = dict(row)
            fixed["actual_peak_observed_mllw"] = new_peak
            fixed["actual_peak_observed_time"] = ff.station_time_storage_key(
                new_time_str)
            fixed["mllw_error_ft"] = pred - new_peak
            buffer = io.StringIO()
            csv.DictWriter(buffer, fieldnames=FIELDS,
                           lineterminator="\n").writerow(fixed)
            out_lines.append(buffer.getvalue().rstrip("\n"))
        report.append(entry)

    if unfetched:
        print(f"ABORT: NOAA returned nothing for {len(unfetched)} row(s): "
              f"{unfetched}. Nothing written.")
        return 3

    corrected = [e for e in report if e["outcome"] == "corrected"]
    rec = [float(e["recorded_error_ft"]) for e in report
           if e["outcome"] != "window-open"]
    new = [float(e["rederived_error_ft"]) for e in report
           if e["outcome"] != "window-open"]

    def stats(errors):
        return {"n": len(errors),
                "mean_error_ft": round(statistics.mean(errors), 3),
                "mean_abs_error_ft": round(
                    statistics.mean(abs(e) for e in errors), 3),
                "worst_abs_error_ft": round(max(abs(e) for e in errors), 3)}

    reasons = {}
    for e in corrected:
        reasons[e["reason"]] = reasons.get(e["reason"], 0) + 1
    by_lead = {}
    for e in corrected:
        by_lead[str(e["lead_days"])] = by_lead.get(str(e["lead_days"]), 0) + 1
    changes = sorted(float(e["change_ft"]) for e in corrected)
    summary = {
        "ledger": RELPATH, "noaa_retrieved_utc": retrieved,
        "rows": len(rows), "corrected": len(corrected),
        "unchanged": sum(e["outcome"] == "unchanged" for e in report),
        "window_open": sum(e["outcome"] == "window-open" for e in report),
        "corrected_by_reason": reasons,
        "corrected_by_lead_days": by_lead,
        "observed_peak_raised": sum(c > 0 for c in changes),
        "observed_peak_lowered": sum(c < 0 for c in changes),
        "change_ft": ({"median": round(statistics.median(changes), 3),
                       "max": round(max(changes), 3),
                       "min": round(min(changes), 3)} if changes else {}),
        "all_rows": {"as_recorded": stats(rec), "rederived": stats(new)},
        "last_30": {"as_recorded": stats(rec[-30:]),
                    "rederived": stats(new[-30:])},
    }
    print(json.dumps(summary, indent=1))

    if not args.apply:
        print("dry run: nothing written (pass --apply)")
        return 0
    if not corrected:
        print("nothing to correct: ledger left as is")
        return 0
    if os.path.exists(snapshot):
        print(f"ABORT: {snapshot} already exists; choose another --tag")
        return 4

    # Validate the corrected ledger with the publish gate's own CSV rules
    # BEFORE anything is written.
    corrected_text = "\n".join(out_lines) + "\n"
    fd, tmp = tempfile.mkstemp(prefix="accuracy-", suffix=".csv",
                               dir=os.path.dirname(LEDGER))
    try:
        with os.fdopen(fd, "w", newline="") as dest:
            dest.write(corrected_text)
        failures = check_artifacts.validate_csv_semantics(tmp, RELPATH)
        if failures:
            print("ABORT: corrected ledger fails the gate:", failures[:5])
            return 5
        os.makedirs(os.path.dirname(snapshot), exist_ok=True)
        os.makedirs(os.path.dirname(detail), exist_ok=True)
        shutil.copyfile(LEDGER, snapshot)
        columns = ["forecast_run_date", "forecast_peak_predicted_mllw",
                   "forecast_peak_predicted_time", "lead_days",
                   "recorded_observed_mllw", "recorded_observed_time",
                   "recorded_error_ft", "rederived_observed_mllw",
                   "rederived_observed_time", "rederived_error_ft",
                   "change_ft", "outcome", "reason",
                   "noaa_now_at_recorded_minute", "readings_in_window",
                   "noaa_retrieved_utc"]
        with open(detail, "w", newline="") as dest:
            writer = csv.DictWriter(dest, fieldnames=columns,
                                    lineterminator="\n", restval="")
            writer.writeheader()
            writer.writerows(report)
        with open(summary_path, "w") as dest:
            json.dump(summary, dest, indent=1)
            dest.write("\n")
        os.replace(tmp, LEDGER)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    print(f"applied: {len(corrected)} rows corrected in {RELPATH}")
    print(f"as-recorded copy: {snapshot}")
    print(f"itemised report:  {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
