"""Claude's round-02 probe for audit 2026-09-24-a3: each scenario Codex
demonstrated in round 01, rerun against the repaired c2 interfaces, recording
the repaired outcome. Read-only apart from temporary directories; no network.
Run from the candidate checkout: python3 audits/2026-09-24-a3/verify_repairs_claude.py
"""
import datetime as dt, importlib.util, json, math, os, sys, tempfile, time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
from forecast import flood_forecast_daily as ff, wind_shadow as ws, check_artifacts  # noqa: E402
import test_wind_shadow as tw  # noqa: E402
spec = importlib.util.spec_from_file_location("ev", ROOT / "history/scripts/evaluate_wind_shadow.py")
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
UTC = dt.timezone.utc
out = {}

# R1: episode rules
o = tw._obs(200, lambda i: 1.5 if i in (10, 11, 12, 13, 14, 16) else 0.0, invalid={15}); t0 = min(o)
out["R1_five_high_gap_one_high"] = len(ev.episodes(o, t0, t0 + dt.timedelta(hours=199)))
o = tw._obs(20 + 24 + 1 + 24, lambda i: 1.5 if 10 <= i < 20 else 0.0, invalid={44})
out["R1_24_quiet_gap_24_quiet_completed"] = ev.episodes(o, t0, t0 + dt.timedelta(hours=68))[0]["completed"]
o = tw._obs(200, lambda i: 1.5 if 10 <= i < 20 else 0.0, invalid={44})
e = ev.episodes(o, t0, t0 + dt.timedelta(hours=199))[0]
out["R1_completed_at_is_actual"] = {"last_high_plus_48": (e["end"] + dt.timedelta(hours=48)).isoformat(),
                                    "completed_at": e["completed_at"].isoformat()}
storms = lambda i: 1.5 if (i % 300) in range(10, 20) else 0.0
o = tw._obs(1464 + 200, storms); t0 = min(o)
slots = {t0 + dt.timedelta(hours=k): tw._rec(t0 + dt.timedelta(hours=k), 0.0, 1.0) for k in range(30)}
rep = ev.evaluate(slots, o, t0 + dt.timedelta(hours=1464 + 199))
out["R1_sparse_30_of_1464"] = {"verdict": rep["verdict"], "coverage": rep["coverage"],
                               "because": rep.get("inconclusive_because", [])[:3]}

# R2: timeout keeps the baseline; QC parsing; opportunity counts
d = tempfile.mkdtemp(); m = os.path.join(d, "manifest.json")
Path(m).write_text(json.dumps({k: v for k, v in tw.MANIFEST.items() if k != "_sha256"}))
def slow(url, params, timeout):
    time.sleep(1.0); raise OSError("late")
ws.run(tw._forecast(), now_utc=tw.T, manifest_path=m, collection="preview", directory=d, get=slow, wall_clock_s=0.2)
r = json.loads(Path(d, "2026-09.jsonl").read_text().splitlines()[-1])
out["R2_timeout_record"] = {"status": r["status"], "reason": r["fallback_reason"],
                            "baseline_leads": len(r["baseline_surge_ft"] or [])}
time.sleep(1.1)
wl = {"data": [{"t": "2026-10-01 00:00", "v": "5.0", "f": "0,0,0,0"}, {"t": "2026-10-01 01:00", "v": "5.0"},
               {"t": "2026-10-01 02:00", "v": "5.0", "f": "0,x,0,0"}, {"t": "2026-10-01 03:00", "v": "NaN", "f": "0,0,0,0"}]}
pr = {"predictions": [{"t": f"2026-10-01 0{h}:00", "v": "4.0"} for h in range(4)]}
out["R2_qc"] = {t.strftime("%H:%M"): (x["valid"], x["reason"]) for t, x in sorted(ev.parse_observations(wl, pr).items())}
o = tw._obs(24, lambda i: 0.2); t0 = min(o)
slots = {t0 + dt.timedelta(hours=k): tw._rec(t0 + dt.timedelta(hours=k), 0.2, 0.3) for k in range(4)}
rep = ev.evaluate(slots, o, t0 + dt.timedelta(hours=3, minutes=30))
out["R2_opportunities"] = {"opportunities": rep["opportunities"], "missing": rep["slot_states"]["missing"]}

# R5: run selection and pressure provenance
c = ws.cycle_for(tw.T, 6)
out["R5_meta_two_cycles_behind"] = ws.select_run(tw.T, 6, c - dt.timedelta(hours=12), tw.T)[1]
out["R5_available_after_issuance"] = ws.select_run(tw.T, 6, c, tw.T + dt.timedelta(minutes=1))[1]

# R6: identity binding and frozen baseline
dd = tempfile.mkdtemp()
good = dict(tw._rec(tw.T0, 0.1, 0.2), candidate_id="c", manifest_sha256="a" * 64, runtime_sha256="b" * 64)
Path(dd, "2026-09.jsonl").write_text("\n".join(json.dumps(x) for x in (good, dict(good, manifest_sha256="z" * 64,
    issuance_utc="2026-09-24T11:00:00Z", nominal_issuance_hour_utc="2026-09-24T11:00:00Z"))) + "\n")
s, exc = ev.load_records(dd, "c", "a" * 64, "b" * 64)
out["R6_two_manifests_same_id"] = {"evaluable": len(s), "excluded": exc}
dec = tw._forecast(tau=99.0)["water_series_input"]["decay"]
out["R6_frozen_baseline_24h_with_production_tau_99"] = round(ws.frozen_baseline(dec, tw.T0 + dt.timedelta(hours=24), 36.0), 4)

# R7: a truncated shadow line does not fail the publication gate
wdir = ROOT / "data" / "wind_shadow"; created = not wdir.exists(); wdir.mkdir(parents=True, exist_ok=True)
probe = wdir / "zz-probe.jsonl"
try:
    probe.write_text('{"v": 2, "status": "candidate"\n')
    out["R7_gate"] = {"fatal_shadow_failures": [w for p, w in check_artifacts.check_artifacts() if "wind_shadow" in str(p)],
                      "shadow_report_flags_it": any("zz-probe" in str(p) for p, _ in check_artifacts.shadow_log_report())}
finally:
    probe.unlink(missing_ok=True)
    if created:
        import shutil; shutil.rmtree(wdir, ignore_errors=True)

# R8: without the opt-in nothing is fetched or written
env = {k: v for k, v in os.environ.items() if not k.startswith("BARNACLE_WIND_SHADOW")}
with patch.dict(os.environ, env, clear=True):
    calls = []
    out["R8_no_opt_in"] = ws.run(tw._forecast(), get=lambda *a: calls.append(a))
    out["R8_fetches_without_opt_in"] = len(calls)
print(json.dumps(out, indent=1, default=str))
