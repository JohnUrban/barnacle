"""Wind-shadow candidate (SHADOW ONLY; plan history/plans/2026-09-24-wind-term-candidate-plan.md,
design models/wind_shadow/DESIGN.md, frozen parameters models/wind_shadow/manifest.json).

After every production output of an hourly run is written, compute the
candidate surge (v0.10.6 decay + a forecast wind/pressure correction) for
leads 1..48 h and append one record to data/wind_shadow/YYYY-MM.jsonl. It
changes NOTHING the forecast publishes, displays or alerts on; it runs inside
a daemon thread with a hard wall-clock limit, and every failure is written
into the shadow record itself (never into forecast.json).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import threading
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(ROOT, "models", "wind_shadow", "manifest.json")
SHADOW_DIR = os.path.join(ROOT, "data", "wind_shadow")
SINGLE_RUNS_URL = "https://single-runs-api.open-meteo.com/v1/forecast"
META_URL = "https://api.open-meteo.com/data/ncep_gfs013/static/meta.json"
COOPS_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
UA = os.environ.get("USER_AGENT", "barnacle-flood-forecast (github.com/JohnUrban/barnacle)")
WALL_CLOCK_S = 25.0
PER_REQUEST_S = 8.0
LEADS = range(1, 49)
REQUIRED_KEYS = ("v", "candidate_id", "issuance_utc", "production_model_version", "status",
                 "fallback_reason", "leads", "baseline_surge_ft", "candidate_surge_ft")


def _utc(stamp):
    t = dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def _stamp(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_manifest(path=MANIFEST_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ pure parts
def select_run(issuance, latency_h, meta_init=None):
    """Latest 00/06/12/18Z cycle with init <= issuance - latency. If the live
    meta says that cycle is not yet available, the previous one."""
    t = issuance - dt.timedelta(hours=latency_h)
    init = t.replace(hour=(t.hour // 6) * 6, minute=0, second=0, microsecond=0)
    note = "latency rule"
    if meta_init is not None and meta_init < init:
        init = init - dt.timedelta(hours=6)
        note = "latency rule; that cycle not yet available per meta, previous cycle used"
    return init, note


def stress(spd_kn, dir_deg, theta_deg):
    return spd_kn * abs(spd_kn) * math.cos(math.radians(dir_deg - theta_deg))


def features(run_hours, issuance, p_obs_now, p_anom, h, theta_deg):
    """(W, dP, P_anom) for lead h, or (None, reason). run_hours: {valid_utc: (spd, dir, p)}.
    Complete window required: every hour in (t, t+h] present and finite."""
    t0 = issuance.replace(minute=0, second=0, microsecond=0)
    ws = []
    for k in range(1, h + 1):
        v = run_hours.get(t0 + dt.timedelta(hours=k))
        if v is None or any(x is None or not math.isfinite(x) for x in v):
            return None, f"incomplete wind window at lead {k} h"
        ws.append(stress(v[0], v[1], theta_deg))
    p_end = run_hours[t0 + dt.timedelta(hours=h)][2]
    if p_obs_now is None or p_anom is None:
        return None, "observed pressure unavailable"
    return (sum(ws) / len(ws), p_end - p_obs_now, p_anom), None


def correction(coefs_h, feats, cap_ft):
    b1, b2, b3, a = coefs_h
    c = b1 * feats[0] + b2 * feats[1] + b3 * feats[2] + a
    capped = abs(c) > cap_ft
    return (max(-cap_ft, min(cap_ft, c)), capped)


def baseline_surge(decay, target):
    """The production v0.10.6 formula from the forecast's water_series_input.decay."""
    mean = decay["mean_ft"]
    if decay.get("surge_obs_ft") is None or decay.get("observation_utc") is None:
        return mean
    age = (target - _utc(decay["observation_utc"])).total_seconds() / 3600.0
    if age <= 0:
        return decay["surge_obs_ft"]
    return mean + (decay["surge_obs_ft"] - mean) * math.exp(-age / decay.get("tau_h", 36.0))


def build_record(forecast, manifest, inputs, now_utc):
    """One shadow record from the production forecast and fetched inputs (dict
    with run_init, run_note, meta, run_hours, raw_sha256, raw_body,
    retrieved_utc, p_obs_now, p_obs_time, p_anom, errors)."""
    issuance = _utc(forecast["generated_utc"])
    si = forecast.get("water_series_input") or {}
    decay = si.get("decay") or {}
    t0 = issuance.replace(minute=0, second=0, microsecond=0)
    targets = [t0 + dt.timedelta(hours=h) for h in LEADS]
    base = [round(baseline_surge(decay, t), 4) if decay.get("mean_ft") is not None else None for t in targets]
    reason = None
    if not decay or decay.get("mean_ft") is None:
        reason = "production decay metadata missing"
    elif decay.get("rung") != "fresh":
        reason = f"surge reading not fresh (rung {decay.get('rung')})"
    elif inputs.get("errors"):
        reason = "; ".join(inputs["errors"])[:300]
    cand, corr, capped = list(base), [None] * len(targets), []
    if reason is None:
        for i, h in enumerate(LEADS):
            feats, why = features(inputs["run_hours"], issuance, inputs["p_obs_now"], inputs["p_anom"], h,
                                  manifest["theta_deg"])
            if feats is None:
                reason = why
                cand, corr, capped = list(base), [None] * len(targets), []
                break
            c, cap = correction(manifest["coefficients"][str(h)], feats, manifest["correction_cap_ft"])
            corr[i] = round(c, 4)
            cand[i] = round(base[i] + c, 4)
            if cap:
                capped.append(h)
    ol = (forecast.get("outlook_7d") or {}).get("series") or []
    ol_by = {}
    for p in ol:
        try:
            ol_by[_utc(p["utc"])] = p
        except (KeyError, ValueError, TypeError):
            continue
    nws = []
    for t in targets:
        p = ol_by.get(t)
        if p is None or p.get("astro_mllw") is None or p.get("tide_navd88") is None:
            nws.append(None)
            continue
        nws.append([round(p["tide_navd88"] - manifest["navd88_offset_ft"] - manifest["local_enhancement_ft"]
                          - p["astro_mllw"], 4), p.get("surge_source")])
    return {
        "v": 1, "candidate_id": manifest["candidate_id"], "manifest_sha256": manifest.get("_sha256"),
        "issuance_utc": _stamp(issuance), "written_utc": _stamp(now_utc),
        "production_model_version": forecast.get("model_version"),
        "status": "candidate" if reason is None else "fallback", "fallback_reason": reason,
        "reading": {k: decay.get(k) for k in ("rung", "surge_obs_ft", "observation_utc", "age_h", "mean_ft",
                                              "mean_source", "tau_h")},
        "run": {"init_utc": _stamp(inputs["run_init"]) if inputs.get("run_init") else None,
                "rule": inputs.get("run_note"), "meta": inputs.get("meta"),
                "retrieved_utc": inputs.get("retrieved_utc"), "raw_sha256": inputs.get("raw_sha256"),
                "raw_body": inputs.get("raw_body")},
        "pressure_obs": {"now_hpa": inputs.get("p_obs_now"), "time_utc": inputs.get("p_obs_time"),
                         "anom_30d_hpa": inputs.get("p_anom")},
        "leads": {"start": _stamp(targets[0]), "step_h": 1, "n": len(targets)},
        "baseline_surge_ft": base, "candidate_surge_ft": cand, "correction_ft": corr,
        "capped_leads": capped, "nws_outlook_surge": nws,
    }


# ------------------------------------------------------------------ network parts
def _get(url, params, timeout):
    req = urllib.request.Request(url + ("?" + urllib.parse.urlencode(params) if params else ""),
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_inputs(issuance, manifest, get=_get):
    out = {"errors": []}
    meta_init = None
    try:
        meta = json.loads(get(META_URL, None, PER_REQUEST_S))
        meta_init = dt.datetime.fromtimestamp(meta["last_run_initialisation_time"], dt.timezone.utc)
        out["meta"] = {k: meta.get(k) for k in ("last_run_initialisation_time", "last_run_availability_time",
                                                "last_run_modification_time")}
    except Exception as e:  # noqa: BLE001
        out["meta"] = None
        out["errors"].append(f"meta unavailable ({type(e).__name__})")
    init, note = select_run(issuance, manifest["latency_h"], meta_init)
    out["run_init"], out["run_note"] = init, note
    try:
        body = get(SINGLE_RUNS_URL, {"latitude": manifest["latitude"], "longitude": manifest["longitude"],
                                      "hourly": "wind_speed_10m,wind_direction_10m,pressure_msl",
                                      "models": manifest["model"], "run": init.strftime("%Y-%m-%dT%H:%M"),
                                      "forecast_hours": manifest["forecast_hours"], "wind_speed_unit": "kn",
                                      "timezone": "GMT"}, PER_REQUEST_S)
        out["retrieved_utc"] = _stamp(dt.datetime.now(dt.timezone.utc))
        out["raw_sha256"] = hashlib.sha256(body).hexdigest()
        out["raw_body"] = body.decode("utf-8")
        d = json.loads(body)
        if d.get("error"):
            raise ValueError(d.get("reason", "error"))
        h = d["hourly"]
        out["run_hours"] = {_utc(t + "Z"): (h["wind_speed_10m"][i], h["wind_direction_10m"][i], h["pressure_msl"][i])
                            for i, t in enumerate(h["time"])}
    except Exception as e:  # noqa: BLE001
        out["run_hours"] = {}
        out["errors"].append(f"single run {init:%Y-%m-%dT%HZ} unavailable ({type(e).__name__}: {str(e)[:80]})")
    try:
        def pressure_rows(begin, end, hourly):
            q = {"product": "air_pressure", "station": "8531680", "begin_date": begin.strftime("%Y%m%d %H:%M"),
                 "end_date": end.strftime("%Y%m%d %H:%M"), "time_zone": "gmt", "units": "metric",
                 "format": "json", "application": "barnacle-wind-shadow"}
            if hourly:
                q["interval"] = "h"
            js = json.loads(get(COOPS_URL, q, PER_REQUEST_S))
            rows = [(_utc(r["t"].replace(" ", "T") + "Z"), float(r["v"])) for r in js.get("data") or []
                    if r.get("v") not in (None, "")]
            return [(t, v) for t, v in rows if math.isfinite(v)]
        t0 = issuance.replace(minute=0, second=0, microsecond=0)
        # the issuance-hour value from the 6-min product (the hourly product's
        # top-of-hour value is published minutes later than the run needs it)
        six = pressure_rows(t0 - dt.timedelta(hours=1), issuance, hourly=False)
        at_t0 = [v for t, v in six if t == t0]
        if at_t0:
            t_last, p_last = t0, at_t0[0]
        elif six:
            t_last, p_last = six[-1]
        else:
            raise ValueError("no recent 6-min pressure")
        if (issuance - t_last).total_seconds() > 3600:
            raise ValueError(f"latest pressure {t_last:%H:%MZ} older than 60 min")
        prior = [v for t, v in pressure_rows(issuance - dt.timedelta(days=31), issuance, hourly=True)
                 if issuance - dt.timedelta(days=30) <= t < t0]
        if len(prior) < 24 * 20:
            raise ValueError(f"only {len(prior)} h of pressure history")
        out["p_obs_now"], out["p_obs_time"] = p_last, _stamp(t_last)
        out["p_anom"] = round(p_last - sum(prior) / len(prior), 3)
    except Exception as e:  # noqa: BLE001
        out["p_obs_now"] = out["p_anom"] = out["p_obs_time"] = None
        out["errors"].append(f"observed pressure unavailable ({type(e).__name__}: {str(e)[:80]})")
    return out


def append_record(record, directory=SHADOW_DIR):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{record['issuance_utc'][:7]}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":"), sort_keys=True, allow_nan=False) + "\n")
    return path


def validate_file(path):
    bad, last = [], ""
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            try:
                r = json.loads(line, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
            except ValueError as e:
                bad.append(f"line {i}: not strict JSON ({e})")
                continue
            miss = [k for k in REQUIRED_KEYS if k not in r]
            if miss:
                bad.append(f"line {i}: missing {miss}")
            if r.get("status") not in ("candidate", "fallback", "error"):
                bad.append(f"line {i}: bad status {r.get('status')!r}")
            if r.get("status") != "candidate" and not r.get("fallback_reason"):
                bad.append(f"line {i}: non-candidate record without a reason")
            g = str(r.get("issuance_utc") or "")
            if g < last:
                bad.append(f"line {i}: issuance before the previous line")
            last = max(last, g)
    return bad


def run(forecast, now_utc=None, manifest_path=MANIFEST_PATH, directory=SHADOW_DIR, get=_get,
        wall_clock_s=WALL_CLOCK_S):
    """Hook for main(): never raises; returns a short status string. The work
    runs in a daemon thread joined for at most wall_clock_s; if it does not
    finish, an 'error' record saying so is appended instead."""
    now_utc = now_utc or dt.datetime.now(dt.timezone.utc)
    box = {}

    def work():
        try:
            with open(manifest_path, "rb") as fh:
                raw = fh.read()
            manifest = json.loads(raw)
            manifest["_sha256"] = hashlib.sha256(raw).hexdigest()
            box["manifest"] = manifest
            inputs = fetch_inputs(_utc(forecast["generated_utc"]), manifest, get=get)
            box["record"] = build_record(forecast, manifest, inputs, now_utc)
        except Exception as e:  # noqa: BLE001
            box["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    th = threading.Thread(target=work, name="wind-shadow", daemon=True)
    th.start()
    th.join(wall_clock_s)
    try:
        if "record" in box and not th.is_alive():
            rec = box["record"]
        else:
            why = box.get("error") or f"wall-clock limit {wall_clock_s:.0f} s exceeded"
            rec = {"v": 1, "candidate_id": (box.get("manifest") or {}).get("candidate_id"),
                   "issuance_utc": str(forecast.get("generated_utc")), "written_utc": _stamp(now_utc),
                   "production_model_version": forecast.get("model_version"), "status": "error",
                   "fallback_reason": why, "leads": None, "baseline_surge_ft": None, "candidate_surge_ft": None}
        append_record(rec, directory)
        return f"wind shadow: {rec['status']}" + (f" ({rec['fallback_reason']})" if rec.get("fallback_reason") else "")
    except Exception as e:  # noqa: BLE001
        return f"wind shadow: not written ({type(e).__name__})"
