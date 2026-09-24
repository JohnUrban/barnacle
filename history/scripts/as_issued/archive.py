"""Read the immutable as-issued archive.

Sources (read-only):
  G  every committed docs/forecast.json (Git history; blob SHA-1 = identity)
  R  data/replay_inputs/*.jsonl (v0.10.6 prospective archive; line identity =
     file blob + line number + SHA-256 of the line)
Nothing is inferred as available at issuance unless it is present in the
published artifact or the replay record of THAT issuance.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
UTC = dt.timezone.utc


def _git(*args, cwd=ROOT, input_=None):
    return subprocess.run(["git", *args], cwd=cwd, input=input_, capture_output=True, check=True).stdout


def forecast_commits(path="docs/forecast.json", rev="HEAD", cwd=ROOT):
    """[(commit, commit_time_iso, blob_sha)] oldest first, for every commit touching path."""
    out = _git("log", rev, "--reverse", "--format=%H %cI", "--", path, cwd=cwd).decode().split("\n")
    rows = [line.split() for line in out if line.strip()]
    if not rows:
        return []
    spec = "".join(f"{c}:{path}\n" for c, _t in rows).encode()
    blobs = _git("cat-file", "--batch-check=%(objectname) %(objecttype)", cwd=cwd, input_=spec).decode().split("\n")
    res = []
    for (c, t), b in zip(rows, blobs):
        parts = b.split()
        if len(parts) == 2 and parts[1] == "blob":
            res.append((c, t, parts[0]))
    return res


def iter_blobs(blob_shas, cwd=ROOT):
    """Yield (blob_sha, bytes) via one `git cat-file --batch` process."""
    p = subprocess.Popen(["git", "cat-file", "--batch"], cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for sha in blob_shas:
            p.stdin.write((sha + "\n").encode()); p.stdin.flush()
            header = p.stdout.readline().decode().split()
            if len(header) < 3 or header[1] != "blob":
                yield sha, None
                continue
            size = int(header[2])
            data = p.stdout.read(size); p.stdout.read(1)
            yield sha, data
    finally:
        p.stdin.close(); p.wait()


def parse_utc(s):
    if s is None:
        return None
    t = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return t if t.tzinfo else None


def summarize_forecast(f):
    """Per-issuance availability summary (no outcomes)."""
    ws = f.get("water_series") or []
    keys = set()
    for p in ws:
        keys |= set(p)
    ol = f.get("outlook_7d") or {}
    series = ol.get("series") or []
    tides = ol.get("tides") or []
    corr = ((ol.get("assumptions") or {}).get("advisory_corrections")) or []
    anchors = []
    for t in tides:
        g = t.get("guidance") or {}
        if g.get("nws_product") is not None and g.get("nwps") is not None:
            anchors.append(round(g["nws_product"] - g["nwps"], 3))
    tide_windows = sum(1 for t in (f.get("all_tides") or []) if t.get("rain_window_3h"))
    decay = ((f.get("water_series_input") or {}).get("decay")) or {}
    return {
        "generated_utc": f.get("generated_utc"), "model_version": f.get("model_version"),
        "core_points": len(ws), "core_first": ws[0].get("time") if ws else None, "core_last": ws[-1].get("time") if ws else None,
        "core_keys": sorted(keys), "core_has_tide": "tide_navd88" in keys,
        "core_pluvial_points": sum(1 for p in ws if p.get("pluvial_navd88") is not None),
        "decay_meta": bool(decay), "decay_rung": decay.get("rung"),
        "current_surge_ft": f.get("current_surge_ft"), "surge_source": f.get("surge_source"),
        "tide_rain_windows": tide_windows,
        "outlook": bool(series), "outlook_points": len(series),
        "outlook_sources": dict(Counter(p.get("surge_source") for p in series)),
        "outlook_rain_hours": sum(1 for p in series if p.get("rain_in_hr") is not None and not p.get("rain_unknown")),
        "outlook_first_lead_h": series[0].get("lead_h") if series else None,
        "outlook_tide_anchors": len(anchors), "outlook_tide_anchors_nonzero": sum(1 for a in anchors if abs(a) >= 0.005),
        "advisory_corrections": len(corr), "advisory_corrections_nonzero": sum(1 for c in corr if abs(c.get("ft") or 0) >= 0.005),
        "nws_status": (f.get("nws_status") or "")[:120] if isinstance(f.get("nws_status"), str) else f.get("nws_status"),
    }


def inventory(rev="HEAD", cwd=ROOT):
    """[summary + commit/blob identity] for every published forecast, deduplicated by
    generated_utc (the first commit carrying a generation is kept; repeats counted)."""
    commits = forecast_commits(rev=rev, cwd=cwd)
    by_blob = {}
    rows, seen, repeats, unparsable = [], {}, 0, []
    blob_of = {b: (c, t) for c, t, b in commits}
    order = [b for _c, _t, b in commits]
    for sha, data in iter_blobs(list(dict.fromkeys(order)), cwd=cwd):
        by_blob[sha] = data
    for c, t, b in commits:
        data = by_blob.get(b)
        try:
            f = json.loads(data)
        except (TypeError, ValueError):
            unparsable.append(c)
            continue
        s = summarize_forecast(f)
        key = s["generated_utc"] or f"commit:{c}"
        if key in seen:
            repeats += 1
            continue
        seen[key] = c
        s.update(commit=c, commit_time=t, blob=b, sha256=hashlib.sha256(data).hexdigest())
        rows.append(s)
    return {"rows": rows, "commits": len(commits), "distinct_generations": len(rows),
            "repeated_generations": repeats, "unparsable_commits": unparsable}


def load_forecast(blob, cwd=ROOT):
    return json.loads(_git("cat-file", "blob", blob, cwd=cwd))


def replay_records(directory=os.path.join(ROOT, "data", "replay_inputs")):
    """[(record, identity)] from the prospective archive, in file order."""
    out = []
    for fn in sorted(os.listdir(directory)) if os.path.isdir(directory) else []:
        if not fn.endswith(".jsonl"):
            continue
        with open(os.path.join(directory, fn), "rb") as fh:
            for i, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                out.append((json.loads(line), {"file": f"data/replay_inputs/{fn}", "line": i,
                                               "sha256": hashlib.sha256(line.rstrip(b"\n")).hexdigest()}))
    return out
