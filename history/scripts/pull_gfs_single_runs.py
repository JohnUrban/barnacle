#!/usr/bin/env python3
"""Archive Open-Meteo `gfs_seamless` SINGLE RUNS at Sandy Hook for the
wind-shadow candidate (plan history/plans/2026-09-24-wind-term-candidate-plan.md,
item 1). One request per GFS cycle (00/06/12/18Z): hourly wind_speed_10m (kn),
wind_direction_10m (deg FROM), pressure_msl (hPa) for forecast hours 0..60 (a run chosen with the 6-h latency rule can be up to 11 h older than the issuance hour, and leads reach 48 h: 59 h needed).
Each raw response is saved verbatim with its SHA-256 and retrieval time
(history/data/gfs_single_runs/raw/<run>.json, git-ignored), then combined into
history/data/gfs_single_runs/runs.parquet (run_init_utc, valid_utc, lead_h, vars).
Unavailable runs are recorded as unavailable, never as zeros.
Run: python3 history/scripts/pull_gfs_single_runs.py [--begin 2026-04-01 --end 2026-09-24]
"""
import argparse, datetime as dt, hashlib, json, sys, time, urllib.parse, urllib.request
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "history/data/gfs_single_runs"
URL = "https://single-runs-api.open-meteo.com/v1/forecast"
UA = "barnacle-research (dr.john.urban@gmail.com)"
LAT, LON = 40.4669, -74.0094
VARS = "wind_speed_10m,wind_direction_10m,pressure_msl"


def fetch(run):
    q = {"latitude": LAT, "longitude": LON, "hourly": VARS, "models": "gfs_seamless",
         "run": run.strftime("%Y-%m-%dT%H:%M"), "forecast_hours": 61, "wind_speed_unit": "kn", "timezone": "GMT"}
    req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            body = e.read()
            if e.code == 400:
                return body                 # "run not available" is an answer, not a failure
            time.sleep(2 ** i)
        except Exception:
            time.sleep(2 ** i)
    raise RuntimeError(f"gave up on {run}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--begin", default="2026-04-01"); ap.add_argument("--end", default=None)
    a = ap.parse_args()
    raw = OUT / "raw"; raw.mkdir(parents=True, exist_ok=True)
    end = dt.datetime.fromisoformat(a.end).replace(tzinfo=dt.timezone.utc) if a.end else dt.datetime.now(dt.timezone.utc)
    run = dt.datetime.fromisoformat(a.begin).replace(tzinfo=dt.timezone.utc)
    rows, index = [], []
    while run <= end:
        path = raw / f"{run:%Y%m%dT%H}.json"
        if not path.exists():
            body = fetch(run)
            rec = {"run_init_utc": run.strftime("%Y-%m-%dT%H:%MZ"),
                   "retrieved_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "sha256": hashlib.sha256(body).hexdigest(), "body": body.decode("utf-8")}
            path.write_text(json.dumps(rec))
            time.sleep(0.25)
        rec = json.loads(path.read_text())
        d = json.loads(rec["body"])
        ok = not d.get("error")
        index.append({"run_init_utc": rec["run_init_utc"], "available": ok, "retrieved_utc": rec["retrieved_utc"],
                      "sha256": rec["sha256"], "reason": d.get("reason")})
        if ok:
            h = d["hourly"]
            for i, t in enumerate(h["time"]):
                v = dt.datetime.fromisoformat(t).replace(tzinfo=dt.timezone.utc)
                rows.append({"run_init_utc": run, "valid_utc": v, "lead_h": (v - run).total_seconds() / 3600,
                             "wind_kn": h["wind_speed_10m"][i], "wind_dir": h["wind_direction_10m"][i],
                             "pressure_hpa": h["pressure_msl"][i]})
        run += dt.timedelta(hours=6)
    pd.DataFrame(rows).to_parquet(OUT / "runs.parquet", index=False)
    idx = pd.DataFrame(index); idx.to_csv(OUT / "runs_index.csv", index=False)
    av = idx[idx.available]
    print(f"runs requested {len(idx)}, available {len(av)}, first {av.run_init_utc.min()}, last {av.run_init_utc.max()}, rows {len(rows)}")


if __name__ == "__main__":
    sys.exit(main())
