#!/usr/bin/env python3
"""Append one landmark-derived water-level BOUND for an existing ledger row.

Owner rule 2026-09-27 (BACKLOG PREF observations-are-quantitative): a report
that relates water to landmarks of known height is quantitative. This tool
records the band an agent computed from the survey — never from prose
parsing — as an append-only JSON line in data/observation_bounds.jsonl,
keyed by the ledger row's content hash (the registry's identity). Production
(`_today_lookback`) and the analysis sidecar read this file; the ledger row
itself is never edited. Validation is the shared contract in
forecast/observation_bounds.py (round 16 R3); an invalid record is never
written.

    python3 bin/append_observation_bound.py --csv-row 231 \\
        --lo 4.14 --hi 4.16 --basis stated_landmarks \\
        --landmark "upstream_grate_sidewalk:4.14:over:assets/map_points.csv (approximated)" \\
        --landmark "curb:4.16:not over:model/elevations.md" \\
        --text "over the upstream-grate sidewalk (4.14); not over the walkway curb (4.16)" \\
        [--time-kind stated_exact|approximate|window|surrogate] \\
        [--time-window "2026-09-26T21:20:00-04:00" "2026-09-26T21:40:00-04:00"] \\
        [--scope intersection|local] [--supersedes-scalar] [--disputed] [--owner-confirmed]

Either bound may be omitted (one-sided). ``--time-kind`` records the
OBSERVATION time's certainty as the source states it (round 16 R2): only
stated_exact bands can cover a model claim. ``--scope local`` marks a band
for a local pool (e.g. around one grate), never a whole-intersection level.
``--supersedes-scalar`` says the band replaces a legacy range-representative
number in the ledger row's depth field (round 16 C1). ``--disputed`` keeps a
band out of claim coverage while a survey point is in question (C2).
Ask the owner when a band cannot be computed; do not invent widths.
"""
import argparse
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from forecast import observation_bounds as ob  # noqa: E402

LEDGER = os.path.join(ROOT, "data", "labeled_observations.csv")
BOUNDS = os.path.join(ROOT, "data", "observation_bounds.jsonl")


def append_bound(csv_row, lo, hi, basis, landmarks, text, recorded_by,
                 ledger_path=LEDGER, bounds_path=BOUNDS, owner_confirmed=False,
                 time_kind="stated_exact", time_window=None, scope="intersection",
                 supersedes_scalar=False, disputed=False):
    rows = ob.load_ledger_rows(ledger_path)
    if not 2 <= csv_row <= len(rows) + 1:
        raise ValueError(f"csv_row {csv_row} outside the ledger")
    row = rows[csv_row - 2]
    rec = {
        "sha256": ob.row_hash(row), "csv_row": csv_row,
        "observation_time_local": row["observation_time_local"],
        "landmark_key": row["landmark_key"],
        "lo_navd88": lo, "hi_navd88": hi, "basis": basis,
        "time_kind": time_kind, "time_window_local": list(time_window) if time_window else None,
        "scope": scope, "landmarks": landmarks, "text": text,
        "recorded_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "recorded_by": recorded_by, "owner_confirmed": bool(owner_confirmed),
        "supersedes_scalar": bool(supersedes_scalar), "disputed": bool(disputed),
    }
    problems = ob.validate_record(rec, rows)
    if problems:
        raise ValueError("; ".join(problems))
    # round 18 R1: metadata is authoritative for readers, so warn loudly when
    # the row's own wording says the time is uncertain and the record does not
    try:
        from forecast.flood_forecast_daily import _lookback_time_uncertain
        if time_kind == "stated_exact" and _lookback_time_uncertain(row.get("observed_qualitative", "")):
            print("WARNING: the row's wording suggests an uncertain time but time_kind is "
                  "stated_exact — confirm, or re-append with --time-kind", file=sys.stderr)
    except Exception:
        pass
    encoded = ob.serialize(rec).encode("utf-8")   # raises before any write on NaN/inf
    fd = os.open(bounds_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)
    return rec


def _parse_landmark(spec):
    parts = spec.split(":", 3)
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("landmark must be key:navd88:relation:source")
    try:
        navd = float(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError("landmark navd88 must be a number")
    return {"key": parts[0], "navd88": navd, "relation": parts[2], "source": parts[3]}


def _finite(text):
    v = float(text)
    if v != v or v in (float("inf"), float("-inf")):
        raise argparse.ArgumentTypeError("bounds must be finite numbers")
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--csv-row", type=int, required=True)
    ap.add_argument("--lo", type=_finite, default=None)
    ap.add_argument("--hi", type=_finite, default=None)
    ap.add_argument("--basis", choices=ob.BASES, default="stated_landmarks")
    ap.add_argument("--landmark", action="append", type=_parse_landmark, required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--time-kind", choices=ob.TIME_KINDS, default="stated_exact")
    ap.add_argument("--time-window", nargs=2, default=None, metavar=("START", "END"))
    ap.add_argument("--scope", choices=ob.SCOPES, default="intersection")
    ap.add_argument("--supersedes-scalar", action="store_true")
    ap.add_argument("--disputed", action="store_true")
    ap.add_argument("--recorded-by", default="agent")
    ap.add_argument("--owner-confirmed", action="store_true")
    ap.add_argument("--ledger", default=LEDGER)
    ap.add_argument("--path", default=BOUNDS)
    a = ap.parse_args()
    rec = append_bound(a.csv_row, a.lo, a.hi, a.basis, a.landmark, a.text, a.recorded_by,
                       ledger_path=a.ledger, bounds_path=a.path, owner_confirmed=a.owner_confirmed,
                       time_kind=a.time_kind, time_window=a.time_window, scope=a.scope,
                       supersedes_scalar=a.supersedes_scalar, disputed=a.disputed)
    print(f"appended bound for row {a.csv_row} ({rec['observation_time_local']}): "
          f"[{a.lo}, {a.hi}] ft NAVD88, time {a.time_kind}, scope {a.scope}")


if __name__ == "__main__":
    main()
