"""Round-04 author probes (Claude): Codex's round-03 scenarios
(verify_c2_boundaries_codex.py) rerun against the repaired interfaces, in a
temporary full mirror of the candidate checkout. Synthetic providers only,
except --live, which runs the REAL production entry point once in the mirror
with --no-send and a preview directory (network reads; nothing sent; the
mirror's data files, not the checkout's, are touched).
Run: python3 audits/2026-09-24-a3/verify_round04_claude.py --repo . --out /tmp/r04.json [--live]
     [--dry-run-probe /path/to/main/audits/2026-09-24-a3/verify_dry_run.py]
"""
import argparse, contextlib, datetime as dt, io, json, os, pathlib, shutil, subprocess, sys, tempfile
from unittest.mock import patch

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True); ap.add_argument("--out", required=True); ap.add_argument("--live", action="store_true")
ap.add_argument("--dry-run-probe", default=None, help="Codex's verify_dry_run.py (on main)")
args = ap.parse_args()
source = pathlib.Path(args.repo).resolve()
mirror = tempfile.TemporaryDirectory(prefix="barnacle-r04-"); R = pathlib.Path(mirror.name)
for name in ("forecast", "tests", "models", "model", "bin", ".github", "docs", "data"):
    if (source / name).exists():
        shutil.copytree(source / name, R / name, ignore=shutil.ignore_patterns("__pycache__"))
(R / "history").mkdir(); shutil.copytree(source / "history/scripts", R / "history/scripts")
for name in ("assets", "analysis"):
    if (source / name).exists():
        (R / name).symlink_to(source / name, target_is_directory=True)
for p in source.iterdir():
    if p.is_file():
        shutil.copy2(p, R / p.name)
for p in (source / "history").iterdir():
    if not (R / "history" / p.name).exists():
        (R / "history" / p.name).symlink_to(p, target_is_directory=p.is_dir())
sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "tests"))
from forecast import wind_shadow as w, flood_forecast_daily as ff  # noqa: E402
import test_wind_shadow as fx  # noqa: E402
import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location("ev", R / "history/scripts/evaluate_wind_shadow.py")
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
out = {"bundle_sha256": w.check_bundle(str(R))["bundle_sha256"], "bundle_ok": w.check_bundle(str(R))["ok"]}

# R7: the ACTUAL gate CLI in the full mirror
wd = R / "data/wind_shadow"; wd.mkdir(exist_ok=True)
for label, body in (("truncated", '{"v":2\n'), ("array", "[]\n"), ("null", "null\n"), ("string", '"x"\n'),
                    ("not_utf8", b"\xff\xfe\n"), ("directory", None)):
    p = wd / "zz-probe.jsonl"
    if body is None:
        p.mkdir()
    elif isinstance(body, bytes):
        p.write_bytes(body)
    else:
        p.write_text(body)
    z = subprocess.run([sys.executable, str(R / "forecast/check_artifacts.py")], cwd=R, capture_output=True, text=True)
    out[f"gate_cli_{label}"] = {"exit": z.returncode, "last_line": z.stdout.strip().splitlines()[-1],
                                "shadow_warnings": sum("SHADOW LOG WARNING" in x for x in z.stdout.splitlines())}
    shutil.rmtree(p) if p.is_dir() else p.unlink()
wd.rmdir()

# R5: a current-pressure reading one hour AFTER issuance
def futurepressure(url, params, timeout):
    if url == w.META_URL:
        return json.dumps({"last_run_initialisation_time": int((fx.T0 - dt.timedelta(hours=10)).timestamp()),
                           "last_run_availability_time": int((fx.T0 - dt.timedelta(hours=5)).timestamp())}).encode()
    if url == w.SINGLE_RUNS_URL:
        return b'{"error":true,"reason":"probe"}'
    if params.get("interval") == "h":
        rows = [{"t": (fx.T0 - dt.timedelta(hours=k)).strftime("%Y-%m-%d %H:%M"), "v": "1000", "f": "0,0,0"} for k in range(720, 0, -1)]
    else:
        rows = [{"t": (fx.T + dt.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"), "v": "1001", "f": "0,0,0"}]
    return json.dumps({"data": rows}).encode()
i = w.fetch_inputs(fx.T, fx.MANIFEST, get=futurepressure)
out["future_pressure"] = {"now_hpa": i["pressure"]["now_hpa"], "pressure_errors": [e for e in i["errors"] if "pressure" in e]}
selected, why = w.select_run(fx.T, 6, w.cycle_for(fx.T, 6) + dt.timedelta(hours=6), fx.T + dt.timedelta(minutes=1))
out["newer_metadata_available_after_issuance"] = {"selected": selected, "reason": why}

# R3: raw guidance vs Barnacle's outlook; observed_decay is not external coverage
ob = fx._obs(200, lambda k: .2); ot = min(ob); sr = fx._rec(ot, .3, .4)
sr["barnacle_outlook_surge"] = [[.4, "observed_decay"]] * 48
cmp = ev.evaluate({ot: sr}, ob, ot + dt.timedelta(hours=199), rain=False)["leads"][24]
out["observed_decay_not_external"] = {"external": {k: v["available_in_scored_pairs"] for k, v in cmp["vs_external_guidance"].items()},
                                      "barnacle_outlook_sources": sorted(cmp["vs_barnacle_outlook"]["by_source"])}

# R3: Codex's rain initialization case, through the evaluator
rr = ev.rain_ref()
start = dt.datetime(2026, 9, 24, 4, tzinfo=dt.timezone.utc); iss = dt.datetime(2026, 9, 24, 10, tzinfo=dt.timezone.utc)
times = [start + dt.timedelta(minutes=30 * k) for k in range(73)]
rates = [1.0 if t < iss else 0.0 for t in times]; prod = [3.68] * 73; after = [t > iss for t in times]
ri = {"series_start": start.isoformat(), "step_min": 30, "issuance_utc": iss.isoformat(), "production_tide_navd88": prod,
      "production_surge_ft": [.5] * 73, "production_pluvial_navd88": rr.simulate_pluvial_series(times, prod, rates),
      "baseline_surge_ft": [.5 if a else None for a in after], "candidate_surge_ft": [.5 if a else None for a in after],
      "qpf_in_hr": rates}
rain = ev.rain_tank_sensitivity({iss: dict(fx._rec(iss, .5, .5), rain_inputs=ri)}, rr)
first_after = times.index(iss + dt.timedelta(minutes=30))
out["rain_prior_storage"] = {"tank_navd88_first_point_after_issuance": ri["production_pluvial_navd88"][first_after],
                             "wet_issuances": rain["wet_issuances"], "curb": rain["landmarks_wet"]["curb"],
                             "frozen_vs_production": rain["frozen_tank_vs_production_pluvial"]}

# R6: unfrozen manifest under the same id, official collection
with tempfile.TemporaryDirectory() as d:
    mod = json.loads((R / "models/wind_shadow/manifest.json").read_text()); mod["tau_h"] = 999
    mp = pathlib.Path(d) / "manifest.json"; mp.write_text(json.dumps(mod))
    calls = []
    status = w.run(fx._forecast(), manifest_path=str(mp), collection="official", directory=d, now_utc=fx.T,
                   get=lambda *a: calls.append(a) or b"", root=str(R))
    row = json.loads((pathlib.Path(d) / "2026-09.jsonl").read_text())
    out["unfrozen_manifest_official"] = {"status": row["status"], "reason": row["fallback_reason"][:160],
                                         "values": row["candidate_surge_ft"], "network_calls": len(calls)}

# R6: evaluator comment appended in the mirror; and a log bound to another bundle
with tempfile.TemporaryDirectory() as d:
    td = pathlib.Path(d); (td / "records").mkdir()
    (td / "obs.json").write_text(json.dumps({"water_level": {"data": []}, "predictions": {"predictions": []}}))
    path = R / "history/scripts/evaluate_wind_shadow.py"; src = path.read_text()
    cmd = [sys.executable, str(path), "--dir", str(td / "records"), "--obs-json", str(td / "obs.json"), "--now", "2026-10-01T00:00:00Z"]
    path.write_text(src + "\n# reviewer test of mismatch rejection\n")
    try:
        z = subprocess.run(cmd, capture_output=True, text=True); j = json.loads(z.stdout)
        out["evaluator_hash_mismatch"] = {"exit": z.returncode, "verdict": j["verdict"], "problems": j["bundle_problems"]}
    finally:
        path.write_text(src)
    rec = dict(fx._rec(fx.T0, .2, .3), candidate_id=w.CANDIDATE_ID, bundle_sha256="0" * 64)
    (td / "records/2026-09.jsonl").write_text(json.dumps(rec) + "\n")
    z = subprocess.run(cmd, capture_output=True, text=True); j = json.loads(z.stdout)
    out["log_bound_to_other_bundle"] = {"exit": z.returncode, "verdict": j["verdict"], "problems": j["bundle_problems"]}

# R8: Codex's actual-main-flow probe, default env and with the trial opt-in
probe = pathlib.Path(args.dry_run_probe) if args.dry_run_probe else source / "audits/2026-09-24-a3/verify_dry_run.py"
if probe.exists():
    for mode in ("default", "opt_in"):
        with tempfile.NamedTemporaryFile(suffix=".json") as ftmp:
            env = {k: v for k, v in os.environ.items() if not k.startswith("BARNACLE_WIND_SHADOW")}
            if mode == "opt_in":
                env["BARNACLE_WIND_SHADOW_TRIAL"] = "1"
            z = subprocess.run([sys.executable, str(probe), "--repo", str(R), "--out", ftmp.name], env=env, capture_output=True, text=True)
            res = json.load(open(ftmp.name)) if z.returncode == 0 else z.stderr[-800:]
            out[f"main_dry_run_{mode}"] = ({k: {"shadow_invocations": v["shadow_invocations"]} for k, v in res.items()}
                                          if isinstance(res, dict) else res)
else:
    out["main_dry_run"] = "verify_dry_run.py (on main) not present in --repo; see tests"

# optional: one REAL production run in the mirror, --no-send, preview directory
if args.live:
    pv = R / "preview"
    env = {k: v for k, v in os.environ.items() if not k.startswith("BARNACLE_WIND_SHADOW")}
    env["BARNACLE_WIND_SHADOW_PREVIEW_DIR"] = str(pv)
    z = subprocess.run([sys.executable, "flood_forecast_daily.py", "--no-send", "--write-json", str(R / "tmp_forecast.json")],
                       cwd=R / "forecast", env=env, capture_output=True, text=True, timeout=900)
    recs = [json.loads(x) for f in sorted(pv.glob("*.jsonl")) for x in f.read_text().splitlines()] if pv.exists() else []
    r = recs[-1] if recs else {}
    ri = r.get("rain_inputs") or {}
    g = r.get("guidance") or {}
    out["live_preview"] = {
        "exit": z.returncode, "shadow_line": [x for x in z.stdout.splitlines() if x.startswith("wind shadow")],
        "records": len(recs), "status": r.get("status"), "reason": r.get("fallback_reason"),
        "bundle_ok": r.get("bundle_ok"), "bundle_problems": r.get("bundle_problems"), "collection": r.get("collection"),
        "selection": (r.get("run") or {}).get("selection"),
        "pressure_basis": (r.get("pressure_obs") or {}).get("basis"), "pressure_prior_hours": (r.get("pressure_obs") or {}).get("prior_hours"),
        "nwps_raw_targets": sum(v is not None for v in (g.get("nwps_raw") or {}).get("surge_ft") or []),
        "petss_mid_targets": sum(v is not None for v in (g.get("petss_mid") or {}).get("surge_ft") or []),
        "outlook_sources": sorted({x[1] for x in r.get("barnacle_outlook_surge") or [] if x}),
        "rain_points": len(ri.get("production_tide_navd88") or []), "rain_series_start": ri.get("series_start"),
        "qpf_available": ri.get("qpf_in_hr") is not None, "record_bytes": len(json.dumps(r, separators=(",", ":"))),
        "official_log_created": (R / "data/wind_shadow").exists()}
    if recs:
        rs = ev.rain_tank_sensitivity({ev._slot(r): r}, rr)
        out["live_preview"]["frozen_tank_vs_production_pluvial"] = rs["frozen_tank_vs_production_pluvial"]
        out["live_preview"]["rain_missing"] = rs["missing_inputs"]

pathlib.Path(args.out).write_text((json.dumps(out, indent=2, default=str) + "\n").replace(str(R), "SCRATCH_MIRROR"))
print(pathlib.Path(args.out).read_text())
mirror.cleanup()
