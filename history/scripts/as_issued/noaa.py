"""CO-OPS Sandy Hook (8531680) retrieval with raw-body retention.

Every response body is saved under its SHA-256 in a raw directory and listed
in a manifest (query, retrieval time, hash, byte size); analyses re-parse the
saved bytes, so results are reproducible offline and a tampered body fails.
Observation QC is quality-aware (lesson of audit 2026-09-24-a3 R5-Q1):
  preliminary q=p, flags [O,F,R,L]: valid iff F=R=L=0 (O is a count);
  verified    q=v, flags [I,F,R,T]: valid iff all 0 (I=1 inferred: excluded);
  missing/unknown q, non-finite value or malformed flags: invalid.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import time
import urllib.parse
import urllib.request

UTC = dt.timezone.utc
URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
STATION = "8531680"
UA = "barnacle-research (as-issued validation)"


def fetch(product, begin, end, save_dir, extra=None, get=None):
    """One request; returns (entry, body). The body is written to save_dir/raw/<sha>.json."""
    q = {"product": product, "station": STATION, "begin_date": begin.strftime("%Y%m%d %H:%M"),
         "end_date": end.strftime("%Y%m%d %H:%M"), "time_zone": "gmt", "units": "english",
         "format": "json", "application": "barnacle-research", **(extra or {})}
    if get is None:
        req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
        body = urllib.request.urlopen(req, timeout=90).read()
    else:
        body = get(q)
    sha = hashlib.sha256(body).hexdigest()
    os.makedirs(os.path.join(save_dir, "raw"), exist_ok=True)
    with open(os.path.join(save_dir, "raw", f"{sha}.json"), "wb") as f:
        f.write(body)
    return {"product": product, "query": q, "retrieved_utc": dt.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sha256": sha, "bytes": len(body), "file": f"raw/{sha}.json"}, body


def fetch_range(product, begin, end, save_dir, extra=None, chunk_days=30, get=None, pause=0.3):
    entries = []
    a = begin
    while a < end:
        b = min(a + dt.timedelta(days=chunk_days), end)
        e, _ = fetch(product, a, b, save_dir, extra, get)
        entries.append(e)
        a = b
        if get is None:
            time.sleep(pause)
    return entries


def load_bodies(manifest_path):
    """[(entry, body)] with every SHA-256 verified (ValueError on mismatch)."""
    with open(manifest_path) as f:
        man = json.load(f)
    base = os.path.dirname(os.path.abspath(manifest_path))
    out = []
    for e in man["responses"]:
        with open(os.path.join(base, e["file"]), "rb") as f:
            body = f.read()
        if hashlib.sha256(body).hexdigest() != e["sha256"]:
            raise ValueError(f"{e['file']} does not match its SHA-256")
        out.append((e, body))
    return out


def _t(s):
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=UTC)


def predictions(bodies):
    """{utc: ft MLLW} from prediction responses (duplicates must agree)."""
    out = {}
    for _e, body in bodies:
        for r in json.loads(body).get("predictions") or []:
            t, v = _t(r["t"]), float(r["v"])
            if t in out and abs(out[t] - v) > 1e-9:
                raise ValueError(f"conflicting predictions at {t}")
            out[t] = v
    return out


def classify_water_level(row):
    """(valid, reason, info) by the row's quality status (see module docstring)."""
    q, fs = row.get("q"), row.get("f")
    info = {"q": q, "f": fs}
    try:
        v = float(row["v"])
    except (KeyError, TypeError, ValueError):
        v = float("nan")
    if not math.isfinite(v):
        return False, "non-finite value", info
    parts = str(fs).split(",") if fs is not None else []
    if len(parts) != 4 or not all(p.strip().isdigit() for p in parts):
        return False, f"malformed flags {fs!r}", info
    fl = [int(p) for p in parts]
    if q == "p":
        if any(fl[1:]):
            return False, "preliminary tolerance flag", info
        info["outlier_samples"] = fl[0]
        return True, None, info
    if q == "v":
        if fl[0]:
            info["inferred"] = True
        if any(fl[1:]):
            return False, "verified tolerance flag", info
        if fl[0]:
            return False, "verified value inferred", info
        return True, None, info
    return False, f"quality status {q!r} missing or unsupported", info


def water_levels(bodies):
    """{utc: {v, valid, reason, q, f, ...}} for every returned 6-min row."""
    out = {}
    for _e, body in bodies:
        for r in json.loads(body).get("data") or []:
            ok, why, info = classify_water_level(r)
            rec = dict(info, valid=ok, reason=why)
            try:
                rec["v"] = float(r["v"])
            except (KeyError, TypeError, ValueError):
                rec["v"] = None
            out[_t(r["t"])] = rec
    return out
