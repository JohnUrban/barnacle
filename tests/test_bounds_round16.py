"""Audit 2026-09-27-a1 round 16 (Codex) regressions, using COMPLETE real
ledger rows (all ten columns, so content hashes match the committed
data/observation_bounds.jsonl) plus a few synthetic rows written with the
same columns.

R1  interval-aware daily summary: a band whose floor exceeds a measured
    maximum at another time is retained; overlapping intervals disclose the
    possible higher level; one-sided bands compare claims against the known
    floor and keep an actually higher model maximum visible.
R2  time/scope metadata from the record; depth/location words never make a
    time uncertain; local pools never cap the intersection.
R3  one shared validation contract for writer, gate and reader; malformed
    lines are visible, never crashes or silent drops.
C1  a legacy range-representative scalar is superseded by its band.
"""
import copy
import csv
import datetime as dt
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import check_artifacts, flood_forecast_daily as ff, observation_bounds as ob, rendering
from tests.test_today_lookback import MODEL_39

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "labeled_observations.csv"
BOUNDS = ROOT / "data" / "observation_bounds.jsonl"
with LEDGER.open(newline="") as _f:
    ROWS = list(csv.DictReader(_f))
FIELDS = list(ROWS[0].keys())


def real(n):
    return dict(ROWS[n - 2])


def synthetic(time, key, depth="", qual=""):
    r = dict.fromkeys(FIELDS, "")
    r.update(observation_time_local=time, landmark_key=key, observed_depth_in=depth,
             observed_qualitative=qual, observer="john")
    return r


def lookback(rows, nowcast=None, now=None, bounds_text=None):
    """Temp repo with the given full rows and (by default) the committed
    bounds file; returns the payload and the input-health entry."""
    tmp = Path(tempfile.mkdtemp())
    (tmp / "data").mkdir(); (tmp / "docs").mkdir()
    with (tmp / "data" / "labeled_observations.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)
    (tmp / "data" / "observation_bounds.jsonl").write_text(
        BOUNDS.read_text() if bounds_text is None else bounds_text)
    if nowcast is not None:
        (tmp / "docs" / "nowcast.json").write_text(json.dumps(nowcast))
    now = now or dt.datetime(2026, 9, 27, 20, 0)
    with mock.patch.object(ff, "_REPO_ROOT", str(tmp)), \
            mock.patch.object(ff, "OBSERVATION_BOUNDS_PATH", str(tmp / "data" / "observation_bounds.jsonl")), \
            mock.patch.object(ff, "DAYMAX_REJECTIONS_PATH", str(tmp / "none.json")), \
            mock.patch.object(ff, "_station_local_now", return_value=now), \
            mock.patch.object(ff, "_fetch_actual_peak_around", return_value=(None, None)):
        lb = ff._today_lookback()
        return lb, ff._bounds_health()


def model(street_in, utc, day="2026-09-27"):
    return dict(MODEL_39, day_local=day, day_max_street_in=street_in, day_max_utc=utc)


def widget(lb):
    src = (ROOT / "docs" / "barnacle-widget.js").read_text(encoding="utf-8")
    js = src[src.index("// SOFAR-BEGIN"):src.index("// SOFAR-END")]
    js += "\nconsole.log(soFarText(JSON.parse(process.argv[1])));"
    run = subprocess.run(["node", "-e", js, json.dumps(lb)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    return run.stdout.strip()


HAS_NODE = bool(shutil.which("node"))


class R1IntervalAwareTests(unittest.TestCase):
    def test_lower_measurement_does_not_hide_higher_band(self):
        # Codex's probe: synthetic 06:00 dry reading + actual row 251 (09:14 breach, 5.41)
        lb, _ = lookback([synthetic("2026-09-27T06:00", "grate_SW", "0"), real(251)])
        self.assertEqual(lb["evidence"], "bounded")
        self.assertEqual(lb["time_local"], "09:14")
        self.assertEqual((lb["lo_rel_grate_in"], lb["hi_rel_grate_in"]), (22.7, 22.7))
        self.assertEqual(lb["n_checks"], 2)
        short = rendering._lookback_phrase(lb, short=True)
        self.assertEqual(short, "BOUNDED +22.7″ at 09:14 (landmarks)")
        if HAS_NODE:
            self.assertEqual(widget(lb), "so far: +22.7″ @09:14 (landmarks)")

    def test_measured_high_beats_lower_band(self):
        lb, _ = lookback([real(254), real(238)])       # 09:44 +25.2 measured; 08:12 band 4.14-4.16
        self.assertEqual(lb["evidence"], "measured")
        self.assertEqual(lb["rel_grate_in"], 25.2)
        self.assertNotIn("possible_up_to_rel_grate_in", lb)

    def test_overlapping_interval_discloses_possible_higher_level(self):
        # measured +8.2 at 09:44 (synthetic) and actual row 188 band 4.63-4.66 (+13.3..+13.7) at 07:15
        lb, _ = lookback([synthetic("2026-09-26T09:44", "curb", "0.5"), real(188)],
                         now=dt.datetime(2026, 9, 26, 12, 0))
        # row 188 is a Sep 26 row: run "today" as Sep 26
        self.assertEqual(lb["evidence"], "bounded")     # 4.63 floor beats the 4.20 point
        self.assertEqual(lb["time_local"], "07:15")
        lb2, _ = lookback([synthetic("2026-09-26T09:44", "curb", "8"), real(188)],
                          now=dt.datetime(2026, 9, 26, 12, 0))
        self.assertEqual(lb2["evidence"], "measured")   # 4.83 point beats the 4.63 floor
        self.assertNotIn("possible_up_to_rel_grate_in", lb2)
        lb3, _ = lookback([synthetic("2026-09-26T09:44", "curb", "6"), real(188)],
                          now=dt.datetime(2026, 9, 26, 12, 0))
        self.assertEqual(lb3["evidence"], "measured")   # 4.66 point equals the band top and beats its 4.63 floor
        self.assertNotIn("possible_up_to_rel_grate_in", lb3)
        # explicit disclosure case: point 4.64 (curb +5.76) inside band 4.63–4.66
        lb4, _ = lookback([synthetic("2026-09-26T09:44", "curb", "5.76"), real(188)],
                          now=dt.datetime(2026, 9, 26, 12, 0))
        self.assertEqual(lb4["evidence"], "measured")
        self.assertEqual(lb4["possible_up_to_rel_grate_in"], 13.7)
        self.assertEqual(lb4["possible_up_to_time_local"], "07:15")
        self.assertIn("allows up to +13.7", rendering._lookback_phrase(lb4, short=True))
        if HAS_NODE:
            self.assertIn("up to +13.7″ @07:15", widget(lb4))

    def test_one_sided_band_compares_claims_to_the_known_floor(self):
        # actual row 270: at least 3.91 (+4.7 in), no upper bound
        below = model(4.0, "2026-09-27T22:30:00Z")
        lb, _ = lookback([real(270)], below)
        self.assertEqual(lb["evidence"], "bounded")
        self.assertEqual(lb["lo_rel_grate_in"], 4.7)
        self.assertNotIn("model_claim", lb)                 # 4.0 is not above the known floor
        above = model(9.0, "2026-09-27T22:30:00Z")
        lb, _ = lookback([real(270)], above)
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 9.0)
        self.assertIn("no upper bound", lb["model_claim"]["verification"])
        self.assertIn("model claims +9.0", rendering._lookback_phrase(lb, short=True))

    def test_claim_within_and_above_a_closed_band(self):
        inside = model(7.5, "2026-09-27T12:15:00Z")         # 08:15 local, inside row 238's 4.14-4.16? no: 7.5 in = 4.145
        lb, _ = lookback([real(238)], inside)
        self.assertNotIn("model_claim", lb)
        above = model(39.0, "2026-09-27T12:15:00Z")
        lb, _ = lookback([real(238)], above)
        self.assertNotIn("model_claim", lb)                  # exact-time closed band covers it
        far = model(39.0, "2026-09-27T16:00:00Z")            # 12:00 local, outside the hour
        lb, _ = lookback([real(238)], far)
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 39.0)


class R2TimeAndScopeMetadataTests(unittest.TestCase):
    def test_depth_and_location_words_do_not_make_time_uncertain(self):
        self.assertFalse(ff._lookback_time_uncertain("puddles over the NE and NW grates, ~1 in above them"))
        self.assertFalse(ff._lookback_time_uncertain("local flooding around each of them"))
        self.assertTrue(ff._lookback_time_uncertain("stated next morning; exact observation time unconfirmed"))
        self.assertTrue(ff._lookback_time_uncertain("sometime 21:20-21:40 water spans"))
        self.assertTrue(ff._lookback_time_uncertain("time of clearing unknown (between 22:39 and 23:12)"))
        self.assertTrue(ff._lookback_time_uncertain("around 7 it was across central"))
        self.assertTrue(ff._lookback_time_uncertain("at the ~20:06 surge high tide"))

    def test_row_237_band_is_used_with_its_exact_time(self):
        lb, _ = lookback([real(237)], model(39.0, "2026-09-27T12:00:00Z"))   # 08:00 local
        self.assertEqual(lb["evidence"], "bounded")
        self.assertEqual((lb["lo_rel_grate_in"], lb["hi_rel_grate_in"]), (4.7, 10.1))
        self.assertFalse(lb["time_uncertain"])
        self.assertNotIn("model_claim", lb)                  # 39 > 4.36 within the hour of an exact band

    def test_row_269_local_pool_is_bounded_but_never_caps_the_intersection(self):
        lb, _ = lookback([real(269)], model(20.0, "2026-09-27T22:20:00Z"))   # 18:20 local
        self.assertEqual(lb["evidence"], "bounded")
        self.assertEqual(lb["scope"], "local")
        self.assertEqual((lb["lo_rel_grate_in"], lb["hi_rel_grate_in"]), (3.4, 6.4))
        self.assertFalse(lb["time_uncertain"])
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 20.0)
        self.assertIn("local pool", lb["model_claim"]["verification"])
        self.assertIn("(local pool)", rendering._lookback_phrase(lb, short=True))
        if HAS_NODE:
            self.assertIn("local pool", widget(lb))

    def test_rows_187_191_230_236_keep_their_time_metadata(self):
        lb, _ = lookback([real(187)], model(39.0, "2026-09-26T11:00:00Z", "2026-09-26"), now=dt.datetime(2026, 9, 26, 8, 0))
        self.assertEqual((lb["evidence"], lb["time_kind"], lb["time_uncertain"]), ("bounded", "approximate", True))
        self.assertIn("model_claim", lb)                     # approximate time never covers
        self.assertIn("~07:00", rendering._lookback_phrase(lb, short=True))
        lb, _ = lookback([real(191)], model(26.0, "2026-09-26T00:06:00Z", "2026-09-25"), now=dt.datetime(2026, 9, 25, 22, 0))
        self.assertEqual((lb["evidence"], lb["time_kind"]), ("bounded", "surrogate"))
        self.assertEqual(lb["hi_rel_grate_in"], 0.0)
        self.assertIn("model_claim", lb)
        lb, _ = lookback([real(230)], model(39.0, "2026-09-27T01:30:00Z", "2026-09-26"), now=dt.datetime(2026, 9, 26, 23, 0))
        self.assertEqual((lb["evidence"], lb["time_kind"]), ("bounded", "window"))
        self.assertEqual(lb["time_window_local"], ["2026-09-26T21:20:00-04:00", "2026-09-26T21:40:00-04:00"])
        self.assertIn("model_claim", lb)                     # window time + disputed cap: never covers
        lb, _ = lookback([real(236)], None, now=dt.datetime(2026, 9, 26, 23, 30))
        self.assertEqual((lb["evidence"], lb["time_kind"], lb["hi_rel_grate_in"]), ("bounded", "window", 0.0))

    def test_disputed_band_is_shown_but_never_covers(self):
        # row 230's 4.37 cap is marked disputed; an exact-time twin without dispute would cover
        lb, _ = lookback([real(230)], model(39.0, "2026-09-27T01:30:00Z", "2026-09-26"), now=dt.datetime(2026, 9, 26, 23, 0))
        self.assertEqual(lb["hi_rel_grate_in"], 10.2)
        self.assertIn("model_claim", lb)


class R3SharedContractTests(unittest.TestCase):
    def _tmp_ledger(self):
        tmp = Path(tempfile.mkdtemp())
        ledger = tmp / "obs.csv"
        with ledger.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerow(real(231))
        return tmp, ledger

    def _good(self, rows):
        return {"sha256": ob.row_hash(rows[0]), "csv_row": 2,
                "observation_time_local": rows[0]["observation_time_local"],
                "landmark_key": rows[0]["landmark_key"], "lo_navd88": 4.14, "hi_navd88": 4.16,
                "basis": "stated_landmarks", "landmarks": [{"key": "curb", "navd88": 4.16,
                                                            "relation": "not over", "source": "model/elevations.md"}],
                "text": "band", "recorded_utc": "2026-09-28T00:00:00Z", "recorded_by": "test"}

    def test_reproduced_invalid_records_are_rejected_by_the_contract(self):
        tmp, ledger = self._tmp_ledger()
        rows = ob.load_ledger_rows(ledger)
        good = self._good(rows)
        self.assertEqual(ob.validate_record(good, rows), [])
        cases = {
            "string bound": dict(good, lo_navd88="4.14"),
            "boolean bound": dict(good, lo_navd88=True),
            "empty landmarks": dict(good, landmarks=[]),
            "landmark without source": dict(good, landmarks=[{"key": "curb", "navd88": 4.16, "relation": "x"}]),
            "landmark elevation infinite": dict(good, landmarks=[{"key": "curb", "navd88": float("inf"), "relation": "x", "source": "s"}]),
            "wrong csv_row identity": dict(good, csv_row=3),
            "wrong time identity": dict(good, observation_time_local="2026-01-01T00:00"),
            "wrong landmark identity": dict(good, landmark_key="lawn_step"),
            "overflow to infinity": dict(good, lo_navd88=float("inf")),
            "inverted": dict(good, lo_navd88=4.20),
            "no bound": dict(good, lo_navd88=None, hi_navd88=None),
            "bad time_kind": dict(good, time_kind="guess"),
            "bad scope": dict(good, scope="street"),
            "window without endpoints": dict(good, time_kind="window"),
            "non-boolean flag": dict(good, disputed="yes"),
        }
        for name, rec in cases.items():
            self.assertTrue(ob.validate_record(rec, rows), name)

    def test_gate_and_reader_see_the_same_problems(self):
        tmp, ledger = self._tmp_ledger()
        rows = ob.load_ledger_rows(ledger)
        good = self._good(rows)
        text = (json.dumps(good) + "\n" + json.dumps(dict(good, lo_navd88="4.14")) + "\n"
                + "null\n" + '{"lo_navd88": 1e309}\n' + json.dumps(dict(good, hi_navd88=4.20)) + "\n")
        path = tmp / "bounds.jsonl"; path.write_text(text)
        problems = check_artifacts.validate_observation_bounds(str(path), str(ledger))
        self.assertEqual(len(problems), 3, problems)          # string bound, null line, overflow line
        by_hash, reader_problems = ob.load_bounds(str(path), rows)
        self.assertEqual(reader_problems, problems)
        self.assertEqual(by_hash[good["sha256"]]["hi_navd88"], 4.20)   # last valid line wins

    def test_nan_write_leaves_the_file_unchanged(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("aob", ROOT / "bin" / "append_observation_bound.py")
        aob = importlib.util.module_from_spec(spec); spec.loader.exec_module(aob)
        tmp, ledger = self._tmp_ledger()
        path = tmp / "bounds.jsonl"; path.write_text("")
        lm = [{"key": "curb", "navd88": 4.16, "relation": "x", "source": "s"}]
        with self.assertRaises(ValueError):
            aob.append_bound(2, float("nan"), 4.16, "stated_landmarks", lm, "t", "t", str(ledger), str(path))
        with self.assertRaises(ValueError):
            aob.append_bound(2, 4.14, float("inf"), "stated_landmarks", lm, "t", "t", str(ledger), str(path))
        self.assertEqual(path.read_text(), "")
        aob.append_bound(2, 4.14, None, "stated_landmarks", lm, "one-sided", "t", str(ledger), str(path))
        self.assertEqual(check_artifacts.validate_observation_bounds(str(path), str(ledger)), [])

    def test_malformed_line_is_a_visible_degraded_input_not_a_crash(self):
        # the full real ledger, so every committed band validates; then one bad line
        bad = BOUNDS.read_text() + '{"sha256": "x", "csv_row": 2, "lo_navd88": "4.14"}\n'
        lb, health = lookback([dict(r) for r in ROWS], bounds_text=bad)
        self.assertEqual(lb["evidence"], "measured")           # Sep 27: the 09:44 reading still leads
        self.assertEqual(lb["rel_grate_in"], 25.2)
        self.assertEqual(health["status"], "degraded")
        self.assertIn("1 invalid line", health["detail"])
        lb, health = lookback([dict(r) for r in ROWS])
        self.assertIsNone(health)

    def test_committed_file_passes_and_carries_metadata(self):
        rows = ob.load_ledger_rows(LEDGER)
        by_hash, problems = ob.load_bounds(str(BOUNDS), rows)
        self.assertEqual(problems, [])
        by_row = {r["csv_row"]: r for r in by_hash.values()}
        self.assertEqual(by_row[187]["time_kind"], "approximate")
        self.assertEqual(by_row[191]["time_kind"], "surrogate")
        self.assertEqual(by_row[230]["time_kind"], "window")
        self.assertTrue(by_row[230]["disputed"])
        self.assertEqual(by_row[269]["scope"], "local")
        self.assertTrue(by_row[231]["supersedes_scalar"])


class C1LegacyScalarTests(unittest.TestCase):
    def test_row_231_band_supersedes_its_range_representative_scalar(self):
        lb, _ = lookback([real(231)], now=dt.datetime(2026, 9, 26, 23, 0))
        self.assertEqual(lb["evidence"], "bounded")
        self.assertEqual((lb["lo_rel_grate_in"], lb["hi_rel_grate_in"]), (7.4, 7.7))
        self.assertEqual(rendering._lookback_phrase(lb, short=True),
                         "BOUNDED +7.4″ to +7.7″ at 21:54 (landmarks)")

    def test_sidecar_marks_the_superseded_scalar(self):
        d = json.loads((ROOT / "assets/observations/2026-09-27/analysis/observation_intervals.json").read_text())
        rec = next(r for r in d["records"] if r["csv_row"] == 231)
        self.assertTrue(rec.get("ledger_scalar_superseded"))
        self.assertEqual(rec["landmark_band_navd88"], [4.14, 4.16])
        self.assertEqual(rec["depth_basis"], "stated_landmarks")


if __name__ == "__main__":
    unittest.main()
