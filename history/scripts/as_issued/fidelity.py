"""Replay fidelity: reproduce PUBLISHED outputs from ARCHIVED inputs before any
outcome is examined. No observation is read here.

F1 core astronomy: published tide_navd88 minus (NOAA 30-min astronomy - 2.82)
   = the surge the curve used; compared with each version's declared rule
   (v0.10.6 decay metadata; v0.10.5 the published reading, constant; earlier
   a constant = the worst tide's surge).
F2 core tank: the published pluvial line re-run from the published bay and the
   as-used hourly rain where that rain is archived (v0.10.6 replay records;
   the outlook's hourly rain from 2026-09-23), with the tank source at the
   forecast's own commit fingerprinted.
F3 advisory control (Study A): published outlook minus raw NWPS versus the
   correction reconstructed from the recorded anchors, by source label.
F4 reading: the published observed-surge reading vs the published gauge level
   at the same time minus hourly-interpolated astronomy (production's method).
Tolerances follow stored precision: bay/tide 0.001 ft, NWPS 0.01 ft, NOAA
predictions 0.001 ft.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

from . import archive as A
from . import noaa

ROOT = A.ROOT
sys.path.insert(0, ROOT)
from forecast.station_time import parse_station_local_time  # noqa: E402

UTC = dt.timezone.utc
NAVD = -2.82
ASTRO_DIR = os.path.join(ROOT, "history", "data", "as_issued", "astronomy")


def load_astronomy(directory=ASTRO_DIR):
    b = noaa.load_bodies(os.path.join(directory, "manifest.json"))
    p30 = noaa.predictions([x for x in b if x[0]["query"].get("interval") == "30"])
    p6 = noaa.predictions([x for x in b if "interval" not in x[0]["query"]])
    hilo = []
    for _e, body in [x for x in b if x[0]["query"].get("interval") == "hilo"]:
        for r in json.loads(body).get("predictions") or []:
            hilo.append((noaa._t(r["t"]), float(r["v"]), r.get("type")))
    return p30, p6, sorted(set(hilo))


def num(x):
    """A finite real number (bools and strings are not)."""
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _time_ok(x):
    try:
        return A.parse_utc(x) is not None
    except (TypeError, ValueError, AttributeError):
        return False


def core_points(f):
    """[(utc, point)] with a parseable time (malformed entries/times are skipped,
    which leaves a gap that later checks treat as a gap)."""
    out = []
    ws = f.get("water_series") if isinstance(f, dict) else None
    for p in ws if isinstance(ws, list) else []:
        if not isinstance(p, dict):
            continue
        try:
            t = parse_station_local_time(p["time"]).astimezone(UTC)
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        out.append((t, p))
    return sorted(out, key=lambda x: x[0])


def series_problems(pts):
    """Counts of invalid published values on the core line (audit a4 round 05):
    bay and combined must be finite numbers where present; pluvial must be a
    finite number or absent (absent = no water above the street base)."""
    c = Counter()
    for _t, p in pts:
        if p.get("tide_navd88") is not None and not num(p.get("tide_navd88")):
            c["bay"] += 1
        if p.get("water_navd88") is not None and not num(p.get("water_navd88")):
            c["combined"] += 1
        if p.get("pluvial_navd88") is not None and not num(p.get("pluvial_navd88")):
            c["pluvial"] += 1
    return dict(c)


def rule_problems(f):
    """Problems in the published surge-rule metadata, checked BEFORE it is used."""
    wsi = f.get("water_series_input")
    if wsi is None:
        return []
    if not isinstance(wsi, dict):
        return ["water_series_input is not an object"]
    out = []
    dec = wsi.get("decay")
    if dec:
        if not isinstance(dec, dict):
            return ["decay metadata is not an object"]
        if not num(dec.get("mean_ft")):
            out.append("decay mean_ft not a finite number")
        has_reading = dec.get("surge_obs_ft") is not None or dec.get("observation_utc") is not None
        if has_reading:
            if not num(dec.get("surge_obs_ft")):
                out.append("decay surge_obs_ft not a finite number")
            if not _time_ok(dec.get("observation_utc")):
                out.append("decay observation_utc not a parseable time")
            # a decaying reading NEEDS its published timescale; it is never filled in from
            # the current constant (a4 round 07)
            if "tau_h" not in dec or dec.get("tau_h") is None:
                out.append("decay tau_h missing or null for a decaying reading")
            elif not (num(dec["tau_h"]) and dec["tau_h"] > 0):
                out.append("decay tau_h not a positive finite number")
        elif dec.get("tau_h") is not None and not (num(dec["tau_h"]) and dec["tau_h"] > 0):
            # declared exception: the mean-only rung (no reading) uses no timescale, so a
            # missing/null tau is acceptable there; a PRESENT tau must still be valid
            out.append("decay tau_h not a positive finite number")
    elif wsi.get("surge_ft") is not None:
        if not num(wsi.get("surge_ft")):
            out.append("published reading surge_ft not a finite number")
        try:
            parse_station_local_time(wsi.get("observation_time"))
        except (TypeError, ValueError, AttributeError):
            out.append("published reading observation_time not parseable")
    return out


def decay_surge(decay, t, tau=None):
    mean = decay["mean_ft"]
    if decay.get("surge_obs_ft") is None or decay.get("observation_utc") is None:
        return mean
    age = (t - A.parse_utc(decay["observation_utc"])).total_seconds() / 3600.0
    if age <= 0:
        return decay["surge_obs_ft"]
    return mean + (decay["surge_obs_ft"] - mean) * math.exp(-age / (tau if tau is not None else decay["tau_h"]))


def declared_rule(f):
    """('decay', decay) | ('constant', value, why) | (None, why)."""
    v = f.get("model_version")
    wsi = f.get("water_series_input") or {}
    if wsi.get("decay"):
        return ("decay", wsi["decay"])
    if wsi.get("surge_ft") is not None:
        return ("constant", float(wsi["surge_ft"]), "published reading (v0.10.5 rule)")
    return ("constant", None, f"worst tide's surge (rule of {v or 'pre-v0.10.1'})")


def f1_astronomy(f, p30):
    pts = [(t, p) for t, p in core_points(f) if p.get("tide_navd88") is not None]
    if not pts:
        return {"status": "no published bay line"}
    bad = series_problems(pts).get("bay", 0)
    rp = rule_problems(f)
    if bad or rp:
        return {"status": "invalid published input", "invalid_bay_values": bad, "rule_problems": rp}
    miss = [t for t, _p in pts if t not in p30]
    if miss:
        return {"status": "astronomy not covered", "missing": len(miss)}
    resid = [(t, p["tide_navd88"] - (p30[t] + NAVD)) for t, p in pts]
    rule = declared_rule(f)
    out = {"points": len(pts), "stale_tides_flag": bool(f.get("tide_predictions_stale"))}
    if rule[0] == "decay":
        d = [abs(r - decay_surge(rule[1], t)) for t, r in resid]
        out.update(rule="decay", max_abs_vs_rule=round(max(d), 4))
    else:
        vals = [r for _t, r in resid]
        out.update(rule="constant", spread=round(max(vals) - min(vals), 4), implied_surge=round(sum(vals) / len(vals), 4),
                   declared=rule[1], rule_note=rule[2])
        if rule[1] is not None:
            out["max_abs_vs_rule"] = round(max(abs(v - rule[1]) for v in vals), 4)
        else:
            tides = [t.get("surge_ft") for t in (f.get("all_tides") or []) if isinstance(t, dict) and num(t.get("surge_ft"))]
            out["matches_a_tide_surge"] = any(abs(out["implied_surge"] - s) <= 0.002 for s in tides)
    return out


def tank_fingerprint(commit, cache={}):
    """SHA-256 of simulate_pluvial_series + _pluvial_fill + tank constants at a commit."""
    if commit in cache:
        return cache[commit]
    try:
        src = A._git("show", f"{commit}:forecast/flood_forecast_daily.py").decode()
    except Exception:  # noqa: BLE001
        cache[commit] = None
        return None
    parts = []
    for name in ("def simulate_pluvial_series", "def _pluvial_fill"):
        i = src.find(name)
        if i < 0:
            cache[commit] = None
            return None
        j = src.find("\ndef ", i + 5)
        parts.append(src[i:j])
    for c in ("PLUVIAL_STREET_BASE", "PLUVIAL_DRAIN_FULL_BELOW", "PLUVIAL_DRAIN_RATE", "TANK_K", "TANK_GAMMA",
              "TANK_KOUT", "TANK_LAG_MIN"):
        m = re.search(rf"^{c}\s*=\s*([^\s#]+)", src, re.M)
        parts.append(f"{c}={m.group(1) if m else None}")
    try:
        curve = A._git("show", f"{commit}:history/data/stage_storage_curve.csv")
    except Exception:  # noqa: BLE001
        curve = b""
    fp = hashlib.sha256(("\n".join(parts)).encode() + curve).hexdigest()
    cache[commit] = fp
    return fp


def _tank():
    spec = importlib.util.spec_from_file_location("rain_ref", os.path.join(ROOT, "models", "wind_shadow", "rain_ref.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def archived_rain(f, replay):
    """(source, {hour: in/hr}) of the as-used core rain, or (None, reason)."""
    if replay is not None and replay.get("qpf_hourly"):
        from forecast import replay_archive as ra
        return "replay record qpf_hourly", {t: v["in_hr"] for t, v in ra.expand(replay["qpf_hourly"])}
    if replay is not None and replay.get("qpf_hourly") is None and "qpf_hourly" in (replay.get("unavailable") or {}):
        return None, "QPF unavailable at issuance (replay record)"
    ser = ((f.get("outlook_7d") or {}).get("series")) or []
    if ser:
        by = {}
        for p in ser:
            if p.get("rain_source") == "nws_grid" and not p.get("rain_unknown") and p.get("rain_in_hr") is not None:
                by[A.parse_utc(p["utc"])] = float(p["rain_in_hr"])
        if by:
            return "outlook hourly rain (nws_grid)", by
    return None, "hourly rain as used not archived"


def f2_tank(f, commit, replay, tank):
    pts = [(t, p) for t, p in core_points(f) if p.get("tide_navd88") is not None]
    if len(pts) < 2:
        return {"status": "no published bay line"}
    sp = series_problems(pts)
    if sp.get("bay") or sp.get("pluvial"):
        return {"status": "not replayable", "reason": f"invalid published values {sp}"}
    src, rain = archived_rain(f, replay)
    if src is None:
        return {"status": "not replayable", "reason": rain}
    times = [t for t, _p in pts]
    bad_rain = [v for v in rain.values() if v is not None and not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0)]
    if bad_rain:
        return {"status": "not replayable", "reason": f"invalid archived rain values ({len(bad_rain)})"}
    rain = {h: v for h, v in rain.items() if v is not None}          # null = unavailable hour, never zero
    hours = {t.replace(minute=0) for t in times}
    covered = [h for h in hours if h in rain]
    rates = [rain.get(t.replace(minute=0), 0.0) for t in times]
    sim = tank.simulate_pluvial_series(times, [p["tide_navd88"] for _t, p in pts], rates)
    pub = [p.get("pluvial_navd88") for _t, p in pts]
    diffs = [abs(a - b) for a, b in zip(sim, pub) if a is not None and b is not None]
    return {"status": "replayed", "rain_source": src, "rain_hours_covered": f"{len(covered)}/{len(hours)}",
            "first_point_hour_covered": times[0].replace(minute=0) in rain,
            "max_abs_diff_ft": round(max(diffs), 4) if diffs else 0.0,
            "presence_mismatches": sum((a is None) != (b is None) for a, b in zip(sim, pub)),
            "published_pluvial_points": sum(b is not None for b in pub),
            "tank_fingerprint": tank_fingerprint(commit)}


def f3_parity(f, replay):
    """Advisory control (a4 R2): published outlook minus raw NWPS versus the
    correction reconstructed from the RECORDED anchors, by source label."""
    if replay is None or not replay.get("nwps"):
        return {"status": "no raw NWPS archived"}
    from forecast import replay_archive as ra
    from . import advisory as AD
    raw = {t: v.get("ft") for t, v in ra.expand(replay["nwps"]["hourly"])}
    corr_rows = replay.get("advisory_corrections") or []
    if any(v is not None and not num(v) for v in raw.values()) or any(
            not num(c.get("ft")) or not _time_ok(c.get("utc")) for c in corr_rows):
        return {"status": "invalid input", "reason": "non-finite raw NWPS value or invalid recorded anchor"}
    raw = {t: v for t, v in raw.items() if v is not None}
    anchors = sorted((A.parse_utc(c["utc"]), float(c["ft"])) for c in corr_rows)
    ser = ((f.get("outlook_7d") or {}).get("series")) or []
    by_src = defaultdict(list)
    label_mismatch = 0
    for p in ser:
        try:
            t = A.parse_utc(p["utc"])
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if p.get("surge_source") in ("nwps", "nws_product") and t in raw and num(p.get("tide_navd88")):
            corr, anchored = AD.correction_at(anchors, t)
            by_src[p["surge_source"]].append(abs((p["tide_navd88"] - NAVD) - raw[t] - corr))
            label_mismatch += (p["surge_source"] == "nws_product") != anchored
    return {"status": "compared", "anchors": [round(c, 3) for _t, c in anchors],
            "nonzero_anchors": sum(1 for _t, c in anchors if abs(c) >= 0.005), "label_mismatches": label_mismatch,
            "by_source": {k: {"n": len(v), "max_abs_residual_ft": round(max(v), 4)} for k, v in by_src.items()},
            "nwps_issued": replay["nwps"].get("issued"), "nwps_retrieved": replay["nwps"].get("retrieved")}


def hourly_interp_astronomy(p30, t):
    """Production's reading astronomy: linear between the bracketing HOURLY
    predictions (flood_forecast_daily fetch surge reading, interval=h)."""
    a = t.replace(minute=0, second=0, microsecond=0)
    b = a + dt.timedelta(hours=1)
    if a not in p30 or b not in p30:
        return None
    if t == a:
        return p30[a]
    return p30[a] + (t - a).total_seconds() / 3600.0 * (p30[b] - p30[a])


def f4_reading(f, p30):
    """Rebuild the observed-surge reading as production computes it: the last
    published gauge level minus hourly-interpolated astronomy at its time. The
    published gauge series is a separate fetch from the one production used,
    so its last point may be a different 6-min observation: compared only when
    the times agree (v0.10.6 observation_utc / v0.10.5 observation_time)."""
    rp = rule_problems(f)
    if rp:
        return {"status": "invalid published input", "rule_problems": rp}
    wsi = f.get("water_series_input") or {}
    dec = wsi.get("decay") or {}
    pub = dec.get("surge_obs_ft", wsi.get("surge_ft"))
    pub_t = dec.get("observation_utc")
    if pub_t is None and wsi.get("observation_time"):
        try:
            pub_t = parse_station_local_time(wsi["observation_time"]).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (TypeError, ValueError):
            pub_t = None
    lg = f.get("live_gauge_24h") or []
    if not lg:
        return {"status": "no published gauge levels"}
    series = {}
    for q in lg if isinstance(lg, list) else []:
        try:
            v = float(q["value_mllw"])
            if math.isfinite(v):
                series[parse_station_local_time(q["time"]).astimezone(UTC)] = v
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    if not series:
        return {"status": "no published gauge levels"}
    t = max(series) if pub_t is None else A.parse_utc(pub_t)
    if t not in series:
        return {"status": "reading time not in the published gauge series", "reading_time_utc": pub_t}
    a = hourly_interp_astronomy(p30, t)
    if a is None:
        return {"status": "astronomy not covered"}
    rebuilt = series[t] - a
    out = {"status": "rebuilt", "reading_time_utc": t.strftime("%Y-%m-%dT%H:%MZ"), "rebuilt_ft": round(rebuilt, 4),
           "time_source": "published observation time" if pub_t else "last published gauge level"}
    if pub is not None:
        out.update(published_ft=pub, abs_diff_ft=round(abs(rebuilt - pub), 4))
    return out


def run(inv_rows=None):
    inv = A.inventory() if inv_rows is None else {"rows": inv_rows}
    p30, p6, _hilo = load_astronomy()
    tank = _tank()
    replay = {r["generated_utc"]: (r, ident) for r, ident in A.replay_records()}
    rows = []
    for s in inv["rows"]:
        if not s["core_has_tide"] and not s["outlook"]:
            continue
        f = A.load_forecast(s["blob"])
        rp = replay.get(s["generated_utc"])
        rows.append({"generated_utc": s["generated_utc"], "model_version": s["model_version"], "commit": s["commit"],
                     "blob": s["blob"], "replay_line": rp[1] if rp else None,
                     "F1": f1_astronomy(f, p30), "F2": f2_tank(f, s["commit"], rp[0] if rp else None, tank),
                     "F3": f3_parity(f, rp[0] if rp else None), "F4": f4_reading(f, p30)})
    return rows


def summarize(rows):
    out = {"issuances": len(rows)}
    byv = defaultdict(list)
    for r in rows:
        byv[r["model_version"] or "pre-v0.10.1"].append(r)
    f1 = {}
    for v, rs in byv.items():
        c = Counter()
        worst = 0.0
        for r in rs:
            x = r["F1"]
            if "max_abs_vs_rule" in x:
                ok = x["max_abs_vs_rule"] <= 0.0025
                c["reproduced within 0.0025 ft" if ok else "NOT reproduced"] += 1
                worst = max(worst, x["max_abs_vs_rule"])
            elif "spread" in x:
                ok = x["spread"] <= 0.0025 and x.get("matches_a_tide_surge")
                c["constant and equal to a tide surge" if ok else "constant rule not confirmed"] += 1
                worst = max(worst, x["spread"])
            else:
                c[x["status"]] += 1
        f1[v] = {"counts": dict(c), "worst_ft": round(worst, 4)}
    out["F1_core_astronomy_by_version"] = f1
    f2 = Counter(r["F2"]["status"] + (": " + r["F2"].get("rain_source", r["F2"].get("reason", "")) if r["F2"].get("rain_source") or r["F2"].get("reason") else "") for r in rows)
    rep = [r["F2"] for r in rows if r["F2"]["status"] == "replayed"]
    out["F2_core_tank"] = {"status_counts": dict(f2), "replayed": len(rep),
                           "max_abs_diff_ft": max((x["max_abs_diff_ft"] for x in rep), default=None),
                           "presence_mismatches": sum(x["presence_mismatches"] for x in rep),
                           "with_published_pluvial": sum(1 for x in rep if x["published_pluvial_points"]),
                           "first_hour_uncovered": sum(1 for x in rep if not x["first_point_hour_covered"]),
                           "tank_fingerprints": dict(Counter(x["tank_fingerprint"] for x in rep))}
    f3 = [r["F3"] for r in rows if r["F3"]["status"] == "compared"]
    out["F3_advisory_control"] = {"records": len(f3), "nonzero_anchors": sum(x["nonzero_anchors"] for x in f3),
                                  "label_mismatches": sum(x["label_mismatches"] for x in f3),
                                  "max_abs_residual_by_source": {s: max(x["by_source"][s]["max_abs_residual_ft"] for x in f3 if s in x["by_source"])
                                                                 for s in {k for x in f3 for k in x["by_source"]}}}
    f4 = [r["F4"] for r in rows if r["F4"].get("abs_diff_ft") is not None]
    out["F4_reading"] = {"compared": len(f4), "max_abs_diff_ft": max((x["abs_diff_ft"] for x in f4), default=None),
                         "rebuilt_only": sum(1 for r in rows if r["F4"]["status"] == "rebuilt" and r["F4"].get("abs_diff_ft") is None),
                         "not_rebuilt": dict(Counter(r["F4"]["status"] for r in rows if r["F4"]["status"] != "rebuilt"))}
    return out
