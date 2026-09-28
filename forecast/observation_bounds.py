"""Landmark-relation bounds: ONE validation contract shared by the writer
(bin/append_observation_bound.py), the publish gate (check_artifacts.py) and
the reader (flood_forecast_daily._today_lookback, the analysis sidecar).

Owner rule 2026-09-27 22:44 (BACKLOG PREF observations-are-quantitative): a
report that relates water to landmarks of known height is quantitative. An
agent computes the band from the survey and records it here; prose is never
parsed for numbers. Records are append-only JSON lines in
data/observation_bounds.jsonl keyed by the ledger row's content hash; a
correction is a NEW line (the last valid line per row wins).

Audit 2026-09-27-a1 round 16 R2/R3: every record carries explicit time
metadata (``time_kind``, optional ``time_window_local``) and a spatial
``scope`` so that coverage decisions never rely on prose heuristics, and
every consumer validates the same way: finite numeric-or-null bounds
(booleans excluded), ordering, well-formed landmark provenance with finite
elevations, identity consistency with the ledger row, strict serialization
(``allow_nan=False``) so an invalid write leaves the file unchanged, and
explicit diagnostics for malformed lines instead of silent drops.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os

try:
    from .station_time import parse_station_local_time
except ImportError:  # script mode
    from station_time import parse_station_local_time

REQUIRED = ("sha256", "csv_row", "observation_time_local", "landmark_key",
            "lo_navd88", "hi_navd88", "basis", "landmarks", "text",
            "recorded_utc", "recorded_by")
DEFAULTS = {"time_kind": "stated_exact", "time_window_local": None,
            "scope": "intersection", "owner_confirmed": False,
            "supersedes_scalar": False, "disputed": False}
BASES = ("stated_landmarks", "stated")
TIME_KINDS = ("stated_exact", "approximate", "window", "surrogate")
SCOPES = ("intersection", "local")
LANDMARK_KEYS = ("key", "navd88", "relation", "source")


def row_hash(row) -> str:
    """Content identity of a ledger row (registry recipe)."""
    return hashlib.sha256(json.dumps(dict(row), sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def _finite_or_null(v) -> bool:
    if v is None:
        return True
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _nonempty_str(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def with_defaults(rec: dict) -> dict:
    out = dict(DEFAULTS)
    out.update(rec)
    return out


def validate_record(rec, ledger_rows=None, locator="strict") -> list:
    """Problems with one record (empty list = valid). When ``ledger_rows``
    (the parsed ledger, in order) is given, the sha256 must identify a row
    and the copied identity fields (observation time, landmark) must match
    that row. ``locator="strict"`` (the publish gate) additionally requires
    ``csv_row`` to be that row's position; ``locator="hash"`` (readers)
    locates the row by content hash and treats ``csv_row`` as a hint, the
    registry's rule that the CSV line number is a locator, not identity."""
    if not isinstance(rec, dict):
        return ["record is not a JSON object"]
    bad = [f"missing {k}" for k in REQUIRED if k not in rec]
    if bad:
        return bad
    lo, hi = rec["lo_navd88"], rec["hi_navd88"]
    for name, v in (("lo_navd88", lo), ("hi_navd88", hi)):
        if not _finite_or_null(v):
            bad.append(f"{name} must be a finite number or null (got {v!r})")
    if lo is None and hi is None:
        bad.append("at least one of lo_navd88/hi_navd88 is required")
    if _finite_or_null(lo) and _finite_or_null(hi) and lo is not None and hi is not None and lo > hi:
        bad.append("lo_navd88 exceeds hi_navd88")
    if rec["basis"] not in BASES:
        bad.append(f"basis must be one of {BASES}")
    tk = rec.get("time_kind", DEFAULTS["time_kind"])
    if tk not in TIME_KINDS:
        bad.append(f"time_kind must be one of {TIME_KINDS}")
    win = rec.get("time_window_local", None)
    if win is not None:
        if not (isinstance(win, list) and len(win) == 2 and all(isinstance(x, str) for x in win)):
            bad.append("time_window_local must be null or [start, end] strings")
        else:
            try:
                a, b = (parse_station_local_time(x) for x in win)
                if a > b:
                    bad.append("time_window_local start is after its end")
            except (TypeError, ValueError) as e:
                bad.append(f"time_window_local unparseable: {e}")
    if tk in ("window", "surrogate", "approximate") and win is None and tk == "window":
        bad.append("time_kind window requires time_window_local")
    if rec.get("scope", DEFAULTS["scope"]) not in SCOPES:
        bad.append(f"scope must be one of {SCOPES}")
    for flag in ("owner_confirmed", "supersedes_scalar", "disputed"):
        if flag in rec and not isinstance(rec[flag], bool):
            bad.append(f"{flag} must be a boolean")
    lms = rec["landmarks"]
    if not isinstance(lms, list) or not lms:
        bad.append("landmarks must be a non-empty list")
    else:
        for i, lm in enumerate(lms):
            if not isinstance(lm, dict):
                bad.append(f"landmark {i} is not an object")
                continue
            for k in LANDMARK_KEYS:
                if k not in lm:
                    bad.append(f"landmark {i} missing {k}")
            if "navd88" in lm and not (_finite_or_null(lm["navd88"]) and lm["navd88"] is not None):
                bad.append(f"landmark {i} navd88 must be a finite number")
            for k in ("key", "relation", "source"):
                if k in lm and not _nonempty_str(lm[k]):
                    bad.append(f"landmark {i} {k} must be a non-empty string")
    if not _nonempty_str(rec["text"]):
        bad.append("text must be a non-empty string")
    for k in ("sha256", "observation_time_local", "landmark_key", "recorded_utc", "recorded_by"):
        if not _nonempty_str(rec[k]):
            bad.append(f"{k} must be a non-empty string")
    if not isinstance(rec["csv_row"], int) or isinstance(rec["csv_row"], bool) or rec["csv_row"] < 2:
        bad.append("csv_row must be an integer >= 2")
    if ledger_rows is not None and not bad:
        n = rec["csv_row"]
        row = None
        if locator == "strict":
            if n - 2 >= len(ledger_rows):
                bad.append(f"csv_row {n} is beyond the ledger")
            else:
                row = ledger_rows[n - 2]
                if row_hash(row) != rec["sha256"]:
                    bad.append(f"sha256 does not match ledger row {n}")
                    row = None
        else:
            hashes = getattr(ledger_rows, "_barnacle_hash_index", None)
            if hashes is None:
                hashes = {row_hash(r): r for r in ledger_rows}
                try:
                    ledger_rows._barnacle_hash_index = hashes
                except AttributeError:
                    pass
            row = hashes.get(rec["sha256"])
            if row is None:
                bad.append("sha256 matches no ledger row")
        if row is not None:
            if row.get("observation_time_local") != rec["observation_time_local"]:
                bad.append("observation_time_local does not match the ledger row")
            if row.get("landmark_key") != rec["landmark_key"]:
                bad.append("landmark_key does not match the ledger row")
    return bad


def serialize(rec) -> str:
    """Strict one-line JSON; raises ValueError on NaN/Infinity so nothing is
    written when a record is invalid."""
    return json.dumps(rec, ensure_ascii=False, allow_nan=False) + "\n"


def _reject_constant(name):
    raise ValueError(f"non-finite JSON constant {name}")


def parse_line(line):
    """(record, None) or (None, problem)."""
    try:
        rec = json.loads(line, parse_constant=_reject_constant)
    except ValueError as e:
        return None, f"not strict JSON ({e})"
    if not isinstance(rec, dict):
        return None, "line is not a JSON object"
    return rec, None


class _Rows(list):
    """list subclass so a hash index can be cached on it."""


def load_ledger_rows(ledger_path):
    with open(ledger_path, newline="", encoding="utf-8") as f:
        return _Rows(csv.DictReader(f))


def load_bounds(path, ledger_rows=None, locator="strict"):
    """(by_sha256, problems). Later valid lines win for the same row; every
    malformed or invalid line is reported, never silently dropped."""
    by_hash, problems = {}, []
    if not os.path.exists(path):
        return by_hash, problems
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            rec, why = parse_line(line)
            if rec is None:
                problems.append(f"line {n}: {why}")
                continue
            bad = validate_record(rec, ledger_rows, locator)
            if bad:
                problems.append(f"line {n}: " + "; ".join(bad))
                continue
            by_hash[rec["sha256"]] = with_defaults(rec)
    return by_hash, problems
