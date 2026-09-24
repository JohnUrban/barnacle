"""Street observations (data/labeled_observations.csv) classified by the
predeclared rules of the protocol, section 4 as amended before scoring
(Amendment 1: 4.2' level type, 4.3' evidence type)."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import os
import re
from zoneinfo import ZoneInfo

UTC = dt.timezone.utc
NY = ZoneInfo("America/New_York")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LEDGER = os.path.join(ROOT, "data", "labeled_observations.csv")
FIRST_BAY_LINE = dt.datetime(2026, 7, 6, 19, 35, 5, tzinfo=UTC)

UPPER_WORDS = ("at/below", "no water", "dry", "receded", "exposed", "driveable")
POINT_WORDS = ("level", "at bottom", "at the bottom", "at base", "hit", "up to", "appearing")
LOWER_WORDS = ("over ", "covered", "covering")
RECON = ("inferred", "backcast", "hindcast", "reconstruct")
DRY_OK = ("clear", "calm", "no rain")
DRY_NO = ("downpour", "thunder", "drizzle", "shower", "burst", "heavy rain", "light rain", "moderate rain",
          "rain continuing", "rain tail", "rain over")


def local_to_utc(s):
    t = dt.datetime.fromisoformat(s.strip())
    if t.tzinfo is None:
        t = t.replace(tzinfo=NY)
    return t.astimezone(UTC)


def _has(text, words):
    return any(w in text for w in words)


def classify(row, elevations):
    """Protocol 4.1-4.4 for one ledger row -> dict (never raises)."""
    key = (row.get("landmark_key") or "").strip()
    qual = (row.get("observed_qualitative") or "").lower()
    notes = (row.get("notes") or "").lower()
    weather = (row.get("weather_in_window") or "").lower()
    out = {"landmark": key, "raw_depth": row.get("observed_depth_in"), "reasons": []}
    try:
        out["time_utc"] = local_to_utc(row["observation_time_local"])
    except (KeyError, ValueError, TypeError):
        out["reasons"].append("unparsable time")
        out["time_utc"] = None
    if key == "none":
        out["reasons"].append("correction record")
    elif key not in elevations:
        out["reasons"].append(f"no current elevation for {key!r}")
    elev = elevations.get(key)
    out["elevation"] = elev
    depth_s = (row.get("observed_depth_in") or "").strip()
    level_type, level = None, None
    if not out["reasons"]:
        d = None
        if depth_s != "":
            try:
                d = float(depth_s)
            except ValueError:
                out["reasons"].append(f"unparsable depth {depth_s!r}")
        if d is not None and d != 0:
            level_type, level = "POINT", elev + d / 12.0
        elif not out["reasons"]:
            if _has(qual, UPPER_WORDS):
                level_type, level = "UPPER", elev
            elif _has(qual, POINT_WORDS):
                level_type, level = "POINT", elev
            elif _has(qual, LOWER_WORDS):
                level_type, level = "LOWER", elev
            elif d == 0:
                level_type, level = "UPPER", elev
            else:
                out["reasons"].append("blank depth without a classifiable wording")
    out["level_type"], out["level_navd88"] = level_type, level
    observer = (row.get("observer") or "").strip().lower()
    if _has(qual, RECON):
        ev = "RECONSTRUCTION"
    elif _has(qual, ("photo", "exif")):
        ev = "PHOTO"
    elif observer not in ("john", "claude", "codex", "") or "second observer" in qual:
        ev = "SECOND_OBSERVER"
    else:
        ev = "OBSERVER_ESTIMATE"
    out["evidence"] = ev
    out["dry"] = _has(weather, DRY_OK) and not _has(weather, DRY_NO)
    if out["time_utc"] is not None and out["time_utc"] < FIRST_BAY_LINE:
        out["reasons"].append("before the first published bay line")
    out["eligible"] = not out["reasons"] and level_type is not None
    return out


def load(path=LEDGER, elevations=None):
    if elevations is None:
        import sys
        sys.path.insert(0, ROOT)
        from forecast import flood_forecast_daily as ff
        elevations = {k: e for k, _l, e, _s in ff.LANDMARKS}
    with open(path, "rb") as f:
        blob = f.read()
    rows = list(csv.DictReader(blob.decode("utf-8").splitlines()))
    out = []
    for i, r in enumerate(rows, 2):
        c = classify(r, elevations)
        c["row"] = i
        out.append(c)
    return out, hashlib.sha256(blob).hexdigest()


def events(times, gap_h=12):
    """Group sorted times: a new event starts after a gap > gap_h. -> [event index]."""
    idx, out, last = -1, [], None
    for t in times:
        if last is None or (t - last) > dt.timedelta(hours=gap_h):
            idx += 1
        out.append(idx)
        last = t
    return out
