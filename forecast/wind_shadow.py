"""Wind-shadow candidate c2 (SHADOW ONLY). Plan
history/plans/2026-09-24-wind-term-candidate-plan.md; design
models/wind_shadow/DESIGN.md; frozen parameters models/wind_shadow/manifest.json;
freeze table models/wind_shadow/FREEZE.md; review audits/2026-09-24-a3
(rounds 01-04).

After every production output and the alert path, compute the candidate
surge (frozen v0.10.6 decay + a forecast wind/pressure correction) for leads
1..48 h and append ONE validated record. Nothing the forecast publishes,
displays or alerts on changes. Collection is OPT-IN (a3 R8):
  BARNACLE_WIND_SHADOW_TRIAL=1        official trial log data/wind_shadow/
                                      (set only by the production workflow),
                                      NEVER for --no-send/--dry-run runs or an
                                      unknown execution mode
  BARNACLE_WIND_SHADOW_PREVIEW_DIR=D  non-official preview records in D
  neither                             nothing runs, nothing is fetched
Before an OFFICIAL record the frozen bundle (FREEZE.md: every file's SHA-256,
including the manifest actually loaded and this runtime) is verified; a
mismatch writes a 'disabled' record with the reason and fetches nothing
(a3 round 03, R6). Production is never affected.
"""
from __future__ import annotations

import base64
import datetime as dt
import gzip
import hashlib
import json
import math
import os
import re
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
FREEZE_PATH = os.path.join(ROOT, "models", "wind_shadow", "FREEZE.md")
MANIFEST_REL = "models/wind_shadow/manifest.json"
RUNTIME_REL = "forecast/wind_shadow.py"
REQUIRED_BUNDLE = (MANIFEST_REL, "models/wind_shadow/DESIGN.md", RUNTIME_REL,
                   "history/scripts/evaluate_wind_shadow.py", "history/scripts/fit_wind_shadow_c2.py",
                   "models/wind_shadow/rain_ref.py", "models/wind_shadow/stage_storage_curve.csv")
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
STATUSES = ("candidate", "fallback", "error", "disabled")
REQUIRED_KEYS = ("v", "candidate_id", "manifest_sha256", "runtime_sha256", "bundle_sha256", "collection", "issuance_utc",
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


def read_freeze(path=FREEZE_PATH):
    """(frozen candidate_id, {repo-relative path: sha256}) from FREEZE.md."""
    cid, table = None, {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|", line)
            if m:
                table[m.group(1)] = m.group(2)
            m = re.match(r"^frozen_candidate_id:\s*`([^`]+)`", line)
            if m:
                cid = m.group(1)
    return cid, table


def bundle_sha256(cid, table):
    """Identity of a frozen bundle: SHA-256 of the canonical (id, sorted path/hash) text."""
    canon = f"candidate_id {cid}\n" + "".join(f"{k} {table[k]}\n" for k in sorted(table))
    return _sha(canon.encode("utf-8"))


def check_bundle(root=ROOT, freeze_path=None):
    """Hash every FREEZE-listed file NOW: {ok, bundle_sha256, table, problems}."""
    try:
        cid, table = read_freeze(freeze_path or os.path.join(root, "models", "wind_shadow", "FREEZE.md"))
    except (OSError, UnicodeDecodeError) as e:
        return {"ok": False, "bundle_sha256": None, "table": {}, "problems": [f"FREEZE.md unreadable ({e})"]}
    problems = []
    if cid != CANDIDATE_ID:
        problems.append(f"FREEZE candidate {cid!r} != runtime {CANDIDATE_ID!r}")
    problems += [f"{rel} not in the FREEZE table" for rel in REQUIRED_BUNDLE if rel not in table]
    for rel, want in sorted(table.items()):
        try:
            with open(os.path.join(root, rel), "rb") as f:
                got = _sha(f.read())
        except OSError:
            problems.append(f"{rel} unreadable")
            continue
        if got != want:
            problems.append(f"{rel} sha256 {got[:12]} != frozen {want[:12]}")
    return {"ok": not problems, "bundle_sha256": bundle_sha256(cid, table) if table else None,
            "table": table, "problems": problems}


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
    the provider's metadata establishes it was available by the issuance time:
    either the metadata's latest run IS the selected run and was available by
    issuance, or a NEWER run was already available by issuance (cycles are
    published in order: a declared assumption). Otherwise fallback; no older
    substitute is used, so live construction equals training (a3 R5)."""
    init = cycle_for(issuance, latency_h)
    if (issuance - init).total_seconds() / 3600 > MAX_RUN_AGE_H:
        return None, f"selected run older than {MAX_RUN_AGE_H} h"
    if meta_init is None:
        return None, "run availability unconfirmed (no provider metadata)"
    if meta_init < init:
        return None, f"run {init:%Y-%m-%dT%HZ} not yet available (latest confirmed {meta_init:%Y-%m-%dT%HZ})"
    if meta_available is None or meta_available > issuance:
        if meta_init == init:
            return None, f"run {init:%Y-%m-%dT%HZ} became available after the issuance time"
        return None, (f"availability of run {init:%Y-%m-%dT%HZ} by issuance not established "
                      f"(metadata shows only the newer {meta_init:%Y-%m-%dT%HZ}, available after issuance)")
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


def _hour(t):
    return t.replace(minute=0, second=0, microsecond=0)


def _guidance(targets, context):
    """As-issued RAW external guidance per target, kept apart from Barnacle's
    blended outlook (a3 round 03, R3): NWPS gauge forecast minus hourly
    astronomy (no advisory correction) and the P-ETSS hourly mid ((p10+p90)/2),
    with issue/retrieval provenance; None where that guidance did not cover
    the target at issuance."""
    od = (context or {}).get("outlook_data") or {}
    oh = (context or {}).get("outlook_health") or {}
    astro = {}
    for q in ((od.get("astro_hourly") or {}).get("points") or []):
        try:
            astro[_hour(_utc(q["utc"]))] = float(q["mllw"])
        except (KeyError, TypeError, ValueError):
            continue
    out = {}
    nw = od.get("nwps") or {}
    by = {}
    for q in nw.get("series") or []:
        try:
            by[_hour(_utc(q["utc"]))] = float(q["ft"])
        except (KeyError, TypeError, ValueError):
            continue
    vals = [(round(by[t] - astro[t], 4) if t in by and t in astro else None) for t in targets]
    out["nwps_raw"] = {"issued": nw.get("issued"), "retrieved": (oh.get("nwps") or {}).get("fetched_at"),
                       "surge_ft": vals, "reason": None if any(v is not None for v in vals) else
                       ((oh.get("nwps") or {}).get("detail") or ("no hourly astronomy" if by else "not available at issuance"))}
    pe = od.get("petss") or {}
    lo, hi = {}, {}
    for key, dst in (("p10", lo), ("p90", hi)):
        for q in pe.get(key) or []:
            try:
                dst[_hour(_utc(q["utc"]))] = float(q["surge_ft"])
            except (KeyError, TypeError, ValueError):
                continue
    vals = [(round((lo[t] + hi[t]) / 2.0, 4) if t in lo and t in hi else None) for t in targets]
    out["petss_mid"] = {"cycle": pe.get("cycle"), "retrieved": (oh.get("petss") or {}).get("fetched_at"),
                        "surge_ft": vals, "reason": None if any(v is not None for v in vals) else
                        ((oh.get("petss") or {}).get("detail") or "not available at issuance")}
    return out


def _rain_inputs(forecast, decay, manifest, issuance, context):
    """The production tank's AS-ISSUED initial condition and forcing (a3 round
    03, R3): its 30-min series from the series start (storage empty there, as
    production), the bay it used, the surge it used per point (reconstructed
    from the reported decay, which is exactly production's formula), the QPF
    rate per point with production's hour lookup (missing hour = 0.0; QPF
    unavailable = no tank), and production's pluvial line for a check. The
    frozen-baseline surge per point is stored for points AFTER issuance; points
    at or before issuance are the shared history (None)."""
    pts = []
    for q in forecast.get("water_series") or []:
        try:
            pts.append((parse_station_local_time(q["time"]).astimezone(dt.timezone.utc), q))
        except (KeyError, TypeError, ValueError):
            continue
    if len(pts) < 2 or decay.get("mean_ft") is None or decay.get("tau_h") is None:
        return {"reason": "no production water series or decay metadata"}
    pts.sort(key=lambda x: x[0])
    times = [t for t, _q in pts]
    qpf = (context or {}).get("qpf_hourly")
    rates, qreason = None, "production QPF unavailable at issuance (production drew no tank)"
    if qpf is not None:
        by = {}
        for tt, r in qpf:
            try:
                by[_hour(tt.astimezone(dt.timezone.utc))] = float(r)
            except (AttributeError, TypeError, ValueError):
                continue
        rates, qreason = [round(by.get(_hour(t), 0.0), 4) for t in times], None
    steps = {(b - a).total_seconds() for a, b in zip(times, times[1:])}
    out = {"series_start": _stamp(times[0]), "tank_init": "empty storage at series start (production)",
           "issuance_utc": _stamp(issuance),
           "production_tide_navd88": [q.get("tide_navd88") for _t, q in pts],
           "production_pluvial_navd88": [q.get("pluvial_navd88") for _t, q in pts],
           "production_surge_ft": [round(frozen_baseline(decay, t, decay["tau_h"]), 4) for t in times],
           "baseline_surge_ft": [(round(frozen_baseline(decay, t, manifest["tau_h"]), 4) if t > issuance else None)
                                 for t in times],
           "candidate_surge_ft": None, "qpf_in_hr": rates, "qpf_reason": qreason}
    if steps == {1800.0}:
        out["step_min"] = 30
    else:
        out["times"] = [_stamp(t) for t in times]
    return out


def rain_times(ri):
    if "times" in ri:
        return [_utc(t) for t in ri["times"]]
    t0 = _utc(ri["series_start"])
    return [t0 + dt.timedelta(minutes=ri["step_min"] * i) for i in range(len(ri["production_tide_navd88"]))]


def correction_at(corr, t0, t):
    """Correction at any time after issuance: linear between whole-hour leads,
    the lead-1 value before t0 + 1 h, none beyond the last lead."""
    x = (t - t0).total_seconds() / 3600.0
    if x <= 1:
        return corr[0]
    if x > len(corr):
        return 0.0
    k = int(x)
    if k >= len(corr):
        return corr[-1]
    return corr[k - 1] + (x - k) * (corr[k] - corr[k - 1])


def pre_network_part(forecast, manifest, collection, now_utc, context=None, bundle=None):
    """Everything computable WITHOUT the network (a3 R2): identity, frozen
    baseline, the actual production curve, raw external guidance, Barnacle's
    outlook (its own comparator) and the tank's as-issued inputs."""
    issuance = _utc(forecast["generated_utc"])
    t0 = _hour(issuance)
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
    outlook = []
    for t in targets:
        p = ol_by.get(t)
        if p is None or p.get("astro_mllw") is None or p.get("tide_navd88") is None:
            outlook.append(None)
        else:
            outlook.append([round(p["tide_navd88"] - manifest["navd88_offset_ft"] - manifest["local_enhancement_ft"]
                                  - p["astro_mllw"], 4), p.get("surge_source")])
    bundle = bundle or {}
    return {
        "v": 3, "candidate_id": manifest["candidate_id"], "manifest_sha256": manifest["_sha256"],
        "runtime_sha256": runtime_sha256(), "bundle_sha256": bundle.get("bundle_sha256"),
        "bundle_ok": bundle.get("ok"), "bundle_problems": bundle.get("problems") or [],
        "collection": collection, "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "issuance_utc": _stamp(issuance), "nominal_issuance_hour_utc": _stamp(t0),
        "written_utc": _stamp(now_utc), "production_model_version": forecast.get("model_version"),
        "reading": {k: decay.get(k) for k in ("rung", "surge_obs_ft", "observation_utc", "age_h",
                                              "mean_ft", "mean_source", "tau_h")},
        "leads": {"start": _stamp(targets[0]), "step_h": 1, "n": NLEADS},
        "baseline_surge_ft": base, "candidate_surge_ft": list(base) if base else None,
        "correction_ft": [None] * NLEADS, "capped_leads": [],
        "production_curve_tide_navd88": prod,
        "guidance": _guidance(targets, context),
        "barnacle_outlook_surge": outlook,
        "rain_inputs": _rain_inputs(forecast, decay, manifest, issuance, context),
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
            _rain_candidate(rec)
            return rec
    rec.update(status="fallback", fallback_reason="; ".join(reasons)[:400])
    _rain_candidate(rec)
    return rec


def _rain_candidate(rec):
    """Candidate surge per tank point after issuance (the baseline for a fallback)."""
    ri = rec.get("rain_inputs") or {}
    if "production_tide_navd88" not in ri:
        return
    t0 = _utc(rec["nominal_issuance_hour_utc"])
    corr = rec["correction_ft"] if rec["status"] == "candidate" else None
    ri["candidate_surge_ft"] = [(None if b is None else
                                 round(b + (correction_at(corr, t0, t) if corr else 0.0), 4))
                                for t, b in zip(rain_times(ri), ri["baseline_surge_ft"])]


# ------------------------------------------------------------------ network parts
def _get(url, params, timeout):
    req = urllib.request.Request(url + ("?" + urllib.parse.urlencode(params) if params else ""),
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _pressure_rows(body):
    """[(t, hPa)] of rows with a finite value and ALL quality flags 0; plus the
    rejected rows verbatim."""
    js = json.loads(body)
    ok, rejected = [], []
    for r in js.get("data") or []:
        try:
            v = float(r["v"])
            flags = [int(x) for x in str(r["f"]).split(",")]
            if len(flags) != 3 or any(flags) or not math.isfinite(v):
                raise ValueError
            t = _utc(r["t"].replace(" ", "T") + "Z")
        except (KeyError, TypeError, ValueError, AttributeError):
            rejected.append(r)
            continue
        ok.append((t, v))
    return ok, rejected


def gz_b64(body):
    """Raw response bytes, losslessly: gzip (mtime 0) then base64."""
    return base64.b64encode(gzip.compress(body, 9, mtime=0)).decode("ascii")


def un_gz_b64(text):
    return gzip.decompress(base64.b64decode(text))


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
            resp = {"query": {k: q[k] for k in ("begin_date", "end_date")} | {"interval": q.get("interval")},
                    "retrieved_utc": _stamp(dt.datetime.now(dt.timezone.utc)), "sha256": _sha(body)}
            if hourly:
                resp["body_gzip_b64"] = gz_b64(body)       # the 31-day response, lossless (a3 round 03 R5)
            else:
                resp["body"] = body.decode("utf-8")        # small: the last hour of 6-min values
            p["responses"].append(resp)
            rows, rejected = _pressure_rows(body)
            resp.update(rows_used=len(rows), rows_rejected_qc=len(rejected), rejected_rows=rejected[:50])
            return rows
        six = fetch(t0 - dt.timedelta(hours=1), issuance, hourly=False)
        # returned rows are admitted only if 0 <= issuance - t <= 60 min (a3 round 03 R5)
        six = sorted((t, v) for t, v in six if 0 <= (issuance - t).total_seconds() <= MAX_PRESSURE_AGE_MIN * 60)
        at_t0 = [v for t, v in six if t == t0]
        if at_t0:
            p.update(basis="value at the issuance hour", now_hpa=at_t0[0], time_utc=_stamp(t0))
        elif six:
            p.update(basis="latest 6-min value (issuance-hour value not yet published)", now_hpa=six[-1][1],
                     time_utc=_stamp(six[-1][0]))
        if p["now_hpa"] is None:
            raise ValueError("no QC-passing pressure within 60 min before issuance")
        prior_by = {}                                  # one value per distinct eligible hourly timestamp
        for t, v in fetch(t0 - dt.timedelta(days=31), issuance, hourly=True):
            if t0 - dt.timedelta(days=30) <= t < t0 and t.minute == 0 and t.second == 0:
                prior_by.setdefault(t, v)
        prior = list(prior_by.values())
        p["prior_hours"] = len(prior)
        if len(prior) < MIN_PRESSURE_HOURS:
            raise ValueError(f"only {len(prior)} QC-passing hourly values in [t0 - 30 d, t0)")
        p["anom_30d_hpa"] = round(p["now_hpa"] - sum(prior) / len(prior), 3)
    except Exception as e:  # noqa: BLE001
        p["anom_30d_hpa"] = None
        out["errors"].append(f"observed pressure unavailable ({type(e).__name__}: {str(e)[:100]})")
    return out


def validate_record(r):
    if not isinstance(r, dict):
        return [f"top-level JSON is {type(r).__name__}, not an object"]
    bad = [f"missing {k}" for k in REQUIRED_KEYS if k not in r]
    if r.get("status") not in STATUSES:
        bad.append(f"bad status {r.get('status')!r}")
    if r.get("status") != "candidate" and not r.get("fallback_reason"):
        bad.append("non-candidate record without a reason")
    if r.get("status") in ("candidate", "fallback"):
        for k in ("baseline_surge_ft", "candidate_surge_ft"):
            arr = r.get(k)
            if not isinstance(arr, list) or len(arr) != NLEADS or not all(
                    isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in arr):
                bad.append(f"{k} must hold {NLEADS} finite values")
    try:
        json.dumps(r, allow_nan=False)
    except (ValueError, TypeError) as e:
        bad.append(f"not strict JSON ({e})")
    return bad


def append_record(record, directory):
    """Validate in memory, then append the complete line with ONE write on an
    O_APPEND descriptor; an invalid record goes to quarantine/ (a3 R7)."""
    bad = validate_record(record)
    target = os.path.join(directory, "quarantine" if bad else "", f"{str(record.get('issuance_utc', 'unknown'))[:7]}.jsonl")
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
    """Problems in one log file; never raises (a3 round 03 R7)."""
    bad, last = [], ""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError) as e:
        return [f"unreadable ({type(e).__name__}: {e})"]
    for i, line in enumerate(lines, 1):
        try:
            r = json.loads(line, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
        except ValueError as e:
            bad.append(f"line {i}: not strict JSON ({e})")
            continue
        problems = validate_record(r)
        bad += [f"line {i}: {b}" for b in problems]
        if not isinstance(r, dict):
            continue
        g = str(r.get("issuance_utc") or "")
        if g < last:
            bad.append(f"line {i}: issuance before the previous line")
        last = max(last, g)
    return bad


def collection_target(mode=None):
    """(collection, directory, reason): ('official', TRIAL_DIR, None) only with
    BARNACLE_WIND_SHADOW_TRIAL=1 AND a known execution mode that is neither
    --no-send nor --dry-run; ('preview', D, why) with a preview directory;
    otherwise (None, None, why)  (a3 R8, round 03)."""
    preview = os.environ.get("BARNACLE_WIND_SHADOW_PREVIEW_DIR")
    why = "no opt-in"
    if os.environ.get("BARNACLE_WIND_SHADOW_TRIAL") == "1":
        if mode is None:
            why = "execution mode unknown: never official"
        elif mode.get("dry_run") or mode.get("no_send"):
            why = "--no-send/--dry-run runs are never official"
        else:
            return "official", TRIAL_DIR, None
    if preview:
        return "preview", preview, (None if why == "no opt-in" else why)
    return None, None, why


def run(forecast, now_utc=None, manifest_path=MANIFEST_PATH, collection=None, directory=None, get=_get,
        wall_clock_s=WALL_CLOCK_S, mode=None, context=None, root=ROOT, freeze_path=None):
    """Never raises; returns a status string. For an OFFICIAL record the frozen
    bundle is verified first (a mismatch writes a 'disabled' record and fetches
    nothing); the frozen baseline is built before any network call; the network
    part runs in a daemon thread joined for wall_clock_s; on timeout the record
    keeps the baseline with the reason (a3 R2, R6)."""
    if collection is None:
        collection, directory, why = collection_target(mode)
        if collection is None:
            return f"wind shadow: not collected ({why})"
    now_utc = now_utc or dt.datetime.now(dt.timezone.utc)
    manifest, problems = None, []
    try:
        bundle = check_bundle(root, freeze_path)
    except Exception as e:  # noqa: BLE001
        bundle = {"ok": False, "bundle_sha256": None, "table": {}, "problems": [f"bundle check failed ({e})"]}
    problems += bundle["problems"]
    try:
        manifest = load_manifest(manifest_path)
        if manifest.get("candidate_id") != CANDIDATE_ID:
            problems.append(f"manifest id {manifest.get('candidate_id')!r} != runtime {CANDIDATE_ID!r}")
        if manifest["_sha256"] != bundle["table"].get(MANIFEST_REL):
            problems.append(f"loaded manifest {manifest_path} sha256 {manifest['_sha256'][:12]} is not the frozen manifest")
    except Exception as e:  # noqa: BLE001
        problems.append(f"manifest unreadable ({type(e).__name__}: {str(e)[:120]})")
    if runtime_sha256() != bundle["table"].get(RUNTIME_REL):
        problems.append("running wind_shadow.py is not the frozen runtime")
    problems = list(dict.fromkeys(problems))
    bundle = dict(bundle, ok=not problems, problems=problems)
    wrong_identity = manifest is None or manifest.get("candidate_id") != CANDIDATE_ID
    # official: any bundle problem disables; preview: only a missing/foreign identity does
    # (a preview of an unfrozen working copy is allowed and labeled bundle_ok false)
    if problems and (collection == "official" or wrong_identity):
        rec = {"v": 3, "candidate_id": CANDIDATE_ID,
               "manifest_sha256": manifest["_sha256"] if manifest else None, "runtime_sha256": runtime_sha256(),
               "bundle_sha256": bundle.get("bundle_sha256"), "bundle_ok": False, "bundle_problems": problems,
               "collection": collection, "github_run_id": os.environ.get("GITHUB_RUN_ID"),
               "issuance_utc": str(forecast.get("generated_utc")), "written_utc": _stamp(now_utc),
               "production_model_version": forecast.get("model_version"),
               "status": "disabled", "fallback_reason": ("frozen bundle check failed: " + "; ".join(problems))[:600],
               "leads": None, "baseline_surge_ft": None, "candidate_surge_ft": None}
        try:
            rec["nominal_issuance_hour_utc"] = _stamp(_hour(_utc(forecast["generated_utc"])))
        except Exception:  # noqa: BLE001
            pass
        try:
            append_record(rec, directory)
        except Exception:  # noqa: BLE001
            return "wind shadow: disabled, not written"
        return f"wind shadow: disabled ({rec['fallback_reason'][:200]})"
    try:
        rec = pre_network_part(forecast, manifest, collection, now_utc, context=context, bundle=bundle)
    except Exception as e:  # noqa: BLE001
        rec = {"v": 3, "candidate_id": CANDIDATE_ID, "manifest_sha256": manifest["_sha256"],
               "runtime_sha256": runtime_sha256(), "bundle_sha256": bundle.get("bundle_sha256"),
               "bundle_ok": bundle["ok"], "collection": collection, "issuance_utc": str(forecast.get("generated_utc")),
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
            _rain_candidate(rec)
        path, bad = append_record(rec, directory)
        return f"wind shadow: {rec['status']}" + (f" ({rec['fallback_reason']})" if rec.get("fallback_reason") else "") \
            + (f" QUARANTINED: {bad}" if bad else "")
    except Exception as e:  # noqa: BLE001
        return f"wind shadow: not written ({type(e).__name__})"
