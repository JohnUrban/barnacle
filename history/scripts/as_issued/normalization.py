"""Observation normalization manifest (audit 2026-09-24-a4 R3; protocol
Amendment 2, POST-REVIEW and POST-SCORING).

Every eligible ledger row gets an auditable entry keyed by its row number and
the SHA-256 of its CSV line: level as POINT (with a tolerance interval when the
source states one), INTERVAL, UPPER or LOWER bound; optional time window;
method (tape / photo-bound / photo / live report / second observer); primary
or sensitivity-only use; supersession; and any unresolved numeric/text
conflict. Defaults come from the Amendment-1 wording rules plus each event
record's stated method; OVERRIDES below change a row only with a quoted source
(the row's own wording or the event record). The append-only ledger is never
edited. Run: python3 history/scripts/as_issued/normalization.py (writes
history/data/as_issued/observation_normalization.json).
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from as_issued import obs as O  # noqa: E402

ROOT = O.ROOT
OUT = os.path.join(ROOT, "history", "data", "as_issued", "observation_normalization.json")
TAPE_TOL_IN = 0.5    # assets/observations/2026-07-13/README.md: "within tape precision" (+-0.5 in)
GRATE = 3.52         # SW grate, the "+X in vs SW grate" reference

# Event-level measurement method, from each event record (assets/observations/<date>/README.md).
EVENT_METHOD = {
    "2026-07-09": ("tape", "README: 'Street peak (tape, lawn-step wall + porch-step wall agree)'; 21 timed measurements"),
    "2026-07-13": ("tape", "README: 'measured across four grates'; 'within tape precision' (+-0.5 in)"),
    "2026-07-18": ("tape", "README: '+19.9 in measured (tape)'; live-dictated timestamps"),
    "2026-08-03": ("live report", "README: timeline from dictation; peak bracketed by lawn-step/porch-base"),
    "2026-08-07": ("live report", "README: photo-timed rise and a receding tape point; other rows are live reports"),
    "2026-08-10": ("photo bound", "README: 'photo-verified, no tape ... landmark presence/absence bounds the water level'"),
    "2026-08-11": ("photo bound", "README: 'photo-verified, no tape'"),
    "2026-08-12": ("photo bound", "README: 'photo-verified, no tape'"),
    "2026-08-13": ("photo bound", "README: 'photo-verified, no tape'"),
    "2026-09-01": ("photo", "README: 'Nineteen EXIF-timed photos'"),
    "2026-09-13": ("photo", "README: '18-photo EXIF timeline'"),
}


def _in(x):
    return GRATE + x / 12.0


# row -> changes + reason (+ quote). Levels NAVD88 ft; times station local.
OVERRIDES = {
    116: {"level_type": "UPPER", "reason": "wording 'water at/below porch step base'"},
    125: {"level_type": "LOWER", "reason": "wording 'WATER OVER NE+NW GRATES'"},
    126: {"level_type": "LOWER", "lo": 3.80, "reason": "wording 'over ALL FIVE grates (water >= 3.80)'"},
    131: {"level_type": "LOWER", "reason": "wording 'CROWN COVERED'"},
    151: {"level_type": "LOWER", "method": "live report", "reason": "wording 'water over the sidewalk'"},
    152: {"level_type": "INTERVAL", "lo": 4.66, "hi": 4.68, "method": "live report",
          "reason": "wording 'level with or just over the lawn step'; upper = porch-step base, which the later PEAK row 153 says was not reached"},
    153: {"level_type": "INTERVAL", "lo": 4.66, "hi": 4.68, "point": 4.67, "time_window": ["2026-08-03T10:31", "2026-08-03T10:36"],
          "method": "live report",
          "conflict": "numeric depth -0.5 at porch_step_base gives 4.638, below the lawn step (4.66); the same row's wording says 'a little above lawn step, not quite to porch-step bottom ... brackets peak ~4.67'. The wording bracket is used; the conflict is unresolved in the source.",
          "reason": "row states a bracket and a time window 10:31-10:36"},
    155: {"level_type": "INTERVAL", "lo": 4.40, "hi": 4.48, "reason": "wording 'water ~4.40-4.48 NAVD88'"},
    159: {"primary": False, "superseded_by": 166, "time_window": ["2026-08-07T18:30", "2026-08-07T18:34"],
          "method": "live report", "reason": "row 166 'Refines the live 18:32 row (18:30-18:34 est)'; 'user has photos' is a pending reference, not a verified photo"},
    160: {"method": "live report (time photo-confirmed by row 166: porch base 18:37:00, photos 10-11)",
          "reason": "live report; row 166 confirms the time"},
    161: {"method": "tape", "tol_in": TAPE_TOL_IN, "reason": "README: 'a receding tape point (+14.9 at 18:43)'"},
    164: {"level_type": "UPPER", "hi": 4.33,
          "conflict": "numeric depth -0.5 gives 4.288; wording says only 'water < +9.7 there' (the lawn-step spot) with water over the rest of the sidewalk. The wording bound is used.",
          "reason": "wording 'sidewalk AT the lawn step EXPOSED (water < +9.7 there)'"},
    165: {"primary": False, "method": "second observer", "reason": "wording 'john 50-60% confident in the LEVEL': sensitivity only"},
    166: {"method": "photo", "time_exact": "2026-08-07T18:33:16", "reason": "wording 'PHOTO-VERIFIED refinement: lawn step level at 18:33:16 EXACT (EXIF, photo 7)'"},
    167: {"level_type": "LOWER", "lo": 3.91, "point": 3.91, "method": "photo bound",
          "reason": "wording 'SE-SW corners (3.64 submerged), just APPEARING at NE+NW corners (3.91)'; no dry landmark stated"},
    168: {"level_type": "INTERVAL", "lo": 3.64, "hi": 3.90, "method": "photo bound",
          "reason": "wording 'bounds water 3.64-3.9'; README 'no tape'"},
    169: {"level_type": "LOWER", "lo": 3.91, "method": "photo bound",
          "reason": "wording 'NE+NW corners wet (3.91+)'; the note's 'topped ~2 in below curb top' is the gauge, not the photo"},
    170: {"level_type": "LOWER", "lo": 3.91, "method": "photo bound", "reason": "wording 'NE corner wet'; no dry landmark stated"},
    171: {"level_type": "LOWER", "lo": 3.64, "method": "photo",
          "reason": "wording 'SE-SW central section completely covered'; the 1-in figure is not stated as measured"},
    172: {"level_type": "LOWER", "lo": 4.16, "point": 4.168, "method": "photo", "reason": "wording 'water over the curb'"},
    173: {"level_type": "INTERVAL", "lo": round(_in(13.7), 4), "hi": round(_in(14.2), 4), "point": round(_in(13.9), 4),
          "time_window": ["2026-09-01T19:23", "2026-09-01T19:27"], "method": "photo",
          "reason": "wording 'PEAK ~+13.7 to +14.2 in vs SW grate, window ~19:23-19:27'; notes 'PEAK ~= +13.9 (bracket 13.7-14.2)'"},
    178: {"primary": False, "superseded_by": 181, "method": "live report",
          "reason": "wording 'exact shot not captured; time +-10 min pending photo EXIF'; row 181 'Refines the 07:10 +/-10min [STATED] row'"},
    181: {"method": "photo", "time_window": ["2026-09-13T07:01:23", "2026-09-13T07:04:21"],
          "reason": "wording 'PEAK REFINED [VERIFIED photo 14 EXIF]: water level with lawn-step top; held through 07:04:21 (photo 18)'"},
    183: {"eligible": True, "level_type": "INTERVAL", "lo": round(_in(7.2), 4), "hi": round(_in(7.5), 4), "method": "live report",
          "reason": "wording 'water almost to curb top => ~+7.2-7.5 vs grate' (a stated bracket; previously excluded as blank depth)"},
}

# Event peaks as established by the primary records (not the sampled maximum).
EVENT_PEAKS = {
    "2026-07-09": {"lo": 5.08 - TAPE_TOL_IN / 12, "hi": 5.08 + TAPE_TOL_IN / 12, "basis": "tape peak 5.08 @15:56 (README), +-0.5 in"},
    "2026-07-13": {"lo": 3.73, "hi": 3.81, "basis": "README 'Cross-grate spread at peak (3.73-3.81)'"},
    "2026-07-18": {"lo": 5.18 - TAPE_TOL_IN / 12, "hi": 5.18 + TAPE_TOL_IN / 12, "basis": "ledger PEAK '6.0 in up riser = 5.18 NAVD88', tape +-0.5 in"},
    "2026-08-03": {"lo": 4.66, "hi": 4.68, "basis": "README 'PEAK ~= +13.8 in (lawn-step/porch-base bracket)'"},
    "2026-08-07": {"lo": _in(14.9), "hi": None, "basis": "ledger 161 'user missed the peak - peak >= +14.9'; backcast ~+15.4 is [INFERRED], not used"},
    "2026-09-01": {"lo": _in(13.7), "hi": _in(14.2), "basis": "README 'Peak ~= +13.9 in vs SW grate (bracket +13.7-14.2)'"},
    "2026-09-13": {"lo": 4.66, "hi": 4.66, "basis": "photo-verified 'level with lawn-step top' 07:01:23-07:04:21 (tolerance unstated)"},
}


def row_hashes(path=O.LEDGER):
    with open(path, "rb") as f:
        text = f.read().decode("utf-8")
    lines = text.splitlines(keepends=False)
    rows = list(csv.reader(io.StringIO(text)))
    # physical-line hashing fails on quoted newlines; hash the parsed record instead
    return {i: hashlib.sha256(json.dumps(r, ensure_ascii=False).encode()).hexdigest()
            for i, r in enumerate(rows[1:], 2)}, hashlib.sha256(text.encode()).hexdigest(), len(lines)


def _local(s):
    return O.local_to_utc(s).strftime("%Y-%m-%dT%H:%M:%SZ")


def build(path=O.LEDGER):
    rows, ledger_sha = O.load(path)
    hashes, _sha, _n = row_hashes(path)
    entries = {}
    for o in rows:
        r = o["row"]
        ov = OVERRIDES.get(r, {})
        eligible = o["eligible"] or ov.get("eligible", False)
        if not eligible:
            continue
        day = o["time_utc"].astimezone(O.NY).strftime("%Y-%m-%d") if o["time_utc"] else None
        method, method_src = EVENT_METHOD.get(day, ("observer estimate", "no event record method"))
        e = {"row": r, "row_sha256": hashes[r], "landmark": o["landmark"], "elevation": o["elevation"],
             "time_utc": o["time_utc"].strftime("%Y-%m-%dT%H:%M:%SZ"), "level_type": o["level_type"],
             "point": o["level_navd88"], "lo": None, "hi": None, "method": method, "method_source": method_src,
             "primary": True, "superseded_by": None, "conflict": None, "reason": "Amendment-1 wording rule",
             "dry": o["dry"]}
        if e["level_type"] == "UPPER":
            e["hi"], e["point"] = o["elevation"], None
        elif e["level_type"] == "LOWER":
            e["lo"], e["point"] = o["elevation"], None
        for k in ("level_type", "lo", "hi", "point", "method", "primary", "superseded_by", "conflict", "reason"):
            if k in ov:
                e[k] = ov[k]
        if ov.get("level_type") == "UPPER" and "hi" not in ov:
            e["hi"], e["point"] = o["elevation"], None
        if ov.get("level_type") == "LOWER" and "lo" not in ov:
            e["lo"] = o["elevation"]
        if ov.get("level_type") in ("UPPER", "LOWER") and "point" not in ov:
            e["point"] = None
        if e["level_type"] == "POINT" and e["method"] == "tape" or ov.get("tol_in"):
            tol = ov.get("tol_in", TAPE_TOL_IN) / 12.0
            e["lo"], e["hi"], e["tolerance"] = e["point"] - tol, e["point"] + tol, "tape +-0.5 in (2026-07-13 README)"
        if ov.get("time_exact"):
            e["time_utc"] = _local(ov["time_exact"])
        if ov.get("time_window"):
            e["time_window_utc"] = [_local(x) for x in ov["time_window"]]
        if o["landmark"] == "curb" and r == 183 and o["elevation"] is None:
            e["elevation"] = 4.16
        if e["level_type"] == "INTERVAL" and "point" not in ov:
            e["point"] = None                      # a ledger depth is not a measurement inside a stated bracket
        if e["level_type"] == "INTERVAL" and e["point"] is None:
            e["point"] = round((e["lo"] + e["hi"]) / 2, 4)
            e["point_is_midpoint"] = True
        entries[r] = e
    return {"ledger_sha256": ledger_sha, "tape_tolerance_in": TAPE_TOL_IN, "event_peaks": EVENT_PEAKS,
            "entries": [entries[k] for k in sorted(entries)],
            "note": "Amendment 2 (post-review, post-scoring): normalization of ledger rows; the ledger is unchanged"}


if __name__ == "__main__":
    m = build()
    with open(OUT, "w") as f:
        json.dump(m, f, indent=1, sort_keys=True)
        f.write("\n")
    from collections import Counter
    print(len(m["entries"]), Counter(e["level_type"] for e in m["entries"]), Counter(e["method"] for e in m["entries"]),
          "non-primary", [e["row"] for e in m["entries"] if not e["primary"]])
