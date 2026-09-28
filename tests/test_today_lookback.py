"""Owner DECISION 2026-09-27 (audit 2026-09-27-a1 reply 04, option 3; round 05
R1): on the "so far today" line empirical evidence beats a model guess and is
chosen INDEPENDENTLY of positivity. Headline by evidence class — tape (even a
dry check), else the latest qualitative report, else the bay peak over
station-local midnight→now labeled as bay, else the nowcast model — and a
higher model day max at an UNMEASURED time is appended as a claim, never
promoted. Every arm renders the same phrase."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import flood_forecast_daily as ff
from forecast import rendering

NOW = dt.datetime(2026, 9, 27, 17, 0)
FIELDS = "observation_time_local,landmark_key,observed_depth_in,observed_qualitative\n"


def lookback(rows="", nowcast=None, gauge=(None, None), now=NOW):
    tmp = Path(tempfile.mkdtemp())
    (tmp / "data").mkdir()
    (tmp / "docs").mkdir()
    (tmp / "data" / "labeled_observations.csv").write_text(FIELDS + rows)
    if nowcast is not None:
        (tmp / "docs" / "nowcast.json").write_text(json.dumps(nowcast))
    fetch = gauge if callable(gauge) else mock.Mock(return_value=gauge)
    with mock.patch.object(ff, "_REPO_ROOT", str(tmp)), \
            mock.patch.object(ff, "DAYMAX_REJECTIONS_PATH", str(tmp / "none.json")), \
            mock.patch.object(ff, "_station_local_now", return_value=now), \
            mock.patch.object(ff, "_fetch_actual_peak_around", fetch):
        return ff._today_lookback()


MODEL_39 = {"generated_utc": "2026-09-27T20:40:52Z", "day_local": "2026-09-27",
            "day_max_street_in": 39.0, "day_max_utc": "2026-09-27T06:40:00Z"}
TAPE = "2026-09-27T09:44,porch_step_base,11.25,\n2026-09-27T12:48:00-04:00,curb,0.75,\n"
DRY_0250 = "2026-09-27T02:50,grate_SW,0,\n"
DRY_0944 = "2026-09-27T09:44,grate_SW,0,\n"


class PrecedenceTests(unittest.TestCase):
    def test_tape_beats_higher_model_and_model_is_appended_as_claim(self):
        lb = lookback(TAPE, MODEL_39)
        self.assertEqual(lb["evidence"], "measured")
        self.assertEqual(lb["rel_grate_in"], 25.2)
        self.assertEqual(lb["time_local"], "09:44")
        self.assertEqual(lb["n_checks"], 2)
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 39.0)
        self.assertEqual(lb["model_claim"]["time_local"], "02:40")

    def test_model_claim_inside_a_measured_hour_is_discarded(self):
        lb = lookback(TAPE + DRY_0250, MODEL_39)
        self.assertEqual(lb["rel_grate_in"], 25.2)
        self.assertNotIn("model_claim", lb)

    def test_lower_model_is_not_a_claim(self):
        lb = lookback(TAPE, dict(MODEL_39, day_max_street_in=6.4))
        self.assertNotIn("model_claim", lb)

    # round 05 R1: dry measurements are evidence, not absence of evidence
    def test_dry_check_in_the_same_window_beats_modeled_flooding(self):
        lb = lookback(DRY_0250, MODEL_39)
        self.assertEqual(lb["evidence"], "measured")
        self.assertEqual(lb["rel_grate_in"], 0.0)
        self.assertEqual(lb["regime"], "dry")
        self.assertEqual(lb["time_local"], "02:50")
        self.assertNotIn("model_claim", lb)          # 02:40 is inside the measured hour

    def test_dry_check_beats_bay_peak_and_is_not_relabeled_bay(self):
        lb = lookback(DRY_0944, None, gauge=(7.57, "2026-09-27 09:44"))
        self.assertEqual(lb["evidence"], "measured")
        self.assertNotIn("corner not measured", lb["source"])
        self.assertEqual(lb["rel_grate_in"], 0.0)

    def test_below_grate_measurement_keeps_negative_value(self):
        lb = lookback("2026-09-27T02:50,grate_SW,-2.0,\n", None)
        self.assertEqual(lb["evidence"], "measured")
        self.assertEqual(lb["rel_grate_in"], -2.0)
        self.assertEqual(lb["regime"], "dry")

    def test_dry_check_with_model_at_a_different_time_appends_claim(self):
        model_1500 = dict(MODEL_39, day_max_street_in=12.0, day_max_utc="2026-09-27T19:00:00Z")
        lb = lookback(DRY_0250, model_1500)
        self.assertEqual(lb["evidence"], "measured")
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 12.0)
        self.assertEqual(lb["model_claim"]["time_local"], "15:00")

    def test_qualitative_only_is_reported_not_modeled(self):
        lb = lookback('2026-09-27T21:10,grate_SW,,still NO flooding at the intersection (user)\n',
                      MODEL_39)
        self.assertEqual(lb["evidence"], "reported")
        self.assertIsNone(lb["rel_grate_in"])
        self.assertEqual(lb["time_local"], "21:10")
        self.assertFalse(lb["time_uncertain"])
        self.assertIn("NO flooding", lb["report"])
        # the model's 02:40 was not covered by any report → appended, not promoted
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 39.0)

    def test_qualitative_uncertain_time_is_flagged(self):
        lb = lookback('2026-09-27T20:06,grate_SW,,"NO flooding (stated next morning; exact observation time unconfirmed)"\n', None)
        self.assertEqual(lb["evidence"], "reported")
        self.assertTrue(lb["time_uncertain"])

    def test_metadata_rows_are_ignored(self):
        lb = lookback('2026-09-27T15:26:00-04:00,none,,Retrospective clarification\n', None)
        self.assertIsNone(lb)

    def test_bay_peak_is_labeled_bay_not_corner_regime(self):
        lb = lookback("", None, gauge=(7.57, "2026-09-27 20:06"))
        self.assertEqual(lb["evidence"], "bay")
        self.assertEqual(lb["regime"], "bay")
        self.assertIn("corner not measured", lb["source"])
        self.assertAlmostEqual(lb["navd88"], 4.75, places=2)

    def test_bay_beats_higher_model_which_is_appended(self):
        lb = lookback("", dict(MODEL_39, day_max_street_in=20.0,
                               day_max_utc="2026-09-27T19:00:00Z"),
                      gauge=(7.57, "2026-09-27 20:06"))
        self.assertEqual(lb["evidence"], "bay")
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 20.0)

    def test_model_alone_when_nothing_empirical(self):
        lb = lookback("", dict(MODEL_39, day_max_street_in=6.4))
        self.assertEqual(lb["evidence"], "modeled")
        self.assertIn("unverified", lb["source"])
        self.assertEqual(lb["rel_grate_in"], 6.4)
        self.assertNotIn("model_claim", lb)

    def test_nothing_at_all_is_none(self):
        self.assertIsNone(lookback("", None))


class DailyGaugeWindowTests(unittest.TestCase):
    """round 05 R1: the gauge fallback must cover station-local midnight → now,
    not ±12 h around now."""
    SERIES = {"2026-09-26 22:00": 8.0, "2026-09-27 00:30": 6.5,
              "2026-09-27 06:00": 7.5, "2026-09-27 20:00": 6.0}

    def _fake(self, time_str, window_hours=2):
        center = ff.parse_station_local_time(time_str)
        lo = center - dt.timedelta(hours=window_hours)
        hi = center + dt.timedelta(hours=window_hours)
        best = None
        for t, v in self.SERIES.items():
            tt = ff.parse_station_local_time(t)
            if lo <= tt <= hi and (best is None or v > best[1]):
                best = (t, v)
        return (best[1], best[0]) if best else (None, None)

    def test_late_in_the_day_finds_the_early_crest(self):
        lb = lookback("", None, gauge=self._fake, now=dt.datetime(2026, 9, 27, 23, 0))
        self.assertEqual(lb["evidence"], "bay")
        self.assertEqual(lb["time_local"], "06:00")
        self.assertAlmostEqual(lb["navd88"], 7.5 - 2.82, places=2)

    def test_early_in_the_day_ignores_yesterdays_bigger_crest(self):
        lb = lookback("", None, gauge=self._fake, now=dt.datetime(2026, 9, 27, 1, 0))
        self.assertEqual(lb["evidence"], "bay")
        self.assertEqual(lb["time_local"], "00:30")


class PhraseTests(unittest.TestCase):
    def test_measured_phrase_with_claim(self):
        lb = {"evidence": "measured", "rel_grate_in": 25.2, "time_local": "09:44",
              "regime": "severe", "model_claim": {"rel_grate_in": 39.0, "time_local": "02:40"}}
        self.assertEqual(rendering._lookback_phrase(lb, short=True),
                         'MEASURED +25.2″ at 09:44; model claims +39.0″ at 02:40')
        self.assertIn("(unmeasured then)", rendering._lookback_phrase(lb))
        self.assertIn("&Prime;", rendering._lookback_phrase(lb, html=True))

    def test_dry_measurement_phrase_is_not_a_whole_day_claim(self):
        lb = {"evidence": "measured", "rel_grate_in": 0.0, "time_local": "02:50",
              "regime": "dry", "n_checks": 1}
        text = rendering._lookback_phrase(lb)
        self.assertIn("MEASURED no street water at 02:50", text)
        self.assertIn("1 check so far", text)
        self.assertIn("not a whole-day claim", text)
        self.assertTrue(rendering._lookback_visible(lb))

    def test_reported_phrase_marks_uncertain_time(self):
        lb = {"evidence": "reported", "rel_grate_in": None, "time_local": "20:06",
              "time_uncertain": True, "report": "NO flooding at the intersection"}
        self.assertEqual(rendering._lookback_phrase(lb, short=True), "REPORTED at ~20:06 (no tape)")
        self.assertIn("NO flooding", rendering._lookback_phrase(lb))
        self.assertTrue(rendering._lookback_visible(lb))

    def test_bay_and_model_phrases_and_visibility(self):
        self.assertIn("BAY PEAK +14.8", rendering._lookback_phrase(
            {"evidence": "bay", "rel_grate_in": 14.8, "time_local": "20:06"}))
        self.assertIn("unverified", rendering._lookback_phrase(
            {"evidence": "modeled", "rel_grate_in": 6.4, "time_local": "16:40"}))
        self.assertFalse(rendering._lookback_visible({"evidence": "modeled", "rel_grate_in": 0}))
        self.assertFalse(rendering._lookback_visible(None))

    def test_every_arm_uses_the_shared_phrase_and_gate(self):
        src = Path(rendering.__file__).read_text()
        self.assertEqual(src.count("_lookback_phrase("), 6)    # 1 def + 5 arms
        self.assertEqual(src.count("_lookback_visible("), 6)   # 1 def + 5 arms
        self.assertNotIn('_lb["source"]', src)
        # the raw positivity gate survives only inside the helper itself
        self.assertEqual(src.count('rel_grate_in") or 0) > 0'), 1)


if __name__ == "__main__":
    unittest.main()
