"""Wind-shadow candidate c2 (SHADOW ONLY): construction, production isolation,
opt-in collection, record/quarantine/gate behaviour, frozen identity, and the
frozen evaluator's declared rules. Regressions for audit 2026-09-24-a3 R1-R8."""
import copy, datetime as dt, hashlib, importlib.util, json, math, os, re, shutil, tempfile, time, unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

from forecast import check_artifacts
from forecast import flood_forecast_daily as ff
from forecast import surge_decay as sd
from forecast import wind_shadow as ws

UTC = dt.timezone.utc
ROOT = Path(__file__).resolve().parents[1]
T = dt.datetime(2026, 9, 24, 10, 30, tzinfo=UTC)
T0 = T.replace(minute=0)
MANIFEST = {"candidate_id": ws.CANDIDATE_ID, "_sha256": "m" * 64, "theta_deg": 70.0, "latency_h": 6, "tau_h": 36.0,
            "correction_cap_ft": 3.0, "latitude": 40.4669, "longitude": -74.0094, "model": "gfs_seamless",
            "forecast_hours": 61, "navd88_offset_ft": -2.82, "local_enhancement_ft": 0.0,
            "coefficients": {str(h): [0.001, -0.02, -0.01, 0.05] for h in range(1, 49)}}


def _forecast(rung="fresh", tau=36.0):
    return {"generated_utc": "2026-09-24T10:30:00Z", "model_version": "v0.10.6",
            "water_series_input": {"decay": {"rung": rung, "surge_obs_ft": 1.5, "observation_utc": "2026-09-24T10:18:00Z",
                                             "mean_ft": 0.53, "mean_source": "m", "tau_h": tau, "age_h": 0.2}},
            "water_series": [{"time": "2026-09-24 07:00-04:00", "tide_navd88": 1.2}],
            "outlook_7d": {"series": [{"utc": "2026-09-24T12:00:00Z", "astro_mllw": 4.0, "tide_navd88": 2.9,
                                       "surge_source": "nwps"}]}}


def _inputs(complete=True, errors=None):
    hours = {dt.datetime(2026, 9, 24, 0, tzinfo=UTC) + dt.timedelta(hours=k): (20.0, 60.0, 1005.0 - 0.1 * k) for k in range(62)}
    if not complete:
        hours.pop(dt.datetime(2026, 9, 24, 20, tzinfo=UTC))
    return {"errors": errors or [], "fetched_utc": "x", "init_utc": "2026-09-24T00:00:00Z", "selection": "ok",
            "meta": None, "run_hours": hours, "retrieved_utc": "x", "raw_sha256": "s", "raw_body": "{}",
            "pressure": {"basis": "value at the issuance hour", "now_hpa": 1010.0, "time_utc": "2026-09-24T10:00:00Z",
                         "anom_30d_hpa": -3.0, "responses": []}}


class ConstructionTests(unittest.TestCase):
    def test_strict_run_selection_R5(self):
        c = dt.datetime(2026, 9, 24, 0, tzinfo=UTC)
        self.assertEqual(ws.cycle_for(T, 6), c)
        self.assertIn("unconfirmed", ws.select_run(T, 6)[1])
        self.assertIn("not yet available", ws.select_run(T, 6, c - dt.timedelta(hours=12), T)[1])   # 2 cycles behind
        self.assertIn("after the issuance", ws.select_run(T, 6, c, T + dt.timedelta(minutes=1))[1])
        self.assertEqual(ws.select_run(T, 6, c, T - dt.timedelta(hours=4)), (c, None))
        self.assertEqual(ws.select_run(T, 6, c + dt.timedelta(hours=6), T)[0], c)                   # newer run exists

    def test_features_complete_windows(self):
        f, why = ws.features(_inputs()["run_hours"], T0, 1010.0, -3.0, 24, 70.0)
        self.assertIsNone(why); self.assertAlmostEqual(f[0], 400 * math.cos(math.radians(-10)), places=9)
        self.assertIn("incomplete", ws.features(_inputs(False)["run_hours"], T0, 1010.0, -3.0, 24, 70.0)[1])

    def test_correction_cap(self):
        self.assertEqual(ws.correction([1.0, 0, 0, 0], (10.0, 0, 0), 3.0), (3.0, True))

    def test_frozen_baseline_ignores_production_tau_R6(self):
        d = _forecast(tau=99.0)["water_series_input"]["decay"]
        anchor = sd.SurgeAnchor("fresh", 0.53, "m", 1.5, dt.datetime(2026, 9, 24, 10, 18, tzinfo=UTC), tau_h=36.0)
        t = T0 + dt.timedelta(hours=24)
        self.assertAlmostEqual(ws.frozen_baseline(d, t, 36.0), anchor.at(t), places=12)

    def test_record_parts(self):
        rec = ws.pre_network_part(_forecast(), MANIFEST, "preview", T)
        self.assertEqual(rec["status"], "fallback")                      # baseline exists before any network
        self.assertEqual(len(rec["baseline_surge_ft"]), 48)
        self.assertEqual(rec["production_curve_tide_navd88"][0], 1.2)    # 11Z = lead 1
        self.assertEqual(rec["nws_outlook_surge"][1], [round(2.9 + 2.82 - 4.0, 4), "nwps"])
        full = ws.complete_record(copy.deepcopy(rec), _forecast(), MANIFEST, _inputs())
        self.assertEqual(full["status"], "candidate")
        self.assertNotEqual(full["candidate_surge_ft"][23], full["baseline_surge_ft"][23])
        stale = ws.complete_record(ws.pre_network_part(_forecast("stale-download"), MANIFEST, "preview", T),
                                   _forecast(), MANIFEST, _inputs())
        self.assertIn("not fresh", stale["fallback_reason"])
        self.assertEqual(stale["candidate_surge_ft"], stale["baseline_surge_ft"])
        inc = ws.complete_record(copy.deepcopy(rec), _forecast(), MANIFEST, _inputs(False))
        self.assertIn("incomplete", inc["fallback_reason"])
        self.assertEqual(ws.validate_record(full), [])


class PressureTests(unittest.TestCase):
    def test_qc_rows(self):
        body = json.dumps({"data": [{"t": "2026-09-24 10:00", "v": "1010.0", "f": "0,0,0"},
                                    {"t": "2026-09-24 10:06", "v": "1010.1", "f": "0,1,0"},
                                    {"t": "2026-09-24 10:12", "v": "nan", "f": "0,0,0"},
                                    {"t": "2026-09-24 10:18", "v": "1010.2"},
                                    {"t": "2026-09-24 10:24", "v": "1010.3", "f": "0,0"}]}).encode()
        rows, rejected = ws._pressure_rows(body)
        self.assertEqual((len(rows), rejected), (1, 4))

    def test_window_is_720_hours_and_basis_recorded_R4(self):
        def fake(url, params, timeout):
            if url == ws.META_URL:
                return json.dumps({"last_run_initialisation_time": int(dt.datetime(2026, 9, 24, 0, tzinfo=UTC).timestamp()),
                                   "last_run_availability_time": int((T - dt.timedelta(hours=4)).timestamp())}).encode()
            if url == ws.SINGLE_RUNS_URL:
                raise OSError("no run")
            if params.get("interval") == "h":
                rows = [{"t": (T0 - dt.timedelta(hours=k)).strftime("%Y-%m-%d %H:%M"), "v": "1000.0", "f": "0,0,0"}
                        for k in range(0, 24 * 31)]
            else:
                rows = [{"t": (T0 + dt.timedelta(minutes=m)).strftime("%Y-%m-%d %H:%M"), "v": "1004.0", "f": "0,0,0"}
                        for m in (-6, 0, 6, 12, 18, 24)]
            return json.dumps({"data": rows}).encode()
        out = ws.fetch_inputs(T, MANIFEST, get=fake)
        p = out["pressure"]
        self.assertEqual(p["prior_hours"], 720)
        self.assertEqual((p["now_hpa"], p["time_utc"], p["anom_30d_hpa"]), (1004.0, "2026-09-24T10:00:00Z", 4.0))
        self.assertEqual(p["basis"], "value at the issuance hour")
        self.assertEqual(len(p["responses"]), 2); self.assertTrue(all(len(r["sha256"]) == 64 for r in p["responses"]))


class CollectionAndIsolationTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.m = os.path.join(self.d, "manifest.json")
        Path(self.m).write_text(json.dumps({k: v for k, v in MANIFEST.items() if k != "_sha256"}))

    def test_no_opt_in_collects_nothing_R8(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BARNACLE_WIND_SHADOW_TRIAL", None); os.environ.pop("BARNACLE_WIND_SHADOW_PREVIEW_DIR", None)
            get = unittest.mock.Mock()
            self.assertIn("not collected", ws.run(_forecast(), manifest_path=self.m, get=get))
            get.assert_not_called()
        with patch.dict(os.environ, {"BARNACLE_WIND_SHADOW_PREVIEW_DIR": self.d}):
            self.assertEqual(ws.collection_target(), ("preview", self.d))
        with patch.dict(os.environ, {"BARNACLE_WIND_SHADOW_TRIAL": "1"}):
            self.assertEqual(ws.collection_target()[0], "official")

    def test_timeout_keeps_the_baseline_R2(self):
        def slow(url, params, timeout):
            time.sleep(1.0); raise OSError("late")
        t0 = time.monotonic()
        msg = ws.run(_forecast(), now_utc=T, manifest_path=self.m, collection="preview", directory=self.d,
                     get=slow, wall_clock_s=0.2)
        self.assertLess(time.monotonic() - t0, 0.6)
        rec = json.loads(Path(self.d, "2026-09.jsonl").read_text().splitlines()[-1])
        self.assertEqual(rec["status"], "fallback"); self.assertIn("wall clock", rec["fallback_reason"])
        self.assertEqual(len(rec["baseline_surge_ft"]), 48)
        self.assertEqual(rec["candidate_surge_ft"], rec["baseline_surge_ft"])
        self.assertEqual(rec["collection"], "preview")
        time.sleep(1.1)

    def test_feed_failure_is_a_labeled_fallback_and_forecast_untouched(self):
        def boom(url, params, timeout):
            raise OSError("down")
        f = _forecast(); before = copy.deepcopy(f)
        ws.run(f, now_utc=T, manifest_path=self.m, collection="preview", directory=self.d, get=boom)
        self.assertEqual(f, before)
        rec = json.loads(Path(self.d, "2026-09.jsonl").read_text().splitlines()[-1])
        self.assertEqual(rec["status"], "fallback"); self.assertIn("unconfirmed", rec["fallback_reason"])
        self.assertEqual(ws.validate_file(str(Path(self.d, "2026-09.jsonl"))), [])

    def test_identity_mismatch_writes_an_identified_error(self):
        bad = os.path.join(self.d, "other.json")
        Path(bad).write_text(json.dumps(dict({k: v for k, v in MANIFEST.items() if k != "_sha256"}, candidate_id="x")))
        ws.run(_forecast(), now_utc=T, manifest_path=bad, collection="preview", directory=self.d, get=lambda *a: b"")
        rec = json.loads(Path(self.d, "2026-09.jsonl").read_text().splitlines()[-1])
        self.assertEqual((rec["status"], rec["candidate_id"]), ("error", ws.CANDIDATE_ID))

    def test_invalid_record_is_quarantined_not_logged_R7(self):
        path, bad = ws.append_record({"issuance_utc": "2026-09-24T10:30:00Z", "status": "candidate"}, self.d)
        self.assertTrue(bad); self.assertIn("quarantine", path)
        self.assertFalse(Path(self.d, "2026-09.jsonl").exists())

    def test_main_wrapper_opt_in_and_isolation_R7_R8(self):
        fc = {"generated_utc": "2026-09-24T10:30:00Z"}
        def core(h):
            h["forecast"], h["json_written"] = fc, True
        env = {k: v for k, v in os.environ.items() if not k.startswith("BARNACLE_WIND_SHADOW")}
        with patch.dict(os.environ, env, clear=True), patch.object(ff, "_main_core", side_effect=core), \
                patch.object(ws, "run") as run:
            ff.main(); run.assert_not_called()                          # --no-send/--dry-run locally: nothing
        with patch.dict(os.environ, dict(env, BARNACLE_WIND_SHADOW_TRIAL="1"), clear=True), \
                patch.object(ff, "_main_core", side_effect=core), patch.object(ws, "run", side_effect=RuntimeError("bug")) as run:
            ff.main(); run.assert_called_once()                         # a crashing shadow cannot fail the run

    def test_publish_gate_ignores_a_broken_shadow_log_R7(self):
        wdir = ROOT / "data" / "wind_shadow"
        created = not wdir.exists()
        wdir.mkdir(parents=True, exist_ok=True)
        probe = wdir / "zz-gate-probe.jsonl"
        try:
            probe.write_text('{"v": 2, "status": "candidate"\n')          # truncated line
            fatal = [w for p, w in check_artifacts.check_artifacts() if "wind_shadow" in str(p)]
            self.assertEqual(fatal, [])
            self.assertTrue(any("zz-gate-probe" in str(p) for p, _w in check_artifacts.shadow_log_report()))
        finally:
            probe.unlink(missing_ok=True)
            if created:
                shutil.rmtree(wdir, ignore_errors=True)


class FreezeInvariantTests(unittest.TestCase):
    def test_freeze_hashes_match_files_R6(self):
        text = (ROOT / "models/wind_shadow/FREEZE.md").read_text()
        rows = re.findall(r"\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|", text)
        self.assertGreaterEqual(len(rows), 5)
        for path, sha in rows:
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), sha, path)
        self.assertEqual(json.loads((ROOT / "models/wind_shadow/manifest.json").read_text())["candidate_id"], ws.CANDIDATE_ID)

    def test_official_trial_log_is_valid_and_bound(self):
        wdir = ROOT / "data" / "wind_shadow"
        if not wdir.exists():
            self.skipTest("no trial log yet")
        text = (ROOT / "models/wind_shadow/FREEZE.md").read_text()
        freeze = dict(re.findall(r"\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|", text))
        for f in sorted(wdir.glob("*.jsonl")):
            self.assertEqual(ws.validate_file(str(f)), [], f)
            for line in f.read_text().splitlines():
                r = json.loads(line)
                if r.get("collection") == "official" and r.get("candidate_id") == ws.CANDIDATE_ID:
                    self.assertEqual(r["manifest_sha256"], freeze["models/wind_shadow/manifest.json"])
                    self.assertEqual(r["runtime_sha256"], freeze["forecast/wind_shadow.py"])


def _ev():
    spec = importlib.util.spec_from_file_location("ev", ROOT / "history/scripts/evaluate_wind_shadow.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def _obs(n, surge_fn, invalid=()):
    base = dt.datetime(2026, 10, 1, tzinfo=UTC)
    out = {}
    for i in range(n):
        t = base + dt.timedelta(hours=i)
        s = surge_fn(i); pred = 4.0 + 2.0 * math.sin(i / 2)
        out[t] = {"pred": pred, "obs": None if i in invalid else pred + s, "surge": None if i in invalid else s,
                  "valid": i not in invalid, "reason": "test gap" if i in invalid else None}
    return out


def _rec(t, cand, base, status="candidate"):
    return {"issuance_utc": t.isoformat(), "nominal_issuance_hour_utc": t.isoformat(), "status": status,
            "collection": "official", "leads": {"start": (t + dt.timedelta(hours=1)).isoformat()},
            "candidate_surge_ft": [cand] * 48, "baseline_surge_ft": [base] * 48, "production_model_version": "v0.10.6",
            "production_curve_tide_navd88": [None] * 48, "nws_outlook_surge": [None] * 48}


class EvaluatorTests(unittest.TestCase):
    def test_gap_resets_the_six_hour_count_R1(self):
        ev = _ev()
        obs = _obs(200, lambda i: 1.5 if i in (10, 11, 12, 13, 14, 16) else 0.0, invalid={15})
        t0 = min(obs)
        self.assertEqual(ev.episodes(obs, t0, t0 + dt.timedelta(hours=199)), [])

    def test_gap_resets_the_quiet_tail_and_completion_time_is_actual_R1(self):
        ev = _ev()
        obs = _obs(200, lambda i: 1.5 if 10 <= i < 20 else 0.0, invalid={44})
        t0 = min(obs)
        e = ev.episodes(obs, t0, t0 + dt.timedelta(hours=199))[0]
        self.assertEqual(e["end"], t0 + dt.timedelta(hours=19))
        self.assertEqual(e["completed_at"], t0 + dt.timedelta(hours=44 + 48))   # quiet run restarts after the gap
        short = _obs(20 + 24 + 1 + 24, lambda i: 1.5 if 10 <= i < 20 else 0.0, invalid={44})
        self.assertFalse(ev.episodes(short, t0, t0 + dt.timedelta(hours=68))[0]["completed"])

    def test_opportunity_count_is_consistent_R2(self):
        ev = _ev()
        obs = _obs(24, lambda i: 0.2)
        t0 = min(obs)
        slots = {t0 + dt.timedelta(hours=k): _rec(t0 + dt.timedelta(hours=k), 0.2, 0.3) for k in range(4)}
        rep = ev.evaluate(slots, obs, t0 + dt.timedelta(hours=3, minutes=30))
        self.assertEqual(rep["opportunities"], 4); self.assertEqual(rep["slot_states"]["missing"], 0)

    def test_sparse_records_are_inconclusive_not_pass_R1_R2(self):
        ev = _ev()
        storms = lambda i: 1.5 if (i % 300) in range(10, 20) else 0.0       # 5 storms over 1,464 h
        obs = _obs(1464 + 200, storms)
        t0 = min(obs)
        slots = {t0 + dt.timedelta(hours=k): _rec(t0 + dt.timedelta(hours=k), 0.0, 1.0) for k in range(0, 30)}
        rep = ev.evaluate(slots, obs, t0 + dt.timedelta(hours=1464 + 199))
        self.assertIn("INCONCLUSIVE", rep["verdict"])
        self.assertTrue(any("coverage" in x for x in rep["inconclusive_because"]))

    def test_observation_qc_R2(self):
        ev = _ev()
        wl = {"data": [{"t": "2026-10-01 00:00", "v": "5.0", "f": "0,0,0,0"},
                       {"t": "2026-10-01 01:00", "v": "5.0"},
                       {"t": "2026-10-01 02:00", "v": "5.0", "f": "0,x,0,0"},
                       {"t": "2026-10-01 03:00", "v": "NaN", "f": "0,0,0,0"},
                       {"t": "2026-10-01 04:00", "v": "5.0", "f": "0,0,1,0"}]}
        pr = {"predictions": [{"t": f"2026-10-01 0{h}:00", "v": "4.0"} for h in range(6)]}
        o = ev.parse_observations(wl, pr)
        valid = [t.hour for t, r in sorted(o.items()) if r["valid"]]
        self.assertEqual(valid, [0])
        self.assertEqual(o[dt.datetime(2026, 10, 1, 5, tzinfo=UTC)]["reason"], "no observation")

    def test_identity_binding_R6(self):
        ev = _ev()
        d = tempfile.mkdtemp()
        good = dict(_rec(T0, 0.1, 0.2), candidate_id="c", manifest_sha256="a" * 64, runtime_sha256="b" * 64)
        rows = [good, dict(good, manifest_sha256="z" * 64, issuance_utc="2026-09-24T11:00:00Z",
                           nominal_issuance_hour_utc="2026-09-24T11:00:00Z"),
                dict(good, collection="preview"), dict(good, manifest_sha256=None)]
        Path(d, "2026-09.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        slots, excluded = ev.load_records(d, "c", "a" * 64, "b" * 64)
        self.assertEqual(len(slots), 1)
        self.assertEqual(excluded, {"manifest hash mismatch": 1, "not official collection": 1, "missing manifest identity": 1})

    def test_comparators_and_episode_maes_R3(self):
        ev = _ev()
        obs = _obs(24 * 20, lambda i: 1.5 if 50 <= i < 70 else 0.1)
        t0 = min(obs)
        slots = {}
        for k in range(24 * 10):
            t = t0 + dt.timedelta(hours=k)
            r = _rec(t, 0.1, 0.4)
            r["production_curve_tide_navd88"] = [obs[t + dt.timedelta(hours=h)]["pred"] + 0.3 + (-2.82) for h in range(1, 49)]
            r["nws_outlook_surge"] = [[0.2, "nwps"]] * 48
            slots[t] = r
        rep = ev.evaluate(slots, obs, t0 + dt.timedelta(days=20), replay={})
        l24 = rep["leads"][24]
        self.assertIn("v0.10.6", l24["vs_actual_production_curve"])
        self.assertAlmostEqual(l24["vs_actual_production_curve"]["v0.10.6"]["production"]["bias"],
                               l24["vs_actual_production_curve"]["v0.10.6"]["production"]["bias"])
        self.assertIn("nwps", l24["vs_nws_petss_guidance"])
        self.assertTrue(l24["episodes"]["rows"]); self.assertIn("mae_candidate", l24["episodes"]["rows"][0])
        self.assertIn("revision_mean_candidate", rep["continuity"])
        self.assertEqual(l24["vs_actual_production_curve_note"], "within the published core reach")
        self.assertIn("no production comparator", rep["leads"][48]["vs_actual_production_curve_note"])

    def test_rain_tank_sensitivity_joins_the_replay_archive_R3(self):
        ev = _ev()
        from forecast import replay_archive as ra
        t = T0
        r = _rec(t, 1.0, 0.5)
        times = [t + dt.timedelta(hours=h) for h in range(1, 49)]
        replay = {r["issuance_utc"]: {"qpf_hourly": ra.columnar(times, in_hr=[0.6] * 3 + [0.0] * 45),
                                      "outlook_hourly": ra.columnar(times, astro_mllw=[6.0] * 48)}}
        out = ev.rain_tank_sensitivity({t: r}, replay)
        self.assertEqual(out["wet_events"], 1)
        self.assertEqual(out["treatment"], "descriptive only (< 3 wet events)")
        self.assertIsNotNone(out["wet_peak_change_in_mean"])


if __name__ == "__main__":
    unittest.main()
