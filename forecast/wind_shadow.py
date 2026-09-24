"""Wind-shadow candidate c2 (SHADOW ONLY). Plan
history/plans/2026-09-24-wind-term-candidate-plan.md; design
models/wind_shadow/DESIGN.md; frozen parameters models/wind_shadow/manifest.json;
freeze table models/wind_shadow/FREEZE.md; review audits/2026-09-24-a3.

After every production output and the alert path, compute the candidate
surge (frozen v0.10.6 decay + a forecast wind/pressure correction) for leads
1..48 h and append ONE validated record. Nothing the forecast publishes,
displays or alerts on changes. Collection is OPT-IN (a3 R8):
  BARNACLE_WIND_SHADOW_TRIAL=1        official trial log data/wind_shadow/
                                      (set only by the production workflow)
  BARNACLE_WIND_SHADOW_PREVIEW_DIR=D  non-official preview records in D
  neither                             nothing runs, nothing is fetched
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

try:
    from .station_time import parse_station_local_time
except ImportError:                          # run as a script from forecast/
    from station_time import parse_station_local_time

CANDIDATE_ID = "wind-shadow-c2"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(ROOT, "models", "wind_shadow", "manifest.json")
TRIAL_DIR = os.path.join(ROOT, "data", "wind_shadow")
SINGLE_RUNS_URL = "https://single-runs-api.open-meteo.com/v1/forecast"
META_URL = "https://api.open-meteo.com/data/ncep_gfs013/static/meta.json"
COOPS_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
UA = os.environ.get("USER_AGENT", "barnacle-flood-forecast (github.com/JohnUrban/barnacle)")
WALL_CLOCK_S = 25.0
PER_REQUEST_S = 8.0
NLEADS = 48
MAX_RUN_AGE_H = 12          # by construction the 6-h rule gives 6..11 h; enforced anyway
MAX_PRESSURE_AGE_MIN = 60
MIN_PRESSURE_HOURS = 480    # of the 720 hourly values in [t0 - 30 d, t0)
STATUSES = ("candidate", "fallback", "error")
REQUIRED_KEYS = ("v", "candidate_id", "manifest_sha256", "runtime_sha256", "collection", "issuance_utc",
                 "production_model_version", "status", "fallback_reason", "leads", "baseline_surge_ft",
                 "candidate_surge_ft")


def _utc(stamp):
    t = dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def _stamp(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def runtime_sha256():
    with open(os.path.abspath(__file__), "rb") as f:
        return _sha(f.read())


def load_manifest(path=MANIFEST_PATH):
    with open(path, "rb") as f:
        raw = f.read()
    m = json.loads(raw)
    m["_sha256"] = _sha(raw)
    return m


# ------------------------------------------------------------------ pure parts
def cycle_for(issuance, latency_h):
    t = issuance - dt.timedelta(hours=latency_h)
    return t.replace(hour=(t.hour // 6) * 6, minute=0, second=0, microsecond=0)


def select_run(issuance, latency_h, meta_init=None, meta_available=None):
    """(init, None) or (None, reason). The rule-selected cycle is used ONLY if
    the provider's metadata confirms it was available by the issuance time;
    no older substitute is used, so live construction equals training (a3 R5)."""
    init = cycle_for(issuance, latency_h)
    if (issuance - init).total_seconds() / 3600 > MAX_RUN_AGE_H:
        return None, f"selected run older than {MAX_RUN_AGE_H} h"
    if meta_init is None:
        return None, "run availability unconfirmed (no provider metadata)"
    if meta_init < init:
        return None, f"run {init:%Y-%m-%dT%HZ} not yet available (latest confirmed {meta_init:%Y-%m-%dT%HZ})"
    if meta_init == init and (meta_available is None or meta_available > issuance):
        return None, f"run {init:%Y-%m-%dT%HZ} became available after the issuance time"
    return init, None


def stress(spd_kn, dir_deg, theta_deg):
    return spd_kn * abs(spd_kn) * math.cos(math.radians(dir_deg - theta_deg))


def features(run_hours, t0, p_obs_now, p_anom, h, theta_deg):
    """(W, dP, P_anom) for nominal lead h from the issuance HOUR t0, or (None, reason).
    Complete window required: every hour in (t0, t0+h] present and finite."""
    ws = []
    for k in range(1, h + 1):
        v = run_hours.get(t0 + dt.timedelta(hours=k))
        if v is None or any(x is None or not math.isfinite(x) for x in v):
            return None, f"incomplete wind window at lead {k} h"
        ws.append(stress(v[0], v[1], theta_deg))
    if p_obs_now is None or p_anom is None:
        return None, "observed pressure unavailable"
    return (sum(ws) / len(ws), run_hours[t0 + dt.timedelta(hours=h)][2] - p_obs_now, p_anom), None


def correction(coefs_h, feats, cap_ft):
    b1, b2, b3, a = coefs_h
    c = b1 * feats[0] + b2 * feats[1] + b3 * feats[2] + a
    return (max(-cap_ft, min(cap_ft, c)), abs(c) > cap_ft)


def frozen_baseline(decay, target, tau_h):
    """v0.10.6 decay with the FROZEN time constant (a3 R6); the reading and the
    mean are the production run's reported inputs."""
    mean = decay["mean_ft"]
    if decay.get("surge_obs_ft") is None or decay.get("observation_utc") is None:
        return mean
    age = (target - _utc(decay["observation_utc"])).total_seconds() / 3600.0
    if age <= 0:
        return decay["surge_obs_ft"]
    return mean + (decay["surge_obs_ft"] - mean) * math.exp(-age / tau_h)


def pre_network_part(forecast, manifest, collection, now_utc):
    """Everything computable WITHOUT the network (a3 R2): identity, frozen
    baseline, the actual production curve and the NWS/P-ETSS comparator."""
    issuance = _utc(forecast["generated_utc"])
    t0 = issuance.replace(minute=0, second=0, microsecond=0)
    targets = [t0 + dt.timedelta(hours=h) for h in range(1, NLEADS + 1)]
    decay = ((forecast.get("water_series_input") or {}).get("decay")) or {}
    base = ([round(frozen_baseline(decay, t, manifest["tau_h"]), 4) for t in targets]
            if decay.get("mean_ft") is not None else None)
    ws_by = {}
    for p in forecast.get("water_series") or []:
        try:
            ws_by[parse_station_local_time(p["time"]).astimezone(dt.timezone.utc)] = p.get("tide_navd88")
        except (KeyError, TypeError, ValueError):
            continue
    prod = [(round(ws_by[t], 4) if ws_by.get(t) is not None else None) for t in targets]
    ol_by = {}
    for p in (forecast.get("outlook_7d") or {}).get("series") or []:
        try:
            ol_by[_utc(p["utc"])] = p
        except (KeyError, TypeError, ValueError):
            continue
    nws = []
    for t in targets:
        p = ol_by.get(t)
        if p is None or p.get("astro_mllw") is None or p.get("tide_navd88") is None:
            nws.append(None)
        else:
            nws.append([round(p["tide_navd88"] - manifest["navd88_offset_ft"] - manifest["local_enhancement_ft"]
                              - p["astro_mllw"], 4), p.get("surge_source")])
    return {
        "v": 2, "candidate_id": manifest["candidate_id"], "manifest_sha256": manifest["_sha256"],
        "runtime_sha256": runtime_sha256(), "collection": collection,
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "issuance_utc": _stamp(issuance), "nominal_issuance_hour_utc": _stamp(t0),
        "written_utc": _stamp(now_utc), "production_model_version": forecast.get("model_version"),
        "reading": {k: decay.get(k) for k in ("rung", "surge_obs_ft", "observation_utc", "age_h",
                                              "mean_ft", "mean_source", "tau_h")},
        "leads": {"start": _stamp(targets[0]), "step_h": 1, "n": NLEADS},
        "baseline_surge_ft": base, "candidate_surge_ft": list(base) if base else None,
        "correction_ft": [None] * NLEADS, "capped_leads": [],
        "production_curve_tide_navd88": prod, "nws_outlook_surge": nws,
        "status": "fallback" if base else "error",
        "fallback_reason": None if base else "production decay metadata missing: no baseline",
    }


def complete_record(rec, forecast, manifest, inputs):
    """Fill the candidate from fetched inputs, or keep the baseline with a reason."""
    rec["inputs_fetched_utc"] = inputs.get("fetched_utc")
    rec["run"] = {k: inputs.get(k) for k in ("init_utc", "selection", "meta", "retrieved_utc", "raw_sha256", "raw_body")}
    rec["pressure_obs"] = inputs.get("pressure")
    if rec["baseline_surge_ft"] is None:
        return rec
    decay = rec["reading"]
    reasons = []
    if decay.get("rung") != "fresh":
        reasons.append(f"surge reading not fresh (rung {decay.get('rung')})")
    reasons += inputs.get("errors") or []
    if not reasons:
        t0 = _utc(rec["nominal_issuance_hour_utc"])
        p = inputs["pressure"]
        corr, cand, capped = [], [], []
        for h in range(1, NLEADS + 1):
            f, why = features(inputs["run_hours"], t0, p["now_hpa"], p["anom_30d_hpa"], h, manifest["theta_deg"])
            if f is None:
                reasons.append(why)
                break
            c, cap = correction(manifest["coefficients"][str(h)], f, manifest["correction_cap_ft"])
            corr.append(round(c, 4)); cand.append(round(rec["baseline_surge_ft"][h - 1] + c, 4))
            if cap:
                capped.append(h)
        if not reasons:
            rec.update(status="candidate", fallback_reason=None, correction_ft=corr,
                       candidate_surge_ft=cand, capped_leads=capped)
            return rec
    rec.update(status="fallback", fallback_reason="; ".join(reasons)[:400])
    return rec


# ------------------------------------------------------------------ network parts
def _get(url, params, timeout):
    req = urllib.request.Request(url + ("?" + urllib.parse.urlencode(params) if params else ""),
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _pressure_rows(body):
    """[(t, hPa)] of rows with a finite value and ALL quality flags 0; plus counts."""
    js = json.loads(body)
    ok, rejected = [], 0
    for r in js.get("data") or []:
        try:
            v = float(r["v"])
            flags = [int(x) for x in str(r["f"]).split(",")]
            if len(flags) != 3 or any(flags) or not math.isfinite(v):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            rejected += 1
            continue
        ok.append((_utc(r["t"].replace(" ", "T") + "Z"), v))
    return ok, rejected


def fetch_inputs(issuance, manifest, get=_get):
    out = {"errors": [], "fetched_utc": _stamp(dt.datetime.now(dt.timezone.utc))}
    t0 = issuance.replace(minute=0, second=0, microsecond=0)
    meta_init = meta_avail = None
    try:
        meta = json.loads(get(META_URL, None, PER_REQUEST_S))
        meta_init = dt.datetime.fromtimestamp(meta["last_run_initialisation_time"], dt.timezone.utc)
        meta_avail = dt.datetime.fromtimestamp(meta["last_run_availability_time"], dt.timezone.utc)
        out["meta"] = {k: meta.get(k) for k in ("last_run_initialisation_time", "last_run_availability_time",
                                                "last_run_modification_time")}
    except Exception as e:  # noqa: BLE001
        out["meta"] = None
    init, why = select_run(issuance, manifest["latency_h"], meta_init, meta_avail)
    out["selection"] = why or "6-h rule, confirmed available by issuance"
    out["init_utc"] = _stamp(init) if init else None
    out["run_hours"] = {}
    if init is None:
        out["errors"].append(why)
    else:
        try:
            body = get(SINGLE_RUNS_URL, {"latitude": manifest["latitude"], "longitude": manifest["longitude"],
                                          "hourly": "wind_speed_10m,wind_direction_10m,pressure_msl",
                                          "models": manifest["model"], "run": init.strftime("%Y-%m-%dT%H:%M"),
                                          "forecast_hours": manifest["forecast_hours"], "wind_speed_unit": "kn",
                                          "timezone": "GMT"}, PER_REQUEST_S)
            out["retrieved_utc"] = _stamp(dt.datetime.now(dt.timezone.utc))
            out["raw_sha256"], out["raw_body"] = _sha(body), body.decode("utf-8")
            d = json.loads(body)
            if d.get("error"):
                raise ValueError(d.get("reason", "error"))
            h = d["hourly"]
            out["run_hours"] = {_utc(t + "Z"): (h["wind_speed_10m"][i], h["wind_direction_10m"][i], h["pressure_msl"][i])
                                for i, t in enumerate(h["time"])}
        except Exception as e:  # noqa: BLE001
            out["errors"].append(f"single run {init:%Y-%m-%dT%HZ} unavailable ({type(e).__name__}: {str(e)[:80]})")
    p = {"basis": None, "now_hpa": None, "time_utc": None, "anom_30d_hpa": None, "responses": []}
    out["pressure"] = p
    try:
        def fetch(begin, end, hourly):
            q = {"product": "air_pressure", "station": "8531680", "begin_date": begin.strftime("%Y%m%d %H:%M"),
                 "end_date": end.strftime("%Y%m%d %H:%M"), "time_zone": "gmt", "units": "metric",
                 "format": "json", "application": "barnacle-wind-shadow"}
            if hourly:
                q["interval"] = "h"
            body = get(COOPS_URL, q, PER_REQUEST_S)
            rows, rejected = _pressure_rows(body)
            resp = {"query": {k: q[k] for k in ("begin_date", "end_date")} | {"interval": q.get("interval")},
                    "retrieved_utc": _stamp(dt.datetime.now(dt.timezone.utc)), "sha256": _sha(body),
                    "rows_used": len(rows), "rows_rejected_qc": rejected}
            if hourly:
                # the 31-day series: the QC-passing values actually used, hourly from
                # their first time (None = absent or rejected); the raw body's hash is kept
                if rows:
                    t_first, by = rows[0][0], dict(rows)
                    n = int((rows[-1][0] - t_first).total_seconds() // 3600) + 1
                    resp["values_hpa"] = {"start": _stamp(t_first), "step_h": 1,
                                          "values": [by.get(t_first + dt.timedelta(hours=i)) for i in range(n)]}
            else:
                resp["body"] = body.decode("utf-8")            # small: the last hour of 6-min values
            p["responses"].append(resp)
            return rows
        six = fetch(t0 - dt.timedelta(hours=1), issuance, hourly=False)
        at_t0 = [v for t, v in six if t == t0]
        if at_t0:
            p.update(basis="value at the issuance hour", now_hpa=at_t0[0], time_utc=_stamp(t0))
        elif six:
            p.update(basis="latest 6-min value (issuance-hour value not yet published)", now_hpa=six[-1][1],
                     time_utc=_stamp(six[-1][0]))
        if p["now_hpa"] is None or (issuance - _utc(p["time_utc"])).total_seconds() > MAX_PRESSURE_AGE_MIN * 60:
            raise ValueError("no QC-passing pressure within 60 min")
        prior = [v for t, v in fetch(t0 - dt.timedelta(days=31), issuance, hourly=True)
                 if t0 - dt.timedelta(days=30) <= t < t0]
        p["prior_hours"] = len(prior)
        if len(prior) < MIN_PRESSURE_HOURS:
            raise ValueError(f"only {len(prior)} QC-passing hourly values in [t0 - 30 d, t0)")
        p["anom_30d_hpa"] = round(p["now_hpa"] - sum(prior) / len(prior), 3)
    except Exception as e:  # noqa: BLE001
        p["anom_30d_hpa"] = None
        out["errors"].append(f"observed pressure unavailable ({type(e).__name__}: {str(e)[:100]})")
    return out


def validate_record(r):
    bad = [f"missing {k}" for k in REQUIRED_KEYS if k not in r]
    if r.get("status") not in STATUSES:
        bad.append(f"bad status {r.get('status')!r}")
    if r.get("status") != "candidate" and not r.get("fallback_reason"):
        bad.append("non-candidate record without a reason")
    if r.get("status") in ("candidate", "fallback"):
        for k in ("baseline_surge_ft", "candidate_surge_ft"):
            arr = r.get(k)
            if not isinstance(arr, list) or len(arr) != NLEADS or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in arr):
                bad.append(f"{k} must hold {NLEADS} finite values")
    try:
        json.dumps(r, allow_nan=False)
    except ValueError as e:
        bad.append(f"not strict JSON ({e})")
    return bad


def append_record(record, directory):
    """Validate in memory, then append the complete line with ONE write on an
    O_APPEND descriptor; an invalid record goes to quarantine/ (a3 R7)."""
    bad = validate_record(record)
    target = os.path.join(directory, "quarantine" if bad else "", f"{record.get('issuance_utc', 'unknown')[:7]}.jsonl")
    if bad:
        record = dict(record, quarantine_reasons=bad)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    line = (json.dumps(record, separators=(",", ":"), sort_keys=True, default=str) + "\n").encode("utf-8")
    fd = os.open(target, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)
    return target, bad


def validate_file(path):
    bad, last = [], ""
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            try:
                r = json.loads(line, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
            except ValueError as e:
                bad.append(f"line {i}: not strict JSON ({e})")
                continue
            bad += [f"line {i}: {b}" for b in validate_record(r)]
            g = str(r.get("issuance_utc") or "")
            if g < last:
                bad.append(f"line {i}: issuance before the previous line")
            last = max(last, g)
    return bad


def collection_target():
    """('official', TRIAL_DIR) | ('preview', dir) | (None, None)  (a3 R8)."""
    if os.environ.get("BARNACLE_WIND_SHADOW_TRIAL") == "1":
        return "official", TRIAL_DIR
    d = os.environ.get("BARNACLE_WIND_SHADOW_PREVIEW_DIR")
    if d:
        return "preview", d
    return None, None


def run(forecast, now_utc=None, manifest_path=MANIFEST_PATH, collection=None, directory=None, get=_get,
        wall_clock_s=WALL_CLOCK_S):
    """Never raises; returns a status string. The frozen baseline is built
    first; the network part runs in a daemon thread joined for wall_clock_s;
    on timeout the record keeps the baseline with the reason (a3 R2)."""
    if collection is None:
        collection, directory = collection_target()
    if collection is None:
        return "wind shadow: not collected (no opt-in)"
    now_utc = now_utc or dt.datetime.now(dt.timezone.utc)
    try:
        manifest = load_manifest(manifest_path)
        if manifest.get("candidate_id") != CANDIDATE_ID:
            raise ValueError(f"manifest id {manifest.get('candidate_id')!r} != runtime {CANDIDATE_ID!r}")
        rec = pre_network_part(forecast, manifest, collection, now_utc)
    except Exception as e:  # noqa: BLE001
        rec = {"v": 2, "candidate_id": CANDIDATE_ID, "manifest_sha256": None, "runtime_sha256": runtime_sha256(),
               "collection": collection, "issuance_utc": str(forecast.get("generated_utc")),
               "written_utc": _stamp(now_utc), "production_model_version": forecast.get("model_version"),
               "status": "error", "fallback_reason": f"record setup failed ({type(e).__name__}: {str(e)[:200]})",
               "leads": None, "baseline_surge_ft": None, "candidate_surge_ft": None}
        try:
            append_record(rec, directory)
        except Exception:  # noqa: BLE001
            pass
        return "wind shadow: error (setup)"
    box = {}

    def work():
        try:
            box["inputs"] = fetch_inputs(_utc(forecast["generated_utc"]), manifest, get=get)
        except Exception as e:  # noqa: BLE001
            box["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    th = threading.Thread(target=work, name="wind-shadow", daemon=True)
    th.start()
    th.join(wall_clock_s)
    try:
        if "inputs" in box and not th.is_alive():
            rec = complete_record(rec, forecast, manifest, box["inputs"])
        elif rec["baseline_surge_ft"] is not None:
            rec.update(status="fallback", fallback_reason=(box.get("error")
                       or f"inputs not fetched within the {wall_clock_s:g}-s wall clock"))
        path, bad = append_record(rec, directory)
        return f"wind shadow: {rec['status']}" + (f" ({rec['fallback_reason']})" if rec.get("fallback_reason") else "") \
            + (f" QUARANTINED: {bad}" if bad else "")
    except Exception as e:  # noqa: BLE001
        return f"wind shadow: not written ({type(e).__name__})"
