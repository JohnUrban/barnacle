#!/usr/bin/env python3
"""Append one landmark-derived water-level BOUND for an existing ledger row.

Owner rule 2026-09-27 (BACKLOG PREF observations-are-quantitative): a report
that relates water to landmarks of known height is quantitative. This tool
records the band an agent computed from the survey — never from prose
parsing — as an append-only JSON line in data/observation_bounds.jsonl,
keyed by the ledger row's content hash (the registry's identity). Production
(`_today_lookback`) and the analysis sidecar read this file; the ledger row
itself is never edited.

    python3 bin/append_observation_bound.py --csv-row 231 \\
        --lo 4.14 --hi 4.16 --basis stated_landmarks \\
        --landmark "upstream_grate_sidewalk:4.14:over:assets/map_points.csv (approximated)" \\
        --landmark "curb:4.16:not over:model/elevations.md" \\
        --text "over the upstream-grate sidewalk (4.14); not over the walkway curb (4.16)"

Either bound may be omitted (one-sided). `--basis` is stated_landmarks (the
owner named the landmarks) or stated (the owner gave the number). Ask the
owner when a band cannot be computed; do not invent widths.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "data", "labeled_observations.csv")
BOUNDS = os.path.join(ROOT, "data", "observation_bounds.jsonl")
BASES = ("stated_landmarks", "stated")
REQUIRED = ("sha256", "csv_row", "observation_time_local", "landmark_key",
            "lo_navd88", "hi_navd88", "basis", "landmarks", "text",
            "recorded_utc", "recorded_by")


def row_hash(row):
    return hashlib.sha256(json.dumps(dict(row), sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def validate_record(rec, ledger_hashes=None):
    """Return a list of problems (empty = valid)."""
    bad = [f"missing {k}" for k in REQUIRED if k not in rec]
    if bad:
        return bad
    lo, hi = rec["lo_navd88"], rec["hi_navd88"]
    if lo is None and hi is None:
        bad.append("at least one of lo_navd88/hi_navd88 is required")
    for name, v in (("lo_navd88", lo), ("hi_navd88", hi)):
        if v is not None and not isinstance(v, (int, float)):
            bad.append(f"{name} must be a number or null")
    if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and lo > hi:
        bad.append("lo_navd88 exceeds hi_navd88")
    if rec["basis"] not in BASES:
        bad.append(f"basis must be one of {BASES}")
    if not isinstance(rec["landmarks"], list) or not rec["landmarks"]:
        bad.append("landmarks must be a non-empty list")
    else:
        for lm in rec["landmarks"]:
            for k in ("key", "navd88", "relation", "source"):
                if k not in lm:
                    bad.append(f"landmark entry missing {k}")
    if ledger_hashes is not None and rec["sha256"] not in ledger_hashes:
        bad.append("sha256 does not match any ledger row")
    return bad


def load_bounds(path=BOUNDS):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def append_bound(csv_row, lo, hi, basis, landmarks, text, recorded_by,
                 ledger_path=LEDGER, bounds_path=BOUNDS, owner_confirmed=False):
    with open(ledger_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not 2 <= csv_row <= len(rows) + 1:
        raise ValueError(f"csv_row {csv_row} outside the ledger")
    row = rows[csv_row - 2]
    rec = {
        "sha256": row_hash(row), "csv_row": csv_row,
        "observation_time_local": row["observation_time_local"],
        "landmark_key": row["landmark_key"],
        "lo_navd88": lo, "hi_navd88": hi, "basis": basis,
        "landmarks": landmarks, "text": text,
        "recorded_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "recorded_by": recorded_by, "owner_confirmed": bool(owner_confirmed),
    }
    problems = validate_record(rec)
    if problems:
        raise ValueError("; ".join(problems))
    encoded = (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8")
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
    return {"key": parts[0], "navd88": float(parts[1]), "relation": parts[2], "source": parts[3]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--csv-row", type=int, required=True)
    ap.add_argument("--lo", type=float, default=None)
    ap.add_argument("--hi", type=float, default=None)
    ap.add_argument("--basis", choices=BASES, default="stated_landmarks")
    ap.add_argument("--landmark", action="append", type=_parse_landmark, required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--recorded-by", default="agent")
    ap.add_argument("--owner-confirmed", action="store_true")
    ap.add_argument("--ledger", default=LEDGER)
    ap.add_argument("--path", default=BOUNDS)
    a = ap.parse_args()
    rec = append_bound(a.csv_row, a.lo, a.hi, a.basis, a.landmark, a.text, a.recorded_by,
                       ledger_path=a.ledger, bounds_path=a.path, owner_confirmed=a.owner_confirmed)
    print(f"appended bound for row {a.csv_row} ({rec['observation_time_local']}): "
          f"[{a.lo}, {a.hi}] ft NAVD88")


if __name__ == "__main__":
    main()
