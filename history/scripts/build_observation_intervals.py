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

BASIS (audit round 05 R5): every window or range carries a basis —
  stated             the owner's own words give the endpoints ("0.5-1 inch",
                     "less than 1 cm below", "between 9:20 and 9:40")
  stated_landmarks   endpoints follow from named landmarks the owner cited
  adjacent_entries   an untimed line bounded by the timed lines around it
  unquantified       the owner gave an approximate/qualitative value and
                     NO defensible numeric width exists; lo/hi stay None
Analyst-chosen widths are NOT encoded here (they were in the first version
and are withdrawn): consumers must never score against a bound whose basis
is not stated / stated_landmarks / adjacent_entries.

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
    191: {"time_kind": "surrogate", "time_basis": "unquantified", "time_window_local": None,
          "time_note": "Negative check; ledger uses the gauge-peak minute (20:06) as a surrogate. Owner home 20:00-20:30, spouse home all evening; exact observation time unconfirmed and not numerically bounded.",
          "depth_kind": "upper_bound", "depth_basis": "stated", "depth_hi_in": 0.0, "depth_note": "No flooding at the intersection (bound: water below the SW grate)."},
    187: {"time_kind": "approximate", "time_basis": "unquantified", "time_window_local": None,
          "time_note": "Original: 'Around 7'; no numeric window is stated. Water already present earlier ('underway for a while')."},
    188: {"depth_kind": "lower_bound", "depth_basis": "stated", "depth_lo_in": 0.0, "depth_note": "Over the curb, near top of lawn step (qualitative)."},
    190: {"depth_kind": "range", "depth_basis": "stated_landmarks", "depth_lo_in": 0.0, "depth_hi_in": 0.24, "depth_note": "Over the lawn step (4.66) but not to the porch-step base (4.68): 0-0.24 in above the lawn step, from the two named landmarks."},
    194: {"depth_kind": "range", "depth_basis": "stated", "depth_lo_in": 1.4, "depth_hi_in": 1.5, "depth_note": "Original 1.4-1.5 in; ledger 1.45 is the midpoint."},
    219: {"time_note": "Original file said '12:06 am'; midday confirmed by owner 2026-09-27 (rawnotes/clarifications.txt)."},
    221: {"depth_kind": "approximate", "depth_basis": "unquantified", "depth_lo_in": None, "depth_hi_in": None, "depth_note": "'about 1 cm under the curb': nominal -0.39 in; ledger -0.4. No stated width."},
    222: {"depth_kind": "upper_bound", "depth_basis": "stated", "depth_hi_in": 0.0, "depth_note": "'Roads virtually clear; intersection clear; safe to drive': water below the intersection high point (4.54)."},
    230: {"time_kind": "window", "time_basis": "stated", "time_window_local": ["2026-09-26T21:20:00-04:00", "2026-09-26T21:40:00-04:00"],
          "time_note": "First water reported 'sometime between 9:20-9:40'; ledger 21:30 is the midpoint, not onset.",
          "depth_kind": "lower_bound", "depth_basis": "stated", "depth_lo_in": 0.0, "depth_note": "Water spans SE-SW grates across Central (above SW grate)."},
    231: {"depth_kind": "range", "depth_basis": "stated", "depth_lo_in": -0.39, "depth_hi_in": 0.0, "depth_note": "'less than 1 cm below the curb'; ledger -0.3."},
    232: {"time_kind": "surrogate", "time_basis": "adjacent_entries", "time_window_local": ["2026-09-26T21:54:00-04:00", "2026-09-26T22:11:00-04:00"],
          "time_note": "Gate visit untimed in the original; ledger 21:58 assigned from the surrounding 21:54 and 22:11 entries.",
          "depth_kind": "not_applicable", "depth_basis": "none", "depth_note": "Infrastructure state report ('almost certainly closed'), not a water level."},
    233: {"depth_kind": "range", "depth_basis": "stated", "depth_lo_in": 0.5, "depth_hi_in": 1.0, "depth_note": "Original 0.5-1 in over curb; ledger 0.75 midpoint. Companion phrase 'base of lawn step and a little up it' implies a different level under the survey; not reconciled."},
    234: {"depth_kind": "range", "depth_basis": "stated", "depth_lo_in": 0.5, "depth_hi_in": 1.0, "depth_note": "'same as 10:11'; range as row 233."},
    235: {"depth_kind": "approximate", "depth_basis": "unquantified", "depth_note": "'more like 0.5 inch, not 1', receding."},
    236: {"time_kind": "upper_bound", "time_basis": "stated", "time_window_local": ["2026-09-26T22:39:00-04:00", "2026-09-26T23:12:00-04:00"],
          "time_note": "Receded 'completely as far as I can tell'; clearing time unknown between the 22:39 report and this 23:12 one.",
          "depth_kind": "upper_bound", "depth_basis": "stated", "depth_hi_in": 0.0},
    237: {"time_kind": "already_present", "time_basis": "stated", "time_note": "Water already present at 07:48; not flood onset.",
          "depth_kind": "lower_bound", "depth_basis": "stated", "depth_lo_in": 0.0, "depth_note": "Minor water SE-SW across Central; ~1 in over NE/NW grates."},
    238: {"depth_kind": "approximate", "depth_basis": "unquantified", "depth_lo_in": None, "depth_hi_in": None, "depth_note": "'nearly to curb level at lawn step' (qualitative); no numeric width stated."},
    240: {"depth_kind": "approximate", "depth_basis": "unquantified", "depth_note": "'6 inches over NE grate; around 5.5 inches above street at curb' (two co-reports)."},
    241: {"depth_kind": "lower_bound", "depth_basis": "stated", "depth_lo_in": 0.0, "depth_note": "Bay Ave crossed at the upstream grate (water at or above it)."},
    251: {"depth_kind": "lower_bound", "depth_basis": "stated", "depth_lo_in": 0.0, "depth_note": "Breached over the first porch step top; water entering garage (level not measured)."},
    255: {"depth_kind": "approximate", "depth_basis": "unquantified", "depth_note": "'may have stopped rising'."},
    256: {"depth_kind": "upper_bound", "depth_basis": "stated", "depth_hi_in": 11.25, "depth_note": "'11.25 or just slightly lower'."},
    257: {"depth_kind": "upper_bound", "depth_basis": "stated", "depth_hi_in": 11.0, "depth_note": "'11 or slightly lower'."},
    258: {"depth_kind": "upper_bound", "depth_basis": "stated", "depth_hi_in": 9.5, "depth_note": "'9.5 or slightly lower'."},
    259: {"time_kind": "surrogate", "time_basis": "adjacent_entries", "time_window_local": ["2026-09-27T08:24:00-04:00", "2026-09-27T08:36:00-04:00"],
          "time_note": "Gate visit untimed in the original; ledger 08:30 assigned between the 08:24 and 08:36 entries.",
          "depth_kind": "not_applicable", "depth_basis": "none", "depth_note": "Infrastructure state ('almost certainly closed'), not visual confirmation."},
    263: {"depth_kind": "range", "depth_basis": "stated", "depth_lo_in": 0.5, "depth_hi_in": 1.0, "depth_note": "'at most an inch above the curb, probably 0.5-1'; ledger 0.75 midpoint."},
}


def row_hash(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


BOUNDS = ROOT / "data/observation_bounds.jsonl"


def landmark_bounds(rows):
    """{row sha256: validated record} from the standing landmark-bounds
    record through the shared contract (round 16 R3); invalid lines are
    reported and skipped, never silently used."""
    from forecast import observation_bounds as ob
    by_hash, problems = ob.load_bounds(str(BOUNDS), rows, locator="hash")
    for p in problems:
        print("WARNING bounds:", p)
    return by_hash


def main():
    reg = json.loads(REGISTRY.read_text())
    with LEDGER.open(newline="") as f:
        rows = list(csv.DictReader(f))
    sys.path.insert(0, str(ROOT))
    from forecast import flood_forecast_daily as ff
    elev = {k: e for k, _l, e, _s in ff.LANDMARKS}
    bounds = landmark_bounds(rows)
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
                "time_basis": "stated",
                "time_window_local": [t.isoformat(), t.isoformat()],
                "ledger_depth_in": float(depth) if depth else None,
                "depth_kind": "point" if depth else ("qualitative" if row["observed_qualitative"] else "none"),
                "depth_basis": "stated" if depth else "none",
                "depth_lo_in": float(depth) if depth else None,
                "depth_hi_in": float(depth) if depth else None,
                "observed_qualitative": row["observed_qualitative"],
            }
            ov = OVERRIDES.get(n, {})
            rec.update({k: v for k, v in ov.items()})
            # landmark bands from the standing record take precedence over the
            # hand overrides: inches relative to the row's landmark, basis
            # stated_landmarks, provenance carried
            lb = bounds.get(ref["sha256"])
            if lb and row["landmark_key"] in elev and (not depth or lb.get("supersedes_scalar")):
                # round 16 C1: a band replaces a legacy range-representative
                # scalar only when the record says supersedes_scalar
                e0 = elev[row["landmark_key"]]
                lo, hi = lb.get("lo_navd88"), lb.get("hi_navd88")
                rec["depth_kind"] = ("range" if lo is not None and hi is not None
                                     else "lower_bound" if lo is not None else "upper_bound")
                rec["depth_basis"] = lb.get("basis", "stated_landmarks")
                rec["depth_lo_in"] = None if lo is None else round((lo - e0) * 12, 2)
                rec["depth_hi_in"] = None if hi is None else round((hi - e0) * 12, 2)
                rec["landmark_band_navd88"] = [lo, hi]
                rec["landmark_band_text"] = lb.get("text")
                rec["landmark_band_sources"] = [lm.get("source") for lm in lb.get("landmarks", [])]
                rec["landmark_band_scope"] = lb.get("scope", "intersection")
                rec["landmark_band_disputed"] = bool(lb.get("disputed"))
                if depth:
                    rec["ledger_scalar_superseded"] = True
                # round 16 R2: time metadata travels with the record
                tk = lb.get("time_kind", "stated_exact")
                if tk != "stated_exact":
                    rec["time_kind"] = tk
                    rec["time_basis"] = "stated" if lb.get("time_window_local") else "unquantified"
                    rec["time_window_local"] = lb.get("time_window_local")
                ov = {}
            if "depth_lo_in" in ov and "depth_hi_in" not in ov and ov.get("depth_kind") == "lower_bound":
                rec["depth_hi_in"] = None
            if "depth_hi_in" in ov and "depth_lo_in" not in ov and ov.get("depth_kind") == "upper_bound":
                rec["depth_lo_in"] = None
            if ov.get("depth_kind") == "not_applicable":
                rec["depth_lo_in"] = rec["depth_hi_in"] = None
            if ov.get("depth_basis") == "unquantified" and ov.get("depth_kind") == "approximate" and "depth_lo_in" not in ov:
                # an approximate stated scalar: keep the ledger value as nominal, no bounds
                rec["depth_lo_in"] = rec["depth_hi_in"] = None
            if rec.get("time_basis") == "unquantified":
                rec["time_window_local"] = None
            assert rec["time_basis"] in ("stated", "stated_landmarks", "adjacent_entries", "unquantified"), n
            assert rec["depth_basis"] in ("stated", "stated_landmarks", "unquantified", "none"), n
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
        "bases": {"stated": "endpoints in the owner's own words", "stated_landmarks": "endpoints from named landmarks the owner cited",
                  "adjacent_entries": "untimed line bounded by the timed lines around it",
                  "unquantified": "approximate/qualitative with no defensible numeric width; lo/hi or window are null",
                  "none": "not applicable"},
        "scoring_rule": "Score only against bounds whose basis is stated, stated_landmarks or adjacent_entries. Unquantified rows are point/nominal values with unknown width; never invent a width for them.",
        "landmark_bounds_source": "data/observation_bounds.jsonl (append-only, row-hash keyed; bands from model/elevations.md and assets/map_points.csv; basis stated_landmarks)",
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
    print(len(records), "records;", sum(r["ledger_time_naive"] for r in records), "naive ledger stamps;",
          sum(1 for r in records if r["time_basis"] == "unquantified" or r["depth_basis"] == "unquantified"), "unquantified")
    for k, v in sorted(kinds.items()):
        print(" ", k, v)


if __name__ == "__main__":
    main()
