"""Wind-shadow candidate (SHADOW ONLY): construction, isolation from
production, the record/gate round trip, and the frozen evaluator's rules."""
import copy, datetime as dt, importlib.util, json, math, os, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch

from forecast import flood_forecast_daily as ff
from forecast import surge_decay as sd
from forecast import wind_shadow as ws

UTC = dt.timezone.utc
ROOT = Path(__file__).resolve().parents[1]
T = dt.datetime(2026, 9, 24, 10, 30, tzinfo=UTC)
MANIFEST = {"candidate_id": "test-c", "theta_deg": 70.0, "latency_h": 6, "correction_cap_ft": 3.0,
            "latitude": 40.4669, "longitude": -74.0094, "model": "gfs_seamless", "forecast_hours": 61,
            "navd88_offset_ft": -2.82, "local_enhancement_ft": 0.0,
            "coefficients": {str(h): [0.001, -0.02, -0.01, 0.05] for h in range(1, 49)}}


def _forecast(rung="fresh"):
    return {"generated_utc": "2026-09-24T10:30:00Z", "model_version": "v0.10.6",
            "water_series_input": {"decay": {"rung": rung, "surge_obs_ft": 1.5, "observation_utc": "2026-09-24T10:18:00Z",
                                             "mean_ft": 0.53, "mean_source": "m", "tau_h": 36.0, "age_h": 0.2}},
            "outlook_7d": {"series": [{"utc": "2026-09-24T12:00:00Z", "astro_mllw": 4.0, "tide_navd88": 2.9,
                                       "surge_source": "nwps"}]}}


def _inputs(complete=True):
    init, note = ws.select_run(T, 6)
    hours = {}
    for k in range(0, 62):
        v = init + dt.timedelta(hours=k)
        hours[v] = (20.0, 60.0, 1005.0 - 0.1 * k)
    if not complete:
        hours.pop(dt.datetime(2026, 9, 24, 20, tzinfo=UTC))
    return {"errors": [], "run_init": init, "run_note": note, "meta": None, "run_hours": hours,
            "retrieved_utc": "x", "raw_sha256": "s", "raw_body": "{}", "p_obs_now": 1010.0,
            "p_obs_time": "2026-09-24T10:00:00Z", "p_anom": -3.0}


class ConstructionTests(unittest.TestCase):
    def test_run_selection_latency_and_meta(self):
        self.assertEqual(ws.select_run(T, 6)[0], dt.datetime(2026, 9, 24, 0, tzinfo=UTC))
        init, note = ws.select_run(T, 6, meta_init=dt.datetime(2026, 9, 23, 18, tzinfo=UTC))
        self.assertEqual(init, dt.datetime(2026, 9, 23, 18, tzinfo=UTC))
        self.assertIn("previous cycle", note)

    def test_features_need_complete_windows_and_pressure(self):
        inp = _inputs()
        f, why = ws.features(inp["run_hours"], T, 1010.0, -3.0, 24, 70.0)
        self.assertIsNone(why)
        self.assertAlmostEqual(f[0], 400 * math.cos(math.radians(-10)), places=9)
        self.assertEqual(f[2], -3.0)
        f, why = ws.features(_inputs(complete=False)["run_hours"], T, 1010.0, -3.0, 24, 70.0)
        self.assertIsNone(f); self.assertIn("incomplete", why)
        self.assertIsNone(ws.features(inp["run_hours"], T, None, -3.0, 6, 70.0)[0])

    def test_correction_cap(self):
        c, cap = ws.correction([1.0, 0, 0, 0], (10.0, 0, 0), 3.0)
        self.assertEqual((c, cap), (3.0, True))

    def test_baseline_is_the_production_formula(self):
        f = _forecast()
        d = f["water_series_input"]["decay"]
        anchor = sd.SurgeAnchor("fresh", 0.53, "m", 1.5, dt.datetime(2026, 9, 24, 10, 18, tzinfo=UTC))
        for h in (1, 12, 48):
            t = T.replace(minute=0) + dt.timedelta(hours=h)
            self.assertAlmostEqual(ws.baseline_surge(d, t), anchor.at(t), places=12)

    def test_record_candidate_fallback_and_comparator(self):
        r = ws.build_record(_forecast(), MANIFEST, _inputs(), T)
        self.assertEqual(r["status"], "candidate")
        self.assertEqual(len(r["candidate_surge_ft"]), 48)
        self.assertNotEqual(r["candidate_surge_ft"][23], r["baseline_surge_ft"][23])
        self.assertEqual(r["nws_outlook_surge"][1], [round(2.9 + 2.82 - 4.0, 4), "nwps"])   # 12Z = lead 2
        r = ws.build_record(_forecast("stale-download"), MANIFEST, _inputs(), T)
        self.assertEqual(r["status"], "fallback"); self.assertIn("not fresh", r["fallback_reason"])
        self.assertEqual(r["candidate_surge_ft"], r["baseline_surge_ft"])
        r = ws.build_record(_forecast(), MANIFEST, _inputs(complete=False), T)
        self.assertEqual(r["status"], "fallback"); self.assertIn("incomplete", r["fallback_reason"])


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.m = os.path.join(self.d, "manifest.json")
        Path(self.m).write_text(json.dumps(MANIFEST))

    def test_run_never_raises_and_records_failures(self):
        def boom(url, params, timeout):
            raise OSError("down")
        f = _forecast(); before = copy.deepcopy(f)
        msg = ws.run(f, now_utc=T, manifest_path=self.m, directory=self.d, get=boom)
        self.assertIn("fallback", msg)
        self.assertEqual(f, before)                                   # production dict untouched
        path = os.path.join(self.d, "2026-09.jsonl")
        self.assertEqual(ws.validate_file(path), [])
        rec = json.loads(Path(path).read_text().splitlines()[-1])
        self.assertIn("unavailable", rec["fallback_reason"])

    def test_wall_clock_bounds_a_slow_feed(self):
        def slow(url, params, timeout):
            time.sleep(1.0); raise OSError("late")
        t0 = time.monotonic()
        msg = ws.run(_forecast(), now_utc=T, manifest_path=self.m, directory=self.d, get=slow, wall_clock_s=0.2)
        self.assertLess(time.monotonic() - t0, 0.6)
        self.assertIn("error", msg)
        rec = json.loads(Path(os.path.join(self.d, "2026-09.jsonl")).read_text().splitlines()[-1])
        self.assertEqual(rec["status"], "error"); self.assertIn("wall-clock", rec["fallback_reason"])
        time.sleep(1.1)

    def test_main_wrapper_isolates_production(self):
        holder_forecast = {"generated_utc": "2026-09-24T10:30:00Z"}
        def core(holder):
            holder["forecast"], holder["json_written"] = holder_forecast, True
        with patch.object(ff, "_main_core", side_effect=core), \
                patch.object(ws, "run", side_effect=RuntimeError("shadow bug")) as run:
            ff.main()                                                  # must not raise
            run.assert_called_once()
        with patch.object(ff, "_main_core", side_effect=core), patch.object(ws, "run") as run, \
                patch.dict(os.environ, {"BARNACLE_WIND_SHADOW": "0"}):
            ff.main(); run.assert_not_called()
        with patch.object(ff, "_main_core", side_effect=lambda h: None), patch.object(ws, "run") as run:
            ff.main(); run.assert_not_called()                         # no JSON written -> no shadow

    def test_gate_rejects_malformed_lines(self):
        p = os.path.join(self.d, "bad.jsonl")
        Path(p).write_text('{"v":1,"status":"fallback"}\n')
        self.assertTrue(ws.validate_file(p))


def _evaluator():
    spec = importlib.util.spec_from_file_location("ev", ROOT / "history/scripts/evaluate_wind_shadow.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


class EvaluatorTests(unittest.TestCase):
    def _obs(self, hours, surge_fn):
        base = dt.datetime(2026, 10, 1, tzinfo=UTC)
        return {base + dt.timedelta(hours=i): (surge_fn(i), 5.0 + surge_fn(i) + math.sin(i / 2), 5.0 + math.sin(i / 2), True)
                for i in range(hours)}

    def test_episode_rules(self):
        ev = _evaluator()
        s = lambda i: 1.5 if 10 <= i < 20 or 40 <= i < 50 else 0.0      # 30-h break < 48: merged
        obs = self._obs(200, s)
        t0 = min(obs)
        eps = ev.episodes(obs, t0, t0 + dt.timedelta(hours=199))
        self.assertEqual(len(eps), 1)
        self.assertEqual(eps[0]["start"], t0 + dt.timedelta(hours=10))
        self.assertEqual(eps[0]["end"], t0 + dt.timedelta(hours=49))
        self.assertTrue(eps[0]["completed"])
        obs2 = self._obs(200, lambda i: 1.5 if 10 <= i < 15 else 0.0)     # only 5 hours: no episode
        self.assertEqual(ev.episodes(obs2, t0, t0 + dt.timedelta(hours=199)), [])
        obs3 = dict(obs2); obs3[t0 + dt.timedelta(hours=15)] = (None, None, 5.0, False)
        obs3[t0 + dt.timedelta(hours=16)] = (1.5, 6.5, 5.0, True)          # missing hour does not supply the 6th
        self.assertEqual(len(ev.episodes(obs3, t0, t0 + dt.timedelta(hours=199))), 1)

    def test_interim_and_inconclusive_without_storms(self):
        ev = _evaluator()
        obs = self._obs(24 * 10, lambda i: 0.2)
        t0 = min(obs)
        recs = {}
        for i in range(24 * 5):
            t = t0 + dt.timedelta(hours=i)
            recs[t] = {"issuance_utc": t.isoformat(), "status": "candidate", "leads": {"start": (t + dt.timedelta(hours=1)).isoformat()},
                       "candidate_surge_ft": [0.2] * 48, "baseline_surge_ft": [0.3] * 48}
        rep = ev.evaluate(recs, obs, t0 + dt.timedelta(days=10))
        self.assertTrue(rep["verdict"].startswith("INTERIM (INCONCLUSIVE"))
        self.assertEqual(rep["leads"][24]["primary"]["all"]["mae_candidate"], 0.0)
        self.assertEqual(rep["leads"][24]["primary"]["all"]["n"], 24 * 5)       # all matured, all valid
        rep = ev.evaluate(recs, obs, t0 + dt.timedelta(days=5, hours=12))
        self.assertLess(rep["leads"][24]["primary"]["all"]["n"], 24 * 5)       # targets < 48 h old wait


if __name__ == "__main__":
    unittest.main()


class PressureSelectionTests(unittest.TestCase):
    def test_issuance_hour_value_from_6min_and_30day_anomaly(self):
        t0 = dt.datetime(2026, 9, 24, 14, tzinfo=UTC)
        iss = t0 + dt.timedelta(minutes=12)

        def fake(url, params, timeout):
            if url == ws.META_URL:
                raise OSError("no meta")
            if url == ws.SINGLE_RUNS_URL:
                raise OSError("no run")
            if params.get("interval") == "h":
                rows = [{"t": (t0 - dt.timedelta(hours=k)).strftime("%Y-%m-%d %H:%M"), "v": "1000.0"} for k in range(1, 24 * 31)]
            else:
                rows = [{"t": (t0 + dt.timedelta(minutes=m)).strftime("%Y-%m-%d %H:%M"), "v": "1004.0"} for m in (-6, 0, 6, 12)]
            return json.dumps({"data": rows}).encode()
        out = ws.fetch_inputs(iss, MANIFEST, get=fake)
        self.assertEqual(out["p_obs_now"], 1004.0)
        self.assertEqual(out["p_obs_time"], "2026-09-24T14:00:00Z")
        self.assertEqual(out["p_anom"], 4.0)
