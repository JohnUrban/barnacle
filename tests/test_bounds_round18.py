"""Audit 2026-09-27-a1 round 18 (Codex) regressions.

R1  the legacy-prose time fallback must not read depth ranges ("around 10
    inches", "between 1 and 2 inches") as time uncertainty, and a recorded
    band's explicit time_kind is authoritative through the whole
    row → payload → render → coverage path.
R2  a disputed upper endpoint is shown but never used to dismiss a higher
    unverified model estimate: not as the eligibility threshold, not as
    coverage, not through possible_up_to.
R3  a missing or unreadable bounds file is a visible degraded input with a
    safe fallback; the gate gives an actionable diagnostic for unreadable
    input; health clears on the next clean read.
"""
import csv
import datetime as dt
import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

from forecast import check_artifacts, flood_forecast_daily as ff, observation_bounds as ob, rendering
from tests.test_bounds_round16 import FIELDS, ROWS, model, real, synthetic, widget, HAS_NODE

ROOT = Path(__file__).resolve().parents[1]
BOUNDS = ROOT / "data" / "observation_bounds.jsonl"
spec = importlib.util.spec_from_file_location("aob", ROOT / "bin" / "append_observation_bound.py")
aob = importlib.util.module_from_spec(spec); spec.loader.exec_module(aob)


def repo(rows, bounds_text=None, bounds_path_override=None):
    tmp = Path(tempfile.mkdtemp())
    (tmp / "data").mkdir(); (tmp / "docs").mkdir()
    with (tmp / "data" / "labeled_observations.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    if bounds_text is not None:
        (tmp / "data" / "observation_bounds.jsonl").write_text(bounds_text)
    return tmp


def run(tmp, nowcast=None, now=None, expected=True):
    if nowcast is not None:
        (tmp / "docs" / "nowcast.json").write_text(json.dumps(nowcast))
    now = now or dt.datetime(2026, 9, 27, 20, 0)
    with mock.patch.object(ff, "_REPO_ROOT", str(tmp)), \
            mock.patch.object(ff, "OBSERVATION_BOUNDS_PATH", str(tmp / "data" / "observation_bounds.jsonl")), \
            mock.patch.object(ff, "OBSERVATION_BOUNDS_EXPECTED", expected), \
            mock.patch.object(ff, "DAYMAX_REJECTIONS_PATH", str(tmp / "none.json")), \
            mock.patch.object(ff, "_station_local_now", return_value=now), \
            mock.patch.object(ff, "_fetch_actual_peak_around", return_value=(None, None)), \
            redirect_stdout(io.StringIO()):
        lb = ff._today_lookback()
        return lb, ff._bounds_health()


class R1TimeFallbackTests(unittest.TestCase):
    def test_depth_ranges_are_not_time_uncertainty(self):
        for text in ("around 10 inches over the grate", "between 1 and 2 inches above the curb",
                     "~1 in above them", "local flooding around each", "around 10\" over the NE grate",
                     "between 0.5 and 1 inch over the curb"):
            self.assertFalse(ff._lookback_time_uncertain(text), text)
        for text in ("around 7 it was across central", "around 7:30 pm the water came",
                     "between 21:20 and 21:40", "between 9 and 10 pm", "time of clearing unknown (between 22:39 and 23:12)",
                     "exact observation time unconfirmed", "at the ~20:06 surge high tide", "sometime after 9"):
            self.assertTrue(ff._lookback_time_uncertain(text), text)

    def _exact_row_with_depth_phrase(self, phrase):
        row = synthetic("2026-09-27T08:12", "curb", "", phrase)
        tmp = repo([row])
        ledger, path = str(tmp / "data" / "labeled_observations.csv"), str(tmp / "data" / "observation_bounds.jsonl")
        lm = [{"key": "upstream_grate_sidewalk", "navd88": 4.14, "relation": "over", "source": "assets/map_points.csv"},
              {"key": "curb", "navd88": 4.16, "relation": "not over", "source": "model/elevations.md"}]
        with redirect_stderr(io.StringIO()):
            aob.append_bound(2, 4.14, 4.16, "stated_landmarks", lm, "band", "t", ledger, path)
        return tmp

    def test_recorded_exact_band_with_depth_phrase_renders_exact_and_covers(self):
        for phrase in ("between 1 and 2 inches above the curb, over the curb at the upstream grate",
                       "around 10 inches over the grate; not over the walkway curb"):
            tmp = self._exact_row_with_depth_phrase(phrase)
            lb, _ = run(tmp, model(39.0, "2026-09-27T12:15:00Z"))
            self.assertEqual(lb["evidence"], "bounded", phrase)
            self.assertFalse(lb["time_uncertain"], phrase)
            short = rendering._lookback_phrase(lb, short=True)
            self.assertIn(" at 08:12", short)
            self.assertNotIn("~08:12", short)
            self.assertNotIn("model_claim", lb)        # exact band covers the same-hour 39-in claim
            if HAS_NODE:
                self.assertIn("@08:12", widget(lb))

    def test_writer_warns_when_prose_and_metadata_disagree(self):
        row = synthetic("2026-09-27T20:06", "grate_SW", "", "NO flooding; exact observation time unconfirmed")
        tmp = repo([row])
        ledger, path = str(tmp / "data" / "labeled_observations.csv"), str(tmp / "data" / "observation_bounds.jsonl")
        lm = [{"key": "grate_SW", "navd88": 3.52, "relation": "not reached", "source": "model/elevations.md"}]
        err = io.StringIO()
        with redirect_stderr(err):
            aob.append_bound(2, None, 3.52, "stated_landmarks", lm, "band", "t", ledger, path)
        self.assertIn("uncertain time", err.getvalue())
        err = io.StringIO()
        with redirect_stderr(err):
            aob.append_bound(2, None, 3.52, "stated_landmarks", lm, "band", "t", ledger, path, time_kind="surrogate")
        self.assertEqual(err.getvalue(), "")


class R2DisputedCapTests(unittest.TestCase):
    """Actual row 230: band 3.91–4.37 with the 4.37 cap disputed, window 21:20–21:40."""

    def _row230(self, street_in, at_utc="2026-09-27T01:30:00Z", bounds_text=None):
        tmp = repo([real(230)], BOUNDS.read_text() if bounds_text is None else bounds_text)
        return run(tmp, model(street_in, at_utc, "2026-09-26"), now=dt.datetime(2026, 9, 26, 23, 0))

    def test_model_between_floor_and_disputed_cap_stays_visible(self):
        lb, _ = self._row230(9.0)                       # 4.27 ft: between 3.91 and 4.37
        self.assertEqual(lb["evidence"], "bounded")
        self.assertTrue(lb["hi_disputed"])
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 9.0)
        self.assertIn("disputed", lb["model_claim"]["verification"])
        short = rendering._lookback_phrase(lb, short=True)
        self.assertIn("(cap disputed)", short)
        self.assertIn("model claims +9.0", short)
        if HAS_NODE:
            self.assertIn("cap?", widget(lb))

    def test_model_above_disputed_cap_stays_visible(self):
        lb, _ = self._row230(39.0)
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 39.0)

    def test_model_below_known_floor_is_not_a_claim(self):
        lb, _ = self._row230(3.0)                       # 3.77 ft < 3.91 floor
        self.assertNotIn("model_claim", lb)

    def test_undisputed_twin_band_keeps_intended_behavior(self):
        # same row, same band, but recorded WITHOUT the dispute and with an exact time:
        # a model inside the band is not a claim and a higher one is covered
        rec = next(json.loads(l) for l in BOUNDS.read_text().splitlines()
                   if l.strip() and json.loads(l)["csv_row"] == 230 and json.loads(l).get("disputed"))
        twin = dict(rec, disputed=False, time_kind="stated_exact", time_window_local=None)
        lb, _ = self._row230(9.0, bounds_text=json.dumps(twin) + "\n")
        self.assertNotIn("model_claim", lb)
        lb, _ = self._row230(39.0, bounds_text=json.dumps(twin) + "\n")
        self.assertNotIn("model_claim", lb)

    def test_secondary_disputed_band_does_not_feed_possible_up_to(self):
        # a measured 4.20 (curb +0.5) at 23:30 (outside the claim's hour, so the
        # measurement itself does not cover) plus row 230's disputed 4.37 cap:
        # the disputed cap must not become "possible up to +10.2" nor dismiss
        # the 4.27 estimate at 21:30
        rows = [real(230), synthetic("2026-09-26T23:30", "curb", "0.5")]
        tmp = repo(rows, BOUNDS.read_text())
        lb, _ = run(tmp, model(9.0, "2026-09-27T01:30:00Z", "2026-09-26"), now=dt.datetime(2026, 9, 26, 23, 0))
        self.assertEqual(lb["evidence"], "measured")
        self.assertNotIn("possible_up_to_rel_grate_in", lb)
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 9.0)   # 4.27 > 4.20 and not dismissed by 4.37


class R3FileLevelTests(unittest.TestCase):
    def test_missing_expected_file_is_degraded_with_safe_fallback(self):
        tmp = repo([real(254)])
        lb, health = run(tmp)
        self.assertEqual(lb["evidence"], "measured")
        self.assertEqual(health["status"], "degraded")
        self.assertIn("missing", health["detail"])

    def test_missing_file_not_expected_is_not_reported(self):
        tmp = repo([real(254)])
        lb, health = run(tmp, expected=False)
        self.assertEqual(lb["evidence"], "measured")
        self.assertIsNone(health)

    def test_unreadable_path_is_degraded_not_an_exception(self):
        tmp = repo([real(254)])
        os.mkdir(tmp / "data" / "observation_bounds.jsonl")     # a directory at the expected path
        lb, health = run(tmp)
        self.assertEqual(lb["evidence"], "measured")
        self.assertEqual(health["status"], "degraded")
        self.assertIn("unavailable", health["detail"])
        self.assertIn("IsADirectoryError", health["detail"])
        self.assertNotIn(str(tmp), health["detail"])              # sanitized: class name only

    def test_undecodable_file_is_degraded(self):
        tmp = repo([real(254)])
        (tmp / "data" / "observation_bounds.jsonl").write_bytes(b"\xff\xfe\x00bad")
        lb, health = run(tmp)
        self.assertEqual(health["status"], "degraded")
        self.assertIn("UnicodeDecodeError", health["detail"])

    def test_health_clears_after_a_clean_read(self):
        tmp = repo([dict(r) for r in ROWS])
        os.mkdir(tmp / "data" / "observation_bounds.jsonl")
        _, health = run(tmp)
        self.assertEqual(health["status"], "degraded")
        os.rmdir(tmp / "data" / "observation_bounds.jsonl")
        (tmp / "data" / "observation_bounds.jsonl").write_text(BOUNDS.read_text())
        _, health = run(tmp)
        self.assertIsNone(health)

    def test_gate_diagnoses_unreadable_input_and_ignores_absence(self):
        tmp = repo([real(254)])
        ledger = str(tmp / "data" / "labeled_observations.csv")
        self.assertEqual(check_artifacts.validate_observation_bounds(str(tmp / "data" / "observation_bounds.jsonl"), ledger), [])
        os.mkdir(tmp / "data" / "observation_bounds.jsonl")
        problems = check_artifacts.validate_observation_bounds(str(tmp / "data" / "observation_bounds.jsonl"), ledger)
        self.assertEqual(len(problems), 1)
        self.assertIn("cannot be read", problems[0])
        self.assertIn("IsADirectoryError", problems[0])

    def test_build_forecast_health_state_is_reset_per_build(self):
        # a stale unreadable status must not leak into a build whose lookback is mocked
        ff._BOUNDS_STATUS["status"] = "unreadable"; ff._BOUNDS_PROBLEMS[:] = ["x"]
        src = Path(ff.__file__).read_text()
        self.assertIn('_BOUNDS_STATUS["status"] = "unknown"', src)
        self.assertIn('_bh = _bounds_health() if _BOUNDS_STATUS.get("status") != "unknown" else None', src)
        ff._BOUNDS_STATUS["status"] = "unknown"; ff._BOUNDS_PROBLEMS[:] = []
        self.assertIsNone(ff._bounds_health())


if __name__ == "__main__":
    unittest.main()
