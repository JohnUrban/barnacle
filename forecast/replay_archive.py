"""Prospective replay-input archive (v0.10.6; owner decision 2026-09-24 on
review audits/2026-09-24-a1 items 2 and 5, following Codex's recommendation).

One compact JSON line per hourly run, appended to
data/replay_inputs/YYYY-MM.jsonl (append-only, gate-checked). It keeps what a
later replay or skill study needs and what no public archive keeps for us:
  - item 2: the RAW hourly NWS gauge forecast (NWPS) with its issuance and
    retrieval times, the NWS advisory rows, the hourly astronomy over the same
    hours, and the corrected hourly outlook surge with its per-hour source;
  - item 5: the production rain forecast (hourly QPF) as issued, the surge
    rung/reading/mean actually used, the tank's initialization, and the
    model version.
Unavailable inputs are written as unavailable (null + a reason), never as zero.

Schema 2 (as-issued validation logging repairs, 2026-09-24; review before
merge): `nwps.retrieved` is the outlook gather's run time (labeled by
`retrieved_basis`) and is never replaced by the generation time; the NWS
advisory's issuance is a dedicated `advisory.issued_utc` (parsed from the
status, null + reason when absent); `qpf_source` keeps the grid's updateTime,
retrieval time and raw (validTime, mm) intervals. Schema-1 rows stay valid.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import re

SCHEMA_VERSION = 2
DIR_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "data", "replay_inputs")
REQUIRED_KEYS = ("v", "generated_utc", "model_version", "surge", "nwps", "advisory",
                 "outlook_hourly", "qpf_hourly", "tank_init", "unavailable")


def _r(v, n=3):
    return None if v is None or not isinstance(v, (int, float)) or not math.isfinite(v) else round(float(v), n)


def _stamp(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _parse(stamp):
    return dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def columnar(times, **cols):
    """Compact hourly arrays: {"start", "step_h": 1, col: [...]} when the times
    are exactly hourly and consecutive; otherwise explicit "times"."""
    ts = [_parse(t) if not isinstance(t, dt.datetime) else t.astimezone(dt.timezone.utc) for t in times]
    out = {k: list(v) for k, v in cols.items()}
    if ts and all((b - a) == dt.timedelta(hours=1) for a, b in zip(ts, ts[1:])):
        out.update(start=_stamp(ts[0]), step_h=1)
    else:
        out["times"] = [_stamp(t) for t in ts]
    return out


def expand(block):
    """Inverse of columnar(): [(utc datetime, {col: value}), ...]."""
    cols = {k: v for k, v in block.items() if k not in ("start", "step_h", "times")}
    n = len(next(iter(cols.values()))) if cols else 0
    if "times" in block:
        ts = [_parse(t) for t in block["times"]]
    else:
        t0 = _parse(block["start"])
        ts = [t0 + dt.timedelta(hours=i * block.get("step_h", 1)) for i in range(n)]
    return [(t, {k: v[i] for k, v in cols.items()}) for i, t in enumerate(ts)]


def advisory_issued_utc(status):
    """(issued UTC stamp, None) parsed from the NWS status text, or (None, reason)."""
    m = re.search(r"issued (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2}))", str(status or ""))
    if not m:
        return None, "no advisory issuance in the status"
    try:
        return _stamp(_parse(m.group(1))), None
    except ValueError:
        return None, f"unparsable issuance {m.group(1)!r}"


def build_record(forecast, outlook_data=None, outlook_health=None, qpf_hourly=None, qpf_meta=None):
    """The archive line for one run. `outlook_data`/`outlook_health` are the
    outlook gather() results; `qpf_hourly` the production [(utc, in/hr)] or
    None when the QPF fetch failed; `qpf_meta` the QPF fetch's provenance."""
    unavailable = {}
    gen = forecast.get("generated_utc")
    si = forecast.get("water_series_input") or {}
    surge = {"decay": si.get("decay"), "live_fetch": si.get("live_fetch"),
             "surge_mean_health": (forecast.get("input_health") or {}).get("surge_mean")}
    nwps = None
    od = outlook_data or {}
    oh = outlook_health or {}
    if od.get("nwps") and (od["nwps"].get("series")):
        fetched = (oh.get("nwps") or {}).get("fetched_at")
        nwps = {"issued": od["nwps"].get("issued"),
                "retrieved": fetched,
                "retrieved_basis": ("outlook gather start (run time), not the response time" if fetched
                                    else "unavailable: no fetch time reported"),
                "hourly": columnar([p["utc"] for p in od["nwps"]["series"]],
                                   ft=[_r(p.get("ft"), 2) for p in od["nwps"]["series"]])}
    else:
        unavailable["nwps"] = (oh.get("nwps") or {}).get("detail") or "not fetched"
    _iss, _iss_why = advisory_issued_utc(forecast.get("nws_status"))
    advisory = {"status": forecast.get("nws_status"), "issued_utc": _iss, "issued_reason": _iss_why,
                "rows": [[t.get("time"), _r(t.get("forecast_peak_mllw"), 2), _r(t.get("surge_ft"), 2)]
                         for t in (forecast.get("all_tides") or [])
                         if t.get("source") == "nws-coastal-flood-product"]}
    ol = forecast.get("outlook_7d") or {}
    pts = [p for p in (ol.get("series") or []) if p.get("lead_h") is not None and -6 <= p["lead_h"] <= 72]
    outlook_hourly = (columnar([p["utc"] for p in pts], astro_mllw=[_r(p.get("astro_mllw"), 3) for p in pts],
                               tide_navd88=[_r(p.get("tide_navd88"), 3) for p in pts],
                               source=[p.get("surge_source") for p in pts]) if pts else None)
    if not pts:
        unavailable["outlook_hourly"] = "no outlook series"
    corrections = (ol.get("assumptions") or {}).get("advisory_corrections")
    if qpf_hourly is None:
        qpf = None
        unavailable["qpf_hourly"] = ((forecast.get("input_health") or {}).get("nws_qpf") or {}).get("detail") or "unavailable"
    else:
        qpf = columnar([t for t, _ in qpf_hourly], in_hr=[_r(r, 4) for _, r in qpf_hourly])
    ws = forecast.get("water_series") or []
    tank_init = {"series_start": ws[0]["time"] if ws else None, "storage": "empty at series start",
                 "first_bay_navd88": _r(ws[0].get("tide_navd88"), 3) if ws else None}
    return {"v": SCHEMA_VERSION, "generated_utc": gen, "model_version": forecast.get("model_version"),
            "surge": surge, "nwps": nwps, "advisory": advisory,
            "advisory_corrections": corrections, "outlook_hourly": outlook_hourly,
            "qpf_hourly": qpf, "rain_guidance_cycles": {
                "nbm": ((ol.get("reach") or {}).get("nbm_cycle")),
                "petss": ((ol.get("reach") or {}).get("petss_cycle"))},
            "tank_init": tank_init, "unavailable": unavailable,
            "qpf_source": qpf_meta if qpf_meta is not None else {"status": "unavailable", "reason": "not captured"}}


def append(record, directory=None):
    """Append one line to the month's file (append-only). Returns the path."""
    d = directory or DIR_DEFAULT
    os.makedirs(d, exist_ok=True)
    month = str(record.get("generated_utc") or "")[:7] or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")
    path = os.path.join(d, f"{month}.jsonl")
    line = json.dumps(record, separators=(",", ":"), sort_keys=True, allow_nan=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return path


def validate_file(path):
    """Gate: every line strict JSON with the required keys; generated_utc
    non-decreasing (append-only order)."""
    bad = []
    last = ""
    try:
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if not line.strip():
                    bad.append(f"line {i}: blank")
                    continue
                try:
                    rec = json.loads(line, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
                except ValueError as e:
                    bad.append(f"line {i}: not strict JSON ({e})")
                    continue
                missing = [k for k in REQUIRED_KEYS if k not in rec]
                if missing:
                    bad.append(f"line {i}: missing {missing}")
                g = str(rec.get("generated_utc") or "")
                if g < last:
                    bad.append(f"line {i}: generated_utc {g} before the previous line")
                last = max(last, g)
    except OSError as e:
        bad.append(f"unreadable ({e})")
    return bad
