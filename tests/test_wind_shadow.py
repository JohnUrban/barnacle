"""Wind-shadow candidate c2 (SHADOW ONLY): construction, production isolation,
opt-in collection, record/quarantine/gate behaviour, frozen identity, and the
frozen evaluator's declared rules. Regressions for audit 2026-09-24-a3 R1-R8
(round 01) and the round-03 findings (gate CLI, bundle enforcement, rain
initial condition, raw guidance, availability/provenance, mode exclusion)."""
import copy, datetime as dt, gzip, hashlib, importlib.util, json, math, os, re, shutil, subprocess, sys, tempfile, time, unittest
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


def _series():
    """Production-like 30-min water series, 04:30Z .. 16:30Z next day (station-local stamps)."""
    out = []
    t = dt.datetime(2026, 9, 24, 4, 30, tzinfo=UTC)
    while t <= dt.datetime(2026, 9, 25, 16, 30, tzinfo=UTC):
        loc = t - dt.timedelta(hours=4)
        out.append({"time": loc.strftime("%Y-%m-%d %H:%M") + "-04:00", "tide_navd88": 1.2})
        t += dt.timedelta(minutes=30)
    return out


def _forecast(rung="fresh", tau=36.0):
    return {"generated_utc": "2026-09-24T10:30:00Z", "model_version": "v0.10.6",
            "water_series_input": {"decay": {"rung": rung, "surge_obs_ft": 1.5, "observation_utc": "2026-09-24T10:18:00Z",
                                             "mean_ft": 0.53, "mean_source": "m", "tau_h": tau, "age_h": 0.2}},
            "water_series": _series(),
            "outlook_7d": {"series": [{"utc": "2026-09-24T12:00:00Z", "astro_mllw": 4.0, "tide_navd88": 2.9,
                                       "surge_source": "nwps"},
                                      {"utc": "2026-09-24T13:00:00Z", "astro_mllw": 4.0, "tide_navd88": 2.0,
                                       "surge_source": "observed_decay"}]}}


def _context(qpf=True):
    hrs = [T0 + dt.timedelta(hours=k) for k in range(-8, 40)]
    return {"outlook_data": {"astro_hourly": {"points": [{"utc": t.isoformat(), "mllw": 4.0} for t in hrs]},
                             "nwps": {"issued": "2026-09-24T09:10:00Z",
                                      "series": [{"utc": t.isoformat(), "ft": 5.0} for t in hrs[:20]]},
                             "petss": {"cycle": "2026-09-24T00:00:00Z",
                                       "p10": [{"utc": t.isoformat(), "surge_ft": 0.4} for t in hrs],
                                       "p90": [{"utc": t.isoformat(), "surge_ft": 0.8} for t in hrs]}},
            "outlook_health": {"nwps": {"fetched_at": "2026-09-24T10:29:00Z"}, "petss": {"fetched_at": "2026-09-24T06:00:00Z"}},
            "qpf_hourly": ([(T0 + dt.timedelta(hours=k), 0.5 if k < 0 else 0.0) for k in range(-8, 40)] if qpf else None)}


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
        self.assertEqual(ws.select_run(T, 6, c + dt.timedelta(hours=6), T)[0], c)                   # newer run by issuance
        # round 03: newer metadata available only AFTER issuance does not establish the older run
        why = ws.select_run(T, 6, c + dt.timedelta(hours=6), T + dt.timedelta(minutes=5))[1]
        self.assertIn("not established", why)

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
        rec = ws.pre_network_part(_forecast(), MANIFEST, "preview", T, context=_context())
        self.assertEqual(rec["status"], "fallback")                      # baseline exists before any network
        self.assertEqual(len(rec["baseline_surge_ft"]), 48)
        self.assertEqual(rec["production_curve_tide_navd88"][0], 1.2)    # 11Z = lead 1
        self.assertEqual(rec["barnacle_outlook_surge"][1], [round(2.9 + 2.82 - 4.0, 4), "nwps"])
        self.assertEqual(rec["barnacle_outlook_surge"][2][1], "observed_decay")
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
        # rain inputs: candidate surge only after issuance, shared history before
        ri = full["rain_inputs"]
        times = ws.rain_times(ri)
        self.assertEqual(ri["series_start"], "2026-09-24T04:30:00Z"); self.assertEqual(ri["step_min"], 30)
        for t, b, c in zip(times, ri["baseline_surge_ft"], ri["candidate_surge_ft"]):
            self.assertEqual(b is None, t <= T); self.assertEqual(c is None, t <= T)
        self.assertEqual(ri["qpf_in_hr"][0], 0.5)                        # pre-issuance rain retained
        i24 = times.index(T0 + dt.timedelta(hours=24))
        self.assertAlmostEqual(ri["candidate_surge_ft"][i24] - ri["baseline_surge_ft"][i24], full["correction_ft"][23], places=3)

    def test_raw_guidance_is_separate_from_barnacle_outlook_R3(self):
        rec = ws.pre_network_part(_forecast(), MANIFEST, "preview", T, context=_context())
        g = rec["guidance"]
        self.assertEqual(g["nwps_raw"]["surge_ft"][0], 1.0)              # 5.0 - 4.0, no advisory correction
        self.assertEqual(g["nwps_raw"]["surge_ft"][47], None)            # beyond the NWPS series
        self.assertEqual((g["nwps_raw"]["issued"], g["nwps_raw"]["retrieved"]), ("2026-09-24T09:10:00Z", "2026-09-24T10:29:00Z"))
        self.assertEqual(g["petss_mid"]["surge_ft"][10], 0.6); self.assertEqual(g["petss_mid"]["cycle"], "2026-09-24T00:00:00Z")
        none = ws.pre_network_part(_forecast(), MANIFEST, "preview", T, context={})
        self.assertIsNotNone(none["guidance"]["nwps_raw"]["reason"])
        self.assertIsNone(none["rain_inputs"]["qpf_in_hr"]); self.assertIn("unavailable", none["rain_inputs"]["qpf_reason"])


class PressureTests(unittest.TestCase):
    def test_qc_rows(self):
        body = json.dumps({"data": [{"t": "2026-09-24 10:00", "v": "1010.0", "f": "0,0,0"},
                                    {"t": "2026-09-24 10:06", "v": "1010.1", "f": "0,1,0"},
                                    {"t": "2026-09-24 10:12", "v": "nan", "f": "0,0,0"},
                                    {"t": "2026-09-24 10:18", "v": "1010.2"},
                                    {"t": "2026-09-24 10:24", "v": "1010.3", "f": "0,0"}]}).encode()
        rows, rejected = ws._pressure_rows(body)
        self.assertEqual((len(rows), len(rejected)), (1, 4))

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
                rows += rows[5:25]                                          # duplicated timestamps
                rows.append({"t": "2026-09-20 00:00", "v": "999.0", "f": "0,1,0"})
            else:
                rows = [{"t": (T0 + dt.timedelta(minutes=m)).strftime("%Y-%m-%d %H:%M"), "v": "1004.0", "f": "0,0,0"}
                        for m in (-6, 0, 6, 12, 18, 24)]
            return json.dumps({"data": rows}).encode()
        out = ws.fetch_inputs(T, MANIFEST, get=fake)
        p = out["pressure"]
        self.assertEqual(p["prior_hours"], 720)                               # distinct hours only
        self.assertEqual((p["now_hpa"], p["time_utc"], p["anom_30d_hpa"]), (1004.0, "2026-09-24T10:00:00Z", 4.0))
        self.assertEqual(p["basis"], "value at the issuance hour")
        self.assertEqual(len(p["responses"]), 2); self.assertTrue(all(len(r["sha256"]) == 64 for r in p["responses"]))
        hourly = p["responses"][1]
        raw = ws.un_gz_b64(hourly["body_gzip_b64"])                        # lossless raw body (round 03 R5)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), hourly["sha256"])
        self.assertEqual(hourly["rows_rejected_qc"], 1); self.assertEqual(hourly["rejected_rows"][0]["f"], "0,1,0")

    def test_current_pressure_must_not_postdate_issuance_R5(self):
        def fake(url, params, timeout):
            if url != ws.COOPS_URL:
                raise OSError("x")
            if params.get("interval") == "h":
                rows = [{"t": (T0 - dt.timedelta(hours=k)).strftime("%Y-%m-%d %H:%M"), "v": "1000.0", "f": "0,0,0"}
                        for k in range(1, 24 * 31)]
            else:                                                            # only a reading 60 min AFTER issuance
                rows = [{"t": (T + dt.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"), "v": "1004.0", "f": "0,0,0"}]
            return json.dumps({"data": rows}).encode()
        p = ws.fetch_inputs(T, MANIFEST, get=fake)
        self.assertIsNone(p["pressure"]["now_hpa"])
        self.assertTrue(any("pressure unavailable" in e for e in p["errors"]))


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
        env = {k: v for k, v in os.environ.items() if not k.startswith("BARNACLE_WIND_SHADOW")}
        prod = {"dry_run": False, "no_send": False}
        with patch.dict(os.environ, dict(env, BARNACLE_WIND_SHADOW_PREVIEW_DIR=self.d), clear=True):
            self.assertEqual(ws.collection_target(prod), ("preview", self.d, None))
        with patch.dict(os.environ, dict(env, BARNACLE_WIND_SHADOW_TRIAL="1"), clear=True):
            self.assertEqual(ws.collection_target(prod)[0], "official")
            # round 03 R8: the opt-in never makes a regeneration/test run official
            for mode in ({"dry_run": True, "no_send": False}, {"dry_run": False, "no_send": True}, None):
                self.assertEqual(ws.collection_target(mode)[:2], (None, None))
                get = unittest.mock.Mock()
                self.assertIn("never official", ws.run(_forecast(), mode=mode, get=get)); get.assert_not_called()
        with patch.dict(os.environ, dict(env, BARNACLE_WIND_SHADOW_TRIAL="1", BARNACLE_WIND_SHADOW_PREVIEW_DIR=self.d), clear=True):
            self.assertEqual(ws.collection_target({"dry_run": True})[:2], ("preview", self.d))

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

    def test_identity_mismatch_writes_an_identified_disabled_record(self):
        bad = os.path.join(self.d, "other.json")
        Path(bad).write_text(json.dumps(dict({k: v for k, v in MANIFEST.items() if k != "_sha256"}, candidate_id="x")))
        get = unittest.mock.Mock()
        ws.run(_forecast(), now_utc=T, manifest_path=bad, collection="preview", directory=self.d, get=get)
        rec = json.loads(Path(self.d, "2026-09.jsonl").read_text().splitlines()[-1])
        self.assertEqual((rec["status"], rec["candidate_id"]), ("disabled", ws.CANDIDATE_ID))
        get.assert_not_called()

    def test_official_collection_refuses_an_unfrozen_manifest_R6(self):
        """Codex round 03: tau 36 -> 999 under the same id logged an OFFICIAL candidate."""
        m = json.loads((ROOT / "models/wind_shadow/manifest.json").read_text()); m["tau_h"] = 999.0
        alt = os.path.join(self.d, "manifest.json"); Path(alt).write_text(json.dumps(m))
        get = unittest.mock.Mock()
        msg = ws.run(_forecast(), now_utc=T, manifest_path=alt, collection="official", directory=self.d, get=get)
        self.assertIn("disabled", msg); get.assert_not_called()
        rec = json.loads(Path(self.d, "2026-09.jsonl").read_text().splitlines()[-1])
        self.assertEqual(rec["status"], "disabled"); self.assertIsNone(rec["candidate_surge_ft"])
        self.assertIn("not the frozen manifest", rec["fallback_reason"])
        self.assertEqual(ws.validate_record(rec), [])

    def test_official_collection_refuses_a_changed_bundle_file_R6(self):
        mirror = _mirror(self.d)
        with open(os.path.join(mirror, "history/scripts/evaluate_wind_shadow.py"), "a") as f:
            f.write("# harmless comment\n")
        get = unittest.mock.Mock()
        msg = ws.run(_forecast(), now_utc=T, collection="official", directory=self.d, get=get, root=mirror)
        self.assertIn("disabled", msg); self.assertIn("evaluate_wind_shadow.py", msg); get.assert_not_called()

    def test_official_collection_with_the_frozen_bundle_proceeds(self):
        def down(url, params, timeout):
            raise OSError("down")
        msg = ws.run(_forecast(), now_utc=T, collection="official", directory=self.d, get=down, context=_context())
        rec = json.loads(Path(self.d, "2026-09.jsonl").read_text().splitlines()[-1])
        self.assertEqual(rec["status"], "fallback", msg); self.assertTrue(rec["bundle_ok"])
        self.assertEqual(rec["bundle_sha256"], ws.check_bundle()["bundle_sha256"])
        self.assertEqual(rec["rain_inputs"]["candidate_surge_ft"][-1], rec["rain_inputs"]["baseline_surge_ft"][-1])

    def test_invalid_record_is_quarantined_not_logged_R7(self):
        path, bad = ws.append_record({"issuance_utc": "2026-09-24T10:30:00Z", "status": "candidate"}, self.d)
        self.assertTrue(bad); self.assertIn("quarantine", path)
        self.assertFalse(Path(self.d, "2026-09.jsonl").exists())

    def test_main_wrapper_opt_in_and_isolation_R7_R8(self):
        fc = {"generated_utc": "2026-09-24T10:30:00Z"}
        def core(h):
            h["forecast"], h["json_written"] = fc, True
            h["mode"] = {"dry_run": False, "no_send": False}
        env = {k: v for k, v in os.environ.items() if not k.startswith("BARNACLE_WIND_SHADOW")}
        with patch.dict(os.environ, env, clear=True), patch.object(ff, "_main_core", side_effect=core), \
                patch.object(ws, "run") as run:
            ff.main(); run.assert_not_called()                          # --no-send/--dry-run locally: nothing
        with patch.dict(os.environ, dict(env, BARNACLE_WIND_SHADOW_TRIAL="1"), clear=True), \
                patch.object(ff, "_main_core", side_effect=core), patch.object(ws, "run", side_effect=RuntimeError("bug")) as run:
            ff.main(); run.assert_called_once()                         # a crashing shadow cannot fail the run
        # round 03 R8: the parsed mode reaches the shadow; --no-send/--dry-run write nothing even with the opt-in
        for flag in ("dry_run", "no_send"):
            def core_mode(h, flag=flag):
                h["forecast"], h["json_written"] = _forecast(), True
                h["mode"] = {"dry_run": flag == "dry_run", "no_send": flag == "no_send"}
            with patch.dict(os.environ, dict(env, BARNACLE_WIND_SHADOW_TRIAL="1"), clear=True), \
                    patch.object(ff, "_main_core", side_effect=core_mode), patch.object(ws, "run") as run, \
                    patch.object(ws, "fetch_inputs") as fetch, patch.object(ws, "append_record") as app:
                ff.main()
                run.assert_not_called(); fetch.assert_not_called(); app.assert_not_called()
        # production mode: the shadow receives the official target, the mode and the as-issued context
        def core_prod(h):
            h["forecast"], h["json_written"] = _forecast(), True
            h["mode"] = {"dry_run": False, "no_send": False}
        with patch.dict(os.environ, dict(env, BARNACLE_WIND_SHADOW_TRIAL="1"), clear=True), \
                patch.object(ff, "_main_core", side_effect=core_prod), patch.object(ws, "run", return_value="x") as run:
            ff.main()
            kw = run.call_args.kwargs
            self.assertEqual((kw["collection"], kw["directory"]), ("official", ws.TRIAL_DIR))
            self.assertIn("qpf_hourly", kw["context"])

    def test_gate_main_survives_malformed_shadow_evidence_R7(self):
        """Round 03: [] / null / unreadable / validator crash must never change the exit code."""
        tmp = tempfile.mkdtemp()
        wdir = Path(tmp, "data", "wind_shadow"); wdir.mkdir(parents=True)
        cases = {"a.jsonl": "[]\n", "b.jsonl": "null\n", "c.jsonl": '{"v": 3\n', "d.jsonl": "\"text\"\n"}
        for name, body in cases.items():
            (wdir / name).write_text(body)
        (wdir / "e.jsonl").mkdir()                                       # unreadable as a file
        (wdir / "f.jsonl").write_bytes(b"\xff\xfe\n")                  # not UTF-8
        with patch.object(check_artifacts, "ROOT", tmp), patch.object(check_artifacts, "check_artifacts", return_value=[]):
            self.assertEqual(check_artifacts.main(), 0)
            rep = check_artifacts.shadow_log_report(tmp)
            self.assertEqual({Path(p).name for p, _w in rep}, set(cases) | {"e.jsonl", "f.jsonl"})
            with patch.object(ws, "validate_file", side_effect=RuntimeError("validator bug")):
                self.assertEqual(check_artifacts.main(), 0)
                self.assertTrue(all("validator failed" in w for _p, w in check_artifacts.shadow_log_report(tmp)))
            with patch.object(check_artifacts, "shadow_log_report", side_effect=RuntimeError("report bug")):
                self.assertEqual(check_artifacts.main(), 0)
        # evidence is preserved, not deleted
        self.assertEqual((wdir / "a.jsonl").read_text(), "[]\n")
        # production failures still fail the gate
        with patch.object(check_artifacts, "ROOT", tmp), patch.object(check_artifacts, "check_artifacts",
                                                                       return_value=[(tmp, "real failure")]):
            self.assertEqual(check_artifacts.main(), 1)
        shutil.rmtree(tmp, ignore_errors=True)

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
        b = ws.check_bundle()
        self.assertTrue(b["ok"], b["problems"])
        self.assertEqual(ws.read_freeze()[0], ws.CANDIDATE_ID)

    def test_frozen_rain_reference_matches_its_golden_output(self):
        rr = _ev().rain_ref()
        t0 = dt.datetime(2026, 9, 24, 4, tzinfo=UTC)
        times = [t0 + dt.timedelta(minutes=30 * i) for i in range(20)]
        out = rr.simulate_pluvial_series(times, [3.68] * 20, [1.0] * 12 + [0.0] * 8)
        self.assertIsNone(out[0])
        self.assertAlmostEqual(max(x for x in out if x is not None), GOLDEN_TANK_PEAK, places=4)

    def test_official_trial_log_is_valid_and_bound(self):
        wdir = ROOT / "data" / "wind_shadow"
        if not wdir.exists():
            self.skipTest("no trial log yet")
        b = ws.check_bundle()
        first = None
        for f in sorted(wdir.glob("*.jsonl")):
            self.assertEqual(ws.validate_file(str(f)), [], f)
            for line in f.read_text().splitlines():
                r = json.loads(line)
                if r.get("collection") == "official" and r.get("candidate_id") == ws.CANDIDATE_ID:
                    first = first or r
        if first is not None:
            # the trial's bundle is fixed by its FIRST official record: editing a file AND its
            # FREEZE entry after the start fails here (round 03 R6); a change needs a new id
            self.assertEqual(first.get("bundle_sha256"), b["bundle_sha256"])


GOLDEN_TANK_PEAK = 4.620739756524687   # frozen tank at freeze time (= production then; Codex's 4.621 ft case)


def _mirror(tmp):
    """A copy of every file the frozen bundle and the evaluator need."""
    m = os.path.join(tmp, "mirror")
    for rel in list(ws.read_freeze()[1]) + ["forecast/station_time.py", "models/wind_shadow/FREEZE.md"]:
        os.makedirs(os.path.dirname(os.path.join(m, rel)), exist_ok=True)
        shutil.copy2(ROOT / rel, os.path.join(m, rel))
    return m


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
            "candidate_id": "c", "bundle_sha256": "B" * 64, "manifest_sha256": "a" * 64, "runtime_sha256": "b" * 64,
            "candidate_surge_ft": [cand] * 48, "baseline_surge_ft": [base] * 48, "production_model_version": "v0.10.6",
            "production_curve_tide_navd88": [None] * 48, "barnacle_outlook_surge": [None] * 48, "guidance": {}}


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
                       {"t": "2026-10-01 04:00", "v": "5.0", "f": "0,0,1,0"},
                       {"t": "2026-10-01 06:00", "v": "5.0", "f": "2,0,0,0"}]}
        pr = {"predictions": [{"t": f"2026-10-01 0{h}:00", "v": "4.0"} for h in range(7)]}
        o = ev.parse_observations(wl, pr)
        valid = [t.hour for t, r in sorted(o.items()) if r["valid"]]
        self.assertEqual(valid, [0, 6])                    # O is an outlier-sample COUNT, not a failure
        self.assertEqual(o[dt.datetime(2026, 10, 1, 6, tzinfo=UTC)]["outlier_samples"], 2)
        self.assertIn("tolerance flag", o[dt.datetime(2026, 10, 1, 4, tzinfo=UTC)]["reason"])
        self.assertEqual(o[dt.datetime(2026, 10, 1, 5, tzinfo=UTC)]["reason"], "no observation")

    def test_raw_outcome_bodies_are_replayed_and_verified_R5(self):
        ev = _ev()
        d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, "raw"))
        wl = json.dumps({"data": [{"t": "2026-10-01 00:00", "v": "5.0", "f": "0,0,0,0"}]}).encode()
        pr = json.dumps({"predictions": [{"t": "2026-10-01 00:00", "v": "4.0"}]}).encode()
        resp = []
        for product, body in (("water_level", wl), ("predictions", pr)):
            sha = hashlib.sha256(body).hexdigest()
            Path(d, "raw", sha + ".json").write_bytes(body)
            resp.append({"product": product, "sha256": sha, "file": f"raw/{sha}.json"})
        Path(d, "b.json").write_text(json.dumps({"water_level": {"data": []}, "predictions": {"predictions": []},
                                                 "responses": resp}))
        b = ev.load_observation_bundle(os.path.join(d, "b.json"))
        self.assertEqual(len(b["water_level"]["data"]), 1); self.assertIn("hashes verified", b["outcome_provenance"])
        Path(d, "raw", resp[0]["sha256"] + ".json").write_bytes(wl + b" ")
        with self.assertRaises(ValueError):
            ev.load_observation_bundle(os.path.join(d, "b.json"))

    def test_identity_binding_R6(self):
        ev = _ev()
        d = tempfile.mkdtemp()
        good = _rec(T0, 0.1, 0.2)
        at = lambda h: {"issuance_utc": f"2026-09-24T{h}:00:00Z", "nominal_issuance_hour_utc": f"2026-09-24T{h}:00:00Z"}
        disabled = dict(good, status="disabled", fallback_reason="bundle", baseline_surge_ft=None, **at("08"))
        rows = [disabled, good, dict(good, manifest_sha256="z" * 64, **at("11")),
                dict(good, collection="preview"), dict(good, manifest_sha256=None, **at("12")),
                dict(good, bundle_sha256="X" * 64, **at("13"))]
        Path(d, "2026-09.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n[]\n")
        slots, attempts, excluded, trial = ev.load_records(d, "c", "B" * 64, "a" * 64, "b" * 64)
        self.assertEqual(len(slots), 1)
        self.assertEqual(excluded, {"manifest hash mismatch": 1, "not official collection": 1, "missing manifest identity": 1,
                                    "bundle mismatch": 1, "disabled (bundle check failed at collection)": 1,
                                    "unparsable line": 1})
        # the trial starts at the FIRST official record (the disabled one), not the first valid one
        self.assertEqual(trial["start"], dt.datetime(2026, 9, 24, 8, tzinfo=UTC))
        obs = _obs(24, lambda i: 0.2)
        rep = ev.evaluate(slots, obs, dt.datetime(2026, 9, 24, 13, 30, tzinfo=UTC), rain=False,
                          attempts=attempts, trial_start=trial["start"])
        self.assertEqual(rep["opportunities"], 6)
        self.assertEqual(rep["slot_states"]["not_evaluable"], 4)
        self.assertEqual(rep["slot_states"]["missing"], 1)                  # 09Z
        self.assertEqual(rep["trial_start"], "2026-09-24T08:00:00+00:00")

    def test_comparators_and_episode_maes_R3(self):
        ev = _ev()
        obs = _obs(24 * 20, lambda i: 1.5 if 50 <= i < 70 else 0.1)
        t0 = min(obs)
        slots = {}
        for k in range(24 * 10):
            t = t0 + dt.timedelta(hours=k)
            r = _rec(t, 0.1, 0.4)
            r["production_curve_tide_navd88"] = [obs[t + dt.timedelta(hours=h)]["pred"] + 0.3 + (-2.82) for h in range(1, 49)]
            r["barnacle_outlook_surge"] = [[0.2, "observed_decay"]] * 48
            if k % 2 == 0:
                r["guidance"] = {"nwps_raw": {"surge_ft": [0.3] * 48}, "petss_mid": {"surge_ft": [None] * 48}}
            slots[t] = r
        rep = ev.evaluate(slots, obs, t0 + dt.timedelta(days=20), rain=False)
        l24 = rep["leads"][24]
        self.assertIn("v0.10.6", l24["vs_actual_production_curve"])
        self.assertAlmostEqual(l24["vs_actual_production_curve"]["v0.10.6"]["production"]["bias"],
                               l24["vs_actual_production_curve"]["v0.10.6"]["production"]["bias"])
        g = l24["vs_external_guidance"]
        self.assertAlmostEqual(g["nwps_raw"]["available_in_scored_pairs"], 0.5, places=2)
        self.assertEqual(g["petss_mid"]["available_in_scored_pairs"], 0.0)
        self.assertEqual(g["petss_mid"]["petss_mid"]["n"], 0)
        # Barnacle's observed-decay fallback is NOT counted as external guidance (round 03 R3)
        self.assertIn("observed_decay", l24["vs_barnacle_outlook"]["by_source"])
        self.assertIn("NOT external guidance", l24["vs_barnacle_outlook"]["note"])
        self.assertTrue(l24["episodes"]["rows"]); self.assertIn("mae_candidate", l24["episodes"]["rows"][0])
        self.assertIn("revision_mean_candidate", rep["continuity"])
        self.assertEqual(l24["vs_actual_production_curve_note"], "within the published core reach")
        self.assertIn("no production comparator", rep["leads"][48]["vs_actual_production_curve_note"])

    def test_rain_keeps_pre_issuance_storage_R3(self):
        """Codex round 03: rain 1 in/h 04:00-10:00Z, issuance 10:00Z, bay 3.68 ft. Restarting the
        tank at the first lead loses the stored water; the as-issued start keeps it."""
        ev = _ev(); rr = ev.rain_ref()
        start = dt.datetime(2026, 9, 24, 4, tzinfo=UTC); iss = dt.datetime(2026, 9, 24, 10, tzinfo=UTC)
        times = [start + dt.timedelta(minutes=30 * i) for i in range(73)]
        prod = [3.68] * 73
        rates = [1.0 if t < iss else 0.0 for t in times]
        after = [t > iss for t in times]
        ri = {"series_start": start.isoformat(), "step_min": 30, "issuance_utc": iss.isoformat(),
              "production_tide_navd88": prod, "production_surge_ft": [0.5] * 73,
              "production_pluvial_navd88": rr.simulate_pluvial_series(times, prod, rates),
              "baseline_surge_ft": [0.5 if a else None for a in after],
              "candidate_surge_ft": [0.7 if a else None for a in after], "qpf_in_hr": rates}
        r = dict(_rec(iss, 0.7, 0.5), rain_inputs=ri)
        out = ev.rain_tank_sensitivity({iss: r}, rr)
        self.assertEqual((out["wet_issuances"], out["wet_events"]), (1, 1))
        self.assertEqual(out["treatment"], "descriptive only (< 3 wet events)")
        curb = out["landmarks_wet"]["curb"]
        self.assertEqual(curb["issuances_reached_baseline"], 1)          # stored rain water above the curb after issuance
        self.assertEqual(out["frozen_tank_vs_production_pluvial"]["max_abs_diff_ft"], 0.0)
        # the old restart-at-first-lead construction sees no water at all
        first = times.index(iss + dt.timedelta(minutes=30))
        self.assertTrue(all(x is None for x in rr.simulate_pluvial_series(times[first:], prod[first:], rates[first:])))
        self.assertEqual(set(out["landmarks_wet"]), set(rr.LANDMARKS_NAVD88))


class EvaluatorBundleEnforcementTests(unittest.TestCase):
    def _run(self, mirror, logdir, *extra):
        return subprocess.run([sys.executable, os.path.join(mirror, "history/scripts/evaluate_wind_shadow.py"),
                               "--dir", logdir, "--now", "2026-10-01T00:00:00Z", *extra],
                              capture_output=True, text=True, timeout=120)

    def test_changed_evaluator_or_rebound_log_is_not_scored_R6(self):
        tmp = tempfile.mkdtemp(); mirror = _mirror(tmp); logdir = os.path.join(tmp, "log"); os.makedirs(logdir)
        ok = self._run(mirror, logdir)
        self.assertEqual(ok.returncode, 0, ok.stderr)                     # frozen mirror, empty log: runs
        with open(os.path.join(mirror, "history/scripts/evaluate_wind_shadow.py"), "a") as f:
            f.write("# harmless comment\n")
        bad = self._run(mirror, logdir)
        self.assertEqual(bad.returncode, 3); self.assertIn("NOT SCORED", bad.stdout)
        lab = self._run(mirror, logdir, "--unfrozen")
        self.assertEqual(lab.returncode, 0)
        # a first official record bound to a different bundle also blocks scoring
        m2 = _mirror(os.path.join(tmp, "b"))
        Path(logdir, "2026-09.jsonl").write_text(json.dumps(dict(_rec(T0, 0.1, 0.2), candidate_id=ws.CANDIDATE_ID,
                                                                  bundle_sha256="0" * 64)) + "\n")
        rebound = self._run(m2, logdir)
        self.assertEqual(rebound.returncode, 3); self.assertIn("first record binds", rebound.stdout)


if __name__ == "__main__":
    unittest.main()
