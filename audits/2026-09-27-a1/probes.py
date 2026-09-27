#!/usr/bin/env python3
"""Read-only audit probes. Run from any directory; requires local repo history.

Pins evidence to the reviewed commit, imports its code in a temporary archive,
does not fetch data or write production files. stdout is the JSON receipt.
"""
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
BASE = "fa3e041c5dd634d038a7b92e2db2baa599237df9"
HEAD = "10ea6c2a29a9a9be1869adf78665b29c1685e96a"
RESEARCH = "cd17a5a14"

def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])

def blob(path, rev=HEAD):
    return git("show", f"{rev}:{path}")

def rows(path, rev=HEAD):
    return list(csv.DictReader(io.StringIO(blob(path, rev).decode())))

def run():
    result = {"baseline": BASE, "reviewed_commit": HEAD, "ledgers": {}}
    for name in ("labeled_observations", "predictions_log", "forecast_accuracy"):
        p = f"data/{name}.csv"
        old, new = rows(p, BASE), rows(p)
        result["ledgers"][name] = {"before": len(old), "after": len(new),
            "old_rows_preserved_in_order": new[:len(old)] == old,
            "added": len(new)-len(old)}
    p = "data/labeled_observations.csv"
    new = rows(p)[len(rows(p, BASE)):]
    result["new_observations"] = {
        "count": len(new),
        "naive_times": sum(dt.datetime.fromisoformat(r["observation_time_local"]).tzinfo is None for r in new),
        "numeric_depths": sum(bool(r["observed_depth_in"]) for r in new),
        "paired_model_depths": sum(bool(r["observed_depth_in"] and r["model_predicted_depth_in"]) for r in new),
        "exact_duplicate_rows": len(new)-len({tuple(r.items()) for r in new}),
    }
    frozen = json.loads(blob("audits/2026-09-24-a4/frozen-files.json"))
    result["frozen_wind_files"] = [{"path": r["path"], "matches":
        hashlib.sha256(blob(r["path"])).hexdigest() == r["sha256"]} for r in frozen]
    cache = json.loads(blob("assets/observations/2026-09-26/analysis/gauge_cache.json"))
    result["cached_gauge_peaks"] = {k: max(v, key=lambda x:x[1]) for k,v in cache.items()}
    with tempfile.TemporaryDirectory(prefix="barnacle-audit-") as tmp:
        repo = Path(tmp)
        archive = git("archive", HEAD, "forecast", "history/data", "model", "models")
        with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
            tf.extractall(repo, filter="data")
        sys.path.insert(0, str(repo))
        from forecast import flood_forecast_daily as ff
        elev = {k:e for k, _, e, _ in ff.LANDMARKS}
        daily, episodes = {}, {}
        for r in new:
            try:
                water = elev[r["landmark_key"]] + float(r["observed_depth_in"])/12
            except (KeyError, ValueError):
                continue
            time = ff.parse_station_local_time(r["observation_time_local"])
            day = time.date().isoformat()
            key = day + ("-am" if time.hour < 17 else "-pm")
            daily[day] = max(daily.get(day, -999), water)
            episodes[key] = max(episodes.get(key, -999), water)
        result["derived_peaks_navd88"] = {"daily":daily, "episodes":episodes}
        # Reuse the actual unmerged classifier/grouping implementation.
        scope = {"__file__":str(repo / "history/scripts/as_issued/obs.py")}
        exec(compile(blob("history/scripts/as_issued/obs.py", RESEARCH), "obs.py", "exec"), scope)
        classified = [scope["classify"](r, elev) for r in new]
        eligible = [r for r in classified if r["eligible"]]
        groups = scope["events"](sorted(r["time_utc"] for r in eligible))
        result["research_classifier"] = {"commit":RESEARCH,
            "eligible_rows":len(eligible), "12h_gap_groups":len(set(groups))}
        # Actual chart renderer: the offset-bearing left boundary is discarded.
        (repo / "data").mkdir()
        with (repo / "data/labeled_observations.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["observation_time_local", "landmark_key", "observed_depth_in"])
            w.writerow(["2026-09-26T07:00:00-04:00", "lawn_step", "0"])
            w.writerow(["2026-09-26T07:18:00-04:00", "lawn_step", "0"])
        series = [{"time":f"2026-09-26 {h:02d}:{m:02d}-04:00", "tide_navd88":4.0}
                  for h in (7,8) for m in (0,30)]
        with mock.patch.object(ff, "_REPO_ROOT", str(repo)):
            html = ff._render_water_series_section({"water_series":series})
        cfg = json.loads(re.search(r"var cfg = (\{.*?\});", html).group(1))
        dots = next(d["data"] for d in cfg["data"]["datasets"] if "tape" in d["label"].lower())
        result["tape_boundary"] = {"input_rows":2, "plotted_rows":len(dots), "dots":dots}
        # Exact comparison expression used by the event plot, with valid input.
        try:
            dt.datetime.fromisoformat("2026-09-26 04:00") <= dt.datetime.fromisoformat("2026-09-26T07:00-04:00")
        except TypeError as e:
            result["event_plot_offset_time"] = str(e)
        # Reconstruct the documented fixed-base, zero-drain sensitivity.
        rain = [r for r in rows("history/data/mrms/mrms_extracted.csv")
                if r["product"] == "PrecipRate" and "2026-09-26T08:00:00Z" <= r["utc"] <= "2026-09-26T14:30:00Z"]
        frames = sorted((dt.datetime.fromisoformat(r["utc"]), float(r["box_mean"])/25.4) for r in rain)
        t0 = dt.datetime.fromisoformat("2026-09-26T08:00:00Z")
        t1 = dt.datetime.fromisoformat("2026-09-26T14:30:00Z")
        expected = [t0+dt.timedelta(minutes=6*i) for i in range(66)]
        result["rain_sensitivity"] = {"frames":len(frames),
            "missing_utc":[t.isoformat() for t in expected if t not in {x[0] for x in frames}],
            "six_min_rectangular_sum_in":sum(v*.1 for _,v in frames),
            "cases":[]}
        for base in (5.3,5.7):
            stage = (base-ff.GRATE_SW)*12
            t, volume, outputs = t0, 0., []
            while t <= t1:
                candidates = [v for ft,v in frames if ft <= t-dt.timedelta(minutes=ff.TANK_LAG_MIN)]
                rate = candidates[-1] if candidates else 0.
                volume = max(0., volume+(ff.TANK_K*rate**ff.TANK_GAMMA-ff.TANK_KOUT*volume)*2/60)
                lift = ff._pluvial_fill(ff._load_stage_curve(), stage, volume)-stage if volume else 0.
                outputs.append((t.isoformat(),lift))
                t += dt.timedelta(minutes=2)
            result["rain_sensitivity"]["cases"].append({"fixed_base_navd88":base,
                "drain_in_hr":0, "peak_lift_utc_in":max(outputs, key=lambda x:x[1])})
    return result

if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
