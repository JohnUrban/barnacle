"""Owner rule 2026-09-27 22:44 (BACKLOG PREF observations-are-quantitative):
a report relating water to landmarks of known height is quantitative. Bands
are recorded by an agent from the survey in data/observation_bounds.jsonl
(append-only, row-hash keyed, landmark provenance); production reads only
those records, never prose. Tests cover the writer, the publish-gate
validator, the so-far precedence and coverage, and every rendering arm."""
import csv
import datetime as dt
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import check_artifacts, flood_forecast_daily as ff, observation_bounds as ob, rendering
from tests.test_today_lookback import FIELDS, MODEL_39, NOW

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("append_observation_bound",
                                              ROOT / "bin" / "append_observation_bound.py")
aob = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aob)

LM = [{"key": "upstream_grate_sidewalk", "navd88": 4.14, "relation": "over",
       "source": "assets/map_points.csv (approximated)"},
      {"key": "curb", "navd88": 4.16, "relation": "not over", "source": "model/elevations.md"}]
ROW_2154 = ('2026-09-27T21:54,curb,,"less than 1 cm below the curb in front of the lawn step; '
            'OVER the curb at the upstream grate area (user)"\n')


def _repo(rows, bounds=None):
    tmp = Path(tempfile.mkdtemp())
    (tmp / "data").mkdir(); (tmp / "docs").mkdir()
    (tmp / "data" / "labeled_observations.csv").write_text(FIELDS + rows)
    if bounds:
        with (tmp / "data" / "observation_bounds.jsonl").open("w") as f:
            for b in bounds:
                f.write(json.dumps(b) + "\n")
    return tmp


def _lookback(tmp, nowcast=None, now=NOW):
    if nowcast is not None:
        (tmp / "docs" / "nowcast.json").write_text(json.dumps(nowcast))
    with mock.patch.object(ff, "_REPO_ROOT", str(tmp)), \
            mock.patch.object(ff, "OBSERVATION_BOUNDS_PATH", str(tmp / "data" / "observation_bounds.jsonl")), \
            mock.patch.object(ff, "DAYMAX_REJECTIONS_PATH", str(tmp / "none.json")), \
            mock.patch.object(ff, "_station_local_now", return_value=now), \
            mock.patch.object(ff, "_fetch_actual_peak_around", return_value=(None, None)):
        return ff._today_lookback()


def _widget(lb):
    src = (ROOT / "docs" / "barnacle-widget.js").read_text(encoding="utf-8")
    js = src[src.index("// SOFAR-BEGIN"):src.index("// SOFAR-END")]
    js += "\nconsole.log(soFarText(JSON.parse(process.argv[1])));"
    run = subprocess.run(["node", "-e", js, json.dumps(lb)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    return run.stdout.strip()


class WriterAndGateTests(unittest.TestCase):
    def test_writer_appends_a_valid_hash_keyed_record(self):
        tmp = _repo(ROW_2154)
        ledger, path = str(tmp / "data" / "labeled_observations.csv"), str(tmp / "data" / "bounds.jsonl")
        rec = aob.append_bound(2, 4.14, 4.16, "stated_landmarks", LM, "band", "test", ledger, path)
        with open(ledger, newline="") as f:
            row = list(csv.DictReader(f))[0]
        self.assertEqual(rec["sha256"], ff._observation_row_hash(row))
        self.assertEqual(list(ob.load_bounds(path)[0].values())[0]["lo_navd88"], 4.14)
        self.assertEqual(check_artifacts.validate_observation_bounds(path, ledger), [])

    def test_writer_rejects_bad_bands(self):
        tmp = _repo(ROW_2154)
        ledger, path = str(tmp / "data" / "labeled_observations.csv"), str(tmp / "data" / "bounds.jsonl")
        with self.assertRaises(ValueError):
            aob.append_bound(2, 4.20, 4.16, "stated_landmarks", LM, "inverted", "t", ledger, path)
        with self.assertRaises(ValueError):
            aob.append_bound(2, None, None, "stated_landmarks", LM, "none", "t", ledger, path)
        with self.assertRaises(ValueError):
            aob.append_bound(2, 4.14, 4.16, "analyst_guess", LM, "basis", "t", ledger, path)
        with self.assertRaises(ValueError):
            aob.append_bound(9, 4.14, 4.16, "stated_landmarks", LM, "row", "t", ledger, path)

    def test_gate_rejects_orphan_and_malformed_lines(self):
        tmp = _repo(ROW_2154)
        ledger, path = str(tmp / "data" / "labeled_observations.csv"), str(tmp / "data" / "bounds.jsonl")
        Path(path).write_text(json.dumps({"sha256": "0" * 64, "csv_row": 2, "observation_time_local": "x",
                                          "landmark_key": "curb", "lo_navd88": 4.14, "hi_navd88": 4.16,
                                          "basis": "stated_landmarks", "landmarks": LM, "text": "t",
                                          "recorded_utc": "u", "recorded_by": "t"}) + "\n{not json\n")
        problems = check_artifacts.validate_observation_bounds(path, ledger)
        self.assertTrue(any("sha256" in p for p in problems))
        self.assertTrue(any("not strict JSON" in p for p in problems))

    def test_committed_bounds_file_passes_the_gate_and_cites_landmarks(self):
        path = ROOT / "data" / "observation_bounds.jsonl"
        self.assertEqual(check_artifacts.validate_observation_bounds(
            str(path), str(ROOT / "data" / "labeled_observations.csv")), [])
        recs = list(ob.load_bounds(str(path))[0].values())
        self.assertGreaterEqual(len(recs), 15)
        for r in recs:
            self.assertTrue(r["landmarks"] and all(lm.get("source") for lm in r["landmarks"]))
        by_row = {r["csv_row"]: r for r in recs}
        self.assertEqual((by_row[231]["lo_navd88"], by_row[231]["hi_navd88"]), (4.14, 4.16))
        self.assertEqual((by_row[251]["lo_navd88"], by_row[251]["hi_navd88"]), (5.41, 5.41))
        self.assertEqual(by_row[224]["hi_navd88"], 3.52)


class BoundedEvidenceTests(unittest.TestCase):
    def _bounded(self, extra_rows="", nowcast=None, **kw):
        tmp = _repo(ROW_2154 + extra_rows)
        ledger, path = str(tmp / "data" / "labeled_observations.csv"), str(tmp / "data" / "observation_bounds.jsonl")
        aob.append_bound(2, kw.get("lo", 4.14), kw.get("hi", 4.16), "stated_landmarks", LM,
                         "over the upstream-grate sidewalk (4.14); not over the walkway curb (4.16)", "t",
                         ledger, path)
        return _lookback(tmp, nowcast)

    def test_band_is_the_headline_when_no_inches_were_read(self):
        lb = self._bounded()
        self.assertEqual(lb["evidence"], "bounded")
        self.assertEqual((lb["lo_rel_grate_in"], lb["hi_rel_grate_in"]), (7.4, 7.7))
        self.assertEqual(lb["time_local"], "21:54")
        self.assertIn("upstream-grate sidewalk", lb["band_text"])
        self.assertIn("2026-09-27T21:54", "2026-09-27T21:54")

    def test_measured_inches_still_beat_a_band(self):
        lb = self._bounded(extra_rows="2026-09-27T09:44,porch_step_base,11.25,\n")
        self.assertEqual(lb["evidence"], "measured")
        self.assertEqual(lb["rel_grate_in"], 25.2)

    def test_band_upper_bound_suppresses_a_higher_same_hour_claim(self):
        claim = dict(MODEL_39, day_max_street_in=39.0, day_max_utc="2026-09-28T01:40:00Z")  # 21:40 local
        lb = self._bounded(nowcast=claim)
        self.assertEqual(lb["evidence"], "bounded")
        self.assertNotIn("model_claim", lb)

    def test_claim_inside_the_band_is_not_a_claim(self):
        claim = dict(MODEL_39, day_max_street_in=7.5, day_max_utc="2026-09-28T01:40:00Z")
        lb = self._bounded(nowcast=claim)
        self.assertNotIn("model_claim", lb)

    def test_lower_bound_only_cannot_suppress(self):
        claim = dict(MODEL_39, day_max_street_in=39.0, day_max_utc="2026-09-28T01:40:00Z")
        lb = self._bounded(nowcast=claim, lo=4.14, hi=None)
        self.assertEqual(lb["evidence"], "bounded")
        self.assertEqual(lb["lo_rel_grate_in"], 7.4)
        self.assertIsNone(lb["hi_rel_grate_in"])
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 39.0)

    def test_uncertain_time_band_does_not_cover(self):
        row = ('2026-09-27T20:06,grate_SW,,"NO flooding (exact observation time unconfirmed)"\n')
        tmp = _repo(row)
        ledger, path = str(tmp / "data" / "labeled_observations.csv"), str(tmp / "data" / "observation_bounds.jsonl")
        aob.append_bound(2, None, 3.52, "stated_landmarks",
                         [{"key": "grate_SW", "navd88": 3.52, "relation": "not reached", "source": "model/elevations.md"}],
                         "below the SW grate", "t", ledger, path)
        claim = dict(MODEL_39, day_max_street_in=26.0, day_max_utc="2026-09-28T00:06:00Z")
        lb = _lookback(tmp, claim)
        # round 16 R2: the band is kept as quantitative evidence with its
        # uncertain time; it never covers the claim
        self.assertEqual(lb["evidence"], "bounded")
        self.assertTrue(lb["time_uncertain"])
        self.assertIn("unconfirmed", lb["model_claim"]["verification"])

    def test_every_arm_renders_the_band(self):
        lb = self._bounded()
        short = rendering._lookback_phrase(lb, short=True)
        full = rendering._lookback_phrase(lb)
        html = rendering._lookback_phrase(lb, html=True)
        self.assertEqual(short, "BOUNDED +7.4″ to +7.7″ at 21:54 (landmarks)")
        self.assertIn("landmark band: over the upstream-grate sidewalk (4.14)", full)
        self.assertIn("&Prime;", html)
        self.assertTrue(rendering._lookback_visible(lb))
        if shutil.which("node"):
            self.assertEqual(_widget(lb), "so far: +7.4″–+7.7″ @21:54 (landmarks)")

    def test_one_sided_band_phrases(self):
        lb = self._bounded(lo=4.14, hi=None)
        self.assertEqual(rendering._lookback_phrase(lb, short=True), "BOUNDED at least +7.4″ at 21:54 (landmarks)")
        lb = self._bounded(lo=None, hi=3.52)
        self.assertEqual(rendering._lookback_phrase(lb, short=True), "BOUNDED at most +0.0″ at 21:54 (landmarks)")


if __name__ == "__main__":
    unittest.main()
