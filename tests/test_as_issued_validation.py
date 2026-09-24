"""As-issued validation research code (branch research/as-issued-validation).
Synthetic fixtures establish MECHANICS only, never skill. Protocol:
history/plans/2026-09-24-as-issued-validation-protocol.md (+ Amendments 1, 2).
Adversarial regressions for audit 2026-09-24-a4 R1-R5 and the smaller items."""
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "history" / "scripts"))
from as_issued import advisory as AD, fidelity as F, mean as M, noaa, normalization as N, obs as O, report as RP, street as S  # noqa: E402

UTC = dt.timezone.utc
EL = {"grate_SW": 3.52, "grate_NE": 3.80, "curb": 4.16, "lawn_step": 4.66, "sidewalk_under_walkway_lawn_step": 4.33,
      "intersection_highpoint": 4.54, "porch_step_base": 4.68, "road_middle": 4.36, "corner_NE": 3.91}


def _row(t, key, depth, qual="", weather="clear evening", observer="john", notes=""):
    return {"observation_time_local": t, "landmark_key": key, "observed_depth_in": depth, "observed_qualitative": qual,
            "weather_in_window": weather, "observer": observer, "notes": notes}


class ObservationRuleTests(unittest.TestCase):
    """Protocol 4.1-4.4 as amended before scoring (Amendment 1)."""
    def c(self, *a, **k):
        return O.classify(_row(*a, **k), EL)

    def test_level_types(self):
        T = "2026-08-10T18:23"
        self.assertEqual((self.c(T, "curb", "2")["level_type"], round(self.c(T, "curb", "2")["level_navd88"], 4)),
                         ("POINT", round(4.16 + 2 / 12, 4)))
        self.assertAlmostEqual(self.c(T, "grate_SW", "-9.25")["level_navd88"], 3.52 - 9.25 / 12)
        self.assertEqual(self.c(T, "curb", "0", "level with curb, coming up")["level_type"], "POINT")
        self.assertEqual(self.c(T, "porch_step_base", "0", "water at bottom of first porch step")["level_type"], "POINT")
        self.assertEqual(self.c(T, "porch_step_base", "0.0", "water at/below porch step base; receding")["level_type"], "UPPER")
        self.assertEqual(self.c(T, "grate_NE", "0", "WATER OVER NE+NW GRATES first")["level_type"], "LOWER")
        self.assertEqual(self.c(T, "intersection_highpoint", "0", "CROWN COVERED - entire intersection")["level_type"], "LOWER")
        self.assertEqual(self.c(T, "sidewalk_under_walkway_lawn_step", "", "water over the sidewalk")["level_type"], "LOWER")
        self.assertEqual(self.c(T, "road_middle", "", "well-receded, roads driveable")["level_type"], "UPPER")
        self.assertEqual(self.c(T, "lawn_step", "0", "")["level_type"], "UPPER")          # README: 0 = no water
        blank = self.c(T, "curb", "", "water almost to curb top => ~+7.2-7.5 vs grate")
        self.assertFalse(blank["eligible"])

    def test_exclusions_evidence_and_dry(self):
        T = "2026-08-10T18:23"
        self.assertIn("correction record", self.c(T, "none", "")["reasons"])
        self.assertTrue(any("no current elevation" in r for r in self.c(T, "driveway_central", "1")["reasons"]))
        self.assertTrue(any("before the first published bay line" in r for r in self.c("2026-06-14T20:00", "curb", "1")["reasons"]))
        self.assertEqual(self.c(T, "curb", "1", "PHOTO (EXIF): water")["evidence"], "PHOTO")
        self.assertEqual(self.c(T, "curb", "1", "backcast crest [INFERRED]")["evidence"], "RECONSTRUCTION")
        # a hindcast mentioned only in the NOTES does not make the observation a reconstruction
        self.assertEqual(self.c(T, "curb", "1", "water 1 in", notes="hindcast +12.2 @ 07:14")["evidence"], "OBSERVER_ESTIMATE")
        self.assertEqual(self.c(T, "curb", "1", observer="household-2 via john")["evidence"], "SECOND_OBSERVER")
        self.assertTrue(self.c(T, "curb", "1", weather="clear spring-tide evening")["dry"])
        self.assertTrue(self.c(T, "curb", "1", weather="calm, no rain")["dry"])
        self.assertFalse(self.c(T, "curb", "1", weather="light rain; Flood Watch active")["dry"])
        self.assertFalse(self.c(T, "curb", "1", weather="clear then sudden evening downpour")["dry"])

    def test_times_and_dst(self):
        self.assertEqual(O.local_to_utc("2026-07-13T19:21"), dt.datetime(2026, 7, 13, 23, 21, tzinfo=UTC))
        self.assertEqual(O.local_to_utc("2025-12-19T10:00"), dt.datetime(2025, 12, 19, 15, 0, tzinfo=UTC))
        self.assertEqual(O.local_to_utc("2026-09-13T06:57:02"), dt.datetime(2026, 9, 13, 10, 57, 2, tzinfo=UTC))
        # shared helper (AGENTS rule 3): offset-bearing kept; legacy ambiguous fall-back hour -> fold=0 (EDT)
        self.assertEqual(O.local_to_utc("2026-11-01T01:30-05:00"), dt.datetime(2026, 11, 1, 6, 30, tzinfo=UTC))
        self.assertEqual(O.local_to_utc("2026-11-01T01:30"), dt.datetime(2026, 11, 1, 5, 30, tzinfo=UTC))

    def test_event_segmentation(self):
        b = dt.datetime(2026, 8, 10, 22, tzinfo=UTC)
        ts = [b, b + dt.timedelta(hours=1), b + dt.timedelta(hours=13, minutes=1), b + dt.timedelta(hours=25)]
        self.assertEqual(O.events(ts), [0, 0, 1, 1])


class NormalizationManifestTests(unittest.TestCase):
    """a4 R3: bounds, provenance, supersession and conflicts from the primary evidence."""
    @classmethod
    def setUpClass(cls):
        cls.m = N.build()
        cls.by = {e["row"]: e for e in cls.m["entries"]}

    def test_committed_manifest_matches_the_builder_and_ledger(self):
        with open(N.OUT) as f:
            committed = json.load(f)
        self.assertEqual(committed["entries"], json.loads(json.dumps(self.m["entries"])))
        hashes, _sha, _n = N.row_hashes()
        self.assertTrue(all(hashes[e["row"]] == e["row_sha256"] for e in committed["entries"]))

    def test_photo_bounds_and_brackets_are_not_exact_points(self):
        e = self.by[168]
        self.assertEqual((e["level_type"], e["lo"], e["hi"]), ("INTERVAL", 3.64, 3.90))
        self.assertTrue(e["point_is_midpoint"]); self.assertEqual(e["method"], "photo bound")
        e = self.by[173]
        self.assertEqual(e["level_type"], "INTERVAL"); self.assertEqual(len(e["time_window_utc"]), 2)
        self.assertEqual((self.by[167]["level_type"], self.by[167]["lo"]), ("LOWER", 3.91))

    def test_conflicts_are_documented_not_resolved_by_numeric_precedence(self):
        e = self.by[153]
        self.assertEqual((e["lo"], e["hi"], e["point"]), (4.66, 4.68, 4.67))
        self.assertIn("4.638", e["conflict"])
        self.assertEqual((self.by[164]["level_type"], self.by[164]["hi"]), ("UPPER", 4.33))

    def test_refined_sightings_count_once_and_pending_photos_are_not_photos(self):
        self.assertEqual((self.by[159]["primary"], self.by[159]["superseded_by"]), (False, 166))
        self.assertEqual((self.by[178]["primary"], self.by[178]["superseded_by"]), (False, 181))
        self.assertEqual(self.by[159]["method"], "live report"); self.assertEqual(self.by[178]["method"], "live report")
        self.assertEqual(self.by[166]["time_utc"], "2026-08-07T22:33:16Z")
        self.assertFalse(self.by[165]["primary"])                         # 50-60 % second observer

    def test_tape_rows_carry_the_stated_tolerance(self):
        e = self.by[105]
        self.assertEqual(e["method"], "tape")
        self.assertAlmostEqual(e["hi"] - e["lo"], 1.0 / 12, places=9)

    def test_a_changed_ledger_row_is_detected(self):
        d = tempfile.mkdtemp()
        src = Path(O.LEDGER).read_text()
        Path(d, "l.csv").write_text(src.replace("bounds water 3.64-3.9", "bounds water 3.64-3.95"))
        h2, _s, _n = N.row_hashes(os.path.join(d, "l.csv"))
        h1, _s, _n = N.row_hashes()
        self.assertNotEqual(h1[168], h2[168]); self.assertEqual(h1[167], h2[167])

    def test_event_peaks_distinguish_brackets_from_lower_bounds(self):
        pk = self.m["event_peaks"]
        self.assertIsNone(pk["2026-08-07"]["hi"])                            # observer missed the crest
        self.assertIn("INFERRED", pk["2026-08-07"]["basis"])
        self.assertEqual(RP._vs_peak(4.82, pk["2026-08-07"]), "indeterminate (peak bounded below only)")
        self.assertEqual(RP._vs_peak(4.70, pk["2026-08-07"]), "below the established peak")
        self.assertEqual(RP._vs_peak(5.01, pk["2026-09-01"]), "above the established peak")


class QualityControlTests(unittest.TestCase):
    def test_quality_aware_flags(self):
        c = lambda **k: noaa.classify_water_level(dict({"v": "5.0", "f": "1,0,0,0"}, **k))
        self.assertTrue(c(q="p")[0]); self.assertEqual(c(q="p")[2]["outlier_samples"], 1)
        self.assertFalse(c(q="v")[0]); self.assertIn("inferred", c(q="v")[1])
        self.assertTrue(c(q="v", f="0,0,0,0")[0])
        for q in (None, "x"):
            self.assertIn("unsupported", c(q=q)[1])
        self.assertFalse(c(q="p", f="0,0,1,0")[0]); self.assertFalse(c(q="p", f="1,0,0")[0])
        self.assertFalse(c(q="p", v="nan", f="0,0,0,0")[0])

    def test_raw_bodies_are_hash_verified(self):
        d = tempfile.mkdtemp()
        e, body = noaa.fetch("water_level", dt.datetime(2026, 9, 1, tzinfo=UTC), dt.datetime(2026, 9, 2, tzinfo=UTC), d,
                             get=lambda q: json.dumps({"data": [{"t": "2026-09-01 00:00", "v": "5.0", "f": "0,0,0,0", "q": "p"}]}).encode())
        Path(d, "manifest.json").write_text(json.dumps({"responses": [e]}))
        lv = noaa.water_levels(noaa.load_bodies(os.path.join(d, "manifest.json")))
        self.assertTrue(lv[dt.datetime(2026, 9, 1, tzinfo=UTC)]["valid"])
        Path(d, e["file"]).write_bytes(body + b" ")
        with self.assertRaises(ValueError):
            noaa.load_bodies(os.path.join(d, "manifest.json"))

    def test_committed_astronomy_verifies_and_covers_the_archive(self):
        p30, p6, hilo = F.load_astronomy()
        self.assertIn(dt.datetime(2026, 7, 6, 19, 30, tzinfo=UTC), p30)
        self.assertIn(dt.datetime(2026, 9, 24, 16, 6, tzinfo=UTC), p6)
        self.assertTrue({h[2] for h in hilo} <= {"H", "L", "HH", "LL"})


def _series(start, n, tide):
    out, t = [], start
    for i in range(n):
        loc = t - dt.timedelta(hours=4)
        out.append({"time": loc.strftime("%Y-%m-%d %H:%M") + "-04:00", "tide_navd88": round(tide(t), 3),
                    "water_navd88": round(tide(t), 3)})
        t += dt.timedelta(minutes=30)
    return out


class FakeMeans:
    def as_of(self, t, lag_d=24, verified_end=None):
        return 0.5, 8000, None, None


class FakeCtx:
    def __init__(self, forecasts, replay=None, p30=None):
        self.p30 = p30
        self.p6 = {}
        self.hilo = []
        self.means = FakeMeans()
        self.replay = replay or {}
        self.tank = F._tank()
        self._blobs, self._arms = dict(forecasts), {}
        self.issuances = []
        for blob, f in forecasts.items():
            s = {"blob": blob, "generated_utc": f.get("generated_utc"), "model_version": f.get("model_version"),
                 "commit_time": f.get("generated_utc")}
            s["_t"], s["_basis"] = S.issuance_time(s)
            self.issuances.append(s)

    def forecast(self, s):
        return self._blobs[s["blob"]]

    def tank_fingerprint(self, s):
        return getattr(self, "fp", next(iter(S.SUPPORTED_TANKS)))


def _astro(t):
    return 4.0 + 2.5 * math.sin(2 * math.pi * (t - dt.datetime(2026, 9, 24, tzinfo=UTC)).total_seconds() / 44712.0)


def _p30(a, b):
    out, t = {}, a
    while t <= b:
        out[t] = round(_astro(t), 3)
        t += dt.timedelta(minutes=30)
    return out


GEN = dt.datetime(2026, 9, 24, 10, 14, tzinfo=UTC)
START = dt.datetime(2026, 9, 24, 4, 30, tzinfo=UTC)


def _entry(t_local, key="curb", level_type="POINT", point=None, lo=None, hi=None, dry=True, primary=True, window=None, row=2):
    e = {"row": row, "time_utc": O.local_to_utc(t_local).strftime("%Y-%m-%dT%H:%M:%SZ"), "landmark": key,
         "elevation": EL[key], "level_type": level_type, "point": point, "lo": lo, "hi": hi,
         "method": "tape", "primary": primary, "dry": dry}
    if window:
        e["time_window_utc"] = [O.local_to_utc(x).strftime("%Y-%m-%dT%H:%M:%SZ") for x in window]
    return e


def _v106(reading=1.5, mean=0.5, rain=None, with_replay=True, pluvial=None):
    p30 = _p30(START - dt.timedelta(hours=2), START + dt.timedelta(hours=40))
    obs_t = GEN - dt.timedelta(minutes=8)
    dec = {"rung": "fresh", "surge_obs_ft": reading, "observation_utc": obs_t.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "mean_ft": mean, "tau_h": 36.0}
    tide = lambda t: p30[t] - 2.82 + S.decay(reading, obs_t, mean, t)
    f = {"generated_utc": GEN.strftime("%Y-%m-%dT%H:%M:%SZ"), "model_version": "v0.10.6",
         "water_series": _series(START, 73, tide), "water_series_input": {"decay": dec}}
    if pluvial == "consistent" and rain:
        tank = F._tank()
        times = [START + dt.timedelta(minutes=30 * i) for i in range(73)]
        hr0 = START.replace(minute=0)
        rates = [rain[int((t.replace(minute=0) - hr0).total_seconds() // 3600)] for t in times]
        pl = tank.simulate_pluvial_series(times, [q["tide_navd88"] for q in f["water_series"]], rates)
        for q, v in zip(f["water_series"], pl):
            if v is not None:
                q["pluvial_navd88"] = round(v, 3)
                q["water_navd88"] = max(q["tide_navd88"], q["pluvial_navd88"])      # a4 round 03: combined line too
    replay = {}
    if with_replay:
        from forecast import replay_archive as ra
        hrs = [START.replace(minute=0) + dt.timedelta(hours=k) for k in range(40)]
        rates = rain or [0.0] * len(hrs)
        replay = {f["generated_utc"]: {"qpf_hourly": ra.columnar(hrs, in_hr=rates), "unavailable": {}}}
    return f, replay, p30


class StreetArmTests(unittest.TestCase):
    def test_decay_arm_reproduces_the_published_v0106_bay_and_persisted_arm_is_constant(self):
        f, replay, p30 = _v106()
        ctx = FakeCtx({"b1": f}, replay, p30)
        res = S.arms(ctx, ctx.issuances[0])
        self.assertEqual(res["reasons"], [])
        self.assertLessEqual(res["facts"]["decay_vs_published_bay_max_ft"], 0.0006)
        k = [b - (p30[t] - 2.82) for t, b in zip(res["times"], res["bay_K"])]
        self.assertAlmostEqual(max(k), 1.5, places=9); self.assertAlmostEqual(min(k), 1.5, places=9)

    def test_pair_classes(self):
        o = _entry("2026-09-24T08:00", "curb", "POINT", point=4.24)
        f, replay, p30 = _v106()
        ctx = FakeCtx({"b1": f}, replay, p30)
        pairs = S.build_pairs(ctx, [o])
        self.assertEqual({p["class"] for p in pairs}, {"EXACT"})
        self.assertEqual(pairs[0]["lead_bin"], "(0,6]")
        f2, _r, p30 = _v106(with_replay=False)
        self.assertEqual(S.build_pairs(FakeCtx({"b1": f2}, {}, p30), [o])[0]["class"], "APPROX-TIDE")
        self.assertEqual(S.build_pairs(FakeCtx({"b1": f2}, {}, p30), [dict(o, dry=False)])[0]["class"], "EXCLUDED")
        f3 = dict(f2, tide_predictions_stale=True)
        self.assertIn("astronomy", S.build_pairs(FakeCtx({"b1": f3}, {}, p30), [o])[0]["class_note"])

    def test_exact_requires_a_matching_control_tank_replay_R1(self):
        """a4 R1 probe: archived rain contradicting a published DRY tank must not be EXACT."""
        rain = [1.0] * 40
        o = _entry("2026-09-24T08:00", "curb", "POINT", point=4.24)
        f, replay, p30 = _v106(rain=rain)                                   # published line has no pluvial
        pairs = S.build_pairs(FakeCtx({"b1": f}, replay, p30), [o])
        self.assertEqual(pairs[0]["class"], "EXCLUDED"); self.assertIn("control tank replay mismatch", pairs[0]["class_note"])
        f, replay, p30 = _v106(rain=rain, pluvial="consistent")             # the consistent record is admitted
        self.assertEqual(S.build_pairs(FakeCtx({"b1": f}, replay, p30), [o])[0]["class"], "EXACT")

    def test_exact_requires_bay_control_supported_tank_and_finite_grid_R1(self):
        o = _entry("2026-09-24T08:00", "curb", "POINT", point=4.24)
        f, replay, p30 = _v106()
        for q in f["water_series"][10:12]:
            q["tide_navd88"] += 0.01                                           # published bay not reproducible
        pr = S.build_pairs(FakeCtx({"b1": f}, replay, p30), [o])[0]
        self.assertEqual(pr["class"], "EXCLUDED")                              # fails the astronomy/bay control replay
        self.assertRegex(pr["class_note"], "astronomy not reproduced|control bay replay mismatch")
        f, replay, p30 = _v106()
        ctx = FakeCtx({"b1": f}, replay, p30); ctx.fp = "0" * 64
        self.assertIn("unsupported tank", S.build_pairs(ctx, [o])[0]["class_note"])
        f, replay, p30 = _v106()
        del f["water_series"][20:26]                                          # a 3-hour hole in the grid
        pr = S.build_pairs(FakeCtx({"b1": f}, replay, p30), [o])
        self.assertTrue(all(p["class"] == "EXCLUDED" for p in pr))

    def test_antecedent_rain_gaps_are_not_exact_R1(self):
        from forecast import replay_archive as ra
        o = _entry("2026-09-24T08:00", "curb", "POINT", point=4.24)
        f, replay, p30 = _v106()
        rec = replay[f["generated_utc"]]
        hrs = [START.replace(minute=0) + dt.timedelta(hours=k) for k in range(40) if k != 3]
        rec["qpf_hourly"] = ra.columnar(hrs, in_hr=[0.0] * len(hrs))
        self.assertIn("antecedent", S.build_pairs(FakeCtx({"b1": f}, replay, p30), [o])[0]["class_note"])
        hrs = [START.replace(minute=0) + dt.timedelta(hours=k) for k in range(1, 40)]
        rec["qpf_hourly"] = ra.columnar(hrs, in_hr=[0.0] * len(hrs))
        self.assertEqual(S.build_pairs(FakeCtx({"b1": f}, replay, p30), [o])[0]["class"], "NEAR")

    def test_combined_line_must_match_its_control_R1_round03(self):
        """Round 03 probe: +5 ft on the published combined line only was admitted as EXACT."""
        o = _entry("2026-09-24T08:00", "curb", "POINT", point=4.24)
        f, replay, p30 = _v106()
        for q in f["water_series"]:
            q["water_navd88"] += 5.0
        pr = S.build_pairs(FakeCtx({"b1": f}, replay, p30), [o])[0]
        self.assertEqual(pr["class"], "EXCLUDED"); self.assertIn("combined output mismatch", pr["class_note"])
        f, replay, p30 = _v106(rain=[1.0] * 40, pluvial="consistent")        # the repaired positive fixture
        self.assertEqual(S.build_pairs(FakeCtx({"b1": f}, replay, p30), [o])[0]["class"], "EXACT")

    def test_constant_rule_uses_the_same_bay_tolerance_R1_round03(self):
        """Round 03 probe: a v0.10.5 constant-reading curve shifted 0.002 ft was admitted as NEAR."""
        from forecast import replay_archive as ra
        p30 = _p30(START - dt.timedelta(hours=2), START + dt.timedelta(hours=40))
        obs_t = GEN - dt.timedelta(minutes=8)
        for shift, expect in ((0.0, "NEAR"), (0.002, "EXCLUDED")):
            tide = lambda t: p30[t] - 2.82 + 1.5 + shift
            f = {"generated_utc": GEN.strftime("%Y-%m-%dT%H:%M:%SZ"), "model_version": "v0.10.5",
                 "water_series": _series(START, 73, tide),
                 "water_series_input": {"surge_ft": 1.5, "observation_time": (obs_t - dt.timedelta(hours=4)).strftime("%Y-%m-%d %H:%M") + "-04:00"}}
            hrs = [START.replace(minute=0) + dt.timedelta(hours=k) for k in range(40)]
            replay = {f["generated_utc"]: {"qpf_hourly": ra.columnar(hrs, in_hr=[0.0] * 40), "unavailable": {}}}
            pr = S.build_pairs(FakeCtx({"b1": f}, replay, p30), [_entry("2026-09-24T08:00", "curb", "POINT", point=4.24)])[0]
            self.assertEqual(pr["class"], expect, pr["class_note"])
            if expect == "EXCLUDED":
                self.assertRegex(pr["class_note"], "control bay replay mismatch|astronomy not reproduced")

    def test_invalid_numbers_are_reasoned_exclusions_not_crashes_R1_round03(self):
        from forecast import replay_archive as ra
        o = _entry("2026-09-24T08:00", "curb", "POINT", point=4.24)
        hrs = [START.replace(minute=0) + dt.timedelta(hours=k) for k in range(40)]
        for rates, why in (([-1.0] * 40, "invalid archived rain"), ([float("nan")] * 40, "invalid archived rain"),
                           ([None] * 40, "antecedent")):
            f, replay, p30 = _v106()
            replay[f["generated_utc"]]["qpf_hourly"] = ra.columnar(hrs, in_hr=rates)
            pr = S.build_pairs(FakeCtx({"b1": f}, replay, p30), [o])[0]      # must not raise
            self.assertEqual(pr["class"], "EXCLUDED", rates[0]); self.assertIn(why, pr["class_note"])
        for field in ("pluvial_navd88", "water_navd88", "tide_navd88"):
            f, replay, p30 = _v106()
            f["water_series"][10][field] = float("nan")
            pr = S.build_pairs(FakeCtx({"b1": f}, replay, p30), [o])
            self.assertTrue(pr and all(p["class"] == "EXCLUDED" for p in pr), field)
        f, replay, p30 = _v106()
        f["water_series_input"]["decay"]["mean_ft"] = float("nan")
        self.assertEqual(S.build_pairs(FakeCtx({"b1": f}, replay, p30), [o])[0]["class"], "EXCLUDED")

    def test_invalid_inputs_cannot_reach_a_verdict_R1_round03(self):
        from forecast import replay_archive as ra
        f, replay, p30 = _v106()
        hrs = [START.replace(minute=0) + dt.timedelta(hours=k) for k in range(40)]
        replay[f["generated_utc"]]["qpf_hourly"] = ra.columnar(hrs, in_hr=[-1.0] * 40)
        obs = [dict(_entry("2026-09-24T08:00", "curb", "POINT", point=4.24), row=i) for i in range(2, 9)]
        rep, pairs = S.evaluate(FakeCtx({"b1": f}, replay, p30), obs)
        self.assertEqual(set(rep["class_counts"]), {"EXCLUDED"})
        self.assertEqual(rep["verdicts"]["B1 decay vs persisted (EXACT only)"], "NOT YET EVALUABLE")

    def test_inconsistent_records_cannot_produce_a_verdict_R1(self):
        rain = [1.0] * 40
        f, replay, p30 = _v106(rain=rain)
        ctx = FakeCtx({"b1": f}, replay, p30)
        obs = [dict(_entry("2026-09-24T08:00", "curb", "POINT", point=4.24), row=i) for i in range(2, 9)]
        rep, _pairs = S.evaluate(ctx, obs)
        self.assertEqual(rep["class_counts"], {"EXCLUDED": len(_pairs)})
        self.assertEqual(rep["verdicts"]["B1 decay vs persisted (EXACT only)"], "NOT YET EVALUABLE")

    def test_tank_uses_antecedent_rain_from_the_series_start(self):
        # rain only BEFORE issuance: the arms still carry the stored water afterwards
        hrs = 40
        rain = [1.0] * 5 + [0.0] * (hrs - 5)            # 04:00-08:59Z
        f, replay, p30 = _v106(reading=-1.0, mean=0.5, rain=rain, pluvial="consistent")
        ctx = FakeCtx({"b1": f}, replay, p30)
        res = S.arms(ctx, ctx.issuances[0])
        i = res["times"].index(dt.datetime(2026, 9, 24, 9, 30, tzinfo=UTC))
        self.assertGreater(res["D"][i], res["T"][i])     # tank water above the bay after the rain
        self.assertIsNotNone(res["L"]); self.assertGreaterEqual(res["L"][i], res["T"][i])   # fixed-low-bay tank arm

    def test_scores_and_threshold_cells_R3_R4(self):
        p = {"elevation": 4.16, "level_type": "POINT", "point": 4.26, "lo": 4.2183, "hi": 4.3017, "D": 4.36}
        sc = S.score(p, "D")
        self.assertAlmostEqual(sc["error"], 0.10); self.assertTrue(sc["observed_wet"]); self.assertTrue(sc["forecast_wet"])
        self.assertAlmostEqual(sc["interval_error"], 4.36 - 4.3017)
        self.assertAlmostEqual(sc["depth_error_in"], 1.2)
        # declared rule (protocol 4.6): a point AT the landmark is dry, never dropped (a4 R4)
        at = S.score(dict(p, point=4.16, lo=None, hi=None), "D")
        self.assertIs(at["observed_wet"], False); self.assertEqual(S.cell(at), "false alarm")
        # a photo bracket straddling the landmark is UNKNOWN and still counted
        iv = S.score({"elevation": 3.80, "level_type": "INTERVAL", "point": 3.77, "lo": 3.64, "hi": 3.90, "D": 3.82}, "D")
        self.assertIsNone(iv["observed_wet"]); self.assertEqual(iv["interval_error"], 0.0)       # inside: no point penalty
        self.assertTrue(S.cell(iv).startswith("unknown"))
        self.assertAlmostEqual(iv["midpoint_error"], 0.05)
        self.assertEqual(S.score({"elevation": 4.16, "level_type": "UPPER", "hi": 4.16, "D": 4.36}, "D")["exceedance"], 4.36 - 4.16)
        self.assertEqual(S.score({"elevation": 4.16, "level_type": "LOWER", "lo": 4.16, "D": 4.0}, "D")["deficit"], 4.16 - 4.0)

    def test_time_windows_use_the_forecast_range(self):
        a = dt.datetime(2026, 9, 24, 10, tzinfo=UTC)
        ts = [a + dt.timedelta(minutes=30 * i) for i in range(4)]
        self.assertEqual(S.window_range(ts, [1.0, 2.0, 3.0, 2.5], a + dt.timedelta(minutes=15), a + dt.timedelta(minutes=75)), (1.5, 3.0))
        p = {"elevation": 3.0, "level_type": "INTERVAL", "point": 3.35, "lo": 3.3, "hi": 3.4, "D": 2.0, "D_range": (1.5, 3.3)}
        self.assertEqual(S.score(p, "D")["interval_error"], 0.0)                 # reached inside the window

    def test_interpolation_between_half_hours(self):
        a = dt.datetime(2026, 9, 24, 10, tzinfo=UTC)
        ts = [a, a + dt.timedelta(minutes=30)]
        self.assertAlmostEqual(S.interp(ts, [1.0, 2.0], a + dt.timedelta(minutes=12)), 1.4)
        self.assertIsNone(S.interp(ts, [1.0, 2.0], a + dt.timedelta(hours=1)))
        self.assertIsNone(S.interp(ts, [1.0, None], a + dt.timedelta(minutes=12)))
        gap = [a, a + dt.timedelta(hours=3)]
        self.assertIsNone(S.interp(gap, [1.0, 2.0], a + dt.timedelta(hours=1)))   # no interpolation across a hole

    def test_verdict_rules(self):
        base = {"event_mean_mae_diff_ft": -0.1, "events_won_by_first": 5, "events_won_by_second": 0, "ci90": [-0.2, -0.05]}
        self.assertEqual(S.verdict(dict(base, events=5)), "FIRST BETTER")
        self.assertEqual(S.verdict(dict(base, events=4)), "DESCRIPTIVE (3-4 events)")
        self.assertEqual(S.verdict(dict(base, events=2)), "NOT YET EVALUABLE")
        self.assertEqual(S.verdict(dict(base, events=5, ci90=[-0.2, 0.05])), "INCONCLUSIVE")
        self.assertEqual(S.verdict(dict(base, events=5, events_won_by_first=2)), "INCONCLUSIVE")


def _mutate(case):
    """(forecast, replay, p30) for a named full-path case (audit a4 rounds 03/05 probes + controls)."""
    from forecast import replay_archive as ra
    rain = None
    if case == "exact_wet":
        rain = [1.0] * 5 + [0.0] * 35
    if case == "near_wet":                # the unarchived first core hour was dry in the published run
        rain = [0.0] + [1.0] * 4 + [0.0] * 35
    f, r, a = _v106(rain=rain, pluvial="consistent" if rain else None)
    ws, dec = f["water_series"], f["water_series_input"]["decay"]
    hrs = [START.replace(minute=0) + dt.timedelta(hours=k) for k in range(40)]
    if case == "bay_string": ws[10]["tide_navd88"] = "bad"
    if case == "mean_string": dec["mean_ft"] = "bad"
    if case == "tau_string": dec["tau_h"] = "bad"
    if case == "tau_null": dec["tau_h"] = None
    if case == "tau_missing": del dec["tau_h"]
    if case == "tau_zero": dec["tau_h"] = 0
    if case == "tau_negative": dec["tau_h"] = -1.0
    if case == "mean_only":                       # declared exception: no reading, no timescale needed
        mean = dec["mean_ft"]
        dec.clear(); dec.update(rung="typical-offset", mean_ft=mean, surge_obs_ft=None, observation_utc=None)
        for q in ws:
            t = F.parse_station_local_time(q["time"]).astimezone(UTC)
            q["tide_navd88"] = q["water_navd88"] = round(a[t] - 2.82 + mean, 3)
    if case == "reading_bad_time": dec["observation_utc"] = "bad"
    if case == "reading_string": dec["surge_obs_ft"] = "bad"
    if case == "combined_nan":
        for q in ws: q["water_navd88"] = float("nan")
    if case == "combined_string":
        for q in ws: q["water_navd88"] = "bad"
    if case == "combined_plus5":
        for q in ws: q["water_navd88"] += 5.0
    if case == "pluvial_nan": ws[12]["pluvial_navd88"] = float("nan")
    if case == "pluvial_string": ws[12]["pluvial_navd88"] = "bad"
    if case == "time_bad": ws[15]["time"] = "not a time"
    if case in ("rain_negative", "rain_nan", "rain_null"):
        v = {"rain_negative": -1.0, "rain_nan": float("nan"), "rain_null": None}[case]
        r[f["generated_utc"]]["qpf_hourly"] = ra.columnar(hrs, in_hr=[v] * 40)
    if case == "near_wet":
        rec = r[f["generated_utc"]]
        rates = [x["in_hr"] for _t, x in ra.expand(rec["qpf_hourly"])]
        rec["qpf_hourly"] = ra.columnar(hrs[1:], in_hr=rates[1:])
    if case == "published_only":          # rain not archived, wet window: counterfactual EXCLUDED, B0 still scored
        r = {}
    return f, r, a


MALFORMED = ("bay_string", "mean_string", "tau_string", "tau_null", "tau_missing", "tau_zero", "tau_negative",
             "reading_bad_time", "reading_string", "combined_nan",
             "combined_string", "combined_plus5", "pluvial_nan", "pluvial_string", "rain_negative", "rain_nan", "rain_null")


def _full_chain(case, dry=True):
    f, r, a = _mutate(case)
    obs = [_entry("2026-09-24T08:00", "curb", "POINT", point=4.24, dry=dry)]
    rep, pairs = S.evaluate(FakeCtx({"b1": f}, r, a), obs)
    events = RP.per_event(pairs, {})
    text = json.dumps({"report": rep, "events": events, "pairs": pairs}, allow_nan=False, default=str)
    return rep, pairs, events, text


class FullPathTests(unittest.TestCase):
    """a4 round 05: evaluate -> per_event -> strict JSON for every boundary case and positive control."""

    def test_malformed_inputs_never_raise_score_or_reach_a_verdict(self):
        for case in MALFORMED:
            with self.subTest(case=case):
                rep, pairs, events, text = _full_chain(case)             # no exception, strict JSON
                self.assertEqual(set(rep["class_counts"]), {"EXCLUDED"}, case)
                self.assertTrue(all(p["class_note"] for p in pairs))       # a specific reason
                self.assertEqual(rep["verdicts"]["B1 decay vs persisted (EXACT only)"], "NOT YET EVALUABLE")
                for p in pairs:
                    for arm in ("K", "D", "T", "L"):
                        self.assertTrue(p[arm] is None or math.isfinite(p[arm]))

    def test_invalid_published_line_is_unscorable_not_a_cell(self):
        for case in ("combined_nan", "combined_string"):
            rep, pairs, events, _t = _full_chain(case)
            b0 = rep["B0_published_by_version"]["v0.10.6"]["(0,6]"]
            self.assertEqual(b0["point_pairs"], 0); self.assertEqual(b0["threshold"], {})
            self.assertEqual(b0["unscorable"], {"published line invalid or missing at the observation time": 1})
            self.assertEqual(events[0]["leads"]["(0,6]"]["threshold"], {})
            self.assertIn("invalid combined", pairs[0]["class_note"])

    def test_valid_published_line_survives_counterfactual_exclusion(self):
        for case in ("bay_string", "mean_string", "tau_string", "reading_bad_time", "rain_negative", "rain_null"):
            rep, _p, _e, _t = _full_chain(case)
            b0 = rep["B0_published_by_version"]["v0.10.6"]["(0,6]"]
            self.assertEqual(b0["point_pairs"], 1, case); self.assertTrue(math.isfinite(b0["mae_ft"]))

    def test_positive_controls(self):
        rep, pairs, _e, _t = _full_chain("baseline")
        self.assertEqual(rep["class_counts"], {"EXACT": 1})
        rep, pairs, _e, _t = _full_chain("exact_wet")
        self.assertEqual(rep["class_counts"], {"EXACT": 1}); self.assertIsNotNone(pairs[0]["D"])
        rep, pairs, _e, _t = _full_chain("near_wet")
        self.assertEqual(rep["class_counts"], {"NEAR": 1}, pairs[0]["class_note"])
        rep, pairs, _e, _t = _full_chain("published_only", dry=False)
        self.assertEqual(rep["class_counts"], {"EXCLUDED": 1})
        b0 = rep["B0_published_by_version"]["v0.10.6"]["(0,6]"]
        self.assertEqual(b0["point_pairs"], 1); self.assertTrue(math.isfinite(b0["mae_ft"]))
        rep, pairs, _e, _t = _full_chain("published_only", dry=True)
        self.assertEqual(rep["class_counts"], {"APPROX-TIDE": 1})

    def test_missing_or_null_timescale_round07(self):
        """a4 round 07: absent/null tau crashed F1 and the full evaluator; now a reasoned
        exclusion that keeps the valid published line in B0 and is never filled in with 36 h."""
        p30 = _v106()[2]
        for case in ("tau_null", "tau_missing"):
            f, r, a = _mutate(case)
            self.assertIn("decay tau_h missing or null for a decaying reading", F.rule_problems(f))
            self.assertEqual(F.f1_astronomy(f, a)["status"], "invalid published input")
            self.assertEqual(F.f4_reading(f, a)["status"], "invalid published input")
            rep, pairs, _e, _t = _full_chain(case)
            self.assertEqual(rep["class_counts"], {"EXCLUDED": 1})
            self.assertIn("tau_h missing or null", pairs[0]["class_note"])
            b0 = rep["B0_published_by_version"]["v0.10.6"]["(0,6]"]
            self.assertEqual(b0["point_pairs"], 1); self.assertTrue(math.isfinite(b0["mae_ft"]))

    def test_mean_only_rung_needs_no_timescale_round07(self):
        f, r, a = _mutate("mean_only")
        self.assertNotIn("tau_h", f["water_series_input"]["decay"])
        self.assertEqual(F.rule_problems(f), [])
        self.assertLessEqual(F.f1_astronomy(f, a)["max_abs_vs_rule"], 0.0006)   # replays the mean-only line
        rep, pairs, _e, _t = _full_chain("mean_only")                              # no reading: excluded, not a crash
        self.assertEqual(rep["class_counts"], {"EXCLUDED": 1}); self.assertIn("reading unavailable", pairs[0]["class_note"])
        self.assertEqual(rep["B0_published_by_version"]["v0.10.6"]["(0,6]"]["point_pairs"], 1)
        f["water_series_input"]["decay"]["tau_h"] = "bad"                          # a PRESENT tau must still be valid
        self.assertIn("decay tau_h not a positive finite number", F.rule_problems(f))

    def test_fidelity_entry_points_do_not_raise(self):
        p30 = _v106()[2]
        tank = F._tank()
        for case in MALFORMED + ("time_bad",):
            f, r, _a = _mutate(case)
            rp = r.get(f["generated_utc"])
            out = [F.f1_astronomy(f, p30), F.f2_tank(f, "HEAD", rp, tank), F.f3_parity(f, rp), F.f4_reading(f, p30)]
            json.dumps(out, allow_nan=False, default=str)
            if case in ("bay_string", "mean_string", "tau_string", "reading_bad_time", "reading_string"):
                self.assertEqual(out[0]["status"], "invalid published input", case)
            if case.startswith("rain_") and case != "rain_null":
                self.assertEqual(out[1]["status"], "not replayable", case)

    def test_advisory_full_chain_is_strict_json(self):
        for mutate in ("outlook_nan", "anchor_nan", "raw_nan", "outcome_nan", "none"):
            rows, fc, levels, hilo = _advisory_fixture(0.3, 6, "corrected")
            g = rows[0][0]["generated_utc"]
            if mutate == "outlook_nan":
                fc[g]["outlook_7d"]["series"][3]["tide_navd88"] = float("nan")
            if mutate == "anchor_nan":
                rows[0][0]["advisory_corrections"][0]["ft"] = float("nan")
            if mutate == "raw_nan":
                rows[0][0]["nwps"]["hourly"]["ft"][2] = float("nan")
            pairs, skipped = AD.build_pairs(rows, fc.get, hilo)
            if mutate == "outcome_nan":
                levels = {k: dict(v, v=float("nan")) if i % 3 == 0 else v for i, (k, v) in enumerate(levels.items())}
            AD.attach_outcomes(pairs, levels, dt.datetime(2026, 12, 1, tzinfo=UTC))
            rep = AD.evaluate(pairs, {"test_mark": 1.35})
            json.dumps({"report": rep, "skipped": skipped, "pairs": pairs}, allow_nan=False, default=str)
            if mutate != "none":
                self.assertTrue(skipped or rep["unscored"], mutate)
        self.assertEqual(rep["phases"]["HIGH"]["verdict"], "IMPROVES")   # positive control still evaluates


def _advisory_fixture(anchor_ft, n_episodes, obs_follows, corrupt_anchors=False, gap_h=72):
    """Synthetic replay records built END TO END: raw NWPS hourly, advisory rows
    whose totals exceed raw NWPS by anchor_ft at each advisory high tide, the
    recorded anchors, and an outlook line = raw + the spec's hourly correction
    (labeled nws_product where anchored). obs_follows: 'corrected' or 'raw'."""
    from forecast import replay_archive as ra
    hilo = []
    t = dt.datetime(2026, 9, 1, 3, tzinfo=UTC)
    while t < dt.datetime(2026, 11, 20, tzinfo=UTC):
        hilo.append((t, 6.0, "H")); hilo.append((t + dt.timedelta(hours=6, minutes=12), 1.0, "L"))
        t += dt.timedelta(hours=12, minutes=25)
    rows, forecasts, levels = [], {}, {}
    for e in range(n_episodes):
        gen = dt.datetime(2026, 9, 2, tzinfo=UTC) + dt.timedelta(hours=gap_h * e)
        hrs = [gen.replace(minute=0) + dt.timedelta(hours=k) for k in range(1, 49)]
        raw = {h: round(4.0 + 0.1 * (k % 5), 2) for k, h in enumerate(hrs)}
        highs = [h for h, _v, ty in hilo if ty == "H" and hrs[3] <= h <= hrs[-6]]
        adv_rows, anchors = [], []
        for h in highs:
            key = h.replace(minute=0)
            base = max(raw[k] for k in (key, key + dt.timedelta(hours=1)) if k in raw)
            adv_rows.append([(h - dt.timedelta(hours=4)).strftime("%Y-%m-%d %H:%M") + "-04:00", round(base + anchor_ft, 2), 1.5])
            anchors.append((h, anchor_ft))
        ser = []
        for h in hrs:
            c, anchored = AD.correction_at(anchors, h)
            ser.append({"utc": h.strftime("%Y-%m-%dT%H:%M:%SZ"), "tide_navd88": round(raw[h] + c - 2.82, 3),
                        "surge_source": "nws_product" if anchored else "nwps"})
            levels[h] = {"v": raw[h] + c if obs_follows == "corrected" else raw[h], "valid": True, "reason": None, "q": "v"}
        ser.append({"utc": (hrs[-1] + dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"), "tide_navd88": 1.0,
                    "surge_source": "petss_hourly"})
        g = gen.strftime("%Y-%m-%dT%H:%M:%SZ")
        rec_anchors = [{"utc": a.strftime("%Y-%m-%dT%H:%M:%SZ"), "ft": 0.0 if corrupt_anchors else round(c, 2)} for a, c in anchors]
        rows.append(({"generated_utc": g, "nwps": {"issued": g, "hourly": ra.columnar(hrs, ft=[raw[h] for h in hrs])},
                      "advisory": {"rows": adv_rows}, "advisory_corrections": rec_anchors},
                     {"file": "synthetic", "line": e + 1, "sha256": "0" * 64}))
        forecasts[g] = {"outlook_7d": {"series": ser}}
    return rows, forecasts, levels, hilo


class AdvisoryTests(unittest.TestCase):
    def _run(self, anchor_ft, n, follows, **kw):
        rows, fc, levels, hilo = _advisory_fixture(anchor_ft, n, follows, **kw)
        pairs, skipped = AD.build_pairs(rows, fc.get, hilo)
        AD.attach_outcomes(pairs, levels, dt.datetime(2026, 12, 1, tzinfo=UTC))
        return AD.evaluate(pairs, {"test_mark": 1.35}), pairs, skipped   # NAVD88; raw levels 1.18-1.58

    def test_zero_correction_parity_is_a_control(self):
        rep, pairs, skipped = self._run(0.0, 6, "raw")
        self.assertEqual(rep["cohorts"], {"ZERO": len(pairs)})
        self.assertEqual(rep["nonzero_episodes_total"], 0)
        for ph in ("HIGH", "MID", "LOW"):
            z = rep["phases"][ph]["ZERO"]["all leads"]
            if z["n"]:
                self.assertEqual(z["mae_corrected"], z["mae_uncorrected"])
            self.assertTrue(rep["phases"][ph]["verdict"].startswith("NOT YET EVALUABLE"))
        self.assertTrue(any("petss_hourly" in k for k in skipped))       # source boundary

    def test_nonzero_anchors_end_to_end_R2(self):
        rep, pairs, _s = self._run(0.3, 6, "corrected")
        self.assertTrue(any(p["cohort"] == "NONZERO" for p in pairs))
        for ph in ("HIGH", "MID", "LOW"):
            self.assertEqual(rep["phases"][ph]["verdict"], "IMPROVES", ph)
        rep, _p, _s = self._run(0.3, 6, "raw")
        for ph in ("HIGH", "MID", "LOW"):
            self.assertEqual(rep["phases"][ph]["verdict"], "HARMS", ph)
        self.assertGreater(rep["phases"]["HIGH"]["NONZERO"]["landmark_flips"]["test_mark"]["flips"], 0)

    def test_corrupted_recorded_anchors_are_rejected_R2(self):
        """a4 R2 probe: a +0.3 ft line correction with every recorded anchor zeroed."""
        rep, pairs, skipped = self._run(0.3, 6, "corrected", corrupt_anchors=True)
        self.assertEqual(rep["cohorts"].get("NONZERO", 0), 0)
        self.assertTrue(any("anchors disagree" in k for k in skipped))
        for ph in ("HIGH", "MID", "LOW"):
            self.assertTrue(rep["phases"][ph]["verdict"].startswith("NOT YET EVALUABLE"))

    def test_line_that_disagrees_with_its_anchors_is_rejected_R2(self):
        rows, fc, levels, hilo = _advisory_fixture(0.3, 1, "corrected")
        g = rows[0][0]["generated_utc"]
        for q in fc[g]["outlook_7d"]["series"]:
            if q["surge_source"] == "nws_product":
                q["tide_navd88"] += 0.05
        pairs, skipped = AD.build_pairs(rows, fc.get, hilo)
        self.assertTrue(any("reconstructed correction" in k for k in skipped))
        self.assertFalse(any(p["source"] == "nws_product" for p in pairs))

    def test_invalid_advisory_numbers_are_excluded_R1_round03(self):
        """Round 03 probe: NaN published outlook levels admitted 48 pairs."""
        rows, fc, levels, hilo = _advisory_fixture(0.3, 1, "corrected")
        g = rows[0][0]["generated_utc"]
        for q in fc[g]["outlook_7d"]["series"]:
            q["tide_navd88"] = float("nan")
        pairs, skipped = AD.build_pairs(rows, fc.get, hilo)
        self.assertEqual(pairs, []); self.assertGreater(skipped["invalid or missing published outlook level"], 0)
        rows, fc, levels, hilo = _advisory_fixture(0.3, 1, "corrected")
        rows[0][0]["advisory_corrections"][0]["ft"] = float("nan")
        pairs, skipped = AD.build_pairs(rows, fc.get, hilo)
        self.assertEqual(pairs, []); self.assertEqual(skipped["record with a missing or invalid recorded anchor"], 1)
        from forecast import replay_archive as ra
        rows, fc, levels, hilo = _advisory_fixture(0.3, 1, "corrected")
        nw = rows[0][0]["nwps"]["hourly"]; nw["ft"][5] = float("nan")
        pairs, skipped = AD.build_pairs(rows, fc.get, hilo)
        self.assertEqual(pairs, []); self.assertEqual(skipped["record with invalid raw NWPS values"], 1)
        rows, fc, levels, hilo = _advisory_fixture(0.3, 1, "corrected")
        pairs, _s = AD.build_pairs(rows, fc.get, hilo)
        levels = {k: dict(v, v=float("nan")) for k, v in levels.items()}
        AD.attach_outcomes(pairs, levels, dt.datetime(2026, 12, 1, tzinfo=UTC))
        self.assertEqual(AD.evaluate(pairs, {})["matured_valid"], 0)

    def test_missing_astronomy_is_unavailable_not_mid_R2(self):
        t = dt.datetime(2026, 9, 24, 13, tzinfo=UTC)
        self.assertEqual(AD.phase_of(t, []), "UNAVAILABLE")
        self.assertEqual(AD.phase_of(t, [(t - dt.timedelta(hours=3), 6.0, "H")]), "UNAVAILABLE")
        rows, fc, levels, _h = _advisory_fixture(0.3, 1, "corrected")
        pairs, skipped = AD.build_pairs(rows, fc.get, [])
        self.assertEqual(pairs, []); self.assertTrue(any("phase unavailable" in k for k in skipped))

    def test_correction_matches_production_interpolation(self):
        import random
        from forecast import outlook
        rnd = random.Random(3)
        base = dt.datetime(2026, 9, 24, tzinfo=UTC)
        for _ in range(50):
            anchors = sorted((base + dt.timedelta(hours=rnd.uniform(0, 72)), rnd.uniform(-0.5, 0.5)) for _k in range(rnd.randint(1, 5)))
            for h in range(-10, 90):
                t = base + dt.timedelta(hours=h)
                a, b = AD.correction_at(anchors, t), outlook._anchor_correction(anchors, t)
                self.assertAlmostEqual(a[0], b[0], places=12); self.assertEqual(a[1], b[1])

    def test_too_few_episodes_is_not_yet_evaluable(self):
        rep, _p, _s = self._run(0.3, 4, "corrected")
        for ph in ("HIGH", "MID", "LOW"):
            self.assertIn("NOT YET EVALUABLE", rep["phases"][ph]["verdict"])

    def test_episode_gap_boundary_is_strict(self):
        a = dt.datetime(2026, 9, 24, tzinfo=UTC)
        ep = AD.episodes([a, a + dt.timedelta(hours=11, minutes=59), a + dt.timedelta(hours=23, minutes=59)])
        self.assertEqual(sorted(set(ep.values())), [0, 1])                   # exactly 12 h apart -> new episode

    def test_immature_and_invalid_outcomes_are_not_scored(self):
        rows, fc, levels, hilo = _advisory_fixture(0.3, 2, "corrected")
        pairs, _s = AD.build_pairs(rows, fc.get, hilo)
        k = next(iter(levels))
        levels[k] = {"v": 5.0, "valid": False, "reason": "verified value inferred", "q": "v"}
        AD.attach_outcomes(pairs, levels, dt.datetime(2026, 9, 3, tzinfo=UTC))
        rep = AD.evaluate(pairs, {})
        self.assertEqual(rep["matured_valid"], 0)
        self.assertIn("immature", rep["unscored"])

    def test_phase_boundaries(self):
        hilo = [(dt.datetime(2026, 9, 24, 12, tzinfo=UTC), 6.0, "H"), (dt.datetime(2026, 9, 24, 18, 12, tzinfo=UTC), 1.0, "L"),
                (dt.datetime(2026, 9, 25, 0, 25, tzinfo=UTC), 6.0, "H")]
        self.assertEqual(AD.phase_of(dt.datetime(2026, 9, 24, 13, 30, tzinfo=UTC), hilo), "HIGH")
        self.assertEqual(AD.phase_of(dt.datetime(2026, 9, 24, 13, 31, tzinfo=UTC), hilo), "MID")
        self.assertEqual(AD.phase_of(dt.datetime(2026, 9, 24, 17, 0, tzinfo=UTC), hilo), "LOW")


class FidelityTests(unittest.TestCase):
    def test_constant_and_decay_rules_are_recognized(self):
        f, _r, p30 = _v106()
        self.assertLessEqual(F.f1_astronomy(f, p30)["max_abs_vs_rule"], 0.0006)
        tide = lambda t: p30[t] - 2.82 + 0.8
        old = {"water_series": _series(START, 73, tide), "all_tides": [{"surge_ft": 0.8}]}
        r = F.f1_astronomy(old, p30)
        self.assertEqual(r["rule"], "constant"); self.assertTrue(r["matches_a_tide_surge"]); self.assertLessEqual(r["spread"], 0.001)

    def test_mean_window_and_minimum(self):
        ms = M.MeanSeries.__new__(M.MeanSeries)
        t0 = dt.datetime(2025, 9, 1, tzinfo=UTC)
        ms.times = [t0 + dt.timedelta(hours=k) for k in range(24 * 400)]
        ms.cum = [0.0]
        for k, _t in enumerate(ms.times):
            ms.cum.append(ms.cum[-1] + (1.0 if k % 2 else 0.0))
        m, n, a, b = ms.as_of(dt.datetime(2026, 9, 24, 4, tzinfo=UTC))
        self.assertEqual(a, dt.datetime(2025, 9, 25, tzinfo=UTC)); self.assertEqual(b, dt.datetime(2026, 8, 31, 4, tzinfo=UTC))
        self.assertAlmostEqual(m, 0.5, places=2)
        self.assertIsNone(ms.as_of(dt.datetime(2025, 12, 1, tzinfo=UTC))[0])        # < 7,200 hours


class IsolationTests(unittest.TestCase):
    def test_production_never_imports_the_research_code(self):
        for p in (ROOT / "forecast").glob("*.py"):
            self.assertNotRegex(p.read_text(), r"as_issued", str(p))


if __name__ == "__main__":
    unittest.main()
