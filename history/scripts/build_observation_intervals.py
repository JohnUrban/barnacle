#!/usr/bin/env python3
"""Additive interval/provenance records for the 2026-09-25..27 ledger rows
(audit 2026-09-27-a1 R6). The append-only ledger keeps its scalar
midpoints and surrogate times untouched; this sidecar says, per row (by
content hash, the registry's identity), what kind of time and depth the
scalar really is, so downstream classification/scoring can preserve
intervals instead of treating midpoints as exact measurements.

Defaults: every registered row of the four episodes is an exact stated
observation time with a point depth. OVERRIDES below come from the owner's
original notes (rawnotes/) and the line-level reconciliation
(2026-09-27/analysis/rawnotes-reconciliation.json). Depths are inches
relative to the row's landmark; times are offset-bearing station-local.

Writes assets/observations/2026-09-27/analysis/observation_intervals.json
and verifies every referenced row hash against the ledger.
Run: python3 history/scripts/build_observation_intervals.py
"""
import csv
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from forecast.station_time import parse_station_local_time  # noqa: E402

REGISTRY = ROOT / "assets/observations/episodes.json"
LEDGER = ROOT / "data/labeled_observations.csv"
OUT = ROOT / "assets/observations/2026-09-27/analysis/observation_intervals.json"
EPISODES = ["2026-09-25-e01", "2026-09-26-e01", "2026-09-26-e02", "2026-09-27-e01"]

# csv_row -> override fields (see module docstring for sources)
OVERRIDES = {
    191: {"time_kind": "surrogate", "time_window_local": ["2026-09-25T19:30:00-04:00", "2026-09-25T21:30:00-04:00"],
          "time_note": "Negative check; ledger uses the gauge-peak minute as a surrogate. Owner home 20:00-20:30, spouse home all evening; exact observation time unconfirmed.",
          "depth_kind": "upper_bound", "depth_hi_in": 0.0, "depth_note": "No flooding at the intersection (bound: water below the SW grate)."},
    187: {"time_kind": "approximate", "time_window_local": ["2026-09-26T06:45:00-04:00", "2026-09-26T07:15:00-04:00"],
          "time_note": "Original: 'Around 7'. Water already present earlier ('underway for a while')."},
    188: {"depth_kind": "lower_bound", "depth_lo_in": 0.0, "depth_note": "Over the curb, near top of lawn step (qualitative)."},
    190: {"depth_kind": "range", "depth_lo_in": 0.0, "depth_hi_in": 0.24, "depth_note": "Over the lawn step (4.66) but not to the porch-step base (4.68): 0-0.24 in above the lawn step."},
    222: {"depth_kind": "upper_bound", "depth_hi_in": 0.0, "depth_note": "'Roads virtually clear; intersection clear; safe to drive': water below the intersection high point (4.54)."},
    241: {"depth_kind": "lower_bound", "depth_lo_in": 0.0, "depth_note": "Bay Ave crossed at the upstream grate (water at or above it)."},
    251: {"depth_kind": "lower_bound", "depth_lo_in": 0.0, "depth_note": "Breached over the first porch step top; water entering garage (level not measured)."},
    194: {"depth_kind": "range", "depth_lo_in": 1.4, "depth_hi_in": 1.5, "depth_note": "Original 1.4-1.5 in; ledger 1.45 is the midpoint."},
    219: {"time_note": "Original file said '12:06 am'; midday confirmed by owner 2026-09-27 (rawnotes/clarifications.txt)."},
    221: {"depth_kind": "range", "depth_lo_in": -0.5, "depth_hi_in": -0.3, "depth_note": "'about 1 cm under the curb': -0.39 in nominal; ledger -0.4."},
    230: {"time_kind": "window", "time_window_local": ["2026-09-26T21:20:00-04:00", "2026-09-26T21:40:00-04:00"],
          "time_note": "First water reported 'sometime between 9:20-9:40'; ledger 21:30 is the midpoint, not onset.",
          "depth_kind": "lower_bound", "depth_lo_in": 0.0, "depth_note": "Water spans SE-SW grates across Central (above SW grate)."},
    231: {"depth_kind": "range", "depth_lo_in": -0.39, "depth_hi_in": 0.0, "depth_note": "'less than 1 cm below the curb'; ledger -0.3."},
    232: {"time_kind": "surrogate", "time_window_local": ["2026-09-26T21:54:00-04:00", "2026-09-26T22:11:00-04:00"],
          "time_note": "Gate visit untimed in the original; ledger 21:58 assigned from surrounding entries.",
          "depth_kind": "not_applicable", "depth_note": "Infrastructure state report ('almost certainly closed'), not a water level."},
    233: {"depth_kind": "range", "depth_lo_in": 0.5, "depth_hi_in": 1.0, "depth_note": "Original 0.5-1 in over curb; ledger 0.75 midpoint. Companion phrase 'base of lawn step and a little up it' implies a different level under the survey; not reconciled."},
    234: {"depth_kind": "range", "depth_lo_in": 0.5, "depth_hi_in": 1.0, "depth_note": "'same as 10:11'; range as row 233."},
    235: {"depth_kind": "approximate", "depth_note": "'more like 0.5 inch, not 1', receding."},
    236: {"time_kind": "upper_bound", "time_window_local": ["2026-09-26T22:39:00-04:00", "2026-09-26T23:12:00-04:00"],
          "time_note": "Receded 'completely as far as I can tell'; clearing time unknown between 22:39 and 23:12.",
          "depth_kind": "upper_bound", "depth_hi_in": 0.0},
    237: {"time_kind": "already_present", "time_note": "Water already present at 07:48; not flood onset.",
          "depth_kind": "lower_bound", "depth_lo_in": 0.0, "depth_note": "Minor water SE-SW across Central; ~1 in over NE/NW grates."},
    238: {"depth_kind": "range", "depth_lo_in": -1.0, "depth_hi_in": 0.0, "depth_note": "'nearly to curb level at lawn step' (qualitative)."},
    240: {"depth_kind": "approximate", "depth_note": "'6 inches over NE grate; around 5.5 inches above street at curb' (two co-reports)."},
    255: {"depth_kind": "approximate", "depth_note": "'may have stopped rising'."},
    256: {"depth_kind": "upper_bound", "depth_hi_in": 11.25, "depth_note": "'11.25 or just slightly lower'."},
    257: {"depth_kind": "upper_bound", "depth_hi_in": 11.0, "depth_note": "'11 or slightly lower'."},
    258: {"depth_kind": "upper_bound", "depth_hi_in": 9.5, "depth_note": "'9.5 or slightly lower'."},
    259: {"time_kind": "surrogate", "time_window_local": ["2026-09-27T08:24:00-04:00", "2026-09-27T08:36:00-04:00"],
          "time_note": "Gate visit untimed in the original; ledger 08:30 assigned between the 08:24 and 08:36 entries.",
          "depth_kind": "not_applicable", "depth_note": "Infrastructure state ('almost certainly closed'), not visual confirmation."},
    263: {"depth_kind": "range", "depth_lo_in": 0.5, "depth_hi_in": 1.0, "depth_note": "'at most an inch above the curb, probably 0.5-1'; ledger 0.75 midpoint."},
}


def row_hash(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def main():
    reg = json.loads(REGISTRY.read_text())
    with LEDGER.open(newline="") as f:
        rows = list(csv.DictReader(f))
    records, seen = [], set()
    for ep in reg["episodes"]:
        if ep["episode_id"] not in EPISODES:
            continue
        for ref in ep["ledger_rows"]:
            n = ref["csv_row"]
            row = rows[n - 2]
            assert row_hash(row) == ref["sha256"], f"row {n} changed"
            t = parse_station_local_time(row["observation_time_local"])
            depth = row["observed_depth_in"].strip()
            rec = {
                "csv_row": n, "sha256": ref["sha256"], "episode_id": ep["episode_id"],
                "landmark_key": row["landmark_key"],
                "ledger_time_local": row["observation_time_local"],
                "time_local_offset_bearing": t.isoformat(),
                "ledger_time_naive": t.tzinfo is not None and "+" not in row["observation_time_local"] and "-04:00" not in row["observation_time_local"],
                "time_kind": "stated_exact",
                "time_window_local": [t.isoformat(), t.isoformat()],
                "ledger_depth_in": float(depth) if depth else None,
                "depth_kind": "point" if depth else ("qualitative" if row["observed_qualitative"] else "none"),
                "depth_lo_in": float(depth) if depth else None,
                "depth_hi_in": float(depth) if depth else None,
                "observed_qualitative": row["observed_qualitative"],
            }
            ov = OVERRIDES.get(n, {})
            rec.update({k: v for k, v in ov.items()})
            if "depth_lo_in" in ov and "depth_hi_in" not in ov and ov.get("depth_kind") == "lower_bound":
                rec["depth_hi_in"] = None
            if "depth_hi_in" in ov and "depth_lo_in" not in ov and ov.get("depth_kind") == "upper_bound":
                rec["depth_lo_in"] = None
            if ov.get("depth_kind") == "not_applicable":
                rec["depth_lo_in"] = rec["depth_hi_in"] = None
            records.append(rec)
            seen.add(n)
    missing = sorted(set(OVERRIDES) - seen)
    assert not missing, f"overrides for unregistered rows: {missing}"
    out = {
        "schema_version": 1,
        "created_local": dt.datetime.now(dt.timezone.utc).astimezone(
            parse_station_local_time("2026-09-27T00:00").tzinfo).isoformat(timespec="seconds"),
        "purpose": ("Additive interval/provenance sidecar for the 2026-09-25..27 ledger rows. "
                    "The ledger scalars are unchanged; consumers that score or classify "
                    "should use time_window_local and depth_lo/hi_in, and treat "
                    "surrogate/window times and range midpoints as such."),
        "time_kinds": ["stated_exact", "approximate", "window", "surrogate", "already_present", "upper_bound"],
        "depth_kinds": ["point", "range", "approximate", "lower_bound", "upper_bound", "qualitative", "not_applicable", "none"],
        "sources": ["assets/observations/2026-09-26/rawnotes/01-morning.txt",
                    "assets/observations/2026-09-26/rawnotes/02-evening.txt",
                    "assets/observations/2026-09-27/rawnotes/01-morning.txt",
                    "assets/observations/2026-09-27/analysis/rawnotes-reconciliation.json"],
        "records": records,
    }
    OUT.write_text(json.dumps(out, indent=1))
    kinds = {}
    for r in records:
        kinds[(r["time_kind"], r["depth_kind"])] = kinds.get((r["time_kind"], r["depth_kind"]), 0) + 1
    print(len(records), "records;", sum(r["ledger_time_naive"] for r in records), "naive ledger stamps")
    for k, v in sorted(kinds.items()):
        print(" ", k, v)


if __name__ == "__main__":
    main()
